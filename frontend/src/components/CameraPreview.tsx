import React, { useEffect } from "react";
import { Box, Paper } from "@mui/material";
import { KIOSK_WIDTH } from "../theme";

interface CameraPreviewProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  onLoadedMetadata?: () => void;
}

const CameraPreview: React.FC<CameraPreviewProps> = ({ videoRef, onLoadedMetadata }) => {
  useEffect(() => {
    let activeStream: MediaStream | null = null;
    async function initCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        activeStream = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        console.error("Kamerazugriff verweigert:", err);
      }
    }
    initCamera();
    return () => {
      activeStream?.getTracks().forEach((track) => track.stop());
    };
  }, [videoRef]);

  return (
    <Paper 
      elevation={3} 
      sx={{ 
        overflow: "hidden", 
        borderRadius: 2,
        width: "100%",
        maxWidth: `${KIOSK_WIDTH}px`,
        margin: "0 auto",
        boxSizing: "border-box",
      }}
    >
      <Box
        component="video"
        ref={videoRef}
        autoPlay
        playsInline
        muted
        sx={{
          width: "100%",
          height: `${KIOSK_WIDTH}px`,
          objectFit: "cover",
          transform: "scaleX(-1)",
        }}
        onLoadedMetadata={onLoadedMetadata}
      />
    </Paper>
  );
};

export default CameraPreview;
