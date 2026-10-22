import { useEffect, useRef, useState } from "react";
import { Box, Button, Typography } from "@mui/material";
import { keyframes } from "@mui/system";
import CameraPreview from "./CameraPreview";
import PhotoCameraIcon from "@mui/icons-material/PhotoCamera";
import confetti from "canvas-confetti";
import { brand, previewSize, px } from "../theme";
import { previewProps } from "../api";
import { runtimeConfig } from "../config/event";
import { playChime, playGo, playShutter, playTick } from "../utils/sound";

const countPop = keyframes`
  from { opacity: 0; transform: scale(0.7); }
  to { opacity: 1; transform: scale(1); }
`;

const flashAnimation = keyframes`
  from { opacity: 1; }
  to { opacity: 0; }
`;

// How the live preview of the Magic accessories works: a small copy of the live image goes to the server a few
// times per second, which returns only the accessories as a transparent picture to lay over the live image.
const PREVIEW_WIDTH = 320;
const PREVIEW_PAUSE_MS = 80; // pause between two requests; the next one starts after the answer arrived

interface CustomCameraComponentProps {
  token: string;
  /** Magic style to show live over the camera image, or null for none. */
  liveStyle: string | null;
  /**
   * Width / height of the part of the frame that shows the photo. The live image and the saved photos are
   * cut to exactly this shape, so everybody who is in the live image is in the picture.
   */
  aspect: number;
  /** Photos taken in a row. With more than one, the guests pick the best afterwards. */
  seriesCount: number;
  /** Called with the base64 PNG of every photo of a complete series. */
  onPhotosCaptured: (photosBase64: string[]) => void;
  onError?: (message: string) => void;
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export default function CustomCameraComponent({
  token,
  liveStyle,
  aspect,
  seriesCount,
  onPhotosCaptured,
  onError,
}: CustomCameraComponentProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [isCapturing, setIsCapturing] = useState<boolean>(false);
  const [videoReady, setVideoReady] = useState<boolean>(false);
  const [flashActive, setFlashActive] = useState<boolean>(false);
  const [seriesLabel, setSeriesLabel] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const size = previewSize(aspect);

  // The accessories to lay over the live image (an object URL of the latest transparent picture).
  const [overlayUrl, setOverlayUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!liveStyle || !videoReady) {
      setOverlayUrl(null);
      return;
    }
    let cancelled = false;
    const run = async () => {
      while (!cancelled) {
        // While the picture is frozen for the shot, the last overlay stays where it is.
        if (videoRef.current?.paused) {
          await sleep(100);
          continue;
        }
        const frame = grabFrame(true);
        if (!frame) {
          await sleep(300);
          continue;
        }
        try {
          const blob = await previewProps(token, frame, liveStyle);
          if (cancelled) return;
          setOverlayUrl((previous) => {
            if (previous) URL.revokeObjectURL(previous);
            return URL.createObjectURL(blob);
          });
        } catch {
          await sleep(1000); // server busy or unreachable: try again shortly, the photo does not depend on it
        }
        await sleep(PREVIEW_PAUSE_MS);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
    // grabFrame reads the refs and `aspect` only; the effect restarts when the style or the shape changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [liveStyle, videoReady, aspect, token]);

  const reportError = (text: string) => {
    console.error(text);
    onError?.(text);
  };

  // Counts down to 0 ("Los!"); the picture freezes at 0 so everyone holds the pose for the shot.
  const countDown = async (from: number) => {
    for (let n = from; n >= 0; n--) {
      setCountdown(n);
      if (runtimeConfig.soundEnabled) {
        if (n === 0) playGo();
        else playTick();
      }
      if (n === 0) {
        videoRef.current?.pause();
      }
      await sleep(1000);
    }
  };

  // The current video frame as base64 PNG (or, for the live preview, a small JPEG), or null if the camera has no
  // picture yet.
  const grabFrame = (small = false): string | null => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.videoWidth === 0 || video.videoHeight === 0) {
      return null;
    }
    // The preview shows the video cropped to `aspect` around its centre; cut the photo the same way.
    const videoAspect = video.videoWidth / video.videoHeight;
    const sourceWidth = videoAspect > aspect ? video.videoHeight * aspect : video.videoWidth;
    const sourceHeight = videoAspect > aspect ? video.videoHeight : video.videoWidth / aspect;
    const sourceX = (video.videoWidth - sourceWidth) / 2;
    const sourceY = (video.videoHeight - sourceHeight) / 2;
    const outputWidth = small ? Math.min(PREVIEW_WIDTH, sourceWidth) : sourceWidth;
    canvas.width = Math.round(outputWidth);
    canvas.height = Math.round((outputWidth * sourceHeight) / sourceWidth);
    const context = canvas.getContext("2d");
    if (!context) {
      return null;
    }
    context.drawImage(video, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, canvas.width, canvas.height);
    if (small) {
      return canvas.toDataURL("image/jpeg", 0.6).replace(/^data:image\/jpeg;base64,/, "");
    }
    return canvas.toDataURL("image/png").replace(/^data:image\/png;base64,/, "");
  };

  const startSeries = async () => {
    if (!videoReady) {
      reportError("Die Kamera startet noch. Bitte kurz warten.");
      return;
    }
    setIsCapturing(true);
    const shots: string[] = [];
    try {
      for (let i = 0; i < seriesCount; i++) {
        if (seriesCount > 1) {
          setSeriesLabel(`Foto ${i + 1} von ${seriesCount}`);
        }
        if (i > 0) {
          if (runtimeConfig.soundEnabled) playChime();
          setMessage("Super! Gleich kommt das nächste.");
          await sleep(1500);
          setMessage(null);
        }
        await countDown(i === 0 ? 3 : 2);
        const shot = grabFrame();
        if (runtimeConfig.soundEnabled) playShutter();
        setCountdown(null);
        videoRef.current?.play();
        if (!shot) {
          reportError("Die Kamera liefert noch kein Bild. Bitte kurz warten.");
          break;
        }
        shots.push(shot);
        setFlashActive(true);
        setTimeout(() => setFlashActive(false), 600);
      }
    } finally {
      setCountdown(null);
      setSeriesLabel(null);
      setMessage(null);
      setIsCapturing(false);
      videoRef.current?.play();
    }
    if (shots.length === seriesCount) {
      confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 } });
      onPhotosCaptured(shots);
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        width: "100%",
        padding: "0 5%",
        boxSizing: "border-box",
      }}
    >
      <Box
        position="relative"
        sx={{
          width: `${size.width}px`,
          maxWidth: "100%",
          height: `${size.height}px`,
          margin: "8px auto",
          cursor: isCapturing ? "default" : "pointer",
        }}
        onClick={() => !isCapturing && startSeries()}
      >
      <CameraPreview
        videoRef={videoRef}
        width={size.width}
        height={size.height}
        onLoadedMetadata={() => {
          setVideoReady(true);
        }}
      />
      <canvas ref={canvasRef} style={{ display: "none" }} />

      {overlayUrl && liveStyle && (
        <Box
          component="img"
          src={overlayUrl}
          alt=""
          sx={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "fill",
            transform: "scaleX(-1)", // the live image is mirrored, so the accessories are too
            pointerEvents: "none",
            borderRadius: 2,
          }}
        />
      )}

      {/* Tapping anywhere on the live image takes the photo; the pill shows that and does not cover the faces.
          Hidden while counting down. */}
      {!isCapturing && (
        <Button
          variant="contained"
          aria-label={seriesCount > 1 ? `${seriesCount} Fotos machen` : "Foto machen"}
          startIcon={<PhotoCameraIcon sx={{ fontSize: "2rem !important" }} />}
          sx={{
            position: "absolute",
            bottom: px(20),
            left: "50%",
            transform: "translateX(-50%)",
            minHeight: px(84),
            minWidth: px(340),
            px: 4,
            fontSize: "1.5rem",
            borderRadius: 40,
            boxShadow: "0 8px 22px rgba(0, 0, 0, 0.35)",
          }}
        >
          {/* The second line tells the guests up front that several photos follow. */}
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", lineHeight: 1.2 }}>
            <span>{seriesCount > 1 ? "Fotos machen" : "Foto machen"}</span>
            {seriesCount > 1 && (
              <Typography component="span" sx={{ fontSize: "1rem", fontWeight: 400, opacity: 0.95 }}>
                {seriesCount} Fotos hintereinander, danach wählt ihr
              </Typography>
            )}
          </Box>
        </Button>
      )}
      
      {flashActive && (
        <Box
          position="absolute"
          sx={{
            top: 0,
            right: 0,
            bottom: 0,
            left: 0,
            backgroundColor: "white",
            animation: `${flashAnimation} 600ms ease-out`,
          }}
        />
      )}
 
      {seriesLabel && (
        <Typography
          variant="h5"
          sx={{
            position: "absolute",
            top: px(16),
            left: 0,
            right: 0,
            textAlign: "center",
            color: "#ffffff",
            fontWeight: 600,
            textShadow: "0 2px 12px rgba(37, 43, 63, 0.7)",
            pointerEvents: "none",
          }}
        >
          {seriesLabel}
        </Typography>
      )}

      {message && (
        <Box
          position="absolute"
          sx={{ inset: 0, display: "flex", alignItems: "center", justifyContent: "center", pointerEvents: "none" }}
        >
          <Typography
            variant="h4"
            sx={{ color: "#ffffff", fontWeight: 600, textAlign: "center", px: 3, textShadow: "0 3px 18px rgba(37, 43, 63, 0.7)" }}
          >
            {message}
          </Typography>
        </Box>
      )}

      {countdown !== null && (
        <Box
          position="absolute"
          aria-live="assertive"
          sx={{
            top: 0,
            right: 0,
            bottom: 0,
            left: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "none",
          }}
        >
          <Typography
            key={countdown}
            sx={{
              fontSize: "14rem",
              lineHeight: 1,
              fontWeight: 700,
              color: countdown === 0 ? brand.magic : "#ffffff",
              textShadow: "0 4px 24px rgba(37, 43, 63, 0.55)",
              animation: `${countPop} 0.5s cubic-bezier(0.22, 1, 0.36, 1)`,
              "@media (prefers-reduced-motion: reduce)": { animation: "none" },
            }}
          >
            {countdown >= 0 ? (countdown === 0 ? "Los!" : countdown) : ""}
          </Typography>
        </Box>
      )}
      </Box>

    </Box>
  );
}
