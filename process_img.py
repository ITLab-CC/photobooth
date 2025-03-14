import sys
from PIL import Image
from PIL import Image
from PIL.Image import Image as PilImage


import torch
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
    rgba = img.convert("RGBA")
    
    min_x, min_y = rgba.width, rgba.height
    max_x, max_y = 0, 0

    for y in range(rgba.height):
        for x in range(rgba.width):
            # Explicitly cast the result to a 4-tuple to satisfy the type checker
            pixel = cast(Tuple[int, int, int, int], rgba.getpixel((x, y)))
            r, g, b, a = pixel
            if a >= alpha_threshold:
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y

    if max_x < min_x or max_y < min_y:
        return None  # No pixels found meeting the alpha threshold

    # The bounding box is defined as (left, top, right, bottom),
    # where right and bottom are one pixel past the last included pixel.
    return (min_x, min_y, max_x + 1, max_y + 1)


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
        apply_alpha_threshold: bool = True
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
        :return: Composited image (RGBA).
        """
        # 1) Isolate the foreground
        fg_rgba = foreground.convert("RGBA")
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

        # 3) Contain approach: Determine the scale required for the subject to exactly fit the frame (without margin)
        contain_scale = min(frame_w / subj_width, frame_h / subj_height)

        # 4) margin_ratio => Safety margin.
        #    The subject fills only margin_ratio * contain_scale.
        #    If you never want to upscale beyond the original size,
        #    limit: final_scale = min(contain_scale * margin_ratio, 1.0)
        final_scale = contain_scale * margin_ratio

        # 5) Scale the entire image
        new_fg_width = int(fg_rgba.width * final_scale)
        new_fg_height = int(fg_rgba.height * final_scale)

        try:
            resample_method = Image.Resampling.LANCZOS
        except AttributeError:
            # Fallback
            resample_method = Image.ANTIALIAS # type: ignore

        fg_rgba_scaled = fg_rgba.resize((new_fg_width, new_fg_height), resample_method)

        # 6) Determine the center of the scaled subject
        scaled_bbox = fg_rgba_scaled.getbbox()
        if scaled_bbox:
            left_s, top_s, right_s, bottom_s = scaled_bbox
            subj_center_x = (left_s + right_s) // 2
            subj_center_y = (top_s + bottom_s) // 2
        else:
            subj_center_x = new_fg_width // 2
            subj_center_y = new_fg_height // 2

        # 7) Center the subject in the frame
        offset_x = (frame_w // 2) - subj_center_x
        offset_y = (frame_h // 2) - subj_center_y

        # 8) Create a new RGBA image with the same size as the background
        new_fg = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        new_fg.paste(fg_rgba_scaled, (offset_x, offset_y), fg_rgba_scaled)

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
        qr_code=qr_img,
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
