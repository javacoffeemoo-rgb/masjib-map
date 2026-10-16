"""candidates.json 전체를 restaurants.json에 일괄 등록.
- 설명란 [식당명]+주소 패턴 파싱, 한 영상 다중 식당 분리
- Nominatim 지오코딩 (실패 시 단계적 축소 재시도)
- 식당 아닌 영상(비공개/해외/주소없음)은 pending에 기록
- 20건마다 중간 저장 (재실행 안전)
"""
import json, urllib.request, urllib.parse, time, re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REST = BASE / "restaurants.json"
CAND = BASE / "updater" / "candidates.json"
PEND = BASE / "updater" / "pending.json"

AREA_TAIL = ("역", "동", "시장", "거리", "골목", "로데오", "타운")
MENU_WORDS = {"오리고기", "족발", "보쌈", "감자탕", "냉면", "칼국수", "국밥", "순대국",
              "순대", "막국수", "해장국", "설렁탕", "육개장", "삼겹살", "곱창", "막창",
              "치킨", "닭갈비", "버거", "햄버거", "초밥", "스시", "회", "탕", "찜",
              "전골", "국수", "면", "떡볶이", "피자", "파스타", "돈까스", "제육",
              "갈비", "등심", "안창살", "토시살", "수육", "편육", "내장탕", "술국"}
SKIP_NAMES = {"먹을텐데", "성시경", "광고", "경소주", "먹방", "맛집추천", "맛집탐방"}

CAT_RULES = [
    ("족발", "족발"), ("보쌈", "보쌈"), ("감자탕", "감자탕"), ("냉면", "냉면"),
    ("칼국수", "칼국수"), ("순대", "순대국"), ("국밥", "국밥"), ("해장국", "해장국"),
    ("설렁탕", "설렁탕"), ("막국수", "막국수"), ("육개장", "육개장"), ("중식", "중식"),
    ("짜장", "중식"), ("짬뽕", "중식"), ("마라", "중식"), ("버거", "버거"),
    ("햄버거", "버거"), ("초밥", "일식"), ("스시", "일식"), ("오마카세", "일식"),
    ("돈까스", "돈까스"), ("피자", "피자"), ("치킨", "치킨"), ("닭", "닭요리"),
    ("오리", "오리고기"), ("고기", "고기"), ("갈비", "고기"), ("삼겹", "고기"),
    ("축산", "고기"), ("정육", "고기"), ("곱창", "곱창"), ("막창", "곱창"),
    ("횟집", "회"), ("어죽", "어죽"), ("낙지", "낙지"), ("쭈꾸미", "쭈꾸미"),
    ("게장", "게장"), ("전복", "전복"), ("매운탕", "매운탕"), ("추어탕", "추어탕"),
    ("시장", "전통시장"), ("분식", "분식"), ("떡볶이", "분식"), ("카페", "카페"),
    ("베이커리", "카페"), ("디저트", "카페"), ("술집", "술집"), ("호프", "술집"),
    ("이자카야", "술집"), ("포차", "술집"),
]

def clean_name(raw):
    toks = raw.strip().split()
    while len(toks) > 1 and toks[0].endswith(AREA_TAIL):
        toks.pop(0)
    while len(toks) >= 3 and toks[-1] in MENU_WORDS:
        toks.pop()
    return " ".join(toks).strip()

def guess_cat(name, title):
    t = name + " " + title
    for kw, cat in CAT_RULES:
        if kw in t:
            return cat
    return "한식"

