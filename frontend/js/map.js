/**
 * Charity Intelligence Map — Map Module
 * =======================================
 * Handles Leaflet map initialisation, marker rendering,
 * search circle overlay, and map interactions.
 */

import { getScoreColor } from './utils.js';

let map, markerGroup, searchCircle;

export function initMap() {
  map = L.map('map', {
    center: [52.5, -1.5],
    zoom: 6,
    zoomControl: false,
    attributionControl: true,
  });

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    maxZoom: 19,
  }).addTo(map);

  L.control.zoom({ position: 'topright' }).addTo(map);

  markerGroup = L.layerGroup().addTo(map);
  return map;
}

export function getMap() { return map; }

/**
 * Update map markers for a set of charities around a center point.
 */
export function updateMap(lat, lng, radiusKm, charities, onMarkerClick) {
  markerGroup.clearLayers();
  if (searchCircle) map.removeLayer(searchCircle);

  // Search radius circle
  searchCircle = L.circle([lat, lng], {
    radius: radiusKm * 1000,
    color: '#2dd4bf',
    fillColor: '#2dd4bf',
    fillOpacity: 0.05,
    weight: 1,
    dashArray: '6,4',
  }).addTo(map);

  // Search center pin
  L.circleMarker([lat, lng], {
    radius: 8,
    color: '#fff',
    fillColor: '#2dd4bf',
    fillOpacity: 1,
    weight: 2,
  }).addTo(markerGroup);

  // Charity markers
  charities.forEach((c) => {
    const size = Math.max(8, Math.min(16, 8 + (c.ns / 100) * 8));
    const color = getScoreColor(c.ns);

    const marker = L.circleMarker([c.lat, c.lng], {
      radius: size,
      color: color,
      fillColor: color,
      fillOpacity: 0.7,
      weight: 1.5,
    });

    marker.bindPopup(`
      <div style="font-family:'Outfit',sans-serif">
        <div style="font-weight:600;font-size:13px">${c.nm}</div>
        <div style="font-family:monospace;font-size:12px;color:${color}">Need Score: ${c.ns}/100</div>
        <div style="font-size:11px;color:#666;margin-top:4px">${(c.cat || []).join(', ')}</div>
      </div>
    `);

    marker.on('click', () => onMarkerClick(c));
    marker.addTo(markerGroup);
  });

  // Fit bounds
  if (charities.length > 0) {
    const bounds = L.latLngBounds(charities.map(c => [c.lat, c.lng]));
    bounds.extend([lat, lng]);
    map.fitBounds(bounds, { padding: [60, 60], maxZoom: 14 });
  } else {
    map.setView([lat, lng], 13);
  }
}