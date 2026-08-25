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
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import { listPrintJobs, deletePrintJob, clearPrintQueue, PrintResponse } from "../../api";
import LazyGalleryThumbnail from "../LazyGalleryThumbnail";

interface PrintQueuePanelProps {
  token: string;
  showMessage: (message: string, severity?: AlertColor) => void;
}

const PrintQueuePanel: React.FC<PrintQueuePanelProps> = ({ token, showMessage }) => {
  const [jobs, setJobs] = useState<PrintResponse[]>([]);

  const refresh = () => {
    listPrintJobs(token)
      .then(setJobs)
      .catch(() => showMessage("Fehler beim Laden der Druckwarteschlange", "error"));
  };

  useEffect(() => {
    if (token) refresh();
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
