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
  const [selectedIndex, setSelectedIndex] = useState<number>(0);

  useEffect(() => {
    listBackgrounds(token)
      .then((data: BackgroundListResponse) => {
        if (data.backgrounds && data.backgrounds.length > 0) {
          setBackgrounds(data.backgrounds);
          setSelectedIndex(0);
        }
      })
      .catch((err) => {
        console.error("Fehler beim Laden der Hintergründe:", err);
      });
  }, [token]);

  useEffect(() => {
    if (onSelect && backgrounds[selectedIndex]) {
      onSelect(backgrounds[selectedIndex].background_id);
    }
  }, [selectedIndex, backgrounds, onSelect]);

  const handlePrev = () => {
    setSelectedIndex((prev) => Math.max(prev - 1, 0));
  };

  const handleNext = () => {
    setSelectedIndex((prev) => Math.min(prev + 1, backgrounds.length - 1));
  };

  const swipeHandlers = useSwipeable({
    onSwipedLeft: handleNext,
    onSwipedRight: handlePrev,
    trackMouse: true,
  });

  const leftIndex = selectedIndex - 1 >= 0 ? selectedIndex - 1 : null;
  const centerIndex = selectedIndex;
  const rightIndex = selectedIndex + 1 < backgrounds.length ? selectedIndex + 1 : null;

  const handleImageClick = (index: number) => {
    setSelectedIndex(index);
  };

  return (
    <Box {...swipeHandlers} display="flex" alignItems="center" mt={2}>
      <IconButton onClick={handlePrev} disabled={selectedIndex === 0}>
        <ArrowBackIosIcon />
      </IconButton>

      <Box display="flex" gap={1}>
        {leftIndex !== null && (
          <Paper
            sx={{
              width: 150,
              height: 150,
              overflow: "hidden",
              cursor: "pointer",
            }}
            onClick={() => handleImageClick(leftIndex)}
          >
            <BackgroundImage
              token={token}
              backgroundId={backgrounds[leftIndex].background_id}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </Paper>
        )}

        <Paper
          sx={{
            width: 180,
            height: 180,
            overflow: "hidden",
            border: "4px solid #1976d2",
            transition: "transform 0.3s",
            transform: "scale(1.2)",
            cursor: "pointer",
          }}
          onClick={() => handleImageClick(centerIndex)}
        >
          {backgrounds[centerIndex] && (
            <BackgroundImage
              token={token}
              backgroundId={backgrounds[centerIndex].background_id}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          )}
        </Paper>

        {rightIndex !== null && (
          <Paper
            sx={{
              width: 150,
              height: 150,
              overflow: "hidden",
              cursor: "pointer",
            }}
            onClick={() => handleImageClick(rightIndex)}
          >
            <BackgroundImage
              token={token}
              backgroundId={backgrounds[rightIndex].background_id}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </Paper>
        )}
      </Box>

      <IconButton
        onClick={handleNext}
        disabled={selectedIndex === backgrounds.length - 1}
      >
        <ArrowForwardIosIcon />
      </IconButton>
    </Box>
  );
};

export default BackgroundSlider;
