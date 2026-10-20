from io import BytesIO

from PIL import Image


def png_to_webp_thumbnail(png_bytes: bytes, max_size: int = 480) -> bytes:
    """
    Downscale an encoded image so that neither side exceeds max_size and return it as WebP.
    WebP keeps transparency, which backgrounds and cut-out photos rely on.
    """
    with Image.open(BytesIO(png_bytes)) as img:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        with BytesIO() as output:
            img.save(output, format="WEBP", quality=80)
            return output.getvalue()
