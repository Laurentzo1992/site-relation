const FALLBACK_COUNTRY = "CI";

/**
 * Detects the visitor's country from their IP address, to preselect a
 * sensible default country/dial code in the phone number input. Best
 * effort only: falls back silently if the geolocation service is
 * unreachable (network issue, ad-blocker, offline dev environment...).
 */
export async function detectCountryFromIp() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    const res = await fetch("https://ipapi.co/country/", { signal: controller.signal });
    clearTimeout(timeout);
    if (!res.ok) return FALLBACK_COUNTRY;
    const code = (await res.text()).trim().toUpperCase();
    return /^[A-Z]{2}$/.test(code) ? code : FALLBACK_COUNTRY;
  } catch {
    return FALLBACK_COUNTRY;
  }
}
