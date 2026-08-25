import React, { useEffect, useState } from "react";
import { getFrame } from "../api";

// In-Memory-Cache für die aktuelle Sitzung
const urlCache: Record<string, string> = {};
const promiseCache: Record<string, Promise<string>> = {};

// Rate Limiting: nur eine Frame-Anfrage gleichzeitig (Backend erlaubt nur
// 1 Request/Sekunde auf /api/v1/frame/{id} — mehrere Frames gleichzeitig
// gerendert würden sonst sofort 429 auslösen).
let isRequestInProgress = false;
const requestQueue: Array<{ resolve: (value: string) => void; reject: (reason: any) => void; frameId: string; token: string }> = [];

const processQueue = async () => {
  if (isRequestInProgress || requestQueue.length === 0) return;

  isRequestInProgress = true;
  const { resolve, reject, frameId, token } = requestQueue.shift()!;

  try {
    const blob = await getFrame(token, frameId);
    const objectUrl = URL.createObjectURL(blob);
    urlCache[frameId] = objectUrl;
    resolve(objectUrl);
  } catch (error) {
    reject(error);
  } finally {
    isRequestInProgress = false;
    setTimeout(() => processQueue(), 500);
  }
};

interface FrameImageProps {
  token: string;
  frameId: string;
  onClick?: () => void;
  style?: React.CSSProperties;
}

const FrameImage: React.FC<FrameImageProps> = ({ token, frameId, onClick, style }) => {
  const [imageUrl, setImageUrl] = useState<string>("");

  useEffect(() => {
    let isMounted = true;

    if (urlCache[frameId]) {
      setImageUrl(urlCache[frameId]);
      return;
    }

    if (!promiseCache[frameId]) {
      promiseCache[frameId] = new Promise<string>((resolve, reject) => {
        requestQueue.push({ resolve, reject, frameId, token });
        processQueue();
      });
    }

    promiseCache[frameId]
      .then((url) => {
        if (isMounted) {
          setImageUrl(url);
        }
      })
      .catch((err) => {
        console.error("Fehler beim Laden des Frame-Bildes:", err);
      });

    return () => {
      isMounted = false;
    };
  }, [token, frameId]);

  if (!imageUrl) return null;
  return <img src={imageUrl} alt="Frame" onClick={onClick} style={style} />;
};

export default FrameImage;
