import random
from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw

from face_smiley_replacer import detect_faces_dnn_on_original, ensure_dnn_model

# Styles a guest can pick. "smileys" is handled by face_smiley_replacer.
PROP_STYLES: Tuple[str, ...] = ("sunglasses", "party_hat", "crown", "party", "mix")

# Props are drawn at this multiple of their final size and scaled down for smooth edges.
SUPERSAMPLE = 2

# A face box is (x, y, w, h). Props are drawn on a layer that starts half a face width
# left of the box and one face height above it, so hats and crowns have room.
LAYER_LEFT = 0.5
LAYER_TOP = 1.6
LAYER_HEIGHT = 2.2

_net: Optional[Any] = None


def _load_net(prototxt_path: str, model_path: str) -> Any:
    global _net
    if _net is None:
        ensure_dnn_model(prototxt_path, model_path)
        _net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)
    return _net


class _Canvas:
    """Draws in face-relative pixel units; (0, 0) is the top-left corner of the face box."""

    def __init__(self, w: int, h: int) -> None:
        self.w = w
        self.h = h
        self.size = (int(w * 2 * SUPERSAMPLE), int(h * LAYER_HEIGHT * SUPERSAMPLE))
        self.image = Image.new("RGBA", self.size, (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)
        self.set_scale()

    def set_scale(self, sx: float = 1.0, sy: float = 1.0, base: float = 0.0) -> None:
        """Enlarge what is drawn next: sx widens around the face center, sy grows away from the line at base."""
        self.sx = sx
        self.sy = sy
        self.base = base

    def p(self, fx: float, fy: float) -> Tuple[float, float]:
        """Face-relative fractions (of width and height) to layer pixels."""
        fx = 0.5 + (fx - 0.5) * self.sx
        fy = self.base + (fy - self.base) * self.sy
        return ((LAYER_LEFT + fx) * self.w * SUPERSAMPLE, (LAYER_TOP + fy) * self.h * SUPERSAMPLE)

    def length(self, value: float) -> float:
        return value * SUPERSAMPLE

    def finish(self) -> Image.Image:
        return self.image.resize(
            (int(self.w * 2), int(self.h * LAYER_HEIGHT)), Image.Resampling.LANCZOS
        )


def _sunglasses(c: _Canvas) -> None:
    c.set_scale(1.1)
    lens_w, lens_h, eye_y = 0.38, 0.24, 0.40
    dark, rim = (18, 18, 24, 240), (0, 0, 0, 255)
    arm_width = max(2, int(c.length(c.h * 0.03)))

    # arms and bridge first so the lenses sit on top
    for x_from, x_to in ((0.09, -0.04), (0.91, 1.04)):
        c.draw.line([c.p(x_from, eye_y - 0.03), c.p(x_to, eye_y - 0.03)], fill=rim, width=arm_width)
    c.draw.rectangle([c.p(0.44, eye_y - 0.06), c.p(0.56, eye_y - 0.02)], fill=rim)

    for center in (0.28, 0.72):
        box = [c.p(center - lens_w / 2, eye_y - lens_h / 2), c.p(center + lens_w / 2, eye_y + lens_h / 2)]
        c.draw.rounded_rectangle(box, radius=c.length(c.h * 0.08), fill=dark, outline=rim, width=max(2, arm_width))
        shine = [
            c.p(center - lens_w * 0.38, eye_y - lens_h * 0.36),
            c.p(center - lens_w * 0.10, eye_y - lens_h * 0.36),
            c.p(center - lens_w * 0.26, eye_y + lens_h * 0.10),
            c.p(center - lens_w * 0.38, eye_y + lens_h * 0.10),
        ]
        c.draw.polygon(shine, fill=(255, 255, 255, 70))


def _party_hat(c: _Canvas) -> None:
    c.set_scale(1.5, 1.45, 0.02)
    base_y, half_base, height = 0.06, 0.36, 0.95
    tip = c.p(0.5 + 0.04, base_y - height)
    left, right = c.p(0.5 - half_base, base_y), c.p(0.5 + half_base, base_y)

    mask = Image.new("L", c.size, 0)
    ImageDraw.Draw(mask).polygon([left, right, tip], fill=255)

    stripes = Image.new("RGBA", c.size, (255, 70, 140, 255))
    stripe_draw = ImageDraw.Draw(stripes)
    for i, color in enumerate([(255, 215, 0, 255), (60, 190, 255, 255)] * 4):
        offset = (i - 3) * 0.16
        stripe_draw.line(
            [c.p(0.5 + offset - 0.5, base_y + 0.1), c.p(0.5 + offset + 0.5, base_y - height - 0.1)],
            fill=color,
            width=int(c.length(c.h * 0.07)),
        )
    c.image.paste(stripes, (0, 0), mask)

    c.draw.line([left, right], fill=(255, 255, 255, 255), width=max(2, int(c.length(c.h * 0.03))))
    radius = c.w * 0.09 * c.sx * SUPERSAMPLE
    tx, ty = tip
    c.draw.ellipse([tx - radius, ty - radius, tx + radius, ty + radius], fill=(255, 230, 80, 255), outline=(255, 255, 255, 255))


def _crown(c: _Canvas) -> None:
    c.set_scale(1.45, 1.4, 0.02)
    gold, edge = (255, 200, 40, 255), (170, 110, 0, 255)
    peaks = [(0.12, -0.42), (0.31, -0.52), (0.50, -0.60), (0.69, -0.52), (0.88, -0.42)]
    valleys = [(0.215, -0.25), (0.405, -0.25), (0.595, -0.25), (0.785, -0.25)]

    outline = [c.p(0.12, 0.06)]
    for i, peak in enumerate(peaks):
        outline.append(c.p(*peak))
        if i < len(valleys):
            outline.append(c.p(*valleys[i]))
    outline.append(c.p(0.88, 0.06))
    c.draw.polygon(outline, fill=gold, outline=edge)
    c.draw.line(outline + [outline[0]], fill=edge, width=max(2, int(c.length(c.h * 0.02))))
    c.draw.rectangle([c.p(0.12, -0.08), c.p(0.88, 0.06)], fill=(235, 170, 20, 255), outline=edge)

    for fx, color in ((0.25, (220, 40, 60, 255)), (0.5, (50, 110, 230, 255)), (0.75, (40, 190, 90, 255))):
        cx, cy = c.p(fx, -0.01)
        radius = c.w * 0.045 * c.sx * SUPERSAMPLE
        c.draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color, outline=edge)
    for peak in peaks:
        cx, cy = c.p(*peak)
        radius = c.w * 0.03 * c.sx * SUPERSAMPLE
        c.draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(255, 245, 200, 255), outline=edge)


