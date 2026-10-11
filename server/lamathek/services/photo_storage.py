from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

from lamathek.config import media_path

WEBP_QUALITY = 85
MAX_FULL_EDGE = 2560
THUMB_SIZES = (160, 640)

ALLOWED_UPLOAD_MIME = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)


def photos_dir() -> Path:
    root = media_path()
    directory = root / "photos"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def thumbs_dir(photo_id: int) -> Path:
    directory = media_path() / "thumbs" / str(photo_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def original_path(photo_id: int) -> Path:
    return photos_dir() / f"{photo_id}.webp"


def thumb_path(photo_id: int, edge: int) -> Path:
    return thumbs_dir(photo_id) / f"{edge}.webp"


def delete_photo_files(photo_id: int) -> None:
    original = original_path(photo_id)
    if original.is_file():
        original.unlink()
    thumb_root = media_path() / "thumbs" / str(photo_id)
    if thumb_root.is_dir():
        for child in thumb_root.iterdir():
            if child.is_file():
                child.unlink()
        thumb_root.rmdir()


def _resize_max_edge(image: Image.Image, max_edge: int) -> Image.Image:
    image = image.copy()
    image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    return image


def _to_rgb(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        return background
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def save_photo_variants(photo_id: int, raw_bytes: bytes) -> None:
    try:
        image = Image.open(BytesIO(raw_bytes))
        image.verify()
        image = Image.open(BytesIO(raw_bytes))
    except OSError as exc:
        raise ValueError("invalid_image") from exc

    image = ImageOps.exif_transpose(image)
    image = _to_rgb(image)
    full = _resize_max_edge(image, MAX_FULL_EDGE)
    full.save(original_path(photo_id), format="WEBP", quality=WEBP_QUALITY, method=6)

    for edge in THUMB_SIZES:
        thumb = _resize_max_edge(image, edge)
        thumb.save(thumb_path(photo_id, edge), format="WEBP", quality=WEBP_QUALITY, method=6)


def resolve_served_path(photo_id: int, size: str) -> Path | None:
    if size == "full":
        path = original_path(photo_id)
        return path if path.is_file() else None
    if size in {"160", "640"}:
        path = thumb_path(photo_id, int(size))
        return path if path.is_file() else None
    return None
