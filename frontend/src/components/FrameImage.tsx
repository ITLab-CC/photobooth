import React, { useEffect, useState } from "react";
import { getFrame } from "../api";

// In-Memory-Cache für die aktuelle Sitzung
const urlCache: Record<string, string> = {};
const promiseCache: Record<string, Promise<string>> = {};

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
      promiseCache[frameId] = getFrame(token, frameId).then((blob) => {
        const objectUrl = URL.createObjectURL(blob);
        urlCache[frameId] = objectUrl;
        return objectUrl;
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
