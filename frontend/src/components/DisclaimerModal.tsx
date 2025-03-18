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
      <DialogTitle>Hinweis</DialogTitle>
      <DialogContent>
        <Typography variant="body1">
          Bitte lesen Sie die Nutzungsbedingungen und Datenschutzhinweise. Um fortzufahren,
          müssen Sie diesen zustimmen.
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
