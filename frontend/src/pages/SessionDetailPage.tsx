import React, { useState, useEffect } from "react";
import { Container, Box, Typography, Grid, Snackbar } from "@mui/material";
import { useParams } from "react-router-dom";
import AuthenticatedImage from "../components/AuthenticatedImage";
import ShareAllButton from "../components/ShareAllButton";

interface ImageData {
  id: string;
  name: string;
  description: string;
  url: string;
  gallery_id?: string;
}

const SessionDetailPage: React.FC = () => {
  const { galleryId } = useParams<{ galleryId: string }>();
  const authToken = localStorage.getItem("authToken") || "";
  const [images, setImages] = useState<ImageData[]>([]);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [error, setError] = useState<string>("");

  const fetchSessionImages = async () => {
    if (!authToken || !galleryId) return;
    try {
      const response = await fetch("http://localhost:8000/api/v1/images", {
        headers: { Authorization: authToken },
      });
      if (response.ok) {
        const data = await response.json();
        const sessionImages = data.images
          .filter((img: ImageData) => img.gallery_id === galleryId)
          .map((img: ImageData) => ({
            ...img,
            url: `http://localhost:8000${img.url}`,
          }));
        setImages(sessionImages);
        setError("");
      } else {
        setError("Fehler beim Laden der Bilder.");
      }
    } catch (err) {
      setError("Fehler beim Laden der Bilder.");
    }
  };

  useEffect(() => {
    fetchSessionImages();
  }, [authToken, galleryId]);

  return (
    <Container
      maxWidth={false}
      disableGutters
      sx={{
        width: "100vw",
        minHeight: "100vh",
        background: "linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%)",
        py: 4,
      }}
    >
      <Typography
        variant="h4"
        align="center"
        gutterBottom
        sx={{ color: "#333" }}
      >
        Session #{galleryId}
      </Typography>
      {error && (
        <Typography variant="body1" color="error" align="center">
          {error}
        </Typography>
      )}
      {images.length === 0 ? (
        <Typography variant="body1" align="center">
          Keine Bilder in dieser Session.
        </Typography>
      ) : (
        <Grid container spacing={2} sx={{ px: 2 }}>
          {images.map((img) => (
            <Grid item xs={12} sm={6} md={4} key={img.id}>
              <Box
                sx={{
                  border: "1px solid #ccc",
                  borderRadius: 1,
                  p: 1,
                  backgroundColor: "rgba(255,255,255,0.9)",
                }}
              >
                <AuthenticatedImage
                  src={img.url}
                  authToken={authToken}
                  alt={img.name}
                />
                <Typography variant="subtitle1">{img.name}</Typography>
                <Typography variant="body2">{img.description}</Typography>
              </Box>
            </Grid>
          ))}
        </Grid>
      )}
      <Box sx={{ textAlign: "center", mt: 2 }}>
        <ShareAllButton
          images={images.map((img) => ({ url: img.url, name: img.name }))}
          authToken={authToken}
        />
      </Box>
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={() => setSnackbarOpen(false)}
        message="Share erfolgreich gestartet"
      />
    </Container>
  );
};

export default SessionDetailPage;
