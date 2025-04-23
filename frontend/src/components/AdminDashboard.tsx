import React, { useEffect, useState, useRef } from "react";
import {
  Box,
  Typography,
  Button,
  Grid,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  TextField,
} from "@mui/material";
import Pagination from "@mui/material/Pagination";
import BackspaceIcon from "@mui/icons-material/Backspace";
import DeleteIcon from "@mui/icons-material/Delete";
import PushPinIcon from "@mui/icons-material/PushPin";
import PrintIcon from "@mui/icons-material/Print";
import RefreshIcon from "@mui/icons-material/Refresh";
import {
  listGalleries,
  deleteGallery,
  updateGalleryPin,
  GalleryResponse,
  logout,
  getImage,
  createFrame,
  listFrames,
  createBackground,
  listBackgrounds,
  deleteBackground,
  printImage,
} from "../api";
import GalleryThumbnail from "./GalleryThumbnail";
import BackgroundImage from "./BackgroundImage";
import itlabImage from "../assets/it-lab-banner.svg";

export interface BackgroundResponse {
  background_id: string;
}

interface AdminDashboardProps {
  token: string;
}

const getAdjustedDate = (dateString: string) => {
  const date = new Date(dateString);
  date.setHours(date.getHours() + 1);
  return date.toLocaleString();
};

