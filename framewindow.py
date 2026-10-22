from typing import Optional, Sequence, Tuple, Union

import cv2
import numpy as np
from PIL import Image

Rect = Tuple[int, int, int, int]  # x0, y0, x1, y1


def normalize_crop(crop: Union[int, float, Sequence[int]]) -> Tuple[int, int, int, int]:
    """Crop as (top, right, left, bottom)."""
    if isinstance(crop, (int, float)):
        value = int(crop)
        return (value, value, value, value)
    top, right, left, bottom = (int(v) for v in crop)
    return (top, right, left, bottom)


def transparent_bbox(frame: Image.Image, threshold: int = 128) -> Optional[Rect]:
    """
    Bounding box of the frame's photo opening: its largest transparent area. Smaller transparent specks
    (for example holes in lettering) are ignored so they do not stretch the opening.
    """
    alpha = np.asarray(frame.convert("RGBA"))[..., 3]
    hole = (alpha < threshold).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(hole, connectivity=4)
    if count <= 1:
        return None
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y = int(stats[largest, cv2.CC_STAT_LEFT]), int(stats[largest, cv2.CC_STAT_TOP])
    return (x, y, x + int(stats[largest, cv2.CC_STAT_WIDTH]), y + int(stats[largest, cv2.CC_STAT_HEIGHT]))


def frame_opening(frame: Image.Image) -> Rect:
    """The area of the frame that shows the photo. A frame without any opening shows the photo over its whole canvas."""
    return transparent_bbox(frame) or (0, 0, frame.width, frame.height)


def cover_fit(img: Image.Image, size: Tuple[int, int], focus: Tuple[float, float] = (0.5, 0.5)) -> Image.Image:
    """
    Scale the image until it covers `size` and cut off what overhangs. `focus` says which part is kept when
    one side overhangs: 0 keeps the left/top, 1 the right/bottom, 0.5 the middle (the same meaning as
    CSS background-position).
    """
    width, height = size
    scale = max(width / img.width, height / img.height)
    scaled = img.resize(
        (max(width, round(img.width * scale)), max(height, round(img.height * scale))), Image.Resampling.LANCZOS
    )
    left = round((scaled.width - width) * min(1.0, max(0.0, focus[0])))
    top = round((scaled.height - height) * min(1.0, max(0.0, focus[1])))
    return scaled.crop((left, top, left + width, top + height))
