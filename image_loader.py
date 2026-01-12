import base64
from pathlib import Path
from typing import List

class ImageObject:
    def __init__(self, filename, base64, media_type):
        self.filename = filename
        self.base64 = base64
        self.media_type = media_type

def get_images_as_base64(images_folder="images") -> List[ImageObject]:
    """Get all images from folder and convert them to base64."""
    images_data = []
    images_path = Path(images_folder)

    # Get all image files (png, jpg, jpeg, gif, bmp, webp)
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']

    for img_file in sorted(images_path.iterdir()):
        if img_file.suffix.lower() in image_extensions:
            with open(img_file, 'rb') as f:
                image_bytes = f.read()
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                media_type = f'image/{img_file.suffix[1:].lower()}'
                images_data.append(ImageObject(
                    img_file.name, base64_image, media_type
                ))

    return images_data
