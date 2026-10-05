"""Phase 0 security helpers + auth dependencies (mentor-owned)."""

import jwt
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app import models
from app.deps import get_current_user, require_admin
from app.main import create_app
from app.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hash_and_verify():
    hashed = get_password_hash("password123")
    assert hashed != "password123"
    assert verify_password("password123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_jwt_roundtrip(user):
    token = create_access_token(user.id)
    assert decode_access_token(token) == user.id


def test_jwt_invalid_rejected():
    with pytest.raises(jwt.PyJWTError):
        decode_access_token("not-a-token")


def _client_with_user(db, user):
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


def test_get_current_user_blocks_deactivated(db, client):
    """Deactivated user with a valid token still gets 403 (PRD B1)."""
    from app.database import get_db

    u = models.User(
        username="zed", email="zed@chirp.local",
        password_hash=get_password_hash("password123"),
        display_name="Zed", role="user", is_active=False,
    )
    db.add(u)
    db.commit()
    db.refresh(u)

    app = create_app()

    def override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_db

    @app.get("/_probe")
    def probe(current=Depends(get_current_user)):  # noqa: B008
        return {"ok": True}

    c = TestClient(app, raise_server_exceptions=False)
    token = create_access_token(u.id)
    r = c.get("/_probe", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_require_admin_forbids_normal_user(user):
    with pytest.raises(Exception) as exc:
        require_admin(user)
    assert getattr(exc.value, "status_code", None) == 403


def test_text_utils():
    from app.text_utils import extract_hashtags, extract_mentions

    assert extract_hashtags("hi #Python #python #fastapi!") == ["python", "fastapi"]
    assert extract_mentions("hello @Ali and @ali_99") == ["ali", "ali_99"]
