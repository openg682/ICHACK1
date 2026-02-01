/**
 * Charity Intelligence Map — Application Entry Point
 * =====================================================
 * Orchestrates all modules: map, search, sidebar, detail, filters.
 * Handles data loading from either the API server, generated file,
 * or the embedded demo data (loaded as a global var via <script> tag).
 */

import { initMap, updateMap } from './map.js';
import { geocodePostcode } from './search.js';
import { updateSidebar, updateHeaderStats } from './sidebar.js';
import { openDetail, closeDetail } from './detail.js';
import { buildFilterChips, applyFilters } from './filters.js';
import { haversine } from './utils.js';

// ── State ──
let allData = [];         // Full dataset
let currentResults = [];  // Charities in current search radius
let searchRadius = 5;     // km
let currentCenter = null; // { lat, lng, area }

// ═══════════════════════════════════════════════════════════════════════════
// DATA LOADING
// ═══════════════════════════════════════════════════════════════════════════

function loadData() {
  // Option 1: Generated full dataset (loaded via <script> as global CHARITY_DATA)
  if (typeof window.CHARITY_DATA !== 'undefined' && window.CHARITY_DATA.length > 0) {
    allData = window.CHARITY_DATA;
    console.log(`✓ Loaded ${allData.length} charities from generated data file`);
    return 'file';
  }

  // Option 2: Demo data (loaded via <script> as global DEMO_DATA)
  if (typeof window.DEMO_DATA !== 'undefined' && window.DEMO_DATA.length > 0) {
    allData = window.DEMO_DATA;
    console.log(`✓ Loaded ${allData.length} charities from demo data`);
    return 'demo';
  }

  console.warn('⚠ No data source available — check that demo_data.js loaded');
  return 'none';
}

// ═══════════════════════════════════════════════════════════════════════════
// SEARCH
// ═══════════════════════════════════════════════════════════════════════════

async function performSearch(postcode) {
  const input = document.getElementById('searchInput');
  input.value = postcode;

  // Show loading state
  document.getElementById('charityList').innerHTML = `
    <div class="empty-state">
      <div class="loading-spinner"></div>
      <div class="empty-title">Searching...</div>
      <div class="empty-desc">Looking up postcode ${postcode}</div>
    </div>`;

  const geo = await geocodePostcode(postcode);
  if (!geo) {
    showError('Postcode not found. Try a valid UK postcode like "SE1 7PB".');
    return;
  }

  currentCenter = geo;
  displayResults(geo.lat, geo.lng, geo.area);
}

function displayResults(lat, lng, areaName) {
  // Hide welcome
  document.getElementById('welcome').classList.add('hidden');
  document.getElementById('mapOverlay').style.display = '';
  document.getElementById('controlsBar').style.display = '';
  document.getElementById('dataBanner').style.display = '';

  // Find nearby charities
  currentResults = allData
    .filter(c => c.lat != null && c.lng != null)
    .map(c => ({
      ...c,
      distance: haversine(lat, lng, c.lat, c.lng),
    }))
    .filter(c => c.distance <= searchRadius)
    .sort((a, b) => b.ns - a.ns);

  const filtered = applyFilters(currentResults);

  // Update all views
  updateMap(lat, lng, searchRadius, filtered, openDetail);
  updateSidebar(filtered, areaName, openDetail);
  updateHeaderStats(filtered);
  buildFilterChips(currentResults, () => onFilterChange());
}

function onFilterChange() {
  if (!currentCenter) return;
  displayResults(currentCenter.lat, currentCenter.lng, currentCenter.area);
}

function showError(msg) {
  document.getElementById('charityList').innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">⚠️</div>
      <div class="empty-title">Search Error</div>
      <div class="empty-desc">${msg}</div>
    </div>`;
}

// ═══════════════════════════════════════════════════════════════════════════
// EVENT BINDING
// ═══════════════════════════════════════════════════════════════════════════

function bindEvents() {
  // Search input — Enter key
  document.getElementById('searchInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') performSearch(e.target.value);
  });

  // Radius slider — live label update
  const slider = document.getElementById('radiusSlider');
  const radiusLabel = document.getElementById('radiusValue');

  slider.addEventListener('input', e => {
    searchRadius = parseInt(e.target.value);
    radiusLabel.textContent = searchRadius + ' km';
  });

  // Radius slider — re-search on release
  slider.addEventListener('change', () => {
    if (currentCenter) {
      displayResults(currentCenter.lat, currentCenter.lng, currentCenter.area);
    }
  });

  // Detail overlay — click backdrop to close
  document.getElementById('detailOverlay').addEventListener('click', e => {
    if (e.target.id === 'detailOverlay') closeDetail();
  });

  // Keyboard — Escape to close detail
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeDetail();
  });

  // Welcome postcode buttons
  document.querySelectorAll('.welcome-pc').forEach(btn => {
    btn.addEventListener('click', () => performSearch(btn.textContent.trim()));
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════════════

function init() {
  initMap();
  bindEvents();

  const source = loadData();
  console.log(`Data source: ${source} (${allData.length} charities)`);

  if (allData.length === 0) {
    document.getElementById('charityList').innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⚠️</div>
        <div class="empty-title">No data loaded</div>
        <div class="empty-desc">
          Check that demo_data.js is being served correctly.
          Open the browser console for details.
        </div>
      </div>`;
  }
}

// Expose for any inline onclick usage
window.searchPostcode = performSearch;

// Boot
init();