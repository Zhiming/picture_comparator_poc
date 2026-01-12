from enum import Enum
from pydantic import BaseModel

class ImageQualityEnum(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ImageQuality(BaseModel):
    quality: ImageQualityEnum