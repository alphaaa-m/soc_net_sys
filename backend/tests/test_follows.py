"""Phase 2 — follow endpoints (PRD Part D, Part K).

Covers the five core PRD follow scenarios (self, duplicate, missing/deactivated
target, unfollow-not-following), the auth guard, lists/pagination and the
profile counts that read the same table.
"""

from app import models
from app.security import create_access_token, get_password_hash

FOLLOW = "/api/v1/users/{user_id}/follow"
FOLLOWERS = "/api/v1/users/{username}/followers"
FOLLOWING = "/api/v1/users/{username}/following"


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


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


# --------------------------------------------------------------------------- #
# Follow / unfollow
# --------------------------------------------------------------------------- #
def test_follow_creates_edge(client, db, user, auth_headers):
    sara = _make_user(db, "sara")
    r = client.put(FOLLOW.format(user_id=sara.id), headers=auth_headers)
    assert r.status_code == 201
    edge = (
        db.query(models.Follow)
        .filter_by(follower_id=user.id, following_id=sara.id)
        .one()
    )
    assert edge is not None


def test_follow_self_is_rejected(client, user, auth_headers):
    r = client.put(FOLLOW.format(user_id=user.id), headers=auth_headers)
    assert r.status_code == 400


def test_follow_unknown_user_is_404(client, auth_headers):
    assert client.put(FOLLOW.format(user_id=9999), headers=auth_headers).status_code == 404


def test_follow_deactivated_target_is_404(client, db, auth_headers):
    ghost = _make_user(db, "ghost", is_active=False)
    assert client.put(FOLLOW.format(user_id=ghost.id), headers=auth_headers).status_code == 404


def test_duplicate_follow_is_409(client, db, auth_headers):
    sara = _make_user(db, "sara")
    first = client.put(FOLLOW.format(user_id=sara.id), headers=auth_headers)
    second = client.put(FOLLOW.format(user_id=sara.id), headers=auth_headers)
    assert first.status_code == 201
    assert second.status_code == 409


def test_follow_requires_auth(client, db):
    sara = _make_user(db, "sara")
    assert client.put(FOLLOW.format(user_id=sara.id)).status_code == 401


def test_unfollow_removes_edge(client, db, user, auth_headers):
    sara = _make_user(db, "sara")
    client.put(FOLLOW.format(user_id=sara.id), headers=auth_headers)
    r = client.delete(FOLLOW.format(user_id=sara.id), headers=auth_headers)
    assert r.status_code == 204
    assert (
        db.query(models.Follow)
        .filter_by(follower_id=user.id, following_id=sara.id)
        .first()
        is None
    )


def test_unfollow_when_not_following_is_404(client, db, auth_headers):
    sara = _make_user(db, "sara")
    assert client.delete(FOLLOW.format(user_id=sara.id), headers=auth_headers).status_code == 404


def test_unfollow_requires_auth(client, db):
    sara = _make_user(db, "sara")
    assert client.delete(FOLLOW.format(user_id=sara.id)).status_code == 401


# --------------------------------------------------------------------------- #
# Lists
# --------------------------------------------------------------------------- #
def test_followers_list_with_pagination(client, db, user):
    sara = _make_user(db, "sara")
    bob = _make_user(db, "bob")
    db.add(models.Follow(follower_id=sara.id, following_id=user.id))
    db.add(models.Follow(follower_id=bob.id, following_id=user.id))
    db.commit()

    body = client.get(FOLLOWERS.format(username="ali")).json()
    assert body["total"] == 2
    assert {item["username"] for item in body["items"]} == {"sara", "bob"}

    page = client.get(FOLLOWERS.format(username="ali") + "?limit=1&offset=0").json()
    assert page["limit"] == 1
    assert len(page["items"]) == 1
    assert page["total"] == 2


def test_following_list(client, db, user, auth_headers):
    sara = _make_user(db, "sara")
    bob = _make_user(db, "bob")
    db.add(models.Follow(follower_id=user.id, following_id=sara.id))
    db.add(models.Follow(follower_id=user.id, following_id=bob.id))
    db.commit()

    body = client.get(FOLLOWING.format(username="ali"), headers=auth_headers).json()
    assert body["total"] == 2
    assert {item["username"] for item in body["items"]} == {"sara", "bob"}
    # Optional auth personalises each row: ali follows both listed users.
    assert all(item["is_following"] for item in body["items"])


def test_followers_list_unknown_user_is_404(client):
    assert client.get(FOLLOWERS.format(username="nobody")).status_code == 404


def test_followers_list_excludes_deactivated_follower(client, db, user):
    ghost = _make_user(db, "ghost", is_active=False)
    db.add(models.Follow(follower_id=ghost.id, following_id=user.id))
    db.commit()

    body = client.get(FOLLOWERS.format(username="ali")).json()
    assert body["total"] == 0
    assert body["items"] == []


# --------------------------------------------------------------------------- #
# Counts on the profile (same table, different module)
# --------------------------------------------------------------------------- #
def test_profile_counts_and_is_following_reflect_follows(client, db, user, auth_headers):
    sara = _make_user(db, "sara")
    db.add(models.Follow(follower_id=sara.id, following_id=user.id))
    db.commit()

    ali = client.get("/api/v1/users/ali").json()
    assert ali["followers_count"] == 1
    assert ali["following_count"] == 0

    sara_profile = client.get("/api/v1/users/sara", headers=auth_headers).json()
    assert sara_profile["followers_count"] == 0
    assert sara_profile["is_following"] is False

    client.put(FOLLOW.format(user_id=sara.id), headers=auth_headers)
    sara_profile = client.get("/api/v1/users/sara", headers=auth_headers).json()
    assert sara_profile["is_following"] is True
    assert sara_profile["followers_count"] == 1
