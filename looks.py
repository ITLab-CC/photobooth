import os
from typing import Callable, Dict, Optional

import cv2
import numpy as np
import torch
from PIL import Image

from animegan2_model import Generator

# Looks a guest can pick. "none" leaves the photo as it is.
# The first four are classic image filters; "anime" and "painting" run a small local neural network.
LOOKS = ("none", "comic", "sketch", "watercolor", "popart", "anime", "painting")

# The networks are fully convolutional, so any size works; larger photos are processed at this
# longest side and scaled back up, which keeps them fast and light on GPU memory.
NETWORK_MAX_SIDE = 1024

_NETWORK_WEIGHTS = {
    "anime": "models/animegan2_face_paint_512_v2.pt",
    "painting": "models/animegan2_paprika.pt",
}
_networks: Dict[str, Generator] = {}


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _network(look: str) -> Generator:
    if look not in _networks:
        net = Generator()
        net.load_state_dict(torch.load(_NETWORK_WEIGHTS[look], map_location="cpu"))
        _networks[look] = net.to(_device()).eval()
    return _networks[look]


def _run_network(img: Image.Image, look: str) -> Image.Image:
    original_size = img.size
    scale = min(1.0, NETWORK_MAX_SIDE / max(original_size))
    # Two downsamplings inside the network need sides divisible by 4.
    width = max(4, int(round(original_size[0] * scale / 4)) * 4)
    height = max(4, int(round(original_size[1] * scale / 4)) * 4)
    small = img.resize((width, height), Image.Resampling.LANCZOS)

    array = np.asarray(small, dtype=np.float32) / 127.5 - 1.0
    tensor = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0).to(_device())
    with torch.no_grad():
        output = _network(look)(tensor, align_corners=True)
    result = ((output[0].permute(1, 2, 0).clamp(-1, 1).cpu().numpy() + 1.0) * 127.5).astype(np.uint8)
    return Image.fromarray(result).resize(original_size, Image.Resampling.LANCZOS)


def _to_bgr(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def _from_bgr(array: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(array, cv2.COLOR_BGR2RGB))


def _comic(img: Image.Image) -> Image.Image:
    bgr = _to_bgr(img)
    smooth = bgr
    for _ in range(3):
        smooth = cv2.bilateralFilter(smooth, d=9, sigmaColor=50, sigmaSpace=9)
    # Flatten brightness into a few bands but keep hue, so colors stay natural.
    hsv = cv2.cvtColor(smooth, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 2] = np.floor(hsv[..., 2] / 48.0) * 48.0 + 24.0
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.2, 0, 255)
    flat = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)
    gray = cv2.medianBlur(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), 7)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 6)
    return _from_bgr(cv2.bitwise_and(flat, flat, mask=edges))


def _sketch(img: Image.Image) -> Image.Image:
    # Classic pencil effect: divide the gray image by its blurred negative (color dodge).
    gray = cv2.cvtColor(_to_bgr(img), cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(255 - gray, (0, 0), sigmaX=max(3.0, gray.shape[1] / 90))
    sketch = cv2.divide(gray, 255 - blurred, scale=256)
    # A little gamma makes the pencil lines read clearly on a bright screen and on paper.
    darker = np.clip((sketch.astype(np.float32) / 255.0) ** 1.8 * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(darker).convert("RGB")


def _watercolor(img: Image.Image) -> Image.Image:
    return _from_bgr(cv2.stylization(_to_bgr(img), sigma_s=60, sigma_r=0.45))


def _popart(img: Image.Image) -> Image.Image:
    hsv = cv2.cvtColor(_to_bgr(img), cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.7, 0, 255)  # vivid colors
    hsv[..., 2] = (np.floor(hsv[..., 2] / 64.0) * 64.0 + 32.0)  # four brightness levels
    bgr = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return _from_bgr(bgr)


_FILTERS: Dict[str, Callable[[Image.Image], Image.Image]] = {
    "comic": _comic,
    "sketch": _sketch,
    "watercolor": _watercolor,
    "popart": _popart,
}


def apply_look(img: Image.Image, look: str) -> Image.Image:
    """Return the photo in the chosen look (RGB). Unknown looks raise ValueError."""
    if look not in LOOKS:
        raise ValueError(f"Unknown look: {look}")
    if look == "none":
        return img
    rgb = img.convert("RGB")
    if look in _FILTERS:
        return _FILTERS[look](rgb)
    return _run_network(rgb, look)
