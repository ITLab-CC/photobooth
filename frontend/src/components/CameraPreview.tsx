import React, { useEffect } from "react";
import { Box, Paper } from "@mui/material";

interface CameraPreviewProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  onLoadedMetadata?: () => void;
  /** Size of the visible image in pixels. The video fills it (cropped, not stretched). */
  width: number;
  height: number;
}

const CameraPreview: React.FC<CameraPreviewProps> = ({ videoRef, onLoadedMetadata, width, height }) => {
  useEffect(() => {
    let activeStream: MediaStream | null = null;
    async function initCamera() {
      try {
        // Ask for the best picture the camera has: without a request browsers often hand out only 640x480.
        // "ideal" takes the closest mode, so a camera that tops out lower still works.
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1920 }, height: { ideal: 1080 }, frameRate: { ideal: 30 } },
        });
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
        width: `${width}px`,
        maxWidth: "100%",
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
          display: "block", // inline video leaves a baseline gap that shows as a white strip
          width: "100%",
          height: `${height}px`,
          objectFit: "cover",
          transform: "scaleX(-1)",
        }}
        onLoadedMetadata={onLoadedMetadata}
      />
    </Paper>
  );
};

export default CameraPreview;
