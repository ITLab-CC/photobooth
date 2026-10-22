from typing import Optional, Sequence, Tuple, Union

import cv2
import numpy as np
from PIL import Image

Rect = Tuple[int, int, int, int]  # x0, y0, x1, y1

# Smallest window (in pixels) that still counts as a real photo area.
MIN_WINDOW = 8


def normalize_crop(crop: Union[int, float, Sequence[int]]) -> Tuple[int, int, int, int]:
    """Crop as (top, right, left, bottom), the order IMGReplacer.add_frame uses."""
    if isinstance(crop, (int, float)):
        value = int(crop)
        return (value, value, value, value)
    top, right, left, bottom = (int(v) for v in crop)
    return (top, right, left, bottom)


def pasted_rect(
    bg_size: Tuple[int, int], scale: float, offset: Sequence[int], crop: Union[int, float, Sequence[int]]
) -> Rect:
    """Where add_frame puts the scaled and cropped background on the frame's canvas."""
    top, right, left, bottom = normalize_crop(crop)
    width = int(bg_size[0] * scale) - left - right
    height = int(bg_size[1] * scale) - top - bottom
    return (int(offset[0]), int(offset[1]), int(offset[0]) + width, int(offset[1]) + height)


def transparent_bbox(frame: Image.Image, threshold: int = 128) -> Optional[Rect]:
    """
    Bounding box of the frame's photo opening: its largest transparent area. Smaller transparent specks
    (for example holes in lettering) are ignored so they do not stretch the window.
    """
    alpha = np.asarray(frame.convert("RGBA"))[..., 3]
    hole = (alpha < threshold).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(hole, connectivity=4)
    if count <= 1:
        return None
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y = int(stats[largest, cv2.CC_STAT_LEFT]), int(stats[largest, cv2.CC_STAT_TOP])
    return (x, y, x + int(stats[largest, cv2.CC_STAT_WIDTH]), y + int(stats[largest, cv2.CC_STAT_HEIGHT]))


def visible_window(
    frame: Image.Image,
    bg_size: Tuple[int, int],
    scale: float,
    offset: Sequence[int],
    crop: Union[int, float, Sequence[int]],
) -> Optional[Rect]:
    """The part of the frame canvas where the guests' photo is seen: the frame's opening, where the pasted background covers it."""
    hole = transparent_bbox(frame)
    if hole is None:
        return None
    pasted = pasted_rect(bg_size, scale, offset, crop)
    window = (max(hole[0], pasted[0]), max(hole[1], pasted[1]), min(hole[2], pasted[2]), min(hole[3], pasted[3]))
    if window[2] - window[0] < MIN_WINDOW or window[3] - window[1] < MIN_WINDOW:
        return None
    return window


def window_in_background(
    window: Rect,
    bg_size: Tuple[int, int],
    scale: float,
    offset: Sequence[int],
    crop: Union[int, float, Sequence[int]],
) -> Rect:
    """The same window in the background image's own pixels, undoing add_frame's crop, scale and offset."""
    top, _, left, _ = normalize_crop(crop)
    x0 = (window[0] - offset[0] + left) / scale
    y0 = (window[1] - offset[1] + top) / scale
    x1 = (window[2] - offset[0] + left) / scale
    y1 = (window[3] - offset[1] + top) / scale
    return (
        max(0, int(round(x0))),
        max(0, int(round(y0))),
        min(bg_size[0], int(round(x1))),
        min(bg_size[1], int(round(y1))),
    )