def geo(q):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1, "countrycodes": "kr"})
    req = urllib.request.Request(url, headers={"User-Agent": "mukten-map/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode())
            if d:
                return float(d[0]["lat"]), float(d[0]["lon"])
    except Exception:
        pass
    return None, None

def short_addr_variants(addr):
    a = re.sub(r"\(.*?\)", "", addr).strip()
    a = re.sub(r"\s*\d+\s*F\b|\s*B\d+\s*층?|\s*\d+\s*층", "", a).strip()
    a = re.sub(r"\s+", " ", a)
    v = [a]
    m = re.match(r"^((?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)\s+\S+[시군구]\s+\S+[로길])\s*(\d+)?", a)
    if m:
        if m.group(2):
            v.append(f"{m.group(1)} {m.group(2)}")
        v.append(m.group(1))
    return v

def extract_pairs(desc):
    """[(식당명, 주소)] 추출"""
    pairs = []
    lines = [l.strip() for l in desc.splitlines()]
    for i, line in enumerate(lines):
        for b in re.findall(r"\[(.+?)\]", line):
            name = clean_name(b)
            if not name or name in SKIP_NAMES or len(name) > 30:
                continue
            addr = ""
            for nxt in lines[i:i + 3]:
                m = re.search(r"((?:서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)[^\n]{2,50})", nxt)
                if m and ("로" in m.group(1) or "길" in m.group(1) or "동" in m.group(1)):
                    addr = m.group(1).strip()
                    break
            pairs.append((name, addr))
    # 중복 제거 (순서 유지)
    seen, out = set(), []
    for p in pairs:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out

def slug(s):
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "-", s).strip("-")[:20]

def save(rest, pending):
    REST.write_text(json.dumps(rest, ensure_ascii=False, indent=2), encoding="utf-8")
    PEND.write_text(json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    rest = json.loads(REST.read_text(encoding="utf-8"))
    cands = json.loads(CAND.read_text(encoding="utf-8"))
    pending = json.loads(PEND.read_text(encoding="utf-8")) if PEND.exists() else []
    pend_ids = {p["youtubeId"] for p in pending}
    have_pair = {(r.get("youtubeId"), r["name"]) for r in rest}
    have_name = {re.sub(r"\s+", "", r["name"]) for r in rest}
    added, skipped, n = 0, 0, 0
    for c in cands:
        yid = c["youtubeId"]
        title = c.get("youtubeTitle", "")
        if title in ("Private video", "Deleted video"):
            skipped += 1
            continue
        for name, addr in extract_pairs(c.get("description", "")):
            key = re.sub(r"\s+", "", name)
            if (yid, name) in have_pair or key in have_name:
                continue
            if not addr:
                if yid not in pend_ids:
                    pending.append({"youtubeId": yid, "title": title, "name": name,
                                    "reason": "주소없음", "url": c.get("youtubeUrl")})
                    pend_ids.add(yid)
                continue
            lat = lng = None
            for q in short_addr_variants(addr):
                lat, lng = geo(q)
                time.sleep(1)
                if lat:
                    break
            if lat is None:
                if yid not in pend_ids:
                    pending.append({"youtubeId": yid, "title": title, "name": name,
                                    "reason": "지오코딩실패: " + addr, "url": c.get("youtubeUrl")})
                    pend_ids.add(yid)
                print("FAIL", name, addr)
                continue
            cat = guess_cat(name, title)
            rest.append({
                "id": f"{slug(name)}-{yid[:6]}",
                "name": name, "category": cat, "address": addr,
                "lat": round(lat, 6), "lng": round(lng, 6), "menu": "",
                "youtubeTitle": title, "youtubeUrl": c.get("youtubeUrl"),
                "youtubeId": yid, "publishedAt": c.get("publishedAt", ""),
                "verified": True,
            })
            have_pair.add((yid, name))
            have_name.add(key)
            added += 1
            n += 1
            print(f"add {name} [{cat}]")
            if n % 20 == 0:
                save(rest, pending)
                print(f"... 중간저장 {len(rest)}곳")
    save(rest, pending)
    (__import__("datetime").date.today().isoformat())
    (BASE / "last_updated.txt").write_text(__import__("datetime").date.today().isoformat(), encoding="utf-8")
    print(f"done: +{added}곳, skip 영상 {skipped}개, 총 {len(rest)}곳, pending {len(pending)}건")

if __name__ == "__main__":
    main()
