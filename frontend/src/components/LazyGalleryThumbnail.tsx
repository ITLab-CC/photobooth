import React, { useEffect, useState, useRef } from "react";
import { getImage } from "../api";

interface LazyGalleryThumbnailProps {
  token: string;
  imageId: string;
  onClick?: () => void;
  loadImmediately?: boolean; // Neuer Prop für sofortiges Laden
}

const LazyGalleryThumbnail: React.FC<LazyGalleryThumbnailProps> = ({ token, imageId, onClick, loadImmediately = false }) => {
  const [imageUrl, setImageUrl] = useState<string>("");
  const [isVisible, setIsVisible] = useState<boolean>(loadImmediately);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const imgRef = useRef<HTMLDivElement>(null);

  // Intersection Observer für Lazy Loading (nur wenn nicht sofort geladen werden soll)
  useEffect(() => {
    if (loadImmediately) return;
    
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
            observer.disconnect();
          }
        });
      },
      {
        threshold: 0.1, // Lade wenn 10% sichtbar
        rootMargin: '50px' // Lade 50px bevor es sichtbar wird
      }
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => observer.disconnect();
  }, []);

  // Lade das Bild nur wenn es sichtbar ist
  useEffect(() => {
    if (!isVisible || isLoading) return;

    let url = "";
    setIsLoading(true);
    
    getImage(token, imageId)
      .then((blob) => {
        url = URL.createObjectURL(blob);
        setImageUrl(url);
      })
      .catch((err) => console.error("Fehler beim Laden des Bildes:", err))
      .finally(() => setIsLoading(false));
    
    return () => {
      if (url) {
        URL.revokeObjectURL(url);
      }
    };
  }, [token, imageId, isVisible, isLoading]);

  return (
    <div ref={imgRef} style={{ minWidth: "80px", minHeight: "80px" }}>
      {isLoading && (
        <div
          style={{
            width: "80px",
            height: "80px",
            backgroundColor: "#f0f0f0",
            borderRadius: "4px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "12px",
            color: "#666",
          }}
        >
          Lädt...
        </div>
      )}
      {imageUrl && (
        <img
          src={imageUrl}
          alt="Thumbnail"
          onClick={onClick}
          style={{
            width: "80px",
            height: "80px",
            objectFit: "cover",
            borderRadius: "4px",
            cursor: "pointer",
          }}
        />
      )}
    </div>
  );
};

export default LazyGalleryThumbnail;
