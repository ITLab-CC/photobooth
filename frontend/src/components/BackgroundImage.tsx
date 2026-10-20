import React, { useEffect, useState } from "react";
import { loadBackgroundWithCache } from "../utils/intelligentCache";

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

    loadBackgroundWithCache(token, backgroundId)
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
      loading="lazy"
      onClick={onClick}
      style={style}
    />
  );
};

export default BackgroundImage;
