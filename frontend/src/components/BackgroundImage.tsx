import React, { useEffect, useState } from "react";
import { getBackground } from "../api";

const urlCache: Record<string, string> = {};
const promiseCache: Record<string, Promise<string>> = {};

interface BackgroundImageProps {
  token: string;
  backgroundId: string;
  onClick?: () => void;
  style?: React.CSSProperties;
}

const BackgroundImage: React.FC<BackgroundImageProps> = ({ token, backgroundId, onClick, style }) => {
  const [imageUrl, setImageUrl] = useState<string>("");

  useEffect(() => {
    let isMounted = true;
    if (urlCache[backgroundId]) {
      setImageUrl(urlCache[backgroundId]);
      return;
    }
    if (!promiseCache[backgroundId]) {
      promiseCache[backgroundId] = getBackground(token, backgroundId).then((blob) => {
        const objectUrl = URL.createObjectURL(blob);
        urlCache[backgroundId] = objectUrl;
        return objectUrl;
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
