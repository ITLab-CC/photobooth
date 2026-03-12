import React, { useEffect, useState } from "react";
import { getBackground } from "../api";

interface OptimizedBackgroundImageProps {
  token: string;
  backgroundId: string;
  onClick?: () => void;
  style?: React.CSSProperties;
}

const OptimizedBackgroundImage: React.FC<OptimizedBackgroundImageProps> = ({ 
  token, 
  backgroundId, 
  onClick, 
  style 
}) => {
  const [imageUrl, setImageUrl] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    let url = "";

    const loadImage = async () => {
      setIsLoading(true);
      try {
        const blob = await getBackground(token, backgroundId);
        url = URL.createObjectURL(blob);
        if (isMounted) {
          setImageUrl(url);
        }
      } catch (error) {
        console.error("Fehler beim Laden des Hintergrundbildes:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadImage();

    return () => {
      isMounted = false;
      if (url) {
        URL.revokeObjectURL(url);
      }
    };
  }, [token, backgroundId]);

  if (isLoading) {
    return (
      <div
        style={{
          ...style,
          backgroundColor: "#f0f0f0",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#666",
          fontSize: "14px",
        }}
      >
        Lädt...
      </div>
    );
  }

  if (!imageUrl) {
    return (
      <div
        style={{
          ...style,
          backgroundColor: "#f0f0f0",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#999",
          fontSize: "12px",
        }}
      >
        Fehler
      </div>
    );
  }

  return (
    <img
      src={imageUrl}
      alt="Hintergrund"
      onClick={onClick}
      style={style}
    />
  );
};

export default OptimizedBackgroundImage;
