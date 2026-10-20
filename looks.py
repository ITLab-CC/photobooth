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

# The networks are fully convolutional, so any size works, but each was trained on small images
# (faces at 512 px, paintings at about 256 px). Fed larger photos they barely change anything, so
# the photo is shrunk to this longest side first and scaled back up afterwards.
NETWORK_MAX_SIDE = {"anime": 512, "painting": 384}

# The classic filters use fixed pixel sizes, so they run at one working size and are scaled back up.
# Otherwise a 1920 px camera frame would look completely different from a 512 px test image.
FILTER_WORK_SIDE = 640

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
    scale = min(1.0, NETWORK_MAX_SIDE[look] / max(original_size))
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
    for _ in range(4):
        smooth = cv2.bilateralFilter(smooth, d=9, sigmaColor=45, sigmaSpace=9)
    # Flatten brightness into four bands but keep the hue, so colors stay natural and vivid.
    hsv = cv2.cvtColor(smooth, cv2.COLOR_BGR2HSV).astype(np.float32)
    bands = np.floor(hsv[..., 2] / 64.0)
    hsv[..., 2] = bands * 64.0 + 40.0
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.35, 0, 255)
    flat = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)

    # Halftone dots in the darkest band, like printed comics.
    yy, xx = np.mgrid[0 : flat.shape[0], 0 : flat.shape[1]]
    dots = (np.sin(xx * 0.9) * np.sin(yy * 0.9)) > 0.15
    flat[(bands == 0) & dots] *= 0.55

    gray = cv2.medianBlur(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), 5)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 7)
    edges = cv2.erode(edges, np.ones((2, 2), np.uint8))  # thicker ink lines
    return _from_bgr(cv2.bitwise_and(flat.astype(np.uint8), flat.astype(np.uint8), mask=edges))


def _sketch(img: Image.Image) -> Image.Image:
    # Classic pencil effect: divide the gray image by its blurred negative (color dodge).
    gray = cv2.cvtColor(_to_bgr(img), cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(255 - gray, (0, 0), sigmaX=max(3.0, gray.shape[1] / 90))
    sketch = cv2.divide(gray, 255 - blurred, scale=256)
    # A little gamma makes the pencil lines read clearly on a bright screen and on paper.
    darker = np.clip((sketch.astype(np.float32) / 255.0) ** 1.8 * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(darker).convert("RGB")


def _watercolor(img: Image.Image) -> Image.Image:
    bgr = _to_bgr(img)
    painted = cv2.stylization(bgr, sigma_s=120, sigma_r=0.35)
    painted = cv2.edgePreservingFilter(painted, flags=1, sigma_s=60, sigma_r=0.4)
    # Washed-out pigment on paper: lift toward white and add faint paper grain.
    rng = np.random.default_rng(1)
    grain = rng.normal(0, 5, painted.shape[:2]).astype(np.float32)[..., None]
    lifted = painted.astype(np.float32) * 0.82 + 255 * 0.18 + grain
    return _from_bgr(np.clip(lifted, 0, 255).astype(np.uint8))


# Warhol-style palette from dark to light (RGB).
_POP_PALETTE = np.array([(24, 30, 90), (214, 36, 124), (255, 140, 20), (255, 238, 70)], dtype=np.uint8)


def _popart(img: Image.Image) -> Image.Image:
    bgr = cv2.bilateralFilter(_to_bgr(img), d=9, sigmaColor=60, sigmaSpace=9)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # Spread the brightness evenly over the four colors, whatever the lighting.
    rank = cv2.equalizeHist(gray)
    levels = np.minimum(rank // 64, 3)
    colored = _POP_PALETTE[levels]
    edges = cv2.adaptiveThreshold(cv2.medianBlur(gray, 5), 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 8)
    colored[edges == 0] = (10, 10, 20)
    return Image.fromarray(colored)


_FILTERS: Dict[str, Callable[[Image.Image], Image.Image]] = {
    "comic": _comic,
    "sketch": _sketch,
    "watercolor": _watercolor,
    "popart": _popart,
}


def _at_work_size(filter_fn: Callable[[Image.Image], Image.Image], img: Image.Image) -> Image.Image:
    original_size = img.size
    scale = FILTER_WORK_SIDE / max(original_size)
    if scale >= 1.0:
        return filter_fn(img)
    work = img.resize((max(1, int(original_size[0] * scale)), max(1, int(original_size[1] * scale))), Image.Resampling.LANCZOS)
    return filter_fn(work).resize(original_size, Image.Resampling.BICUBIC)


def apply_look(img: Image.Image, look: str) -> Image.Image:
    """Return the photo in the chosen look (RGB). Unknown looks raise ValueError."""
    if look not in LOOKS:
        raise ValueError(f"Unknown look: {look}")
    if look == "none":
        return img
    rgb = img.convert("RGB")
    if look in _FILTERS:
        return _at_work_size(_FILTERS[look], rgb)
    return _run_network(rgb, look)
