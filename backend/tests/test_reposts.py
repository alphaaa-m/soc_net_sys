"""Team A — Reposts tests (Phase 3, PRD B8 + Part K).

Covers repost/unrepost happy paths, self-repost, duplicates, quote-text
validation, soft-deleted/deactivated-author posts, the UNIQUE constraint, and
the bulk share-count helper (including a no-N+1 assertion).
"""

from contextlib import contextmanager

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from app import models
from app.security import create_access_token, get_password_hash
from app.services import repost_service

POSTS = "/api/v1/posts"
REPOST = "/api/v1/posts/{post_id}/repost"

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


def repost(client, headers: dict, post_id: int, body: dict | None = None):
    kwargs = {"headers": headers}
    if body is not None:
        kwargs["json"] = body
    return client.post(REPOST.format(post_id=post_id), **kwargs)


def unrepost(client, headers: dict, post_id: int):
    return client.delete(REPOST.format(post_id=post_id), headers=headers)


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


# --- repost ---


def test_repost_success_returns_201(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob, "repost me")

    r = repost(client, auth_headers, post_id, {"quote_text": "Worth reading"})

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user_id"] == user.id
    assert body["original_post_id"] == post_id
    assert body["quote_text"] == "Worth reading"
    assert db.get(models.Repost, body["id"]) is not None
    assert repost_service.get_repost_counts(db, [post_id]) == {post_id: 1}


def test_repost_without_body_is_allowed(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)

    r = repost(client, auth_headers, post_id)

    assert r.status_code == 201, r.text
    assert r.json()["quote_text"] is None


def test_repost_with_empty_body_is_allowed(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)

    r = repost(client, auth_headers, post_id, {})

    assert r.status_code == 201
    assert r.json()["quote_text"] is None


def test_repost_trims_and_blank_quote_becomes_none(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)

    trimmed = repost(client, auth_headers, post_id, {"quote_text": "  spaced  "})
    assert trimmed.status_code == 201
    assert trimmed.json()["quote_text"] == "spaced"

    other = make_post(client, bob, "another")
    blank = repost(client, auth_headers, other, {"quote_text": "   "})
    assert blank.status_code == 201
    assert blank.json()["quote_text"] is None


def test_repost_accepts_quote_of_exactly_280_chars(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)

    r = repost(client, auth_headers, post_id, {"quote_text": "x" * 280})

    assert r.status_code == 201
    assert len(r.json()["quote_text"]) == 280


def test_repost_rejects_quote_over_280_chars(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)

    r = repost(client, auth_headers, post_id, {"quote_text": "x" * 281})

    assert r.status_code == 422


def test_duplicate_repost_returns_409(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)
    assert repost(client, auth_headers, post_id).status_code == 201

    r = repost(client, auth_headers, post_id, {"quote_text": "again"})

    assert r.status_code == 409
    assert r.json()["detail"] == "You have already reposted this post."
    assert db.query(models.Repost).count() == 1
    assert repost_service.get_repost_counts(db, [post_id]) == {post_id: 1}


def test_self_repost_is_rejected(client, db, user, auth_headers):
    post_id = make_post(client, user)

    r = repost(client, auth_headers, post_id)

    assert r.status_code == 403
    assert r.json()["detail"] == "You cannot repost your own post."
    assert db.query(models.Repost).count() == 0


def test_repost_unknown_post_returns_404(client, auth_headers):
    r = repost(client, auth_headers, 10**9)

    assert r.status_code == 404
    assert r.json()["detail"] == "Post not found."


def test_repost_soft_deleted_post_returns_404(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)
    assert client.delete(f"{POSTS}/{post_id}", headers=headers_for(bob)).status_code == 204

    r = repost(client, auth_headers, post_id)

    assert r.status_code == 404
    assert db.query(models.Repost).count() == 0


def test_repost_post_of_deactivated_author_returns_404(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)
    bob.is_active = False
    db.add(bob)
    db.commit()

    assert repost(client, auth_headers, post_id).status_code == 404


def test_two_users_can_repost_the_same_post(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    carol = make_user(db, "carol")
    post_id = make_post(client, carol)

    assert repost(client, auth_headers, post_id).status_code == 201
    assert repost(client, headers_for(bob), post_id).status_code == 201

    assert repost_service.get_repost_counts(db, [post_id]) == {post_id: 2}


def test_repost_requires_authentication(client, db):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)

    assert client.post(REPOST.format(post_id=post_id)).status_code == 401


def test_repost_invalid_post_id_returns_422(client, auth_headers):
    assert client.post("/api/v1/posts/not-a-number/repost", headers=auth_headers).status_code == 422


# --- unrepost ---


def test_unrepost_success_returns_204_and_removes_row(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)
    assert repost(client, auth_headers, post_id).status_code == 201

    r = unrepost(client, auth_headers, post_id)

    assert r.status_code == 204
    assert r.content == b""
    assert (
        db.query(models.Repost)
        .filter(
            models.Repost.user_id == user.id,
            models.Repost.original_post_id == post_id,
        )
        .first()
        is None
    )
    assert repost_service.get_repost_counts(db, [post_id]) == {post_id: 0}


def test_unrepost_when_not_reposted_returns_404(client, db, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)

    r = unrepost(client, auth_headers, post_id)

    assert r.status_code == 404
    assert r.json()["detail"] == "You have not reposted this post."


def test_unrepost_works_after_original_is_soft_deleted(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)
    assert repost(client, auth_headers, post_id).status_code == 201
    assert client.delete(f"{POSTS}/{post_id}", headers=headers_for(bob)).status_code == 204

    r = unrepost(client, auth_headers, post_id)

    assert r.status_code == 204
    assert db.query(models.Repost).count() == 0


def test_unrepost_requires_authentication(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)
    assert repost(client, auth_headers, post_id).status_code == 201

    assert client.delete(REPOST.format(post_id=post_id)).status_code == 401


# --- database constraints ---


def test_unique_constraint_rejects_duplicate_repost(db, user):
    bob = make_user(db, "bob")
    post = models.Post(author_id=bob.id, content="constraint check")
    db.add(post)
    db.commit()

    db.add(models.Repost(user_id=user.id, original_post_id=post.id))
    db.commit()

    db.add(models.Repost(user_id=user.id, original_post_id=post.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    assert db.query(models.Repost).count() == 1


# --- bulk helpers ---


def test_get_repost_counts_returns_zero_for_unreposted_posts(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    reposted = make_post(client, bob, "reposted")
    untouched = make_post(client, bob, "untouched")
    assert repost(client, auth_headers, reposted).status_code == 201

    counts = repost_service.get_repost_counts(db, [reposted, untouched])

    assert counts == {reposted: 1, untouched: 0}


def test_get_repost_counts_uses_one_grouped_query(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    carol = make_user(db, "carol")
    first = make_post(client, bob, "first")
    second = make_post(client, carol, "second")
    assert repost(client, auth_headers, first).status_code == 201
    assert repost(client, headers_for(bob), second).status_code == 201

    with capture_statements(db) as statements:
        counts = repost_service.get_repost_counts(db, [first, second])

    assert counts == {first: 1, second: 1}
    selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
    assert len(selects) == 1
    assert "GROUP BY" in selects[0].upper()


def test_get_repost_counts_accepts_empty_input(db):
    assert repost_service.get_repost_counts(db, []) == {}
