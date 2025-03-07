import sys
from PIL import Image

import torch
from PIL import Image
from ben2 import BEN_Base # type: ignore
from typing import Optional

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

    def replace_background(self, img: Image.Image, new_background: Image.Image, refine_foreground: bool = False) -> Image.Image:
        """
        Replace the background of a given PIL Image with a new background.

        :param img: Input PIL image from which to remove background.
        :param new_background: New background PIL image.
        :return: Final composite image with new background.
        """
        foreground = self.remove_background(img, refine_foreground)

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



def main() -> None:
    # Define file paths
    input_image_path = "./image.png"           # Original image from which you want to remove background
    new_background_path = "./new_background.jpg"  # The new background you want to add
    output_final_path = "./final_image.png"     # Where you will store the final composite

    # Read images
    input_img = Image.open(input_image_path)
    background_img = Image.open(new_background_path)

    # Create an instance of IMGReplacer (assuming the class is in the same file or imported)
    replacer = IMGReplacer()

    # 1) Remove background from the input image
    final_img = replacer.replace_background(input_img, background_img, refine_foreground=False)

    # 2) Save the final composite image
    final_img.save(output_final_path)
    print(f"Final composite image saved to: {output_final_path}")


if __name__ == "__main__":
    # If you want to optionally pass paths via command line, you could do so here.
    # For simplicity, we’re using the hard-coded paths above.
    main()