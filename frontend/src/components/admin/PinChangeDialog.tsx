import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  Button,
  IconButton,
} from "@mui/material";
import BackspaceIcon from "@mui/icons-material/Backspace";

interface PinChangeDialogProps {
  open: boolean;
  pin: string;
  onPinChange: (pin: string) => void;
  onClose: () => void;
  onConfirm: () => void;
}

const PinChangeDialog: React.FC<PinChangeDialogProps> = ({
  open,
  pin,
  onPinChange,
  onClose,
  onConfirm,
}) => {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle sx={{ textAlign: "center" }}>PIN ändern</DialogTitle>
      <DialogContent>
        <TextField
          value={pin.replace(/./g, "•")}
          variant="outlined"
          fullWidth
          disabled
          sx={{ mb: 2, textAlign: "center" }}
        />
        <Grid container spacing={1}>
          {["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"].map((digit) => (
            <Grid item xs={4} key={digit}>
              <Button
                variant="outlined"
                fullWidth
                onClick={() => onPinChange(pin.length < 4 ? pin + digit : pin)}
                sx={{ fontSize: "1.2rem", padding: "0.5rem" }}
              >
                {digit}
              </Button>
            </Grid>
          ))}
          <Grid item xs={4}>
            <IconButton
              onClick={() => onPinChange(pin.slice(0, -1))}
              sx={{ fontSize: "1.2rem", padding: "0.25rem" }}
            >
              <BackspaceIcon />
            </IconButton>
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions sx={{ justifyContent: "center" }}>
        <Button
          variant="contained"
          onClick={onConfirm}
          disabled={!/^\d{4}$/.test(pin)}
          sx={{ fontSize: "0.9rem", px: 2 }}
        >
          Bestätigen
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PinChangeDialog;
