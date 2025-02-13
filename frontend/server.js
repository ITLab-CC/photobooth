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

app.get("/images", (req, res) => {
  const imagesDir = path.join(__dirname, "public", "images");

  fs.readdir(imagesDir, (err, files) => {
    if (err) {
      return res.status(500).json({ error: "Fehler beim Laden der Bilder." });
    }

    const imageFiles = files.filter((file) =>
      /\.(jpg|jpeg|png|gif)$/i.test(file)
    );
    res.json(imageFiles);
  });
});

app.delete("/delete-image/:imageName", (req, res) => {
  const { imageName } = req.params;
  const filePath = path.join(__dirname, "public", "images", imageName);

  fs.unlink(filePath, (err) => {
    if (err) {
      return res.status(500).json({ error: "Fehler beim Löschen des Bildes." });
    }
    res.sendStatus(200);
  });
});
