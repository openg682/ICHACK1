/**
 * Charity Intelligence Map — Detail Panel Module
 * =================================================
 * Renders the full detail overlay for a selected charity,
 * including score breakdown, financials, history chart,
 * and anomaly alerts.
 *
 * The panel is rendered INSIDE #detailOverlay so it appears
 * when the overlay is shown via .open class.
 */

import { formatMoney, getScoreColor, charityRegisterUrl } from './utils.js';

/**
 * Open the detail panel for a charity.
 */
export function openDetail(charity) {
  if (!charity) return;

  const overlay = document.getElementById('detailOverlay');

  // Render the panel directly inside the overlay
  overlay.innerHTML = `
    <div class="detail-panel">
      ${renderHeader(charity)}
      <div class="detail-body">
        ${renderAnomalies(charity)}
        ${renderFinancials(charity)}
        ${renderHistory(charity)}
        ${renderActivities(charity)}
        ${renderRegisterLink(charity)}
      </div>
    </div>`;

  overlay.classList.add('open');

  // Close button handler
  const closeBtn = overlay.querySelector('.detail-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      closeDetail();
    });
  }
}

/**
 * Close the detail panel.
 */
export function closeDetail() {
  const overlay = document.getElementById('detailOverlay');
  overlay.classList.remove('open');
}

// ═══════════════════════════════════════════════════════════════════════════
// RENDERERS
// ═══════════════════════════════════════════════════════════════════════════

function renderHeader(c) {
  const scoreColor = getScoreColor(c.ns);
  const circ = 2 * Math.PI * 30;
  const offset = circ * (1 - c.ns / 100);

  const factorDefs = [
    { key: 'low_reserves',     label: 'Reserves Level',     max: 30 },
    { key: 'income_declining', label: 'Income Trend',       max: 25 },
    { key: 'overspending',     label: 'Spending vs Income', max: 20 },
    { key: 'small_charity',    label: 'Organisation Size',  max: 15 },
    { key: 'late_filing',      label: 'Filing Recency',     max: 10 },
  ];

  const factorsHTML = factorDefs.map(f => {
    const val = (c.nf && c.nf[f.key]) || 0;
    const pct = (val / f.max) * 100;
    const color = val >= f.max * 0.7 ? 'var(--accent-coral)'
                : val >= f.max * 0.4 ? 'var(--accent-amber)'
                : 'var(--accent-teal)';
    return `
      <div class="score-factor-row">
        <div class="score-factor-label">${f.label}</div>
        <div class="score-factor-bar">
          <div class="score-factor-fill" style="width:${pct}%;background:${color}"></div>
        </div>
        <div class="score-factor-val">${val}/${f.max}</div>
      </div>`;
  }).join('');

  return `
    <div class="detail-header">
      <button class="detail-close">✕</button>
      <div class="detail-charity-num">
        Charity No. ${c.n} ·
        <a href="${charityRegisterUrl(c.n)}" target="_blank" rel="noopener">View on Register ↗</a>
      </div>
      <div class="detail-name">${c.nm}</div>
      <div class="detail-cats">
        ${(c.cat || []).map(x => `<span class="cat-tag">${x}</span>`).join('')}
        ${(c.ben || []).map(x => `<span class="cat-tag" style="border-color:var(--accent-purple);color:var(--accent-purple)">${x}</span>`).join('')}
      </div>
      <div class="detail-score-row">
        <div class="detail-score-big" style="color:${scoreColor}">
          <svg viewBox="0 0 72 72">
            <circle cx="36" cy="36" r="30" stroke="rgba(255,255,255,0.08)" />
            <circle cx="36" cy="36" r="30" stroke="${scoreColor}"
              stroke-dasharray="${circ}" stroke-dashoffset="${offset}" />
          </svg>
          <div class="score-num">${c.ns}</div>
          <div class="score-of">/ 100</div>
        </div>
        <div class="score-breakdown">${factorsHTML}</div>
      </div>
    </div>`;
}

