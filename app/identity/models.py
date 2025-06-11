import uuid
import secrets
import hashlib
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    JSON,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from passlib.context import CryptContext
from app.db import Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(50), unique=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone_number = Column(String(20))
    date_of_birth = Column(Date)
    country_code = Column(String(2))
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    profile_picture_url = Column(String(500))
    account_type = Column(String(20), default="standard")
    account_status = Column(String(20), default="active")
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(100))
    password_reset_token = Column(String(100))
    password_reset_expires_at = Column(DateTime(timezone=True))
    last_login_at = Column(DateTime(timezone=True))

    roles = relationship(
        "UserRole", back_populates="user", foreign_keys="UserRole.user_id"
    )
    tokens = relationship("ApiToken", back_populates="user")
    kyc_verifications = relationship(
        "KycVerification", back_populates="user", foreign_keys="KycVerification.user_id"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    is_system_role = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    hierarchy_level = Column(Integer, default=0)
    parent_role_id = Column(String(36), ForeignKey("roles.id"))

    parent = relationship("Role", remote_side=[id])
    permissions = relationship("RolePermission", back_populates="role")

    __table_args__ = (Index("idx_role_hierarchy", "parent_role_id", "hierarchy_level"),)


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(150), nullable=False)
    description = Column(Text)
    category = Column(String(50), nullable=False)
    resource = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)

    roles = relationship("RolePermission", back_populates="permission")

    __table_args__ = (Index("idx_permission_resource", "resource", "action"),)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=False)
    permission_id = Column(String(36), ForeignKey("permissions.id"), nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    granted_by = Column(String(36), ForeignKey("users.id"))

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")

    __table_args__ = (
        Index("idx_role_perms", "role_id"),
        Index("idx_perm_roles", "permission_id"),
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(String(36), ForeignKey("users.id"))
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="roles", foreign_keys=[user_id])
    role = relationship("Role")

    __table_args__ = (
        Index("idx_user_roles", "user_id", "is_active"),
        Index("idx_role_users", "role_id", "is_active"),
        {"sqlite_autoincrement": True},
    )


class ApiToken(Base, TimestampMixin):
    __tablename__ = "api_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    token_name = Column(String(100), nullable=False)
    token_type = Column(String(20), nullable=False)
    permissions = Column(JSON, nullable=False, default=dict)
    role_restrictions = Column(JSON, default=dict)
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    is_revoked = Column(Boolean, default=False)

    user = relationship("User", back_populates="tokens")

    def generate_token(self) -> str:
        raw = secrets.token_hex(32)
        self.token_hash = hash_token(raw)
        return raw


class KycVerification(Base, TimestampMixin):
    __tablename__ = "kyc_verifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    kyc_level = Column(String(20), nullable=False, default="basic")
    status = Column(String(20), nullable=False, default="pending")
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True))
    reviewed_by = Column(String(36), ForeignKey("users.id"))
    rejection_reason = Column(Text)
    compliance_score = Column(Integer)

    user = relationship(
        "User", back_populates="kyc_verifications", foreign_keys=[user_id]
    )
    documents = relationship("KycDocument", back_populates="verification")


class KycDocument(Base):
    __tablename__ = "kyc_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kyc_verification_id = Column(
        String(36), ForeignKey("kyc_verifications.id"), nullable=False
    )
    document_type = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    encryption_key_id = Column(String(100), nullable=False)
    ocr_data = Column(JSON)
    validation_status = Column(String(20), default="pending")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    verification = relationship("KycVerification", back_populates="documents")


class PermissionAuditLog(Base):
    __tablename__ = "permission_audit_log"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)
    resource = Column(String(100), nullable=False)
    permission_checked = Column(String(100))
    access_granted = Column(Boolean, nullable=False)
    role_context = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_audit_user", "user_id", "created_at"),
        Index("idx_audit_resource", "resource", "created_at"),
    )


class TokenUsageLog(Base):
    """Audit trail of API token usage."""

    __tablename__ = "token_usage_log"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token_id = Column(String(36), ForeignKey("api_tokens.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    used_at = Column(DateTime(timezone=True), server_default=func.now())

    token = relationship("ApiToken")
    user = relationship("User")

    __table_args__ = (Index("idx_token_usage", "token_id", "used_at"),)
