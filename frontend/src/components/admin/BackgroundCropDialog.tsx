import React, { useEffect, useState } from "react";
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Slider, Typography } from "@mui/material";
import { BackgroundResponse, FrameWindow, getBackground, getFrame, getFrameWindow, listFrames } from "../../api";

interface BackgroundCropDialogProps {
  open: boolean;
  token: string;
  background: BackgroundResponse | null;
  onClose: () => void;
  onSave: (focusX: number, focusY: number) => void;
}

const PREVIEW_WIDTH = 340;

/**
 * Shows the background inside the active frame, cut the way guests will get it, and lets the admin choose
 * which part stays visible when the picture is wider or taller than the frame's opening.
 */
const BackgroundCropDialog: React.FC<BackgroundCropDialogProps> = ({ open, token, background, onClose, onSave }) => {
  const [frameUrl, setFrameUrl] = useState<string | null>(null);
  const [window_, setWindow] = useState<FrameWindow | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null);
  const [focusX, setFocusX] = useState(0.5);
  const [focusY, setFocusY] = useState(0.5);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!open || !background) return;
    setFocusX(background.focus_x);
    setFocusY(background.focus_y);
    setError(false);
    let urls: string[] = [];
    (async () => {
      try {
        const frames = await listFrames(token);
        const active = frames.frames.find((f) => f.is_active) ?? frames.frames[0];
        if (!active) throw new Error("no frame");
        const [frameBlob, win, imageBlob] = await Promise.all([
          getFrame(token, active.frame_id),
          getFrameWindow(token, active.frame_id),
          getBackground(token, background.background_id, true),
        ]);
        const frame = URL.createObjectURL(frameBlob);
        const image = URL.createObjectURL(imageBlob);
        urls = [frame, image];
        const probe = new Image();
        probe.onload = () => setImageSize({ width: probe.naturalWidth, height: probe.naturalHeight });
        probe.src = image;
        setFrameUrl(frame);
        setImageUrl(image);
        setWindow(win);
      } catch {
        setError(true);
      }
    })();
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, [open, background, token]);

  // Which direction the picture overflows the opening decides which slider does anything.
  const overflow =
    imageSize && window_
      ? imageSize.width / imageSize.height > window_.aspect + 0.01
        ? "horizontal"
        : imageSize.width / imageSize.height < window_.aspect - 0.01
          ? "vertical"
          : "none"
      : null;

  const previewHeight = window_ ? (PREVIEW_WIDTH * window_.frame_height) / window_.frame_width : PREVIEW_WIDTH;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Bildausschnitt: {background?.name || "Hintergrund"}</DialogTitle>
      <DialogContent>
        {error && (
          <Typography color="error" variant="body2">
            Der aktive Frame oder das Bild konnte nicht geladen werden. Ist ein Frame aktiv gesetzt?
          </Typography>
        )}
        {!error && window_ && imageUrl && frameUrl && (
          <>
            <Box
              sx={{
                position: "relative",
                width: PREVIEW_WIDTH,
                height: previewHeight,
                mx: "auto",
                mb: 2,
                backgroundColor: "#ffffff",
                boxShadow: 2,
              }}
            >
              <Box
                sx={{
                  position: "absolute",
                  left: `${(window_.x / window_.frame_width) * 100}%`,
                  top: `${(window_.y / window_.frame_height) * 100}%`,
                  width: `${(window_.width / window_.frame_width) * 100}%`,
                  height: `${(window_.height / window_.frame_height) * 100}%`,
                  backgroundImage: `url(${imageUrl})`,
                  backgroundSize: "cover",
                  backgroundPosition: `${focusX * 100}% ${focusY * 100}%`,
                }}
              />
              <Box
                component="img"
                src={frameUrl}
                alt="Frame"
                sx={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
              />
            </Box>
            {overflow === "none" && (
              <Typography variant="body2" color="text.secondary">
                Das Bild hat genau die Form des Fensters, es wird nichts abgeschnitten.
              </Typography>
            )}
            {overflow === "horizontal" && (
              <>
                <Typography variant="body2" color="text.secondary">
                  Das Bild ist breiter als das Fenster. Wähle, welcher Teil sichtbar bleibt.
                </Typography>
                <Slider
                  value={focusX * 100}
                  onChange={(_e, value) => setFocusX((value as number) / 100)}
                  aria-label="Horizontal"
                  valueLabelDisplay="off"
                />
              </>
            )}
            {overflow === "vertical" && (
              <>
                <Typography variant="body2" color="text.secondary">
                  Das Bild ist höher als das Fenster. Wähle, welcher Teil sichtbar bleibt.
                </Typography>
                <Slider
                  value={focusY * 100}
                  onChange={(_e, value) => setFocusY((value as number) / 100)}
                  aria-label="Vertikal"
                  valueLabelDisplay="off"
                />
              </>
            )}
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
              Die Personen werden zusätzlich in das Fenster eingepasst. Hier siehst du nur den Hintergrund.
            </Typography>
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Abbrechen</Button>
        <Button variant="contained" onClick={() => onSave(focusX, focusY)} disabled={error || !window_}>
          Speichern
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default BackgroundCropDialog;
