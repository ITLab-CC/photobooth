import cv2
import numpy as np
import os
import random
import urllib.request
from datetime import datetime
from PIL import Image
from typing import Optional, Tuple, Union

# -----------------------------
# EXIF orientation handling (Pillow)
# -----------------------------
def load_with_exif(path):
    """
    Loads an image and applies EXIF orientation, returning a PIL Image (RGB).
    Requires Pillow; if not available, falls back to cv2.imread -> PIL.
    """
    try:
        from PIL import Image, ImageOps
        pil_img = Image.open(path)
        pil_img = ImageOps.exif_transpose(pil_img)  # normalize orientation
        return pil_img.convert("RGB")
    except Exception:
        # Fallback to cv2 then convert to PIL RGB
        bgr = cv2.imread(path, cv2.IMREAD_COLOR)
        if bgr is None:
            return None
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

# -----------------------------
# Model helper
# -----------------------------
def ensure_dnn_model(prototxt_path, model_path):
    proto_url = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
    model_url = "https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"

    os.makedirs(os.path.dirname(prototxt_path) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(model_path) or ".", exist_ok=True)

    if not os.path.isfile(prototxt_path):
        print(f"[model] Downloading prototxt -> {prototxt_path}")
        urllib.request.urlretrieve(proto_url, prototxt_path)
    if not os.path.isfile(model_path):
        print(f"[model] Downloading caffemodel -> {model_path}")
        urllib.request.urlretrieve(model_url, model_path)

# -----------------------------
# I/O helpers
# -----------------------------
def load_smileys(smiley_dir, allowed_exts={".png"}):
    files = []
    if os.path.isdir(smiley_dir):
        for f in os.listdir(smiley_dir):
            _, ext = os.path.splitext(f.lower())
            if ext in allowed_exts:
                files.append(os.path.join(smiley_dir, f))
    return files

def overlay_png(bg, fg, x, y):
    """
    Overlay fg (BGRA) onto bg (BGR) at top-left (x,y) using alpha blend.
    fg must already be scaled. Preserves bg size.
    """
    if fg is None:
        return bg
    if fg.shape[2] == 3:
        alpha = np.ones((fg.shape[0], fg.shape[1], 1), dtype=fg.dtype) * 255
        fg = np.concatenate([fg, alpha], axis=2)

    h, w = fg.shape[:2]
    H, W = bg.shape[:2]

    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(W, x + w), min(H, y + h)
    if x1 >= x2 or y1 >= y2:
        return bg

    fg_roi = fg[(y1 - y):(y2 - y), (x1 - x):(x2 - x)]
    bg_roi = bg[y1:y2, x1:x2]

    alpha = fg_roi[:, :, 3:4].astype(np.float32) / 255.0
    fg_rgb = fg_roi[:, :, :3].astype(np.float32)
    bg_rgb = bg_roi.astype(np.float32)

    out = alpha * fg_rgb + (1.0 - alpha) * bg_rgb
    bg[y1:y2, x1:x2] = np.clip(out, 0, 255).astype(np.uint8)
    return bg

def scale_smiley_preserve_aspect(smiley, target_box_w, target_box_h, scale=1.25):
    """
    Scales smiley to fit inside the face box while preserving aspect ratio.
    'scale' enlarges relative to the box (e.g., 1.25 = 25% larger than the box's limiting dimension).
    Returns resized BGRA image.
    """
    if smiley is None:
        return None
    if smiley.shape[2] == 3:
        # add full alpha if missing
        alpha = np.ones((smiley.shape[0], smiley.shape[1], 1), dtype=smiley.dtype) * 255
        smiley = np.concatenate([smiley, alpha], axis=2)

    h0, w0 = smiley.shape[:2]
    # Fit inside face box using the limiting dimension, preserve aspect ratio
    # We want the smiley roughly to cover the face box; so use min-based fit, then multiply by scale.
    fit_scale = min(target_box_w / w0, target_box_h / h0)
    fit_scale *= scale
    new_w = max(1, int(round(w0 * fit_scale)))
    new_h = max(1, int(round(h0 * fit_scale)))
    interp = cv2.INTER_AREA if new_w < w0 or new_h < h0 else cv2.INTER_LINEAR
    return cv2.resize(smiley, (new_w, new_h), interpolation=interp)

