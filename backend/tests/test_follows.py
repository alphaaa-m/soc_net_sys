"""Team A — Follow system tests (Phase 2). Uses the isolated SQLite test DB."""

from app import models
from app.security import create_access_token, get_password_hash
from app.services import follow_service

BASE = "/api/v1/users"

# One bcrypt hash reused by all test users keeps the suite fast.
PASSWORD_HASH = get_password_hash("password123")


def make_user(db, username: str, *, active: bool = True) -> models.User:
    user = models.User(
        username=username,
        email=f"{username}@chirp.local",
        password_hash=PASSWORD_HASH,
        display_name=username.title(),
        bio=None,
        role="user",
        is_active=active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def headers_for(user: models.User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def follow(client, headers: dict, user_id: int):
    return client.put(f"{BASE}/{user_id}/follow", headers=headers)


def unfollow(client, headers: dict, user_id: int):
    return client.delete(f"{BASE}/{user_id}/follow", headers=headers)


# --- follow ---


def test_follow_success(client, db, user, auth_headers):
    target = make_user(db, "bob")

    r = follow(client, auth_headers, target.id)

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["follower_id"] == user.id
    assert body["following_id"] == target.id
    assert db.get(models.Follow, (user.id, target.id)) is not None
    assert follow_service.count_followers(db, target.id) == 1
    assert follow_service.count_following(db, user.id) == 1


def test_follow_self_returns_400(client, user, auth_headers):
    r = follow(client, auth_headers, user.id)

    assert r.status_code == 400
    assert "yourself" in r.json()["detail"].lower()


def test_duplicate_follow_returns_409(client, db, user, auth_headers):
    target = make_user(db, "bob")
    assert follow(client, auth_headers, target.id).status_code == 201

    r = follow(client, auth_headers, target.id)

    assert r.status_code == 409
    assert follow_service.count_followers(db, target.id) == 1


def test_follow_missing_user_returns_404(client, auth_headers):
    r = follow(client, auth_headers, 10**9)

    assert r.status_code == 404
    assert r.json()["detail"] == "User not found."


def test_follow_deactivated_user_returns_404(client, db, auth_headers):
    target = make_user(db, "sleeping", active=False)

    r = follow(client, auth_headers, target.id)

    assert r.status_code == 404
    assert r.json()["detail"] == "User not found."


def test_follow_requires_authentication(client, db):
    target = make_user(db, "bob")

    r = follow(client, {}, target.id)

    assert r.status_code == 401


def test_deactivated_caller_cannot_follow(client, db, user):
    target = make_user(db, "bob")
    token = create_access_token(user.id)
    user.is_active = False
    db.add(user)
    db.commit()

    r = follow(client, {"Authorization": f"Bearer {token}"}, target.id)

    assert r.status_code == 403


def test_follow_invalid_user_id_returns_422(client, auth_headers):
    r = client.put(f"{BASE}/not-a-number/follow", headers=auth_headers)

    assert r.status_code == 422


# --- unfollow ---


def test_unfollow_success(client, db, user, auth_headers):
    target = make_user(db, "bob")
    assert follow(client, auth_headers, target.id).status_code == 201

    r = unfollow(client, auth_headers, target.id)

    assert r.status_code == 204
    assert db.get(models.Follow, (user.id, target.id)) is None
    assert follow_service.count_followers(db, target.id) == 0
    assert follow_service.count_following(db, user.id) == 0


def test_unfollow_when_not_following_returns_404(client, db, auth_headers):
    target = make_user(db, "bob")

    r = unfollow(client, auth_headers, target.id)

    assert r.status_code == 404
    assert r.json()["detail"] == "You are not following this user."


def test_unfollow_missing_user_returns_404(client, auth_headers):
    r = unfollow(client, auth_headers, 10**9)

    assert r.status_code == 404


def test_unfollow_requires_authentication(client, db):
    target = make_user(db, "bob")

    r = unfollow(client, {}, target.id)

    assert r.status_code == 401


def test_unfollow_allowed_for_deactivated_target(client, db, user, auth_headers):
    target = make_user(db, "bob")
    assert follow(client, auth_headers, target.id).status_code == 201
    target.is_active = False
    db.add(target)
    db.commit()

    r = unfollow(client, auth_headers, target.id)

    assert r.status_code == 204
    assert db.get(models.Follow, (user.id, target.id)) is None


# --- follower / following lists ---


def test_list_followers_is_public_and_paginated(client, db, user):
    bob = make_user(db, "bob")
    carol = make_user(db, "carol")
    assert follow(client, headers_for(bob), user.id).status_code == 201
    assert follow(client, headers_for(carol), user.id).status_code == 201

    r = client.get(f"{BASE}/ali/followers")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["total"] == 2
    assert {item["username"] for item in body["items"]} == {"bob", "carol"}
    # Public fields only: never leak private account data.
    assert "email" not in body["items"][0]
    assert "password_hash" not in body["items"][0]
    assert "role" not in body["items"][0]


def test_list_following_is_public(client, db, user):
    bob = make_user(db, "bob")
    carol = make_user(db, "carol")
    assert follow(client, headers_for(user), bob.id).status_code == 201
    assert follow(client, headers_for(user), carol.id).status_code == 201

    r = client.get(f"{BASE}/ali/following")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    assert {item["username"] for item in body["items"]} == {"bob", "carol"}


def test_followers_pagination_has_no_overlap(client, db, user):
    followers = [make_user(db, f"fan_{i}") for i in range(5)]
    for follower in followers:
        assert follow(client, headers_for(follower), user.id).status_code == 201

    page1 = client.get(f"{BASE}/ali/followers?limit=2&offset=0")
    page2 = client.get(f"{BASE}/ali/followers?limit=2&offset=2")

    assert page1.status_code == 200
    assert page2.status_code == 200
    first = page1.json()
    second = page2.json()
    assert first["total"] == second["total"] == 5
    assert len(first["items"]) == len(second["items"]) == 2
    ids1 = {item["id"] for item in first["items"]}
    ids2 = {item["id"] for item in second["items"]}
    assert ids1.isdisjoint(ids2)


def test_list_pagination_limit_is_capped_at_50(client, user):
    assert client.get(f"{BASE}/ali/followers?limit=51").status_code == 422
    assert client.get(f"{BASE}/ali/followers?limit=0").status_code == 422
    assert client.get(f"{BASE}/ali/followers?offset=-1").status_code == 422


def test_list_missing_user_returns_404(client):
    assert client.get(f"{BASE}/nobody/followers").status_code == 404
    assert client.get(f"{BASE}/nobody/following").status_code == 404


def test_list_deactivated_user_returns_404(client, db):
    make_user(db, "gone", active=False)

    assert client.get(f"{BASE}/gone/followers").status_code == 404
    assert client.get(f"{BASE}/gone/following").status_code == 404


def test_lists_hide_deactivated_accounts(client, db, user):
    bob = make_user(db, "bob")
    dave = make_user(db, "dave")
    assert follow(client, headers_for(bob), user.id).status_code == 201
    db.add(models.Follow(follower_id=dave.id, following_id=user.id))
    db.commit()
    dave.is_active = False
    db.add(dave)
    db.commit()

    r = client.get(f"{BASE}/ali/followers")

    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert [item["username"] for item in body["items"]] == ["bob"]
    assert follow_service.count_followers(db, user.id) == 1


def test_list_username_lookup_is_case_insensitive(client, db, user):
    bob = make_user(db, "bob")
    assert follow(client, headers_for(bob), user.id).status_code == 201

    r = client.get(f"{BASE}/ALI/followers")

    assert r.status_code == 200
    assert r.json()["total"] == 1


# --- count / wiring helpers ---


def test_count_helpers_and_is_following(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    carol = make_user(db, "carol")
    assert follow(client, auth_headers, bob.id).status_code == 201
    assert follow(client, headers_for(bob), user.id).status_code == 201
    assert follow(client, headers_for(carol), user.id).status_code == 201

    assert follow_service.count_following(db, user.id) == 1
    assert follow_service.count_followers(db, user.id) == 2
    assert follow_service.is_following(db, user.id, bob.id) is True
    assert follow_service.is_following(db, bob.id, user.id) is True
    assert follow_service.is_following(db, user.id, carol.id) is False
