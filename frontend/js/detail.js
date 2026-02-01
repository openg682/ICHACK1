import { get } from './utils.js';

export function showDetail(charity) {
  const overlay = document.getElementById('detailOverlay');
  const panel = document.getElementById('detailPanel');

  const breakdown = get(charity, ['score_breakdown', 'breakdown'], {});

  overlay.style.display = 'block';
  panel.style.display = 'block';

  panel.innerHTML = `
    <div class="detail-panel">
      <h2>${charity.name}</h2>
      <p><strong>Need score:</strong> ${get(charity, ['need_score', 'ns'], 0)}</p>

      <h3>Why this charity?</h3>
      <ul>
        <li>Reserves cover ~${breakdown.reserves_months ?? '—'} months</li>
        <li>Income change: ${breakdown.income_change_pct ?? '—'}%</li>
        <li>Spend ratio: ${breakdown.spend_ratio_raw ?? '—'}</li>
      </ul>
    </div>
  `;

  overlay.onclick = hideDetail;
}

export function hideDetail() {
  document.getElementById('detailOverlay').style.display = 'none';
  document.getElementById('detailPanel').style.display = 'none';
}
