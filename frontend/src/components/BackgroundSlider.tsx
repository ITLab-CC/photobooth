import React, { useEffect, useState } from "react";
import { Box, IconButton, Paper } from "@mui/material";
import ArrowBackIosIcon from "@mui/icons-material/ArrowBackIos";
import ArrowForwardIosIcon from "@mui/icons-material/ArrowForwardIos";
import { useSwipeable } from "react-swipeable";
import { listBackgrounds } from "../api";
import OptimizedBackgroundImage from "./OptimizedBackgroundImage";

interface BackgroundResponse {
  background_id: string;
}

interface BackgroundListResponse {
  backgrounds: BackgroundResponse[];
}

interface BackgroundSliderProps {
  token: string;
  onSelect?: (backgroundId: string | null) => void;
}


const BackgroundSlider: React.FC<BackgroundSliderProps> = ({ token, onSelect }) => {
  const [backgrounds, setBackgrounds] = useState<BackgroundResponse[]>([]);
  const paddedBackgrounds = [null, ...backgrounds, null];
  const [selectedIndex, setSelectedIndex] = useState<number>(0);

  useEffect(() => {
    // Hintergrundbilder laden
    listBackgrounds(token)
      .then((data: BackgroundListResponse) => {
        if (data.backgrounds && data.backgrounds.length > 0) {
          setBackgrounds(data.backgrounds);
          // Behalte den Index 0 für "No Background"
        }
      })
      .catch((err) => {
        console.error("Fehler beim Laden der Hintergrundbilder:", err);
      });
  }, [token]);

  useEffect(() => {
    if (onSelect) {
      // Wenn das erste Element ausgewählt ist (No Background), null übergeben
      if (selectedIndex === 0) {
        onSelect(null);
      } else if (paddedBackgrounds[selectedIndex]) {
        onSelect(paddedBackgrounds[selectedIndex]!.background_id);
      }
    }
  }, [selectedIndex, paddedBackgrounds, onSelect]);

  const clampIndex = (index: number) =>
    Math.max(0, Math.min(index, paddedBackgrounds.length - 2));

  const handlePrev = () => {
    setSelectedIndex((prev) => clampIndex(prev - 1));
  };

  const handleNext = () => {
    setSelectedIndex((prev) => clampIndex(prev + 1));
  };

  const swipeHandlers = useSwipeable({
    onSwipedLeft: () => handleNext(),
    onSwipedRight: () => handlePrev(),
    trackMouse: true,
  });

  const leftItem = paddedBackgrounds[selectedIndex - 1];
  const centerItem = paddedBackgrounds[selectedIndex];
  const rightItem = paddedBackgrounds[selectedIndex + 1];

  return (
    <Box {...swipeHandlers} display="flex" alignItems="center" mt={2}>
      <IconButton onClick={handlePrev} disabled={selectedIndex === 0}>
        <ArrowBackIosIcon />
      </IconButton>
      <Box display="flex" gap={1}>
        {leftItem && (
          <OptimizedBackgroundImage
            token={token}
            backgroundId={leftItem.background_id}
            style={{
              width: 150,
              height: 150,
              borderRadius: 4,
              objectFit: "cover",
              opacity: 0.7,
              cursor: "pointer",
            }}
            onClick={handlePrev}
          />
        )}
        <Box sx={{ position: "relative", width: 180, height: 180 }}>
          {centerItem ? (
            <OptimizedBackgroundImage
              token={token}
              backgroundId={centerItem.background_id}
              style={{
                width: "100%",
                height: "100%",
                borderRadius: 2,
                objectFit: "cover",
                border: "3px solid #fff",
                boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
              }}
            />
          ) : (
            <Box
              sx={{
                width: "100%",
                height: "100%",
                borderRadius: 2,
                border: "3px solid #fff",
                boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: "rgba(255,255,255,0.1)",
              }}
            >
              No Background
            </Box>
          )}
        </Box>
        {rightItem && (
          <OptimizedBackgroundImage
            token={token}
            backgroundId={rightItem.background_id}
            style={{
              width: 150,
              height: 150,
              borderRadius: 4,
              objectFit: "cover",
              opacity: 0.7,
              cursor: "pointer",
            }}
            onClick={handleNext}
          />
        )}
      </Box>
      <IconButton onClick={handleNext} disabled={selectedIndex === paddedBackgrounds.length - 2}>
        <ArrowForwardIosIcon />
      </IconButton>
    </Box>
  );
};

export default BackgroundSlider;
