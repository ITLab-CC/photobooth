import React, { useRef, useState, useEffect } from "react";
import { Container, Box, Typography } from "@mui/material";
import { keyframes } from "@emotion/react";
import CameraPreview from "../components/CameraPreview";
import Countdown from "../components/Countdown";
import FlashAnimation from "../components/FlashAnimation";
import PhotoCameraIcon from "@mui/icons-material/PhotoCamera";
import itlab from "../assets/itlab.png";
import confetti from "canvas-confetti";

const gradientAnimation = keyframes`
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
`;

const PhotoboothPage: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [countdownActive, setCountdownActive] = useState(false);
  const [overlayVisible, setOverlayVisible] = useState(true);
  const [flashActive, setFlashActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (currentStep > 0 && currentStep < 3 && !countdownActive) {
      const timer = setTimeout(() => {
        setCountdownActive(true);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [currentStep, countdownActive]);

  useEffect(() => {
    if (currentStep === 3) {
      const timer = setTimeout(() => {
        resetPhotobooth();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [currentStep]);

  const handleOverlayClick = () => {
    if (currentStep === 0) {
      setOverlayVisible(false);
      setCountdownActive(true);
    }
  };

  const triggerConfetti = () => {
    confetti({
      particleCount: 150,
      spread: 70,
      origin: { y: 0.6 },
    });
  };

  const captureImage = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/png");
      uploadImage(dataUrl);
      setFlashActive(true);
      setTimeout(() => setFlashActive(false), 300);
      triggerConfetti();
      setCurrentStep((prev) => prev + 1);
    }
  };

  const onCountdownComplete = () => {
    setCountdownActive(false);
    captureImage();
  };

  const uploadImage = async (dataUrl: string) => {
    setUploading(true);
    try {
      const base64Data = dataUrl.replace(/^data:image\/png;base64,/, "");
      const response = await fetch("http://localhost:5000/upload", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ image: base64Data }),
      });
      const result = await response.json();
      console.log("Image uploaded:", result);
    } catch (error) {
      console.error("Upload failed:", error);
    } finally {
      setUploading(false);
    }
  };

  const resetPhotobooth = () => {
    setCurrentStep(0);
    setOverlayVisible(true);
    setCountdownActive(false);
  };

  return (
    <Container
      maxWidth={false}
      disableGutters
      sx={{
        minHeight: "100vh",
        p: 0,
        m: 0,
        background:
          "linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab)",
        backgroundSize: "400% 400%",
        animation: `${gradientAnimation} 15s ease infinite`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
      }}
    >
      <Box sx={{ width: "95%", maxWidth: 800 }}>
        <Box
          sx={{
            position: "relative",
            mb: 2,
            border: "5px solid white",
            boxShadow: "0px 0px 15px rgba(0,0,0,0.5)",
            borderRadius: 2,
            overflow: "hidden",
          }}
        >
          <CameraPreview videoRef={videoRef} />
          {overlayVisible && currentStep === 0 && !countdownActive && (
            <Box
              onClick={handleOverlayClick}
              sx={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: "100%",
                backdropFilter: "blur(5px)",
                backgroundColor: "rgba(255,255,255,0.3)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
                zIndex: 10,
              }}
            >
              <PhotoCameraIcon sx={{ fontSize: 64, color: "black" }} />
              <Typography variant="h6" color="black" sx={{ mt: 1 }}>
                Klicken, um 3 Bilder zu machen
              </Typography>
            </Box>
          )}
          {countdownActive && (
            <Box
              sx={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: "100%",
                backgroundColor: "rgba(0,0,0,0.5)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 20,
              }}
            >
              <Countdown seconds={5} onComplete={onCountdownComplete} />
            </Box>
          )}
          <FlashAnimation active={flashActive} />
        </Box>
        {uploading && (
          <Box sx={{ textAlign: "center", color: "white" }}>
            Bild wird hochgeladen...
          </Box>
        )}
      </Box>
      <Box
        sx={{
          position: "fixed",
          bottom: 16,
          right: 16,
          zIndex: 1000,
        }}
      >
        <img src={itlab} alt="Dekoration" style={{ width: "75px" }} />
      </Box>
    </Container>
  );
};

export default PhotoboothPage;
