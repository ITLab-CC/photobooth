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
import qrCode from '../assets/qr_code.png';

interface DisclaimerModalProps {
  open: boolean;
  onAccept: () => void;
}

export default function DisclaimerModal({ open, onAccept }: DisclaimerModalProps) {
  const [checked, setChecked] = useState(false);

  return (
    <Dialog open={open} disableEscapeKeyDown>
      <DialogTitle>Datenschutzhinweis</DialogTitle>
      <DialogContent>
        <Typography variant="body1">
          Bevor es losgeht: Bitte schau dir unsere <u>Datenschutzhinweise</u> an und stimme ihnen zu, um fortzufahren.<br/><br/>
          👉 Dein Name wird nicht gespeichert.<br/>
          👉 Deine Bilder werden nach 7 Tagen automatisch gelöscht.<br/>
          👉 Der Zugriff auf die Bilder ist nur über den geschützten QR-Code auf dem Papierfoto und deinen persönlichen PIN möglich.<br/><br />
          Wenn du mehr wissen willst, scanne den QR-Code für alle weiteren Infos zum Datenschutz.
        </Typography>
        <img 
          src={qrCode} 
          alt="QR Code" 
          style={{ display: 'block', margin: '20px auto', maxWidth: '200px' }} 
        />
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
