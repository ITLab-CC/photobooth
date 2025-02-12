const express = require("express");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = 3000;

app.use(express.json({ limit: "50mb" }));

app.use(express.static(path.join(__dirname, "public")));

app.post("/upload", (req, res) => {
  const imageData = req.body.image;
  if (!imageData) {
    return res.status(400).json({ error: "No image data provided" });
  }
  const base64Data = imageData.replace(/^data:image\/\w+;base64,/, "");

  const fileName = `foto_${Date.now()}.png`;
  const imagesDir = path.join(__dirname, "public", "images");
  if (!fs.existsSync(imagesDir)) {
    fs.mkdirSync(imagesDir, { recursive: true });
  }
  const filePath = path.join(imagesDir, fileName);

  fs.writeFile(filePath, base64Data, "base64", (err) => {
    if (err) {
      console.error("Fehler beim Speichern:", err);
      return res
        .status(500)
        .json({ error: "Fehler beim Speichern des Bildes" });
    }

    const imageURL = `/images/${fileName}`;
    res.json({ url: imageURL });
  });
});

app.listen(PORT, () => {
  console.log(`Server läuft auf http://localhost:${PORT}`);
});
