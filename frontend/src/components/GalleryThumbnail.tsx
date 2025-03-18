import React, { useEffect, useState } from "react";
import { getImage } from "../api";

interface GalleryThumbnailProps {
  token: string;
  imageId: string;
  onClick?: () => void;
  onLoad?: () => void; // Neuer Callback
}

const GalleryThumbnail: React.FC<GalleryThumbnailProps> = ({ token, imageId, onClick, onLoad }) => {
  const [imageUrl, setImageUrl] = useState<string>("");

  useEffect(() => {
    let url = "";
    getImage(token, imageId)
      .then((blob) => {
        url = URL.createObjectURL(blob);
        setImageUrl(url);
      })
      .catch((err) => console.error("Fehler beim Laden des Bildes:", err));
    return () => {
      if (url) {
        URL.revokeObjectURL(url);
      }
    };
  }, [token, imageId]);

  if (!imageUrl) return null;
  return (
    <img
      src={imageUrl}
      alt="Thumbnail"
      onClick={onClick}
      onLoad={onLoad}  // Hier wird der Callback aufgerufen, wenn das Bild geladen ist
      style={{
        width: "80px",
        height: "80px",
        objectFit: "cover",
        borderRadius: "4px",
        cursor: "pointer",
      }}
    />
  );
};

export default GalleryThumbnail;
