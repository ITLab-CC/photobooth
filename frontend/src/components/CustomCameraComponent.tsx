import { useRef, useState } from "react";
import { Box, Typography } from "@mui/material";
import { keyframes } from "@mui/system";
import { addGalleryImage } from "../api";
import CameraPreview from "./CameraPreview";
import PhotoCameraIcon from "@mui/icons-material/PhotoCamera";
import confetti from "canvas-confetti";

const flashAnimation = keyframes`
  from { opacity: 1; }
  to { opacity: 0; }
`;

interface CustomCameraComponentProps {
  galleryId: string;
  token: string;
  onImageUpload?: (imageId: string) => void;
}

export default function CustomCameraComponent({
  galleryId,
  token,
  onImageUpload,
}: CustomCameraComponentProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [isCapturing, setIsCapturing] = useState<boolean>(false);
  const [videoReady, setVideoReady] = useState<boolean>(false);
  const [flashActive, setFlashActive] = useState<boolean>(false);

  const startCountdown = () => {
    if (!galleryId) {
      alert("Keine Galerie vorhanden. Bitte erst eine Galerie erstellen.");
      return;
    }
    if (!videoReady) {
      alert("Kamerastream ist noch nicht bereit. Bitte warten Sie einen Moment.");
      return;
    }
    setIsCapturing(true);
    let counter = 3;
    setCountdown(counter);
    const interval = setInterval(() => {
      counter -= 1;
      setCountdown(counter);
      if (counter < 0) {
        clearInterval(interval);
        capturePhoto();
      }
    }, 1000);
  };

  const capturePhoto = async () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const width = video.videoWidth;
      const height = video.videoHeight;
      if (width === 0 || height === 0) {
        alert("Kamerastream ist noch nicht verfügbar.");
        setCountdown(null);
        setIsCapturing(false);
        return;
      }
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d");
      if (context) {
        context.drawImage(video, 0, 0, width, height);
        const dataUrl = canvas.toDataURL("image/png");
        // Entferne den Daten-URL-Präfix
        const base64Data = dataUrl.replace(/^data:image\/png;base64,/, "");
        try {
          const response = await addGalleryImage(token, galleryId, base64Data, "");
          console.log("Foto erfolgreich hochgeladen, Bild ID:", response.image_id);
          if (onImageUpload) {
            onImageUpload(response.image_id);
          }
          setFlashActive(true);
          setTimeout(() => setFlashActive(false), 600);
          confetti({
            particleCount: 150,
            spread: 70,
            origin: { y: 0.6 },
          });
        } catch (uploadError) {
          console.error("Fehler beim Upload:", uploadError);
          alert("Fehler beim Hochladen des Fotos.");
        }
      }
    }
    setCountdown(null);
    setIsCapturing(false);
  };

  return (
    <Box
      position="relative"
      sx={{
        width: "calc(100% - 40px)", 
        maxWidth: 680,
        height: 680,
        margin: "20px auto",
      }}
    >
      <CameraPreview
        videoRef={videoRef}
        onLoadedMetadata={() => {
          console.log(
            "loadedmetadata fired:",
            videoRef.current?.videoWidth,
            videoRef.current?.videoHeight
          );
          setVideoReady(true);
        }}
      />
      <canvas ref={canvasRef} style={{ display: "none" }} />
      
      {flashActive && (
        <Box
          position="absolute"
          sx={{
            top: 0,
            right: 0,
            bottom: 0,
            left: 0,
            backgroundColor: "white",
            animation: `${flashAnimation} 600ms ease-out`,
          }}
        />
      )}
 
      {!isCapturing && (
        <Box
          position="absolute"
          sx={{
            top: 0,
            right: 0,
            bottom: 0,
            left: 0,
            backgroundColor: "rgba(0, 0, 0, 0.4)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
          }}
          onClick={startCountdown}
        >
          <PhotoCameraIcon sx={{ fontSize: 64, color: "white" }} />
          <Typography variant="h6" color="white" sx={{ mt: 1 }}>
            Tippe um den Countdown zu starten
          </Typography>
        </Box>
      )}

      {countdown !== null && (
        <Box
          position="absolute"
          sx={{
            top: 0,
            right: 0,
            bottom: 0,
            left: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Typography variant="h1" color="white">
            {countdown >= 0 ? (countdown === 0 ? "Go!" : countdown) : ""}
          </Typography>
        </Box>
      )}
    </Box>
  );
}
