from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, Form
import os
from typing import Optional
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import datetime, timedelta, date
from app.db import SessionLocal
from .models import (
    User,
    Role,
    Permission,
    RolePermission,
    UserRole,
    ApiToken,
    KycVerification,
    KycDocument,
    PermissionAuditLog,
)
from .auth import create_jwt, decode_jwt, get_current_user
from .permissions import permission_required
from app.compliance.storage import save_encrypted_data
from app.compliance.ocr import perform_ocr
from app.compliance.virus_scan import scan_for_viruses
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


class TokenCreatePayload(BaseModel):
    token_name: str
    token_type: str
    permissions: dict = {}
    role_restrictions: list[str] | None = None
    expires_in: int | None = None
    mfa_code: str | None = None


class TokenUpdatePayload(BaseModel):
    token_name: str | None = None
    permissions: dict | None = None
    role_restrictions: list[str] | None = None
    expires_in: int | None = None
    is_revoked: bool | None = None


class KycSubmitPayload(BaseModel):
    kyc_level: str = "basic"


class DocumentUploadPayload(BaseModel):
    document_type: str


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
    return {
        "user_id": user.id,
        "email_verification_token": user.email_verification_token,
    }


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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    token = create_jwt(user.id, expires_in=86400)
    user.last_login_at = datetime.utcnow()
    db.commit()
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(current: User = Depends(get_current_user)):
    return {"message": "logged out"}


class MfaSetupResponse(BaseModel):
    secret: str


