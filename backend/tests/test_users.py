"""Phase 1 Team B: user profile API tests."""

from app.models import User
from app.security import get_password_hash


def test_get_my_profile_returns_private_fields_only_to_owner(client, auth_headers):
    response = client.get("/api/v1/users/me", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "ali"
    assert body["email"] == "ali@chirp.local"
    assert "password_hash" not in body
    assert "role" not in body
    assert "is_active" not in body


def test_get_my_profile_requires_authentication(client):
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_get_public_profile_has_zero_count_stubs_and_no_private_fields(client, user):
    response = client.get("/api/v1/users/ALI")

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "ali"
    assert body["followers_count"] == 0
    assert body["following_count"] == 0
    assert body["posts_count"] == 0
    assert "email" not in body
    assert "password_hash" not in body
    assert "role" not in body


def test_get_public_profile_returns_404_for_unknown_user(client):
    response = client.get("/api/v1/users/missing")

    assert response.status_code == 404


def test_get_public_profile_hides_deactivated_user(client, db):
    db.add(
        User(
            username="inactive",
            email="inactive@chirp.local",
            password_hash=get_password_hash("password123"),
            display_name="Inactive",
            is_active=False,
        )
    )
    db.commit()

    response = client.get("/api/v1/users/inactive")

    assert response.status_code == 404


def test_patch_my_profile_updates_display_name_and_bio(client, auth_headers, user):
    response = client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json={"display_name": "  Ali Khan  ", "bio": "Python learner"},
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Ali Khan"
    assert response.json()["bio"] == "Python learner"
    assert user.display_name == "Ali Khan"
    assert user.bio == "Python learner"


def test_patch_my_profile_can_clear_bio(client, auth_headers, user):
    user.bio = "Existing bio"

    response = client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json={"bio": None},
    )

    assert response.status_code == 200
    assert response.json()["bio"] is None


def test_patch_my_profile_rejects_empty_patch(client, auth_headers):
    response = client.patch("/api/v1/users/me", headers=auth_headers, json={})

    assert response.status_code == 422


def test_patch_my_profile_rejects_invalid_values(client, auth_headers):
    for body in (
        {"display_name": "   "},
        {"display_name": None},
        {"display_name": "x" * 51},
        {"bio": "x" * 161},
    ):
        response = client.patch("/api/v1/users/me", headers=auth_headers, json=body)
        assert response.status_code == 422


def test_patch_my_profile_rejects_private_or_unowned_fields(client, auth_headers):
    response = client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json={"email": "attacker@chirp.local", "display_name": "Changed"},
    )

    assert response.status_code == 422


def test_patch_my_profile_requires_authentication(client):
    response = client.patch("/api/v1/users/me", json={"bio": "Not signed in"})

    assert response.status_code == 401
