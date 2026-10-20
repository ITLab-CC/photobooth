import { brand } from "../theme";
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
                    border: selectedCount === count ? `3px solid ${brand.teal}` : `1px solid ${brand.line}`,
                    borderRadius: 2,
                    transition: "all 0.2s ease",
                    backgroundColor: selectedCount === count ? brand.tealTint : "#ffffff",
                    '&:hover': {
                      backgroundColor: selectedCount === count ? brand.tealTint : brand.surface,
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
                          color: "text.secondary",
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
                      color: selectedCount === count ? "primary.main" : "text.primary",
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
            fontWeight: 600,
            minHeight: 72,
            borderRadius: 2,
          }}
        >
          Drucken
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PrintCountModal;
