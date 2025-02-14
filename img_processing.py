import torch
from PIL import Image
from ben2 import BEN_Base # type: ignore
from typing import Optional

class IMGReplacer:
    def __init__(self, refine_foreground: bool = False) -> None:
        """
        Initialize the IMGReplacer.
        Loads the BEN2 model onto the available device (GPU if available).

        :param refine_foreground: Whether to use refined matting for higher-quality results (slower inference).
        """
        self.device: torch.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.refine_foreground: bool = refine_foreground
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

    def remove_background(self, img: Image.Image) -> Image.Image:
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
        foreground: Image.Image = self.model.inference(img_rgb, refine_foreground=self.refine_foreground)
        return foreground

    def replace_background(self, img: Image.Image, new_background: Image.Image) -> Image.Image:
        """
        Replace the background of a given PIL Image with a new background.

        :param img: Input PIL image from which to remove background.
        :param new_background: New background PIL image.
        :return: Final composite image with new background.
        """
        foreground = self.remove_background(img)

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
