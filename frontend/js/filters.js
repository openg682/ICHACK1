/**
 * Charity Intelligence Map — Filters Module
 * ============================================
 * Manages category filter chips and applies them
 * to the current result set.
 */

let activeFilters = new Set();

/**
 * Build filter chips from the current charity set.
 *
 * @param {Array} charities - All charities in the current search radius
 * @param {Function} onToggle - Callback(categoryName) when a chip is toggled
 */
export function buildFilterChips(charities, onToggle) {
  const cats = {};
  charities.forEach(c =>
    (c.cat || []).forEach(cat => {
      cats[cat] = (cats[cat] || 0) + 1;
    })
  );

  const sorted = Object.entries(cats)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);

  const container = document.getElementById('filterChips');
  container.innerHTML = sorted
    .map(
      ([cat, count]) =>
        `<div class="filter-chip ${activeFilters.has(cat) ? 'active' : ''}"
              data-cat="${cat}">${cat.length > 20 ? cat.slice(0, 17) + '…' : cat} (${count})</div>`
    )
    .join('');

  // Attach click handlers
  container.querySelectorAll('.filter-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const cat = chip.dataset.cat;
      toggleFilter(cat);
      onToggle(cat);
    });
  });
}

/**
 * Toggle a category filter on/off.
 */
export function toggleFilter(cat) {
  if (activeFilters.has(cat)) activeFilters.delete(cat);
  else activeFilters.add(cat);
}

/**
 * Apply active filters to a list of charities.
 *
 * @param {Array} charities - Unfiltered charities
 * @returns {Array} Filtered charities (or all if no filters active)
 */
export function applyFilters(charities) {
  if (activeFilters.size === 0) return charities;
  return charities.filter(c =>
    c.cat && c.cat.some(cat => activeFilters.has(cat))
  );
}

/**
 * Get the current set of active filter categories.
 */
export function getActiveFilters() {
  return activeFilters;
}