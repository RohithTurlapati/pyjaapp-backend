import uuid
from typing import Any

from pydantic import BaseModel, EmailStr


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    requires_password: bool = False


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: str
    profile_data: dict[str, Any] | None

    class Config:
        from_attributes = True


class ProfileUpdateRequest(BaseModel):
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    newPassword: str


class ChangePasswordRequest(BaseModel):
    email: EmailStr
    oldPassword: str
    newPassword: str
