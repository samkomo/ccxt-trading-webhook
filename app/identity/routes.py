from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db import SessionLocal
from .models import (
    User,
    Role,
    Permission,
    RolePermission,
    UserRole,
)
from .auth import create_jwt, decode_jwt, get_current_user
from .permissions import permission_required
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


class RolePayload(BaseModel):
    name: str
    display_name: str
    description: str | None = None


class PermissionPayload(BaseModel):
    name: str
    display_name: str
    category: str
    resource: str
    action: str
    description: str | None = None


class AssignRolePayload(BaseModel):
    role_id: str


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


@permission_required("role_management", "read")
@router.get("/roles")
def list_roles(db: Session = Depends(get_db)):
    roles = db.query(Role).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "display_name": r.display_name,
            "description": r.description,
        }
        for r in roles
    ]


@permission_required("role_management", "write")
@router.post("/roles")
def create_role(payload: RolePayload, db: Session = Depends(get_db)):
    role = Role(
        name=payload.name,
        display_name=payload.display_name,
        description=payload.description,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return {"id": role.id}


@permission_required("permission_management", "read")
@router.get("/permissions")
def list_permissions(db: Session = Depends(get_db)):
    perms = db.query(Permission).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "display_name": p.display_name,
            "resource": p.resource,
            "action": p.action,
            "category": p.category,
            "description": p.description,
        }
        for p in perms
    ]


@permission_required("permission_management", "write")
@router.post("/permissions")
def create_permission(payload: PermissionPayload, db: Session = Depends(get_db)):
    perm = Permission(**payload.model_dump())
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return {"id": perm.id}


@permission_required("role_management", "read")
@router.get("/users/{user_id}/roles")
def get_user_roles(user_id: str, db: Session = Depends(get_db)):
    roles = (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id, UserRole.is_active == True)
        .all()
    )
    return [r.role_id for r in roles]


@permission_required("role_management", "write")
@router.post("/users/{user_id}/roles")
def assign_role(user_id: str, payload: AssignRolePayload, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not user or not role:
        raise HTTPException(status_code=404, detail="User or role not found")
    assoc = UserRole(user_id=user_id, role_id=payload.role_id)
    db.add(assoc)
    db.commit()
    db.refresh(assoc)
    return {"id": assoc.id}
