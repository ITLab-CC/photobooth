import React, { useState, useEffect } from "react";
import {
  Container,
  Box,
  TextField,
  Button,
  Typography,
  Grid,
  Card,
  CardHeader,
  CardContent,
  CardActions,
  Divider,
  Snackbar,
  IconButton,
} from "@mui/material";
import { Link } from "react-router-dom";
import DeleteIcon from "@mui/icons-material/Delete";
import AuthenticatedImage from "../components/AuthenticatedImage";

interface GalleryData {
  id: string;
  creation_time: string;
  expiration_time: string;
}

interface ImageData {
  id: string;
  name: string;
  description: string;
  url: string;
  gallery_id?: string;
}

const AdminPage: React.FC = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authToken, setAuthToken] = useState<string>(
    () => localStorage.getItem("authToken") || ""
  );
  const [galleries, setGalleries] = useState<GalleryData[]>([]);
  const [images, setImages] = useState<ImageData[]>([]);
  const [error, setError] = useState<string>("");
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  const handleLogin = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/v1/auth/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (response.ok) {
        const data = await response.json();
        setAuthToken(data.token);
        localStorage.setItem("authToken", data.token);
        setError("");
      } else {
        setError("Login fehlgeschlagen. Bitte überprüfe deine Zugangsdaten.");
      }
    } catch (err) {
      setError("Fehler beim Login. Bitte versuche es erneut.");
    }
  };

  const fetchData = async () => {
    if (!authToken) return;
    try {
      const [galleriesResponse, imagesResponse] = await Promise.all([
        fetch("http://localhost:8000/api/v1/gallerys", {
          headers: { Authorization: authToken },
        }),
        fetch("http://localhost:8000/api/v1/images", {
          headers: { Authorization: authToken },
        }),
      ]);
      if (galleriesResponse.ok && imagesResponse.ok) {
        const galleriesData = await galleriesResponse.json();
        const imagesData = await imagesResponse.json();
        setGalleries(galleriesData.galleries);
        const loadedImages = imagesData.images.map((img: ImageData) => ({
          ...img,
          url: `http://localhost:8000${img.url}`,
        }));
        setImages(loadedImages);
        setError("");
      } else {
        setError("Fehler beim Laden der Daten.");
      }
    } catch (err) {
      setError("Fehler beim Laden der Daten.");
    }
  };

  useEffect(() => {
    if (authToken) {
      fetchData();
      const interval = setInterval(fetchData, 10000);
      return () => clearInterval(interval);
    }
  }, [authToken]);

  const handleDeleteImage = async (id: string) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/images/${id}`,
        {
          method: "DELETE",
          headers: { Authorization: authToken },
        }
      );
      if (response.ok) {
        setImages((prev) => prev.filter((image) => image.id !== id));
      } else {
        setError("Fehler beim Löschen des Bildes.");
      }
    } catch (err) {
      setError("Fehler beim Löschen des Bildes.");
    }
  };

  const handleDeleteSession = async (galleryId: string) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/gallerys/${galleryId}`,
        {
          method: "DELETE",
          headers: { Authorization: authToken },
        }
      );
      if (response.ok) {
        setGalleries((prev) => prev.filter((g) => g.id !== galleryId));
        setImages((prev) => prev.filter((img) => img.gallery_id !== galleryId));
        setSnackbarOpen(true);
      } else {
        setError("Fehler beim Löschen der Session.");
      }
    } catch (err) {
      setError("Fehler beim Löschen der Session.");
    }
  };

  if (!authToken) {
    return (
      <Container sx={{ mt: 4 }}>
        <Typography variant="h4" align="center" gutterBottom>
          Admin Login
        </Typography>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <TextField
            label="Benutzername"
            variant="outlined"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            sx={{ mb: 2, width: "300px" }}
          />
          <TextField
            label="Passwort"
            type="password"
            variant="outlined"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            sx={{ mb: 2, width: "300px" }}
          />
          <Button variant="contained" onClick={handleLogin}>
            Einloggen
          </Button>
          {error && (
            <Typography variant="body1" color="error" sx={{ mt: 2 }}>
              {error}
            </Typography>
          )}
        </Box>
      </Container>
    );
  }

  const imagesByGallery: { [key: string]: ImageData[] } = {};
  images.forEach((img) => {
    if (img.gallery_id) {
      if (!imagesByGallery[img.gallery_id]) {
        imagesByGallery[img.gallery_id] = [];
      }
      imagesByGallery[img.gallery_id].push(img);
    }
  });

  const sortedGalleries = galleries.sort(
    (a, b) =>
      new Date(a.creation_time).getTime() - new Date(b.creation_time).getTime()
  );

  return (
    <Container
      maxWidth={false}
      disableGutters
      sx={{
        width: "100vw",
        minHeight: "100vh",
        background: "linear-gradient(135deg, #f6d365 0%, #fda085 100%)",
        py: 4,
        px: 2,
      }}
    >
      <Typography
        variant="h4"
        align="center"
        gutterBottom
        sx={{ color: "#333" }}
      >
        Admin Panel - Sessions
      </Typography>
      {error && (
        <Typography variant="body1" color="error" align="center">
          {error}
        </Typography>
      )}
      {sortedGalleries.length === 0 ? (
        <Typography variant="body1" align="center">
          Keine Sessions gefunden.
        </Typography>
      ) : (
        <Grid container spacing={3}>
          {sortedGalleries.map((gallery, index) => (
            <Grid item xs={12} sm={6} md={4} key={gallery.id}>
              <Card sx={{ backgroundColor: "rgba(255,255,255,0.9)" }}>
                <CardHeader
                  title={`#${index + 1}`}
                  subheader={`Erstellt: ${new Date(
                    gallery.creation_time
                  ).toLocaleString()} | Ablauf: ${new Date(
                    gallery.expiration_time
                  ).toLocaleString()}`}
                />
                <Divider />
                <CardContent>
                  {imagesByGallery[gallery.id] &&
                  imagesByGallery[gallery.id].length > 0 ? (
                    <Grid container spacing={1}>
                      {imagesByGallery[gallery.id].map((img) => (
                        <Grid item xs={4} key={img.id}>
                          <Box sx={{ position: "relative" }}>
                            <AuthenticatedImage
                              src={img.url}
                              authToken={authToken}
                              alt={img.name}
                            />
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleDeleteImage(img.id)}
                              sx={{
                                position: "absolute",
                                top: 4,
                                right: 4,
                                backgroundColor: "rgba(255,255,255,0.7)",
                              }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Box>
                        </Grid>
                      ))}
                    </Grid>
                  ) : (
                    <Typography variant="body2">
                      Keine Bilder in dieser Session.
                    </Typography>
                  )}
                </CardContent>
                <CardActions sx={{ justifyContent: "space-between" }}>
                  <Button
                    size="small"
                    component={Link}
                    to={`/session/${gallery.id}`}
                  >
                    Session ansehen
                  </Button>
                  <Button
                    size="small"
                    color="error"
                    onClick={() => handleDeleteSession(gallery.id)}
                  >
                    Session löschen
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={() => setSnackbarOpen(false)}
        message="Löschvorgang erfolgreich"
      />
    </Container>
  );
};

export default AdminPage;
