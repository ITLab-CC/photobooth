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
} from "@mui/material";
import { keyframes } from "@mui/system";
import AutoLogin from "../components/AutoLogin";
import DisclaimerModal from "../components/DisclaimerModal";
import PrintCountModal from "../components/PrintCountModal";
import CustomCameraComponent from "../components/CustomCameraComponent";
import BackgroundSlider from "../components/BackgroundSlider";
import {
  createGallery,
  GalleryResponse,
  processImage,
  listFrames,
  getImage,
  printImage,
} from "../api";
import itlabImage from "../assets/it-lab-banner.svg";

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

const backgroundAnimation = keyframes`
  0% { background: linear-gradient(45deg, #ff9a9e, #fad0c4); }
  33% { background: linear-gradient(45deg, #fad0c4, #a18cd1); }
  66% { background: linear-gradient(45deg, #a18cd1, #fbc2eb); }
  100% { background: linear-gradient(45deg, #fbc2eb, #ff9a9e); }
`;

export default function PhotoBoxPage() {
  const [token, setToken] = useState<string | null>(null);
  const [galleryId, setGalleryId] = useState<string | null>(null);
  const [showDisclaimer, setShowDisclaimer] = useState(true);
  const [showPrintCountModal, setShowPrintCountModal] = useState(false);
  const [printCount, setPrintCount] = useState(1);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [showResultModal, setShowResultModal] = useState<boolean>(false);
  const [processing, setProcessing] = useState<boolean>(false);
  const [processedImageId, setProcessedImageId] = useState<string | null>(null);
  const [selectedBackgroundId, setSelectedBackgroundId] = useState<string | null>(null);
  const [frameId, setFrameId] = useState<string | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  // Galerie erstellen
  useEffect(() => {
    if (token && !galleryId) {
      createGallery(token)
        .then((resp: GalleryResponse) => {
          console.log("Galerie erstellt:", resp.gallery_id);
          setGalleryId(resp.gallery_id);
        })
        .catch((err) => {
          console.error("Fehler beim Erstellen der Galerie:", err);
        });
    }
  }, [token, galleryId]);

  // Frames laden
  useEffect(() => {
    if (token) {
      listFrames(token)
        .then((res) => {
          if (res.frames && res.frames.length > 0) {
            setFrameId(res.frames[0].frame_id);
          }
        })
        .catch((err) => {
          console.error("Fehler beim Laden des Frames:", err);
        });
    }
  }, [token]);

  const handleBackgroundSelect = (bgId: string) => {
    console.log("Ausgewählter Hintergrund:", bgId);
    setSelectedBackgroundId(bgId);
  };

  // Bild hochladen und verarbeiten
  const handleImageUpload = (imageId: string) => {
    setCapturedImage(imageId);
    setProcessing(true);
    setShowResultModal(true);
    const payload = {
      image_id: imageId,
      image_background_id: selectedBackgroundId ? selectedBackgroundId : "",
      img_frame_id: frameId ? frameId : "",
      refine_foreground: false,
    };
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

  // Beim Erneut Versuchen: Alle Daten zurücksetzen (nichts wird gespeichert)
  const handleRetry = () => {
    setCapturedImage(null);
    setProcessedImageId(null);
    setProcessing(false);
    setShowResultModal(false);
  };

  // Klick auf Fertigstellen: Öffnet das Modal zur Auswahl der Anzahl der Drucke
  const handleFinish = () => {
    setShowPrintCountModal(true);
  };

  // Nach Auswahl der Anzahl der Drucke: Drucken der ausgewählten Anzahl
  const handlePrintCountSubmit = (count: number) => {
    setPrintCount(count);
    setShowPrintCountModal(false);
    
    // Drucken der ausgewählten Anzahl von Bildern
    const printPromises = [];
    for (let i = 0; i < count; i++) {
      printPromises.push(printImage(token!, processedImageId!));
    }
    
    Promise.all(printPromises)
      .then(() => {
        setSnackbarOpen(true);
        setTimeout(() => {
          window.location.reload();
        }, 3000);
      })
      .catch((err) => {
        console.error("Fehler beim Drucken:", err);
        alert("Fehler beim Drucken. Bitte versuche es erneut.");
        window.location.reload();
      });
  };

  return (
    <Box
      sx={{
        animation: `${backgroundAnimation} 15s ease infinite`,
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        p: 2,
        position: "relative",
      }}
    >
      {!token && <AutoLogin onToken={setToken} />}

      {token && !galleryId && (
        <Typography variant="h5" color="white" sx={{ mb: 2 }}>
          Galerie wird erstellt…
        </Typography>
      )}

      {token && galleryId && showDisclaimer && (
        <DisclaimerModal
          open={showDisclaimer}
          onAccept={() => {
            setShowDisclaimer(false);
          }}
        />
      )}

      {token && galleryId && !showDisclaimer && !showResultModal && (
        <>
          <CustomCameraComponent
            galleryId={galleryId}
            pin="" 
            token={token}
            onImageUpload={handleImageUpload}
          />
          <Box mt={10}>
            <BackgroundSlider token={token} onSelect={handleBackgroundSelect} />
          </Box>
        </>
      )}

      <Dialog open={showResultModal} disableEscapeKeyDown maxWidth="xs" fullWidth>
        <DialogTitle sx={{ textAlign: "center" }}>
          {processing ? "Bild wird verarbeitet…" : "Bild aufgenommen"}
        </DialogTitle>
        <DialogContent sx={{ textAlign: "center" }}>
          {processing ? (
            <CircularProgress />
          ) : (
            <Box
              component="img"
              src={capturedImage ? capturedImage : itlabImage}
              alt="Aufgenommenes Bild"
              sx={{
                width: "100%",
                borderRadius: 2,
                boxShadow: 3,
                '@media print': {
                  transform: 'rotate(90deg)',
                  transformOrigin: 'center center',
                },
              }}
            />
          )}
        </DialogContent>
        {!processing && (
          <DialogActions sx={{ justifyContent: "center", p: 2, gap: 2 }}>
            <Button variant="outlined" onClick={handleRetry}>
              Erneut Versuchen
            </Button>
            <Button variant="contained" onClick={handleFinish}>
              🥳 Fertigstellen!
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
          width: 250,
          opacity: 0.8,
        }}
      />

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={() => setSnackbarOpen(false)}
        message={`Hurra, ${printCount} ${printCount === 1 ? 'Bild befindet' : 'Bilder befinden'} sich im Druck!`}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      />
    </Box>
  );
}