function renderAnomalies(c) {
  if (!c.an || c.an.length === 0) return '';
  const icons = { high: '🔴', medium: '🟡', low: '🔵' };
  return `
    <div class="detail-section">
      <div class="detail-section-title">⚠ Anomaly Flags</div>
      <div class="anomaly-list">
        ${c.an.map(a => `
          <div class="anomaly-alert ${a.severity}">
            <span class="anomaly-icon">${icons[a.severity] || '⚪'}</span>
            <span class="anomaly-text">${a.detail}</span>
          </div>`).join('')}
      </div>
    </div>`;
}

function renderFinancials(c) {
  const trendClass = c.it > 0 ? 'trend-up' : c.it < 0 ? 'trend-down' : 'trend-neutral';
  const trendSymbol = c.it > 0 ? '↑' : c.it < 0 ? '↓' : '→';
  const trendText = c.it != null ? `${trendSymbol} ${(Math.abs(c.it) * 100).toFixed(1)}%` : 'N/A';
  const reservesInfo = c.rm != null ? `${c.rm < 3 ? '⚠️' : '✓'} ${c.rm} months` : 'Not reported';

  return `
    <div class="detail-section">
      <div class="detail-section-title">Financial Overview</div>
      <div class="finance-grid">
        <div class="finance-card">
          <div class="finance-card-label">Annual Income</div>
          <div class="finance-card-value">£${formatMoney(c.inc)}</div>
          <div class="finance-card-sub ${trendClass}">${trendText} YoY</div>
        </div>
        <div class="finance-card">
          <div class="finance-card-label">Annual Spending</div>
          <div class="finance-card-value">£${formatMoney(c.exp)}</div>
          <div class="finance-card-sub">${c.sr ? (c.sr * 100).toFixed(0) + '% of income' : ''}</div>
        </div>
        <div class="finance-card">
          <div class="finance-card-label">Reserves</div>
          <div class="finance-card-value">£${formatMoney(c.res)}</div>
          <div class="finance-card-sub">${reservesInfo}</div>
        </div>
        ${c.emp ? `<div class="finance-card"><div class="finance-card-label">Employees</div><div class="finance-card-value">${c.emp.toLocaleString()}</div></div>` : ''}
        ${c.vol ? `<div class="finance-card"><div class="finance-card-label">Volunteers</div><div class="finance-card-value">${c.vol.toLocaleString()}</div></div>` : ''}
        <div class="finance-card">
          <div class="finance-card-label">Postcode</div>
          <div class="finance-card-value" style="font-size:14px">${c.pc}</div>
          <div class="finance-card-sub">${c.dist || ''}</div>
        </div>
      </div>
    </div>`;
}

function renderHistory(c) {
  const history = (c.ar || []).slice().reverse();
  if (history.length < 2) return '';

  const maxVal = Math.max(...history.map(h => Math.max(h.i, h.e)));

  return `
    <div class="detail-section">
      <div class="detail-section-title">Financial History</div>
      <div class="chart-bars">
        ${history.map(h => {
          const iPct = maxVal > 0 ? (h.i / maxVal) * 100 : 0;
          const ePct = maxVal > 0 ? (h.e / maxVal) * 100 : 0;
          return `
            <div class="chart-bar-group">
              <div class="chart-bar-pair">
                <div class="chart-bar income" style="height:${iPct}%"></div>
                <div class="chart-bar spending" style="height:${ePct}%"></div>
              </div>
              <div class="chart-bar-label">${h.d.slice(0, 4)}</div>
            </div>`;
        }).join('')}
      </div>
      <div class="chart-legend-row">
        <div class="chart-legend-item"><div class="chart-legend-dot" style="background:var(--accent-teal)"></div> Income</div>
        <div class="chart-legend-item"><div class="chart-legend-dot" style="background:var(--accent-coral)"></div> Expenditure</div>
      </div>
    </div>`;
}

function renderActivities(c) {
  if (!c.act) return '';
  return `
    <div class="detail-section">
      <div class="detail-section-title">Activities & Purpose</div>
      <div class="detail-activities">${c.act}</div>
    </div>`;
}

function renderRegisterLink(c) {
  return `
    <div class="detail-section">
      <a class="detail-link" href="${charityRegisterUrl(c.n)}" target="_blank" rel="noopener">
        📋 View full record on Charity Commission Register
      </a>
    </div>`;
}