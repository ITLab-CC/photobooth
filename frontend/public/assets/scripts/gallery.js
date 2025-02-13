document.addEventListener("DOMContentLoaded", async () => {
  const imageGrid = document.getElementById("imageGrid");
  const imageModal = document.getElementById("imageModal");
  const modalImage = document.getElementById("modalImage");
  const closeModal = document.getElementById("closeModal");

  async function loadImages() {
    try {
      const response = await fetch("/images");
      const images = await response.json();

      imageGrid.innerHTML = "";

      images.forEach((image) => {
        const imageItem = document.createElement("div");
        imageItem.classList.add("imageItem");

        const img = document.createElement("img");
        img.src = `/images/${image}`;
        img.alt = "Gespeichertes Bild";
        img.addEventListener("click", () => openModal(img.src));

        const actions = document.createElement("div");
        actions.classList.add("imageActions");

        const downloadBtn = document.createElement("a");
        downloadBtn.href = `/images/${image}`;
        downloadBtn.download = image;
        downloadBtn.textContent = "⬇️";

        const deleteBtn = document.createElement("button");
        deleteBtn.textContent = "❌";
        deleteBtn.addEventListener("click", () => deleteImage(image));

        actions.appendChild(downloadBtn);
        actions.appendChild(deleteBtn);

        imageItem.appendChild(img);
        imageItem.appendChild(actions);

        imageGrid.appendChild(imageItem);
      });
    } catch (error) {
      console.error("Fehler beim Laden der Bilder:", error);
    }
  }

  function openModal(src) {
    modalImage.src = src;
    imageModal.classList.add("visible");
  }

  closeModal.addEventListener("click", () => {
    imageModal.classList.remove("visible");
  });

  async function deleteImage(imageName) {
    if (!confirm("Möchtest du dieses Bild wirklich löschen?")) return;

    try {
      const response = await fetch(`/delete-image/${imageName}`, {
        method: "DELETE",
      });

      if (response.ok) {
        loadImages();
      } else {
        alert("Fehler beim Löschen des Bildes.");
      }
    } catch (error) {
      console.error("Fehler beim Löschen:", error);
    }
  }

  loadImages();
});
