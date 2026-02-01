import { get, scoreToColour } from './utils.js';

let map;
let markers = [];
let circle;

export function initMap() {
  map = L.map('map').setView([51.5074, -0.1278], 12);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
}

export function renderMap(center, radiusKm, charities, onSelect) {
  map.setView([center.lat, center.lng], 13);

  if (circle) map.removeLayer(circle);
  circle = L.circle([center.lat, center.lng], {
    radius: radiusKm * 1000,
    color: '#666',
    fillOpacity: 0.05
  }).addTo(map);

  markers.forEach(m => map.removeLayer(m));
  markers = [];

  charities.forEach(c => {
    const lat = get(c, ['lat', 'latitude']);
    const lng = get(c, ['lng', 'longitude']);
    const score = get(c, ['need_score', 'ns'], 0);

    if (lat == null || lng == null) return;

    const marker = L.circleMarker([lat, lng], {
      radius: 8,
      fillColor: scoreToColour(score),
      fillOpacity: 0.85,
      color: '#222',
      weight: 1
    })
      .addTo(map)
      .on('click', () => onSelect(c));

    marker.bindTooltip(
      `<strong>${c.name}</strong><br>Need score: ${score}`,
      { direction: 'top' }
    );

    markers.push(marker);
  });
}
