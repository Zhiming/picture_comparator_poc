from enum import Enum
from pydantic import BaseModel

class VisualContext(BaseModel):
    summary: str
    possible_causes: list[str]
    comparison_notes: str