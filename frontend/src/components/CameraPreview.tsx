import React, { useEffect } from "react";
import { Box, Paper } from "@mui/material";

interface CameraPreviewProps {
  videoRef: React.RefObject<HTMLVideoElement>;
}

const CameraPreview: React.FC<CameraPreviewProps> = ({ videoRef }) => {
  useEffect(() => {
    async function initCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: true,
        });
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
    <Paper elevation={3} sx={{ overflow: "hidden" }}>
      <Box
        component="video"
        ref={videoRef}
        autoPlay
        playsInline
        sx={{ width: "100%" }}
      />
    </Paper>
  );
};

export default CameraPreview;
