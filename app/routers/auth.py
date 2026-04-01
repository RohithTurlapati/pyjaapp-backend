import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.email import send_otp_email
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.domain import PasswordReset, User
from app.schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    GoogleAuthRequest,
    ProfileUpdateRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    VerifyOTPRequest,
)

router = APIRouter(tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    summary="Register a local user",
    description=(
        "Registers a new user inside the database using a standard email "
        "and password. Returns an active JWT token."
    ),
)
async def register(
    data: UserRegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    user = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        auth_provider="local",
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in for a user",
    description=(
        "Authenticates an existing user matching the provided email and "
        "password. Returns an active JWT token."
    ),
)
async def login(data: UserLoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Authenticate via Google OAuth",
    description=(
        "Verifies a Google Identity ID Token signature and provisions or "
        "accesses the user state."
    ),
)
async def google_auth(
    data: GoogleAuthRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            data.token, requests.Request(), settings.google_client_id
        )
        email = idinfo["email"]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}",
        )

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    requires_password = False
    if not user:
        # Create new user
        user = User(
            email=email,
            password_hash=None,
            auth_provider="google",
            role="user",
            profile_data={"name": idinfo.get("name"), "picture": idinfo.get("picture")},
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        requires_password = True

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "requires_password": requires_password,
        }
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "requires_password": requires_password,
    }


@router.put(
    "/profile",
    response_model=TokenResponse,
    summary="Finalize Google Auth profile",
    description=(
        "Completes a Google Auth two-step flow by securely hashing the user's "
        "new structural password and issuing a final JWT."
    ),
)
async def finalize_profile(
    data: ProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Hash the new password and save it
    current_user.password_hash = get_password_hash(data.password)
    db.add(current_user)
    await db.commit()

    # Issue a final standard JWT
    access_token = create_access_token(
        data={
            "sub": str(current_user.id),
            "role": current_user.role,
            "requires_password": False,
        }
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "requires_password": False,
    }


@router.get(
    "/",
    response_model=UserResponse,
    summary="Retrieve current user",
    description=(
        "Returns the active user profile data via standard Bearer " "token validation."
    ),
)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.post(
    "/forgot-password",
    summary="Initiate forgot password flow",
    description=(
        "Generates a 6-digit OTP and dispatches it via email. "
        "Strictly rate-limited per hour and day to prevent abuse."
    ),
)
async def forgot_password(
    data: ForgotPasswordRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Always return a generic success message so hackers can't enumerate valid emails
    success_msg = {
        "message": "If the email is registered, you will receive an OTP shortly."
    }

    if not user or not user.is_active:
        return success_msg

    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Rule 1: Batch Rate Limit (Max 3 attempts per 1-hour window)
    batch_stmt = select(PasswordReset).where(
        PasswordReset.user_id == user.id, PasswordReset.created_at >= one_hour_ago
    )
    recent_resets = (await db.execute(batch_stmt)).scalars().all()
    if len(recent_resets) >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again in 1 hour.",
        )

    # Rule 2: Daily Rate Limit (Max 9 attempts per day)
    daily_stmt = select(PasswordReset).where(
        PasswordReset.user_id == user.id, PasswordReset.created_at >= today
    )
    today_resets = (await db.execute(daily_stmt)).scalars().all()
    if len(today_resets) >= 9:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily limit reached. Try again tomorrow.",
        )

    # Generate 6-digit OTP
    otp_code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    otp_hash = get_password_hash(otp_code)

    reset_record = PasswordReset(
        user_id=user.id, otp_hash=otp_hash, expires_at=now + timedelta(minutes=10)
    )
    db.add(reset_record)
    await db.commit()

    # Dispatch email
    await send_otp_email(user.email, otp_code)
    return success_msg


@router.post(
    "/verify-otp",
    summary="Verify email OTP",
    description=(
        "Validates a recent 6-digit OTP. Triggers a 3-day Soft Delete lockout "
        "penalty upon 27 consecutive invalid failures. On success, returns an "
        "exclusive 15-minute reset token."
    ),
)
async def verify_otp(
    data: VerifyOTPRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = select(User).where(User.email == data.email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request"
        )

    now = datetime.now(timezone.utc)

    # Get the latest un-expired OTP requested by this user
    otp_stmt = (
        select(PasswordReset)
        .where(
            PasswordReset.user_id == user.id,
            PasswordReset.used == False,  # noqa: E712
            PasswordReset.expires_at > now,
        )
        .order_by(PasswordReset.created_at.desc())
    )

    otp_record = (await db.execute(otp_stmt)).scalars().first()

    if not otp_record or not verify_password(data.otp, otp_record.otp_hash):
        # Apply failure penalty
        user.failed_login_streak += 1
        if user.failed_login_streak >= 27:
            user.is_active = False  # Soft delete / account lock
        db.add(user)

        if otp_record:
            otp_record.failed_attempts += 1
            db.add(otp_record)

        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP"
        )

    # Success
    user.failed_login_streak = 0
    otp_record.used = True  # Mark OTP verified globally in DB
    db.add(user)
    db.add(otp_record)
    await db.commit()

    return {"message": "OTP verified successfully"}


@router.post(
    "/reset-password",
    summary="Reset forgotten password",
    description=(
        "Requires an active 15-minute reset-scoped JWT exactly as provided by "
        "verify-otp. Instantly hashes and replaces the user's password."
    ),
)
async def reset_password(
    data: ResetPasswordRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = select(User).where(User.email == data.email)
    reset_user = (await db.execute(stmt)).scalar_one_or_none()

    if not reset_user or not reset_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request"
        )

    now = datetime.now(timezone.utc)
    valid_window = now - timedelta(minutes=5)

    # Check if this user dynamically verified an OTP within the last 5 minutes
    history_stmt = select(PasswordReset).where(
        PasswordReset.user_id == reset_user.id,
        PasswordReset.used == True,  # noqa: E712
        PasswordReset.created_at >= valid_window,
    )
    validated_otp = (await db.execute(history_stmt)).scalars().first()

    if not validated_otp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "No recently verified OTP flag found. "
                "Please restart the forgot password flow."
            ),
        )

    # Hash new password securely
    reset_user.password_hash = get_password_hash(data.newPassword)
    reset_user.last_password_change = now
    reset_user.password_changes_today = 0
    db.add(reset_user)

    # Instantly purge the verified OTP record to prevent reuse
    await db.delete(validated_otp)
    await db.commit()

    return {"message": "Password reset successfully"}


@router.post(
    "/change-password",
    summary="Manually change password",
    description=(
        "Allows an actively logged-in user to rotate their password after "
        "providing standard validation. Strongly rate-limited globally."
    ),
)
async def change_password(
    data: ChangePasswordRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = select(User).where(User.email == data.email)
    current_user = (await db.execute(stmt)).scalar_one_or_none()

    if not current_user or not current_user.is_active:
        # Generic error to prevent email enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect old password or email",
        )

    now = datetime.now(timezone.utc)
    today = now.date()

    # Check manual change limits dynamically
    if (
        current_user.last_password_change
        and current_user.last_password_change.date() == today
    ):
        if current_user.password_changes_today >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily manual change limit exceeded.",
            )
    else:
        current_user.password_changes_today = 0

    if not current_user.password_hash or not verify_password(
        data.oldPassword, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect old password",  # Deliberately vague
        )

    current_user.password_hash = get_password_hash(data.newPassword)
    current_user.last_password_change = now
    current_user.password_changes_today += 1

    db.add(current_user)
    await db.commit()

    return {"message": "Password changed successfully"}
