import math
import os
import random
import threading
import urllib.request
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw

YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
YUNET_PATH = "models/face_detection_yunet_2023mar.onnx"

# Styles a guest can pick. "smileys" is handled by face_smiley_replacer.
PROP_STYLES: Tuple[str, ...] = (
    "sunglasses", "party_hat", "crown", "party",
    "moustache", "clown_nose", "bunny_ears", "halo", "hearts", "mix",
)

# Props are drawn at this multiple of their final size and scaled down for smooth edges.
SUPERSAMPLE = 2

# Props are drawn upright for a face of w x h pixels on a layer that reaches one face width
# to each side, 1.6 face heights above the face and 0.3 below it, so hats and crowns have room even when
# the layer is rotated to follow a tilted head.
LAYER_LEFT = 1.0
LAYER_WIDTH = 3.0
LAYER_TOP = 1.6
LAYER_HEIGHT = 2.9

# Where the eyes sit on the upright face: the pivot the layer is rotated around and placed at.
EYE_LINE = 0.40
# Distance between the eyes as a fraction of the face width. The props are sized from this.
EYE_DISTANCE = 0.40
FACE_ASPECT = 1.4  # face height / face width


class Face(NamedTuple):
    eye_left: Tuple[float, float]   # the eye that is left in the image
    eye_right: Tuple[float, float]  # the eye that is right in the image
    # Five landmarks in the order face recognition expects: left eye, right eye, nose tip,
    # left mouth corner, right mouth corner (all "left/right" as seen in the image).
    kps: np.ndarray
    box: Tuple[float, float, float, float]  # x, y, width, height


_detector: Optional[Any] = None
# The detector keeps its input size between calls, so photo processing and the live preview must not share it at once.
_detector_lock = threading.Lock()


def _load_detector() -> Any:
    """YuNet face detector. It also returns the eye positions, which give us the head tilt."""
    global _detector
    if _detector is None:
        if not os.path.isfile(YUNET_PATH):
            os.makedirs(os.path.dirname(YUNET_PATH), exist_ok=True)
            urllib.request.urlretrieve(YUNET_URL, YUNET_PATH)
        _detector = cv2.FaceDetectorYN.create(YUNET_PATH, "", (320, 320), 0.7, 0.3, 5000)
    return _detector


# YuNet only finds faces up to a limited size relative to its input, so a close-up portrait or a large
# camera frame can come back empty at full resolution. Detection therefore runs on a shrunken copy, first
# at 640 px and, if nothing is found, at 320 px for very large faces.
DETECT_SIDES = (640, 320)


def _detect_rows(img_bgr: np.ndarray) -> Any:
    height, width = img_bgr.shape[:2]
    with _detector_lock:
        detector = _load_detector()
        detector.setInputSize((width, height))
        _, rows = detector.detect(img_bgr)
    return rows


def detect_faces(img_bgr: np.ndarray) -> List[Face]:
    height, width = img_bgr.shape[:2]
    for side in DETECT_SIDES:
        scale = min(1.0, side / max(height, width))
        small = img_bgr if scale == 1.0 else cv2.resize(img_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        rows = _detect_rows(small)
        if rows is None or len(rows) == 0:
            continue
        faces: List[Face] = []
        for row in rows:
            values = row[:14] / scale  # positions back in the original image's pixels
            # YuNet names the eyes from the person's point of view, so sort them by image position.
            eyes = sorted([(float(values[4]), float(values[5])), (float(values[6]), float(values[7]))])
            mouth = sorted([(float(values[10]), float(values[11])), (float(values[12]), float(values[13]))])
            kps = np.array([eyes[0], eyes[1], (float(values[8]), float(values[9])), mouth[0], mouth[1]], dtype=np.float32)
            faces.append(
                Face(
                    eye_left=eyes[0],
                    eye_right=eyes[1],
                    kps=kps,
                    box=(float(values[0]), float(values[1]), float(values[2]), float(values[3])),
                )
            )
        return faces
    return []


class _Canvas:
    """Draws in face-relative pixel units; (0, 0) is the top-left corner of the face box."""

    def __init__(self, w: int, h: int) -> None:
        self.w = w
        self.h = h
        self.size = (int(w * LAYER_WIDTH * SUPERSAMPLE), int(h * LAYER_HEIGHT * SUPERSAMPLE))
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
            (int(self.w * LAYER_WIDTH), int(self.h * LAYER_HEIGHT)), Image.Resampling.LANCZOS
        )


