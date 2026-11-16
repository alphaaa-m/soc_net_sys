"""Wiring PR (Phase 3 Team A) — interaction fields on ``PostRead``.

Verifies that ``like_count``, ``share_count`` and ``liked_by_me`` are plugged
into the existing post responses without N+1 queries. ``comment_count`` stays
at its Phase 2 stub because that belongs to Team B's wiring PR.
"""

from contextlib import contextmanager

from sqlalchemy import event

from app import models
from app.security import create_access_token, get_password_hash

POSTS = "/api/v1/posts"
USER_POSTS = "/api/v1/users/{username}/posts"

PASSWORD_HASH = get_password_hash("password123")


def make_user(db, username: str) -> models.User:
    user = models.User(
        username=username,
        email=f"{username}@chirp.local",
        password_hash=PASSWORD_HASH,
        display_name=username.title(),
        bio=None,
        role="user",
        is_active=True,
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


@contextmanager
def capture_statements(db):
    statements: list[str] = []
    engine = db.get_bind()

    def listener(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", listener)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", listener)


def test_get_post_exposes_interaction_fields(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    carol = make_user(db, "carol")
    post_id = make_post(client, bob)

    assert client.post(f"{POSTS}/{post_id}/like", headers=auth_headers).status_code == 201
    assert client.post(f"{POSTS}/{post_id}/repost", headers=headers_for(carol)).status_code == 201

    body = client.get(f"{POSTS}/{post_id}", headers=auth_headers).json()

    assert body["like_count"] == 1
    assert body["share_count"] == 1
    assert body["liked_by_me"] is True
    assert body["comment_count"] == 0  # Team B's wiring PR


def test_get_post_anonymous_sees_counts_without_personal_flag(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)
    assert client.post(f"{POSTS}/{post_id}/like", headers=auth_headers).status_code == 201

    body = client.get(f"{POSTS}/{post_id}").json()

    assert body["like_count"] == 1
    assert body["share_count"] == 0
    assert body["liked_by_me"] is False


def test_liked_by_me_is_viewer_specific(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    post_id = make_post(client, bob)
    assert client.post(f"{POSTS}/{post_id}/like", headers=auth_headers).status_code == 201

    as_bob = client.get(f"{POSTS}/{post_id}", headers=headers_for(bob)).json()

    assert as_bob["like_count"] == 1
    assert as_bob["liked_by_me"] is False


def test_personal_post_list_has_per_post_counts(client, db, user, auth_headers):
    bob = make_user(db, "bob")
    carol = make_user(db, "carol")
    first = make_post(client, bob, "first")
    second = make_post(client, bob, "second")

    assert client.post(f"{POSTS}/{first}/like", headers=auth_headers).status_code == 201
    assert client.post(f"{POSTS}/{first}/like", headers=headers_for(carol)).status_code == 201
    assert client.post(f"{POSTS}/{second}/repost", headers=headers_for(carol)).status_code == 201

    body = client.get(
        USER_POSTS.format(username="bob"),
        headers=headers_for(carol),
    ).json()
    by_id = {item["id"]: item for item in body["items"]}

    assert by_id[first]["like_count"] == 2
    assert by_id[first]["share_count"] == 0
    assert by_id[first]["liked_by_me"] is True
    assert by_id[second]["like_count"] == 0
    assert by_id[second]["share_count"] == 1
    assert by_id[second]["liked_by_me"] is False


def test_personal_post_list_query_count_does_not_grow_with_page_size(client, db, auth_headers):
    bob = make_user(db, "bob")
    for index in range(5):
        make_post(client, bob, f"post {index}")

    def select_count() -> int:
        with capture_statements(db) as statements:
            r = client.get(USER_POSTS.format(username="bob"), headers=auth_headers)
        assert r.status_code == 200, r.text
        return len([s for s in statements if s.lstrip().upper().startswith("SELECT")])

    # Warm the current-user lookup so the first measured request does not
    # include an extra SELECT that later requests skip via the session cache.
    assert client.get(USER_POSTS.format(username="bob"), headers=auth_headers).status_code == 200

    five_posts = select_count()

    # A page of one post uses the same number of SELECTs as a page of five:
    # base count + page + one grouped query per interaction type + liked ids.
    with capture_statements(db) as statements:
        r = client.get(USER_POSTS.format(username="bob") + "?limit=1", headers=auth_headers)
    assert r.status_code == 200
    one_post = len([s for s in statements if s.lstrip().upper().startswith("SELECT")])

    assert five_posts == one_post
