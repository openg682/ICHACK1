import { get } from './utils.js';

export function renderSidebar(charities, areaName, onSelect) {
  const list = document.getElementById('charityList');
  const subtitle = document.getElementById('sidebarSub');

  subtitle.textContent = `${charities.length} charities near ${areaName}`;
  list.innerHTML = '';

  if (!charities.length) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📭</div>
        <div class="empty-title">No charities found</div>
        <div class="empty-desc">Try increasing the radius.</div>
      </div>`;
    return;
  }

  charities.forEach(c => {
    const score = get(c, ['need_score', 'ns'], 0);
    const distance = get(c, ['distance', 'distance_km'], 0);

    const item = document.createElement('div');
    item.className = 'charity-item';
    item.innerHTML = `
      <div class="charity-name">${c.name}</div>
      <div class="charity-meta">
        <span>${c.category || 'Other'}</span>
        <span>${distance.toFixed(1)} km</span>
        <span class="score">${score}</span>
      </div>
    `;
    item.onclick = () => onSelect(c);
    list.appendChild(item);
  });

  updateStats(charities);
}

function updateStats(charities) {
  document.getElementById('statTotal').textContent = charities.length;
  document.getElementById('statHighNeed').textContent =
    charities.filter(c => get(c, ['need_score', 'ns'], 0) >= 50).length;

  const scores = charities.map(c => get(c, ['need_score', 'ns'], 0)).sort((a, b) => a - b);
  document.getElementById('statMedian').textContent =
    scores.length ? scores[Math.floor(scores.length / 2)] : '—';
}
