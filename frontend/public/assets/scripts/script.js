const video = document.getElementById("video");
const cameraTriggerOverlay = document.getElementById("cameraTriggerOverlay");
const countdownOverlay = document.getElementById("countdownOverlay");
const countdownText = document.getElementById("countdownText");
const flashOverlay = document.getElementById("flashOverlay");

const resultContainer = document.getElementById("resultContainer");
const capturedImage = document.getElementById("capturedImage");
const qrCodeContainer = document.getElementById("qrCode");
const timerElement = document.getElementById("timer");

window.addEventListener("DOMContentLoaded", () => {
  startCamera();

  cameraTriggerOverlay.addEventListener("click", () => {
    startCountdown(5);
  });
});

async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
  } catch (err) {
    console.error("Fehler beim Zugriff auf die Kamera:", err);
    alert("Kamera-Zugriff verweigert oder nicht verfügbar.");
  }
}

function startCountdown(seconds) {
  let counter = seconds;

  cameraTriggerOverlay.style.display = "none";

  countdownOverlay.classList.add("showOverlay");

  updateCountdownText(counter);

  const intervalId = setInterval(() => {
    counter--;
    if (counter > 0) {
      updateCountdownText(counter);
    } else {
      clearInterval(intervalId);

      updateCountdownText("GO");

      setTimeout(() => {
        launchFireworks();
        cameraFlash();
        playShutterSound();
        countdownOverlay.classList.remove("showOverlay");
        captureImage();
      }, 1000);
    }
  }, 1000);
}

function updateCountdownText(value) {
  countdownText.textContent = value;

  countdownText.style.animation = "none";
  countdownText.offsetHeight;
  countdownText.style.animation = "popUp 0.5s ease";
}

function launchFireworks() {
  const duration = 3000;
  const end = Date.now() + duration;
  const colors = ["#2596be", "#ffffff", "#FFA500", "#008000"];

  (function frame() {
    confetti({
      particleCount: 6,
      angle: 60,
      spread: 55,
      origin: { x: 0 },
      colors,
    });
    confetti({
      particleCount: 6,
      angle: 120,
      spread: 55,
      origin: { x: 1 },
      colors,
    });
    if (Date.now() < end) requestAnimationFrame(frame);
  })();
}

function cameraFlash() {
  flashOverlay.classList.remove("flash");
  void flashOverlay.offsetWidth;
  flashOverlay.classList.add("flash");
}

function playShutterSound() {
  const audio = new Audio("assets/sounds/shutter.mp3");
  audio.play().catch((err) => {
    console.warn("Audio nicht abspielbar:", err);
  });
}

function captureImage() {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  canvas.width = 1920;
  canvas.height = 1080;
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const dataUrl = canvas.toDataURL("image/png");

  showResult(dataUrl);
  uploadImage(dataUrl);
}

function showResult(dataUrl) {
  resultContainer.style.display = "block";
  capturedImage.src = dataUrl;
}

async function uploadImage(dataUrl) {
  try {
    const response = await fetch("/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: dataUrl }),
    });
    if (!response.ok) throw new Error("Fehler beim Hochladen.");

    const result = await response.json();
    const imageUrl = window.location.origin + result.url;
    console.log("Bild gespeichert unter:", imageUrl);

    generateQRCode(imageUrl);
    startResultCountdown(30);
  } catch (err) {
    console.error("Fehler:", err);
    alert("Fehler beim Hochladen des Bildes.");
  }
}

function generateQRCode(url) {
  qrCodeContainer.innerHTML = "";
  new QRCode(qrCodeContainer, {
    text: url,
    width: 400,
    height: 400,
  });
}

function startResultCountdown(seconds) {
  let counter = seconds;
  timerElement.textContent = `Verbleibende Zeit: ${counter} Sekunden`;

  const interval = setInterval(() => {
    counter--;
    timerElement.textContent = `Verbleibende Zeit: ${counter} Sekunden`;
    if (counter <= 0) {
      clearInterval(interval);
      resetView();
    }
  }, 1000);
}

function resetView() {
  resultContainer.style.display = "none";
  timerElement.textContent = "";
  qrCodeContainer.innerHTML = "";
  cameraTriggerOverlay.style.display = "flex";
}
