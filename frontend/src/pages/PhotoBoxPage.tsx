import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  Button,
  ButtonBase,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
  Snackbar,
  Fade,
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
  MagicStyle,
  FaceResponse,
  listFaces,
  addGalleryImage,
  listFrames,
  getImage,
  printImage,
} from "../api";
import { runtimeConfig, initEventConfig } from "../config/event";
import { logDebug } from "../utils/logger";
import { KIOSK_SCALE, KIOSK_WIDTH, brand, px } from "../theme";
import { useIdleTimeout } from "../utils/useIdleTimeout";
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

// Ohne Eingabe geht die Box nach dieser Zeit zurück zum Startbildschirm.
const IDLE_TIMEOUT_MS = 60_000;
// So lange wird ein Verarbeitungsschritt angezeigt, bevor der nächste erscheint.
const PROCESSING_STEP_MS = 3500;

const MAGIC_STYLES: { value: MagicStyle; label: string }[] = [
  { value: "smileys", label: "😀 Smileys" },
  { value: "sunglasses", label: "😎 Sonnenbrille" },
  { value: "party_hat", label: "🎉 Partyhut" },
  { value: "crown", label: "👑 Krone" },
  { value: "party", label: "🥳 Partylook" },
  { value: "moustache", label: "🥸 Schnurrbart" },
  { value: "clown_nose", label: "🤡 Clownsnase" },
  { value: "bunny_ears", label: "🐰 Hasenohren" },
  { value: "halo", label: "😇 Heiligenschein" },
  { value: "hearts", label: "😍 Herzaugen" },
  { value: "mix", label: "🎲 Überraschung" },
];

// Soft ring that invites the first tap on the start screen.
const pulseRing = keyframes`
  0% { transform: scale(1); opacity: 0.55; }
  100% { transform: scale(1.3); opacity: 0; }
`;

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

// Horizontally scrolling row of large touch chips (Magic styles).
const chipRowSx = {
  display: "flex",
  gap: 1,
  overflowX: "auto",
  pb: 1,
  scrollSnapType: "x proximity",
  WebkitOverflowScrolling: "touch",
  // Touch scrolling only: no scrollbar, the half-visible last chip is the cue.
  scrollbarWidth: "none",
  "&::-webkit-scrollbar": { display: "none" },
} as const;

