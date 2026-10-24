"""Schemas cho AI Advisor."""
from pydantic import BaseModel, Field


class EnhanceDescriptionRequest(BaseModel):
    poi_name: str
    keywords: list[str] = Field(..., description="Danh sách từ khóa đặc trưng của quán")
    raw_notes: str = ""
