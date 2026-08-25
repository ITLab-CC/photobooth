import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Slider,
  TextField,
  Grid,
  AlertColor,
} from "@mui/material";
import {
  createFrame,
  updateFrame,
  getFrame,
  FrameResponse,
  FrameCrop,
  FrameOffset,
} from "../../api";

// Canvas render size cap, purely for preview performance — the true
// background_scale/offset/crop values below stay in the frame's native
// pixel space and are converted to this preview scale only when drawing.
const MAX_CANVAS_WIDTH = 440;

interface FrameEditorProps {
  open: boolean;
  token: string;
  frame: FrameResponse | null; // null = creating a new frame
  newFrameBase64: string | null; // set when creating a new frame
  backgroundSampleUrl: string | null; // sample photo shown behind the frame
  onClose: () => void;
  onSaved: () => void;
  showMessage: (message: string, severity?: AlertColor) => void;
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

const FrameEditor: React.FC<FrameEditorProps> = ({
  open,
  token,
  frame,
  newFrameBase64,
  backgroundSampleUrl,
  onClose,
  onSaved,
  showMessage,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameImgRef = useRef<HTMLImageElement | null>(null);
  const bgImgRef = useRef<HTMLImageElement | null>(null);
  const dragStateRef = useRef<{ startX: number; startY: number; startOffset: FrameOffset } | null>(null);

  const [imagesReady, setImagesReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [previewScale, setPreviewScale] = useState(1);

  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState<FrameOffset>([0, 0]);
  const [crop, setCrop] = useState<FrameCrop>([0, 0, 0, 0]);

  // Load frame + sample background images, and seed draft state from the
  // frame being edited (or defaults for a brand-new frame).
  useEffect(() => {
    if (!open) return;
    setImagesReady(false);

    setScale(frame?.background_scale ?? 1);
    setOffset(frame?.background_offset ?? [0, 0]);
    setCrop(frame?.background_crop ?? [0, 0, 0, 0]);

    const frameSrc = newFrameBase64
      ? `data:image/png;base64,${newFrameBase64}`
      : null;

    const loadFrameImg = frameSrc
      ? loadImage(frameSrc)
      : frame
      ? getFrame(token, frame.frame_id).then((blob) => loadImage(URL.createObjectURL(blob)))
      : Promise.reject(new Error("Kein Frame-Bild verfügbar"));

    const loadBgImg = backgroundSampleUrl
      ? loadImage(backgroundSampleUrl)
      : Promise.resolve(null);

    Promise.all([loadFrameImg, loadBgImg])
      .then(([frameImg, bgImg]) => {
        frameImgRef.current = frameImg;
        bgImgRef.current = bgImg;
        const scaleFactor = Math.min(1, MAX_CANVAS_WIDTH / frameImg.naturalWidth);
        setPreviewScale(scaleFactor);
        setImagesReady(true);
      })
      .catch((err) => {
        console.error("Fehler beim Laden der Editor-Bilder:", err);
        showMessage("Frame oder Beispielbild konnte nicht geladen werden.", "error");
      });
  }, [open, frame, newFrameBase64, backgroundSampleUrl, token]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const frameImg = frameImgRef.current;
    if (!canvas || !frameImg || !imagesReady) return;

    const width = Math.round(frameImg.naturalWidth * previewScale);
    const height = Math.round(frameImg.naturalHeight * previewScale);
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, width, height);

    const bgImg = bgImgRef.current;
    if (bgImg) {
      const [cropTop, cropRight, cropLeft, cropBottom] = crop;
      const scaledBgWidth = bgImg.naturalWidth * scale;
      const scaledBgHeight = bgImg.naturalHeight * scale;

      // Source rect in the background's own native pixel space.
      const sx = cropLeft / scale;
      const sy = cropTop / scale;
      const sw = Math.max(1, (scaledBgWidth - cropLeft - cropRight) / scale);
      const sh = Math.max(1, (scaledBgHeight - cropTop - cropBottom) / scale);

      // Dest rect in preview-canvas pixel space.
      const dx = offset[0] * previewScale;
      const dy = offset[1] * previewScale;
      const dw = Math.max(1, (scaledBgWidth - cropLeft - cropRight) * previewScale);
      const dh = Math.max(1, (scaledBgHeight - cropTop - cropBottom) * previewScale);

      try {
        ctx.drawImage(bgImg, sx, sy, sw, sh, dx, dy, dw, dh);
      } catch {
        // Out-of-range crop/scale combos can produce invalid source rects while dragging — skip that frame.
      }
    }

    ctx.drawImage(frameImg, 0, 0, width, height);
  }, [scale, offset, crop, previewScale, imagesReady]);

  useEffect(() => {
    draw();
  }, [draw]);

  const handlePointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    (e.target as HTMLCanvasElement).setPointerCapture(e.pointerId);
    dragStateRef.current = { startX: e.clientX, startY: e.clientY, startOffset: offset };
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const drag = dragStateRef.current;
    if (!drag) return;
    const deltaX = (e.clientX - drag.startX) / previewScale;
    const deltaY = (e.clientY - drag.startY) / previewScale;
    setOffset([Math.round(drag.startOffset[0] + deltaX), Math.round(drag.startOffset[1] + deltaY)]);
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLCanvasElement>) => {
    (e.target as HTMLCanvasElement).releasePointerCapture(e.pointerId);
    dragStateRef.current = null;
  };

