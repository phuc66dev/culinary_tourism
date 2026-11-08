from typing import Any, List, Optional
from pydantic import BaseModel, EmailStr


# ==========================================
# AUTH SCHEMAS
# ==========================================
class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    username: Optional[str] = None
    email: EmailStr
    password: str
    full_name: str


class VerifyRequest(BaseModel):
    email: str
    otp: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


class GoogleLoginRequest(BaseModel):
    idToken: Optional[str] = None
    id_token: Optional[str] = None
    token: Optional[str] = None


class DeviceLoginRequest(BaseModel):
    device_id: Optional[str] = None
    deviceId: Optional[str] = None


class RefreshRequest(BaseModel):
    refreshToken: Optional[str] = None
    refresh_token: Optional[str] = None


class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str
    tokenType: str = "Bearer"


class UserProfileResponse(BaseModel):
    id: str
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = "user"


# ==========================================
# POI / STALL SCHEMAS
# ==========================================
class POIResponse(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    radius: int = 30
    priority: int = 0
    is_listened: bool = False
    cover_image: Optional[str] = None
    category: Optional[str] = None
    price_range: Optional[str] = None
    opening_hours: Optional[str] = None
    close_hours: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    average_rating: float = 0.0
    total_reviews: int = 0
    distance: Optional[float] = None


class POIListResponse(BaseModel):
    items: List[POIResponse]
    total: int


class POIContentResponse(BaseModel):
    id: str
    stall_id: str
    poi_id: str
    language_code: str
    title: str
    text_content: Optional[str] = None
    translated_text: Optional[str] = None
    audio_url: Optional[str] = None
    duration: Optional[int] = 0
    order: int = 1
    is_fallback: bool = False


class AvailableLanguageResponse(BaseModel):
    language_code: str


class AvailableLanguagesResponse(BaseModel):
    languages: List[AvailableLanguageResponse]


# ==========================================
# LISTENING HISTORY SCHEMAS
# ==========================================
class ListeningHistoryCreate(BaseModel):
    stall_id: Optional[str] = None
    poi_id: Optional[str] = None
    stall_content_id: Optional[str] = None
    poi_content_id: Optional[str] = None
    listened_at: Optional[int] = None
    listen_duration: int = 0
    device_id: Optional[str] = None


class ListeningHistoryItem(BaseModel):
    id: str
    stall_id: str
    poi_id: str
    stall_content_id: Optional[str] = None
    poi_content_id: Optional[str] = None
    listened_at: int
    listen_duration: int
    stall_name: Optional[str] = None
    poi_name: Optional[str] = None
    cover_image: Optional[str] = None


class ListeningHistoryListResponse(BaseModel):
    total: int
    items: List[ListeningHistoryItem]
