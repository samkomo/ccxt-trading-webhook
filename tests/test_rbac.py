import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("WEBHOOK_SECRET", "testsecret")
os.environ.setdefault("DEFAULT_EXCHANGE", "binance")
os.environ.setdefault("DEFAULT_API_KEY", "key")
os.environ.setdefault("DEFAULT_API_SECRET", "secret")
os.environ["DATABASE_URL"] = "sqlite:///test_rbac.db"

from main import app
from sqlalchemy import text
from app.db import Base, engine, SessionLocal
from app.identity.models import Permission, Role, RolePermission, UserRole

if os.path.exists('test_rbac.db'):
    os.remove('test_rbac.db')
Base.metadata.create_all(engine)

transport = ASGITransport(app=app)

@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

async def register_and_login(client):
    resp = await client.post("/api/v1/identity/register", json={"email": "u@example.com", "password": "pw"})
    token = resp.json()["email_verification_token"]
    user_id = resp.json()["user_id"]
    await client.post("/api/v1/identity/verify-email", json={"token": token})
    resp = await client.post("/api/v1/identity/login", json={"email": "u@example.com", "password": "pw"})
    return user_id, resp.json()["access_token"]

@pytest.mark.asyncio
async def test_permission_middleware():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id, token = await register_and_login(client)

        # Attempt to list roles without permission
        resp = await client.get("/api/v1/identity/roles", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

        # Set up permission and role directly in DB
        with SessionLocal() as db:
            perm = Permission(name="role_read", display_name="Role Read", category="role", resource="role_management", action="read")
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
            db.commit()

        resp = await client.get("/api/v1/identity/roles", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        # Check audit log entries
        with SessionLocal() as db:
            count = db.execute(text("select count(*) from permission_audit_log")).fetchone()[0]
            assert count == 2
