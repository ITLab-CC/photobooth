import React, { useEffect, useRef, useState } from "react";
import {
  Box,
  Typography,
  Paper,
  IconButton,
  AlertColor,
  Switch,
  TextField,
  LinearProgress,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import {
  createBackground,
  listBackgrounds,
  deleteBackground,
  updateBackground,
  BackgroundResponse,
} from "../../api";
import BackgroundImage from "../BackgroundImage";

interface BackgroundsPanelProps {
  token: string;
  showMessage: (message: string, severity?: AlertColor) => void;
}

// Das Backend erlaubt einen Upload pro Sekunde.
const UPLOAD_DELAY_MS = 1100;

const fileToBase64 = (file: File): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve((reader.result as string).replace(/^data:image\/[a-z+.-]+;base64,/, ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const BackgroundsPanel: React.FC<BackgroundsPanelProps> = ({ token, showMessage }) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [backgrounds, setBackgrounds] = useState<BackgroundResponse[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ done: number; total: number } | null>(null);

  const reload = async () => {
    try {
      const res = await listBackgrounds(token);
      setBackgrounds(res.backgrounds);
    } catch {
      showMessage("Fehler beim Laden der Hintergründe", "error");
    }
  };

  useEffect(() => {
    if (token) {
      reload();
    }
  }, [token]);

  const uploadFiles = async (files: File[]) => {
    const images = files.filter((file) => file.type.startsWith("image/"));
    if (images.length === 0) {
      showMessage("Bitte Bilddateien auswählen", "warning");
      return;
    }
    setUploadProgress({ done: 0, total: images.length });
    let failed = 0;
    for (let i = 0; i < images.length; i++) {
      try {
        const base64 = await fileToBase64(images[i]);
        const name = images[i].name.replace(/\.[^.]+$/, "");
        await createBackground(token, base64, name);
      } catch (err) {
        console.error(err);
        failed += 1;
      }
      setUploadProgress({ done: i + 1, total: images.length });
      if (i < images.length - 1) {
        await wait(UPLOAD_DELAY_MS);
      }
    }
    setUploadProgress(null);
    await reload();
    if (failed === 0) {
      showMessage(`${images.length} Hintergrund/Hintergründe hochgeladen`);
    } else {
      showMessage(`${failed} von ${images.length} Uploads fehlgeschlagen`, "error");
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    uploadFiles(Array.from(e.dataTransfer.files));
  };

  const patchBackground = async (backgroundId: string, patch: { name?: string; active?: boolean }) => {
    try {
      const updated = await updateBackground(token, backgroundId, patch);
      setBackgrounds((prev) => prev.map((bg) => (bg.background_id === backgroundId ? updated : bg)));
    } catch {
      showMessage("Änderung konnte nicht gespeichert werden", "error");
      reload();
    }
  };

  const handleDeleteBackground = async (backgroundId: string) => {
    if (!window.confirm("Hintergrund endgültig löschen? Zum Ausblenden reicht der Schalter.")) return;
    try {
      await deleteBackground(token, backgroundId);
      setBackgrounds((prev) => prev.filter((bg) => bg.background_id !== backgroundId));
    } catch {
      showMessage("Fehler beim Löschen des Hintergrunds", "error");
    }
  };

  const activeCount = backgrounds.filter((bg) => bg.active).length;

  return (
    <Box sx={{ maxWidth: 720 }}>
      <Box
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        sx={{
          border: "2px dashed",
          borderColor: dragOver ? "primary.main" : "divider",
          backgroundColor: dragOver ? "action.hover" : "transparent",
          borderRadius: 2,
          p: 3,
          mb: 3,
          textAlign: "center",
          cursor: "pointer",
        }}
      >
        <UploadFileIcon sx={{ fontSize: 40, color: "text.secondary" }} />
        <Typography variant="body1">Bilder hierher ziehen oder tippen zum Auswählen</Typography>
        <Typography variant="body2" color="text.secondary">
          Mehrere Dateien auf einmal sind möglich. Der Dateiname wird als Name übernommen.
        </Typography>
        <input
          type="file"
          accept="image/*"
          multiple
          ref={inputRef}
          style={{ display: "none" }}
          onChange={(e) => {
            if (e.target.files) {
              uploadFiles(Array.from(e.target.files));
              e.target.value = "";
            }
          }}
        />
      </Box>

      {uploadProgress && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            Lade hoch: {uploadProgress.done} von {uploadProgress.total}
          </Typography>
          <LinearProgress variant="determinate" value={(uploadProgress.done / uploadProgress.total) * 100} />
        </Box>
      )}

      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        {activeCount} von {backgrounds.length} Hintergründen sind für Gäste sichtbar.
      </Typography>

      <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
        {backgrounds.map((bg, index) => (
          <Paper
            key={bg.background_id}
            sx={{ p: 1, display: "flex", alignItems: "center", gap: 1.5, opacity: bg.active ? 1 : 0.55 }}
          >
            <BackgroundImage
              token={token}
              backgroundId={bg.background_id}
              style={{ width: 100, height: 60, borderRadius: 4, objectFit: "cover" }}
            />
            <TextField
              size="small"
              variant="standard"
              placeholder={`Hintergrund ${index + 1}`}
              defaultValue={bg.name}
              key={`${bg.background_id}-${bg.name}`}
              onBlur={(e) => {
                const name = e.target.value.trim();
                if (name !== bg.name) {
                  patchBackground(bg.background_id, { name });
                }
              }}
              sx={{ flexGrow: 1 }}
            />
            <Box sx={{ display: "flex", alignItems: "center" }}>
              <Typography variant="caption">{bg.active ? "Sichtbar" : "Ausgeblendet"}</Typography>
              <Switch
                checked={bg.active}
                onChange={(e) => patchBackground(bg.background_id, { active: e.target.checked })}
              />
            </Box>
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
