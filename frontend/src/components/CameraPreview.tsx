import React, { useEffect } from "react";
import { Box, Paper } from "@mui/material";

interface CameraPreviewProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  onLoadedMetadata?: () => void;
}

const CameraPreview: React.FC<CameraPreviewProps> = ({ videoRef, onLoadedMetadata }) => {
  useEffect(() => {
    async function initCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        console.error("Kamerazugriff verweigert:", err);
      }
    }
    initCamera();
  }, [videoRef]);

  return (
    <Paper elevation={3} sx={{ overflow: "hidden", borderRadius: 2 }}>
      <Box
        component="video"
        ref={videoRef}
        autoPlay
        playsInline
        muted
        sx={{
          width: "720px",
          height: "680px",
          objectFit: "cover",
          transform: "scaleX(-1)",
        }}
        onLoadedMetadata={onLoadedMetadata}
      />
    </Paper>
  );
};

export default CameraPreview;
