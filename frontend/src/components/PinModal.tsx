import React, { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Grid,
  Box,
  Typography,
} from "@mui/material";
import BackspaceIcon from "@mui/icons-material/Backspace";
import LockIcon from "@mui/icons-material/Lock";
import LockOpenIcon from "@mui/icons-material/LockOpen";

interface PinModalProps {
  open: boolean;
  onSubmit: (pin: string) => Promise<void> | void;
  onCancel: () => void;
}

const PinModal: React.FC<PinModalProps> = ({ open, onSubmit, onCancel }) => {
  const [pin, setPin] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const handleDigitClick = (digit: string) => {
    if (pin.length < 4) {
      setPin((prev) => prev + digit);
      setErrorMessage("");
    }
  };

  const handleBackspace = () => {
    setPin((prev) => prev.slice(0, -1));
    setErrorMessage("");
  };

  const isPinValid = () => /^\d{4}$/.test(pin);

  const handleConfirm = async () => {
    if (isPinValid()) {
      try {
        await onSubmit(pin);
        setPin("");
        setErrorMessage("");
      } catch (err: any) {
        setErrorMessage(err.message || "Falscher PIN. Bitte erneut versuchen.");
      }
    } else {
      setErrorMessage("Bitte geben Sie einen gültigen 4-stelligen PIN ein.");
    }
  };

  return (
    <Dialog
      open={open}
      onClose={(_event, reason) => {
        if (reason === "backdropClick" || reason === "escapeKeyDown") return;
        onCancel();
      }}
      maxWidth="xs"
      fullWidth
      disableEscapeKeyDown
      PaperProps={{
        sx: {
          background: "linear-gradient(45deg, #ffffff, #f0f0f0)",
          boxShadow: 3,
          p: 2,
        },
      }}
    >
      <DialogTitle sx={{ textAlign: "center", fontWeight: "bold" }}>
        PIN Eingabe
      </DialogTitle>
      <DialogContent>
        <Box
          sx={{
            mb: 2,
            textAlign: "center",
            fontSize: "2rem",
            display: "flex",
            justifyContent: "center",
            gap: 1,
          }}
        >
          {[0, 1, 2, 3].map((index) =>
            index < pin.length ? (
              <LockIcon key={index} fontSize="inherit" />
            ) : (
              <LockOpenIcon key={index} fontSize="inherit" />
            )
          )}
        </Box>
        {errorMessage && (
          <Typography variant="body2" color="error" sx={{ textAlign: "center", mb: 1 }}>
            {errorMessage}
          </Typography>
        )}
        <Box sx={{ width: 260, mx: "auto" }}>
          <Grid container spacing={1}>
            {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((digit) => (
              <Grid item xs={4} key={digit}>
                <Button
                  variant="contained"
                  onClick={() => handleDigitClick(digit)}
                  fullWidth
                  sx={{
                    borderRadius: "50%",
                    width: 80,
                    height: 80,
                    minWidth: 0,
                    padding: 0,
                    fontSize: "1.8rem",
                    background: "linear-gradient(45deg, #ffffff, #e0e0e0)",
                    color: "black",
                    boxShadow: 3,
                  }}
                >
                  {digit}
                </Button>
              </Grid>
            ))}
            <Grid item xs={4}>
              <Box sx={{ width: 80, height: 80 }} />
            </Grid>
            <Grid item xs={4}>
              <Button
                variant="contained"
                onClick={() => handleDigitClick("0")}
                fullWidth
                sx={{
                  borderRadius: "50%",
                  width: 80,
                  height: 80,
                  minWidth: 0,
                  padding: 0,
                  fontSize: "1.8rem",
                  background: "linear-gradient(45deg, #ffffff, #e0e0e0)",
                  color: "black",
                  boxShadow: 3,
                }}
              >
                0
              </Button>
            </Grid>
            <Grid item xs={4}>
              <Button
                variant="contained"
                onClick={handleBackspace}
                fullWidth
                sx={{
                  borderRadius: "50%",
                  width: 80,
                  height: 80,
                  minWidth: 0,
                  padding: 0,
                  background: "linear-gradient(45deg, #ffffff, #e0e0e0)",
                  color: "black",
                  boxShadow: 3,
                }}
              >
                <BackspaceIcon fontSize="large" />
              </Button>
            </Grid>
          </Grid>
        </Box>
      </DialogContent>
      <DialogActions sx={{ justifyContent: "center", p: 2 }}>
        <Button
          variant="contained"
          fullWidth
          onClick={handleConfirm}
          disabled={!isPinValid()}
          sx={{
            fontSize: "1.4rem",
            py: 1.5,
            background: "linear-gradient(45deg, #ffffff, #e0e0e0)",
            color: "black",
          }}
        >
          Bestätigen
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PinModal;
