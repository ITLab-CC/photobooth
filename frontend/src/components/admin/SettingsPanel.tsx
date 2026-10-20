import React, { useEffect, useRef, useState } from "react";
import { Box, TextField, Button, AlertColor, Stack, Typography } from "@mui/material";
import {
  getEventConfig,
  updateEventConfig,
  uploadEventLogo,
  deleteEventLogo,
  getEventLogo,
  EventConfigResponse,
} from "../../api";

interface SettingsPanelProps {
  token: string;
  showMessage: (message: string, severity?: AlertColor) => void;
}

type TextField_ = "title" | "subtitle" | "brand_name" | "start_text";

const SettingsPanel: React.FC<SettingsPanelProps> = ({ token, showMessage }) => {
  const [config, setConfig] = useState<EventConfigResponse | null>(null);
  const [saving, setSaving] = useState(false);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const logoInputRef = useRef<HTMLInputElement>(null);

  const loadLogo = async (hasLogo: boolean) => {
    if (!hasLogo) {
      setLogoUrl(null);
      return;
    }
    try {
      setLogoUrl(URL.createObjectURL(await getEventLogo(token)));
    } catch {
      setLogoUrl(null);
    }
  };

  useEffect(() => {
    if (!token) return;
    getEventConfig(token)
      .then((res) => {
        setConfig(res);
        loadLogo(res.has_logo);
      })
      .catch(() => showMessage("Fehler beim Laden der Einstellungen", "error"));
  }, [token]);

  const updateField = (field: TextField_, value: string) => {
    setConfig((prev) => (prev ? { ...prev, [field]: value } : prev));
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      const saved = await updateEventConfig(token, config);
      setConfig(saved);
      showMessage("Einstellungen gespeichert.");
    } catch {
      showMessage("Fehler beim Speichern der Einstellungen", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleLogoFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = async () => {
      const base64 = (reader.result as string).replace(/^data:image\/[a-z+.-]+;base64,/, "");
      try {
        const saved = await uploadEventLogo(token, base64);
        setConfig(saved);
        await loadLogo(saved.has_logo);
        showMessage("Logo gespeichert. Die Fotobox übernimmt es beim nächsten Neuladen.");
      } catch {
        showMessage("Logo konnte nicht hochgeladen werden", "error");
      }
    };
    reader.readAsDataURL(file);
  };

  const handleLogoRemove = async () => {
    try {
      const saved = await deleteEventLogo(token);
      setConfig(saved);
      setLogoUrl(null);
      showMessage("Logo entfernt, die Fotobox zeigt wieder das Standard-Logo.");
    } catch {
      showMessage("Logo konnte nicht entfernt werden", "error");
    }
  };

  if (!config) return null;

  return (
    <Box sx={{ maxWidth: 480 }}>
      <Stack spacing={2}>
        <TextField
          label="Titel"
          value={config.title}
          onChange={(e) => updateField("title", e.target.value)}
          fullWidth
        />
        <TextField
          label="Subtitel"
          value={config.subtitle}
          onChange={(e) => updateField("subtitle", e.target.value)}
          fullWidth
        />
        <TextField
          label="Marke"
          value={config.brand_name}
          onChange={(e) => updateField("brand_name", e.target.value)}
          fullWidth
        />
        <TextField
          label="Text auf dem Startbildschirm"
          value={config.start_text}
          onChange={(e) => updateField("start_text", e.target.value)}
          helperText="Steht unter dem Tipp-Symbol, bevor ein Gast startet."
          fullWidth
        />
        <Box>
          <Button variant="contained" onClick={handleSave} disabled={saving}>
            Speichern
          </Button>
        </Box>

        <Box sx={{ pt: 2, borderTop: 1, borderColor: "divider" }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Logo
          </Typography>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: 120,
              mb: 1.5,
              borderRadius: 1,
              backgroundColor: "action.hover",
            }}
          >
            {logoUrl ? (
              <img src={logoUrl} alt="Logo" style={{ maxHeight: 100, maxWidth: "100%" }} />
            ) : (
              <Typography variant="body2" color="text.secondary">
                Standard-Logo der Fotobox
              </Typography>
            )}
          </Box>
          <Stack direction="row" spacing={1}>
            <Button variant="outlined" onClick={() => logoInputRef.current?.click()}>
              Logo hochladen
            </Button>
            {config.has_logo && (
              <Button variant="outlined" color="error" onClick={handleLogoRemove}>
                Entfernen
              </Button>
            )}
          </Stack>
          <input
            type="file"
            accept="image/*"
            ref={logoInputRef}
            style={{ display: "none" }}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleLogoFile(e.target.files[0]);
                e.target.value = "";
              }
            }}
          />
        </Box>
      </Stack>
    </Box>
  );
};

export default SettingsPanel;
