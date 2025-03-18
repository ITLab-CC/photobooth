import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getGalleryImagesByPin, GalleryImageListResponse } from "../api";
import { Box, Typography, Grid,  Snackbar, Alert, IconButton } from "@mui/material";
import PinModal from "../components/PinModal";
import itlabLogo from "../assets/it-lab-banner.svg";
import DownloadIcon from "@mui/icons-material/Download";

const DetailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const galleryId = searchParams.get("id");
  const [pinModalOpen, setPinModalOpen] = useState<boolean>(true);
  const [images, setImages] = useState<string[]>([]);
  const [notificationOpen, setNotificationOpen] = useState<boolean>(false);
  const [notificationMessage, setNotificationMessage] = useState<string>("");

  const fetchImages = (galleryId: string, pin: string) => {
    getGalleryImagesByPin(galleryId, pin)
      .then((res: GalleryImageListResponse) => {
        const urls = res.images.map((imgObj) =>
          `${window.location.origin}/api/v1/gallery/${galleryId}/image/${imgObj.image_id}/pin/${pin}`
        );
        setImages(urls);
        setNotificationMessage("");
        setPinModalOpen(false);
      })
      .catch(() => {
        window.location.href =
          "https://www.entega.ag/karriere/ausbildung-duales-studium-berufsorientierung/ausbildung/";
      });
  };

  const handlePinSubmit = (enteredPin: string) => {
    if (galleryId && enteredPin.length === 4 && /^\d{4}$/.test(enteredPin)) {
      fetchImages(galleryId, enteredPin);
    } else {
      setNotificationMessage("Bitte geben Sie einen gültigen 4-stelligen PIN ein.");
      setNotificationOpen(true);
    }
  };

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
          <Alert onClose={() => setNotificationOpen(false)} severity="error" sx={{ width: "100%" }}>
            {notificationMessage}
          </Alert>
        </Snackbar>
      )}

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
                    borderRadius: 2,
                    boxShadow: 3,
                  }}
                />
                <Box
                  component="a"
                  href={url}
                  download={`gallery_${galleryId}_image_${idx + 1}.png`}
                  sx={{
                    position: "absolute",
                    top: "50%",
                    left: "50%",
                    transform: "translate(-50%, -50%)",
                    textDecoration: "none",
                  }}
                >
                  <IconButton
                    sx={{
                      backgroundColor: "rgba(255,255,255,0.8)",
                      "&:hover": { backgroundColor: "rgba(255,255,255,0.9)" },
                    }}
                  >
                    <DownloadIcon fontSize="large" />
                  </IconButton>
                </Box>
              </Box>
            </Grid>
          ))}
        </Grid>
      ) : (
        !pinModalOpen && (
          <Typography variant="body1" sx={{ textAlign: "center", color: "white" }}>
            Keine Bilder gefunden.
          </Typography>
        )
      )}

      <PinModal
        open={pinModalOpen}
        onSubmit={handlePinSubmit}
        onCancel={() => setPinModalOpen(true)}
      />

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