# -----------------------------
# Face detection (DNN on resized, mapped back)
# -----------------------------
def detect_faces_dnn_on_original(img_orig, net, conf_threshold):
    H, W = img_orig.shape[:2]
    resized = cv2.resize(img_orig, (300, 300))
    blob = cv2.dnn.blobFromImage(
        resized,
        scalefactor=1.0,
        size=(300, 300),
        mean=(104.0, 177.0, 123.0),
        swapRB=False,
        crop=False
    )
    net.setInput(blob)
    detections = net.forward()

    boxes, confs = [], []
    for i in range(detections.shape[2]):
        confidence = float(detections[0, 0, i, 2])
        if confidence >= conf_threshold:
            x1 = int(detections[0, 0, i, 3] * W)
            y1 = int(detections[0, 0, i, 4] * H)
            x2 = int(detections[0, 0, i, 5] * W)
            y2 = int(detections[0, 0, i, 6] * H)

            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(W - 1, x2), min(H - 1, y2)
            bw, bh = max(0, x2 - x1), max(0, y2 - y1)
            if bw > 0 and bh > 0:
                boxes.append((x1, y1, bw, bh))
                confs.append(confidence)
    return boxes, confs

def replace_faces_with_smileys_dnn(
    img_orig: Image.Image,
    smiley_dir: str = "./smileys",
    prototxt_path: str = "models/deploy.prototxt",
    model_path: str = "models/res10_300x300_ssd_iter_140000.caffemodel",
    conf_threshold: float = 0.85,
    face_scale: float = 1.25,
    random_seed: Optional[int] = int(datetime.now().timestamp()),
    print_detections: bool = True
) -> Image.Image:
    if random_seed is not None:
        random.seed(int(random_seed))

    # PIL (RGB) -> OpenCV (BGR)
    img_rgb = np.array(img_orig)  # RGB
    img_cv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)  # BGR

    H, W = img_cv.shape[:2]
    print(f"[info] original size: {W}x{H}")

    ensure_dnn_model(prototxt_path, model_path)
    net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)

    boxes, confs = detect_faces_dnn_on_original(img_cv, net, conf_threshold)

    if print_detections:
        if boxes:
            for (x, y, w, h), c in zip(boxes, confs):
                print(f"[det] x={x}, y={y}, w={w}, h={h}, conf={c*100:.1f}%")
        else:
            print("[det] Keine Gesichter über Schwelle gefunden.")

    if len(boxes) == 0:
        # No faces -> return the original PIL Image without any color change
        return img_orig

    out = img_cv.copy()  # BGR
    smiley_files = load_smileys(smiley_dir)
    if not smiley_files:
        raise FileNotFoundError(f"Keine Smiley-Bilder im Ordner gefunden: {smiley_dir}")

    for (x, y, w, h), c in zip(boxes, confs):
        smiley_path = random.choice(smiley_files)
        smiley = cv2.imread(smiley_path, cv2.IMREAD_UNCHANGED)  # BGRA or BGR
        if smiley is None:
            continue

        smiley_resized = scale_smiley_preserve_aspect(smiley, w, h, scale=face_scale)

        sh, sw = smiley_resized.shape[:2]
        cx = x + w // 2
        cy = y + h // 2
        place_x = cx - sw // 2
        place_y = cy - sh // 2

        out = overlay_png(out, smiley_resized, place_x, place_y)  # stays in BGR/BGRA

    # Final conversion back to PIL RGB
    # out is BGR (3 channels). overlay_png writes into 3-channel BGR even when fg is BGRA.
    rgb_out = cv2.cvtColor(out, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb_out)

if __name__ == "__main__":
    img_orig = load_with_exif("input.png")  # returns PIL Image (RGB)
    if img_orig is None:
        raise FileNotFoundError("Konnte Bild nicht laden")

    result = replace_faces_with_smileys_dnn(
        img_orig,
        smiley_dir="./smileys",
        prototxt_path="models/deploy.prototxt",
        model_path="models/res10_300x300_ssd_iter_140000.caffemodel",
        conf_threshold=0.85,
        face_scale=1.20,
        random_seed=int(datetime.now().timestamp()),
        print_detections=True
    )

    result.save("output.png")