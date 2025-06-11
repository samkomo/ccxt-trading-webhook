import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Ensure a temporary SQLite DB is used for tests
os.environ.setdefault("WEBHOOK_SECRET", "testsecret")
os.environ.setdefault("DEFAULT_EXCHANGE", "binance")
os.environ.setdefault("DEFAULT_API_KEY", "key")
os.environ.setdefault("DEFAULT_API_SECRET", "secret")
os.environ["DATABASE_URL"] = "sqlite:///test_onboarding.db"

from main import app
from app.db import Base, engine, SessionLocal
from app.identity.models import (
    ApiToken,
    Permission,
    Role,
    RolePermission,
    UserRole,
    KycVerification,
)

if os.path.exists("test_onboarding.db"):
    os.remove("test_onboarding.db")
Base.metadata.create_all(engine)

transport = ASGITransport(app=app)

@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.mark.asyncio
async def test_register_duplicate_email():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/identity/register",
            json={"email": "dup@example.com", "password": "pw"},
        )
        assert resp.status_code == 200
        resp2 = await client.post(
            "/api/v1/identity/register",
            json={"email": "dup@example.com", "password": "pw"},
        )
        assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_login_invalid_password():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/identity/register",
            json={"email": "login@example.com", "password": "pw"},
        )
        resp = await client.post(
            "/api/v1/identity/login",
            json={"email": "login@example.com", "password": "wrong"},
        )
        assert resp.status_code == 401


def test_api_token_generation():
    token = ApiToken(user_id="u", token_name="t", token_type="personal")
    raw = token.generate_token()
    assert len(raw) == 64
    assert token.token_hash != raw


@pytest.mark.asyncio
async def test_permission_denied_for_kyc_listing():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/identity/register",
            json={"email": "perm@example.com", "password": "pw"},
        )
        login = await client.post(
            "/api/v1/identity/login",
            json={"email": "perm@example.com", "password": "pw"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(
            "/api/v1/identity/admin/identity/kyc/pending",
            headers=headers,
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_kyc_state_transitions():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post(
            "/api/v1/identity/register",
            json={"email": "kyc@example.com", "password": "pw"},
        )
        verify_token = reg.json()["email_verification_token"]
        user_id = reg.json()["user_id"]
        await client.post("/api/v1/identity/verify-email", json={"token": verify_token})
        login = await client.post(
            "/api/v1/identity/login",
            json={"email": "kyc@example.com", "password": "pw"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        submit = await client.post("/api/v1/identity/kyc", json={"kyc_level": "basic"}, headers=headers)
        kyc_id = submit.json()["id"]
        assert submit.json()["status"] == "pending"

        with SessionLocal() as db:
            perm = Permission(
                name="kyc_write",
                display_name="KYC Write",
                category="kyc",
                resource="kyc_management",
                action="write",
            )
            role = Role(name="kyc_admin", display_name="KYC Admin")
            db.add_all([perm, role])
            db.commit()
            db.refresh(perm)
            db.refresh(role)
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
            db.add(UserRole(user_id=user_id, role_id=role.id))
            db.commit()

        approve = await client.put(
            f"/api/v1/identity/admin/identity/kyc/{kyc_id}/approve",
            headers=headers,
        )
        assert approve.status_code == 200
        assert approve.json()["status"] == "approved"

        status = await client.get("/api/v1/identity/kyc", headers=headers)
        assert status.status_code == 200
        assert status.json()["status"] == "approved"

        submit2 = await client.post("/api/v1/identity/kyc", json={"kyc_level": "basic"}, headers=headers)
        kyc_id2 = submit2.json()["id"]
        reject = await client.put(
            f"/api/v1/identity/admin/identity/kyc/{kyc_id2}/reject?reason=bad",
            headers=headers,
        )
        assert reject.status_code == 200
        assert reject.json()["status"] == "rejected"
        with SessionLocal() as db:
            latest = db.query(KycVerification).filter(KycVerification.id == kyc_id2).first()
            assert latest.status == "rejected"


@pytest.mark.asyncio
async def test_full_onboarding_flow():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post(
            "/api/v1/identity/register",
            json={"email": "flow@example.com", "password": "pw"},
        )
        verify_token = reg.json()["email_verification_token"]
        user_id = reg.json()["user_id"]
        await client.post("/api/v1/identity/verify-email", json={"token": verify_token})
        login = await client.post(
            "/api/v1/identity/login",
            json={"email": "flow@example.com", "password": "pw"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        submit = await client.post("/api/v1/identity/kyc", json={"kyc_level": "basic"}, headers=headers)
        kyc_id = submit.json()["id"]

        with SessionLocal() as db:
            perm = Permission(
                name="kyc_write2",
                display_name="KYC Write",
                category="kyc",
                resource="kyc_management",
                action="write",
            )
            role = Role(name="kyc_admin2", display_name="KYC Admin")
            db.add_all([perm, role])
            db.commit()
            db.refresh(perm)
            db.refresh(role)
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
            db.add(UserRole(user_id=user_id, role_id=role.id))
            db.commit()

        approve = await client.put(
            f"/api/v1/identity/admin/identity/kyc/{kyc_id}/approve",
            headers=headers,
        )
        assert approve.status_code == 200

        status = await client.get("/api/v1/identity/kyc", headers=headers)
        assert status.json()["status"] == "approved"