_PROP_DRAWERS: Dict[str, Callable[[_Canvas], None]] = {
    "sunglasses": _sunglasses,
    "party_hat": _party_hat,
    "crown": _crown,
}


def render_props(w: int, h: int, kinds: List[str]) -> Image.Image:
    """Render the given props for a face box of w x h pixels onto one transparent layer."""
    canvas = _Canvas(w, h)
    for kind in kinds:
        _PROP_DRAWERS[kind](canvas)
    return canvas.finish()


def _kinds_for_style(style: str) -> List[str]:
    if style == "party":
        return ["party_hat", "sunglasses"]
    if style == "mix":
        return [random.choice(list(_PROP_DRAWERS))]
    return [style]


def apply_face_props(
    img_orig: Image.Image,
    style: str,
    prototxt_path: str = "models/deploy.prototxt",
    model_path: str = "models/res10_300x300_ssd_iter_140000.caffemodel",
    conf_threshold: float = 0.85,
) -> Image.Image:
    """
    Put sunglasses, party hats or crowns on every detected face. Props are drawn procedurally,
    so no extra image assets are needed. Returns the original image if no face is found.
    """
    if style not in PROP_STYLES:
        raise ValueError(f"Unknown style: {style}")

    img_cv = cv2.cvtColor(np.array(img_orig.convert("RGB")), cv2.COLOR_RGB2BGR)
    boxes, _ = detect_faces_dnn_on_original(img_cv, _load_net(prototxt_path, model_path), conf_threshold)
    if not boxes:
        return img_orig

    out = img_orig.convert("RGB")
    for x, y, w, h in boxes:
        layer = render_props(w, h, _kinds_for_style(style))
        out.paste(layer, (int(x - LAYER_LEFT * w), int(y - LAYER_TOP * h)), layer)
    return out
