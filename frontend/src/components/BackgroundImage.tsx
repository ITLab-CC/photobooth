import React, { useEffect, useState } from "react";
import { getBackground } from "../api";
import { logDebug } from "../utils/logger";

// In-Memory-Cache für die aktuelle Sitzung
const urlCache: Record<string, string> = {};
const promiseCache: Record<string, Promise<string>> = {};

// Rate Limiting: Nur eine Anfrage gleichzeitig
let isRequestInProgress = false;
const requestQueue: Array<{ resolve: (value: string) => void; reject: (reason: any) => void; backgroundId: string; token: string }> = [];

/**
 * Verarbeitet die Warteschlange für Hintergrundbild-Anfragen
 */
const processQueue = async () => {
  if (isRequestInProgress || requestQueue.length === 0) return;
  
  isRequestInProgress = true;
  const { resolve, reject, backgroundId, token } = requestQueue.shift()!;
  
  try {
    const blob = await getBackground(token, backgroundId);
    const objectUrl = URL.createObjectURL(blob);
    urlCache[backgroundId] = objectUrl;
    
    // Im Local Storage speichern für zukünftige Verwendung
    await saveImageToLocalStorage(backgroundId, blob);
    
    resolve(objectUrl);
  } catch (error) {
    reject(error);
  } finally {
    isRequestInProgress = false;
    // Verarbeite nächsten Eintrag in der Warteschlange nach einer kurzen Verzögerung
    setTimeout(() => processQueue(), 500);
  }
};

// Local Storage Keys
const LS_PREFIX = 'photobooth_bg_';
const LS_TIMESTAMP_PREFIX = 'photobooth_bg_timestamp_';
const CACHE_EXPIRY_MS = 24 * 60 * 60 * 1000; // 24 Stunden

interface BackgroundImageProps {
  token: string;
  backgroundId: string;
  onClick?: () => void;
  style?: React.CSSProperties;
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
 * Speichert ein Bild im Local Storage (mit Quota-Handling)
 */
const saveImageToLocalStorage = async (id: string, blob: Blob) => {
  try {
    const base64 = await blobToBase64(blob);
    localStorage.setItem(LS_PREFIX + id, base64);
    localStorage.setItem(LS_TIMESTAMP_PREFIX + id, Date.now().toString());
  } catch (error) {
    if (error instanceof Error && error.name === 'QuotaExceededError') {
      console.warn('Local Storage voll, überspringe Cache für Hintergrundbild:', id);
      // Lösche alte Cache-Einträge um Platz zu schaffen
      try {
        const keys = Object.keys(localStorage);
        const bgKeys = keys.filter(key => key.startsWith(LS_PREFIX));
        // Lösche die ältesten 5 Hintergrundbilder
        bgKeys.slice(0, 5).forEach(key => {
          const timestampKey = key.replace(LS_PREFIX, LS_TIMESTAMP_PREFIX);
          localStorage.removeItem(key);
          localStorage.removeItem(timestampKey);
        });
        logDebug('Alte Cache-Einträge gelöscht');
      } catch (cleanupError) {
        console.error('Fehler beim Cleanup des Local Storage:', cleanupError);
      }
    } else {
      console.error('Fehler beim Speichern im Local Storage:', error);
    }
  }
};

/**
 * Lädt ein Bild aus dem Local Storage
 */
const loadImageFromLocalStorage = (id: string): { blob: Blob | null, expired: boolean } => {
  try {
    const base64 = localStorage.getItem(LS_PREFIX + id);
    const timestamp = localStorage.getItem(LS_TIMESTAMP_PREFIX + id);
    
    if (!base64 || !timestamp) return { blob: null, expired: true };
    
    const isExpired = Date.now() - parseInt(timestamp) > CACHE_EXPIRY_MS;
    if (isExpired) return { blob: null, expired: true };
    
    return { blob: base64ToBlob(base64), expired: false };
  } catch (error) {
    console.error('Fehler beim Laden aus dem Local Storage:', error);
    return { blob: null, expired: true };
  }
};

const BackgroundImage: React.FC<BackgroundImageProps> = ({ token, backgroundId, onClick, style }) => {
  const [imageUrl, setImageUrl] = useState<string>("");

  useEffect(() => {
    let isMounted = true;
    
    // 1. Prüfen, ob das Bild im In-Memory-Cache ist
    if (urlCache[backgroundId]) {
      setImageUrl(urlCache[backgroundId]);
      return;
    }
    
    // 2. Prüfen, ob das Bild im Local Storage ist
    const { blob, expired } = loadImageFromLocalStorage(backgroundId);
    
    if (blob && !expired) {
      const objectUrl = URL.createObjectURL(blob);
      urlCache[backgroundId] = objectUrl;
      setImageUrl(objectUrl);
      return;
    }
    
    // 3. Wenn nicht im Cache oder abgelaufen, vom Server laden mit Rate Limiting
    if (!promiseCache[backgroundId]) {
      promiseCache[backgroundId] = new Promise<string>((resolve, reject) => {
        requestQueue.push({ resolve, reject, backgroundId, token });
        processQueue();
      });
    }
    
    promiseCache[backgroundId]
      .then((url) => {
        if (isMounted) {
          setImageUrl(url);
        }
      })
      .catch((err) => {
        console.error("Fehler beim Laden des Hintergrundbildes:", err);
      });
      
    return () => {
      isMounted = false;
    };
  }, [token, backgroundId]);

  if (!imageUrl) return null;
  return (
    <img
      src={imageUrl}
      alt="Hintergrund"
      onClick={onClick}
      style={style}
    />
  );
};

export default BackgroundImage;
