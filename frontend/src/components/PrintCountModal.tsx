import React from "react";
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
        Anzahl der Drucke wählen
      </DialogTitle>
      <DialogContent>
        <Typography variant="body1" sx={{ textAlign: "center", mb: 3 }}>
          Wie viele Bilder möchten Sie drucken?
        </Typography>
        <Box sx={{ width: 260, mx: "auto" }}>
          <Grid container spacing={2} justifyContent="center">
            {[1, 2, 3].map((count) => (
              <Grid item xs={4} key={count}>
                <Button
                  variant="contained"
                  onClick={() => onSubmit(count)}
                  fullWidth
                  sx={{
                    borderRadius: "50%",
                    width: 80,
                    height: 80,
                    minWidth: 0,
                    padding: 0,
                    fontSize: "2rem",
                    fontWeight: "bold",
                    background: `linear-gradient(45deg, ${count === 1 ? "#e3f2fd, #bbdefb" : count === 2 ? "#e8f5e9, #c8e6c9" : "#fff3e0, #ffe0b2"})`,
                    color: "black",
                    boxShadow: 3,
                    '&:hover': {
                      background: `linear-gradient(45deg, ${count === 1 ? "#bbdefb, #90caf9" : count === 2 ? "#c8e6c9, #a5d6a7" : "#ffe0b2, #ffcc80"})`,
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
          variant="outlined"
          onClick={onCancel}
          sx={{
            fontSize: "1rem",
            py: 1,
          }}
        >
          Abbrechen
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PrintCountModal;
