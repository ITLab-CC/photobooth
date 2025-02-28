import React from "react";
import { Button } from "@mui/material";

interface ShareAllButtonProps {
  images: { url: string; name: string }[];
  authToken: string;
}

const ShareAllButton: React.FC<ShareAllButtonProps> = ({
  images,
  authToken,
}) => {
  const handleShareAll = async () => {
    if (navigator.share) {
      try {
        const files = await Promise.all(
          images.map(async (img) => {
            const response = await fetch(img.url, {
              headers: { Authorization: authToken },
            });
            if (response.ok) {
              const blob = await response.blob();
              return new File([blob], `${img.name || img.url}.png`, {
                type: blob.type,
              });
            } else {
              throw new Error(`Fehler beim Laden von ${img.name}`);
            }
          })
        );

        if (navigator.canShare && navigator.canShare({ files })) {
          await navigator.share({
            files,
            title: "Photobooth Bilder",
            text: "Schau dir diese Bilder an!",
          });
        } else {
          await navigator.share({
            title: "Photobooth Bilder",
            text: "Schau dir dieses Bild an!",
            url: images[0].url,
          });
        }
      } catch (error) {
        console.error("Fehler beim Teilen aller Bilder:", error);
      }
    } else {
      alert("Sharing wird in diesem Browser nicht unterstützt.");
    }
  };

  return (
    <Button variant="contained" onClick={handleShareAll}>
      Alle Bilder teilen
    </Button>
  );
};

export default ShareAllButton;
