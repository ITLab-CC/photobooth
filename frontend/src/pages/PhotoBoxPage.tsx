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
} from "@mui/material";
import { keyframes } from "@mui/system";
import PrintIcon from "@mui/icons-material/Print";
import AutoLogin from "../components/AutoLogin";
import DisclaimerModal from "../components/DisclaimerModal";
import PinModal from "../components/PinModal";
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
  setGalleryPin,
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

const printerAnimation = keyframes`
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
`;

export default function PhotoBoxPage() {
  const [token, setToken] = useState<string | null>(null);
  const [galleryId, setGalleryId] = useState<string | null>(null);
  const [showDisclaimer, setShowDisclaimer] = useState(true);
  const [showPinModal, setShowPinModal] = useState(false);
  const [userPin, setUserPin] = useState("");
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [showResultModal, setShowResultModal] = useState<boolean>(false);
  const [processing, setProcessing] = useState<boolean>(false);
  const [processedImageId, setProcessedImageId] = useState<string | null>(null);
  const [selectedBackgroundId, setSelectedBackgroundId] = useState<string | null>(null);
  const [frameId, setFrameId] = useState<string | null>(null);
  const [printingModalOpen, setPrintingModalOpen] = useState(false);

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

  const handleRetry = async () => {
    if (galleryId) {
      try {
        console.log("Lösche Galerie:", galleryId);
        await deleteGallery(token!, galleryId);
        console.log("Galerie erfolgreich gelöscht");
      } catch (error) {
        console.error("Fehler beim Löschen der Galerie:", error);
      }
    }
    setCapturedImage(null);
    setProcessedImageId(null);
    setProcessing(false);
    setShowResultModal(false);
    setUserPin("");
    setGalleryId(null);
    if (token) {
      try {
        const newGalleryResponse = await createGallery(token);
        console.log("Neue Galerie erstellt:", newGalleryResponse.gallery_id);
        setGalleryId(newGalleryResponse.gallery_id);
      } catch (error) {
        console.error("Fehler beim Erstellen der neuen Galerie:", error);
      }
    }
  };

  const handleFinish = () => {
    if (!userPin) {
      setShowPinModal(true);
      return;
    }
    setGalleryPin(token!, galleryId!, userPin)
      .then(() => {
        return printImage(token!, processedImageId!);
      })
      .then(() => {
        setPrintingModalOpen(true);
        setTimeout(() => {
          setPrintingModalOpen(false);
          window.location.reload();
        }, 3000);
      })
      .catch((err) => {
        console.error("Fehler beim Drucken:", err);
        alert("Fehler beim Drucken. Bitte versuche es erneut.");
        window.location.reload();
      });
  };

  const handlePinSubmit = (pin: string) => {
    setUserPin(pin);
    setShowPinModal(false);
    setGalleryPin(token!, galleryId!, pin)
      .then(() => {
        return printImage(token!, processedImageId!);
      })
      .then(() => {
        setPrintingModalOpen(true);
        setTimeout(() => {
          setPrintingModalOpen(false);
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
          <Box
            sx={{
              width: 680,
              backgroundColor: "white",
              color: "black",                 
              borderRadius: 2,
              p: 2,
              mb: 2,
              boxShadow: "2px 2px 6px rgba(0,0,0,0.3)", 
            }}
          >
            <Typography variant="h5" gutterBottom>
              IT-Lab - Photobooth 
            </Typography>
            <Typography variant="body1">
              Willkommen zur ENTEGA-Fotobox! 📸 Schlüpf in deinen Traumberuf, pose vor der Kamera und nimm dein persönliches Foto direkt mit! 🎓🚀
            </Typography>
          </Box>

          <CustomCameraComponent
            galleryId={galleryId}
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

      <PinModal
        open={showPinModal}
        onSubmit={handlePinSubmit}
        onCancel={() => {
          setShowPinModal(false);
        }}
      />

      <Dialog open={printingModalOpen} disableEscapeKeyDown maxWidth="xs" fullWidth>
        <DialogContent sx={{ textAlign: "center", p: 4 }}>
          <PrintIcon sx={{ fontSize: 80, animation: `${printerAnimation} 2s linear infinite` }} />
          <Typography variant="h6" sx={{ mt: 2 }}>
            Bild wird gedruckt
          </Typography>
        </DialogContent>
      </Dialog>

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
    </Box>
  );
}
