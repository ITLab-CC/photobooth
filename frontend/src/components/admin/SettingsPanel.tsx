import React, { useEffect, useState } from "react";
import { Box, TextField, Button, AlertColor, Stack } from "@mui/material";
import { getEventConfig, updateEventConfig, EventConfigResponse } from "../../api";

interface SettingsPanelProps {
  token: string;
  showMessage: (message: string, severity?: AlertColor) => void;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({ token, showMessage }) => {
  const [config, setConfig] = useState<EventConfigResponse | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!token) return;
    getEventConfig(token)
      .then(setConfig)
      .catch(() => showMessage("Fehler beim Laden der Einstellungen", "error"));
  }, [token]);

  const updateField = (field: keyof EventConfigResponse, value: string) => {
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
          label="Redirect-URL bei falscher PIN"
          value={config.pin_fail_redirect_url}
          onChange={(e) => updateField("pin_fail_redirect_url", e.target.value)}
          fullWidth
        />
        <Box>
          <Button variant="contained" onClick={handleSave} disabled={saving}>
            Speichern
          </Button>
        </Box>
      </Stack>
    </Box>
  );
};

export default SettingsPanel;
