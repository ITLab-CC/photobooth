import io
import json
import os
import threading
import urllib.request
import uuid
import zipfile
from typing import Dict, List, NamedTuple, Optional

import cv2
import numpy as np
import onnx
import onnxruntime as ort
from onnx import numpy_helper
from PIL import Image

from face_props import detect_faces

# Models are large (about 730 MB together) and not part of the repository.
# NOTE: inswapper_128 is released by its authors (InsightFace) for non-commercial research use only.
MODELS_DIR = os.getenv("FACE_MODELS_DIR", "face-models")
FACES_DIR = os.getenv("FACES_DIR", "faces")

SWAPPER_URL = "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx"
RECOGNITION_ZIP_URL = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
SWAPPER_FILE = "inswapper_128.onnx"
RECOGNITION_FILE = "w600k_r50.onnx"

# Where the five landmarks sit in a face crop, as used when the networks were trained.
_ARCFACE_DST = np.array(
    [[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366], [41.5493, 92.3655], [70.7299, 92.2041]],
    dtype=np.float32,
)
SWAP_SIZE = 128
RECOGNITION_SIZE = 112

_lock = threading.Lock()
_swapper: Optional[ort.InferenceSession] = None
_recognizer: Optional[ort.InferenceSession] = None
_emap: Optional[np.ndarray] = None
_download_error: Optional[str] = None


class StoredFace(NamedTuple):
    face_id: str
    name: str


def models_ready() -> bool:
    return all(os.path.isfile(os.path.join(MODELS_DIR, f)) for f in (SWAPPER_FILE, RECOGNITION_FILE))


def download_error() -> Optional[str]:
    return _download_error


def ensure_models() -> None:
    """Download the models once. Safe to call from a background thread; failures are kept for the dashboard."""
    global _download_error
    if models_ready():
        return
    try:
        os.makedirs(MODELS_DIR, exist_ok=True)
        swapper_path = os.path.join(MODELS_DIR, SWAPPER_FILE)
        if not os.path.isfile(swapper_path):
            urllib.request.urlretrieve(SWAPPER_URL, swapper_path + ".part")
            os.replace(swapper_path + ".part", swapper_path)
        recognition_path = os.path.join(MODELS_DIR, RECOGNITION_FILE)
        if not os.path.isfile(recognition_path):
            zip_path = os.path.join(MODELS_DIR, "buffalo_l.zip")
            urllib.request.urlretrieve(RECOGNITION_ZIP_URL, zip_path)
            with zipfile.ZipFile(zip_path) as archive:
                with archive.open(RECOGNITION_FILE) as source, open(recognition_path + ".part", "wb") as target:
                    target.write(source.read())
            os.replace(recognition_path + ".part", recognition_path)
            os.remove(zip_path)
        _download_error = None
    except Exception as e:  # network down, disk full, ...
        _download_error = str(e)
        print(f"Face swap models could not be downloaded: {e}")


def _load() -> None:
    global _swapper, _recognizer, _emap
    with _lock:
        if _swapper is not None:
            return
        if not models_ready():
            raise RuntimeError("Die Gesichtstausch-Modelle sind noch nicht geladen.")
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        available = [p for p in providers if p in ort.get_available_providers()]
        swapper_path = os.path.join(MODELS_DIR, SWAPPER_FILE)
        _recognizer = ort.InferenceSession(os.path.join(MODELS_DIR, RECOGNITION_FILE), providers=available)
        _emap = numpy_helper.to_array(onnx.load(swapper_path).graph.initializer[-1])
        _swapper = ort.InferenceSession(swapper_path, providers=available)


def _align(img_bgr: np.ndarray, kps: np.ndarray, size: int):
    """Warp the face so its landmarks match the reference positions. Returns the crop and the 2x3 matrix."""
    if size % 112 == 0:
        ratio, shift = size / 112.0, 0.0
    else:
        ratio, shift = size / 128.0, 8.0 * size / 128.0
    destination = _ARCFACE_DST * ratio
    destination[:, 0] += shift
    matrix, _ = cv2.estimateAffinePartial2D(kps.astype(np.float32), destination, method=cv2.LMEDS)
    return cv2.warpAffine(img_bgr, matrix, (size, size), borderValue=0.0), matrix


