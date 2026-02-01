/**
 * Charity Intelligence Map — Sidebar Module
 * ============================================
 * Renders the ranked charity list, borough summary,
 * and header statistics.
 */

import { formatCompact, getScoreColor, getScoreClass } from './utils.js';

/**
 * Update the sidebar charity list.
 *
 * @param {Array} charities - Charities to display (already filtered & sorted)
 * @param {string} areaName - Name of the searched area
 * @param {Function} onCardClick - Callback when a charity card is clicked
 */
export function updateSidebar(charities, areaName, onCardClick) {
  const sub = document.getElementById('sidebarSub');
  sub.innerHTML = `<strong>${charities.length}</strong> charities near ${areaName} · sorted by need`;

  const list = document.getElementById('charityList');

  if (charities.length === 0) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📍</div>
        <div class="empty-title">No charities found</div>
        <div class="empty-desc">
          Try increasing the search radius or a different postcode.
          The demo covers London, Manchester, Bristol, Birmingham, Leeds, and Sheffield.
        </div>
      </div>`;
    return;
  }

  let html = renderBoroughSummary(charities);

  charities.forEach((c, i) => {
    html += renderCharityCard(c, i, onCardClick);
  });

  list.innerHTML = html;

  // Attach click handlers via delegation
  list.querySelectorAll('.charity-card').forEach(card => {
    card.addEventListener('click', () => {
      const id = card.dataset.id;
      const charity = charities.find(c => c.n === id);
      if (charity) onCardClick(charity);
    });
  });
}

/**
 * Update the three header stat counters.
 */
export function updateHeaderStats(charities) {
  document.getElementById('statTotal').textContent = charities.length;
  document.getElementById('statHighNeed').textContent =
    charities.filter(c => c.ns >= 50).length;

  if (charities.length > 0) {
    const sorted = [...charities].sort((a, b) => a.ns - b.ns);
    document.getElementById('statMedian').textContent =
      sorted[Math.floor(sorted.length / 2)].ns;
  }
}

// ── Internal helpers ───────────────────────────────────────────────────────

function renderBoroughSummary(charities) {
  const districts = {};
  charities.forEach(c => {
    const d = c.dist || 'Unknown';
    if (!districts[d]) districts[d] = { count: 0, totalNeed: 0, totalInc: 0 };
    districts[d].count++;
    districts[d].totalNeed += c.ns;
    districts[d].totalInc += c.inc;
  });

  const top = Object.entries(districts).sort((a, b) => b[1].count - a[1].count)[0];
  if (!top) return '';

  const d = top[1];
  const avgNeed = Math.round(d.totalNeed / d.count);
  const highNeed = charities.filter(c => c.dist === top[0] && c.ns >= 50).length;

  return `
    <div class="borough-summary">
      <div class="borough-name">${top[0]}</div>
      <div class="borough-stats">
        <div class="borough-stat">
          <div class="borough-stat-val" style="color:var(--accent-teal)">${d.count}</div>
          <div class="borough-stat-label">Charities</div>
        </div>
        <div class="borough-stat">
          <div class="borough-stat-val" style="color:${getScoreColor(avgNeed)}">${avgNeed}</div>
          <div class="borough-stat-label">Avg Score</div>
        </div>
        <div class="borough-stat">
          <div class="borough-stat-val" style="color:var(--accent-coral)">${highNeed}</div>
          <div class="borough-stat-label">High Need</div>
        </div>
        <div class="borough-stat">
          <div class="borough-stat-val" style="color:var(--accent-amber)">£${formatCompact(d.totalInc)}</div>
          <div class="borough-stat-label">Total Income</div>
        </div>
      </div>
    </div>`;
}

function renderCharityCard(c, index) {
  const scoreClass = getScoreClass(c.ns);
  const scoreColor = getScoreColor(c.ns);
  const circ = 2 * Math.PI * 18;
  const offset = circ * (1 - c.ns / 100);

  const factors = buildFactorBadges(c.nf);

  return `
    <div class="charity-card ${scoreClass}" data-id="${c.n}">
      <div class="card-top">
        <div style="flex:1">
          <span class="card-rank">#${index + 1}</span>
          <span class="card-name">${c.nm}${c.an && c.an.length ? '<span class="anomaly-dot" title="Anomaly detected"></span>' : ''}</span>
        </div>
        <div class="card-score">
          <div class="score-circle">
            <svg viewBox="0 0 44 44">
              <circle cx="22" cy="22" r="18" stroke="rgba(255,255,255,0.08)" />
              <circle cx="22" cy="22" r="18" stroke="${scoreColor}"
                stroke-dasharray="${circ}" stroke-dashoffset="${offset}" />
            </svg>
            ${c.ns}
          </div>
          <div class="score-label">Need</div>
        </div>
      </div>
      <div class="card-meta">
        <div class="meta-item"><span class="mi">💷</span> £${formatCompact(c.inc)}</div>
        <div class="meta-item"><span class="mi">📍</span> ${c.distance !== undefined ? c.distance.toFixed(1) + 'km' : c.pc}</div>
        ${c.emp ? `<div class="meta-item"><span class="mi">👤</span> ${c.emp}</div>` : ''}
        ${c.vol ? `<div class="meta-item"><span class="mi">🤝</span> ${c.vol} vol</div>` : ''}
      </div>
      ${c.cat && c.cat.length ? `<div class="card-cats">${c.cat.map(cat =>
        `<span class="cat-tag">${cat.length > 25 ? cat.slice(0, 22) + '…' : cat}</span>`
      ).join('')}</div>` : ''}
      ${factors.length ? `<div class="card-factors">${factors.join('')}</div>` : ''}
    </div>`;
}

function buildFactorBadges(nf) {
  if (!nf) return [];
  const badges = [];
  if (nf.low_reserves >= 20) badges.push('<span class="factor-badge high">⚑ Low reserves</span>');
  else if (nf.low_reserves >= 10) badges.push('<span class="factor-badge medium">⚑ Moderate reserves</span>');
  if (nf.income_declining >= 15) badges.push('<span class="factor-badge high">⚑ Income declining</span>');
  else if (nf.income_declining >= 5) badges.push('<span class="factor-badge medium">⚑ Income dip</span>');
  if (nf.overspending >= 10) badges.push('<span class="factor-badge high">⚑ Overspending</span>');
  if (nf.small_charity >= 10) badges.push('<span class="factor-badge low">⚑ Small org</span>');
  if (nf.late_filing >= 5) badges.push('<span class="factor-badge medium">⚑ Late filing</span>');
  return badges;
}