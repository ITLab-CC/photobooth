import io
import base64
from PIL import Image

def img_to_base64(img_path: str) -> str:
    with open(img_path, "rb") as img_file:
        # Instead of using tobytes(), we read the raw bytes from the file.
        img_bytes = img_file.read()
        img_str = base64.b64encode(img_bytes).decode()
        return img_str

def from_base64(base64_str: str) -> Image.Image:
    """
    Create a PIL Image object from a base64 string.
    """
    try:
        image_bytes = base64.b64decode(base64_str)
        image_file = io.BytesIO(image_bytes)
        pil_image = Image.open(image_file).convert("RGBA")
    except Exception:
        raise ValueError("Invalid base64 string; cannot convert to image.")
    return pil_image

img_path = "img.png"
img_str = img_to_base64(img_path)

# Write base64 string to a file
with open("img_base64.txt", "w") as f:
    f.write(img_str)

# Reconstruct the image from the base64 string and save it
img = from_base64(img_str)
img.save("img_from_base64.png")
