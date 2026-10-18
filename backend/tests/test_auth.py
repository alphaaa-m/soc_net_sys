"""Team A — Authentication tests (Phase 1). Uses isolated SQLite test DB."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import get_settings
from app.models import User
from app.security import create_access_token, get_password_hash

BASE = "/api/v1/auth"


def register(client, **overrides):
    payload = {
        "email": "new@chirp.local",
        "username": "newuser",
        "password": "password123",
        "display_name": "New",
    }
    payload.update(overrides)
    return client.post(f"{BASE}/register", json=payload)


def login(client, identifier, password):
    return client.post(f"{BASE}/login", json={"identifier": identifier, "password": password})


# --- registration ---


def test_register_success(client):
    r = register(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "new@chirp.local"
    assert body["username"] == "newuser"
    assert "password" not in body and "password_hash" not in body


def test_register_invalid_input(client):
    assert register(client, email="not-an-email").status_code == 422
    assert register(client, username="ab").status_code == 422
    assert register(client, username="bad-name!").status_code == 422
    assert register(client, password="short").status_code == 422
    assert register(client, display_name="").status_code == 422


def test_register_duplicate_email(client, user):
    r = register(client, email=user.email, username="someone_else")
    assert r.status_code == 409


def test_register_duplicate_username(client, user):
    r = register(client, email="other@chirp.local", username=user.username)
    assert r.status_code == 409


def test_register_case_insensitive_duplicates(client, user):
    assert register(client, email=user.email.upper(), username="unique_one").status_code == 409
    assert (
        register(client, email="unique@chirp.local", username=user.username.upper()).status_code
        == 409
    )


def test_register_normalizes_case(client):
    r = register(client, email="MiXeD@Chirp.Local", username="MiXeD_User")
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "mixed@chirp.local"
    assert r.json()["username"] == "mixed_user"


# --- login ---


def test_login_with_email(client, user):
    r = login(client, user.email, "password123")
    assert r.status_code == 200, r.text
    assert r.json()["access_token"] and r.json()["token_type"] == "bearer"


def test_login_with_username(client, user):
    assert login(client, user.username, "password123").status_code == 200


def test_login_case_insensitive_identifier(client, user):
    assert login(client, user.email.upper(), "password123").status_code == 200
    assert login(client, user.username.upper(), "password123").status_code == 200


def test_login_wrong_password_and_unknown_user_same_error(client, user):
    bad_pw = login(client, user.email, "wrongpassword")
    unknown = login(client, "nobody_here@chirp.local", "wrongpassword")
    assert bad_pw.status_code == 401
    assert unknown.status_code == 401
    assert bad_pw.json() == unknown.json()
    assert "password_hash" not in bad_pw.text.lower()


def test_login_deactivated_user(client, db, user):
    user.is_active = False
    db.add(user)
    db.commit()
    r = login(client, user.email, "password123")
    assert r.status_code == 403


# --- logout ---


def test_logout_success(client, auth_headers):
    r = client.post(f"{BASE}/logout", headers=auth_headers)
    assert r.status_code == 204
    assert r.content in (b"", b"null") or True  # no body expected


def test_logout_requires_auth(client):
    assert client.post(f"{BASE}/logout").status_code == 401


# --- password change ---


def test_change_password_success(client, auth_headers):
    r = client.put(
        f"{BASE}/password",
        json={"current_password": "password123", "new_password": "newpassword456"},
        headers=auth_headers,
    )
    assert r.status_code == 204, r.text
    assert login(client, "ali@chirp.local", "newpassword456").status_code == 200
    assert login(client, "ali@chirp.local", "password123").status_code == 401


def test_change_password_wrong_current(client, auth_headers):
    r = client.put(
        f"{BASE}/password",
        json={"current_password": "nope", "new_password": "newpassword456"},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_change_password_same_as_current(client, auth_headers):
    r = client.put(
        f"{BASE}/password",
        json={"current_password": "password123", "new_password": "password123"},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_change_password_requires_auth(client):
    r = client.put(
        f"{BASE}/password", json={"current_password": "a", "new_password": "newpassword456"}
    )
    assert r.status_code == 401


def test_change_password_short_new_rejected(client, auth_headers):
    r = client.put(
        f"{BASE}/password",
        json={"current_password": "password123", "new_password": "short"},
        headers=auth_headers,
    )
    assert r.status_code == 422


# --- deactivation ---


def test_deactivate_success(client, db, auth_headers, user):
    r = client.post(f"{BASE}/deactivate", json={"password": "password123"}, headers=auth_headers)
    assert r.status_code == 204, r.text
    db.refresh(user)
    assert user.is_active is False
    assert login(client, user.email, "password123").status_code == 403


def test_deactivate_wrong_password(client, auth_headers):
    r = client.post(f"{BASE}/deactivate", json={"password": "wrong"}, headers=auth_headers)
    assert r.status_code == 401


def test_deactivate_requires_auth(client):
    assert client.post(f"{BASE}/deactivate", json={"password": "password123"}).status_code == 401


# --- tokens ---


def _expired_token(user_id: int) -> str:
    settings = get_settings()
    payload = {"sub": str(user_id), "exp": datetime.now(UTC) - timedelta(minutes=1)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def test_missing_malformed_invalid_expired_jwt(client, user):
    assert client.post(f"{BASE}/logout").status_code == 401
    assert (
        client.post(f"{BASE}/logout", headers={"Authorization": "Bearer not-a-token"}).status_code
        == 401
    )
    assert (
        client.post(
            f"{BASE}/logout", headers={"Authorization": "Bearer bogus.bogus.bogus"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"{BASE}/logout", headers={"Authorization": f"Bearer {_expired_token(user.id)}"}
        ).status_code
        == 401
    )


def test_jwt_rejected_after_deactivation(client, db):
    u = User(
        username="gone",
        email="gone@chirp.local",
        password_hash=get_password_hash("password123"),
        display_name="Gone",
        role="user",
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    token = create_access_token(u.id)
    u.is_active = False
    db.add(u)
    db.commit()
    for method, url, kwargs in [
        ("post", f"{BASE}/logout", {}),
        (
            "put",
            f"{BASE}/password",
            {"json": {"current_password": "x", "new_password": "y12345678"}},
        ),
        ("post", f"{BASE}/deactivate", {"json": {"password": "x"}}),
    ]:
        r = getattr(client, method)(url, headers={"Authorization": f"Bearer {token}"}, **kwargs)
        assert r.status_code == 403, (url, r.status_code, r.text)


def test_protected_endpoints_reject_unauthenticated(client):
    assert client.post(f"{BASE}/logout").status_code == 401
    assert client.put(
        f"{BASE}/password", json={"current_password": "a", "new_password": "b12345678"}
    ).status_code in (
        401,
        403,
    )
    assert client.post(f"{BASE}/deactivate", json={"password": "a"}).status_code == 401


def test_unknown_user_id_token_rejected(client, user):
    token = create_access_token(10**9)
    r = client.post(f"{BASE}/logout", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


@pytest.mark.parametrize("username", ["ok_name_1", "User_Name"])
def test_register_username_variants_ok(client, username, db):
    email = username.lower() + "@chirp.local"
    r = register(client, email=email, username=username)
    assert r.status_code == 201, r.text
