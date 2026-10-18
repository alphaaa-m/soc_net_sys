"""Phase 1 — user profile endpoints (PRD B2, Part K)."""

from datetime import UTC, datetime

from app import models
from app.security import get_password_hash


def _make_user(db, username, *, is_active=True):
    user = models.User(
        username=username,
        email=f"{username}@chirp.local",
        password_hash=get_password_hash("password123"),
        display_name=username.title(),
        role="user",
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------- #
# GET /users/me
# --------------------------------------------------------------------------- #
def test_get_me_requires_token(client):
    assert client.get("/api/v1/users/me").status_code == 401


def test_get_me_returns_private_fields(client, user, auth_headers):
    r = client.get("/api/v1/users/me", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "ali"
    assert body["email"] == "ali@chirp.local"
    assert body["role"] == "user"
    assert body["is_active"] is True
    assert "password_hash" not in body


# --------------------------------------------------------------------------- #
# PATCH /users/me
# --------------------------------------------------------------------------- #
def test_patch_me_updates_display_name_and_bio(client, auth_headers):
    r = client.patch(
        "/api/v1/users/me",
        json={"display_name": "Ali Updated", "bio": "Hi there"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["display_name"] == "Ali Updated"
    assert body["bio"] == "Hi there"


def test_patch_me_is_partial(client, user, auth_headers):
    r = client.patch("/api/v1/users/me", json={"bio": "only bio"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["bio"] == "only bio"
    assert r.json()["display_name"] == user.display_name


def test_patch_me_cannot_change_username_or_email(client, user, auth_headers):
    r = client.patch(
        "/api/v1/users/me",
        json={"username": "hacker", "email": "hacker@evil.com"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["username"] == "ali"
    assert r.json()["email"] == "ali@chirp.local"


def test_patch_me_rejects_long_bio(client, auth_headers):
    r = client.patch("/api/v1/users/me", json={"bio": "x" * 161}, headers=auth_headers)
    assert r.status_code == 422


def test_patch_me_rejects_blank_display_name(client, auth_headers):
    r = client.patch("/api/v1/users/me", json={"display_name": ""}, headers=auth_headers)
    assert r.status_code == 422


def test_patch_me_requires_token(client):
    assert client.patch("/api/v1/users/me", json={"bio": "x"}).status_code == 401


# --------------------------------------------------------------------------- #
# GET /users/{username}
# --------------------------------------------------------------------------- #
def test_get_public_profile_hides_private_fields(client, user):
    r = client.get("/api/v1/users/ali")
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "ali"
    assert body["is_following"] is False
    assert "email" not in body
    assert "password_hash" not in body
    assert "role" not in body


def test_get_public_profile_is_case_insensitive(client, user):
    assert client.get("/api/v1/users/ALI").status_code == 200


def test_get_public_profile_not_found(client):
    assert client.get("/api/v1/users/nobody").status_code == 404


def test_get_public_profile_hides_deactivated(client, db):
    _make_user(db, "ghost", is_active=False)
    assert client.get("/api/v1/users/ghost").status_code == 404


def test_is_following_true_when_logged_in_and_following(client, db, user, auth_headers):
    other = _make_user(db, "sara")
    db.add(models.Follow(follower_id=user.id, following_id=other.id))
    db.commit()

    r = client.get("/api/v1/users/sara", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["is_following"] is True


def test_profile_counts_reflect_rows_and_ignore_deleted_posts(client, db, user):
    other = _make_user(db, "sara")
    db.add(models.Follow(follower_id=user.id, following_id=other.id))  # ali follows sara
    db.add(models.Follow(follower_id=other.id, following_id=user.id))  # sara follows ali
    db.add(models.Post(author_id=user.id, content="visible"))
    db.add(
        models.Post(
            author_id=user.id,
            content="deleted",
            deleted_at=datetime.now(UTC),
        )
    )
    db.commit()

    body = client.get("/api/v1/users/ali").json()
    assert body["followers_count"] == 1
    assert body["following_count"] == 1
    assert body["posts_count"] == 1  # the soft-deleted post is excluded
