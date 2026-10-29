"""Schemas cho Admin Auth, User, Role, Registration Review & Submission Review."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["admin@quan4culinary.vn"])
    password: str = Field(min_length=1, max_length=72, examples=["ChangeMe123!"])


class UserMe(BaseModel):
    """Thông tin phiên đăng nhập hiện tại — Frontend lưu vào `authStore.setUser()`."""

    id: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str = Field(examples=["super_admin", "admin", "poi_owner", "user"])
    permissions: list[str] = Field(examples=[["poi:read", "poi:approve"]])
    is_poi_owner_verified: bool = False
    must_change_password: bool = False


class LoginResponse(BaseModel):
    user: UserMe
    # Chỉ có khi APP_ENV=development, để test bằng Bearer header / curl. Production luôn là null
    # (token chỉ nằm trong httpOnly Cookie).
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class RefreshRequest(BaseModel):
    """Body tuỳ chọn — mặc định server đọc refresh_token từ httpOnly Cookie."""

    refresh_token: Optional[str] = None


class MessageResponse(BaseModel):
    message: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=12, max_length=72)


class UserCreateRequest(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=12, max_length=72)
    role: str = Field(min_length=1, max_length=50)
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    role: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None


class ResetPasswordRequest(BaseModel):
    password: str = Field(min_length=12, max_length=72)


class RoleCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{2,49}$")
    permissions: list[str] = Field(default_factory=list, max_length=32)
    priority: int = Field(default=5, ge=1, le=99)


class RoleUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}
    permissions: list[str] = Field(min_length=0, max_length=32)
    priority: int | None = Field(default=None, ge=1, le=99)


class OwnerRegisterRequest(BaseModel):
    full_name: str
    phone: str
    email: EmailStr
    password: str
    poi_name: str
    poi_address: str
    cccd_number: str
    storefront_image_url: Optional[str] = None


class ReviewDecisionRequest(BaseModel):
    action: str  # "approve" | "reject"
    admin_note: Optional[str] = None
    expected_revision: Optional[int] = None  # dùng cho review submission chống stale diff

# Task 3.4: only allow editable POI fields; never accept Mongo operators / owner_id / IDs.
from typing import Literal
from pydantic import ConfigDict, field_validator


class POILocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]  # GeoJSON: [longitude, latitude]

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, value):
        lng, lat = value
        if not (-180 <= lng <= 180 and -90 <= lat <= 90):
            raise ValueError("Tọa độ không hợp lệ (longitude, latitude)")
        return value


class POICreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=180)
    address: str = Field(min_length=1, max_length=400)
    ward: str = Field(min_length=1, max_length=80)
    location: POILocation
    original_description: str = Field(min_length=1, max_length=8000)
    category: str = Field(default="street_food", min_length=1, max_length=80)
    images: list[str] = Field(default_factory=list, max_length=20)
    trigger_radius: int = Field(default=30, ge=5, le=500)
    audio_priority: int = Field(default=5, ge=1, le=10)
    is_active: bool = False

    @field_validator("images")
    @classmethod
    def validate_images(cls, images):
        if any(not isinstance(image, str) or len(image) > 2048 or not image.strip() for image in images):
            raise ValueError("Đường dẫn ảnh không hợp lệ")
        return images


class POIUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str | None = Field(default=None, min_length=1, max_length=180)
    address: str | None = Field(default=None, min_length=1, max_length=400)
    ward: str | None = Field(default=None, min_length=1, max_length=80)
    location: POILocation | None = None
    original_description: str | None = Field(default=None, min_length=1, max_length=8000)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    images: list[str] | None = Field(default=None, max_length=20)
    trigger_radius: int | None = Field(default=None, ge=5, le=500)
    audio_priority: int | None = Field(default=None, ge=1, le=10)
    is_active: bool | None = None
    expected_revision: int | None = Field(default=None, ge=0)

    @field_validator("images")
    @classmethod
    def validate_images(cls, images):
        return POICreateRequest.validate_images(images) if images is not None else images


class EnglishLocalizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(min_length=1, max_length=8000)
    expected_revision: int = Field(ge=0)
