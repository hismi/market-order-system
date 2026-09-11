from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


ALLOWED_IMAGE_TYPES = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def save_product_image(
    *,
    upload: UploadFile,
    upload_dir: Path,
    max_bytes: int,
) -> str:
    content_type = (upload.content_type or "").lower()
    extension = ALLOWED_IMAGE_TYPES.get(content_type)
    if extension is None:
        raise ValueError("Sadece JPG, PNG, WebP veya GIF yukleyebilirsiniz.")

    contents = upload.file.read(max_bytes + 1)
    if not contents:
        raise ValueError("Bos dosya yuklenemez.")

    if len(contents) > max_bytes:
        max_mb = max_bytes / 1024 / 1024
        raise ValueError(f"Urun gorseli en fazla {max_mb:g} MB olabilir.")

    if not has_valid_image_signature(contents, content_type):
        raise ValueError("Dosya icerigi secilen gorsel tipiyle uyusmuyor.")

    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    upload_path = upload_dir / filename
    upload_path.write_bytes(contents)
    return f"/uploads/products/{filename}"


def has_valid_image_signature(contents: bytes, content_type: str) -> bool:
    if content_type == "image/jpeg":
        return contents.startswith(b"\xff\xd8\xff")

    if content_type == "image/png":
        return contents.startswith(b"\x89PNG\r\n\x1a\n")

    if content_type == "image/gif":
        return contents.startswith((b"GIF87a", b"GIF89a"))

    if content_type == "image/webp":
        return (
            len(contents) >= 12
            and contents[:4] == b"RIFF"
            and contents[8:12] == b"WEBP"
        )

    return False
