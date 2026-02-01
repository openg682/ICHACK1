export async function geocodePostcode(postcode) {
  const res = await fetch(`https://api.postcodes.io/postcodes/${encodeURIComponent(postcode)}`);
  const data = await res.json();
  if (!data.result) throw new Error('Invalid postcode');

  return {
    lat: data.result.latitude,
    lng: data.result.longitude,
    area: data.result.admin_district || postcode.toUpperCase()
  };
}
