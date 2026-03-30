from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.domain import User
from app.schemas.user import (
    GoogleAuthRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=TokenResponse)
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


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if (
        not user
        or user.auth_provider != "local"
        or not verify_password(data.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/google", response_model=TokenResponse)
async def google_auth(
    data: GoogleAuthRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            data.token, requests.Request(), settings.google_client_id
        )
        email = idinfo["email"]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token"
        )

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    requires_background = False
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
        requires_background = True

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "requires_background": requires_background,
        }
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "requires_background": requires_background,
    }


@router.get("/", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
