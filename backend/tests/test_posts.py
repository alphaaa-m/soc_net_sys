"""Phase 2 — post endpoints (PRD Part D, Part K).

Covers create/read/edit/soft-delete, ownership, validation, the personal-posts
list (newest first + pagination) and the two PRD edge cases: whitespace-only
content and posts whose author was deactivated.
"""

from app import models
from app.security import create_access_token, get_password_hash

POSTS = "/api/v1/posts"
USER_POSTS = "/api/v1/users/{username}/posts"


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


def _create(client, headers, content="Hello Chirp"):
    return client.post(POSTS, json={"content": content}, headers=headers)


# --------------------------------------------------------------------------- #
# Create
# --------------------------------------------------------------------------- #
def test_create_post_returns_author_and_stubbed_counts(client, auth_headers):
    r = _create(client, auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["content"] == "Hello Chirp"
    assert body["author"]["username"] == "ali"
    assert body["like_count"] == 0
    assert body["comment_count"] == 0
    assert body["share_count"] == 0
    assert body["liked_by_me"] is False
    assert body["bookmarked_by_me"] is False
    assert body["is_edited"] is False
    assert body["updated_at"] is None


def test_create_post_trims_content(client, auth_headers):
    body = _create(client, auth_headers, "  spaced  ").json()
    assert body["content"] == "spaced"


def test_create_post_rejects_blank_content(client, auth_headers):
    assert _create(client, auth_headers, "   ").status_code == 422


def test_create_post_rejects_oversized_content(client, auth_headers):
    assert _create(client, auth_headers, "x" * 281).status_code == 422


def test_create_post_accepts_exactly_280_chars(client, auth_headers):
    assert _create(client, auth_headers, "x" * 280).status_code == 201


def test_create_post_requires_auth(client):
    assert client.post(POSTS, json={"content": "hi"}).status_code == 401


# --------------------------------------------------------------------------- #
# Read
# --------------------------------------------------------------------------- #
def test_get_post(client, auth_headers):
    created = _create(client, auth_headers).json()
    r = client.get(f"{POSTS}/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_unknown_post_is_404(client):
    assert client.get(f"{POSTS}/9999").status_code == 404


def test_get_soft_deleted_post_is_404(client, auth_headers):
    post_id = _create(client, auth_headers).json()["id"]
    assert client.delete(f"{POSTS}/{post_id}", headers=auth_headers).status_code == 204
    assert client.get(f"{POSTS}/{post_id}").status_code == 404


def test_get_post_of_deactivated_author_is_404(client, db, auth_headers):
    sara = _make_user(db, "sara")
    post_id = _create(client, _headers(sara), "will vanish").json()["id"]
    sara.is_active = False
    db.commit()
    assert client.get(f"{POSTS}/{post_id}").status_code == 404


# --------------------------------------------------------------------------- #
# Update
# --------------------------------------------------------------------------- #
def test_update_own_post(client, auth_headers):
    post_id = _create(client, auth_headers, "original").json()["id"]
    r = client.patch(
        f"{POSTS}/{post_id}",
        json={"content": "edited"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["content"] == "edited"
    assert body["is_edited"] is True
    assert body["updated_at"] is not None


def test_update_someone_elses_post_is_403(client, db, auth_headers):
    sara = _make_user(db, "sara")
    post_id = _create(client, _headers(sara), "sara's post").json()["id"]
    r = client.patch(
        f"{POSTS}/{post_id}",
        json={"content": "hijacked"},
        headers=auth_headers,
    )
    assert r.status_code == 403


def test_update_unknown_post_is_404(client, auth_headers):
    r = client.patch(f"{POSTS}/9999", json={"content": "x"}, headers=auth_headers)
    assert r.status_code == 404


def test_update_soft_deleted_post_is_404(client, auth_headers):
    post_id = _create(client, auth_headers).json()["id"]
    client.delete(f"{POSTS}/{post_id}", headers=auth_headers)
    r = client.patch(
        f"{POSTS}/{post_id}",
        json={"content": "too late"},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_update_rejects_blank_content(client, auth_headers):
    post_id = _create(client, auth_headers).json()["id"]
    r = client.patch(
        f"{POSTS}/{post_id}",
        json={"content": "   "},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_update_requires_auth(client, auth_headers):
    post_id = _create(client, auth_headers).json()["id"]
    assert client.patch(f"{POSTS}/{post_id}", json={"content": "x"}).status_code == 401


# --------------------------------------------------------------------------- #
# Delete (soft)
# --------------------------------------------------------------------------- #
def test_delete_own_post_soft_deletes_row(client, db, auth_headers):
    post_id = _create(client, auth_headers).json()["id"]
    assert client.delete(f"{POSTS}/{post_id}", headers=auth_headers).status_code == 204

    row = db.get(models.Post, post_id)
    assert row is not None
    assert row.deleted_at is not None


def test_delete_someone_elses_post_is_403(client, db, auth_headers):
    sara = _make_user(db, "sara")
    post_id = _create(client, _headers(sara)).json()["id"]
    assert client.delete(f"{POSTS}/{post_id}", headers=auth_headers).status_code == 403


def test_delete_unknown_post_is_404(client, auth_headers):
    assert client.delete(f"{POSTS}/9999", headers=auth_headers).status_code == 404


def test_admin_can_delete_someone_elses_post(client, auth_headers, admin_headers):
    post_id = _create(client, auth_headers).json()["id"]
    assert client.delete(f"{POSTS}/{post_id}", headers=admin_headers).status_code == 204


# --------------------------------------------------------------------------- #
# Personal posts list
# --------------------------------------------------------------------------- #
def test_personal_posts_are_newest_first_and_paginated(client, auth_headers):
    ids = [_create(client, auth_headers, f"post {i}").json()["id"] for i in range(3)]

    body = client.get(USER_POSTS.format(username="ali")).json()
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == list(reversed(ids))

    page = client.get(USER_POSTS.format(username="ali") + "?limit=2&offset=0").json()
    assert page["limit"] == 2
    assert len(page["items"]) == 2
    assert page["total"] == 3


def test_personal_posts_exclude_soft_deleted(client, auth_headers):
    keep = _create(client, auth_headers, "keep").json()["id"]
    gone = _create(client, auth_headers, "gone").json()["id"]
    client.delete(f"{POSTS}/{gone}", headers=auth_headers)

    body = client.get(USER_POSTS.format(username="ali")).json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [keep]


def test_personal_posts_unknown_user_is_404(client):
    assert client.get(USER_POSTS.format(username="nobody")).status_code == 404


def test_personal_posts_of_deactivated_user_is_404(client, db):
    sara = _make_user(db, "sara", is_active=False)
    assert client.get(USER_POSTS.format(username=sara.username)).status_code == 404
