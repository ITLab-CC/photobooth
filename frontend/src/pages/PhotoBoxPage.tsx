import { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Snackbar,
  Fade,
  Container,
} from "@mui/material";
import { keyframes } from "@mui/system";
import AutoLogin from "../components/AutoLogin";
import PrintCountModal from "../components/PrintCountModal";
import CustomCameraComponent from "../components/CustomCameraComponent";
import BackgroundSlider from "../components/BackgroundSlider";
import {
  createGallery,
  deleteGallery,
  GalleryResponse,
  processImage,
  listFrames,
  getImage,
  printImage,
} from "../api";
import { runtimeConfig, initEventConfig } from "../config/event";
import { logDebug } from "../utils/logger";
import itlabImage from "../assets/itlab_logo.png";

interface ImageResponse {
  image_id: string;
  type: string;
  gallery: string;
}

interface ExtendedImageProcessResponse {
  img_no_background: ImageResponse;
  img_new_background: ImageResponse;
  img_with_frame: ImageResponse;
}

// Decorative leaf animation
const floatAnimation = keyframes`
  0% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-10px) rotate(5deg); }
  100% { transform: translateY(0px) rotate(0deg); }
`;

// Animation for text fade in
const fadeInAnimation = keyframes`
  0% { opacity: 0; transform: translateY(20px); }
  100% { opacity: 1; transform: translateY(0); }
`;