const chipSx = {
  flex: "0 0 auto",
  minHeight: px(56),
  px: 2.5,
  fontSize: "1.05rem",
  whiteSpace: "nowrap",
  scrollSnapAlign: "start",
} as const;

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
  const [magicStyle, setMagicStyle] = useState<MagicStyle>("smileys");
  // Faces from the admin dashboard that can replace the guests' faces (face swap).
  const [faces, setFaces] = useState<FaceResponse[]>([]);
  const [faceSwapId, setFaceSwapId] = useState<string | null>(null);
  // Photos of a series while the guests pick the best one (base64 PNG).
  const [candidates, setCandidates] = useState<string[] | null>(null);
  const [frameId, setFrameId] = useState<string | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState("Eure Erinnerung wird gedruckt!");
  const [processingStep, setProcessingStep] = useState(0);
  // Re-render once the admin-configured texts and logo have been loaded.
  const [, setEventConfigLoaded] = useState(false);
  
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
      initEventConfig(token).then(() => setEventConfigLoaded(true));
    }
  }, [token]);

  // Gesichter für den Gesichtstausch laden (leer, solange die Modelle noch nicht bereit sind)
  useEffect(() => {
    if (token) {
      listFaces(token)
        .then((res) => setFaces(res.models_ready ? res.faces : []))
        .catch((err) => console.error("Fehler beim Laden der Gesichter:", err));
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
    // rem-based text (all MUI typography) scales with the kiosk screen; restored when leaving the page.
    const previousFontSize = document.documentElement.style.fontSize;
    document.documentElement.style.fontSize = `${16 * KIOSK_SCALE}px`;
    
    // Verhindere nur horizontales Wischen, erlaube vertikales Scrollen und Kamera-Interaktion
    const preventHorizontalSwipe = (e: TouchEvent) => {
      // Rows marked data-scroll-x (the Magic style picker) scroll sideways on purpose.
      if ((e.target as HTMLElement | null)?.closest?.('[data-scroll-x]')) return;
      // Nur horizontales Wischen verhindern, vertikales Scrollen erlauben
      if (e.touches[0] && Math.abs(e.touches[0].clientX) > Math.abs(e.touches[0].clientY)) {
        e.preventDefault();
      }
    };
    // Verwende ein passives Event für bessere Performance
    document.addEventListener('touchmove', preventHorizontalSwipe, { passive: false });
    
    return () => {
      document.head.removeChild(style);
      document.documentElement.style.fontSize = previousFontSize;
      document.removeEventListener('touchmove', preventHorizontalSwipe);
    };
  }, []);
  
  const showNotice = (message: string) => {
    setSnackbarMessage(message);
    setSnackbarOpen(true);
  };

  // Schritte, die der Gast während der KI-Verarbeitung sieht
  const processingSteps = [
    ...(magicEnabled && faceSwapId ? ["Die Gesichter werden getauscht 🎭"] : []),
    selectedBackgroundId !== null ? "Ich schneide euch aus…" : "Euer Foto wird angepasst…",
    ...(selectedBackgroundId !== null ? ["Euer Hintergrund wird gebaut…"] : []),
    ...(magicEnabled && !faceSwapId ? ["Magic wird gestreut ✨"] : []),
    "Der Rahmen wird gesetzt…",
  ];

  useEffect(() => {
    if (!processing) {
      setProcessingStep(0);
      return;
    }
    const timer = setInterval(() => {
      setProcessingStep((step) => Math.min(step + 1, processingSteps.length - 1));
    }, PROCESSING_STEP_MS);
    return () => clearInterval(timer);
  }, [processing, processingSteps.length]);

  // Zurück zum Start, wenn niemand mehr etwas tut. Die Galerie mit dem Foto wird dabei gelöscht.
  const handleIdle = useCallback(() => {
    const cleanup = token && galleryId ? deleteGallery(token, galleryId) : Promise.resolve({ ok: true });
    cleanup.catch((err) => console.error("Fehler beim Aufräumen:", err)).finally(() => window.location.reload());
  }, [token, galleryId]);

  useIdleTimeout(
    !showStartScreen && !processing && !showPrintCountModal && !!token,
    IDLE_TIMEOUT_MS,
    handleIdle
  );

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

  const uploadAndProcess = async (photoBase64: string) => {
    if (!token || !galleryId) return;
    try {
      const response = await addGalleryImage(token, galleryId, photoBase64);
      handleImageUpload(response.image_id);
    } catch (err) {
      console.error("Fehler beim Upload:", err);
      showNotice("Das Foto konnte nicht gespeichert werden. Bitte noch einmal versuchen.");
    }
  };

  // One photo goes straight to processing; a series first asks which one the guests like best.
  const handlePhotos = (photos: string[]) => {
    if (photos.length === 1) {
      uploadAndProcess(photos[0]);
    } else {
      setCandidates(photos);
    }
  };

  const handleChoosePhoto = (index: number) => {
    const chosen = candidates?.[index];
    setCandidates(null);
    if (chosen) uploadAndProcess(chosen);
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
      random_stuff: magicEnabled && !faceSwapId,
      magic_style: magicStyle,
      ...(magicEnabled && faceSwapId ? { face_swap_id: faceSwapId } : {}),
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
        setShowResultModal(false);
        setSnackbarMessage("Das hat nicht geklappt. Versucht es bitte noch einmal.");
        setSnackbarOpen(true);
      });
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
    // With a limit of one copy there is nothing to choose.
    if (runtimeConfig.maxPrints <= 1) {
      handlePrintCountSubmit(1);
    } else {
      setShowPrintCountModal(true);
    }
  };

  // Nach Auswahl der Druckanzahl: Einen einzelnen Druckauftrag mit der angegebenen Anzahl senden
  const handlePrintCountSubmit = async (count: number) => {
    setShowPrintCountModal(false);
    setSnackbarMessage("Eure Erinnerung wird gedruckt!");
    setSnackbarOpen(true);
    
    try {
      // Einzelnen Druckauftrag mit der gewünschten Anzahl senden
      await printImage(token!, processedImageId!, count);
      
      setTimeout(() => {
        window.location.reload();
      }, 3000);
    } catch (err) {
      console.error("Fehler beim Drucken:", err);
      setSnackbarMessage("Das Drucken hat nicht geklappt. Bitte sagt kurz dem Team Bescheid.");
      setSnackbarOpen(true);
      setTimeout(() => window.location.reload(), 5000);
    }
  };

  return (
      <Box
        sx={{
          minHeight: '100vh',
          width: '100%',
          background: brand.surface,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: showMainContent && !showResultModal ? 'flex-start' : 'center',
          pt: showMainContent && !showResultModal ? 2 : 0,
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
                    position: 'relative',
                    backgroundColor: '#ffffff',
                    border: `3px solid ${brand.teal}`,
                    boxShadow: '0 10px 30px rgba(0, 117, 133, 0.18)',
                    '&::after': {
                      content: '""',
                      position: 'absolute',
                      inset: -6,
                      borderRadius: '50%',
                      border: `2px solid ${brand.teal}`,
                      animation: `${pulseRing} 2.4s ease-out infinite`,
                      '@media (prefers-reduced-motion: reduce)': { animation: 'none', opacity: 0.3 },
                    },
                    width: px(180),
                    height: px(180),
                    transition: 'all 0.3s ease',
                    mb: 3,
                    '&:hover': {
                      backgroundColor: brand.tealTint,
                      transform: 'scale(1.05)',
                    },
                  }}
                >
                  {/* Hand Icon */}
                  <Box
                    sx={{
                      width: px(100),
                      height: px(100),
                      backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512' fill='%23007585'%3E%3Cpath d='M288 32c0-17.7-14.3-32-32-32s-32 14.3-32 32V240c0 8.8-7.2 16-16 16s-16-7.2-16-16V64c0-17.7-14.3-32-32-32s-32 14.3-32 32V336c0 1.5 0 3.1 .1 4.6L67.6 283c-16-15.2-41.3-14.6-56.6 1.4s-14.6 41.3 1.4 56.6L124.8 448c43.1 41.1 100.4 64 160 64H304c97.2 0 176-78.8 176-176V128c0-17.7-14.3-32-32-32s-32 14.3-32 32V240c0 8.8-7.2 16-16 16s-16-7.2-16-16V64c0-17.7-14.3-32-32-32s-32 14.3-32 32V240c0 8.8-7.2 16-16 16s-16-7.2-16-16V32z'/%3E%3C/svg%3E")`,
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
                    color: 'text.primary',
                    fontWeight: 500,
                    textAlign: 'center',
                    cursor: 'pointer',
                    width: '100%',
                    maxWidth: '90%',
                    margin: '0 auto',
                    '&:hover': {
                      color: 'primary.main',
                    },
                  }}
                >
                  {runtimeConfig.startText}
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
                      color: "text.primary",
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
                      color: "text.secondary",
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

        {token && galleryId && !showResultModal && showMainContent && (
          <Box sx={{ textAlign: "center", mb: 2, px: 2, position: "relative", zIndex: 1 }}>
            <Typography variant="h4" component="h1" sx={{ letterSpacing: 0.5 }}>
              {runtimeConfig.title}
            </Typography>
            <Typography variant="h6" component="p" color="text.secondary">
              {runtimeConfig.subtitle}
            </Typography>
          </Box>
        )}

        {!token && <AutoLogin onToken={setToken} />}

        {token && !galleryId && !showStartScreen && (
          <Typography variant="h5" color="text.secondary" sx={{ mb: 2 }}>
            Die Fotobox wird vorbereitet…
          </Typography>
        )}

        {token && galleryId && !showResultModal && showMainContent && (
          <>
            <CustomCameraComponent
              seriesCount={runtimeConfig.seriesCount}
              onPhotosCaptured={handlePhotos}
              onError={showNotice}
            />

            {/* Bottom padding keeps the controls clear of the fixed logos. */}
            <Box
              sx={{
                width: "100%",
                maxWidth: KIOSK_WIDTH,
                px: 2,
                pt: 1.5,
                pb: `${px(120)}px`,
                boxSizing: "border-box",
                display: "flex",
                flexDirection: "column",
                gap: 2.5,
              }}
            >
              {/* "Aus" comes first; Magic uses the orange so it stays distinct from the teal actions. */}
              <Box component="section" aria-label="Magic">
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                  Magic
                </Typography>
                <Box data-scroll-x role="radiogroup" aria-label="Magic-Stil" sx={chipRowSx}>
                  {[
                    { value: "off", label: "Aus" },
                    ...faces.map((face) => ({ value: `face:${face.face_id}`, label: `🎭 ${face.name}` })),
                    ...MAGIC_STYLES,
                  ].map((style) => {
                    const current = !magicEnabled ? "off" : faceSwapId ? `face:${faceSwapId}` : magicStyle;
                    const selected = current === style.value;
                    return (
                      <Button
                        key={style.value}
                        role="radio"
                        aria-checked={selected}
                        variant={selected ? "contained" : "outlined"}
                        onClick={() => {
                          if (style.value === "off") {
                            setMagicEnabled(false);
                          } else if (style.value.startsWith("face:")) {
                            setMagicEnabled(true);
                            setFaceSwapId(style.value.slice("face:".length));
                          } else {
                            setMagicEnabled(true);
                            setFaceSwapId(null);
                            setMagicStyle(style.value as MagicStyle);
                          }
                        }}
                        sx={{
                          ...chipSx,
                          ...(selected && { backgroundColor: brand.magic, borderColor: brand.magic, "&:hover": { backgroundColor: brand.magic } }),
                          ...(!selected && { color: "text.primary", borderColor: brand.line, backgroundColor: "background.paper" }),
                        }}
                      >
                        {style.label}
                      </Button>
                    );
                  })}
                </Box>
              </Box>

              <Box component="section" aria-label="Hintergrund wählen">
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                  Hintergrund wählen
                </Typography>
                <BackgroundSlider token={token} onSelect={handleBackgroundSelect} />
              </Box>

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
              maxWidth: px(700),
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
            {processing ? "Einen Moment, die KI arbeitet…" : "Euer Moment"}
          </DialogTitle>
          <DialogContent sx={{ textAlign: "center", px: 4, pb: 4 }}>
            {processing ? (
              <Box sx={{ py: 4 }}>
                <Typography
                  key={processingStep}
                  variant="h5"
                  sx={{ mb: 3, minHeight: "2em", animation: `${fadeInAnimation} 0.5s ease` }}
                >
                  {processingSteps[Math.min(processingStep, processingSteps.length - 1)]}
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={((Math.min(processingStep, processingSteps.length - 1) + 1) / processingSteps.length) * 100}
                  sx={{ height: 10, borderRadius: 5, "& .MuiLinearProgress-bar": { backgroundColor: brand.teal } }}
                />
              </Box>
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
                  fontSize: "1.2rem",
                  minHeight: px(64),
                  minWidth: px(180),
                }}
              >
                Neues Foto
              </Button>
              <Button 
                variant="contained" 
                onClick={handleFinish}
                sx={{ 
                  fontSize: "1.2rem",
                  fontWeight: 600,
                  minHeight: px(64),
                  minWidth: px(180),
                }}
              >
                ✨ Drucken
              </Button>
            </DialogActions>
          )}
        </Dialog>

        <Dialog
          open={candidates !== null}
          disableEscapeKeyDown
          fullWidth
          maxWidth={false}
          PaperProps={{ sx: { width: "95%", maxWidth: px(900), borderRadius: 3 } }}
        >
          <DialogTitle sx={{ textAlign: "center", fontWeight: 600 }}>Welches Foto gefällt euch am besten?</DialogTitle>
          <DialogContent>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: `repeat(auto-fit, minmax(${px(240)}px, 1fr))`,
                gap: 2,
                pt: 1,
              }}
            >
              {candidates?.map((photo, index) => (
                <ButtonBase
                  key={index}
                  onClick={() => handleChoosePhoto(index)}
                  aria-label={`Foto ${index + 1} auswählen`}
                  sx={{
                    borderRadius: 2,
                    overflow: "hidden",
                    border: `3px solid ${brand.line}`,
                    "&:hover, &:focus-visible": { borderColor: brand.teal },
                  }}
                >
                  <Box
                    component="img"
                    src={`data:image/png;base64,${photo}`}
                    alt={`Foto ${index + 1}`}
                    sx={{ width: "100%", display: "block" }}
                  />
                </ButtonBase>
              ))}
            </Box>
          </DialogContent>
          <DialogActions sx={{ justifyContent: "center", p: 2 }}>
            <Button variant="outlined" onClick={() => setCandidates(null)} sx={{ minHeight: px(64), minWidth: px(200) }}>
              Alle neu aufnehmen
            </Button>
          </DialogActions>
        </Dialog>

        <PrintCountModal
          open={showPrintCountModal}
          maxCount={runtimeConfig.maxPrints}
          onSubmit={handlePrintCountSubmit}
          onCancel={() => {
            setShowPrintCountModal(false);
          }}
        />

      {/* The IT-Lab logo is fixed branding. An event logo from the admin settings joins it on the left. */}
      {runtimeConfig.logoUrl && (
        <Box
          component="img"
          src={runtimeConfig.logoUrl}
          alt="Event-Logo"
          sx={{
            position: "fixed",
            bottom: 16,
            left: 16,
            maxWidth: px(125),
            maxHeight: px(90),
            objectFit: "contain",
            opacity: 0.9,
          }}
        />
      )}
      <Box
        component="img"
        src={itlabImage}
        alt="IT-Lab Logo"
        sx={{
          position: "fixed",
          bottom: 16,
          right: 16,
          width: px(125),
          opacity: 0.9,
        }}
      />


        <Snackbar
          open={snackbarOpen}
          autoHideDuration={5000}
          onClose={() => setSnackbarOpen(false)}
          message={snackbarMessage}
          anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
          ContentProps={{
            sx: {
              background: brand.navy,
              fontFamily: "'Inter', sans-serif",
              fontSize: "1.1rem",
              fontWeight: 400,
            }
          }}
        />
      </Box>
  );
}
