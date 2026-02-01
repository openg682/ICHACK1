let activeCategory = null;

export function renderFilters(charities, onChange) {
  const container = document.getElementById('filterChips');
  container.innerHTML = '';

  const categories = [...new Set(charities.map(c => c.category).filter(Boolean))];

  categories.forEach(cat => {
    const chip = document.createElement('div');
    chip.className = 'filter-chip';
    chip.textContent = cat;
    chip.onclick = () => {
      activeCategory = activeCategory === cat ? null : cat;
      onChange();
    };
    container.appendChild(chip);
  });
}

export function applyFilters(charities) {
  if (!activeCategory) return charities;
  return charities.filter(c => c.category === activeCategory);
}
