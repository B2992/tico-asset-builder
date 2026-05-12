from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


VALID_STYLES = ("fit", "crop", "stretch")


def convert_cover(source: Path, destination: Path, style: str, size: int = 512) -> None:
    if style not in VALID_STYLES:
        raise ValueError(f"Unsupported cover style: {style}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        converted = ImageOps.exif_transpose(image).convert("RGB")
        if style == "fit":
            output = _fit_with_padding(converted, size)
        elif style == "crop":
            output = ImageOps.fit(converted, (size, size), method=Image.Resampling.LANCZOS)
        else:
            output = converted.resize((size, size), Image.Resampling.LANCZOS)
        output.save(destination, format="JPEG", quality=92, optimize=True)


def _fit_with_padding(image: Image.Image, size: int) -> Image.Image:
    fitted = ImageOps.contain(image, (size, size), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size, size), (0, 0, 0))
    x = (size - fitted.width) // 2
    y = (size - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    return canvas

