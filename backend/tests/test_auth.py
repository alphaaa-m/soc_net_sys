"""Phase 1 — authentication endpoints (PRD B1, Part K).

Covers register / login / logout / change-password / deactivate: happy paths
plus the failure paths a reviewer will ask about (duplicates, bad credentials,
deactivated accounts, validation).
"""

from app import models
from app.security import get_password_hash, verify_password

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
PASSWORD = "/api/v1/auth/password"
DEACTIVATE = "/api/v1/auth/deactivate"


def _register(client, **overrides):
    payload = {
        "email": "new@chirp.local",
        "username": "newuser",
        "password": "password123",
        "display_name": "New User",
    }
    payload.update(overrides)
    return client.post(REGISTER, json=payload)


def _make_inactive(db, username="ghost"):
    user = models.User(
        username=username,
        email=f"{username}@chirp.local",
        password_hash=get_password_hash("password123"),
        display_name=username.title(),
        role="user",
        is_active=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------- #
# Register
# --------------------------------------------------------------------------- #
def test_register_success_stores_hash_and_hides_it(client, db):
    r = _register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "newuser"
    assert body["email"] == "new@chirp.local"
    assert body["role"] == "user"
    assert body["is_active"] is True
    assert "password" not in body
    assert "password_hash" not in body

    stored = db.query(models.User).filter_by(username="newuser").one()
    assert stored.password_hash != "password123"
    assert verify_password("password123", stored.password_hash)


def test_register_normalises_email_and_username(client):
    r = _register(client, email="Mixed@Case.COM", username="MixedCase")
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "mixed@case.com"
    assert body["username"] == "mixedcase"


def test_register_duplicate_email(client, user):
    r = _register(client, email="ali@chirp.local", username="someoneelse")
    assert r.status_code == 409


def test_register_duplicate_username(client, user):
    r = _register(client, email="someoneelse@chirp.local", username="ali")
    assert r.status_code == 409


def test_register_invalid_email(client):
    assert _register(client, email="not-an-email").status_code == 422


def test_register_short_password(client):
    assert _register(client, password="short").status_code == 422


def test_register_bad_username(client):
    assert _register(client, username="ab").status_code == 422
    assert _register(client, username="bad-name").status_code == 422


def test_register_blank_display_name(client):
    assert _register(client, display_name="   ").status_code == 422


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #
def test_login_with_username(client, user):
    r = client.post(LOGIN, json={"identifier": "ali", "password": "password123"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_with_email(client, user):
    r = client.post(LOGIN, json={"identifier": "ali@chirp.local", "password": "password123"})
    assert r.status_code == 200


def test_login_identifier_is_case_insensitive(client, user):
    r = client.post(LOGIN, json={"identifier": "ALI", "password": "password123"})
    assert r.status_code == 200


def test_login_wrong_password(client, user):
    r = client.post(LOGIN, json={"identifier": "ali", "password": "wrongpassword"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post(LOGIN, json={"identifier": "nobody", "password": "password123"})
    assert r.status_code == 401


def test_login_deactivated_account(client, db):
    _make_inactive(db)
    r = client.post(LOGIN, json={"identifier": "ghost", "password": "password123"})
    assert r.status_code == 403


# --------------------------------------------------------------------------- #
# Logout
# --------------------------------------------------------------------------- #
def test_logout_requires_token(client):
    assert client.post(LOGOUT).status_code == 401


def test_logout_returns_no_content(client, auth_headers):
    assert client.post(LOGOUT, headers=auth_headers).status_code == 204


# --------------------------------------------------------------------------- #
# Change password
# --------------------------------------------------------------------------- #
def test_change_password_then_login_with_new_one(client, user, auth_headers):
    r = client.put(
        PASSWORD,
        json={"current_password": "password123", "new_password": "newpassword456"},
        headers=auth_headers,
    )
    assert r.status_code == 204
    new_login = client.post(LOGIN, json={"identifier": "ali", "password": "newpassword456"})
    old_login = client.post(LOGIN, json={"identifier": "ali", "password": "password123"})
    assert new_login.status_code == 200
    assert old_login.status_code == 401


def test_change_password_wrong_current(client, auth_headers):
    r = client.put(
        PASSWORD,
        json={"current_password": "notmypassword", "new_password": "newpassword456"},
        headers=auth_headers,
    )
    assert r.status_code == 401


def test_change_password_same_as_current(client, auth_headers):
    r = client.put(
        PASSWORD,
        json={"current_password": "password123", "new_password": "password123"},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_change_password_too_short(client, auth_headers):
    r = client.put(
        PASSWORD,
        json={"current_password": "password123", "new_password": "short"},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_change_password_requires_token(client):
    r = client.put(
        PASSWORD,
        json={"current_password": "password123", "new_password": "newpassword456"},
    )
    assert r.status_code == 401


# --------------------------------------------------------------------------- #
# Deactivate
# --------------------------------------------------------------------------- #
def test_deactivate_account_blocks_login_and_token(client, user, auth_headers):
    r = client.post(DEACTIVATE, json={"password": "password123"}, headers=auth_headers)
    assert r.status_code == 204
    # Cannot log in again (PRD B1).
    relogin = client.post(LOGIN, json={"identifier": "ali", "password": "password123"})
    assert relogin.status_code == 403
    # An already-issued token is now rejected too.
    assert client.get("/api/v1/users/me", headers=auth_headers).status_code == 403


def test_deactivate_wrong_password(client, auth_headers):
    r = client.post(DEACTIVATE, json={"password": "nope"}, headers=auth_headers)
    assert r.status_code == 401


def test_deactivate_requires_token(client):
    assert client.post(DEACTIVATE, json={"password": "password123"}).status_code == 401
