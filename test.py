from PIL import Image

from PIL import Image

from PIL import Image
from typing import Union, Tuple, Optional

def add_frame(background_image_path: str,
              frame_image_path: str,
              output_path: Optional[str] = None,
              scale: float = 1.0,
              offset: Tuple[int, int] = (0, 0),
              crop: Union[int, Tuple[int, int, int, int]] = 0) -> Image.Image:
    """
    Overlays a PNG frame (with a transparent background) on a scaled, optionally cropped background image,
    which is then placed at specified coordinates on a canvas matching the frame's dimensions.
    
    Parameters:
        background_image_path (str): Path to the background image.
        frame_image_path (str): Path to the PNG frame image.
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
    frame = Image.open(frame_image_path).convert("RGBA")
    frame_width, frame_height = frame.size

    # Open the background image and convert to RGBA
    background = Image.open(background_image_path).convert("RGBA")
    
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
    combined = Image.alpha_composite(canvas, frame)
    
    # Save the output if an output path is provided
    if output_path:
        combined.save(output_path)
    
    return combined


result = add_frame("new_background.png", "frame.png", "final_image.png", scale=1.0, offset=(-100, -100), crop = (0, 0, 0, 0))
