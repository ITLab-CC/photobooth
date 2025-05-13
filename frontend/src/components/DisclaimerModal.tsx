import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Checkbox,
  FormControlLabel,
} from '@mui/material';

interface DisclaimerModalProps {
  open: boolean;
  onAccept: () => void;
}

export default function DisclaimerModal({ open, onAccept }: DisclaimerModalProps) {
  const [checked, setChecked] = useState(false);

  return (
    <Dialog open={open} disableEscapeKeyDown>
      <DialogTitle>Deine ENTEGA Fotobox!</DialogTitle>
      <DialogContent>
        <Typography variant="body1">
        Dein Foto wird nur kurz verarbeitet - direkt nach dem Druck wird es gelöscht 🗑️.
        Alles passiert lokal auf der Fotobox - keine Speicherung, kein Upload, kein Stress 🔒.
        </Typography>
        <FormControlLabel
          control={
            <Checkbox
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              name="agree"
              color="primary"
            />
          }
          label="Ich stimme den Bedingungen zu."
        />
      </DialogContent>
      <DialogActions>
        <Button variant="contained" onClick={onAccept} disabled={!checked}>
          Zustimmen
        </Button>
      </DialogActions>
    </Dialog>
  );
}
