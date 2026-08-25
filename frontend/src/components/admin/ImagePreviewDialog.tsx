import React from "react";
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Box } from "@mui/material";

interface ImagePreviewDialogProps {
  imageUrl: string | null;
  onClose: () => void;
}

const ImagePreviewDialog: React.FC<ImagePreviewDialogProps> = ({ imageUrl, onClose }) => {
  return (
    <Dialog open={!!imageUrl} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ textAlign: "center" }}>Bildvorschau</DialogTitle>
      <DialogContent sx={{ display: "flex", justifyContent: "center" }}>
        {imageUrl && (
          <Box
            component="img"
            src={imageUrl}
            alt="Vorschau"
            sx={{
              width: "100%",
              maxWidth: 800,
              objectFit: "contain",
            }}
          />
        )}
      </DialogContent>
      <DialogActions sx={{ justifyContent: "center" }}>
        <Button variant="contained" onClick={onClose}>
          Schließen
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ImagePreviewDialog;
