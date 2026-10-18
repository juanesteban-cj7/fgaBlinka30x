import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.app_user import AppUser
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.services.auth import (
    JWT_EXPIRATION_MINUTES,
    create_access_token,
    verify_password,
)

router = APIRouter()
_INVALID_PASSWORD_HASH = bcrypt.hashpw(b"invalid", bcrypt.gensalt()).decode("ascii")


@router.post("/login", response_model=LoginResponse, tags=["auth"])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(AppUser).filter(AppUser.username == payload.username).first()
    password_hash = user.password_hash if user else _INVALID_PASSWORD_HASH
    if not verify_password(payload.password, password_hash) or user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    return LoginResponse(
        access_token=create_access_token(user.id),
        expires_in=JWT_EXPIRATION_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut, tags=["auth"])
def current_user(user: AppUser = Depends(get_current_user)):
    return user
