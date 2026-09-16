from pydantic import BaseModel
from typing import Optional

class ConstellationCreateUpdateSchema(BaseModel):
    name_ko: str
    name_en: str
    description: Optional[str] = None
    mythology: Optional[str] = None
    difficulty: Optional[int] = 1
    image_url: Optional[str] = None
    abbreviation: Optional[str] = None