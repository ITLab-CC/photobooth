import React, { useEffect, useRef, useState } from "react";
import {
  Box,
  TextField,
  Button,
  AlertColor,
  Stack,
  Typography,
  Switch,
  FormControlLabel,
  Paper,
  ToggleButton,
  ToggleButtonGroup,
} from "@mui/material";
import {
  getEventConfig,
  updateEventConfig,
  uploadEventLogo,
  deleteEventLogo,
  getEventLogo,
  listProfiles,
  saveProfile,
  applyProfile,
  deleteProfile,
  EventConfigResponse,
  ProfileResponse,
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
  const [profiles, setProfiles] = useState<ProfileResponse[]>([]);
  const [profileName, setProfileName] = useState("");

  const loadProfiles = () =>
    listProfiles(token)
      .then((res) => setProfiles(res.profiles))
      .catch(() => showMessage("Fehler beim Laden der Profile", "error"));

  const reloadSettings = () =>
    getEventConfig(token).then((res) => {
      setConfig(res);
      loadLogo(res.has_logo);
    });

  const handleSaveProfile = async () => {
    const name = profileName.trim();
    if (!name) return;
    try {
      await saveProfile(token, name);
      setProfileName("");
      showMessage(`Profil "${name}" gespeichert.`);
      await loadProfiles();
    } catch {
      showMessage("Profil konnte nicht gespeichert werden", "error");
    }
  };

  const handleApplyProfile = async (profile: ProfileResponse) => {
    if (!window.confirm(`Profil "${profile.name}" anwenden? Texte, Limits, sichtbare Hintergründe und Rahmen werden umgestellt.`)) return;
    try {
      await applyProfile(token, profile.profile_id);
      await reloadSettings();
      showMessage(`Profil "${profile.name}" ist aktiv. Die Fotobox übernimmt es beim nächsten Neuladen.`);
    } catch {
      showMessage("Profil konnte nicht angewendet werden", "error");
    }
  };

  const handleDeleteProfile = async (profile: ProfileResponse) => {
    if (!window.confirm(`Profil "${profile.name}" löschen?`)) return;
    try {
      await deleteProfile(token, profile.profile_id);
      await loadProfiles();
    } catch {
      showMessage("Löschen fehlgeschlagen", "error");
    }
  };

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
    loadProfiles();
  }, [token]);

  const updateField = (field: TextField_, value: string) => {
    setConfig((prev) => (prev ? { ...prev, [field]: value } : prev));
  };

  // Number fields keep the last valid value while the admin is typing.
  const updateNumber = (
    field: "max_prints" | "series_count" | "countdown_seconds",
    value: string,
    min: number,
    max: number
  ) => {
    const parsed = parseInt(value, 10);
    if (Number.isNaN(parsed)) return;
    setConfig((prev) => (prev ? { ...prev, [field]: Math.min(max, Math.max(min, parsed)) } : prev));
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
      showMessage("Logo entfernt.");
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
        <TextField
          label="Fotos pro Serie"
          type="number"
          value={config.series_count}
          onChange={(e) => updateNumber("series_count", e.target.value, 1, 5)}
          slotProps={{ htmlInput: { min: 1, max: 5 } }}
          helperText="So viele Fotos nimmt die Fotobox hintereinander auf, die Gäste wählen das beste. Bei 1 gibt es keine Auswahl."
          fullWidth
        />
        <TextField
          label="Countdown vor dem Foto (Sekunden)"
          type="number"
          value={config.countdown_seconds}
          onChange={(e) => updateNumber("countdown_seconds", e.target.value, 2, 10)}
          slotProps={{ htmlInput: { min: 2, max: 10 } }}
          helperText="Mehr Zeit zum Aufstellen für große Gruppen. Die weiteren Fotos einer Serie zählen eine Sekunde weniger."
          fullWidth
        />
        <TextField
          label="Abzüge pro Foto (Maximum)"
          type="number"
          value={config.max_prints}
          onChange={(e) => updateNumber("max_prints", e.target.value, 1, 10)}
          slotProps={{ htmlInput: { min: 1, max: 10 } }}
          helperText="So viele Exemplare eines Fotos können Gäste höchstens drucken. Bei 1 entfällt die Auswahl."
          fullWidth
        />
        <Box>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            Personen im Bild
          </Typography>
          <ToggleButtonGroup
            exclusive
            size="small"
            value={config.subject_anchor}
            onChange={(_e, value) => value && setConfig((prev) => (prev ? { ...prev, subject_anchor: value } : prev))}
            aria-label="Position der Personen"
          >
            <ToggleButton value="bottom">Unten (stehen auf dem Rand)</ToggleButton>
            <ToggleButton value="center">In der Mitte</ToggleButton>
          </ToggleButtonGroup>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
            Bei "Unten" stehen die Personen auf dem unteren Rand des Fotos, wer unten vom Kamerabild abgeschnitten ist,
            läuft aus dem Bild. Bei "Mitte" schweben sie mit Abstand nach allen Seiten.
          </Typography>
        </Box>
        <FormControlLabel
          control={
            <Switch
              checked={config.sound_enabled}
              onChange={(e) => setConfig((prev) => (prev ? { ...prev, sound_enabled: e.target.checked } : prev))}
            />
          }
          label="Töne (Countdown und Auslöser)"
        />
        <Box>
          <Button variant="contained" onClick={handleSave} disabled={saving}>
            Speichern
          </Button>
        </Box>

        <Box sx={{ pt: 2, borderTop: 1, borderColor: "divider" }}>
          <Typography variant="subtitle1" sx={{ mb: 0.5 }}>
            Event-Profile
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            Ein Profil merkt sich Texte, Limits, die sichtbaren Hintergründe und den aktiven Rahmen. Einrichten, speichern,
            beim nächsten Event mit einem Klick wieder anwenden. Das Logo gehört nicht zum Profil.
          </Typography>
          <Stack spacing={1} sx={{ mb: 1.5 }}>
            {profiles.map((profile) => (
              <Paper key={profile.profile_id} sx={{ p: 1.5, display: "flex", alignItems: "center", gap: 1 }}>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="body1">{profile.name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {profile.title}, {profile.backgrounds} Hintergründe{profile.has_frame ? ", mit Rahmen" : ""}
                  </Typography>
                </Box>
                <Button variant="contained" size="small" onClick={() => handleApplyProfile(profile)}>
                  Anwenden
                </Button>
                <Button variant="outlined" color="error" size="small" onClick={() => handleDeleteProfile(profile)}>
                  Löschen
                </Button>
              </Paper>
            ))}
            {profiles.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                Noch keine Profile gespeichert.
              </Typography>
            )}
          </Stack>
          <Box sx={{ display: "flex", gap: 1 }}>
            <TextField
              size="small"
              label="Name für den aktuellen Stand"
              value={profileName}
              onChange={(e) => setProfileName(e.target.value)}
              fullWidth
            />
            <Button variant="outlined" onClick={handleSaveProfile} disabled={!profileName.trim()}>
              Speichern
            </Button>
          </Box>
        </Box>

        <Box sx={{ pt: 2, borderTop: 1, borderColor: "divider" }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Zusätzliches Logo
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            Erscheint links unten neben dem IT-Lab-Logo, das immer sichtbar bleibt.
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
                Kein zusätzliches Logo
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