  const handleCropChange = (index: number, value: string) => {
    const num = Math.max(0, Number(value) || 0);
    setCrop((prev) => {
      const next: FrameCrop = [...prev];
      next[index] = num;
      return next;
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (frame) {
        await updateFrame(token, frame.frame_id, {
          background_scale: scale,
          background_offset: offset,
          background_crop: crop,
          qr_position: frame.qr_position,
          qr_scale: frame.qr_scale,
        });
        showMessage("Ausrichtung gespeichert.");
      } else if (newFrameBase64) {
        await createFrame(token, newFrameBase64, {
          background_scale: scale,
          background_offset: offset,
          background_crop: crop,
        });
        showMessage("Frame erfolgreich hochgeladen.");
      }
      onSaved();
    } catch (err) {
      console.error("Fehler beim Speichern des Frames:", err);
      showMessage("Speichern fehlgeschlagen.", "error");
    } finally {
      setSaving(false);
    }
  };

  const cropLabels = ["Oben", "Rechts", "Links", "Unten"];

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{frame ? "Ausrichtung bearbeiten" : "Neuer Frame"}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", justifyContent: "center", mb: 3 }}>
          <canvas
            ref={canvasRef}
            style={{
              border: "1px solid #ddd",
              borderRadius: 4,
              touchAction: "none",
              cursor: imagesReady ? "grab" : "default",
              maxWidth: "100%",
            }}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
          />
        </Box>

        {!backgroundSampleUrl && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, textAlign: "center" }}>
            Kein Beispielbild vorhanden — lade zuerst einen Hintergrund hoch, um die Vorschau zu sehen.
          </Typography>
        )}

        <Typography variant="body2" gutterBottom>
          Skalierung ({scale.toFixed(2)}x)
        </Typography>
        <Slider
          value={scale}
          min={0.1}
          max={3}
          step={0.01}
          onChange={(_e, value) => setScale(value as number)}
          sx={{ mb: 2 }}
        />

        <Typography variant="body2" gutterBottom>
          Position (per Drag auf dem Bild verschieben): x={offset[0]}, y={offset[1]}
        </Typography>

        <Typography variant="body2" sx={{ mt: 2, mb: 1 }}>
          Zuschnitt (Pixel)
        </Typography>
        <Grid container spacing={1}>
          {cropLabels.map((label, index) => (
            <Grid item xs={3} key={label}>
              <TextField
                label={label}
                type="number"
                size="small"
                fullWidth
                value={crop[index]}
                onChange={(e) => handleCropChange(index, e.target.value)}
              />
            </Grid>
          ))}
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          Abbrechen
        </Button>
        <Button variant="contained" onClick={handleSave} disabled={saving || !imagesReady}>
          Speichern
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default FrameEditor;
