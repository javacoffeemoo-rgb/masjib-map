"""
성시경 먹을텐데 매일 업데이트 스크립트
- 유튜브 Data API v3로 '먹을텐데' 재생목록 신상 영상을 가져옴
- 완전 자동 식당명/주소 추출은 오탐이 많아 '후보(candidates)'로 분리 저장
- 사람이 candidates.json 확인 후 restaurants.json에 확정하는 반자동 구조 (추천 방식)

필요 환경변수:
  YOUTUBE_API_KEY : YouTube Data API v3 키
선택 환경변수 (좌표 자동보정용):
  NAVER_CLIENT_ID, NAVER_CLIENT_SECRET : Naver Cloud Geocode용

실행:
  pip install -r requirements.txt
  set YOUTUBE_API_KEY=xxx & python fetch_mukten.py
"""
import os, re, json, datetime, urllib.request, urllib.parse
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REST_JSON = BASE / "restaurants.json"
CAND_JSON = BASE / "updater" / "candidates.json"
LAST_TXT = BASE / "last_updated.txt"

PLAYLIST_ID = "PLuMuHAJh9g_Py_PSm8gmHdlcil6CQ9QCM"  # 성시경의 먹을텐데
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

ADDR_RE = re.compile(r"(서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)[^\n]{0,40}[시군구읍면동로길]\s?[^\n]{0,40}\d*")

def yt_get(url, params):
    q = urllib.parse.urlencode({**params, "key": YOUTUBE_API_KEY})
    with urllib.request.urlopen(f"{url}?{q}", timeout=20) as r:
        return json.loads(r.read().decode())

def fetch_playlist_videos(max_n=15):
    """최근 영상 max_n개 반환"""
    items, page = [], None
    while len(items) < max_n:
        p = {"part": "snippet,contentDetails", "playlistId": PLAYLIST_ID, "maxResults": min(50, max_n - len(items))}
        if page: p["pageToken"] = page
        data = yt_get("https://www.googleapis.com/youtube/v3/playlistItems", p)
        items += data.get("items", [])
        page = data.get("nextPageToken")
        if not page: break
    out = []
    for it in items:
        sn = it["snippet"]
        out.append({
            "youtubeId": sn["resourceId"]["videoId"],
            "youtubeTitle": sn["title"],
            "youtubeUrl": f"https://www.youtube.com/watch?v={sn['resourceId']['videoId']}",
            "description": sn.get("description", ""),
            "publishedAt": sn.get("publishedAt", "")[:10],
        })
    return out

def fetch_descriptions(videos):
    """description 전체가 필요하면 videos API로 보강 (playlist snippet은 잘림)"""
    ids = [v["youtubeId"] for v in videos]
    for i in range(0, len(ids), 50):
        chunk = ",".join(ids[i:i+50])
        data = yt_get("https://www.googleapis.com/youtube/v3/videos",
                       {"part": "snippet", "id": chunk})
        desc_map = {v["id"]: v["snippet"].get("description", "") for v in data.get("items", [])}
        for v in videos:
            if v["youtubeId"] in desc_map and len(desc_map[v["youtubeId"]]) > len(v["description"]):
                v["description"] = desc_map[v["youtubeId"]]
    return videos

def geocode_naver(query):
    cid = os.environ.get("NAVER_CLIENT_ID", "")
    sec = os.environ.get("NAVER_CLIENT_SECRET", "")
    if not cid or not sec: return None, None
    url = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode?query=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"X-NCP-APIGW-API-KEY-ID": cid, "X-NCP-APIGW-API-KEY": sec})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode())
            addrs = d.get("addresses", [])
            if addrs: return float(addrs[0]["y"]), float(addrs[0]["x"])
    except Exception as e:
        print("geocode fail:", query, e)
    return None, None

def guess_name(title):
    # "OOO | 먹을텐데", "먹을텐데 OOO편", "[먹을텐데] OOO" 등에서 식당명 추측
    t = re.sub(r"(성시경|먹을텐데|먹을 텐데|ep\.?\d+|편|｜|\||\[|\]|\(|\)|-|,)", " ", title)
    t = re.sub(r"\s+", " ", t).strip()
    parts = t.split(" ")
    # 너무 짧거나 일반적인 단어는 제외, 가장 그럴듯한 1~2단어 반환 (사람 검수 전제)
    return t[:40]

def main():
    if not YOUTUBE_API_KEY:
        print("YOUTUBE_API_KEY 없음. YouTube 콘솔에서 Data API v3 키 발급 후 환경변수로 설정.")
        return
    rest = json.loads(REST_JSON.read_text(encoding="utf-8"))
    known_ids = {r.get("youtubeId") for r in rest if r.get("youtubeId")}
    videos = fetch_playlist_videos(15)
    videos = fetch_descriptions(videos)
    new_cands = []
    for v in videos:
        if v["youtubeId"] in known_ids: continue
        m = ADDR_RE.search(v["description"] + "\n" + v["youtubeTitle"])
        addr = m.group(0).strip() if m else ""
        lat, lng = (None, None)
        if addr:
            lat, lng = geocode_naver(addr)
        new_cands.append({
            "guessName": guess_name(v["youtubeTitle"]),
            "address_guess": addr,
            "lat": lat, "lng": lng,
            "needsReview": True,
            **v,
        })
    # 기존 candidates와 병합
    old = json.loads(CAND_JSON.read_text(encoding="utf-8")) if CAND_JSON.exists() else []
    old_ids = {c["youtubeId"] for c in old}
    merged = old + [c for c in new_cands if c["youtubeId"] not in old_ids]
    CAND_JSON.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    LAST_TXT.write_text(datetime.date.today().isoformat(), encoding="utf-8")
    print(f"신규 후보 {len(new_cands)}건, 누적 후보 {len(merged)}건 -> updater/candidates.json 확인 후 restaurants.json에 확정 추가하세요.")

if __name__ == "__main__":
    main()
