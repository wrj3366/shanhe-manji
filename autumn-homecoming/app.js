(() => {
  'use strict';
  const { days, budget, preparation } = window.tripData;
  const colors = { outbound: '#2e6789', home: '#34775b', return: '#a65a27' };
  const phaseNames = { outbound: '去程', home: '在家', return: '返程' };
  // Regional WGS84 anchors, not hotel addresses or scenic-area entrances.
  const stops = {
    beijing: { name: '北京', coords: [39.9042, 116.4074], day: 1, label: '起 / 终', phase: 'outbound', direction: 'right' },
    datong: { name: '大同 · 2晚', coords: [40.0768, 113.3001], day: 2, label: '同', phase: 'outbound', direction: 'bottom' },
    hohhot: { name: '呼和浩特 · 停车换飞机', coords: [40.8426, 111.7492], day: 4, label: '呼', phase: 'outbound', direction: 'left' },
    hasuhai: { name: '哈素海 · 敕勒川', coords: [40.63, 111.04], day: 4, label: '湖', phase: 'outbound', direction: 'left' },
    volcano: { name: '乌兰哈达火山', coords: [41.62, 113.13], day: 12, label: '火', phase: 'return', direction: 'top' },
    xiy: { name: '西安咸阳机场 · 接送', coords: [34.4471, 108.7516], day: 5, label: '✈', phase: 'home', direction: 'right' },
    xunyi: { name: '旬邑 · 家', coords: [35.1122, 108.3337], day: 6, label: '家', phase: 'home', direction: 'left' },
    wulanchabu: { name: '乌兰察布 · 集宁2晚', coords: [40.9949, 113.1326], day: 11, label: '乌', phase: 'return', direction: 'top' },
    huitengxile: { name: '辉腾锡勒 · 黄花沟', coords: [41.10, 112.52], day: 11, label: '草', phase: 'return', direction: 'left' }
  };
  const calendar = document.getElementById('calendar');
  const dayList = document.getElementById('day-list');
  const cards = new Map();
  let selectedDay = null;
  let selectedPhase = 'all';
  let tripMap;
  const routes = new Map();
  const markers = new Map();
  let scenicLayer;
  // Approximate scenic-area anchors; exact entrances are found through named searches.
  const scenicPoints = {
    yungang: { name: '云冈石窟', coords: [40.11, 113.13], query: '大同 云冈石窟 游客中心' },
    huayan: { name: '华严寺 · 可选', coords: [40.09, 113.29], query: '大同 华严寺' },
    dazhao: { name: '大召寺 / 塞上老街', coords: [40.80, 111.65], query: '呼和浩特 大召寺' },
  };
  const scenicByDay = { 2: ['yungang', 'huayan'], 3: ['dazhao'] };
  const escape = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const range = values => values[0] === values[1] ? String(values[0]) : values.join('—');
  const searchUrl = query => `https://www.amap.com/search?query=${encodeURIComponent(query)}`;
  const dateLabel = date => date.slice(5).replace('-', '.');
  const distanceText = day => day.phase === 'home' ? '自有车停呼市' : `${day.mode === 'flight' ? '呼市地面自驾' : '自驾'}约${range(day.km)}公里`;
  const driveText = day => day.phase === 'home' ? '无长途安排' : day.mode === 'flight' ? '飞机 + 地面接送 · 半天以上' : `纯开约${range(day.hours)}小时`;
  const total = days.reduce((sum, day) => [sum[0] + day.km[0], sum[1] + day.km[1]], [0, 0]);
  document.getElementById('total-km').innerHTML = `${(Math.round(total[0] / 100) * 100).toLocaleString()}—${(Math.round(total[1] / 100) * 100).toLocaleString()}<span>公里</span>`;

  for (const day of days) {
    const dateButton = document.createElement('button');
    dateButton.type = 'button';
    dateButton.className = 'date-button';
    dateButton.style.setProperty('--phase-color', colors[day.phase]);
    dateButton.dataset.day = day.id;
    dateButton.setAttribute('aria-pressed', 'false');
    dateButton.setAttribute('aria-label', `D${day.id} ${dateLabel(day.date)} ${day.title}`);
    dateButton.innerHTML = `<small>D${day.id} · ${day.weekday}</small><strong>${dateLabel(day.date)}</strong><span>${escape(day.mode === 'flight' ? (day.id === 5 ? '✈ 回家' : '✈ 取车') : day.phase === 'home' ? '旬邑在家' : stops[day.to].name.split(' · ')[0])}</span>`;
    dateButton.addEventListener('click', () => selectDay(day.id));
    calendar.appendChild(dateButton);

    const card = document.createElement('details');
    card.className = 'day-card';
    card.id = `day-${day.id}`;
    card.style.setProperty('--phase-color', colors[day.phase]);
    card.dataset.phase = day.phase;
    card.innerHTML = `<summary><span class="day-number">D${String(day.id).padStart(2, '0')}</span><div><strong>${escape(day.title)}</strong><small>${dateLabel(day.date)} ${day.weekday} · ${distanceText(day)}</small></div></summary>
      <div class="day-content"><p>${escape(day.subtitle)}</p>${day.transfer ? `<p class="travel-transfer">${escape(day.transfer)}</p>` : ''}<div class="pills"><span>${driveText(day)}</span>${day.highlights.map(item => `<span>${escape(item)}</span>`).join('')}</div>
      <ol class="schedule">${day.schedule.map(item => `<li><time>${escape(item.time)}</time><p>${escape(item.text)}</p></li>`).join('')}</ol>
      <div class="day-meta"><div><strong>今晚住哪里</strong><p>${escape(day.stay)}</p><p class="small muted">${escape(day.stayNote)}</p></div><div><strong>当地吃什么</strong><p>${escape(day.food)}</p></div><div><strong>预约与准备</strong><p>${escape(day.booking)}</p></div></div>
      <p class="day-note">${escape(day.tip)}</p><details class="backup"><summary>天气或时间变化时，怎么调整</summary><p>${escape(day.backup)}</p></details>
      <div class="nav-links">${day.searches.map(item => `<a href="${searchUrl(item.query)}" target="_blank" rel="noopener noreferrer">${escape(item.name)} · 高德 ↗</a>`).join('')}</div></div>`;
    card.querySelector('summary').addEventListener('click', event => {
      event.preventDefault();
      if (card.open) {
        card.open = false;
        selectedDay = null;
        syncControls();
        setSummary();
        updateMap();
      }
      else selectDay(day.id, false);
    });
    dayList.appendChild(card);
    cards.set(day.id, card);
  }

  function syncControls() {
    document.querySelectorAll('.filter-group [data-phase]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.phase === selectedPhase)));
    document.querySelectorAll('.date-button').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.day) === selectedDay)));
    cards.forEach((card, id) => { card.hidden = selectedPhase !== 'all' && days[id - 1].phase !== selectedPhase; });
    document.getElementById('day-count').textContent = `${days.filter(day => selectedPhase === 'all' || day.phase === selectedPhase).length}天`;
  }

  function setSummary(day) {
    const box = document.getElementById('selection-summary');
    box.style.setProperty('--phase-color', colors[day ? day.phase : 'outbound']);
    box.innerHTML = day
      ? `<span class="day-number">D${day.id}</span><div><strong>${dateLabel(day.date)} · ${escape(day.title)}</strong><p>${distanceText(day)} · ${driveText(day)} · ${escape(day.stay)}</p></div>`
      : `<span class="day-number">${days.filter(item => selectedPhase === 'all' || item.phase === selectedPhase).length}天</span><div><strong>${selectedPhase === 'all' ? '去程大同，返程集宁连住两晚后直返北京；中段飞回家' : phaseNames[selectedPhase] + '路线'}</strong><p>${selectedPhase === 'home' ? '9月29日到家，10月4日离家；9月30日—10月3日四个完整白天。' : '选择一天，地图高亮当天路线，右侧展开行程。'}</p></div>`;
  }

  function focusCard(card) {
    const listRect = dayList.getBoundingClientRect();
    dayList.scrollTop += card.getBoundingClientRect().top - listRect.top - 8;
  }

  function selectDay(id, scroll = true) {
    const day = days.find(item => item.id === id);
    if (!day) return;
    selectedDay = id;
    if (selectedPhase !== 'all' && selectedPhase !== day.phase) selectedPhase = 'all';
    cards.forEach((card, cardId) => { card.open = cardId === id; });
    syncControls();
    setSummary(day);
    updateMap(day);
    if (scroll) focusCard(cards.get(id));
  }

  function setPhase(phase) {
    selectedPhase = phase;
    selectedDay = null;
    if (tripMap) tripMap.closePopup();
    cards.forEach(card => { card.open = false; });
    dayList.scrollTop = 0;
    syncControls();
    setSummary();
    updateMap();
  }
  document.querySelectorAll('.filter-group [data-phase]').forEach(button => button.addEventListener('click', () => setPhase(button.dataset.phase)));
  document.getElementById('reset-map').addEventListener('click', () => setPhase('all'));
  document.getElementById('show-flight').addEventListener('click', () => {
    selectedPhase = 'all';
    selectDay(5);
    document.getElementById('journey').scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
  });

  const stayList = document.getElementById('stay-list');
  const stays = [];
  days.slice(0, -1).forEach(day => {
    const previous = stays[stays.length - 1];
    if (previous && previous.city === day.to) { previous.end = day.date; previous.nights++; }
    else stays.push({ city: day.to, start: day.date, end: day.date, nights: 1, stay: day.stay, note: day.stayNote });
  });
  stayList.innerHTML = stays.map(stay => `<div class="stay-row"><time>${dateLabel(stay.start)}${stay.start !== stay.end ? '—' + dateLabel(stay.end) : ''}</time><div><strong>${escape(stay.stay)} · ${stay.nights}晚</strong><p>${escape(stay.note)}</p></div></div>`).join('');
  document.getElementById('budget-list').innerHTML = budget.map(item => `<tr><td><details><summary>${escape(item.name)}</summary><p>${escape(item.note)}</p></details></td><td>${escape(item.range)}</td></tr>`).join('');
  document.getElementById('preparation-list').innerHTML = preparation.map(item => `<li>${escape(item)}</li>`).join('');
  setSummary();

  // Reuse the existing project's WGS84 → GCJ-02 conversion for its Amap basemap.
  function transformLat(x, y) {
    let ret = -100 + 2*x + 3*y + .2*y*y + .1*x*y + .2*Math.sqrt(Math.abs(x));
    ret += (20*Math.sin(6*x*Math.PI) + 20*Math.sin(2*x*Math.PI))*2/3;
    ret += (20*Math.sin(y*Math.PI) + 40*Math.sin(y/3*Math.PI))*2/3;
    ret += (160*Math.sin(y/12*Math.PI) + 320*Math.sin(y*Math.PI/30))*2/3;
    return ret;
  }
  function transformLng(x, y) {
    let ret = 300 + x + 2*y + .1*x*x + .1*x*y + .1*Math.sqrt(Math.abs(x));
    ret += (20*Math.sin(6*x*Math.PI) + 20*Math.sin(2*x*Math.PI))*2/3;
    ret += (20*Math.sin(x*Math.PI) + 40*Math.sin(x/3*Math.PI))*2/3;
    ret += (150*Math.sin(x/12*Math.PI) + 300*Math.sin(x/30*Math.PI))*2/3;
    return ret;
  }
  function project([lat, lng]) {
    if (lng < 72.004 || lng > 137.8347 || lat < .8293 || lat > 55.8271) return [lat, lng];
    const a = 6378245, ee = .00669342162296594323;
    const rad = lat / 180 * Math.PI;
    const magic = 1 - ee * Math.sin(rad) ** 2;
    const root = Math.sqrt(magic);
    return [lat + transformLat(lng-105,lat-35)*180/((a*(1-ee)/(magic*root))*Math.PI), lng + transformLng(lng-105,lat-35)*180/(a/root*Math.cos(rad)*Math.PI)];
  }
  const dayLegs = day => day.legs || (day.from === day.to ? [] : [{ from: day.from, to: day.to, mode: 'drive' }]);
  const pointKeys = day => [...new Set([day.from, ...dayLegs(day).flatMap(leg => [leg.from, leg.to]), day.to])];
  const visibleDays = () => days.filter(day => selectedPhase === 'all' || day.phase === selectedPhase);

  function updateMap(day) {
    if (!tripMap) return;
    const visible = visibleDays();
    const activeKeys = new Set((day ? [day] : visible).flatMap(pointKeys));
    routes.forEach((lines, id) => {
      const current = days[id - 1];
      const shown = selectedPhase === 'all' || current.phase === selectedPhase;
      lines.forEach(line => line.setStyle({ opacity: shown ? (day ? id === day.id ? 1 : .2 : .85) : 0, weight: day && id === day.id ? 5 : 3 }));
    });
    markers.forEach((marker, key) => {
      const visibleKeys = new Set(visible.flatMap(pointKeys));
      marker.setOpacity(visibleKeys.has(key) ? (activeKeys.has(key) ? 1 : .4) : .15);
      if (activeKeys.has(key)) marker.openTooltip(); else marker.closeTooltip();
    });
    const bounds = [...activeKeys].map(key => project(stops[key].coords));
    scenicLayer.clearLayers();
    if (day) (scenicByDay[day.id] || []).forEach((key, index) => {
      const point = scenicPoints[key];
      bounds.push(project(point.coords));
      const marker = L.circleMarker(project(point.coords), { radius: 7, color: 'white', weight: 2, fillColor: colors[day.phase], fillOpacity: 1 }).addTo(scenicLayer);
      marker.bindTooltip(point.name, { permanent: true, direction: index % 2 ? 'left' : 'right', offset: [index % 2 ? -8 : 8, 0], className: 'city-tip' });
      marker.bindPopup(`<strong>${point.name}</strong><br>景区区域示意，入口以当期公告为准。<br><a href="${searchUrl(point.query)}" target="_blank" rel="noopener noreferrer">高德搜索 ↗</a>`);
    });
    if (bounds.length === 1) tripMap.setView(bounds[0], 9, { animate: false });
    else if (bounds.length) tripMap.fitBounds(bounds, { padding: [65, 45], maxZoom: day && day.from === day.to ? 12 : 9, animate: false });
  }

  const mapError = document.getElementById('map-error');
  if (window.L) {
    tripMap = L.map('map', { scrollWheelZoom: false, zoomSnap: .25, zoomDelta: .5, maxZoom: 12 });
    scenicLayer = L.layerGroup().addTo(tripMap);
    const tileLayer = L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}', {
      subdomains: ['1', '2', '3', '4'], maxZoom: 12, attribution: '© 高德地图 · 行程示意'
    }).addTo(tripMap);
    let successfulTiles = 0;
    tileLayer.on('tileload', () => { successfulTiles++; mapError.hidden = true; });
    tileLayer.on('tileerror', () => { if (!successfulTiles) { mapError.textContent = '底图暂时无法加载，仍可查看路线与每日路书；精确导航请使用高德搜索。'; mapError.hidden = false; } });
    days.forEach(day => {
      const lines = dayLegs(day).map(leg => {
        const modeLabel = leg.mode === 'flight' ? '飞行示意' : leg.mode === 'transfer' ? '陕西地面接送' : '自驾示意';
        const line = L.polyline([leg.from, leg.to].map(key => project(stops[key].coords)), {
          color: leg.mode === 'flight' ? '#7560a0' : leg.mode === 'transfer' ? '#34775b' : colors[day.phase],
          weight: 3, dashArray: leg.mode === 'flight' ? '10 8' : leg.mode === 'transfer' ? '3 7' : null, opacity: .85
        }).addTo(tripMap);
        line.bindTooltip(`D${day.id} ${day.title} · ${modeLabel}`);
        line.on('click', () => selectDay(day.id));
        return line;
      });
      routes.set(day.id, lines);
    });
    Object.entries(stops).forEach(([key, stop]) => {
      const marker = L.marker(project(stop.coords), { title: `${stop.name}，点击查看行程`, icon: L.divIcon({ className: '', html: `<div class="pin ${stop.phase}" style="--phase-color:${colors[stop.phase]}">${stop.label}</div>`, iconSize: [29, 29], iconAnchor: [14, 14] }) }).addTo(tripMap);
      marker.bindTooltip(stop.name, { permanent: true, direction: stop.direction, offset: stop.direction === 'top' ? [0, -17] : stop.direction === 'left' ? [-17, 0] : [17, 0], className: 'city-tip' });
      marker.bindPopup(`<strong>${stop.name}</strong><br>${key === 'xunyi' ? '9/29到家，9/30—10/3四个完整白天，10/4离家。' : key === 'hohhot' ? '自有车留呼市9/29—10/4约5晚。点位为城市，非机场停车点。' : key === 'xiy' ? '落地接送回旬邑，无需进西安市区。' : '查看右侧每日安排。'}<br><a href="${searchUrl(stop.name.split(' · ')[0])}" target="_blank" rel="noopener noreferrer">高德搜索 ↗</a>`);
      marker.on('click', () => {
        const current = selectedDay ? days[selectedDay - 1] : null;
        if (current && pointKeys(current).includes(key)) { selectDay(current.id); return; }
        const phase = selectedPhase !== 'all' ? selectedPhase : current?.phase;
        let dayId = stop.day;
        if (key === 'beijing' && phase === 'return') dayId = 13;
        if (key === 'xunyi') dayId = phase === 'return' ? 10 : phase === 'outbound' ? 5 : 6;
        if (key === 'hohhot') dayId = phase === 'return' ? 10 : 4;
        if (key === 'xiy') dayId = phase === 'return' ? 10 : 5;
        selectDay(dayId);
      });
      markers.set(key, marker);
    });
    updateMap();
    new ResizeObserver(() => { tripMap.invalidateSize(); updateMap(selectedDay ? days[selectedDay - 1] : null); }).observe(document.getElementById('map'));
  } else { mapError.hidden = false; }

  let printSnapshot;
  window.addEventListener('beforeprint', () => {
    printSnapshot = [...cards.values()].map(card => ({ card, open: card.open, hidden: card.hidden }));
    printSnapshot.forEach(({ card }) => { card.open = true; card.hidden = false; });
  });
  window.addEventListener('afterprint', () => { if (printSnapshot) printSnapshot.forEach(({ card, open, hidden }) => { card.open = open; card.hidden = hidden; }); });
  document.getElementById('print').addEventListener('click', () => window.print());
})();
