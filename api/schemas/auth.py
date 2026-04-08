"""Auth request/response schemas."""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r"^0\d{9}$")
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(..., pattern=r"^(buyer|worker|contractor|supplier)$")


class LoginRequest(BaseModel):
    email_or_phone: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: UUID
    email: str
    phone: Optional[str] = None
    full_name: str
    role: str
    status: str
    plan: str
    avatar_url: Optional[str] = None
    email_verified: bool
    # Supplier fields
    store_name: Optional[str] = None
    supplier_type: Optional[str] = None
    is_verified_supplier: bool = False

    model_config = {"from_attributes": True}


class UserPreferenceResponse(BaseModel):
    lang: str
    theme: str
    daily_quota: int

    model_config = {"from_attributes": True}


class PreferenceUpdateRequest(BaseModel):
    lang: Optional[str] = Field(None, max_length=5)
    theme: Optional[str] = Field(None, pattern=r"^(dark|light)$")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str


class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str = Field(..., min_length=6, max_length=6)


class MessageResponse(BaseModel):
    message: str
    ok: bool = True
