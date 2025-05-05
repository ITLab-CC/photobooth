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

interface PrintCountModalProps {
  open: boolean;
  onSubmit: (count: number) => Promise<void> | void;
  onCancel: () => void;
}

const PrintCountModal: React.FC<PrintCountModalProps> = ({ open, onSubmit, onCancel }) => {
  const [selectedCount, setSelectedCount] = useState<number>(1);

  const handleCountSelect = (count: number) => {
    setSelectedCount(count);
  };

  const handleConfirm = async () => {
    try {
      await onSubmit(selectedCount);
    } catch (err: any) {
      console.error("Fehler beim Drucken:", err);
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
        Anzahl der Drucke auswählen
      </DialogTitle>
      <DialogContent>
        <Typography variant="body1" sx={{ textAlign: "center", mb: 3 }}>
          Wie viele Exemplare möchtest Du drucken?
        </Typography>
        <Box sx={{ width: "100%", mx: "auto" }}>
          <Grid container spacing={2} justifyContent="center">
            {[1, 2, 3].map((count) => (
              <Grid item xs={4} key={count}>
                <Button
                  variant={selectedCount === count ? "contained" : "outlined"}
                  onClick={() => handleCountSelect(count)}
                  fullWidth
                  sx={{
                    height: 80,
                    fontSize: "2rem",
                    backgroundColor: selectedCount === count ? "#4caf50" : undefined,
                    '&:hover': {
                      backgroundColor: selectedCount === count ? "#388e3c" : undefined,
                    }
                  }}
                >
                  {count}
                </Button>
              </Grid>
            ))}
          </Grid>
        </Box>
      </DialogContent>
      <DialogActions sx={{ justifyContent: "center", p: 2 }}>
        <Button
          variant="contained"
          fullWidth
          onClick={handleConfirm}
          sx={{
            fontSize: "1.4rem",
            py: 1.5,
            background: "linear-gradient(45deg,rgb(255, 255, 255),rgb(204, 204, 204))",
            color: "black",
          }}
        >
          Drucken
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PrintCountModal;