export default function PhotoBoxPage() {
  const [token, setToken] = useState<string | null>(null);
  const [galleryId, setGalleryId] = useState<string | null>(null);
  const [showPrintCountModal, setShowPrintCountModal] = useState(false);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [showResultModal, setShowResultModal] = useState<boolean>(false);
  const [processing, setProcessing] = useState<boolean>(false);
  const [processedImageId, setProcessedImageId] = useState<string | null>(null);
  const [selectedBackgroundId, setSelectedBackgroundId] = useState<string | null>(null);
  const [magicEnabled, setMagicEnabled] = useState<boolean>(false);
  const [frameId, setFrameId] = useState<string | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  
  // Animation states for start screen
  const [showStartScreen, setShowStartScreen] = useState(true);
  const [animationStarted, setAnimationStarted] = useState(false);
  const [showNames, setShowNames] = useState(false);
  const [showMainContent, setShowMainContent] = useState(false);

  // Galerie erstellen
  useEffect(() => {
    if (token && !galleryId) {
      createGallery(token)
        .then((resp: GalleryResponse) => {
          logDebug("Galerie erstellt:", resp.gallery_id);
          setGalleryId(resp.gallery_id);
        })
        .catch((err) => {
          console.error("Fehler beim Erstellen der Galerie:", err);
        });
    }
  }, [token, galleryId]);

  // Event-Settings (Titel/Branding) vom Backend laden
  useEffect(() => {
    if (token) {
      initEventConfig(token);
    }
  }, [token]);

  // Frames laden
  useEffect(() => {
    if (token) {
      listFrames(token)
        .then((res) => {
          if (res.frames && res.frames.length > 0) {
            const activeFrame = res.frames.find((f) => f.is_active);
            setFrameId((activeFrame ?? res.frames[0]).frame_id);
          }
        })
        .catch((err) => {
          console.error("Fehler beim Laden des Frames:", err);
        });
    }
  }, [token]);

  // Disable swipe gestures, but allow camera interaction
  useEffect(() => {
    // Verhindere Wischgesten, aber erlaube Kamera-Interaktion
    const style = document.createElement('style');
    style.textContent = `
      html, body {
        overscroll-behavior: none;
        overflow: hidden;
        position: fixed;
        width: 100%;
        height: 100%;
        -webkit-overflow-scrolling: touch;
        -ms-overflow-style: none;
      }
    `;
    document.head.appendChild(style);
    
    // Verhindere nur horizontales Wischen, erlaube vertikales Scrollen und Kamera-Interaktion
    const preventHorizontalSwipe = (e: TouchEvent) => {
      // Nur horizontales Wischen verhindern, vertikales Scrollen erlauben
      if (e.touches[0] && Math.abs(e.touches[0].clientX) > Math.abs(e.touches[0].clientY)) {
        e.preventDefault();
      }
    };
    // Verwende ein passives Event für bessere Performance
    document.addEventListener('touchmove', preventHorizontalSwipe, { passive: false });
    
    return () => {
      document.head.removeChild(style);
      document.removeEventListener('touchmove', preventHorizontalSwipe);
    };
  }, []);
  
  // Handle the start animation sequence
  const handleStartClick = () => {
    setAnimationStarted(true);
    setShowNames(true);
    
    setTimeout(() => {
      setShowStartScreen(false);
      setShowMainContent(true);
    }, 2000);
  };

  const handleBackgroundSelect = (bgId: string | null) => {
    logDebug("Ausgewählter Hintergrund:", bgId);
    setSelectedBackgroundId(bgId);
  };

  // Bild hochladen und verarbeiten
  const handleImageUpload = (imageId: string) => {
    setCapturedImage(imageId);
    setProcessing(true);
    setShowResultModal(true);
    // Basis-Payload erstellen
    const payload: any = {
      image_id: imageId,
      img_frame_id: frameId ? frameId : "",
      refine_foreground: false,
      random_stuff: magicEnabled,
    };
    
    // image_background_id nur hinzufügen, wenn ein Hintergrund ausgewählt wurde
    if (selectedBackgroundId !== null) {
      payload.image_background_id = selectedBackgroundId;
    }
    processImage(token!, payload)
      .then((resp) => {
        const extendedResp = resp as unknown as ExtendedImageProcessResponse;
        setProcessedImageId(extendedResp.img_with_frame.image_id);
        return getImage(token!, extendedResp.img_with_frame.image_id);
      })
      .then((blob) => {
        const processedImageUrl = URL.createObjectURL(blob);
        setCapturedImage(processedImageUrl);
        setProcessing(false);
      })
      .catch((err) => {
        console.error("Fehler bei der Bildverarbeitung:", err);
        setProcessing(false);
      });
  };
  
  // Magic Toggle Handler
  const handleMagicToggle = () => {
    setMagicEnabled(!magicEnabled);
  };

  // Beim Erneut Versuchen: Alte Galerie löschen und neue erstellen
  const handleRetry = () => {
    setCapturedImage(null);
    setProcessedImageId(null);
    setProcessing(false);
    setShowResultModal(false);
    
    // Alte Galerie löschen, wenn vorhanden
    if (token && galleryId) {
      deleteGallery(token, galleryId)
        .then(() => {
          logDebug("Alte Galerie gelöscht:", galleryId);
          setGalleryId(""); // Galerie-ID zurücksetzen
          
          // Neue Galerie erstellen
          return createGallery(token);
        })
        .then((resp: GalleryResponse) => {
          logDebug("Neue Galerie erstellt:", resp.gallery_id);
          setGalleryId(resp.gallery_id);
        })
        .catch((err: Error) => {
          console.error("Fehler beim Löschen/Erstellen der Galerie:", err);
        });
    }
  };

  // Klick auf Fertigstellen: Öffnet die Druckauswahl-Modal
  const handleFinish = () => {
    setShowPrintCountModal(true);
  };

  // Nach Auswahl der Druckanzahl: Einen einzelnen Druckauftrag mit der angegebenen Anzahl senden
  const handlePrintCountSubmit = async (count: number) => {
    setShowPrintCountModal(false);
    setSnackbarOpen(true);
    
    try {
      // Einzelnen Druckauftrag mit der gewünschten Anzahl senden
      await printImage(token!, processedImageId!, count);
      
      setTimeout(() => {
        window.location.reload();
      }, 3000);
    } catch (err) {
      console.error("Fehler beim Drucken:", err);
      alert("Fehler beim Drucken. Bitte versuche es erneut.");
      window.location.reload();
    }
  };

  return (
      <Box
        sx={{
          minHeight: '100vh',
          width: '100%',
          background: '#ffffff',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center', // Vertikale Zentrierung
          position: 'relative',
          overflow: 'hidden',
          overscrollBehavior: 'none',
          userSelect: 'none',
          WebkitOverflowScrolling: 'touch',
          msOverflowStyle: 'none',
        }}
      >
        
        {/* Start Screen */}
        {showStartScreen && (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100vh',
              width: '100%',
              position: 'absolute',
              top: 0,
              left: 0,
              zIndex: 10,
            }}
          >
            {/* Tap to Start with Hand Icon */}
            {!animationStarted && (
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  width: '100%',
                }}
              >
                {/* Circle with Hand Icon */}
                <Box
                  onClick={handleStartClick}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: '50%',
                    backgroundColor: 'rgba(0, 0, 0, 0.05)',
                    width: 180,
                    height: 180,
                    transition: 'all 0.3s ease',
                    mb: 3,
                    '&:hover': {
                      backgroundColor: 'rgba(0, 0, 0, 0.1)',
                      transform: 'scale(1.05)',
                    },
                  }}
                >
                  {/* Hand Icon */}
                  <Box
                    sx={{
                      width: 100,
                      height: 100,
                      backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512' fill='%23000000'%3E%3Cpath d='M288 32c0-17.7-14.3-32-32-32s-32 14.3-32 32V240c0 8.8-7.2 16-16 16s-16-7.2-16-16V64c0-17.7-14.3-32-32-32s-32 14.3-32 32V336c0 1.5 0 3.1 .1 4.6L67.6 283c-16-15.2-41.3-14.6-56.6 1.4s-14.6 41.3 1.4 56.6L124.8 448c43.1 41.1 100.4 64 160 64H304c97.2 0 176-78.8 176-176V128c0-17.7-14.3-32-32-32s-32 14.3-32 32V240c0 8.8-7.2 16-16 16s-16-7.2-16-16V64c0-17.7-14.3-32-32-32s-32 14.3-32 32V240c0 8.8-7.2 16-16 16s-16-7.2-16-16V32z'/%3E%3C/svg%3E")`,
                      backgroundRepeat: 'no-repeat',
                      backgroundSize: 'contain',
                      animation: `${floatAnimation} 2s ease-in-out infinite`,
                    }}
                  />
                </Box>
                
                {/* Text outside the circle */}
                <Typography
                  variant="h4"
                  onClick={handleStartClick}
                  sx={{
                    fontFamily: "'Inter', sans-serif",
                    color: '#000000',
                    fontWeight: 400,
                    textAlign: 'center',
                    cursor: 'pointer',
                    width: '100%',
                    maxWidth: '90%',
                    margin: '0 auto',
                    '&:hover': {
                      color: '#333333',
                    },
                  }}
                >
                  Erschaffe eine Erinnerung
                </Typography>
              </Box>
            )}
            
            
            {/* Names Reveal */}
            {showNames && (
              <Fade in={showNames} timeout={1000}>
                <Box 
                  sx={{ 
                    textAlign: "center", 
                    position: "relative",
                    zIndex: 1,
                    animation: `${fadeInAnimation} 1s ease`,
                  }}
                >
                  <Typography 
                    variant="h2" 
                    sx={{ 
                      fontFamily: "'Inter', sans-serif",
                      color: "#3c3c3c",
                      fontWeight: 600,
                      letterSpacing: 1,
                      mb: 1,
                    }}
                  >
                    {runtimeConfig.title}
                  </Typography>
                  <Typography 
                    variant="h5" 
                    sx={{ 
                      fontFamily: "'Inter', sans-serif",
                      color: "#666666",
                      fontWeight: 400,
                      letterSpacing: 1,
                    }}
                  >
                    {runtimeConfig.subtitle}
                  </Typography>
                </Box>
              </Fade>
            )}
          </Box>
        )}

        {/* Wedding title - shown after animation or when returning to main screen */}
        {token && galleryId && !showResultModal && showMainContent && (
          <Box 
            sx={{ 
              textAlign: "center", 
              mb: 4, 
              position: "relative",
              zIndex: 1,
            }}
          >
            <Typography 
              variant="h3" 
              sx={{ 
                fontFamily: "'Inter', sans-serif",
                color: "#3c3c3c",
                fontWeight: 600,
                letterSpacing: 1,
                mb: 1,
              }}
            >
              {runtimeConfig.title}
            </Typography>
            <Typography 
              variant="h6" 
              sx={{ 
                fontFamily: "'Inter', sans-serif",
                color: "#666666",
                fontWeight: 400,
                letterSpacing: 1,
              }}
            >
              {runtimeConfig.subtitle}
            </Typography>
          </Box>
        )}

        {!token && <AutoLogin onToken={setToken} />}

        {token && !galleryId && !showStartScreen && (
          <Typography
            variant="h5"
            sx={{
              mb: 2,
              color: "#3c3c3c",
            }}
          >
            Galerie wird erstellt…
          </Typography>
        )}

        {token && galleryId && !showResultModal && showMainContent && (
          <>
            <CustomCameraComponent
              galleryId={galleryId}
              token={token}
              onImageUpload={handleImageUpload}
            />
            {/* Magic Toggle Switch */}
            <Container maxWidth="sm" sx={{ mt: 2, textAlign: 'center' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>
                  Magic Mode
                </Typography>
                <Box 
                  onClick={() => !processing && handleMagicToggle()}
                  sx={{
                    width: '60px',
                    height: '30px',
                    borderRadius: '15px',
                    backgroundColor: magicEnabled ? '#000000' : '#e0e0e0',
                    position: 'relative',
                    transition: 'background-color 0.3s',
                    cursor: processing ? 'not-allowed' : 'pointer',
                    opacity: processing ? 0.6 : 1,
                    boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.2)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: magicEnabled ? 'flex-end' : 'flex-start',
                    padding: '3px',
                  }}
                >
                  <Box
                    sx={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      backgroundColor: '#ffffff',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.2)',
                      transition: 'transform 0.3s',
                    }}
                  />
                </Box>
                <Typography variant="body2" sx={{ color: '#666666' }}>
                  {magicEnabled ? '✨ An' : 'Aus'}
                </Typography>
              </Box>
            </Container>
            
            <Box mt={4}>
              <BackgroundSlider token={token} onSelect={handleBackgroundSelect} />
            </Box>
          </>
        )}

        <Dialog 
          open={showResultModal} 
          disableEscapeKeyDown 
          maxWidth="sm" 
          fullWidth
          PaperProps={{
            sx: {
              borderRadius: 3,
              boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
              overflow: "hidden",
              width: "95%",
              maxWidth: "700px",
              margin: "auto"
            }
          }}
        >
          <DialogTitle 
            sx={{ 
              textAlign: "center",
              fontFamily: "'Inter', sans-serif",
              fontSize: "1.5rem",
              fontWeight: 500,
              pt: 3,
            }}
          >
            {processing ? "Bild wird verarbeitet…" : "Euer Moment"}
          </DialogTitle>
          <DialogContent sx={{ textAlign: "center", px: 4, pb: 4 }}>
            {processing ? (
              <CircularProgress sx={{ color: "#000000" }} />
            ) : (
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  width: "100%",
                  height: "auto",
                  overflow: "hidden",
                }}
              >
                <Box
                  component="img"
                  src={capturedImage ? capturedImage : ""}
                  alt="Aufgenommenes Bild"
                  sx={{
                    width: "100%",
                    maxHeight: "70vh",
                    objectFit: "contain",
                    borderRadius: 2,
                    boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                    border: "4px solid white",
                    '@media print': {
                      transform: 'rotate(90deg)',
                      transformOrigin: 'center center',
                    },
                  }}
                />
              </Box>
            )}
          </DialogContent>
          {!processing && (
            <DialogActions sx={{ justifyContent: "center", p: 3, gap: 2 }}>
              <Button 
                variant="outlined" 
                onClick={handleRetry}
                sx={{ 
                  borderWidth: 1.5,
                  fontSize: "0.95rem",
                }}
              >
                Neues Foto
              </Button>
              <Button 
                variant="contained" 
                onClick={handleFinish}
                sx={{ 
                  fontSize: "0.95rem",
                  fontWeight: 600,
                }}
              >
                ✨ Drucken
              </Button>
            </DialogActions>
          )}
        </Dialog>

        <PrintCountModal
          open={showPrintCountModal}
          onSubmit={handlePrintCountSubmit}
          onCancel={() => {
            setShowPrintCountModal(false);
          }}
        />

      <Box
        component="img"
        src={itlabImage}
        alt="Itlab Logo"
        sx={{
          position: "fixed",
          bottom: 16,
          right: 16,
          width: 125,
          opacity: 0.8,
        }}
      />


        <Snackbar
          open={snackbarOpen}
          autoHideDuration={3000}
          onClose={() => setSnackbarOpen(false)}
          message="Eure Erinnerung wird gedruckt!"
          anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
          ContentProps={{
            sx: {
              background: "#000000",
              fontFamily: "'Inter', sans-serif",
              fontSize: "1.1rem",
              fontWeight: 400,
            }
          }}
        />
      </Box>
  );
}
