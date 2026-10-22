import sys
from PIL import Image
from PIL import Image
from PIL.Image import Image as PilImage


import cv2
import numpy as np
import torch
from relight import match_light
from ben2 import BEN_Base  # type: ignore
from typing import Optional, Tuple, Union, cast


def get_bbox_with_alpha_threshold(img: Image.Image, alpha_threshold: int = 128) -> Optional[Tuple[int, int, int, int]]:
    """
    Returns a bounding box for pixels with an alpha value >= alpha_threshold
    (ignores semi-transparent edges).

    Parameters:
        img (Image.Image): The input image.
        alpha_threshold (int): The threshold for the alpha channel (default: 128).

    Returns:
        Optional[Tuple[int, int, int, int]]: The bounding box as (left, top, right, bottom),
                                             or None if no pixel meets the threshold.
    """
    alpha = np.asarray(img.convert("RGBA"))[..., 3]
    solid = alpha >= alpha_threshold
    rows = np.flatnonzero(solid.any(axis=1))
    columns = np.flatnonzero(solid.any(axis=0))
    if rows.size == 0:
        return None  # No pixels found meeting the alpha threshold

    # The bounding box is defined as (left, top, right, bottom),
    # where right and bottom are one pixel past the last included pixel.
    return (int(columns[0]), int(rows[0]), int(columns[-1]) + 1, int(rows[-1]) + 1)


def clean_cutout_edges(cutout: Image.Image) -> Image.Image:
    """
    Remove the light fringe around a cut-out person. The matte's edge pixels still carry the colour of the old
    background, which shows as a bright outline on the new one. The matte is thinned by about a pixel and
    smoothed, and the colours near the edge are taken from the inside of the person instead.
    """
    rgba = np.asarray(cutout.convert("RGBA"))
    rgb = rgba[..., :3].astype(np.float32)
    alpha = rgba[..., 3]

    step = max(1, round(max(cutout.size) / 1100))  # one pixel at Full HD, more for larger pictures
    eroded = cv2.erode(alpha, np.ones((2 * step + 1, 2 * step + 1), np.uint8))
    softened = cv2.GaussianBlur(eroded, (0, 0), step * 0.8)

    # Colours are only trusted well inside the person (about three pixels from the edge at Full HD).
    deep = 2 * step + 1
    inside = cv2.erode((alpha >= 250).astype(np.uint8), np.ones((2 * deep + 1, 2 * deep + 1), np.uint8)).astype(np.float32)
    sigma = 3.0 * step + 1.0
    colour_sum = cv2.GaussianBlur(rgb * inside[..., None], (0, 0), sigma)
    weight = cv2.GaussianBlur(inside, (0, 0), sigma)[..., None]
    from_inside = colour_sum / np.maximum(weight, 1e-4)
    cleaned = np.where((inside[..., None] > 0.5) | (weight < 0.02), rgb, from_inside)

    return Image.fromarray(np.dstack([np.clip(cleaned, 0, 255).astype(np.uint8), softened]), "RGBA")


# With anchor="bottom": share of the height kept free above the subject, and the gap left under
# a subject whose feet are in the picture.
BOTTOM_ANCHOR_TOP_MARGIN = 0.04
BOTTOM_ANCHOR_FLOOR_MARGIN = 0.03


