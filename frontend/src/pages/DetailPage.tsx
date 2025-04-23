import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  getGalleryImagesByPin,
  GalleryImageListResponse,
  deleteGalleryWithPin,
} from "../api";
import {
  Box,
  Typography,
  Grid,
  Snackbar,
  Alert,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
} from "@mui/material";
import PinModal from "../components/PinModal";
import itlabLogo from "../assets/it-lab-banner.svg";
import DownloadIcon from "@mui/icons-material/Download";

const DetailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const galleryId = searchParams.get("id");

  // Pin-Modal
  const [pinModalOpen, setPinModalOpen] = useState<boolean>(true);
  const [pin, setPin] = useState<string>("");

  // Bilderliste
  const [images, setImages] = useState<string[]>([]);

  // Notification (Snackbar)
  const [notificationOpen, setNotificationOpen] = useState<boolean>(false);
  const [notificationMessage, setNotificationMessage] = useState<string>("");

  // Lösch-Dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState<boolean>(false);

  // ------------------------------------
  // Bilder abrufen
  // ------------------------------------
  const fetchImages = (galleryId: string, enteredPin: string) => {
    getGalleryImagesByPin(galleryId, enteredPin)
      .then((res: GalleryImageListResponse) => {
        const urls = res.images.map(
          (imgObj) =>
            `${window.location.origin}/api/v1/gallery/${galleryId}/image/${imgObj.image_id}/pin/${enteredPin}`
        );
        setImages(urls);
        setNotificationMessage("");
        setPinModalOpen(false);
      })
      .catch((error) => {
        // Falls Backend einen Statuscode 404 sendet, existiert die Galerie nicht
        if (error?.response?.status === 404) {
          window.location.href =
            "https://www.entega.ag/karriere/ausbildung-duales-studium-berufsorientierung/ausbildung/";
        } else {
          // Bei allen anderen Fehlern (z.B. falscher PIN) Fehlermeldung ausgeben
          setNotificationMessage("Falscher PIN. Bitte noch einmal versuchen.");
          setNotificationOpen(true);
          // Das Modal wieder öffnen, damit man den PIN erneut eingeben kann
          setPinModalOpen(true);
        }
      });
  };

  // ------------------------------------
  // PIN aus PinModal verarbeiten
  // ------------------------------------
  const handlePinSubmit = (enteredPin: string) => {
    // Prüfen, ob PIN eine 4-stellige Zahl ist
    if (galleryId && enteredPin.length === 4 && /^\d{4}$/.test(enteredPin)) {
      setPin(enteredPin);
      fetchImages(galleryId, enteredPin);
    } else {
      setNotificationMessage("Bitte geben Sie einen gültigen 4-stelligen PIN ein.");
      setNotificationOpen(true);
    }
  };

  // ------------------------------------
  // Galerie via PIN löschen
  // ------------------------------------
  const handleGalleryDelete = async () => {
    if (!galleryId || !pin) return;
    try {
      await deleteGalleryWithPin(galleryId, pin);
      // Nach dem Löschen weiterleiten
      window.location.href =
        "https://www.entega.ag/karriere/ausbildung-duales-studium-berufsorientierung/ausbildung/";
    } catch (error: any) {
      setNotificationMessage(error.message || "Fehler beim Löschen.");
      setNotificationOpen(true);
    } finally {
      setDeleteDialogOpen(false);
    }
  };

  // ------------------------------------
  // Falls keine galleryId -> Hinweis
  // ------------------------------------
  if (!galleryId) {
    return (
      <Box p={2}>
        <Typography variant="body1">
          Bitte geben Sie eine Galerie-ID in der URL an (z.B. ?id=GAL-...).
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #f2ac25, #96234b)",
        p: 3,
        fontFamily: "'Poppins', sans-serif",
        position: "relative",
      }}
    >
      <Box sx={{ textAlign: "center", mb: 3 }}>
        <Typography
          variant="h3"
          sx={{
            color: "white",
            textShadow: "2px 2px 4px black",
          }}
        >
          Nacht der Ausbildung bei der Entega
        </Typography>
      </Box>

      {notificationMessage && (
        <Snackbar
          open={notificationOpen}
          autoHideDuration={5000}
          onClose={() => setNotificationOpen(false)}
        >
          <Alert
            onClose={() => setNotificationOpen(false)}
            severity="error"
            sx={{ width: "100%" }}
          >
            {notificationMessage}
          </Alert>
        </Snackbar>
      )}

      {/* Bilder Grid */}
      {images.length > 0 ? (
        <Grid container spacing={2}>
          {images.map((url, idx) => (
            <Grid item xs={12} sm={6} md={6} key={idx}>
              <Box sx={{ position: "relative" }}>
                <Box
                  component="img"
                  src={url}
                  alt={`Bild ${idx + 1}`}
                  sx={{
                    width: "100%",
                    height: 400,
                    objectFit: "cover",
                    borderRadius: 2,
                    boxShadow: 3,
                  }}
                />
                {/* Download-Button als Overlay (rechts unten) */}
                <Box
                  component="a"
                  href={url}
                  download={`gallery_${galleryId}_image_${idx + 1}.png`}
                  sx={{
                    position: "absolute",
                    bottom: 8,
                    right: 8,
                  }}
                >
                  <IconButton
                    sx={{
                      color: "white",
                      backgroundColor: "rgba(0, 0, 0, 0.5)",
                      "&:hover": {
                        backgroundColor: "rgba(0, 0, 0, 0.7)",
                      },
                    }}
                  >
                    <DownloadIcon />
                  </IconButton>
                </Box>
              </Box>
            </Grid>
          ))}
        </Grid>
      ) : (
        // Nur anzeigen, wenn Modal NICHT offen ist, um "Keine Bilder gefunden" nicht sofort anzuzeigen,
        // während man noch keinen PIN eingegeben hat
        !pinModalOpen && (
          <Typography variant="body1" sx={{ textAlign: "center", color: "white" }}>
            Keine Bilder gefunden.
          </Typography>
        )
      )}

      {/* Modal zum PIN-Eingeben (beim Initialaufruf) */}
      <PinModal
        open={pinModalOpen}
        onSubmit={handlePinSubmit}
        onCancel={() => setPinModalOpen(true)}
      />

      {/* Button zum Löschen der Bilder (unten im Layout) */}
      {images.length > 0 && (
        <Box sx={{ textAlign: "center", mt: 4 }}>
          <Button
            variant="contained"
            color="error"
            onClick={() => setDeleteDialogOpen(true)}
          >
            Meine Bilder löschen
          </Button>
        </Box>
      )}

      {/* Bestätigungsdialog zum Löschen */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Galerie löschen?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Möchten Sie wirklich alle Ihre Bilder löschen? Dieser Vorgang kann nicht
            rückgängig gemacht werden.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} color="primary">
            Abbrechen
          </Button>
          <Button onClick={handleGalleryDelete} color="error">
            Ja, löschen
          </Button>
        </DialogActions>
      </Dialog>

      {/* IT-Lab Logo (fixiert rechts unten) */}
      <Box
        component="img"
        src={itlabLogo}
        alt="Itlab Logo"
        sx={{
          position: "fixed",
          bottom: 16,
          right: 16,
          width: 250,
          opacity: 0.8,
        }}
      />
    </Box>
  );
};

export default DetailPage;
