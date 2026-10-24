"""
Schemas cho POI, Localization và MenuItem.
"""
from typing import Optional
from pydantic import BaseModel, Field


class GeoPoint(BaseModel):
    type: str = "Point"
    coordinates: list[float] = Field(..., description="[longitude, latitude]")


class POIBase(BaseModel):
    name: str
    category: str = "street_food"
    address: str
    location: GeoPoint
    trigger_radius: int = 30
    audio_priority: int = 5
    original_description: str
    images: list[str] = []
    is_active: bool = False