class IMGReplacer:
    def __init__(self) -> None:
        """
        Initialize the IMGReplacer.
        Loads the BEN2 model onto the available device (GPU if available).
        """
        self.device: torch.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model: Optional[BEN_Base] = None
        self.model_name: str = "PramaLLC/BEN2"
        self._load_model()

    def _load_model(self) -> None:
        """
        Load the BEN2 model and set it to evaluation mode.
        """
        self.model = BEN_Base.from_pretrained(self.model_name)
        self.model.to(self.device).eval()

    def _unload_model(self) -> None:
        """
        Unload the model from memory (optional usage).
        """
        self.model = None

    def remove_background(self, img: Image.Image, refine_foreground: bool = False) -> Image.Image:
        """
        Remove the background from a given PIL Image and return a foreground image (RGBA) with transparency.

        :param img: Input PIL image from which to remove the background.
        :param refine_foreground: Whether to use refined matting for higher-quality results (slower inference).
        :return: Foreground PIL Image with an alpha channel.
        """
        if self.model is None:
            raise RuntimeError("Model is not loaded. Please call _load_model() first.")

        # Convert to RGB to ensure consistent input
        img_rgb: Image.Image = img.convert("RGBA")
        
        # Perform inference (background removal)
        foreground: Image.Image = self.model.inference(img_rgb, refine_foreground=refine_foreground)
        return foreground

    def replace_background(
        self,
        foreground: Image.Image,
        new_background: Image.Image,
        refine_foreground: bool = False,
        margin_ratio: float = 0.9,
        apply_alpha_threshold: bool = True,
        light_match: bool = False,
        anchor: str = "center"
    ) -> Image.Image:
        """
        Replaces the background of the input image with a new background.
        Scales the subject so that it fills at most (margin_ratio * 100%) of the new background 
        without distortion (contain approach).

        :param foreground: Input PIL image from which to replace the background.
        :param new_background: New background image.
        :param refine_foreground: If True, uses BEN2 "Refined Matting" (slower but more accurate).
        :param margin_ratio: For example, 0.9 means 90% of the maximum possible size (adds an automatic margin).
        :param apply_alpha_threshold: If True, uses get_bbox_with_alpha_threshold to ignore semi-transparent edge pixels.
        :param light_match: If True, adapt the subject's brightness/color to the new background (see relight.py).
        :param anchor: "center" puts the subject in the middle; "bottom" lets it stand on the lower edge, and a
                       person who is cut off at the bottom of the camera picture continues beyond the lower edge
                       instead of ending in mid-air.
        :return: Composited image (RGBA).
        """
        # 1) Isolate the foreground
        fg_rgba = clean_cutout_edges(foreground)
        bg_rgba = new_background.convert("RGBA")
        frame_w, frame_h = bg_rgba.size

        # 2) Determine the bounding box (optionally with alpha threshold)
        if apply_alpha_threshold:
            bbox = get_bbox_with_alpha_threshold(fg_rgba, alpha_threshold=128)
        else:
            bbox = fg_rgba.getbbox()

        if not bbox:
            # If nothing is detected, simply return the background
            return bg_rgba

        left, top, right, bottom = bbox
        subj_width = right - left
        subj_height = bottom - top

        # 3) Contain approach: scale the subject to fit the frame, leaving a margin
        if anchor == "bottom":
            # width keeps its margin; the height may use nearly everything, as the subject stands on the lower edge
            final_scale = min(frame_w * margin_ratio / subj_width, frame_h * (1 - BOTTOM_ANCHOR_TOP_MARGIN) / subj_height)
        else:
            final_scale = min(frame_w / subj_width, frame_h / subj_height) * margin_ratio

        # 4) Scale the entire image
        new_fg_width = int(fg_rgba.width * final_scale)
        new_fg_height = int(fg_rgba.height * final_scale)

        try:
            resample_method = Image.Resampling.LANCZOS
        except AttributeError:
            # Fallback
            resample_method = Image.ANTIALIAS # type: ignore

        fg_rgba_scaled = fg_rgba.resize((new_fg_width, new_fg_height), resample_method)

        # 5) Place it: centered horizontally, and either centered vertically or standing on the lower edge
        offset_x = round(frame_w / 2 - (left + right) / 2 * final_scale)
        if anchor == "bottom":
            cut_off_below = bottom >= fg_rgba.height - max(2, fg_rgba.height // 250)
            floor_gap = 0 if cut_off_below else round(frame_h * BOTTOM_ANCHOR_FLOOR_MARGIN)
            # a subject cut off by the camera picture bleeds one pixel past the edge so no seam shows
            offset_y = round(frame_h - floor_gap - bottom * final_scale) + (1 if cut_off_below else 0)
        else:
            offset_y = round(frame_h / 2 - (top + bottom) / 2 * final_scale)

        # 8) Create a new RGBA image with the same size as the background
        new_fg = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        new_fg.paste(fg_rgba_scaled, (offset_x, offset_y), fg_rgba_scaled)

        if light_match:
            new_fg = match_light(new_fg, bg_rgba)

        # 9) Insert the subject into the background
        bg_rgba.paste(new_fg, (0, 0), new_fg)
        return bg_rgba

    def add_frame(
        self,
        background_image: Image.Image,
        frame_image: Image.Image,
        scale: float = 1.0,
        offset: Tuple[int, int] = (0, 0),
        crop: Union[int, Tuple[int, int, int, int]] = 0
    ) -> Image.Image:
        """
        Overlays a PNG frame (with a transparent background) on a scaled, optionally cropped background image,
        which is then placed at specified coordinates on a canvas matching the frame's dimensions.
        
        Parameters:
            background_image (Image.Image): The background image.
            frame_image (Image.Image): The PNG frame image.
            scale (float): Scaling factor for the background image 
                           (e.g., 0.5 for 50% size, 2.0 for 200%). Defaults to 1.0.
            offset (Tuple[int, int]): (x, y) coordinates specifying where to place the processed background
                                      on the final canvas (top-left corner). Defaults to (0, 0).
            crop (Union[int, Tuple[int, int, int, int]]): If an int, crops that many pixels from all four sides of the scaled background.
                                                          If a tuple, it should be (crop_top, crop_right, crop_left, crop_bottom).
                                                          Defaults to 0 (no cropping).
        
        Returns:
            Image.Image: The resulting image with the frame overlay.
        """
        frame_width, frame_height = frame_image.size
        background = background_image.convert("RGBA")
        
        bg_width, bg_height = background.size
        try:
            resample_method = Image.Resampling.LANCZOS
        except AttributeError:
            # Fallback
            resample_method = Image.ANTIALIAS # type: ignore

        # 1) Scale the background
        new_bg_width = int(bg_width * scale)
        new_bg_height = int(bg_height * scale)
        scaled_background = background.resize((new_bg_width, new_bg_height), resample_method)

        # 2) Apply cropping
        if crop:
            if isinstance(crop, int):
                crop = (crop, crop, crop, crop)
            if len(crop) != 4:
                raise ValueError("crop must be int or a tuple of four ints (top, right, left, bottom)")
            
            crop_top, crop_right, crop_left, crop_bottom = crop
            new_left = crop_left
            new_top = crop_top
            new_right = scaled_background.width - crop_right
            new_bottom = scaled_background.height - crop_bottom

            if new_left < 0 or new_top < 0 or new_right > scaled_background.width or new_bottom > scaled_background.height:
                raise ValueError("Crop values are out of bounds.")
            
            scaled_background = scaled_background.crop((new_left, new_top, new_right, new_bottom))

        # 3) Create a blank canvas with the size of the frame
        canvas = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))

        # 4) Paste the background onto the canvas
        canvas.paste(scaled_background, offset, scaled_background)

        # 5) Overlay the frame
        combined = Image.alpha_composite(canvas, frame_image)
        return combined

    def add_qr_code(
            self,
            img: Image.Image,
            qr_code: PilImage, # type: ignore
            position: Tuple[int, int],
            scale: float = 1.0
        ) -> Image.Image:
        """
        Overlays a QR code onto an image at the specified position.

        Args:
            img (Image.Image): The background image.
            qr_code (Image.Image): The QR code image to overlay.
            position (Tuple[int, int]): The (x, y) coordinates where the QR code will be placed.
            scale (float, optional): Scale factor to resize the QR code. Defaults to 1.0.

        Returns:
            Image.Image: The resulting image with the QR code overlay.
        """
        # Ensure QR code is in RGBA mode to preserve transparency.
        if qr_code.mode != "RGBA":
            qr_code = qr_code.convert("RGBA")

        # Scale the QR code if a scale factor other than 1.0 is provided.
        if scale != 1.0:
            new_size = (round(qr_code.width * scale), round(qr_code.height * scale))
            try:
                resample_method = Image.Resampling.LANCZOS
            except AttributeError:
                # Fallback
                resample_method = Image.ANTIALIAS # type: ignore

            qr_code = qr_code.resize(new_size, resample_method)

        # Create a mask for transparency if available.
        mask = qr_code.split()[3] if qr_code.mode == "RGBA" else None

        # Paste the QR code onto the image using the mask.
        img.paste(qr_code, position, mask)
        return img


        
