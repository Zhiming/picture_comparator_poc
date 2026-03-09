import base64
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass


SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
MAX_IMAGE_SIZE_MB = 10


@dataclass
class ImageObject:
    filename: str
    base64: str
    media_type: str


def validate_image_file(file_path: Path, logger: logging.Logger) -> Tuple[bool, Optional[str]]:
    if file_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        return False, f"Unsupported file extension: {file_path.suffix}"

    try:
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_IMAGE_SIZE_MB:
            return False, f"File too large: {file_size_mb:.2f}MB (max {MAX_IMAGE_SIZE_MB}MB)"
    except OSError as e:
        return False, f"Cannot access file: {str(e)}"

    return True, None


def load_image_as_base64(file_path: Path, logger: logging.Logger) -> Optional[ImageObject]:
    try:
        is_valid, error_msg = validate_image_file(file_path, logger)
        if not is_valid:
            logger.warning(f"Skipping {file_path.name}: {error_msg}")
            return None

        with open(file_path, 'rb') as f:
            image_bytes = f.read()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            media_type = f'image/{file_path.suffix[1:].lower()}'

            return ImageObject(
                filename=file_path.name,
                base64=base64_image,
                media_type=media_type
            )

    except OSError as e:
        logger.error(f"Failed to read {file_path.name}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading {file_path.name}: {str(e)}")
        return None


def load_images_from_folder(folder_path: str, logger: logging.Logger) -> List[ImageObject]:
    images_path = Path(folder_path)

    if not images_path.exists():
        raise ValueError(f"Images folder does not exist: {folder_path}")

    if not images_path.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")

    images = []

    for img_file in sorted(images_path.iterdir()):
        if img_file.is_file():
            image_obj = load_image_as_base64(img_file, logger)
            if image_obj:
                images.append(image_obj)

    return images
