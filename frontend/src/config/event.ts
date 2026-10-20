import { getEventConfig, getEventLogo } from "../api";
import { logDebug } from "../utils/logger";

// Build-time fallbacks (env vars). Used until the backend settings doc loads,
// and as the final fallback if the backend has no settings doc yet either.
export const EVENT_TITLE = import.meta.env.VITE_EVENT_TITLE ?? "IT-Lab 2026";
export const EVENT_SUBTITLE = import.meta.env.VITE_EVENT_SUBTITLE ?? "ENTEGA • Darmstadt";
export const BRAND_NAME = import.meta.env.VITE_BRAND_NAME ?? "ENTEGA";
export const START_TEXT = "Erschaffe eine Erinnerung";
export const MAX_PRINTS = 3;
export const SERIES_COUNT = 3;
export const PIN_FAIL_REDIRECT_URL =
  import.meta.env.VITE_PIN_FAIL_REDIRECT_URL ??
  "https://www.entega.ag/karriere/ausbildung-duales-studium-berufsorientierung/ausbildung/";

// Runtime-editable copy: starts out equal to the build-time defaults above,
// overwritten in place once the kiosk fetches the admin-configured settings.
// A mutated module object (rather than React state/Context) fits this app's
// existing convention of plain exported config values, and is fine here since
// the kiosk only reads these after its multi-second start-screen animation.
export const runtimeConfig = {
  title: EVENT_TITLE,
  subtitle: EVENT_SUBTITLE,
  brandName: BRAND_NAME,
  pinFailRedirectUrl: PIN_FAIL_REDIRECT_URL,
  startText: START_TEXT,
  maxPrints: MAX_PRINTS, // copies of one photo a guest may print
  seriesCount: SERIES_COUNT, // photos taken in a row before the guests pick one (1 = single photo)
  soundEnabled: true, // countdown ticks and shutter sound
  // Object URL of the logo uploaded in the admin dashboard; null = use the built-in logo.
  logoUrl: null as string | null,
};

let initialized = false;

// Call once (e.g. on kiosk boot, once a session token is available) to load
// admin-configured settings from the backend. Safe to call multiple times;
// only the first call performs a fetch.
export async function initEventConfig(token: string): Promise<void> {
  if (initialized) return;
  initialized = true;
  try {
    const config = await getEventConfig(token);
    runtimeConfig.title = config.title;
    runtimeConfig.subtitle = config.subtitle;
    runtimeConfig.brandName = config.brand_name;
    runtimeConfig.pinFailRedirectUrl = config.pin_fail_redirect_url;
    runtimeConfig.startText = config.start_text;
    runtimeConfig.maxPrints = config.max_prints;
    runtimeConfig.seriesCount = config.series_count;
    runtimeConfig.soundEnabled = config.sound_enabled;
    if (config.has_logo) {
      runtimeConfig.logoUrl = URL.createObjectURL(await getEventLogo(token));
    }
  } catch (err) {
    logDebug("Konnte Event-Settings nicht laden, nutze Standardwerte:", err);
  }
}