def resize_with_crop_or_pad(
    img: Image.Image,
    target_size: Tuple[int, int],
    background_color: Optional[Tuple[int, int, int, int]] = None,
    resample: Optional[int] = None
) -> Image.Image:
    """
    Resize an image to exactly (target_w, target_h) without distortion:
      - If the scaled image is larger than target in either dimension, center-crop the overflow.
      - If smaller, center it on a canvas and pad (transparent by default for RGBA, white for RGB).

    Parameters:
        img: PIL Image.
        target_size: (target_w, target_h).
        background_color: RGBA/RGB fill for padding. If None:
            - uses transparent (0,0,0,0) for RGBA output,
            - or white (255,255,255) for RGB/others.
        resample: PIL resampling filter. Defaults to LANCZOS if available.

    Returns:
        PIL Image of size target_size, same mode as input if possible (RGBA preferred if input has alpha).
    """
    target_w, target_h = target_size

    if resample is None:
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.ANTIALIAS  # type: ignore

    # Decide output mode and background
    if img.mode == "RGBA":
        out_mode = "RGBA"
        default_bg = (0, 0, 0, 0)
    else:
        out_mode = "RGB"
        default_bg = (255, 255, 255)

    if background_color is None:
        background_color = default_bg

    # Convert to a working mode that supports alpha if present
    work = img.convert(out_mode)

    # Compute scale to cover the target (no letterbox inside content)
    scale = max(target_w / work.width, target_h / work.height) if work.width and work.height else 1.0
    scaled_w = max(1, int(round(work.width * scale)))
    scaled_h = max(1, int(round(work.height * scale)))
    scaled = work.resize((scaled_w, scaled_h), resample)

    # Create background canvas
    canvas = Image.new(out_mode, (target_w, target_h), background_color)

    # Compute paste position to center
    offset_x = (target_w - scaled_w) // 2
    offset_y = (target_h - scaled_h) // 2

    # If scaled is larger than target in any dimension, paste will be negative.
    # Paste with mask if RGBA to preserve transparency.
    mask = scaled.split()[3] if out_mode == "RGBA" and scaled.mode == "RGBA" else None
    canvas.paste(scaled, (offset_x, offset_y), mask)

    return canvas



