from pathlib import Path

from PIL import Image

MAX_SIZE = (480, 360)


def normalize_thumbnail(path: Path) -> Path:
    """Shrink to fit MAX_SIZE (keeping aspect ratio) and save as JPEG; returns the new path."""
    target = path.with_suffix(".jpg")
    with Image.open(path) as img:
        if img.format == "JPEG" and img.width <= MAX_SIZE[0] and img.height <= MAX_SIZE[1]:
            return path
        img = img.convert("RGB")
        img.thumbnail(MAX_SIZE)
        img.save(target, "JPEG", quality=85, optimize=True)
    if target != path:
        path.unlink()
    return target
