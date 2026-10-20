import { getBackground } from "../api";
import { logDebug } from "./logger";

// Object-URLs und laufende Anfragen der aktuellen Sitzung. Die Bilddaten selbst
// hält der Browser über die Cache-Header des Servers, nicht der Local Storage.
const urlCache = new Map<string, string>();
const pendingCache = new Map<string, Promise<string>>();

/**
 * Lädt das Vorschaubild eines Hintergrunds. Mehrfache Aufrufe für dieselbe ID
 * teilen sich eine Anfrage und denselben Object-URL.
 */
export const loadBackgroundWithCache = (token: string, backgroundId: string): Promise<string> => {
  const cachedUrl = urlCache.get(backgroundId);
  if (cachedUrl) {
    return Promise.resolve(cachedUrl);
  }

  const pending = pendingCache.get(backgroundId);
  if (pending) {
    return pending;
  }

  logDebug(`Vorschau für Hintergrundbild ${backgroundId} laden`);
  const request = getBackground(token, backgroundId, true)
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      urlCache.set(backgroundId, url);
      return url;
    })
    .finally(() => {
      pendingCache.delete(backgroundId);
    });

  pendingCache.set(backgroundId, request);
  return request;
};
