

/**
 * Lädt alle Hintergrundbilder vor und speichert sie im Local Storage mit Rate Limiting
 * DEAKTIVIERT wegen Storage Quota und Rate Limiting Problemen
 */
export const preloadBackgrounds = async (): Promise<void> => {
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
