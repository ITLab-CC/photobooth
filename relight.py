from typing import Tuple

import cv2
import numpy as np
from PIL import Image

# OpenCV stores LAB as 8-bit: L runs 0-255 (not 0-100), a and b are offset by 128.
MAX_L_SHIFT = 25.0
MAX_AB_SHIFT = 12.0


def match_light(
    person: Image.Image,
    background: Image.Image,
    strength: float = 0.3,
    wrap: float = 0.5,
) -> Image.Image:
    """
    Make a cut-out person look less pasted onto a new background.

    1. Shift the person's brightness and color part of the way towards the background's
       average (strength 0 = untouched, 1 = same average). Capped, so skin tones stay natural.
    2. Light wrap: blend blurred background color into the person's inner edge, as if
       the background light spilled over the outline.

    person must be RGBA with the same size as background. Returns RGBA.
    """
    person_rgba = np.array(person.convert("RGBA"))
    alpha = person_rgba[..., 3].astype(np.float32) / 255.0
    inside = alpha > 0.5
    if not inside.any():
        return person

    rgb = np.ascontiguousarray(person_rgba[..., :3])
    background_rgb = np.array(background.convert("RGB").resize(person.size))

    person_lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    background_lab = cv2.cvtColor(background_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)

    difference = (background_lab.reshape(-1, 3).mean(axis=0) - person_lab[inside].mean(axis=0)) * strength
    difference[0] = np.clip(difference[0], -MAX_L_SHIFT, MAX_L_SHIFT)
    difference[1:] = np.clip(difference[1:], -MAX_AB_SHIFT, MAX_AB_SHIFT)
    person_lab += difference
    matched = cv2.cvtColor(np.clip(person_lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)

    # Light wrap: strongest right at the outline, fading inwards.
    sigma = max(2.0, 0.012 * person.width)
    background_glow = cv2.GaussianBlur(background_rgb, (0, 0), sigma * 4).astype(np.float32)
    outside_blur = cv2.GaussianBlur(1.0 - alpha, (0, 0), sigma)
    edge = (alpha * outside_blur * wrap)[..., None]
    mixed = matched * (1.0 - edge) + background_glow * edge

    result = np.dstack([np.clip(mixed, 0, 255).astype(np.uint8), person_rgba[..., 3]])
    return Image.fromarray(result, "RGBA")
