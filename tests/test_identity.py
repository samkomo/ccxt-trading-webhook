import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport
os.environ.setdefault("TOKEN_DB_PATH", "test_tokens.db")
from app.identity.auth import verify_token

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Ensure a temporary SQLite DB is used for tests
os.environ.setdefault("WEBHOOK_SECRET", "testsecret")
os.environ.setdefault("DEFAULT_EXCHANGE", "binance")
os.environ.setdefault("DEFAULT_API_KEY", "key")
os.environ.setdefault("DEFAULT_API_SECRET", "secret")
os.environ["DATABASE_URL"] = "sqlite:///test_identity.db"

from main import app
from app.db import Base, engine, SessionLocal
from app.identity.models import (
    Permission,
    Role,
    RolePermission,
    UserRole,
    KycVerification,
    PermissionAuditLog,
)

if os.path.exists("test_identity.db"):
    os.remove("test_identity.db")
Base.metadata.create_all(engine)


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


transport = ASGITransport(app=app)


@pytest.mark.asyncio
async def test_register_verify_login_flow(tmp_path):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/identity/register",
            json={"email": "a@example.com", "password": "pass"},
        )
        assert resp.status_code == 200
        token = resp.json()["email_verification_token"]
        resp = await client.post("/api/v1/identity/verify-email", json={"token": token})
        assert resp.status_code == 200
        resp = await client.post(
            "/api/v1/identity/login",
            json={"email": "a@example.com", "password": "pass"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        reset_resp = await client.post(
            "/api/v1/identity/forgot-password", json={"email": "a@example.com"}
        )
        reset_token = reset_resp.json()["reset_token"]
        resp = await client.post(
            "/api/v1/identity/reset-password",
            json={"token": reset_token, "new_password": "newpass"},
        )
        assert resp.status_code == 200
        resp = await client.post(
            "/api/v1/identity/login",
            json={"email": "a@example.com", "password": "newpass"},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_profile_crud_and_delete(tmp_path):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # register and login
        await client.post(
            "/api/v1/identity/register",
            json={"email": "b@example.com", "password": "pass"},
        )
        login = await client.post(
            "/api/v1/identity/login",
            json={"email": "b@example.com", "password": "pass"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # get profile
        resp = await client.get("/api/v1/identity/profile", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "b@example.com"

        # update profile
        resp = await client.put(
            "/api/v1/identity/profile",
            json={"first_name": "Bob"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Bob"

        # upload picture
        files = {"file": ("pic.txt", b"img", "text/plain")}
        resp = await client.post(
            "/api/v1/identity/profile/picture",
            files=files,
            headers=headers,
        )
        assert resp.status_code == 200
        assert "profile_picture_url" in resp.json()

        # delete account
        resp = await client.delete("/api/v1/identity/account", headers=headers)
        assert resp.status_code == 200
        # access after deletion should fail
        resp = await client.get("/api/v1/identity/profile", headers=headers)
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_token_endpoints(tmp_path):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/identity/register",
            json={"email": "c@example.com", "password": "pass"},
        )
        login = await client.post(
            "/api/v1/identity/login",
            json={"email": "c@example.com", "password": "pass"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/identity/tokens",
            json={"token_name": "t1", "token_type": "personal"},
            headers=headers,
        )
        assert resp.status_code == 200
        api_token = resp.json()["token"]
        token_id = resp.json()["id"]

        assert verify_token(api_token, "n1") is True

        resp = await client.get("/api/v1/identity/tokens", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        resp = await client.put(
            f"/api/v1/identity/tokens/{token_id}",
            json={"token_name": "updated"},
            headers=headers,
        )
        assert resp.status_code == 200

        resp = await client.delete(
            f"/api/v1/identity/tokens/{token_id}", headers=headers
        )
        assert resp.status_code == 200

        resp = await client.get("/api/v1/identity/tokens", headers=headers)
        assert resp.json()[0]["is_revoked"] is True


@pytest.mark.asyncio
async def test_compliance_report(tmp_path):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # create user and login
        reg = await client.post("/api/v1/identity/register", json={"email": "d@example.com", "password": "pass"})
        user_id = reg.json()["user_id"]
        login = await client.post(
            "/api/v1/identity/login",
            json={"email": "d@example.com", "password": "pass"},
        )
        token = login.json()["access_token"]

        # grant permission
        with SessionLocal() as db:
            perm = Permission(
                name="kyc_read",
                display_name="KYC Read",
                category="kyc",
                resource="kyc_management",
                action="read",
            )
            db.add(perm)
            db.commit()
            db.refresh(perm)
            role = Role(name="admin", display_name="Admin")
            db.add(role)
            db.commit()
            db.refresh(role)
            rp = RolePermission(role_id=role.id, permission_id=perm.id)
            db.add(rp)
            db.commit()
            ur = UserRole(user_id=user_id, role_id=role.id)
            db.add(ur)

            db.add_all([
                KycVerification(user_id=user_id, kyc_level="basic", status="pending"),
                KycVerification(user_id=user_id, kyc_level="basic", status="approved"),
                KycVerification(user_id=user_id, kyc_level="basic", status="rejected"),
            ])
            db.add_all([
                PermissionAuditLog(user_id=user_id, action="read", resource="kyc_management", access_granted=True),
                PermissionAuditLog(user_id=user_id, action="read", resource="kyc_management", access_granted=False),
            ])
            db.commit()

        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(
            "/api/v1/identity/admin/identity/compliance",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["kyc"]["approved"] == 1
        assert data["kyc"]["pending"] == 1
        assert data["kyc"]["rejected"] == 1
        assert len(data["permission_audit"]) >= 2

