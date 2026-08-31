import os

# Must be set before app.config.Settings() is instantiated (on first import
# of app.database / app.main below). Real OS env vars always take
# precedence over backend/.env, so this is safe even when a dev .env exists.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-admin-session-secret")
os.environ.setdefault("PAYMENT_PROVIDER", "mock")

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app

DEFAULT_USER = {
    "email": "user@example.com",
    "password": "password123",
    "full_name": "Test User",
    "phone": "+22501020304",
    "gender": "femme",
}


@pytest.fixture(autouse=True)
def _fresh_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def register_user(client):
    """Registers a user and returns an {"Authorization": "Bearer ..."} header
    dict ready to use in subsequent requests."""

    def _register(**overrides):
        payload = {**DEFAULT_USER, **overrides}
        res = client.post("/auth/register", json=payload)
        assert res.status_code == 201, res.text
        login = client.post(
            "/auth/login",
            data={"username": payload["email"], "password": payload["password"]},
        )
        assert login.status_code == 200, login.text
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    return _register


@pytest.fixture
def publish_ad(client):
    """Creates an ad for the given auth headers and pays for it (mock
    provider), returning the published ad."""

    def _publish(headers, **overrides):
        payload = {
            "title": "Bonjour",
            "description": "Une annonce de test",
            "looking_for_gender": "homme",
        }
        payload.update(overrides)
        ad = client.post("/ads", json=payload, headers=headers).json()
        payment = client.post(
            "/payments/initiate",
            json={"type": "ad_publication", "reference_id": ad["id"]},
            headers=headers,
        ).json()
        client.post(f"/payments/{payment['id']}/confirm", headers=headers)
        return ad

    return _publish
