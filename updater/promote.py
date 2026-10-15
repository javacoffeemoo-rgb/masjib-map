"""candidates.json -> restaurants.json 승인 스크립트 (Nominatim 지오코딩)"""
import json, urllib.request, urllib.parse, time, re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REST = BASE / "restaurants.json"
CAND = BASE / "updater" / "candidates.json"

MANUAL = [
    # (candidate youtubeId, name, category, short address, menu)
    ("0r19H2CGeTg", "폴스다이너", "양식", "서울 용산구 녹사평대로54길 6", "경리단길 다이너"),
    ("0r19H2CGeTg", "여수댁", "한식", "서울 용산구 녹사평대로52길 17", "경리단길 한식"),
    ("8X-uk7WO83k", "일호족발", "족발", "서울 중랑구 사가정로50길 36", "족발"),
    ("xc_D1hAraD4", "신이 주신 선물", "오리고기", "서울 서초구 신반포로 334", "오리고기·오리백숙"),
    ("IOz7sdH57PQ", "복향원판점", "중식", "서울 중구 서애로1길 6-4", "중식당"),
    ("L9DMbzAsRXM", "논골집", "족발", "부산 해운대구 해운대해변로209번가길 3", "족발·불족발·오뎅탕"),
    ("W0tEtSoNGUs", "노케찹", "양식", "서울 용산구 한강대로62가길 20", "노케찹"),
    ("W0tEtSoNGUs", "대원식당", "한식", "서울 용산구 한강대로62나길 16-1", "삼각지 한식"),
    ("NFsxMs4DwGs", "버거리 건대점", "버거", "서울 광진구 능동로13길 36", "그릴드치즈버거"),
    ("u4bhSCvA36A", "제일식당", "한식", "서울 은평구 수색로 271", "삼겹살·집반찬"),
    ("oGlOUzsCa4k", "당케올레국수", "국수", "제주 서귀포시 표선면 표선당포로 4", "보말칼국수"),
    ("JT_90k23UMU", "홍복", "중식", "서울 중구 남대문시장길 73-3", "중식당"),
    ("mTOWU4Mtm44", "만천리상회", "막국수", "서울 강남구 삼성로 766", "들기름막국수·녹두전"),
    ("BY3BY_7ZYSk", "시미베", "일식", "서울 중구 퇴계로 386-1", "신당동 일식"),
]

def geo(q):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1, "countrycodes": "kr"})
    req = urllib.request.Request(url, headers={"User-Agent": "mukten-map/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read().decode())
        if d:
            return float(d[0]["lat"]), float(d[0]["lon"])
    return None, None

def slug(s):
    s = re.sub(r"[^0-9a-zA-Z가-힣]+", "-", s).strip("-")
    return s

def main():
    rest = json.loads(REST.read_text(encoding="utf-8"))
    cands = {c["youtubeId"]: c for c in json.loads(CAND.read_text(encoding="utf-8"))}
    have = {(r.get("youtubeId"), r["name"]) for r in rest}
    added = 0
    for yid, name, cat, addr, menu in MANUAL:
        if (yid, name) in have:
            print("skip", name)
            continue
        c = cands.get(yid, {})
        lat, lng = geo(addr)
        time.sleep(1)
        if lat is None:
            print("GEO FAIL:", name, addr)
            continue
        # 상세주소는 후보 description에서 같은 가게명 줄 찾기
        full_addr = addr
        desc = c.get("description", "")
        for line in desc.splitlines():
            if name.replace(" ", "") in line.replace(" ", "") and ("서울" in line or "부산" in line or "제주" in line):
                full_addr = line.strip().lstrip("[] ")
                break
        rest.append({
            "id": f"{slug(name)}-{yid[:6]}",
            "name": name,
            "category": cat,
            "address": full_addr,
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "menu": menu,
            "youtubeTitle": c.get("youtubeTitle", ""),
            "youtubeUrl": c.get("youtubeUrl", ""),
            "youtubeId": yid,
            "publishedAt": c.get("publishedAt", ""),
            "verified": True,
        })
        print(f"add {name} {lat},{lng}")
        added += 1
    REST.write_text(json.dumps(rest, ensure_ascii=False, indent=2), encoding="utf-8")
    (BASE / "last_updated.txt").write_text(__import__("datetime").date.today().isoformat(), encoding="utf-8")
    print(f"done: +{added}곳, 총 {len(rest)}곳")

if __name__ == "__main__":
    main()
