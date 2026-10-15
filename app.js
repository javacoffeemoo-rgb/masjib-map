let allData = [];
let markers = [];
let map = null;
let infoWindow = null;

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
    d.innerHTML = `<h3>${r.name}<em>${r.category}</em></h3>
      <div class="addr">${r.address}</div>
      <div class="menu">🍽 ${r.menu}</div>
      <div class="links">
        <a class="btn yt" href="${r.youtubeUrl}" target="_blank" onclick="event.stopPropagation()">▶ 영상보기</a>
        <a class="btn" href="${naverLink(r)}" target="_blank" onclick="event.stopPropagation()">네이버지도</a>
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
    <div style="font-size:13px;margin-top:6px">🍽 ${r.menu}</div>
    <div style="font-size:12px;color:#888;margin-top:6px">🎬 ${r.youtubeTitle}</div>
    <div class="row">
      <a class="naver" target="_blank" href="${naverLink(r)}">네이버 길찾기</a>
      <a class="youtube" target="_blank" href="${r.youtubeUrl}">유튜브 원본</a>
    </div>`;
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
    if (!navigator.geolocation || !map) return alert("위치 미지원");
    navigator.geolocation.getCurrentPosition((p) => {
      map.setCenter(new naver.maps.LatLng(p.coords.latitude, p.coords.longitude));
      map.setZoom(14);
    });
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