def _embedding(img_bgr: np.ndarray, kps: np.ndarray) -> np.ndarray:
    _load()
    assert _recognizer is not None
    crop, _ = _align(img_bgr, kps, RECOGNITION_SIZE)
    blob = cv2.dnn.blobFromImage(crop, 1.0 / 127.5, (RECOGNITION_SIZE, RECOGNITION_SIZE), (127.5, 127.5, 127.5), swapRB=True)
    vector = _recognizer.run(None, {_recognizer.get_inputs()[0].name: blob})[0].reshape(-1)
    return vector / np.linalg.norm(vector)


def _to_bgr(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------- stored faces (no original photos)
def _face_paths(face_id: str):
    return os.path.join(FACES_DIR, f"{face_id}.json"), os.path.join(FACES_DIR, f"{face_id}.png")


def add_face(photo: Image.Image, name: str) -> StoredFace:
    """
    Store the identity of the one face in the photo. Only the 512 numbers that describe the face and a small
    thumbnail are kept; the photo itself is discarded. Raises ValueError if there is not exactly one clear face.
    """
    img = _to_bgr(photo)
    faces = detect_faces(img)
    if len(faces) == 0:
        raise ValueError("Im Foto wurde kein Gesicht erkannt.")
    if len(faces) > 1:
        raise ValueError("Im Foto sind mehrere Gesichter zu sehen. Bitte ein Foto mit nur einer Person nehmen.")

    face = faces[0]
    vector = _embedding(img, face.kps)

    x, y, w, h = face.box
    pad = 0.35
    left, top = max(0, int(x - pad * w)), max(0, int(y - pad * h))
    right, bottom = min(img.shape[1], int(x + (1 + pad) * w)), min(img.shape[0], int(y + (1 + pad) * h))
    thumbnail = photo.convert("RGB").crop((left, top, right, bottom))
    thumbnail.thumbnail((256, 256), Image.Resampling.LANCZOS)

    face_id = f"Face-{uuid.uuid4()}"
    os.makedirs(FACES_DIR, exist_ok=True)
    json_path, png_path = _face_paths(face_id)
    thumbnail.save(png_path, format="PNG")
    with open(json_path, "w") as f:
        json.dump({"name": name, "embedding": vector.tolist()}, f)
    return StoredFace(face_id, name)


def list_faces() -> List[StoredFace]:
    if not os.path.isdir(FACES_DIR):
        return []
    result = []
    for filename in sorted(os.listdir(FACES_DIR)):
        if filename.endswith(".json"):
            with open(os.path.join(FACES_DIR, filename)) as f:
                result.append(StoredFace(filename[:-5], json.load(f)["name"]))
    return result


def rename_face(face_id: str, name: str) -> bool:
    json_path, _ = _face_paths(_safe_id(face_id))
    if not os.path.isfile(json_path):
        return False
    with open(json_path) as f:
        data = json.load(f)
    data["name"] = name
    with open(json_path, "w") as f:
        json.dump(data, f)
    return True


def delete_face(face_id: str) -> bool:
    json_path, png_path = _face_paths(_safe_id(face_id))
    existed = os.path.isfile(json_path)
    for path in (json_path, png_path):
        if os.path.isfile(path):
            os.remove(path)
    return existed


def face_thumbnail(face_id: str) -> Optional[bytes]:
    _, png_path = _face_paths(_safe_id(face_id))
    if not os.path.isfile(png_path):
        return None
    with open(png_path, "rb") as f:
        return f.read()


def _safe_id(face_id: str) -> str:
    # ids come from the URL and become file names
    if not face_id.startswith("Face-") or not all(c.isalnum() or c == "-" for c in face_id):
        raise ValueError("Invalid face id")
    return face_id


def _load_embedding(face_id: str) -> np.ndarray:
    json_path, _ = _face_paths(_safe_id(face_id))
    if not os.path.isfile(json_path):
        raise KeyError(face_id)
    with open(json_path) as f:
        return np.array(json.load(f)["embedding"], dtype=np.float32)


# ---------------------------------------------------------------- the swap
def _swap_one(frame: np.ndarray, kps: np.ndarray, latent: np.ndarray) -> np.ndarray:
    assert _swapper is not None
    crop, matrix = _align(frame, kps, SWAP_SIZE)
    blob = cv2.dnn.blobFromImage(crop, 1.0 / 255.0, (SWAP_SIZE, SWAP_SIZE), (0, 0, 0), swapRB=True)
    output = _swapper.run([_swapper.get_outputs()[0].name], {_swapper.get_inputs()[0].name: blob, _swapper.get_inputs()[1].name: latent})[0]
    swapped = np.clip(255 * output.transpose((0, 2, 3, 1))[0], 0, 255).astype(np.uint8)[:, :, ::-1]

    # The network only sees 128 px, so the result is soft: sharpen it a little, and bring its skin tone
    # part of the way towards the guest's so the face does not look like a sticker.
    mask = _face_mask()
    swapped = _sharpen(swapped)
    swapped = _match_skin(swapped, crop, mask)

    # Paste back: the swapped crop is warped to the original position and blended through the soft oval mask,
    # so only the face area changes and the edge fades into the original skin.
    inverse = cv2.invertAffineTransform(matrix)
    height, width = frame.shape[:2]
    warped = cv2.warpAffine(swapped, inverse, (width, height), flags=cv2.INTER_CUBIC, borderValue=0.0)
    warped_mask = cv2.warpAffine(mask, inverse, (width, height), flags=cv2.INTER_LINEAR, borderValue=0.0)[..., None]
    return (warped.astype(np.float32) * warped_mask + frame.astype(np.float32) * (1.0 - warped_mask)).astype(np.uint8)


def _face_mask() -> np.ndarray:
    """Soft oval over forehead, cheeks and chin in the 128 px crop. It must stop at the chin: below it the
    crop shows the stored photo's neck and collar, which must not end up on the guest."""
    mask = np.zeros((SWAP_SIZE, SWAP_SIZE), dtype=np.float32)
    cv2.ellipse(mask, (SWAP_SIZE // 2, int(SWAP_SIZE * 0.49)), (int(SWAP_SIZE * 0.39), int(SWAP_SIZE * 0.38)), 0, 0, 360, 1.0, -1)
    return cv2.GaussianBlur(mask, (0, 0), SWAP_SIZE * 0.05)


def _sharpen(img: np.ndarray, amount: float = 0.7) -> np.ndarray:
    blurred = cv2.GaussianBlur(img, (0, 0), 1.2)
    return cv2.addWeighted(img, 1.0 + amount, blurred, -amount, 0)


def _match_skin(swapped: np.ndarray, original: np.ndarray, mask: np.ndarray, strength: float = 0.6) -> np.ndarray:
    """Move the swapped face's average Lab color towards the original face's inside the mask."""
    inside = mask > 0.5
    swapped_lab = cv2.cvtColor(swapped, cv2.COLOR_BGR2LAB).astype(np.float32)
    original_lab = cv2.cvtColor(original, cv2.COLOR_BGR2LAB).astype(np.float32)
    shift = (original_lab[inside].mean(axis=0) - swapped_lab[inside].mean(axis=0)) * strength
    swapped_lab += shift
    return cv2.cvtColor(np.clip(swapped_lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def swap_faces(photo: Image.Image, face_id: str) -> Image.Image:
    """
    Replace every face in the photo with the stored identity. Pose, gaze and expression stay those of the
    person in the photo. Returns the photo unchanged if no face is found.
    """
    _load()
    assert _emap is not None
    latent = _load_embedding(face_id).reshape(1, -1)
    latent = np.dot(latent, _emap)
    latent = (latent / np.linalg.norm(latent)).astype(np.float32)

    frame = _to_bgr(photo)
    faces = detect_faces(frame)
    if not faces:
        return photo
    result = frame
    for face in faces:
        result = _swap_one(result, face.kps, latent)
    return Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
