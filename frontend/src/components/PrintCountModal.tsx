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
  Paper,
} from "@mui/material";
import PrintIcon from "@mui/icons-material/Print";
import ImageIcon from "@mui/icons-material/Image";

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
          <Grid container spacing={3} justifyContent="center">
            {[1, 2, 3].map((count) => (
              <Grid item xs={4} key={count}>
                <Paper 
                  elevation={selectedCount === count ? 8 : 2}
                  onClick={() => handleCountSelect(count)}
                  sx={{
                    height: 120,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    border: selectedCount === count ? "2px solid #000000" : "1px solid #e0e0e0",
                    borderRadius: 2,
                    transition: "all 0.2s ease",
                    backgroundColor: selectedCount === count ? "rgba(0, 0, 0, 0.05)" : "#ffffff",
                    '&:hover': {
                      backgroundColor: selectedCount === count ? "rgba(0, 0, 0, 0.08)" : "#f5f5f5",
                      transform: "translateY(-2px)"
                    }
                  }}
                >
                  <Box sx={{ position: "relative", mb: 1 }}>
                    {Array(count).fill(0).map((_, i) => (
                      <ImageIcon 
                        key={i} 
                        sx={{ 
                          fontSize: "1.8rem", 
                          color: "#555",
                          position: "relative",
                          left: i * -5,
                          zIndex: 3 - i
                        }} 
                      />
                    ))}
                  </Box>
                  <Typography
                    variant="h4"
                    sx={{
                      fontWeight: 600,
                      color: selectedCount === count ? "#000000" : "#333",
                      fontFamily: "'Inter', sans-serif"
                    }}
                  >
                    {count}
                  </Typography>
                </Paper>
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
          startIcon={<PrintIcon sx={{ fontSize: "1.8rem" }} />}
          sx={{
            fontSize: "1.4rem",
            py: 1.5,
            backgroundColor: "#000000",
            color: "white",
            fontWeight: 500,
            borderRadius: 2,
            boxShadow: "0 4px 10px rgba(0, 0, 0, 0.25)",
            '&:hover': {
              backgroundColor: "#333333",
              boxShadow: "0 6px 12px rgba(0, 0, 0, 0.3)",
            }
          }}
        >
          Drucken
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PrintCountModal;
