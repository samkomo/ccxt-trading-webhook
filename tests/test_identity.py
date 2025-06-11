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
os.environ["DATABASE_URL"] = "sqlite:///test_identity.db"

from main import app
from app.db import Base, engine

if os.path.exists('test_identity.db'):
    os.remove('test_identity.db')
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
        resp = await client.post("/api/v1/identity/register", json={"email": "a@example.com", "password": "pass"})
        assert resp.status_code == 200
        token = resp.json()["email_verification_token"]
        resp = await client.post("/api/v1/identity/verify-email", json={"token": token})
        assert resp.status_code == 200
        resp = await client.post("/api/v1/identity/login", json={"email": "a@example.com", "password": "pass"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        reset_resp = await client.post("/api/v1/identity/forgot-password", json={"email": "a@example.com"})
        reset_token = reset_resp.json()["reset_token"]
        resp = await client.post("/api/v1/identity/reset-password", json={"token": reset_token, "new_password": "newpass"})
        assert resp.status_code == 200
        resp = await client.post("/api/v1/identity/login", json={"email": "a@example.com", "password": "newpass"})
        assert resp.status_code == 200

