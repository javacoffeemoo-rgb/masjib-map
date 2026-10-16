let allData = [];
let markers = [];
let map = null;
let infoWindow = null;
let userLoc = null;

function distKm(a, b, c, d) {
  const R = 6371, t = Math.PI / 180;
  const h = Math.sin((c - a) * t / 2) ** 2 + Math.cos(a * t) * Math.cos(c * t) * Math.sin((d - b) * t / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
function fmtDist(km) { return km < 1 ? Math.round(km * 1000) + "m" : km.toFixed(1) + "km"; }

function loadNaverMap() {
  return new Promise((resolve, reject) => {
    const cid = window.NAVER_CLIENT_ID;
    if (!cid || cid === "YOUR_NAVER_CLIENT_ID") {
      reject(new Error("NAVER_CLIENT_ID 미설정"));
      return;
    }
    const s = document.createElement("script");
    s.src = "https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=" + cid;
    s.onload = resolve;
    s.onerror = () => reject(new Error("네이버 지도 로드 실패"));
    document.head.appendChild(s);
  });
}

function initMap() {
  map = new naver.maps.Map("map", {
    center: new naver.maps.LatLng(37.55, 126.98),
    zoom: 11,
  });
  infoWindow = new naver.maps.InfoWindow({ anchorSkew: true });
}

function clearMarkers() {
  markers.forEach((m) => m.setMap(null));
  markers = [];
}

function drawMarkers(list) {
  clearMarkers();
  const bounds = new naver.maps.LatLngBounds();
  list.forEach((r, idx) => {
    const pos = new naver.maps.LatLng(r.lat, r.lng);
    const marker = new naver.maps.Marker({
      position: pos,
      map,
      title: r.name,
    });
    naver.maps.Event.addListener(marker, "click", () => showDetail(r.id, true));
    markers.push(marker);
    bounds.extend(pos);
  });
  if (list.length > 0) {
    if (list.length === 1) map.setCenter(new naver.maps.LatLng(list[0].lat, list[0].lng));
    else map.fitBounds(bounds);
  }
}

function naverLink(r) {
  // 네이버 리뷰 API가 외부에 없어 플레이스 검색으로 연결 (첫 결과가 해당 가게)
  return "https://map.naver.com/p/search/" + encodeURIComponent(r.name + " " + r.address);
}

function renderList(list) {
  const el = document.getElementById("list");
  document.getElementById("count").textContent = `총 ${list.length}곳 · 성시경 먹을텐데만`;
  document.getElementById("updated").textContent = "업데이트: " + (window.LAST_UPDATED || "restaurants.json 기준");
  el.querySelectorAll(".card").forEach((n) => n.remove());
  list.forEach((r) => {
    const d = document.createElement("div");
    d.className = "card";
    d.id = "card-" + r.id;
    const dist = userLoc ? `<em class="dist">📍${fmtDist(distKm(userLoc.lat, userLoc.lng, r.lat, r.lng))}</em>` : "";
    d.innerHTML = `<h3>${r.name}<em>${r.category}</em>${dist}</h3>
      <div class="addr">${r.address}</div>
      ${r.menu ? `<div class="menu">🍽 ${r.menu}</div>` : ""}
      <div class="links">
        <a class="btn yt" href="${r.youtubeUrl}" target="_blank" onclick="event.stopPropagation()">▶ 영상보기</a>
        <a class="btn review" href="${naverLink(r)}" target="_blank" onclick="event.stopPropagation()">⭐ 리뷰보기</a>
        <button class="btn" onclick="event.stopPropagation();copyAddr('${r.id}')">주소복사</button>
      </div>`;
    d.onclick = () => showDetail(r.id, true);
    el.appendChild(d);
  });
}

function showDetail(id, moveMap) {
  const r = allData.find((x) => x.id === id);
  if (!r) return;
  document.querySelectorAll(".card").forEach((c) => c.classList.remove("active"));
  const card = document.getElementById("card-" + id);
  if (card) card.scrollIntoView({ behavior: "smooth", block: "center" }), card.classList.add("active");
  const det = document.getElementById("detail");
  det.innerHTML = `<button class="close" onclick="hideDetail()">✕</button>
    <h2>${r.name} <span style="font-size:12px;color:#888">${r.category}</span></h2>
    <div style="font-size:13px;color:#555">${r.address}</div>
    ${r.menu ? `<div style="font-size:13px;margin-top:6px">🍽 ${r.menu}</div>` : ""}
    <div style="font-size:12px;color:#888;margin-top:6px">🎬 ${r.youtubeTitle}</div>
    <div class="row">
      <a class="naver" target="_blank" href="${naverLink(r)}">⭐ 리뷰·길찾기</a>
      <a class="youtube" target="_blank" href="${r.youtubeUrl}">유튜브 원본</a>
    </div>
    <div style="font-size:11px;color:#999;margin-top:8px">리뷰는 네이버 플레이스에서 확인 (검색 첫 결과가 해당 가게)</div>`;
  det.classList.add("show");
  if (moveMap && map) {
    map.setCenter(new naver.maps.LatLng(r.lat, r.lng));
    map.setZoom(16);
  }
}
function hideDetail() { document.getElementById("detail").classList.remove("show"); }
function copyAddr(id) {
  const r = allData.find((x) => x.id === id);
  navigator.clipboard.writeText(r.address).then(() => alert("주소 복사됨: " + r.address));
}

function applyFilter() {
  const q = document.getElementById("q").value.trim();
  const cat = document.getElementById("cat").value;
  let list = allData.filter((r) => {
    const okQ = !q || (r.name + r.address + r.menu).includes(q);
    const okC = !cat || r.category === cat;
    return okQ && okC;
  });
  if (userLoc) list = list.slice().sort((a, b) =>
    distKm(userLoc.lat, userLoc.lng, a.lat, a.lng) - distKm(userLoc.lat, userLoc.lng, b.lat, b.lng));
  renderList(list);
  if (map) drawMarkers(list);
}

function fillCategories() {
  const cats = [...new Set(allData.map((r) => r.category))].sort();
  const sel = document.getElementById("cat");
  cats.forEach((c) => {
    const o = document.createElement("option");
    o.value = c; o.textContent = c;
    sel.appendChild(o);
  });
}

async function boot() {
  const res = await fetch("restaurants.json?t=" + Date.now());
  allData = await res.json();
  try {
    const h = await fetch("last_updated.txt?t=" + Date.now()).then((r) => r.text());
    window.LAST_UPDATED = h.trim();
  } catch {}
  fillCategories();
  renderList(allData);
  document.getElementById("q").addEventListener("input", applyFilter);
  document.getElementById("cat").addEventListener("change", applyFilter);
  document.getElementById("locate").onclick = () => {
    if (!navigator.geolocation) return alert("위치 미지원");
    navigator.geolocation.getCurrentPosition((p) => {
      userLoc = { lat: p.coords.latitude, lng: p.coords.longitude };
      if (map) {
        map.setCenter(new naver.maps.LatLng(userLoc.lat, userLoc.lng));
        map.setZoom(14);
      }
      applyFilter();
    }, () => alert("위치 권한을 허용해주세요"));
  };
  try {
    await loadNaverMap();
    initMap();
    drawMarkers(allData);
  } catch (e) {
    document.getElementById("map").innerHTML =
      `<div style="padding:30px;text-align:center;font-size:14px">네이버 Client ID를 <b>config.js</b>에 입력하면 지도가 표시됩니다.<br><br>목록은 아래에서 정상 사용 가능.</div>`;
  }
}
boot();
