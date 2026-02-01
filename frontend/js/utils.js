/**
 * Charity Intelligence Map — Utilities
 * =====================================
 * Shared formatting, colour, and distance functions
 * used across all frontend modules.
 */

export function formatMoney(val) {
  if (val == null) return '—';
  if (val >= 1e9) return (val / 1e9).toFixed(1) + 'bn';
  if (val >= 1e6) return (val / 1e6).toFixed(1) + 'm';
  if (val >= 1e3) return (val / 1e3).toFixed(0) + 'k';
  return val.toLocaleString();
}

export function formatCompact(val) {
  if (val == null) return '—';
  if (val >= 1e9) return (val / 1e9).toFixed(1) + 'bn';
  if (val >= 1e6) return (val / 1e6).toFixed(1) + 'm';
  if (val >= 1e3) return (val / 1e3).toFixed(0) + 'k';
  return val.toString();
}

export function getScoreColor(score) {
  if (score >= 75) return '#dc2626';
  if (score >= 50) return '#f43f5e';
  if (score >= 25) return '#f59e0b';
  return '#2dd4bf';
}

export function getScoreClass(score) {
  if (score >= 75) return 'need-critical';
  if (score >= 50) return 'need-high';
  if (score >= 25) return 'need-medium';
  return 'need-low';
}

export function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Get the CC register URL for a charity.
 */
export function charityRegisterUrl(charityNumber) {
  return `https://register-of-charities.charitycommission.gov.uk/charity-search/-/charity-details/${charityNumber}`;
}