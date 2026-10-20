import React, { useEffect, useState } from "react";
import { Box, Button, CircularProgress, Paper, Typography, AlertColor } from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import { getHealth, runSelfTest, HealthCheck, HealthResponse, SelfTestResponse } from "../../api";

interface OverviewPanelProps {
  token: string;
  showMessage: (message: string, severity?: AlertColor) => void;
}

const REFRESH_MS = 10000;

const StatusCard: React.FC<{ title: string; check: HealthCheck }> = ({ title, check }) => (
  <Paper sx={{ p: 2, display: "flex", alignItems: "center", gap: 1.5 }}>
    {check.ok ? <CheckCircleIcon color="success" /> : <ErrorIcon color="error" />}
    <Box>
      <Typography variant="subtitle2">{title}</Typography>
      <Typography variant="body2" color="text.secondary">
        {check.detail}
      </Typography>
    </Box>
  </Paper>
);

const Counter: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <Paper sx={{ p: 2, textAlign: "center" }}>
    <Typography variant="h4">{value}</Typography>
    <Typography variant="body2" color="text.secondary">
      {label}
    </Typography>
  </Paper>
);

const OverviewPanel: React.FC<OverviewPanelProps> = ({ token, showMessage }) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [failed, setFailed] = useState(false);
  const [selfTest, setSelfTest] = useState<SelfTestResponse | null>(null);
  const [testing, setTesting] = useState(false);

  const handleSelfTest = async () => {
    setTesting(true);
    setSelfTest(null);
    try {
      setSelfTest(await runSelfTest(token));
    } catch {
      showMessage("Der Selbsttest konnte nicht ausgeführt werden", "error");
    } finally {
      setTesting(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      getHealth(token)
        .then((res) => {
          if (!cancelled) {
            setHealth(res);
            setFailed(false);
          }
        })
        .catch(() => {
          if (!cancelled) {
            setFailed(true);
          }
        });

    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [token]);

  useEffect(() => {
    if (failed) {
      showMessage("Status konnte nicht geladen werden. Läuft der Server?", "error");
    }
  }, [failed]);

  if (!health) return null;

  const magicShare = health.photos_today > 0 ? Math.round((health.magic_photos_today / health.photos_today) * 100) : 0;

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 1 }}>
        Status
      </Typography>
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 2, mb: 4 }}>
        <StatusCard title="Datenbank" check={health.database} />
        <StatusCard title="Grafikkarte" check={health.gpu} />
        <StatusCard title="KI-Modell" check={health.model} />
        <StatusCard title="Speicherplatz" check={health.disk} />
        <StatusCard title="Druckwarteschlange" check={health.print_queue} />
        <StatusCard title="Papier und Folie" check={health.media} />
      </Box>

      <Typography variant="h6" sx={{ mb: 1 }}>
        Selbsttest
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        Prüft vor dem Event die ganze Kette mit einem erzeugten Testbild: Datenbank, Freisteller, Gesichtserkennung,
        Rahmen, Hintergründe und Papier. Dauert einige Sekunden.
      </Typography>
      <Button variant="contained" onClick={handleSelfTest} disabled={testing} sx={{ mb: 2 }}>
        {testing ? <CircularProgress size={22} color="inherit" /> : "Selbsttest starten"}
      </Button>
      {selfTest && (
        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 2, mb: 4 }}>
          {selfTest.checks.map((check) => (
            <StatusCard
              key={check.name}
              title={`${check.name} (${check.seconds} s)`}
              check={{ ok: check.ok, detail: check.detail }}
            />
          ))}
        </Box>
      )}
      {!selfTest && <Box sx={{ mb: 4 }} />}

      <Typography variant="h6" sx={{ mb: 1 }}>
        Heute
      </Typography>
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 2 }}>
        <Counter label="Fotos seit Serverstart" value={String(health.photos_today)} />
        <Counter label="davon mit Magic" value={`${magicShare} %`} />
        <Counter
          label="Ø KI-Verarbeitung"
          value={health.avg_processing_seconds === null ? "–" : `${health.avg_processing_seconds} s`}
        />
        <Counter
          label="Hintergründe sichtbar"
          value={`${health.backgrounds_active}/${health.backgrounds_total}`}
        />
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
        Die Zahlen werden nur gezählt, es werden keine Fotos dafür gespeichert. Aktualisiert sich alle 10 Sekunden.
      </Typography>
    </Box>
  );
};

export default OverviewPanel;