const AdminDashboard: React.FC<AdminDashboardProps> = ({ token }) => {
  const [galleries, setGalleries] = useState<GalleryResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 9;

  const [pinModalOpen, setPinModalOpen] = useState<boolean>(false);
  const [selectedGallery, setSelectedGallery] = useState<GalleryResponse | null>(null);
  const [newPin, setNewPin] = useState("");

  const [frameFile, setFrameFile] = useState<File | null>(null);
  const frameInputRef = useRef<HTMLInputElement>(null);
  const [frames, setFrames] = useState<any[]>([]);

  const [backgroundFile, setBackgroundFile] = useState<File | null>(null);
  const backgroundInputRef = useRef<HTMLInputElement>(null);
  const [backgrounds, setBackgrounds] = useState<BackgroundResponse[]>([]);

  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);

  // Cache, um geladene Bilder zu speichern (Mapping von imageId zu Blob-URL)
  const imageCache = useRef<{ [key: string]: string }>({});

  useEffect(() => {
    if (token) {
      listGalleries(token)
        .then((res) => {
          const sortedGalleries = res.galleries.sort(
            (a, b) =>
              new Date(b.creation_time).getTime() - new Date(a.creation_time).getTime()
          );
          setGalleries(sortedGalleries);
        })
        .catch(() => setError("Fehler beim Laden der Galerien"));
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      listFrames(token)
        .then((res) => setFrames(res.frames))
        .catch(() => setError("Fehler beim Laden des Frames"));
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      listBackgrounds(token)
        .then((res) => setBackgrounds(res.backgrounds))
        .catch(() => setError("Fehler beim Laden der Hintergründe"));
    }
  }, [token]);

  const handleDeleteGallery = async (galleryId: string) => {
    if (!token) return;
    if (window.confirm("Galerie wirklich löschen?")) {
      try {
        await deleteGallery(token, galleryId);
        setGalleries((prev) => prev.filter((g) => g.gallery_id !== galleryId));
      } catch {
        setError("Fehler beim Löschen der Galerie");
      }
    }
  };

  const openPinModal = (gallery: GalleryResponse) => {
    setSelectedGallery(gallery);
    setNewPin("");
    setPinModalOpen(true);
  };

  const handleUpdatePin = async () => {
    if (token && selectedGallery && newPin.length === 4 && /^\d{4}$/.test(newPin)) {
      try {
        await updateGalleryPin(token, selectedGallery.gallery_id, newPin);
        alert("PIN geändert.");
        setPinModalOpen(false);
        setGalleries((prev) =>
          prev.map((g) =>
            g.gallery_id === selectedGallery.gallery_id ? { ...g, pin_set: true } : g
          )
        );
      } catch {
        setError("Fehler beim Ändern der PIN");
      }
    }
  };

  const handleFrameButtonClick = () => {
    if (frames.length === 0) {
      frameInputRef.current?.click();
    }
  };

  const handleFrameUpload = () => {
    if (frameFile && token && frames.length === 0) {
      const reader = new FileReader();
      reader.onload = async () => {
        const base64 = (reader.result as string).replace(/^data:image\/[a-z]+;base64,/, "");
        try {
          await createFrame(token, base64);
          alert("Frame erfolgreich hochgeladen");
          const res = await listFrames(token);
          setFrames(res.frames);
        } catch (err) {
          console.error(err);
          alert("Frame-Upload fehlgeschlagen");
        }
      };
      reader.readAsDataURL(frameFile);
    }
  };

  const handleBackgroundButtonClick = () => {
    backgroundInputRef.current?.click();
  };

  const handleBackgroundUpload = () => {
    if (backgroundFile && token) {
      const reader = new FileReader();
      reader.onload = async () => {
        const base64 = (reader.result as string).replace(/^data:image\/[a-z]+;base64,/, "");
        try {
          await createBackground(token, base64);
          alert("Hintergrund erfolgreich hochgeladen");
          const res = await listBackgrounds(token);
          setBackgrounds(res.backgrounds);
        } catch (err) {
          console.error(err);
          alert("Hintergrund-Upload fehlgeschlagen");
        }
      };
      reader.readAsDataURL(backgroundFile);
    }
  };

  const handleDeleteBackground = async (backgroundId: string) => {
    if (!token) return;
    if (window.confirm("Hintergrund wirklich löschen?")) {
      try {
        await deleteBackground(token, backgroundId);
        setBackgrounds((prev) => prev.filter((bg) => bg.background_id !== backgroundId));
      } catch {
        setError("Fehler beim Löschen des Hintergrunds");
      }
    }
  };

  const handleThumbnailClick = async (imageId: string) => {
    // Wenn das Bild bereits im Cache ist, nutze die zwischengespeicherte URL
    if (imageCache.current[imageId]) {
      setPreviewImageUrl(imageCache.current[imageId]);
      return;
    }
    try {
      const blob = await getImage(token, imageId);
      const url = URL.createObjectURL(blob);
      // Speichere die URL im Cache
      imageCache.current[imageId] = url;
      setPreviewImageUrl(url);
    } catch (err) {
      console.error("Fehler beim Laden des Bildes:", err);
    }
  };

  const closePreviewModal = () => {
    // Hier verzichten wir auf URL.revokeObjectURL, um den Cache zu erhalten
    setPreviewImageUrl(null);
  };

  const handlePrintImage = (imageId: string) => {
    if (!token) return;
    printImage(token, imageId)
      .then(() => {
        alert("Druckauftrag gesendet!");
      })
      .catch((err) => {
        console.error("Fehler beim Drucken:", err);
        alert("Fehler beim Drucken. Bitte versuche es erneut.");
      });
  };

  // Berechnung der aktuell anzuzeigenden Galerien für die Pagination
  const displayedGalleries = galleries.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  return (
    <Box sx={{ p: 3, minHeight: "100vh", background: "linear-gradient(135deg, #f6d365, #fda085)" }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography variant="h4">Admin Dashboard</Typography>
        <Button
          variant="contained"
          color="error"
          onClick={() => {
            logout(token).then(() => {
              localStorage.removeItem("adminAuthToken");
              window.location.reload();
            });
          }}
        >
          Logout
        </Button>
      </Box>

      {error && (
        <Typography color="error" sx={{ mb: 2, textAlign: "center" }}>
          {error}
        </Typography>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} md={8} sx={{ mb: 3 }}>
          <Grid container spacing={3}>
            {displayedGalleries.map((g) => (
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
                        <Typography variant="body2">Bild:</Typography>
                        <GalleryThumbnail
                          token={token}
                          imageId={g.images[0]}
                          onClick={() => handleThumbnailClick(g.images[0])}
                        />
                      </Box>
                    ) : (
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        Kein Bild
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
                      sx={{
                        borderRadius: 2,
                        flex: 1,
                        backgroundColor: "primary.main",
                        color: "common.white",
                      }}
                    >
                      Drucken
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<PushPinIcon />}
                      size="small"
                      onClick={() => openPinModal(g)}
                      sx={{
                        borderRadius: 2,
                        flex: 1,
                        backgroundColor: "secondary.main",
                        color: "common.white",
                      }}
                    >
                      PIN ändern
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<DeleteIcon />}
                      size="small"
                      onClick={() => handleDeleteGallery(g.gallery_id)}
                      sx={{
                        borderRadius: 2,
                        flex: 1,
                        backgroundColor: "error.main",
                        color: "common.white",
                      }}
                    >
                      Löschen
                    </Button>
                  </Box>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </Grid>

        <Grid item xs={12} md={4} sx={{ mb: 3 }}>
          <Box sx={{ mb: 4, textAlign: "center" }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Frame
            </Typography>
            {frames.length === 0 ? (
              <>
                <Button variant="contained" onClick={handleFrameButtonClick}>
                  Datei auswählen
                </Button>
                <input
                  type="file"
                  accept="image/*"
                  ref={frameInputRef}
                  style={{ display: "none" }}
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setFrameFile(e.target.files[0]);
                    }
                  }}
                />
                {frameFile && (
                  <Button variant="contained" onClick={handleFrameUpload} sx={{ mt: 1 }}>
                    Hochladen
                  </Button>
                )}
              </>
            ) : (
              <Button variant="contained" disabled>
                Frame bereits hochgeladen
              </Button>
            )}
          </Box>

          <Box sx={{ textAlign: "center" }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Hintergrund
            </Typography>
            <Button variant="contained" onClick={handleBackgroundButtonClick}>
              Datei auswählen
            </Button>
            <input
              type="file"
              accept="image/*"
              ref={backgroundInputRef}
              style={{ display: "none" }}
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setBackgroundFile(e.target.files[0]);
                }
              }}
            />
            {backgroundFile && (
              <Button variant="contained" onClick={handleBackgroundUpload} sx={{ mt: 1 }}>
                Hochladen
              </Button>
            )}
            <Box sx={{ mt: 2, display: "flex", flexDirection: "column", gap: 2 }}>
              {backgrounds.map((bg, index) => (
                <Paper
                  key={bg.background_id}
                  sx={{
                    p: 1,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <BackgroundImage
                    token={token}
                    backgroundId={bg.background_id}
                    style={{ width: 100, height: 60, borderRadius: 4, objectFit: "cover" }}
                  />
                  <Typography variant="body2" sx={{ ml: 1, flexGrow: 1 }}>
                    Hintergrund {index + 1}
                  </Typography>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => handleDeleteBackground(bg.background_id)}
                  >
                    <DeleteIcon />
                  </IconButton>
                </Paper>
              ))}
            </Box>
          </Box>
        </Grid>
      </Grid>

      {/* Pagination */}
      {galleries.length > itemsPerPage && (
        <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
          <Pagination
            count={Math.ceil(galleries.length / itemsPerPage)}
            page={currentPage}
            onChange={(_event, page) => setCurrentPage(page)}
            color="primary"
          />
        </Box>
      )}

      {/* PIN ändern Dialog */}
      <Dialog open={pinModalOpen} onClose={() => setPinModalOpen(false)}>
        <DialogTitle sx={{ textAlign: "center" }}>PIN ändern</DialogTitle>
        <DialogContent>
          <TextField
            value={newPin.replace(/./g, "•")}
            variant="outlined"
            fullWidth
            disabled
            sx={{ mb: 2, textAlign: "center" }}
          />
          <Grid container spacing={1}>
            {["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"].map((digit) => (
              <Grid item xs={4} key={digit}>
                <Button
                  variant="outlined"
                  fullWidth
                  onClick={() => setNewPin((prev) => (prev.length < 4 ? prev + digit : prev))}
                  sx={{ fontSize: "1.2rem", padding: "0.5rem" }}
                >
                  {digit}
                </Button>
              </Grid>
            ))}
            <Grid item xs={4}>
              <IconButton
                onClick={() => setNewPin((prev) => prev.slice(0, -1))}
                sx={{ fontSize: "1.2rem", padding: "0.25rem" }}
              >
                <BackspaceIcon />
              </IconButton>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions sx={{ justifyContent: "center" }}>
          <Button
            variant="contained"
            onClick={handleUpdatePin}
            disabled={!/^\d{4}$/.test(newPin)}
            sx={{ fontSize: "0.9rem", px: 2 }}
          >
            Bestätigen
          </Button>
        </DialogActions>
      </Dialog>

      {/* Bildvorschau Dialog */}
      <Dialog open={!!previewImageUrl} onClose={closePreviewModal} maxWidth="md" fullWidth>
        <DialogTitle sx={{ textAlign: "center" }}>Bildvorschau</DialogTitle>
        <DialogContent sx={{ display: "flex", justifyContent: "center" }}>
          {previewImageUrl && (
            <Box
              component="img"
              src={previewImageUrl}
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
          <Button variant="contained" onClick={closePreviewModal}>
            Schließen
          </Button>
        </DialogActions>
      </Dialog>

      {/* Manuelles Reload-Icon */}
      <Box
        sx={{
          position: "fixed",
          bottom: 16,
          right: 16,
          display: "flex",
          alignItems: "center",
          gap: 1,
        }}
      >
        <Box
          component="img"
          src={itlabImage}
          alt="IT-Lab Logo"
          sx={{
            width: 100,
            opacity: 0.8,
          }}
        />
        <IconButton onClick={() => window.location.reload()} color="primary" size="large">
          <RefreshIcon fontSize="inherit" />
        </IconButton>
      </Box>
    </Box>
  );
};

export default AdminDashboard;
