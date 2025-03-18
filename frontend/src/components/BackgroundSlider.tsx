import React, { useEffect, useState } from "react";
import { Box, IconButton, Paper } from "@mui/material";
import ArrowBackIosIcon from "@mui/icons-material/ArrowBackIos";
import ArrowForwardIosIcon from "@mui/icons-material/ArrowForwardIos";
import { useSwipeable } from "react-swipeable";
import { listBackgrounds } from "../api";
import BackgroundImage from "./BackgroundImage";

interface BackgroundResponse {
  background_id: string;
}

interface BackgroundListResponse {
  backgrounds: BackgroundResponse[];
}

interface BackgroundSliderProps {
  token: string;
  onSelect?: (backgroundId: string) => void;
}


const BackgroundSlider: React.FC<BackgroundSliderProps> = ({ token, onSelect }) => {
  const [backgrounds, setBackgrounds] = useState<BackgroundResponse[]>([]);
  const paddedBackgrounds = [null, ...backgrounds, null];
  const [selectedIndex, setSelectedIndex] = useState<number>(1);

  useEffect(() => {
    listBackgrounds(token)
      .then((data: BackgroundListResponse) => {
        if (data.backgrounds && data.backgrounds.length > 0) {
          setBackgrounds(data.backgrounds);
          setSelectedIndex(1);
        }
      })
      .catch((err) => {
        console.error("Fehler beim Laden der Hintergründe:", err);
      });
  }, [token]);

  useEffect(() => {
    if (onSelect && paddedBackgrounds[selectedIndex]) {
      onSelect(paddedBackgrounds[selectedIndex]!.background_id);
    }
  }, [selectedIndex, paddedBackgrounds, onSelect]);

  const clampIndex = (index: number) =>
    Math.max(1, Math.min(index, paddedBackgrounds.length - 2));

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
      <IconButton onClick={handlePrev} disabled={selectedIndex === 1}>
        <ArrowBackIosIcon />
      </IconButton>
      <Box display="flex" gap={1}>
        <Paper sx={{ width: 150, height: 150, overflow: "hidden" }}>
          {leftItem ? (
            <BackgroundImage
              token={token}
              backgroundId={leftItem.background_id}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          ) : (
            <Box sx={{ width: "100%", height: "100%" }} />
          )}
        </Paper>
        <Paper
          sx={{
            width: 180,
            height: 180,
            overflow: "hidden",
            border: "4px solid #1976d2",
            transition: "transform 0.3s",
            transform: "scale(1.2)",
          }}
        >
          {centerItem && (
            <BackgroundImage
              token={token}
              backgroundId={centerItem.background_id}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          )}
        </Paper>
        <Paper sx={{ width: 150, height: 150, overflow: "hidden" }}>
          {rightItem ? (
            <BackgroundImage
              token={token}
              backgroundId={rightItem.background_id}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          ) : (
            <Box sx={{ width: "100%", height: "100%" }} />
          )}
        </Paper>
      </Box>
      <IconButton onClick={handleNext} disabled={selectedIndex === paddedBackgrounds.length - 2}>
        <ArrowForwardIosIcon />
      </IconButton>
    </Box>
  );
};

export default BackgroundSlider;
