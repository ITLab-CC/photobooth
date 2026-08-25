import { getBackground } from "../api";
import { logDebug } from "./logger";

// Cache Konfiguration
const CACHE_PREFIX = 'photobooth_bg_cache_';
const METADATA_PREFIX = 'photobooth_bg_meta_';
const MAX_CACHE_SIZE = 3; // Nur 3 Hintergrundbilder speichern
const MAX_CACHE_AGE_MS = 60 * 60 * 1000; // 1 Stunde gültig

interface CacheMetadata {
  lastUsed: number;
  cachedAt: number;
  size: number;
}

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
 * Konvertiert einen Base64-String zurück in einen Blob
 */
const base64ToBlob = (base64: string): Blob => {
  const parts = base64.split(';base64,');
  const contentType = parts[0].split(':')[1];
  const raw = window.atob(parts[1]);
  const rawLength = raw.length;
  const uInt8Array = new Uint8Array(rawLength);
  
  for (let i = 0; i < rawLength; ++i) {
    uInt8Array[i] = raw.charCodeAt(i);
  }
  
  return new Blob([uInt8Array], { type: contentType });
};

/**
 * Holt alle Cache-Metadaten
 */
const getAllCacheMetadata = (): Record<string, CacheMetadata> => {
  const metadata: Record<string, CacheMetadata> = {};
  
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && key.startsWith(METADATA_PREFIX)) {
      try {
        const data = JSON.parse(localStorage.getItem(key) || '{}');
        const backgroundId = key.replace(METADATA_PREFIX, '');
        metadata[backgroundId] = data;
      } catch (error) {
        // Ignoriere fehlerhafte Metadaten
        localStorage.removeItem(key);
      }
    }
  }
  
  return metadata;
};

/**
 * Löscht die ältesten Cache-Einträge um Platz zu schaffen
 */
const cleanupOldCache = (): void => {
  const metadata = getAllCacheMetadata();
  const entries = Object.entries(metadata);
  
  if (entries.length <= MAX_CACHE_SIZE) return;
  
  // Sortiere nach letzter Verwendung (älteste zuerst)
  entries.sort(([, a], [, b]) => a.lastUsed - b.lastUsed);
  
  // Lösche die ältesten Einträge
  const toDelete = entries.slice(0, entries.length - MAX_CACHE_SIZE);
  toDelete.forEach(([backgroundId]) => {
    localStorage.removeItem(CACHE_PREFIX + backgroundId);
    localStorage.removeItem(METADATA_PREFIX + backgroundId);
  });
  
  logDebug(`Cache aufgeräumt: ${toDelete.length} alte Einträge gelöscht`);
};

/**
 * Speichert ein Bild im intelligenten Cache
 */
const saveToCache = async (backgroundId: string, blob: Blob): Promise<void> => {
  try {
    // Bereinige zuerst den Cache
    cleanupOldCache();
    
    const base64 = await blobToBase64(blob);
    const metadata: CacheMetadata = {
      lastUsed: Date.now(),
      cachedAt: Date.now(),
      size: base64.length
    };
    
    localStorage.setItem(CACHE_PREFIX + backgroundId, base64);
    localStorage.setItem(METADATA_PREFIX + backgroundId, JSON.stringify(metadata));
    
    logDebug(`Hintergrundbild ${backgroundId} im Cache gespeichert`);
  } catch (error) {
    if (error instanceof Error && error.name === 'QuotaExceededError') {
      console.warn('Cache voll, führe erzwungenes Cleanup durch');
      // Erzwungenes Cleanup: Lösche alles außer dem aktuellsten
      const metadata = getAllCacheMetadata();
      const entries = Object.entries(metadata);
      entries.sort(([, a], [, b]) => a.lastUsed - b.lastUsed);
      
      // Lösche alle außer dem neuesten
      entries.slice(0, -1).forEach(([backgroundId]) => {
        localStorage.removeItem(CACHE_PREFIX + backgroundId);
        localStorage.removeItem(METADATA_PREFIX + backgroundId);
      });
      
      // Versuche es erneut
      try {
        const base64 = await blobToBase64(blob);
        const newMetadata: CacheMetadata = {
          lastUsed: Date.now(),
          cachedAt: Date.now(),
          size: base64.length
        };
        
        localStorage.setItem(CACHE_PREFIX + backgroundId, base64);
        localStorage.setItem(METADATA_PREFIX + backgroundId, JSON.stringify(newMetadata));
      } catch (retryError) {
        console.error('Cache auch nach Cleanup voll:', retryError);
      }
    } else {
      console.error('Fehler beim Speichern im Cache:', error);
    }
  }
};

/**
 * Lädt ein Bild aus dem intelligenten Cache
 */
const loadFromCache = (backgroundId: string): { blob: Blob | null; isValid: boolean } => {
  try {
    const base64 = localStorage.getItem(CACHE_PREFIX + backgroundId);
    const metadataStr = localStorage.getItem(METADATA_PREFIX + backgroundId);
    
    if (!base64 || !metadataStr) {
      return { blob: null, isValid: false };
    }
    
    const metadata: CacheMetadata = JSON.parse(metadataStr);
    const now = Date.now();
    
    // Prüfe ob der Cache abgelaufen ist
    if (now - metadata.cachedAt > MAX_CACHE_AGE_MS) {
      localStorage.removeItem(CACHE_PREFIX + backgroundId);
      localStorage.removeItem(METADATA_PREFIX + backgroundId);
      return { blob: null, isValid: false };
    }
    
    // Aktualisiere die letzte Verwendung
    metadata.lastUsed = now;
    localStorage.setItem(METADATA_PREFIX + backgroundId, JSON.stringify(metadata));
    
    return { blob: base64ToBlob(base64), isValid: true };
  } catch (error) {
    console.error('Fehler beim Laden aus Cache:', error);
    // Bereinige fehlerhafte Einträge
    localStorage.removeItem(CACHE_PREFIX + backgroundId);
    localStorage.removeItem(METADATA_PREFIX + backgroundId);
    return { blob: null, isValid: false };
  }
};

/**
 * Intelligente Hintergrundbild-Ladefunktion mit Cache
 */
export const loadBackgroundWithCache = async (token: string, backgroundId: string): Promise<string> => {
  // 1. Versuche aus Cache zu laden
  const cached = loadFromCache(backgroundId);
  if (cached.blob && cached.isValid) {
    logDebug(`Hintergrundbild ${backgroundId} aus Cache geladen`);
    return URL.createObjectURL(cached.blob);
  }
  
  // 2. Lade vom Server
  logDebug(`Hintergrundbild ${backgroundId} vom Server laden`);
  const blob = await getBackground(token, backgroundId);
  
  // 3. Speichere im Cache für nächste Verwendung
  saveToCache(backgroundId, blob);
  
  return URL.createObjectURL(blob);
};
