"""Schemas cho Owner Portal (MenuItem, POISubmission)."""
from typing import Optional
from pydantic import BaseModel


class MenuItemRequest(BaseModel):
    poi_id: str
    name: str
    price_vnd: int
    image_url: Optional[str] = None
    tags: list[str] = []  # e.g. ["bestseller", "spicy", "vegetarian"]


class POISubmissionRequest(BaseModel):
    poi_id: str
    proposed_changes: dict
