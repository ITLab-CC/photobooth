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
 * Verzögert eine Funktion um die angegebene Anzahl Millisekunden
 */
const delay = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

/**
 * Lädt alle Hintergrundbilder vor und speichert sie im Local Storage mit Rate Limiting
 * DEAKTIVIERT wegen Storage Quota und Rate Limiting Problemen
 */
export const preloadBackgrounds = async (token: string): Promise<void> => {
  // Preloading deaktiviert um Speicherplatz zu sparen und Rate Limits zu vermeiden
  console.log('Background preloading ist deaktiviert');
  return;
  
  // Alter Code (deaktiviert):
  /*
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
      
      // Lade Hintergrundbilder einzeln mit Verzögerung um Rate Limiting zu vermeiden
      for (let i = 0; i < response.backgrounds.length; i++) {
        const bg = response.backgrounds[i];
        try {
          const blob = await getBackground(token, bg.background_id);
          await saveImageToLocalStorage(bg.background_id, blob);
          console.log(`Hintergrundbild ${bg.background_id} erfolgreich vorgeladen`);
          
          // Warte 1 Sekunde zwischen den Anfragen um Rate Limiting zu vermeiden
          if (i < response.backgrounds.length - 1) {
            await delay(1000);
          }
        } catch (error) {
          console.error(`Fehler beim Vorladen von Hintergrundbild ${bg.background_id}:`, error);
          
          // Bei "Too Many Requests" Fehler, warte länger
          if (error instanceof Error && error.message.includes('Too Many Requests')) {
            console.log('Rate Limit erreicht, warte 5 Sekunden...');
            await delay(5000);
          }
        }
      }
      
      console.log('Preloading der Hintergrundbilder abgeschlossen');
    }
  } catch (error) {
    console.error('Fehler beim Preloading der Hintergrundbilder:', error);
  }
  */
};
