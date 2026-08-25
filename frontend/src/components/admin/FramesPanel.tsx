import React, { useEffect, useRef, useState } from "react";
import { Box, Typography, Button, Paper, IconButton, Chip, AlertColor } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import {
  listFrames,
  deleteFrame,
  activateFrame,
  listBackgrounds,
  getBackground,
  FrameResponse,
} from "../../api";
import FrameImage from "../FrameImage";
import FrameEditor from "./FrameEditor";

interface FramesPanelProps {
  token: string;
  showMessage: (message: string, severity?: AlertColor) => void;
}

const FramesPanel: React.FC<FramesPanelProps> = ({ token, showMessage }) => {
  const [frames, setFrames] = useState<FrameResponse[]>([]);
  const frameInputRef = useRef<HTMLInputElement>(null);
  const [backgroundSampleUrl, setBackgroundSampleUrl] = useState<string | null>(null);

  const [editorOpen, setEditorOpen] = useState(false);
  const [editingFrame, setEditingFrame] = useState<FrameResponse | null>(null);
  const [newFrameBase64, setNewFrameBase64] = useState<string | null>(null);

  const refreshFrames = () => {
    listFrames(token)
      .then((res) => setFrames(res.frames))
      .catch(() => showMessage("Fehler beim Laden der Frames", "error"));
  };

  useEffect(() => {
    if (token) refreshFrames();
  }, [token]);

  // Load one sample background (if any exist) so the editor has something to preview against.
  useEffect(() => {
    if (!token) return;
    listBackgrounds(token)
      .then((res) => {
        if (res.backgrounds.length === 0) return;
        return getBackground(token, res.backgrounds[0].background_id).then((blob) => {
          setBackgroundSampleUrl(URL.createObjectURL(blob));
        });
      })
      .catch(() => {
        // No sample available — the editor will just show the frame without a preview background.
      });
  }, [token]);

  const handleUploadClick = () => {
    frameInputRef.current?.click();
  };

  const handleFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = (reader.result as string).replace(/^data:image\/[a-z]+;base64,/, "");
      setNewFrameBase64(base64);
      setEditingFrame(null);
      setEditorOpen(true);
    };
    reader.readAsDataURL(file);
    e.target.value = "";
  };

  const handleEdit = (frame: FrameResponse) => {
    setEditingFrame(frame);
    setNewFrameBase64(null);
    setEditorOpen(true);
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

  const handleSaved = () => {
    setEditorOpen(false);
    refreshFrames();
  };

  return (
    <Box sx={{ maxWidth: 640 }}>
      <Box sx={{ mb: 3 }}>
        <Button variant="contained" onClick={handleUploadClick}>
          Neuen Frame hochladen
        </Button>
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
            <IconButton size="small" onClick={() => handleEdit(f)}>
              <EditIcon />
            </IconButton>
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

      <FrameEditor
        open={editorOpen}
        token={token}
        frame={editingFrame}
        newFrameBase64={newFrameBase64}
        backgroundSampleUrl={backgroundSampleUrl}
        onClose={() => setEditorOpen(false)}
        onSaved={handleSaved}
        showMessage={showMessage}
      />
    </Box>
  );
};

export default FramesPanel;
