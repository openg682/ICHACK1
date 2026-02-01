/**
 * Charity Intelligence Map — Application Entry Point
 * =====================================================
 * Orchestrates all modules: map, search, sidebar, detail, filters.
 * Handles data loading from either the API server or embedded demo data.
 */

import { initMap, updateMap, getMap } from './map.js';
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

// ── Data Loading ──

async function loadData() {
  // Option 1: Try loading from API (if backend is running)
  try {
    const resp = await fetch('/api/health');
    if (resp.ok) {
      console.log('✓ Connected to API server');
      // Data will be fetched per-search via /api/search
      return 'api';
    }
  } catch (_) {}

  // Option 2: Try loading the generated data file
  if (typeof CHARITY_DATA !== 'undefined' && CHARITY_DATA.length > 0) {
    allData = CHARITY_DATA;
    console.log(`✓ Loaded ${allData.length} charities from generated data file`);
    return 'file';
  }

  // Option 3: Load embedded demo data
  try {
    const module = await import('./demo_data.js');
    allData = module.DEMO_DATA;
    console.log(`✓ Loaded ${allData.length} charities from demo data`);
    return 'demo';
  } catch (_) {}

  console.warn('⚠ No data source available');
  return 'none';
}

// ── Search ──

async function performSearch(postcode) {
  const input = document.getElementById('searchInput');
  input.value = postcode;

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

// ── Event Binding ──

function bindEvents() {
  // Search input
  document.getElementById('searchInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') performSearch(e.target.value);
  });

  // Radius slider
  const slider = document.getElementById('radiusSlider');
  const radiusLabel = document.getElementById('radiusValue');

  slider.addEventListener('input', e => {
    searchRadius = parseInt(e.target.value);
    radiusLabel.textContent = searchRadius + ' km';
  });

  slider.addEventListener('change', () => {
    if (currentCenter) {
      displayResults(currentCenter.lat, currentCenter.lng, currentCenter.area);
    }
  });

  // Detail overlay close
  document.getElementById('detailOverlay').addEventListener('click', e => {
    if (e.target === document.getElementById('detailOverlay')) closeDetail();
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeDetail();
  });

  // Welcome postcode buttons
  document.querySelectorAll('.welcome-pc').forEach(btn => {
    btn.addEventListener('click', () => performSearch(btn.textContent.trim()));
  });
}

// ── Init ──

async function init() {
  initMap();
  bindEvents();

  const source = await loadData();
  console.log(`Data source: ${source}`);
}

// Expose for welcome buttons (onclick in HTML)
window.searchPostcode = performSearch;

// Boot
init();