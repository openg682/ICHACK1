/**
 * Charity Intelligence Map — Search Module
 * ==========================================
 * Handles postcode geocoding via postcodes.io
 * and coordinates the search → display pipeline.
 */

/**
 * Look up a UK postcode and return coordinates + area name.
 *
 * @param {string} postcode - UK postcode string
 * @returns {Promise<{lat: number, lng: number, area: string}|null>}
 */
export async function geocodePostcode(postcode) {
  const pc = postcode.trim().toUpperCase();
  if (!pc) return null;

  try {
    // Try full postcode first
    const resp = await fetch(
      `https://api.postcodes.io/postcodes/${encodeURIComponent(pc)}`
    );
    const data = await resp.json();

    if (data.status === 200 && data.result) {
      return {
        lat: data.result.latitude,
        lng: data.result.longitude,
        area: data.result.admin_district || pc,
      };
    }

    // Fallback: try as an outward code (e.g. "SE1")
    const outward = pc.split(' ')[0];
    const resp2 = await fetch(
      `https://api.postcodes.io/outcodes/${encodeURIComponent(outward)}`
    );
    const data2 = await resp2.json();

    if (data2.status === 200 && data2.result) {
      return {
        lat: data2.result.latitude,
        lng: data2.result.longitude,
        area: data2.result.admin_district?.[0] || outward,
      };
    }

    return null;
  } catch (err) {
    console.error('Geocoding error:', err);
    return null;
  }
}