import { getBackground, listBackgrounds } from "../api";

// Local Storage Keys
const LS_PREFIX = 'photobooth_bg_';
const LS_TIMESTAMP_PREFIX = 'photobooth_bg_timestamp_';
const LS_PRELOAD_TIMESTAMP = 'photobooth_bg_preload_timestamp';
const PRELOAD_INTERVAL_MS = 24 * 60 * 60 * 1000; // 24 Stunden

/**
 * Konvertiert einen Blob in einen Base64-String
 */
const blobToBase64 = (blob: Blob): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
};

/**
 * Speichert ein Bild im Local Storage
 */
const saveImageToLocalStorage = async (id: string, blob: Blob) => {
  try {
    const base64 = await blobToBase64(blob);
    localStorage.setItem(LS_PREFIX + id, base64);
    localStorage.setItem(LS_TIMESTAMP_PREFIX + id, Date.now().toString());
  } catch (error) {
    console.error('Fehler beim Speichern im Local Storage:', error);
  }
};

/**
 * Prüft, ob der Preload in letzter Zeit durchgeführt wurde
 */
const shouldPreload = (): boolean => {
  const lastPreload = localStorage.getItem(LS_PRELOAD_TIMESTAMP);
  if (!lastPreload) return true;
  
  const lastPreloadTime = parseInt(lastPreload);
  return Date.now() - lastPreloadTime > PRELOAD_INTERVAL_MS;
};

/**
 * Lädt alle Hintergrundbilder vor und speichert sie im Local Storage
 */
export const preloadBackgrounds = async (token: string): Promise<void> => {
  // Nur einmal alle 24 Stunden preloaden
  if (!shouldPreload()) {
    console.log('Hintergrundbilder wurden bereits kürzlich vorgeladen');
    return;
  }
  
  try {
    console.log('Starte Preloading der Hintergrundbilder...');
    const response = await listBackgrounds(token);
    
    if (response.backgrounds && response.backgrounds.length > 0) {
      // Setze den Preload-Zeitstempel, auch wenn nicht alle Bilder erfolgreich geladen werden
      localStorage.setItem(LS_PRELOAD_TIMESTAMP, Date.now().toString());
      
      // Lade alle Hintergrundbilder parallel
      const loadPromises = response.backgrounds.map(async (bg) => {
        try {
          const blob = await getBackground(token, bg.background_id);
          await saveImageToLocalStorage(bg.background_id, blob);
          console.log(`Hintergrundbild ${bg.background_id} erfolgreich vorgeladen`);
        } catch (error) {
          console.error(`Fehler beim Vorladen von Hintergrundbild ${bg.background_id}:`, error);
        }
      });
      
      await Promise.all(loadPromises);
      console.log('Preloading der Hintergrundbilder abgeschlossen');
    }
  } catch (error) {
    console.error('Fehler beim Preloading der Hintergrundbilder:', error);
  }
};
