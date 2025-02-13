Hier ist eine Markdown-Dokumentation für das gesamte Frontend deiner **IT LAB PHOTOBOOTH**-Anwendung.

---

# 📸 IT LAB PHOTOBOOTH - Frontend Dokumentation

## 📌 Inhaltsverzeichnis

- [Projektübersicht](#projektübersicht)
- [Dateistruktur](#dateistruktur)
- [HTML-Struktur](#html-struktur)
- [CSS-Styling](#css-styling)
- [JavaScript-Funktionen](#javascript-funktionen)
- [Galerie-Seite](#galerie-seite)
- [Laufende Probleme & Lösungen](#laufende-probleme--lösungen)

---

## 📍 Projektübersicht

Die **IT LAB PHOTOBOOTH** ist eine Web-Anwendung, die eine Kamera streamt und Screenshots als Bilder speichert. Anschließend können diese als QR-Code geteilt oder aus einer Galerie angezeigt, heruntergeladen oder gelöscht werden.

**Technologien:**

- HTML5
- CSS3
- JavaScript (Vanilla)
- Node.js mit Express.js (für das Backend)

---

## 📂 Dateistruktur

```plaintext
📦 it-lab-photobooth
 ┣ 📂 public
 ┃ ┣ 📂 assets
 ┃ ┃ ┣ 📂 img            # Bilder für UI-Elemente (Icons)
 ┃ ┃ ┣ 📂 styles         # CSS-Dateien
 ┃ ┃ ┣ 📂 scripts        # JavaScript-Dateien
 ┃ ┃ ┣ 📂 sounds         # Shutter-Soundeffekte
 ┃ ┣ 📂 images           # Gespeicherte Fotos (wird durch das Backend verwaltet)
 ┃ ┣ 📜 index.html       # Hauptseite mit Kamera
 ┃ ┣ 📜 gallery.html     # Galerie-Seite für gespeicherte Bilder
 ┣ 📜 server.js          # Node.js-Server für Speicherung & Verwaltung
 ┣ 📜 package.json       # Node.js-Abhängigkeiten
 ┗ 📜 README.md          # Dokumentation
```

---

## 🏗️ HTML-Struktur

### 🔹 **index.html**

Die Hauptseite enthält:

- **Header**: Titel der Anwendung
- **Video-Container**: Zeigt den Live-Kamera-Feed
- **Countdown-Overlay**: Zeigt den Countdown für die Fotoaufnahme
- **Flash-Effekt**: Simuliert einen Kamera-Blitz
- **Ergebnisbereich**: Zeigt das aufgenommene Bild + QR-Code
- **Footer**: Navigation zur Galerie

📜 **Wichtige Elemente in `index.html`**

```html
<video id="video" autoplay playsinline></video>
<div id="cameraTriggerOverlay">
  <img src="assets/img/icon_camera.png" alt="Kamera-Icon" />
  <p>Klicke, um ein Foto zu machen</p>
</div>
<img id="capturedImage" src="" alt="Aufgenommenes Bild" />
<div id="qrCode"></div>
```

---

## 🎨 CSS-Styling (`style.css`)

### 📌 **Wichtige Styles**

- **Video-Container:** Kamera wird auf **Full HD (1920x1080)** skaliert.
- **Countdown-Overlay:** Countdown-Animation für Fototimer.
- **Flash-Effekt:** Simuliert einen Foto-Blitz (`@keyframes cameraFlash`).
- **Result-Container:** Enthält das aufgenommene Bild und den QR-Code.
- **Galerie-Grid:** Zeigt alle gespeicherten Bilder in einer flexiblen Grid-Darstellung.

📜 **Beispiel: Styling für den Kamera-Overlay**

```css
#cameraTriggerOverlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 20;
}
```

---

## ⚙️ JavaScript-Funktionen (`script.js`)

### 📌 **1. Kamera starten**

```js
async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
  } catch (err) {
    console.error("Fehler beim Zugriff auf die Kamera:", err);
    alert("Kamera-Zugriff verweigert oder nicht verfügbar.");
  }
}
```

### 📌 **2. Countdown starten**

```js
function startCountdown(seconds) {
  let counter = seconds;
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
        cameraFlash();
        captureImage();
      }, 1000);
    }
  }, 1000);
}
```

### 📌 **3. Bild aufnehmen und hochladen**

```js
function captureImage() {
  const canvas = document.createElement("canvas");
  canvas.width = 1920;
  canvas.height = 1080;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const dataUrl = canvas.toDataURL("image/png");
  uploadImage(dataUrl);
}
```

### 📌 **4. QR-Code generieren**

```js
function generateQRCode(url) {
  qrCodeContainer.innerHTML = "";
  new QRCode(qrCodeContainer, { text: url, width: 400, height: 400 });
}
```

---

## 🖼️ Galerie-Seite (`gallery.html` + `gallery.js`)

📜 **HTML-Grundstruktur**

```html
<div id="imageGrid"></div>
<div id="imageModal" class="hidden">
  <span id="closeModal">&times;</span>
  <img id="modalImage" src="" alt="Großansicht" />
</div>
```

📜 **Galerie laden (`gallery.js`)**

```js
async function loadImages() {
  const response = await fetch("/images");
  const images = await response.json();
  images.forEach((image) => {
    const img = document.createElement("img");
    img.src = `/images/${image}`;
    img.addEventListener("click", () => openModal(img.src));
    imageGrid.appendChild(img);
  });
}
```

📜 **Bild löschen**

```js
async function deleteImage(imageName) {
  if (!confirm("Möchtest du dieses Bild wirklich löschen?")) return;
  await fetch(`/delete-image/${imageName}`, { method: "DELETE" });
  loadImages();
}
```

---

## 🔥 Laufende Probleme & Lösungen

| Problem                          | Lösung                                                                              |
| -------------------------------- | ----------------------------------------------------------------------------------- |
| **Kamera wird nicht angezeigt**  | Überprüfe Kamera-Berechtigungen in Chrome unter `chrome://settings/content/camera`. |
| **QR-Code wird nicht generiert** | Prüfe, ob `qrcode.min.js` korrekt eingebunden ist.                                  |
| **Bilder werden nicht geladen**  | Stelle sicher, dass der `images/` Ordner existiert und `server.js` läuft.           |

---

🚀 **Weitere Verbesserungen:**

- GIF-Generierung aus mehreren Bildern
- Cloud-Speicherung der Bilder
- Mehr Kamera-Einstellungen

🎯 **Letzte Schritte**
Starte den Server mit:

```bash
node server.js
```

Rufe die Kamera unter `http://localhost:3000/index.html` und die Galerie unter `http://localhost:3000/gallery.html` auf. 📷✨

---
