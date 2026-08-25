import React, { useEffect, useRef, useState } from "react";
import { Box, Typography, Button, Paper, IconButton, AlertColor } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  createBackground,
  listBackgrounds,
  deleteBackground,
  BackgroundResponse,
} from "../../api";
import BackgroundImage from "../BackgroundImage";

interface BackgroundsPanelProps {
  token: string;
  showMessage: (message: string, severity?: AlertColor) => void;
}

const BackgroundsPanel: React.FC<BackgroundsPanelProps> = ({ token, showMessage }) => {
  const [backgroundFile, setBackgroundFile] = useState<File | null>(null);
  const backgroundInputRef = useRef<HTMLInputElement>(null);
  const [backgrounds, setBackgrounds] = useState<BackgroundResponse[]>([]);

  useEffect(() => {
    if (token) {
      listBackgrounds(token)
        .then((res) => setBackgrounds(res.backgrounds))
        .catch(() => showMessage("Fehler beim Laden der Hintergründe", "error"));
    }
  }, [token]);

  const handleBackgroundButtonClick = () => {
    backgroundInputRef.current?.click();
  };

  const handleBackgroundUpload = () => {
    if (!backgroundFile) return;
    const reader = new FileReader();
    reader.onload = async () => {
      const base64 = (reader.result as string).replace(/^data:image\/[a-z]+;base64,/, "");
      try {
        await createBackground(token, base64);
        showMessage("Hintergrund erfolgreich hochgeladen");
        setBackgroundFile(null);
        const res = await listBackgrounds(token);
        setBackgrounds(res.backgrounds);
      } catch (err) {
        console.error(err);
        showMessage("Hintergrund-Upload fehlgeschlagen", "error");
      }
    };
    reader.readAsDataURL(backgroundFile);
  };

  const handleDeleteBackground = async (backgroundId: string) => {
    if (!window.confirm("Hintergrund wirklich löschen?")) return;
    try {
      await deleteBackground(token, backgroundId);
      setBackgrounds((prev) => prev.filter((bg) => bg.background_id !== backgroundId));
    } catch {
      showMessage("Fehler beim Löschen des Hintergrunds", "error");
    }
  };

  return (
    <Box sx={{ maxWidth: 480 }}>
      <Box sx={{ textAlign: "center", mb: 3 }}>
        <Button variant="contained" onClick={handleBackgroundButtonClick}>
          Datei auswählen
        </Button>
        <input
          type="file"
          accept="image/*"
          ref={backgroundInputRef}
          style={{ display: "none" }}
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              setBackgroundFile(e.target.files[0]);
            }
          }}
        />
        {backgroundFile && (
          <Button variant="contained" onClick={handleBackgroundUpload} sx={{ mt: 1, ml: 1 }}>
            Hochladen
          </Button>
        )}
      </Box>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {backgrounds.map((bg, index) => (
          <Paper
            key={bg.background_id}
            sx={{ p: 1, display: "flex", alignItems: "center", justifyContent: "space-between" }}
          >
            <BackgroundImage
              token={token}
              backgroundId={bg.background_id}
              style={{ width: 100, height: 60, borderRadius: 4, objectFit: "cover" }}
            />
            <Typography variant="body2" sx={{ ml: 1, flexGrow: 1 }}>
              Hintergrund {index + 1}
            </Typography>
            <IconButton size="small" color="error" onClick={() => handleDeleteBackground(bg.background_id)}>
              <DeleteIcon />
            </IconButton>
          </Paper>
        ))}
        {backgrounds.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", py: 2 }}>
            Keine Hintergründe vorhanden.
          </Typography>
        )}
      </Box>
    </Box>
  );
};

export default BackgroundsPanel;
