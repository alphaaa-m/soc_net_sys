"""Team A — Likes tests (Phase 3, PRD B7 + Part K).

Covers happy paths, duplicate/unlike errors, authentication, soft-deleted and
deactivated-author posts, the database composite primary key, and the bulk
count helpers (including a no-N+1 assertion).
"""

from contextlib import contextmanager

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from app import models
from app.security import create_access_token, get_password_hash
from app.services import like_service

POSTS = "/api/v1/posts"
LIKE = "/api/v1/posts/{post_id}/like"

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


def make_post(client, author: models.User, content: str = "Hello Chirp") -> int:
    r = client.post(POSTS, json={"content": content}, headers=headers_for(author))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def like(client, headers: dict, post_id: int):
    return client.post(LIKE.format(post_id=post_id), headers=headers)


def unlike(client, headers: dict, post_id: int):
    return client.delete(LIKE.format(post_id=post_id), headers=headers)


@contextmanager
def capture_statements(db):
    """Record SQL emitted on the test connection (for the N+1 assertion)."""
    statements: list[str] = []
    engine = db.get_bind()

    def listener(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", listener)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", listener)


# --- like ---


def test_like_success_returns_201(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)

    r = like(client, auth_headers, post_id)

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user_id"] == user.id
    assert body["post_id"] == post_id
    assert db.get(models.PostLike, (user.id, post_id)) is not None
    assert like_service.get_like_counts(db, [post_id]) == {post_id: 1}


def test_like_own_post_is_allowed(client, db, user, auth_headers):
    post_id = make_post(client, user)

    r = like(client, auth_headers, post_id)

    assert r.status_code == 201
    assert like_service.get_like_counts(db, [post_id]) == {post_id: 1}


def test_duplicate_like_returns_409(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)
    assert like(client, auth_headers, post_id).status_code == 201

    r = like(client, auth_headers, post_id)

    assert r.status_code == 409
    assert r.json()["detail"] == "You have already liked this post."
    assert db.query(models.PostLike).count() == 1
    assert like_service.get_like_counts(db, [post_id]) == {post_id: 1}


def test_two_users_can_like_the_same_post(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    carol = make_user(db, "carol")
    post_id = make_post(client, carol)

    assert like(client, auth_headers, post_id).status_code == 201
    assert like(client, headers_for(bob), post_id).status_code == 201

    assert like_service.get_like_counts(db, [post_id]) == {post_id: 2}


def test_like_unknown_post_returns_404(client, auth_headers):
    r = like(client, auth_headers, 10**9)

    assert r.status_code == 404
    assert r.json()["detail"] == "Post not found."


def test_like_soft_deleted_post_returns_404(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)
    assert client.delete(f"{POSTS}/{post_id}", headers=headers_for(bob)).status_code == 204

    r = like(client, auth_headers, post_id)

    assert r.status_code == 404
    assert db.get(models.PostLike, (user.id, post_id)) is None


def test_like_post_of_deactivated_author_returns_404(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)
    bob.is_active = False
    db.add(bob)
    db.commit()

    r = like(client, auth_headers, post_id)

    assert r.status_code == 404


def test_like_requires_authentication(client, db):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)

    assert client.post(LIKE.format(post_id=post_id)).status_code == 401


def test_like_invalid_post_id_returns_422(client, auth_headers):
    assert client.post("/api/v1/posts/not-a-number/like", headers=auth_headers).status_code == 422


# --- unlike ---


def test_unlike_success_returns_204_and_removes_row(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)
    assert like(client, auth_headers, post_id).status_code == 201

    r = unlike(client, auth_headers, post_id)

    assert r.status_code == 204
    assert r.content == b""
    assert db.get(models.PostLike, (user.id, post_id)) is None
    assert like_service.get_like_counts(db, [post_id]) == {post_id: 0}


def test_unlike_when_not_liked_returns_404(client, db, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)

    r = unlike(client, auth_headers, post_id)

    assert r.status_code == 404
    assert r.json()["detail"] == "You have not liked this post."


def test_unlike_unknown_post_returns_404(client, auth_headers):
    r = unlike(client, auth_headers, 10**9)

    assert r.status_code == 404
    assert r.json()["detail"] == "Post not found."


def test_unlike_soft_deleted_post_returns_404(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)
    assert like(client, auth_headers, post_id).status_code == 201
    assert client.delete(f"{POSTS}/{post_id}", headers=headers_for(bob)).status_code == 204

    r = unlike(client, auth_headers, post_id)

    assert r.status_code == 404
    # Hiding a post does not silently delete interaction history.
    assert db.get(models.PostLike, (user.id, post_id)) is not None


def test_unlike_requires_authentication(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)
    assert like(client, auth_headers, post_id).status_code == 201

    assert client.delete(LIKE.format(post_id=post_id)).status_code == 401


# --- database constraints ---


def test_composite_primary_key_rejects_duplicate_like(db, user):
    bob = make_user(db, "bob")
    post = models.Post(author_id=bob.id, content="constraint check")
    db.add(post)
    db.commit()

    db.add(models.PostLike(user_id=user.id, post_id=post.id))
    db.commit()

    db.add(models.PostLike(user_id=user.id, post_id=post.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    assert db.query(models.PostLike).count() == 1


# --- bulk helpers ---


def test_get_like_counts_returns_zero_for_posts_without_likes(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    liked = make_post(client, bob, "liked")
    unliked = make_post(client, bob, "unliked")
    assert like(client, auth_headers, liked).status_code == 201

    counts = like_service.get_like_counts(db, [liked, unliked])

    assert counts == {liked: 1, unliked: 0}


def test_get_like_counts_uses_one_grouped_query(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    carol = make_user(db, "carol")
    first = make_post(client, bob, "first")
    second = make_post(client, carol, "second")
    assert like(client, auth_headers, first).status_code == 201
    assert like(client, headers_for(bob), second).status_code == 201

    with capture_statements(db) as statements:
        counts = like_service.get_like_counts(db, [first, second])

    assert counts == {first: 1, second: 1}
    selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
    assert len(selects) == 1
    assert "GROUP BY" in selects[0].upper()


def test_liked_post_ids_helper(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    liked = make_post(client, bob)
    other = make_post(client, bob)
    assert like(client, auth_headers, liked).status_code == 201

    assert like_service.liked_post_ids(db, user.id, [liked, other]) == {liked}
    assert like_service.liked_post_ids(db, bob.id, [liked, other]) == set()


def test_count_helpers_accept_empty_input(db):
    assert like_service.get_like_counts(db, []) == {}
    assert like_service.liked_post_ids(db, 1, []) == set()