def _sunglasses(c: _Canvas) -> None:
    c.set_scale(1.0)
    lens_w, lens_h, eye_y = 0.34, 0.24, EYE_LINE
    dark, rim = (18, 18, 24, 240), (0, 0, 0, 255)
    arm_width = max(2, int(c.length(c.h * 0.03)))

    # arms and bridge first so the lenses sit on top
    for x_from, x_to in ((0.13, -0.04), (0.87, 1.04)):
        c.draw.line([c.p(x_from, eye_y - 0.03), c.p(x_to, eye_y - 0.03)], fill=rim, width=arm_width)
    c.draw.rectangle([c.p(0.46, eye_y - 0.06), c.p(0.54, eye_y - 0.02)], fill=rim)

    for center in (0.30, 0.70):
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


# Where nose tip and upper lip sit on the upright face (eyes are at EYE_LINE). Measured on
# YuNet landmarks: the nose is ~0.7 and the mouth ~1.25 eye distances below the eye line.
NOSE_LINE = 0.60
UPPER_LIP_LINE = 0.69


def _ellipse_points(
    c: _Canvas, fx: float, fy: float, rx: float, ry: float, angle_deg: float = 0.0, steps: int = 48
) -> List[Tuple[float, float]]:
    """Polygon of an ellipse centered at the face fraction (fx, fy); rx is a fraction of the width, ry of the height."""
    cx, cy = c.p(fx, fy)
    a = math.radians(angle_deg)
    points = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        x = rx * c.w * c.sx * SUPERSAMPLE * math.cos(t)
        y = ry * c.h * c.sy * SUPERSAMPLE * math.sin(t)
        points.append((cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)))
    return points


def _moustache(c: _Canvas) -> None:
    c.set_scale(1.0)
    brown, edge = (62, 38, 22, 255), (30, 16, 8, 255)
    y = UPPER_LIP_LINE
    # two lobes whose outer ends curl up, a bump in the middle and curled tips
    for side, angle in ((-1, 14), (1, -14)):
        lobe = _ellipse_points(c, 0.5 + side * 0.15, y, 0.16, 0.05, angle)
        c.draw.polygon(lobe, fill=brown, outline=edge)
        tip = _ellipse_points(c, 0.5 + side * 0.285, y - 0.035, 0.035, 0.035)
        c.draw.polygon(tip, fill=brown, outline=edge)
    c.draw.polygon(_ellipse_points(c, 0.5, y - 0.012, 0.08, 0.045), fill=brown, outline=edge)


def _clown_nose(c: _Canvas) -> None:
    c.set_scale(1.0)
    c.draw.polygon(_ellipse_points(c, 0.5, NOSE_LINE, 0.115, 0.082), fill=(225, 30, 45, 255), outline=(130, 10, 20, 255))
    c.draw.polygon(_ellipse_points(c, 0.47, NOSE_LINE - 0.02, 0.03, 0.02, -25), fill=(255, 255, 255, 120))


def _bunny_ears(c: _Canvas) -> None:
    c.set_scale(1.3, 1.2, 0.0)
    for side, angle in ((-1, -12), (1, 12)):
        outer = _ellipse_points(c, 0.5 + side * 0.20, -0.40, 0.11, 0.40, angle)
        c.draw.polygon(outer, fill=(246, 246, 246, 255), outline=(150, 150, 160, 255))
        inner = _ellipse_points(c, 0.5 + side * 0.20, -0.38, 0.062, 0.31, angle)
        c.draw.polygon(inner, fill=(255, 175, 195, 255))


def _halo(c: _Canvas) -> None:
    c.set_scale(1.2, 1.2, 0.0)
    cy, rx, ry = -0.30, 0.40, 0.085
    box = [c.p(0.5 - rx, cy - ry), c.p(0.5 + rx, cy + ry)]
    c.draw.ellipse(box, outline=(255, 235, 140, 90), width=max(2, int(c.length(c.h * 0.11))))
    c.draw.ellipse(box, outline=(255, 205, 40, 255), width=max(2, int(c.length(c.h * 0.05))))


