(() => {
  'use strict';
  const data = window.travelLibrary;
  if (!data) {
    document.getElementById('trip-grid').textContent = '档案数据暂未加载，请稍后刷新。';
    return;
  }
  data.trips.sort((a, b) => ({ planned: 0, idea: 1, recorded: 2 }[a.status] - { planned: 0, idea: 1, recorded: 2 }[b.status]) || (b.startDate || b.id).localeCompare(a.startDate || a.id));
  const states = { planned: '计划中', recorded: '已有现场记录', idea: '想去' };
  const prefStates = { confirmed: '已确认', context: '当次背景', inferred: '待确认倾向', wishlist: '愿望' };
  const entryTypes = { observation: '现场观察', reflection: '复盘想法', note: '新增记录' };
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const safePath = value => {
    if (typeof value !== 'string' || /^[a-z][a-z0-9+.-]*:/i.test(value) || value.startsWith('/') || value.includes('\\')) return null;
    let decoded;
    try { decoded = decodeURIComponent(value); } catch { return null; }
    if (decoded.startsWith('/') || decoded.includes('\\') || decoded.split(/[/?#]/).includes('..') || /[\x00-\x1f]/.test(decoded)) return null;
    return value;
  };
  const link = (path, label) => safePath(path) ? `<a href="${esc(path)}">${esc(label)}</a>` : `<span>${esc(label)}</span>`;
  const source = src => `<p class="source">来源：${src?.path ? link(src.path, src.label) : esc(src?.label || '待补')}</p>`;
  let filter = 'all';
  let query = '';
  const searchable = trip => [trip.title, trip.summary, ...trip.tags, ...trip.route, ...(trip.journal || []).flatMap(e => [e.title, e.text])].join(' ').toLocaleLowerCase();
  const matches = trip => (filter === 'all' || trip.status === filter) && (!query || searchable(trip).includes(query));
  function render() {
    const trips = data.trips.filter(matches);
    document.getElementById('result-count').textContent = `${trips.length} / ${data.trips.length} 份档案`;
    document.getElementById('trip-empty').hidden = trips.length > 0;
    document.getElementById('trip-grid').innerHTML = trips.map(trip => {
      const primary = trip.links.find(l => l.kind === (trip.status === 'recorded' ? 'review' : 'plan')) || trip.links[0];
      return `<article class="trip-card" data-status="${esc(trip.status)}"><div class="trip-banner"><small>JOURNEY ${String(data.trips.indexOf(trip) + 1).padStart(2, '0')}</small><span class="badge">${esc(states[trip.status])}</span></div><div class="trip-body"><h3>${esc(trip.title)}</h3><p class="trip-date">${esc(trip.dateLabel)}</p><p class="trip-description">${esc(trip.summary)}</p><div class="tags">${trip.tags.map(t => `<span class="tag">${esc(t)}</span>`).join('')}</div><p class="route">${trip.route.map(esc).join(' → ')}</p><div class="trip-actions">${primary ? link(primary.path, primary.label + ' ↗') : ''}<span>${trip.journal.length ? trip.journal.length + ' 条记录' : '尚未填写现场日记'}</span></div><details class="trip-details"><summary>查看档案说明与所有版本</summary><p>${esc(trip.dateNote)}</p><ul>${trip.highlights.map(h => `<li>${esc(h)}</li>`).join('')}</ul><ul>${trip.links.map(l => `<li>${link(l.path, l.label)}</li>`).join('')}</ul></details></div></article>`;
    }).join('');
    const entries = trips.flatMap(t => t.journal.map(e => ({ ...e, tripTitle: t.title }))).filter(e => !query || [e.title, e.text, e.tripTitle].join(' ').toLocaleLowerCase().includes(query)).sort((a, b) => (b.date || '').localeCompare(a.date || ''));
    document.getElementById('memory-empty').hidden = entries.length > 0;
    document.getElementById('memory-list').innerHTML = entries.map(e => `<article class="memory"><p class="memory-meta">${esc(e.tripTitle)} · ${esc(entryTypes[e.type])}${e.date ? ' · ' + esc(e.date) : ''}</p><h3>${esc(e.title)}</h3><p>${esc(e.text)}</p>${source(e.source)}</article>`).join('');
  }
  document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
    filter = button.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    render();
  }));
  document.getElementById('trip-search').addEventListener('input', event => { query = event.target.value.trim().toLocaleLowerCase(); render(); });
  const prefCard = p => `<article class="preference-card"><span class="category">${esc(p.category)} · ${esc(prefStates[p.status])}</span><h3>${esc(p.label)}</h3><p>${esc(p.detail)}</p>${source(p.source)}</article>`;
  document.getElementById('preference-grid').innerHTML = data.preferences.items.filter(p => p.status === 'confirmed').map(prefCard).join('');
  document.getElementById('context-grid').innerHTML = data.preferences.items.filter(p => ['context', 'inferred'].includes(p.status)).map(prefCard).join('');
  document.getElementById('wish-grid').innerHTML = data.preferences.items.filter(p => p.status === 'wishlist').map(p => `<article class="wish"><h3>${esc(p.label)}</h3><p>${esc(p.detail)}</p>${source(p.source)}</article>`).join('');
  const nextTrip = data.trips.find(t => t.status === 'planned') || data.trips[0];
  const nextLink = nextTrip?.links.find(l => l.kind === 'plan') || nextTrip?.links[0];
  const continueLink = document.getElementById('continue-trip');
  if (nextLink && safePath(nextLink.path)) {
    continueLink.href = nextLink.path;
    continueLink.textContent = `${nextTrip.status === 'planned' ? '继续规划' : '查看档案'} · ${nextTrip.title} ↗`;
  } else { continueLink.hidden = true; }
  document.getElementById('trip-count').textContent = data.trips.length;
  document.getElementById('updated-at').textContent = `资料更新于 ${data.updatedAt}`;
  render();
})();
