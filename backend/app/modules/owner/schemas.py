"""Validated request schemas for the Owner Portal."""
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modules.admin.schemas import POILocation


def _clean_tags(tags):
    clean = [tag.strip() for tag in tags]
    if any(not tag or len(tag) > 32 for tag in clean):
        raise ValueError("Tag phải có từ 1 đến 32 ký tự")
    if len(set(clean)) != len(clean):
        raise ValueError("Tag không được trùng lặp")
    return clean


class OwnerRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=8, max_length=30)
    email: EmailStr
    password: str = Field(min_length=12, max_length=72)
    poi_name: str = Field(min_length=1, max_length=180)
    poi_address: str = Field(min_length=1, max_length=400)
    poi_location: POILocation | None = None
    poi_ward: str | None = Field(default=None, min_length=1, max_length=80)
    cccd_number: str = Field(min_length=9, max_length=12, pattern=r"^(?:\d{9}|\d{12})$")
    storefront_image_url: Optional[str] = Field(default=None, max_length=2048)


MenuImageUrl = Annotated[str, Field(min_length=1, max_length=2048)]


class MenuItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    poi_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    price_vnd: int = Field(gt=0, le=1_000_000_000)
    image_url: Optional[str] = Field(default=None, max_length=2048)
    image_urls: list[MenuImageUrl] | None = Field(default=None, max_length=6)
    tags: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, tags):
        return _clean_tags(tags)


class MenuItemUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    price_vnd: int | None = Field(default=None, gt=0, le=1_000_000_000)
    image_url: Optional[str] = Field(default=None, max_length=2048)
    image_urls: list[MenuImageUrl] | None = Field(default=None, max_length=6)
    tags: list[str] | None = Field(default=None, max_length=12)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, tags):
        if tags is None:
            return tags
        return _clean_tags(tags)


class OwnerPOIAvailabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_open: bool


class POISubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    poi_id: str = Field(min_length=1, max_length=64)
    proposed_changes: dict = Field(min_length=1, max_length=10)


class POIPhotoSubmissionRequest(POISubmissionRequest):
    proposed_changes: dict = Field(default_factory=dict, max_length=10)
