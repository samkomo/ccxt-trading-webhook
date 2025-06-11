from fastapi import APIRouter, HTTPException, Depends, status, UploadFile
import os
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from app.db import SessionLocal
from .models import User
from .auth import create_jwt, decode_jwt, get_current_user
import secrets

router = APIRouter(prefix="/api/v1/identity", tags=["identity"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RegisterPayload(BaseModel):
    email: EmailStr
    password: str | None = None
    username: str | None = None
    registration_type: str | None = "standard"  # standard | social | demo


class VerifyEmailPayload(BaseModel):
    token: str


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class ForgotPayload(BaseModel):
    email: EmailStr


class ResetPayload(BaseModel):
    token: str
    new_password: str


class ProfileResponse(BaseModel):
    id: str
    email: EmailStr
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    date_of_birth: date | None = None
    country_code: str | None = None
    timezone: str | None = None
    language: str | None = None
    profile_picture_url: str | None = None


class UpdateProfilePayload(BaseModel):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    date_of_birth: date | None = None
    country_code: str | None = None
    timezone: str | None = None
    language: str | None = None


@router.post("/register")
def register(payload: RegisterPayload, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email, username=payload.username)

    if payload.registration_type == "demo":
        user.account_type = "demo"
        user.email_verified = True
        user.set_password(secrets.token_hex(8))
    elif payload.registration_type == "social":
        user.account_type = "social"
        user.email_verified = True
        user.set_password(secrets.token_hex(8))
    else:
        if not payload.password:
            raise HTTPException(status_code=400, detail="Password required")
        user.set_password(payload.password)
        token = create_jwt(user.email, expires_in=3600)
        user.email_verification_token = token

    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user_id": user.id, "email_verification_token": user.email_verification_token}


@router.post("/verify-email")
def verify_email(payload: VerifyEmailPayload, db: Session = Depends(get_db)):
    email = decode_jwt(payload.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = db.query(User).filter(User.email_verification_token == payload.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    user.email_verified = True
    user.email_verification_token = None
    db.commit()
    return {"message": "email verified"}


@router.post("/login")
def login(payload: LoginPayload, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.verify_password(payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_jwt(user.id, expires_in=86400)
    user.last_login_at = datetime.utcnow()
    db.commit()
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(current: User = Depends(get_current_user)):
    return {"message": "logged out"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPayload, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        return {"message": "ok"}
    token = create_jwt(user.id, expires_in=3600)
    user.password_reset_token = token
    user.password_reset_expires_at = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    return {"reset_token": token}


@router.post("/reset-password")
def reset_password(payload: ResetPayload, db: Session = Depends(get_db)):
    user_id = decode_jwt(payload.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = db.query(User).filter(User.password_reset_token == payload.token).first()
    if not user or not user.password_reset_expires_at or user.password_reset_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user.set_password(payload.new_password)
    user.password_reset_token = None
    user.password_reset_expires_at = None
    db.commit()
    return {"message": "password updated"}


@router.get("/profile", response_model=ProfileResponse)
def get_profile(current: User = Depends(get_current_user)):
    return ProfileResponse(
        id=current.id,
        email=current.email,
        username=current.username,
        first_name=current.first_name,
        last_name=current.last_name,
        phone_number=current.phone_number,
        date_of_birth=current.date_of_birth,
        country_code=current.country_code,
        timezone=current.timezone,
        language=current.language,
        profile_picture_url=current.profile_picture_url,
    )


@router.put("/profile", response_model=ProfileResponse)
def update_profile(
    payload: UpdateProfilePayload,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current.id).first()
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return get_profile(user)


@router.post("/profile/picture")
def upload_profile_picture(
    file: UploadFile,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    directory = "uploads/profile_pictures"
    os.makedirs(directory, exist_ok=True)
    filename = f"{current.id}_{file.filename}"
    path = os.path.join(directory, filename)
    with open(path, "wb") as out:
        out.write(file.file.read())
    user = db.query(User).filter(User.id == current.id).first()
    user.profile_picture_url = path
    db.commit()
    return {"profile_picture_url": user.profile_picture_url}


@router.delete("/account")
def delete_account(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == current.id).first()
    db.delete(user)
    db.commit()
    return {"message": "account deleted"}

