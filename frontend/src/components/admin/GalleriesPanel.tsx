import React, { useEffect, useState } from "react";
import { Box, Typography, Button, Grid, Paper } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import PushPinIcon from "@mui/icons-material/PushPin";
import PrintIcon from "@mui/icons-material/Print";
import {
  listGalleries,
  deleteGallery,
  updateGalleryPin,
  GalleryResponse,
  getImage,
  printImage,
} from "../../api";
import LazyGalleryThumbnail from "../LazyGalleryThumbnail";
import PinChangeDialog from "./PinChangeDialog";
import ImagePreviewDialog from "./ImagePreviewDialog";
import { AlertColor } from "@mui/material";

const getAdjustedDate = (dateString: string) => {
  const date = new Date(dateString);
  date.setHours(date.getHours() + 1);
  return date.toLocaleString();
};

interface GalleriesPanelProps {
  token: string;
  showMessage: (message: string, severity?: AlertColor) => void;
}

const GalleriesPanel: React.FC<GalleriesPanelProps> = ({ token, showMessage }) => {
  const [galleries, setGalleries] = useState<GalleryResponse[]>([]);
  const [pinModalOpen, setPinModalOpen] = useState<boolean>(false);
  const [selectedGallery, setSelectedGallery] = useState<GalleryResponse | null>(null);
  const [newPin, setNewPin] = useState("");
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      listGalleries(token)
        .then((res) => setGalleries(res.galleries))
        .catch(() => showMessage("Fehler beim Laden der Galerien", "error"));
    }
  }, [token]);

  const handleDeleteGallery = async (galleryId: string) => {
    if (!window.confirm("Galerie wirklich löschen?")) return;
    try {
      await deleteGallery(token, galleryId);
      setGalleries((prev) => prev.filter((g) => g.gallery_id !== galleryId));
    } catch {
      showMessage("Fehler beim Löschen der Galerie", "error");
    }
  };

  const openPinModal = (gallery: GalleryResponse) => {
    setSelectedGallery(gallery);
    setNewPin("");
    setPinModalOpen(true);
  };

  const handleUpdatePin = async () => {
    if (!(selectedGallery && newPin.length === 4 && /^\d{4}$/.test(newPin))) return;
    try {
      await updateGalleryPin(token, selectedGallery.gallery_id, newPin);
      showMessage("PIN geändert.");
      setPinModalOpen(false);
      setGalleries((prev) =>
        prev.map((g) =>
          g.gallery_id === selectedGallery.gallery_id ? { ...g, pin_set: true } : g
        )
      );
    } catch {
      showMessage("Fehler beim Ändern der PIN", "error");
    }
  };

  const handleThumbnailClick = async (imageId: string) => {
    try {
      const blob = await getImage(token, imageId);
      const url = URL.createObjectURL(blob);
      setPreviewImageUrl(url);
    } catch (err) {
      console.error("Fehler beim Laden des Bildes:", err);
    }
  };

  const closePreviewModal = () => {
    if (previewImageUrl) {
      URL.revokeObjectURL(previewImageUrl);
    }
    setPreviewImageUrl(null);
  };

  const handlePrintImage = (imageId: string) => {
    printImage(token, imageId)
      .then(() => {
        showMessage("Druckauftrag gesendet!");
      })
      .catch((err) => {
        console.error("Fehler beim Drucken:", err);
        showMessage("Fehler beim Drucken. Bitte versuche es erneut.", "error");
      });
  };

  return (
    <>
      <Grid container spacing={3}>
        {galleries.map((g) => (
          <Grid item xs={12} sm={6} md={4} key={g.gallery_id}>
            <Paper
              sx={{
                p: 2,
                mb: 2,
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                height: "100%",
              }}
            >
              <Box>
                <Typography variant="subtitle1" gutterBottom>
                  Galerie: {g.gallery_id}
                </Typography>
                <Typography variant="body2" gutterBottom>
                  Erzeugt: {getAdjustedDate(g.creation_time)}
                </Typography>
                {g.images && g.images.length > 0 ? (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2">Bilder:</Typography>
                    <Box sx={{ display: "flex", gap: 1, overflowX: "auto", pt: 1 }}>
                      {g.images.map((imgId, index) => (
                        <LazyGalleryThumbnail
                          key={imgId}
                          token={token}
                          imageId={imgId}
                          onClick={() => handleThumbnailClick(imgId)}
                          loadImmediately={index === 0}
                        />
                      ))}
                    </Box>
                  </Box>
                ) : (
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Keine Bilder
                  </Typography>
                )}
              </Box>
              <Box sx={{ mt: 2, mb: 1, display: "flex", gap: 1 }}>
                <Button
                  variant="outlined"
                  startIcon={<PrintIcon />}
                  size="small"
                  disabled={!g.images || g.images.length === 0}
                  onClick={() => handlePrintImage(g.images[g.images.length - 1])}
                  sx={{ borderRadius: 2, flex: 1 }}
                >
                  Drucken
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<PushPinIcon />}
                  size="small"
                  onClick={() => openPinModal(g)}
                  sx={{ borderRadius: 2, flex: 1 }}
                >
                  PIN ändern
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<DeleteIcon />}
                  size="small"
                  onClick={() => handleDeleteGallery(g.gallery_id)}
                  sx={{ borderRadius: 2, flex: 1 }}
                >
                  Löschen
                </Button>
              </Box>
            </Paper>
          </Grid>
        ))}
        {galleries.length === 0 && (
          <Grid item xs={12}>
            <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", py: 4 }}>
              Keine Galerien vorhanden.
            </Typography>
          </Grid>
        )}
      </Grid>

      <PinChangeDialog
        open={pinModalOpen}
        pin={newPin}
        onPinChange={setNewPin}
        onClose={() => setPinModalOpen(false)}
        onConfirm={handleUpdatePin}
      />

      <ImagePreviewDialog imageUrl={previewImageUrl} onClose={closePreviewModal} />
    </>
  );
};

export default GalleriesPanel;
