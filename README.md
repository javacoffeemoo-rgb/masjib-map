# 🍶 성시경 먹을텐데 지도

성시경이 다녀간 곳(유튜브 `성시경 SUNG SI KYUNG` → `먹을텐데` 재생목록)만 보여주는 모바일 웹 지도.
지도: 네이버지도 / 데이터: `restaurants.json` / 5일마다 업데이트: 유튜브 API 스크립트.

## 1. 실행 방법
1. `config.js`에 네이버 Client ID 입력
   - 발급: https://console.ncloud.com → AI·NAVER API → Application → Maps(Web Dynamic Map) 선택
   - Web 서비스 URL에 `http://localhost:8000` 등록 (배포 시 실제 도메인도 추가)
2. 로컬 실행:
```powershell
cd sung-food-map
python -m http.server 8000
# 브라우저: http://localhost:8000
```
> `file://`로 직접 열면 `restaurants.json` fetch가 차단되므로 반드시 http 서버로 실행.

## 2. 5일마다 업데이트 (선택한 방식: 유튜브 자동수집)
정확도 문제로 **완전 자동 확정은 하지 않음**. 스크립트가 신상 영상을 후보로 뽑고, 사람이 1분 검수 후 확정하는 반자동.

- 재생목록 ID: `PLuMuHAJh9g_Py_PSm8gmHdlcil6CQ9QCM`
- 채널 ID: `UCl23-Cci_SMqyGXE1T_LYUg`

### 로컬(Windows) 5일마다 실행
1. https://console.cloud.google.com → YouTube Data API v3 키 발급
2. `setx YOUTUBE_API_KEY "키값"` (재부팅 없이 영구 저장)
3. `pip install -r updater/requirements.txt`
4. `python updater/fetch_mukten.py` → `updater/candidates.json`에 신규 후보 쌓임
5. 후보 확인 후 `restaurants.json`에 아래 형식 1줄 추가:
```json
{"id":"고유id","name":"식당명","category":"냉면","address":"서울 ...","lat":37.5,"lng":127.0,"menu":"대표메뉴","youtubeTitle":"영상제목","youtubeUrl":"https://www.youtube.com/watch?v=...","youtubeId":"...","publishedAt":"2026-10-15","verified":true}
```
6. 좌표는 네이버지도에서 식당 검색 → URL 속 `lat/lng` 복사, 또는 스크립트의 Naver Geocode 자동보정 사용 (`NAVER_CLIENT_ID/SECRET` 환경변수 설정 시)
7. 작업 스케줄러 → `daily_update.bat`를 매일 오전 9시 등록하면 완전 로컬 자동화.

### GitHub Actions 5일마다 실행
- 리포지토리 Secrets에 `YOUTUBE_API_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` 등록
- `.github/workflows/daily-update.yml`이 5일마다 09:00 KST 실행 → 후보 자동 커밋.

## 3. 왜 완전 자동 확정을 안 하나요?
- 먹을텐데 영상 설명란에 주소가 항상 정형으로 있지 않음
- 제목에서 식당명 자동 추출 시 오탐 (예: "또 갔습니다" 같은 문구)
- 잘못된 핀이 찍히면 지도 신뢰도가 깨지므로 후보→검수 1단계 유지. 검수는 건당 1분 내외.

## 4. 파일 구조
```
sung-food-map/
 index.html / style.css / app.js / config.js
 restaurants.json      ← 확정 데이터 (지도에 표시되는 것)
 last_updated.txt      ← 화면에 표시되는 날짜
 updater/fetch_mukten.py / candidates.json
 .github/workflows/daily-update.yml
```

## 5. 다음 확장 아이디어
- 지역구/지하철역 필터, 영업중 표시, 웨이팅 정보
- 관리자 페이지 (후보 승인 버튼식)
