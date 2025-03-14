import sys
from PIL import Image

import torch
from PIL import Image
from ben2 import BEN_Base # type: ignore
from typing import Optional, Tuple, Union

class IMGReplacer:
    def __init__(self) -> None:
        """
        Initialize the IMGReplacer.
        Loads the BEN2 model onto the available device (GPU if available).

        :param refine_foreground: Whether to use refined matting for higher-quality results (slower inference).
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

        :param img: Input PIL image from which to remove background.
        :return: Foreground PIL Image with alpha channel.
        """
        if self.model is None:
            raise RuntimeError("Model is not loaded. Please call _load_model() first.")

        # Convert to RGB to ensure consistent input
        img_rgb: Image.Image = img.convert("RGB")
        
        # Perform inference (background removal)
        foreground: Image.Image = self.model.inference(img_rgb, refine_foreground=refine_foreground)
        return foreground

    def replace_background(self, foreground: Image.Image, new_background: Image.Image, refine_foreground: bool = False) -> Image.Image:
        """
        Replace the background of a given PIL Image with a new background.

        :param foreground: Input PIL image from which to replace the background.
        :param new_background: New background PIL image.
        :return: Final composite image with new background.
        """

        # Convert both to RGBA
        fg_rgba: Image.Image = foreground.convert("RGBA")
        bg_rgba: Image.Image = new_background.convert("RGBA")

        # Resize the foreground image by adding empty spaces, so the foreground is in the center of the background
        if fg_rgba.size != bg_rgba.size:
            new_size = bg_rgba.size
            fg_rgba_resized = Image.new("RGBA", new_size, (0, 0, 0, 0))
            offset = ((new_size[0] - fg_rgba.size[0]) // 2, (new_size[1] - fg_rgba.size[1]) // 2)
            fg_rgba_resized.paste(fg_rgba, offset)
            fg_rgba = fg_rgba_resized

        # Composite using the alpha channel
        bg_rgba.paste(fg_rgba, (0, 0), fg_rgba)
        return bg_rgba
    
    def add_frame(self,
                background_image: Image.Image,
                frame_image: Image.Image,
                scale: float = 1.0,
                offset: Tuple[int, int] = (0, 0),
                crop: Union[int, Tuple[int, int, int, int]] = 0) -> Image.Image:
        """
        Overlays a PNG frame (with a transparent background) on a scaled, optionally cropped background image,
        which is then placed at specified coordinates on a canvas matching the frame's dimensions.
        
        Parameters:
            background_image (Image.Image): The background image.
            frame_image (Image.Image): The PNG frame image.
            output_path (Optional[str]): If provided, the combined image is saved to this path.
            scale (float): Scaling factor for the background image 
                        (e.g., 0.5 for 50% size, 2.0 for 200%). Defaults to 1.0.
            offset (Tuple[int, int]): (x, y) coordinates specifying where to place the processed background
                                    on the final canvas (top-left corner). Defaults to (0, 0).
            crop (Union[int, Tuple[int, int, int, int]]): If an int, crops that many pixels from all four sides of the scaled background.
                                                        If a tuple, it should be (crop_top, crop_right, crop_left, crop_bottom)
                                                        specifying the number of pixels to crop from the top, right, left, and bottom sides respectively.
                                                        Defaults to 0 (no cropping).
        
        Returns:
            Image.Image: The resulting image with the frame overlay.
        """
        # Open the frame image and convert to RGBA for transparency support
        frame_width, frame_height = frame_image.size

        # Open the background image and convert to RGBA
        background = background_image.convert("RGBA")
        
        # Scale the background image by the provided factor
        bg_width, bg_height = background.size
        new_bg_width = int(bg_width * scale)
        new_bg_height = int(bg_height * scale)
        
        try:
            resample_method = Image.Resampling.LANCZOS
        except AttributeError:
            # Fallback for older Pillow versions
            resample_method = Image.ANTIALIAS # type: ignore

        scaled_background = background.resize((new_bg_width, new_bg_height), resample_method)
        
        # Apply cropping if requested
        if crop:
            # If crop is an int, apply equally to all sides
            if isinstance(crop, int):
                crop = (crop, crop, crop, crop)
            elif not (isinstance(crop, (tuple, list)) and len(crop) == 4):
                raise ValueError("crop must be an int or a tuple/list of four integers: (crop_top, crop_right, crop_left, crop_bottom)")
            
            crop_top, crop_right, crop_left, crop_bottom = crop
            
            # Calculate new crop boundaries for the scaled background
            new_left = crop_left
            new_top = crop_top
            new_right = scaled_background.width - crop_right
            new_bottom = scaled_background.height - crop_bottom
            
            # Validate boundaries
            if new_left < 0 or new_top < 0 or new_right > scaled_background.width or new_bottom > scaled_background.height or new_left >= new_right or new_top >= new_bottom:
                raise ValueError("Crop values are out of bounds for the scaled background image.")
            
            scaled_background = scaled_background.crop((new_left, new_top, new_right, new_bottom))
        
        # Create a new transparent canvas with the same dimensions as the frame
        canvas = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
        
        # Paste the processed background onto the canvas at the specified offset.
        # The mask ensures that any transparency in the background image is preserved.
        canvas.paste(scaled_background, offset, scaled_background)
        
        # Composite the frame over the background canvas
        combined = Image.alpha_composite(canvas, frame_image)
        
        return combined




def main() -> None:
    # Define file paths
    input_image_path = "./image.png"           # Original image from which you want to remove background
    new_background_path = "./new_background.png"  # The new background you want to add
    output_final_path = "./final_image.png"     # Where you will store the final composite
    frame_path = "./frame.png"                  # Optional: frame to add around the final

    # Read images
    input_img = Image.open(input_image_path)
    background_img = Image.open(new_background_path)

    # Create an instance of IMGReplacer (assuming the class is in the same file or imported)
    replacer = IMGReplacer()

    # 1) Remove background from the input image
    no_background = replacer.remove_background(input_img, refine_foreground=False)

    # 2) Remove background from the input image
    new_background = replacer.replace_background(no_background, background_img, refine_foreground=False)

    img_with_frame = replacer.add_frame(new_background, Image.open(frame_path), scale=1.0, offset=(100, 100), crop = (0, 0, 0, 0))

    # 3) Save the final composite image
    img_with_frame.save(output_final_path)
    print(f"Final composite image saved to: {output_final_path}")


if __name__ == "__main__":
    main()