@router.post("/mfa/setup", response_model=MfaSetupResponse)
def mfa_setup(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    if current.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA already enabled")
    import pyotp
    secret = pyotp.random_base32()
    current.mfa_secret = secret
    db.commit()
    return MfaSetupResponse(secret=secret)


@router.post("/mfa/disable")
def mfa_disable(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    current.mfa_secret = None
    db.commit()
    return {"disabled": True}


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
    if (
        not user
        or not user.password_reset_expires_at
        or user.password_reset_expires_at < datetime.utcnow()
    ):
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
    data = file.file.read()
    if not scan_for_viruses(data):
        raise HTTPException(status_code=400, detail="File failed virus scan")
    path, _ = save_encrypted_data(data, "uploads/profile_pictures")
    user = db.query(User).filter(User.id == current.id).first()
    user.profile_picture_url = path
    db.commit()
    return {"profile_picture_url": user.profile_picture_url}


@router.delete("/account")
def delete_account(
    db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == current.id).first()
    db.delete(user)
    db.commit()
    return {"message": "account deleted"}


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
def assign_role(
    user_id: str, payload: AssignRolePayload, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not user or not role:
        raise HTTPException(status_code=404, detail="User or role not found")
    assoc = UserRole(user_id=user_id, role_id=payload.role_id)
    db.add(assoc)
    db.commit()
    db.refresh(assoc)
    return {"id": assoc.id}


@router.post("/tokens")
def issue_token(
    payload: TokenCreatePayload,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if current.mfa_secret:
        if not payload.mfa_code:
            raise HTTPException(status_code=400, detail="MFA code required")
        try:
            import pyotp
            totp = pyotp.TOTP(current.mfa_secret)
            if not totp.verify(payload.mfa_code, valid_window=1):
                raise HTTPException(status_code=400, detail="Invalid MFA code")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid MFA code")
    token = ApiToken(
        user_id=current.id,
        token_name=payload.token_name,
        token_type=payload.token_type,
        permissions=payload.permissions,
        role_restrictions=(
            {"roles": payload.role_restrictions} if payload.role_restrictions else {}
        ),
    )
    if payload.expires_in:
        token.expires_at = datetime.utcnow() + timedelta(seconds=payload.expires_in)
    raw = token.generate_token()
    db.add(token)
    db.commit()
    db.refresh(token)
    return {"id": token.id, "token": raw}


@router.get("/tokens")
def list_tokens(
    db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    tokens = db.query(ApiToken).filter(ApiToken.user_id == current.id).all()
    return [
        {
            "id": t.id,
            "token_name": t.token_name,
            "token_type": t.token_type,
            "permissions": t.permissions,
            "role_restrictions": t.role_restrictions,
            "expires_at": t.expires_at.isoformat() if t.expires_at else None,
            "is_revoked": t.is_revoked,
        }
        for t in tokens
    ]


@router.delete("/tokens/{token_id}")
def revoke_token_route(
    token_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    token = (
        db.query(ApiToken)
        .filter(ApiToken.id == token_id, ApiToken.user_id == current.id)
        .first()
    )
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    token.is_revoked = True
    db.commit()
    return {"revoked": True}


@router.put("/tokens/{token_id}")
def update_token_route(
    token_id: str,
    payload: TokenUpdatePayload,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    token = (
        db.query(ApiToken)
        .filter(ApiToken.id == token_id, ApiToken.user_id == current.id)
        .first()
    )
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    data = payload.model_dump(exclude_unset=True)
    if "expires_in" in data:
        token.expires_at = datetime.utcnow() + timedelta(seconds=data.pop("expires_in"))
    if "role_restrictions" in data:
        token.role_restrictions = {"roles": data.pop("role_restrictions")}
    for field, value in data.items():
        setattr(token, field, value)
    db.commit()
    db.refresh(token)
    return {"updated": True}


@router.post("/kyc")
def submit_kyc(
    payload: KycSubmitPayload,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    verification = KycVerification(
        user_id=current.id,
        kyc_level=payload.kyc_level,
        status="pending",
    )
    db.add(verification)
    db.commit()
    db.refresh(verification)
    return {"id": verification.id, "status": verification.status}


@router.get("/kyc")
def get_kyc_status(
    db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    verification = (
        db.query(KycVerification)
        .filter(KycVerification.user_id == current.id)
        .order_by(KycVerification.submitted_at.desc())
        .first()
    )
    if not verification:
        raise HTTPException(status_code=404, detail="No KYC record")
    return {
        "id": verification.id,
        "status": verification.status,
        "kyc_level": verification.kyc_level,
    }


@router.post("/kyc/documents")
def upload_kyc_document(
    file: UploadFile,
    document_type: str = Form(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    verification = (
        db.query(KycVerification)
        .filter(KycVerification.user_id == current.id, KycVerification.status == "pending")
        .order_by(KycVerification.submitted_at.desc())
        .first()
    )
    if not verification:
        raise HTTPException(status_code=400, detail="No pending KYC application")
    data = file.file.read()
    if not scan_for_viruses(data):
        raise HTTPException(status_code=400, detail="File failed virus scan")
    path, key_id = save_encrypted_data(data, "uploads/kyc")
    ocr = perform_ocr(data)
    doc = KycDocument(
        kyc_verification_id=verification.id,
        document_type=document_type,
        file_path=path,
        file_size=len(data),
        mime_type=file.content_type,
        encryption_key_id=key_id,
        ocr_data=ocr,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"id": doc.id}


@permission_required("kyc_management", "read")
@router.get("/admin/identity/kyc/pending")
def list_pending_kyc(db: Session = Depends(get_db)):
    verifications = db.query(KycVerification).filter(KycVerification.status == "pending").all()
    return [
        {
            "id": v.id,
            "user_id": v.user_id,
            "kyc_level": v.kyc_level,
            "submitted_at": v.submitted_at.isoformat(),
        }
        for v in verifications
    ]


@permission_required("kyc_management", "write")
@router.put("/admin/identity/kyc/{kyc_id}/approve")
def approve_kyc(kyc_id: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    verification = db.query(KycVerification).filter(KycVerification.id == kyc_id).first()
    if not verification:
        raise HTTPException(status_code=404, detail="KYC record not found")
    verification.status = "approved"
    verification.reviewed_at = datetime.utcnow()
    verification.reviewed_by = current.id
    db.commit()
    return {"status": verification.status}


@permission_required("kyc_management", "write")
@router.put("/admin/identity/kyc/{kyc_id}/reject")
def reject_kyc(
    kyc_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    verification = db.query(KycVerification).filter(KycVerification.id == kyc_id).first()
    if not verification:
        raise HTTPException(status_code=404, detail="KYC record not found")
    verification.status = "rejected"
    verification.reviewed_at = datetime.utcnow()
    verification.reviewed_by = current.id
    verification.rejection_reason = reason
    db.commit()
    return {"status": verification.status}


@permission_required("kyc_management", "read")
@router.get("/admin/identity/compliance")
def compliance_report(db: Session = Depends(get_db)):
    """Aggregate KYC stats and permission audit activity."""
    kyc_totals = {
        s: db.query(func.count(KycVerification.id))
        .filter(KycVerification.status == s)
        .scalar()
        for s in ["pending", "approved", "rejected"]
    }
    kyc_by_level = {
        level: count
        for level, count in db.query(
            KycVerification.kyc_level, func.count(KycVerification.id)
        ).group_by(KycVerification.kyc_level)
    }
    audit_data = [
        {
            "resource": r,
            "action": a,
            "access_granted": g,
            "count": c,
        }
        for r, a, g, c in db.query(
            PermissionAuditLog.resource,
            PermissionAuditLog.action,
            PermissionAuditLog.access_granted,
            func.count(PermissionAuditLog.id),
        )
        .group_by(
            PermissionAuditLog.resource,
            PermissionAuditLog.action,
            PermissionAuditLog.access_granted,
        )
    ]
    return {"kyc": {**kyc_totals, "by_level": kyc_by_level}, "permission_audit": audit_data}
