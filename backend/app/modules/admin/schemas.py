"""Schemas cho Admin Auth, User, Role, Registration Review & Submission Review."""
from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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
