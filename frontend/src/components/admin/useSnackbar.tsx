import { useState, useCallback } from "react";
import { Snackbar, Alert, AlertColor } from "@mui/material";

export interface SnackbarState {
  showMessage: (message: string, severity?: AlertColor) => void;
  SnackbarHost: React.FC;
}

export function useSnackbar(): SnackbarState {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [severity, setSeverity] = useState<AlertColor>("success");

  const showMessage = useCallback((msg: string, sev: AlertColor = "success") => {
    setMessage(msg);
    setSeverity(sev);
    setOpen(true);
  }, []);

  const SnackbarHost: React.FC = () => (
    <Snackbar
      open={open}
      autoHideDuration={4000}
      onClose={() => setOpen(false)}
      anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
    >
      <Alert onClose={() => setOpen(false)} severity={severity} sx={{ width: "100%" }}>
        {message}
      </Alert>
    </Snackbar>
  );

  return { showMessage, SnackbarHost };
}
