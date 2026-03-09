from enum import Enum
from pydantic import BaseModel


class ImageQualityEnum(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ImageQuality(BaseModel):
    quality: ImageQualityEnum


class VisualContext(BaseModel):
    summary: str
    possible_causes: list[str]
    comparison_notes: str