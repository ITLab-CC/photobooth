import { useRef, useState } from "react";
import { Box, Button, Typography } from "@mui/material";
import { keyframes } from "@mui/system";
import { addGalleryImage } from "../api";
import CameraPreview from "./CameraPreview";
import PhotoCameraIcon from "@mui/icons-material/PhotoCamera";
import confetti from "canvas-confetti";
import { logDebug } from "../utils/logger";
import { KIOSK_WIDTH, brand, px } from "../theme";

const countPop = keyframes`
  from { opacity: 0; transform: scale(0.7); }
  to { opacity: 1; transform: scale(1); }
`;

const flashAnimation = keyframes`
  from { opacity: 1; }
  to { opacity: 0; }
`;

interface CustomCameraComponentProps {
  galleryId: string;
  token: string;
  onImageUpload?: (imageId: string) => void;
  onError?: (message: string) => void;
}

export default function CustomCameraComponent({
  galleryId,
  token,
  onImageUpload,
  onError,
}: CustomCameraComponentProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [isCapturing, setIsCapturing] = useState<boolean>(false);
  const [videoReady, setVideoReady] = useState<boolean>(false);
  const [flashActive, setFlashActive] = useState<boolean>(false);

  const reportError = (message: string) => {
    console.error(message);
    onError?.(message);
  };

  const startCountdown = () => {
    if (!galleryId) {
      reportError("Die Fotobox ist noch nicht bereit. Bitte kurz warten.");
      return;
    }
    if (!videoReady) {
      reportError("Die Kamera startet noch. Bitte kurz warten.");
      return;
    }
    setIsCapturing(true);
    let counter = 3;
    setCountdown(counter);
    const interval = setInterval(() => {
      counter -= 1;
      setCountdown(counter);
      if (counter === 0) {
        videoRef.current?.pause();
      }
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
        reportError("Die Kamera liefert noch kein Bild. Bitte kurz warten.");
        setCountdown(null);
        setIsCapturing(false);
        videoRef.current?.play();
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
          const response = await addGalleryImage(token, galleryId, base64Data);
          logDebug("Foto erfolgreich hochgeladen, Bild ID:", response.image_id);
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
          reportError("Das Foto konnte nicht gespeichert werden. Bitte noch einmal versuchen.");
        }
      }
    }
    setCountdown(null);
    setIsCapturing(false);
    videoRef.current?.play();
  };

  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "center",
        width: "100%",
        padding: "0 5%",
        boxSizing: "border-box",
      }}
    >
      <Box
        position="relative"
        sx={{
          width: "100%",
          maxWidth: `${KIOSK_WIDTH}px`,
          height: `${KIOSK_WIDTH}px`,
          margin: "20px auto",
        }}
      >
      <CameraPreview
        videoRef={videoRef}
        onLoadedMetadata={() => {
          logDebug(
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
 
      {countdown !== null && (
        <Box
          position="absolute"
          aria-live="assertive"
          sx={{
            top: 0,
            right: 0,
            bottom: 0,
            left: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "none",
          }}
        >
          <Typography
            key={countdown}
            sx={{
              fontSize: "14rem",
              lineHeight: 1,
              fontWeight: 700,
              color: countdown === 0 ? brand.magic : "#ffffff",
              textShadow: "0 4px 24px rgba(37, 43, 63, 0.55)",
              animation: `${countPop} 0.5s cubic-bezier(0.22, 1, 0.36, 1)`,
              "@media (prefers-reduced-motion: reduce)": { animation: "none" },
            }}
          >
            {countdown >= 0 ? (countdown === 0 ? "Los!" : countdown) : ""}
          </Typography>
        </Box>
      )}
      </Box>

      {!isCapturing && (
        <Button
          variant="contained"
          onClick={startCountdown}
          startIcon={<PhotoCameraIcon sx={{ fontSize: "2.2rem !important" }} />}
          sx={{
            position: "fixed",
            bottom: px(28),
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 20,
            minHeight: px(84),
            minWidth: px(320),
            px: 5,
            fontSize: "1.7rem",
            borderRadius: 42,
            boxShadow: "0 10px 24px rgba(0, 117, 133, 0.35)",
          }}
        >
          Foto machen
        </Button>
      )}
    </Box>
  );
}