def _heart_points(cx: float, cy: float, size: float) -> List[Tuple[float, float]]:
    points = []
    for i in range(64):
        t = 2 * math.pi * i / 64
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        points.append((cx + x / 17 * size, cy - y / 17 * size))
    return points


def _hearts(c: _Canvas) -> None:
    c.set_scale(1.0)
    size = c.w * 0.20 * SUPERSAMPLE
    for fx in (0.30, 0.70):
        cx, cy = c.p(fx, EYE_LINE)
        c.draw.polygon(_heart_points(cx, cy, size), fill=(235, 40, 85, 240), outline=(140, 10, 40, 255))
        c.draw.polygon(_ellipse_points(c, fx - 0.045, EYE_LINE - 0.045, 0.03, 0.02, -35), fill=(255, 255, 255, 140))


_PROP_DRAWERS: Dict[str, Callable[[_Canvas], None]] = {
    "sunglasses": _sunglasses,
    "party_hat": _party_hat,
    "crown": _crown,
    "moustache": _moustache,
    "clown_nose": _clown_nose,
    "bunny_ears": _bunny_ears,
    "halo": _halo,
    "hearts": _hearts,
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


def apply_face_props(img_orig: Image.Image, style: str) -> Image.Image:
    """
    Put sunglasses, party hats or crowns on every detected face. Props are drawn procedurally,
    so no extra image assets are needed, and follow the tilt of the head (from the eye line).
    Returns the original image if no face is found.
    """
    if style not in PROP_STYLES:
        raise ValueError(f"Unknown style: {style}")

    img_cv = cv2.cvtColor(np.array(img_orig.convert("RGB")), cv2.COLOR_RGB2BGR)
    faces = detect_faces(img_cv)
    if not faces:
        return img_orig

    out = img_orig.convert("RGB")
    for face in faces:
        placed = _placed_props(face, style)
        if placed is not None:
            layer, position = placed
            out.paste(layer, position, layer)
    return out


def _placed_props(face: Face, style: str) -> Optional[Tuple[Image.Image, Tuple[int, int]]]:
    """The props for one face, rotated with the head, and the top-left position to paste them at."""
    (lx, ly), (rx, ry) = face.eye_left, face.eye_right
    eye_distance = math.hypot(rx - lx, ry - ly)
    if eye_distance < 1:
        return None

    w = max(1, int(round(eye_distance / EYE_DISTANCE)))
    h = max(1, int(round(w * FACE_ASPECT)))
    layer = render_props(w, h, _kinds_for_style(style))

    # PIL rotates counter-clockwise; a right eye lower than the left means a clockwise tilt.
    tilt = math.degrees(math.atan2(ry - ly, rx - lx))
    pivot = ((LAYER_LEFT + 0.5) * w, (LAYER_TOP + EYE_LINE) * h)
    layer = layer.rotate(-tilt, resample=Image.Resampling.BICUBIC, center=pivot)

    mid_x, mid_y = (lx + rx) / 2, (ly + ry) / 2
    return layer, (int(round(mid_x - pivot[0])), int(round(mid_y - pivot[1])))


# "mix" picks something at random for every photo, so there is nothing fixed to preview.
PREVIEW_STYLES: Tuple[str, ...] = tuple(style for style in PROP_STYLES if style != "mix")


def render_overlay(img: Image.Image, style: str) -> Image.Image:
    """
    Only the props, on a transparent image of the same size, for the live preview: the browser lays it over
    the camera picture. Returns a fully transparent image if no face is found.
    """
    if style not in PREVIEW_STYLES:
        raise ValueError(f"No live preview for style: {style}")

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    faces = detect_faces(cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR))
    for face in faces:
        placed = _placed_props(face, style)
        if placed is None:
            continue
        layer, position = placed
        # Pasting without a mask copies the layer's alpha too (and clips at the edges); compositing then
        # blends it over what is already there without darkening soft edges.
        piece = Image.new("RGBA", img.size, (0, 0, 0, 0))
        piece.paste(layer, position)
        overlay = Image.alpha_composite(overlay, piece)
    return overlay
