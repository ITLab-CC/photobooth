import React, { useEffect, useRef, useState } from "react";
import {
  Alert,
  AlertColor,
  Avatar,
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  IconButton,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  addFace,
  deleteFace,
  getFaceThumb,
  listFaces,
  renameFace,
  FaceListResponse,
} from "../../api";

interface FacesPanelProps {
  token: string;
  showMessage: (message: string, severity?: AlertColor) => void;
}

const fileToBase64 = (file: File): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve((reader.result as string).replace(/^data:image\/[a-z+.-]+;base64,/, ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });

const FaceThumb: React.FC<{ token: string; faceId: string }> = ({ token, faceId }) => {
  const [url, setUrl] = useState<string | undefined>();
  useEffect(() => {
    let objectUrl: string | undefined;
    getFaceThumb(token, faceId)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => setUrl(undefined));
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [token, faceId]);
  return <Avatar src={url} variant="rounded" sx={{ width: 72, height: 72 }} />;
};

const FacesPanel: React.FC<FacesPanelProps> = ({ token, showMessage }) => {
  const [data, setData] = useState<FaceListResponse | null>(null);
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const reload = () =>
    listFaces(token)
      .then(setData)
      .catch(() => showMessage("Fehler beim Laden der Gesichter", "error"));

  useEffect(() => {
    if (!token) return;
    reload();
    // While the models are still downloading, check again every few seconds.
    const timer = setInterval(() => {
      listFaces(token).then(setData).catch(() => undefined);
    }, 8000);
    return () => clearInterval(timer);
  }, [token]);

  const handleAdd = async () => {
    if (!file || !name.trim() || !consent) return;
    setSaving(true);
    try {
      await addFace(token, name.trim(), await fileToBase64(file), consent);
      showMessage(`"${name.trim()}" wurde hinzugefügt. Das Foto selbst wurde nicht gespeichert.`);
      setName("");
      setFile(null);
      setConsent(false);
      await reload();
    } catch (err) {
      const text = err instanceof Error ? err.message : "";
      // The server's explanation (no face, several faces, ...) comes after the request description.
      const detail = text.match(/"detail":"([^"]+)"/)?.[1];
      showMessage(detail ?? "Das Gesicht konnte nicht hinzugefügt werden", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleRename = async (faceId: string, current: string, value: string) => {
    const next = value.trim();
    if (!next || next === current) return;
    try {
      await renameFace(token, faceId, next);
      await reload();
    } catch {
      showMessage("Name konnte nicht geändert werden", "error");
    }
  };

  const handleDelete = async (faceId: string, faceName: string) => {
    if (!window.confirm(`"${faceName}" endgültig löschen?`)) return;
    try {
      await deleteFace(token, faceId);
      await reload();
    } catch {
      showMessage("Löschen fehlgeschlagen", "error");
    }
  };

  if (!data) return null;

  return (
    <Box sx={{ maxWidth: 640 }}>
      <Typography variant="body1" sx={{ mb: 2 }}>
        Hier legst du Gesichter fest, die als Magic-Auswahl auf der Fotobox erscheinen. Die Gesichter aller Gäste im Bild
        werden dann durch dieses Gesicht ersetzt. Blick, Kopfhaltung und Mimik bleiben die des Gastes.
      </Typography>

      {!data.models_ready && (
        <Alert severity={data.download_error ? "error" : "info"} sx={{ mb: 2 }}>
          {data.download_error
            ? `Die Modelle konnten nicht geladen werden: ${data.download_error}`
            : "Die Modelle für den Gesichtstausch werden geladen (etwa 700 MB). Danach geht es hier weiter."}
        </Alert>
      )}

      <Alert severity="warning" sx={{ mb: 3 }}>
        Nur mit Einverständnis der abgebildeten Person. Das Foto wird nach dem Hinzufügen verworfen, gespeichert werden
        nur die Gesichtsdaten und ein kleines Vorschaubild auf diesem Server. Das verwendete Modell (InsightFace
        inswapper) ist nur für nicht-kommerzielle Forschung freigegeben, also zum Testen.
      </Alert>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle1" sx={{ mb: 1.5 }}>
          Gesicht hinzufügen
        </Typography>
        <TextField
          label="Name auf der Fotobox (zum Beispiel Chef)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          fullWidth
          sx={{ mb: 1.5 }}
        />
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1 }}>
          <Button variant="outlined" onClick={() => inputRef.current?.click()}>
            Foto auswählen
          </Button>
          <Typography variant="body2" color="text.secondary">
            {file ? file.name : "Ein Foto mit nur einer Person, Gesicht gut sichtbar und von vorn."}
          </Typography>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            style={{ display: "none" }}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) setFile(e.target.files[0]);
              e.target.value = "";
            }}
          />
        </Box>
        <FormControlLabel
          control={<Checkbox checked={consent} onChange={(e) => setConsent(e.target.checked)} />}
          label="Die Person im Foto ist einverstanden, dass ihr Gesicht auf Gäste gesetzt und ausgedruckt wird."
          sx={{ mb: 1 }}
        />
        <Box>
          <Button
            variant="contained"
            onClick={handleAdd}
            disabled={saving || !file || !name.trim() || !consent || !data.models_ready}
          >
            Hinzufügen
          </Button>
        </Box>
      </Paper>

      <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
        {data.faces.map((face) => (
          <Paper key={face.face_id} sx={{ p: 1, display: "flex", alignItems: "center", gap: 1.5 }}>
            <FaceThumb token={token} faceId={face.face_id} />
            <TextField
              size="small"
              variant="standard"
              defaultValue={face.name}
              key={`${face.face_id}-${face.name}`}
              onBlur={(e) => handleRename(face.face_id, face.name, e.target.value)}
              sx={{ flexGrow: 1 }}
            />
            <IconButton color="error" onClick={() => handleDelete(face.face_id, face.name)} aria-label="Löschen">
              <DeleteIcon />
            </IconButton>
          </Paper>
        ))}
        {data.faces.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", py: 2 }}>
            Noch keine Gesichter hinzugefügt.
          </Typography>
        )}
      </Box>
    </Box>
  );
};

export default FacesPanel;
