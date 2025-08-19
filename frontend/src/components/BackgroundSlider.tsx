import React, { useEffect, useState } from "react";
import { Box, IconButton, Paper } from "@mui/material";
import ArrowBackIosIcon from "@mui/icons-material/ArrowBackIos";
import ArrowForwardIosIcon from "@mui/icons-material/ArrowForwardIos";
import { useSwipeable } from "react-swipeable";
import { listBackgrounds } from "../api";
import BackgroundImage from "./BackgroundImage";
import { preloadBackgrounds } from "../utils/backgroundPreloader";

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
          
          // Starte das Preloading der Hintergrundbilder im Hintergrund
          preloadBackgrounds(token).catch(err => {
            console.error("Fehler beim Preloading der Hintergrundbilder:", err);
          });
        }
      })
      .catch((err) => {
        console.error("Fehler beim Laden der Hintergründe:", err);
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
        {leftItem ? (
          <Paper 
            sx={{ 
              width: 150, 
              height: 150, 
              overflow: "hidden",
              cursor: "pointer"
            }}
            onClick={handlePrev}
          >
            <BackgroundImage
              token={token}
              backgroundId={leftItem.background_id}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </Paper>
        ) : (
          <Paper 
            sx={{ 
              width: 150, 
              height: 150,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: "#f5f5f5",
              color: "#666",
              fontSize: "14px",
              fontWeight: 500,
              cursor: selectedIndex === 0 ? "default" : "pointer",
              border: "1px solid #e0e0e0"
            }}
            onClick={selectedIndex !== 0 ? handlePrev : undefined}
          >
            {selectedIndex === 0 && "No Background"}
          </Paper>
        )}
        <Paper
          sx={{
            width: 180,
            height: 180,
            overflow: "hidden",
            border: "4px solid #1976d2",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {centerItem ? (
            <BackgroundImage
              token={token}
              backgroundId={centerItem.background_id}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          ) : (
            <Box sx={{ 
              width: "100%", 
              height: "100%", 
              display: "flex", 
              alignItems: "center", 
              justifyContent: "center",
              backgroundColor: "#f5f5f5",
              color: "#333",
              fontSize: "18px",
              fontWeight: 600
            }}>
              No Background
            </Box>
          )}
        </Paper>
        {rightItem ? (
          <Paper 
            sx={{ 
              width: 150, 
              height: 150, 
              overflow: "hidden",
              cursor: "pointer"
            }}
            onClick={handleNext}
          >
            <BackgroundImage
              token={token}
              backgroundId={rightItem.background_id}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </Paper>
        ) : (
          <Paper 
            sx={{ 
              width: 150, 
              height: 150,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: "#f5f5f5",
              color: "#666",
              fontSize: "14px",
              fontWeight: 500,
              cursor: selectedIndex === paddedBackgrounds.length - 2 ? "default" : "pointer",
              border: "1px solid #e0e0e0"
            }}
            onClick={selectedIndex !== paddedBackgrounds.length - 2 ? handleNext : undefined}
          >
            {selectedIndex === paddedBackgrounds.length - 2 && "No Background"}
          </Paper>
        )}
      </Box>
      <IconButton onClick={handleNext} disabled={selectedIndex === paddedBackgrounds.length - 2}>
        <ArrowForwardIosIcon />
      </IconButton>
    </Box>
  );
};

export default BackgroundSlider;
