import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Button,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  IconButton,
  AlertColor,
  Alert,
  Paper,
  TextField,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  listPrintJobs,
  deletePrintJob,
  clearPrintQueue,
  getMedia,
  setMediaCapacity,
  resetMedia,
  MediaResponse,
  PrintResponse,
} from "../../api";
import LazyGalleryThumbnail from "../LazyGalleryThumbnail";

interface PrintQueuePanelProps {
  token: string;
  showMessage: (message: string, severity?: AlertColor) => void;
}

const PrintQueuePanel: React.FC<PrintQueuePanelProps> = ({ token, showMessage }) => {
  const [jobs, setJobs] = useState<PrintResponse[]>([]);
  const [media, setMedia] = useState<MediaResponse | null>(null);
  const [capacityInput, setCapacityInput] = useState("");

  const refresh = (silent = false) => {
    listPrintJobs(token)
      .then(setJobs)
      .catch(() => {
        if (!silent) showMessage("Fehler beim Laden der Druckwarteschlange", "error");
      });
  };

  const loadMedia = () =>
    getMedia(token)
      .then((res) => {
        setMedia(res);
        setCapacityInput(String(res.capacity));
      })
      .catch(() => showMessage("Fehler beim Laden des Papierzählers", "error"));

  useEffect(() => {
    if (token) loadMedia();
  }, [token]);

  const handleCapacitySave = async () => {
    const capacity = parseInt(capacityInput, 10);
    if (Number.isNaN(capacity) || capacity < 10 || capacity > 5000) {
      showMessage("Bitte eine Zahl zwischen 10 und 5000 eingeben", "warning");
      return;
    }
    try {
      setMedia(await setMediaCapacity(token, capacity));
      showMessage("Kapazität gespeichert.");
    } catch {
      showMessage("Speichern fehlgeschlagen", "error");
    }
  };

  const handleRollChanged = async () => {
    if (!window.confirm("Neue Rolle eingelegt? Der Zähler startet bei 0.")) return;
    try {
      setMedia(await resetMedia(token));
      showMessage("Zähler zurückgesetzt.");
    } catch {
      showMessage("Zurücksetzen fehlgeschlagen", "error");
    }
  };

  // Neue Aufträge und gedruckte Aufträge sollen ohne Neuladen sichtbar werden.
  useEffect(() => {
    if (!token) return;
    refresh();
    const timer = setInterval(() => refresh(true), 5000);
    return () => clearInterval(timer);
  }, [token]);

  const handleDelete = async (printId: string) => {
    try {
      await deletePrintJob(token, printId);
      setJobs((prev) => prev.filter((j) => j.id !== printId));
    } catch {
      showMessage("Fehler beim Entfernen des Druckauftrags", "error");
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm("Gesamte Druckwarteschlange leeren?")) return;
    try {
      await clearPrintQueue(token);
      setJobs([]);
      showMessage("Druckwarteschlange geleert.");
    } catch {
      showMessage("Fehler beim Leeren der Druckwarteschlange", "error");
    }
  };

  return (
    <Box>
      {media && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Papier und Folie
          </Typography>
          {media.low && (
            <Alert severity="warning" sx={{ mb: 1.5 }}>
              Die Rolle ist bald leer: noch etwa {media.remaining} Drucke.
            </Alert>
          )}
          <Typography variant="body2" sx={{ mb: 1.5 }}>
            {media.count} Drucke seit dem letzten Rollenwechsel, noch etwa {media.remaining} von {media.capacity}.
            Gezählt wird, wenn ein Druck angefordert wird; fehlgeschlagene Drucke zählen mit.
          </Typography>
          <Box sx={{ display: "flex", gap: 1.5, alignItems: "center", flexWrap: "wrap" }}>
            <TextField
              size="small"
              label="Drucke pro Rolle"
              type="number"
              value={capacityInput}
              onChange={(e) => setCapacityInput(e.target.value)}
              sx={{ width: 180 }}
            />
            <Button variant="outlined" onClick={handleCapacitySave}>
              Speichern
            </Button>
            <Button variant="contained" onClick={handleRollChanged}>
              Rolle gewechselt
            </Button>
          </Box>
        </Paper>
      )}

      <Box sx={{ mb: 2 }}>
        <Button variant="outlined" color="error" onClick={handleClearAll} disabled={jobs.length === 0}>
          Warteschlange leeren
        </Button>
      </Box>

      {jobs.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", py: 4 }}>
          Keine Druckaufträge in der Warteschlange.
        </Typography>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Bild</TableCell>
              <TableCell>Anzahl</TableCell>
              <TableCell>Erstellt</TableCell>
              <TableCell align="right">Aktion</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {jobs.map((job) => (
              <TableRow key={job.id}>
                <TableCell>
                  <LazyGalleryThumbnail token={token} imageId={job.img_id} loadImmediately />
                </TableCell>
                <TableCell>{job.number}</TableCell>
                <TableCell>{new Date(job.created_at).toLocaleString()}</TableCell>
                <TableCell align="right">
                  <IconButton size="small" color="error" onClick={() => handleDelete(job.id)}>
                    <DeleteIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Box>
  );
};

export default PrintQueuePanel;
