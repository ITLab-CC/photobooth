import React, { useEffect, useRef, useState } from "react";
import { Box, Typography, Button, Paper, IconButton, Chip, AlertColor } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { listFrames, deleteFrame, activateFrame, upscaleFrame, createFrame, FrameResponse } from "../../api";
import FrameImage from "../FrameImage";

interface FramesPanelProps {
  token: string;
  showMessage: (message: string, severity?: AlertColor) => void;
}

const FramesPanel: React.FC<FramesPanelProps> = ({ token, showMessage }) => {
  const [frames, setFrames] = useState<FrameResponse[]>([]);
  const frameInputRef = useRef<HTMLInputElement>(null);

  const refreshFrames = () => {
    listFrames(token)
      .then((res) => setFrames(res.frames))
      .catch(() => showMessage("Fehler beim Laden der Frames", "error"));
  };

  useEffect(() => {
    if (token) refreshFrames();
  }, [token]);

  const handleUploadClick = () => {
    frameInputRef.current?.click();
  };

  // The frame's opening decides where the photo goes, so a frame needs no alignment: upload and it is ready.
  const handleFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async () => {
      const base64 = (reader.result as string).replace(/^data:image\/[a-z+.-]+;base64,/, "");
      try {
        await createFrame(token, base64);
        refreshFrames();
        showMessage('Frame hochgeladen. Mit "Aktiv setzen" einschalten.');
      } catch {
        showMessage("Der Frame konnte nicht hochgeladen werden", "error");
      }
    };
    reader.readAsDataURL(file);
    e.target.value = "";
  };

  const handleDelete = async (frameId: string) => {
    if (!window.confirm("Frame wirklich löschen?")) return;
    try {
      await deleteFrame(token, frameId);
      setFrames((prev) => prev.filter((f) => f.frame_id !== frameId));
    } catch {
      showMessage("Fehler beim Löschen des Frames", "error");
    }
  };

  const handleActivate = async (frameId: string) => {
    try {
      await activateFrame(token, frameId);
      refreshFrames();
      showMessage("Frame als aktiv markiert.");
    } catch {
      showMessage("Fehler beim Aktivieren des Frames", "error");
    }
  };

  const handleUpscale = async (frame: FrameResponse, factor: number) => {
    const width = Math.round(frame.width * factor);
    const height = Math.round(frame.height * factor);
    if (
      !window.confirm(
        `Eine Kopie dieses Frames mit ${width} x ${height} Pixeln anlegen? Die Ausrichtung wird mit umgerechnet. ` +
          "Das Bild des Rahmens wird dabei nur hochgerechnet, scharfe Kanten und Schrift werden nicht schärfer. " +
          "Für das beste Ergebnis den Frame in dieser Größe neu exportieren und hochladen."
      )
    )
      return;
    try {
      await upscaleFrame(token, frame.frame_id, factor);
      refreshFrames();
      showMessage(`Kopie mit ${width} x ${height} Pixeln angelegt. Mit "Aktiv setzen" einschalten.`);
    } catch (err) {
      const detail = err instanceof Error ? err.message.match(/"detail":"([^"]+)"/)?.[1] : undefined;
      showMessage(detail ?? "Der Frame konnte nicht vergrößert werden", "error");
    }
  };

  return (
    <Box sx={{ maxWidth: 640 }}>
      <Box sx={{ mb: 3 }}>
        <Button variant="contained" onClick={handleUploadClick}>
          Neuen Frame hochladen
        </Button>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Der durchsichtige Bereich des Frames ist das Fenster für das Foto. Die Größe des Frames ist die Größe des
          fertigen Fotos.
        </Typography>
        <input
          type="file"
          accept="image/*"
          ref={frameInputRef}
          style={{ display: "none" }}
          onChange={handleFileSelected}
        />
      </Box>

      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {frames.map((f, index) => (
          <Paper
            key={f.frame_id}
            sx={{
              p: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              border: f.is_active ? "2px solid #000000" : "1px solid transparent",
            }}
          >
            <FrameImage
              token={token}
              frameId={f.frame_id}
              style={{ width: 80, height: 80, borderRadius: 4, objectFit: "contain", background: "#f5f5f5" }}
            />
            <Box sx={{ ml: 1, flexGrow: 1 }}>
              <Typography variant="body2">Frame {index + 1}</Typography>
              {f.width > 0 && (
                <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                  {f.width} x {f.height} Pixel (so groß wird das fertige Foto)
                </Typography>
              )}
              {f.is_active && (
                <Chip
                  icon={<CheckCircleIcon />}
                  label="Aktiv"
                  size="small"
                  sx={{ mt: 0.5 }}
                />
              )}
            </Box>
            {!f.is_active && (
              <Button size="small" onClick={() => handleActivate(f.frame_id)} sx={{ mr: 1 }}>
                Aktiv setzen
              </Button>
            )}
            <Button size="small" onClick={() => handleUpscale(f, 1.5)} sx={{ mr: 1 }}>
              Größer (×1,5)
            </Button>
            <IconButton size="small" color="error" onClick={() => handleDelete(f.frame_id)}>
              <DeleteIcon />
            </IconButton>
          </Paper>
        ))}
        {frames.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", py: 2 }}>
            Keine Frames vorhanden.
          </Typography>
        )}
      </Box>

    </Box>
  );
};

export default FramesPanel;
