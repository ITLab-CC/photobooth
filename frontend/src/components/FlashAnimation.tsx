import React from "react";
import { Box } from "@mui/material";

interface FlashAnimationProps {
  active: boolean;
}

const FlashAnimation: React.FC<FlashAnimationProps> = ({ active }) => {
  return (
    <Box
      sx={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        backgroundColor: "white",
        opacity: active ? 1 : 0,
        transition: "opacity 0.3s ease",
        pointerEvents: "none",
        zIndex: 1300,
      }}
    />
  );
};

export default FlashAnimation;
