import React, { useEffect, useState } from "react";
import { Box, IconButton, Typography } from "@mui/material";
import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import ArrowForwardIosIcon from "@mui/icons-material/ArrowForwardIos";
import BlockIcon from "@mui/icons-material/Block";
import { useSwipeable } from "react-swipeable";
import { listBackgrounds, BackgroundResponse } from "../api";
import OptimizedBackgroundImage from "./OptimizedBackgroundImage";
import { brand, px } from "../theme";

interface BackgroundSliderProps {
  token: string;
  onSelect?: (backgroundId: string | null) => void;
}

const SIDE_SIZE = px(120);
const CENTER_SIZE = px(170);

const arrowSx = {
  width: px(64),
  height: px(64),
  color: "text.primary",
  "&.Mui-disabled": { opacity: 0.25 },
};

const BackgroundSlider: React.FC<BackgroundSliderProps> = ({ token, onSelect }) => {
  const [backgrounds, setBackgrounds] = useState<BackgroundResponse[]>([]);
  // Index 0 and the last entry are empty slots, so the first real item can sit in the center.
  const paddedBackgrounds = [null, ...backgrounds, null];
  const [selectedIndex, setSelectedIndex] = useState<number>(0);

  useEffect(() => {
    listBackgrounds(token, true)
      .then((data) => {
        if (data.backgrounds && data.backgrounds.length > 0) {
          setBackgrounds(data.backgrounds);
        }
      })
      .catch((err) => {
        console.error("Fehler beim Laden der Hintergrundbilder:", err);
      });
  }, [token]);

  useEffect(() => {
    if (onSelect) {
      if (selectedIndex === 0) {
        onSelect(null);
      } else if (paddedBackgrounds[selectedIndex]) {
        onSelect(paddedBackgrounds[selectedIndex]!.background_id);
      }
    }
  }, [selectedIndex, paddedBackgrounds, onSelect]);

  const clampIndex = (index: number) => Math.max(0, Math.min(index, paddedBackgrounds.length - 2));
  const handlePrev = () => setSelectedIndex((prev) => clampIndex(prev - 1));
  const handleNext = () => setSelectedIndex((prev) => clampIndex(prev + 1));

  const swipeHandlers = useSwipeable({
    onSwipedLeft: handleNext,
    onSwipedRight: handlePrev,
    trackMouse: true,
  });

  const leftItem = paddedBackgrounds[selectedIndex - 1];
  const centerItem = paddedBackgrounds[selectedIndex];
  const rightItem = paddedBackgrounds[selectedIndex + 1];

  const centerName = centerItem
    ? centerItem.name || `Hintergrund ${selectedIndex}`
    : "Ohne Hintergrund (Original)";

  const sideTile = (item: BackgroundResponse, onClick: () => void) => (
    <OptimizedBackgroundImage
      token={token}
      backgroundId={item.background_id}
      onClick={onClick}
      style={{
        width: SIDE_SIZE,
        height: SIDE_SIZE,
        borderRadius: 12,
        objectFit: "cover",
        opacity: 0.7,
        cursor: "pointer",
      }}
    />
  );

  return (
    <Box {...swipeHandlers} sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1 }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 0.5 }}>
        <IconButton onClick={handlePrev} disabled={selectedIndex === 0} aria-label="Voriger Hintergrund" sx={arrowSx}>
          <ArrowBackIosNewIcon />
        </IconButton>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Box sx={{ width: SIDE_SIZE, height: SIDE_SIZE, display: "flex" }}>
            {leftItem && sideTile(leftItem, handlePrev)}
          </Box>

          <Box
            sx={{
              width: CENTER_SIZE,
              height: CENTER_SIZE,
              borderRadius: 3,
              border: `4px solid ${brand.teal}`,
              boxShadow: "0 6px 16px rgba(37, 43, 63, 0.18)",
              overflow: "hidden",
              backgroundColor: "background.paper",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {centerItem ? (
              <OptimizedBackgroundImage
                token={token}
                backgroundId={centerItem.background_id}
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            ) : (
              <Box sx={{ textAlign: "center", color: "text.secondary", px: 1 }}>
                <BlockIcon sx={{ fontSize: 44 }} />
                <Typography variant="body1">Original</Typography>
              </Box>
            )}
          </Box>

          <Box sx={{ width: SIDE_SIZE, height: SIDE_SIZE, display: "flex" }}>
            {rightItem && sideTile(rightItem, handleNext)}
          </Box>
        </Box>

        <IconButton
          onClick={handleNext}
          disabled={selectedIndex === paddedBackgrounds.length - 2}
          aria-label="Nächster Hintergrund"
          sx={arrowSx}
        >
          <ArrowForwardIosIcon />
        </IconButton>
      </Box>

      <Typography variant="h6" sx={{ minHeight: "1.6em", textAlign: "center" }}>
        {centerName}
      </Typography>
    </Box>
  );
};

export default BackgroundSlider;
