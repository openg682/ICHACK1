export function get(obj, keys, fallback = null) {
  for (const k of keys) {
    if (obj && obj[k] !== undefined && obj[k] !== null) return obj[k];
  }
  return fallback;
}

export function scoreToColour(score) {
  if (score >= 75) return 'var(--need-critical)';
  if (score >= 50) return 'var(--need-high)';
  if (score >= 25) return 'var(--need-medium)';
  return 'var(--need-low)';
}