def main() -> None:
    # Example paths (adjust as needed!)
    input_image_path = "./image.png"            # Original image (to be isolated)
    new_background_path = "./new_background.png"
    frame_path = "./frame.png"
    output_final_path = "./final_image.png"
    output_no_frame_path = "./final_image_no_frame.png"

    # 1) Load images
    input_img = Image.open(input_image_path)
    background_img = Image.open(new_background_path)
    frame_img = Image.open(frame_path)

    # 2) Instantiate the replacer
    replacer = IMGReplacer()

    no_background = replacer.remove_background(input_img)

    # 4) Remove the background and dynamically scale
    #    margin_ratio=0.9 means the subject fills 90% of the maximum possible area (contain approach)
    #    You can also try values like 1.0, 1.1, or 0.8.
    new_background = replacer.replace_background(
        foreground=no_background,
        new_background=background_img,
        refine_foreground=False,
        margin_ratio=0.9,
        apply_alpha_threshold=True
    )
    new_background.save(output_no_frame_path)

    # 4) Add a QR code
    import qrcode
    img_url = f"https://google.com"
    qr_img = qrcode.make(img_url) # type: ignore

    frame_with_qr = replacer.add_qr_code(
        img=frame_img,
        qr_code=qr_img, # type: ignore
        position=(1300, 2150),
        scale=0.6
    )

    # 5) Optional: Overlay the frame
    #    If you need additional scaling or offset, adjust the scale and offset parameters.
    final_img = replacer.add_frame(
        background_image=new_background,
        frame_image=frame_with_qr,
        scale=0.75,
        offset=(-200, 0),
        crop=(0, 0, 0, 0)
    )
    final_img.save(output_final_path)

    print(f"Result without frame: {output_no_frame_path}")
    print(f"Result with frame:  {output_final_path}")


if __name__ == "__main__":
    main()
