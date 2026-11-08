"""Request schemas for the owner AI writing assistant."""
from pydantic import BaseModel, ConfigDict, Field


class EnhanceDescriptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    poi_id: str = Field(min_length=1, max_length=64)
    poi_name: str = Field(min_length=1, max_length=180)
    keywords: list[str] = Field(min_length=1, max_length=12)
    raw_notes: str = Field(default="", max_length=2000)
