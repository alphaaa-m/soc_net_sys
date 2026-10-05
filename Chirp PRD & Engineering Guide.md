# Chirp — Product Requirements Document & Engineering Guide

*A text-only social network, built by students as a team software engineering project.*

**Audience:** student backend developers, mentor/instructor (frontend + code review) **Stack:** Python · FastAPI · SQLAlchemy · Pydantic · Alembic · PostgreSQL · JWT · pytest · Next.js

> **How to read this document.** Parts A–D define *what* we build. Parts E–F define *how the code and team are organised*. Parts G–J define *how we work together*. The rest is testing, security, exercises, and roadmap. Questions marked 🤔 are meant to be discussed **before** coding. Some have guidance; others you must discuss with your mentor.

---

# PART A — PRODUCT OVERVIEW

## Product Name

**Chirp** (temporary working name). Rename later if the team agrees.

## Product Vision

Chirp is a text-only social network where people create short posts, follow each other, discuss in comments, and discover content through hashtags, mentions, and search.

## Project Purpose

1. **Application purpose:** a working social network with a REST API consumed by a Next.js frontend.
2. **Educational purpose:** students learn how real software is made: designing databases and APIs, splitting work, using Git/GitHub in a team, reviewing code, testing, and handling bugs. **The process matters more than the app.**

## Target Users

| User type | Description | Main needs |
| --- | --- | --- |
| Regular user | Student or learner who posts and follows others | Post, follow, read feed, interact |
| Moderator-minded user | Reports abusive content | Report, block |
| Admin | Staff member | Review reports, deactivate users, remove content |

## Core User Journey

```mermaid
flowchart LR
    A[Register] --> B[Login]
    B --> C[Complete Profile]
    C --> D[Follow Users]
    D --> E[Create Posts]
    E --> F[View Feed]
    F --> G[Like and Comment]
    G --> H[Receive Notifications]
    H --> F
```

## Key Terms (explained once)

- **API (Application Programming Interface):** a set of URLs the frontend calls to ask the backend to do things.
- **REST:** an API style where URLs name *things* (`/posts/5`) and HTTP methods name *actions* (GET = read, POST = create, PATCH = update, DELETE = remove).
- **Endpoint:** one URL + method combination, e.g. `POST /posts`.
- **JSON:** the text format used to send data between frontend and backend.
- **ORM (Object-Relational Mapper):** a library (SQLAlchemy) that lets you work with database rows as Python objects.
- **Migration:** a versioned script that changes the database structure (Alembic).
- **Schema (Pydantic):** a class describing the shape of data going in or out of the API. (Not the same as a database table.)

---

# PART B — FUNCTIONAL REQUIREMENTS

Each module lists: description, why, user stories, behaviour, backend responsibilities, key API operations, entities, validation, permissions, edge cases, errors, and 🤔 questions. Full endpoint details are in Part D; full tables in Part C.

## B1. Authentication

**Description:** Register, log in, log out, stay logged in via tokens, change password, deactivate account. **Why:** Every other feature needs to know *who* is acting.

**Concepts**

- **Authentication** = proving *who you are* (logging in). *Analogy: showing your ID at the gate.*
- **Authorization** = deciding *what you may do* (can you delete this post?). *Analogy: the gate guard checking if your ticket allows the VIP area.* Being authenticated does **not** mean being authorized.
- **Password hashing:** a one-way scramble of the password (bcrypt/argon2). We store the hash, never the password. Even we cannot read it back; at login we hash the typed password and compare.
- **JWT (JSON Web Token):** a signed string the server gives after login. The client sends it with each request (`Authorization: Bearer <token>`). The server verifies the signature and reads the user id inside. It is *signed*, not *encrypted* — never put secrets in it.

**User stories**

- As a visitor, I can register with email, username, and password.
- As a user, I can log in and receive an access token.
- As a user, I can fetch my own account (`/users/me`), change my password, or deactivate my account.

**Expected behaviour**

- Registration creates a user with a hashed password; response never contains the password.
- Login accepts email-or-username + password, returns `{access_token, token_type}`.
- Protected routes reject missing/invalid/expired tokens with 401.
- Logout: with stateless JWTs, logout is mainly the client discarding the token. The server endpoint may exist for API completeness (optional token denylist is an advanced extension).
- Deactivated users cannot log in; their content is hidden from public views.

**Backend responsibilities:** hash/verify passwords, issue/verify JWTs, a reusable `get_current_user` dependency, a `get_current_admin` dependency. **Entities:** `users` **Validation:** email valid format; username 3–30 chars, `[a-zA-Z0-9_]`, stored lowercase; password ≥ 8 chars; new password ≠ old. **Permissions:** register/login public; everything else needs a token. **Edge cases:** email differs only in case (`A@x.com` vs `a@x.com`); wrong password vs unknown user (return the *same* generic message to avoid leaking which emails exist); expired token; user deactivated while holding a valid token. **Errors:** 409 duplicate email/username, 401 bad credentials, 422 invalid body, 403 deactivated account.

🤔 **Questions**

- Why must the login error not say "email not found"?
- If a token lasts 7 days and the user is deactivated on day 2, what happens on day 3? How does `get_current_user` handle it?
- Where should the secret key live, and what happens if it leaks?

## B2. User Profiles

**Description:** Public identity and editable details. **Fields:** username (unique), display name, bio, email (unique, **private**), created_at, followers_count, following_count, posts_count.

| Field | Public API? | Notes |
| --- | --- | --- |
| id, username, display_name, bio, created_at | ✅ |  |
| followers_count, following_count, posts_count | ✅ | computed |
| email | ❌ only in `/users/me` | privacy |
| password_hash | ❌ never |  |
| role, is_active | ❌ (admin views only) |  |

**Stories:** view any profile by username; update my display name/bio. **Validation:** display_name 1–50 chars; bio ≤ 160 chars; username changes optional (if allowed, must remain unique). **Permissions:** only the owner edits (`PATCH /users/me` — the *token* decides who, not an id in the body). **Edge cases:** viewing a deactivated or blocking user's profile (see B15); empty bio. **Errors:** 404 user not found; 409 username taken; 422 validation.

🤔 Why is `PATCH /users/me` safer than `PATCH /users/{id}`? What could a malicious user try with the second?

## B3. Following System

**Description:** One user follows another. This is a **many-to-many relationship**: one user can follow many users, and one user can be followed by many users. A relational database models this with a **junction table** (`follows`) holding pairs `(follower_id, following_id)`.

**Stories:** follow/unfollow; list followers; list following; see counts. **Behaviour:** Follow is idempotent-ish: following twice returns 409 (or 200 no-op — **team decides and documents**). Unfollow of a non-followed user returns 404 or 204 (decide and document). **Validation/Rules:** cannot follow self (400); cannot follow deactivated users; cannot follow if either user blocked the other (403). **Notifications:** follow creates a notification for the target. **Errors:** 400 self-follow, 404 target missing, 409 duplicate, 403 blocked.

🤔

- Can a user follow themselves? What stops it — code, database, or both? *(Guidance: both. A `CHECK (follower_id <> following_id)` constraint is the safety net.)*
- If a user is deleted, should their follow rows be deleted? (Think: `ON DELETE CASCADE`.)
- Count followers by `COUNT(*)` each time, or store a counter on the user? What goes wrong with stored counters if two requests arrive at the same time?

## B4. Posts

**Description:** Text-only content, max **280 characters** (decide with mentor). **Stories:** create, read, edit own, delete own post; see author, timestamps, like/comment/share counts. **Behaviour:** `created_at` on create; `updated_at` on edit; edited posts show `is_edited`. **Soft vs permanent deletion**

- *Hard delete:* row is removed. Simple, but related data (comments, likes, notifications) must go too, and there is no undo or moderation evidence.
- *Soft delete:* row stays, `deleted_at` is set, and every query filters `deleted_at IS NULL`. Enables undo and admin review; risk: **forgetting the filter leaks deleted content**.
- **Recommendation for Chirp:** soft delete for posts and comments; hard delete only for relationship rows (likes, bookmarks, follows). **Validation:** content trimmed, non-empty, ≤ 280 chars. **Permissions:** only author edits/deletes (admin can remove). **Edge cases:** whitespace-only content; post of a deactivated author; edit after being reported. **Errors:** 404 (also for soft-deleted), 403 not owner, 422.

🤔 If a post is soft-deleted, should its comments be visible on the user's "my comments" page? Should its notifications remain?

## B5. Comments

**Stories:** comment on a post; edit/delete own comment; list comments of a post. **Behaviour:** newest-first or oldest-first (pick one; default oldest-first for readable conversations). Paginated. **Validation:** 1–300 chars. **Permissions:** author edits; author or post owner may delete (policy to confirm); admin may remove. **Edge cases:** commenting on a deleted post (404); commenting when blocked (403).

🤔 Can the post owner edit someone else's comment? *(Guidance: almost certainly no — deleting is moderation, editing is putting words in someone's mouth.)*

## B6. Comment Replies (threads)

**Options for the database**

| Approach | Idea | Pros | Cons |
| --- | --- | --- | --- |
| **A. `parent_comment_id` on comments (self-reference)** | A reply is a comment pointing to its parent | Simple, one table | Deep nesting needs recursive queries |
| B. Separate `replies` table | Dedicated table | Clear separation | Duplicate logic |
| C. Closure/path tables | Store ancestry | Fast deep queries | Complex for beginners |

**Recommendation:** Approach A, **limited to one level**: replies may only target top-level comments. Replying to a reply attaches to the top-level parent (like many platforms). **Rules:** deleting a parent comment soft-deletes it and shows "\[deleted\]" while keeping replies visible. 🤔 What should `parent_comment_id` be for a top-level comment? What happens if the parent belongs to a *different post*? (Validate!)

## B7. Likes

**Stories:** like/unlike a post; optionally like a comment. **Prevent duplicates:** a **composite unique constraint** on `(user_id, post_id)` in `post_likes`. The primary key can *be* that pair, so no separate `id` is needed. **Behaviour:** `POST /posts/{id}/like` → 201 (409 if already liked); `DELETE` → 204 (404 if not liked). **Counts:** compute with `COUNT(*)` (MVP). Cached counters are a later optimisation. **Notifications:** liking another user's post notifies the author; liking your own post does not.

🤔 Does the like table need its own `id`? Is "check then insert" in Python enough to prevent duplicates if two requests arrive simultaneously? *(Only the DB constraint is truly safe.)*

## B8. Sharing / Reposting

**Design options**

1. **Copy content** into a new post — duplicates text; edits/deletes of the original don't propagate; loses attribution.
2. **Reference the original** — a repost is a row pointing to the original post. ✅

**Recommendation:** `reposts(id, user_id, original_post_id, quote_text NULL, created_at)` with `UNIQUE(user_id, original_post_id)`. Reposts appear in feeds as "X reposted" + the original post. If the original is deleted, the repost disappears from feeds. Optional: quote text (≤ 280). **Rules:** cannot repost your own post (policy choice), cannot repost a deleted or blocked-user post. **Counts:** `share_count` = number of reposts.

🤔 Should unreposting be possible? What should a feed show if the original author deactivates?

## B9. User Feed

| Feed | Contents | MVP |
| --- | --- | --- |
| Following feed | Posts + reposts from followed users | ✅ |
| Personal posts | Posts by one user (`/users/{username}/posts`) | ✅ |
| Global feed | Recent posts from everyone | Optional |

**Generation (no algorithm):** collect IDs of followed users → select their non-deleted posts ordered by `created_at DESC, id DESC` → paginate. Exclude blocked users both ways and deactivated authors. **Offset pagination (start here):** `?limit=20&offset=40`. Simple, but can show duplicates/skip items if new posts arrive between pages, and slows on huge offsets. **Cursor pagination (advanced):** `?limit=20&before_id=105` — "give me 20 posts older than this one". Stable and fast. **Rules:** `limit` default 20, max 50.

🤔 Why must we order by `(created_at, id)` rather than only `created_at`? What does the feed look like for a user following nobody?

## B10. Bookmarks

Save/remove/list saved posts. **Private**: only the owner ever sees them; no counts shown publicly. `UNIQUE(user_id, post_id)`. Listing excludes deleted posts. 🤔 If a bookmarked post is later deleted, should the bookmark row be removed or just hidden?

## B11. Notifications

**Types:** `follow`, `post_like`, `comment`, `reply`, `mention`. **Fields:** recipient, actor, type, related post/comment (nullable), `is_read`, `created_at`. **Synchronous generation:** in this educational project, create the notification **in the same request** that causes it (inside the service function, same database transaction). No message queues. A background-task version is an optional extension. **Rules:** never notify yourself; don't notify when blocked; no duplicates for the same like. **Endpoints:** list (paginated, filter `unread_only`), mark one read, mark all read, unread count. 🤔 If a user likes then immediately unlikes, should the notification vanish? Should many likes on one post collapse into "5 people liked your post"?

## B12. Mentions

Syntax: `@username` in posts/comments. **Detection:** regex such as `@([A-Za-z0-9_]{3,30})` on create/edit; lowercase; ignore non-existent users; ignore duplicates; cap (e.g. max 10 mentions). **Storage:** a `mentions` table (`post_id` or `comment_id`, `mentioned_user_id`) — enables "posts mentioning me" and avoids re-parsing. **Notifications:** one `mention` notification per mentioned user (not to self, not if blocked). 🤔 What if someone edits a post to add a mention? To remove one?

## B13. Hashtags

Syntax: `#python`. Regex such as `#([A-Za-z0-9_]{1,50})`, stored lowercase without `#`. **Database approaches**

1. Parse on every search with `ILIKE '%#python%'` — easy, slow, imprecise.
2. **Normalized tables:** `hashtags(id, name UNIQUE)` + `post_hashtags(post_id, hashtag_id)` ✅ (many-to-many).
3. PostgreSQL array/JSONB column — compact but less beginner-friendly. **Endpoints:** `GET /hashtags/{name}/posts`; optional `GET /hashtags/trending` (count of uses in last 24h). 🤔 Is `#Python` the same as `#python`? What happens to hashtag links when a post is edited?

## B14. Search

Users by username/display name; posts by text; hashtags by name. Start with `ILIKE '%term%'` (case-insensitive) with pagination and minimum 2 characters. Always exclude deleted/blocked/deactivated. **Extension:** PostgreSQL full-text search (`tsvector`, GIN index) or `pg_trgm`. 🤔 Why is `ILIKE '%term%'` slow at scale, and why must we still never build SQL by concatenating the search string?

## B15. Blocking

**Policy (simple and consistent):** If A blocks B:

- B cannot follow A, like/comment/reply/repost A's content, or mention-notify A.
- Existing follows between them (both directions) are removed.
- Neither sees the other's posts in feeds, search, or comment lists.
- B viewing A's profile returns **404** (A appears not to exist) — avoids leaking the block.
- A can see B's profile *basic info* only to manage the block list (`GET /blocks`). **Rules:** cannot block self; duplicate block → 409 (or no-op); unblock restores nothing automatically (follows must be redone). 🤔 Block is *directional* in the table but its effect is *symmetric* in visibility. How does a query check "either direction"?

## B16. Reporting

Report a post, comment, or user. **Fields:** reporter, target type + id, reason (enum: `spam`, `harassment`, `hate`, `misinformation`, `other`), optional description (≤ 500), status (`open`, `reviewed`, `dismissed`, `action_taken`), timestamps. **Rules:** one open report per (reporter, target); cannot report yourself or your own content; reporters never see who else reported. 🤔 One table with `target_type` + `target_id` (flexible, no real FK) vs three nullable FK columns with a CHECK that exactly one is set (safer). *Recommendation: three nullable FKs + CHECK.*

## B17. Admin Functionality

**RBAC (Role-Based Access Control):** permissions come from a role stored on the user (`user` or `admin`). Endpoints declare the role they need through a dependency. Admins can: list/filter reports, change report status, deactivate/reactivate users, remove posts/comments (soft delete with `removed_by_admin`). **Rules:** admins cannot deactivate themselves; every admin action is logged (optional `admin_actions` table as Later). **Creating the first admin:** via a CLI/seed script, never a public endpoint.

---

# PART C — DATABASE DESIGN (PostgreSQL)

**Conventions:** table names plural snake_case; `id BIGINT GENERATED ALWAYS AS IDENTITY` primary keys; all timestamps `TIMESTAMPTZ` stored in UTC; `created_at DEFAULT now()`.

### users

| Column | Type | Null | Default | Constraints / Notes |
| --- | --- | --- | --- | --- |
| id | BIGINT identity | NO | auto | **PK** |
| username | VARCHAR(30) | NO |  | **UNIQUE**, stored lowercase |
| email | VARCHAR(255) | NO |  | **UNIQUE**, lowercase |
| password_hash | VARCHAR(255) | NO |  | never exposed |
| display_name | VARCHAR(50) | NO |  |  |
| bio | VARCHAR(160) | YES | NULL |  |
| role | VARCHAR(10) | NO | 'user' | CHECK in ('user','admin') |
| is_active | BOOLEAN | NO | true | deactivation |
| created_at | TIMESTAMPTZ | NO | now() |  |
| updated_at | TIMESTAMPTZ | NO | now() |  |

Indexes: unique on `username`, unique on `email` (automatic with UNIQUE).

### follows

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| follower_id | BIGINT | NO | **FK → users.id** ON DELETE CASCADE |
| following_id | BIGINT | NO | **FK → users.id** ON DELETE CASCADE |
| created_at | TIMESTAMPTZ | NO | default now() |

**PK** `(follower_id, following_id)`; **CHECK** `follower_id <> following_id`; index on `following_id` (to list followers fast).

### posts

| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | BIGINT identity | NO |  | PK |
| author_id | BIGINT | NO |  | FK → users.id (ON DELETE CASCADE) |
| content | VARCHAR(280) | NO |  |  |
| created_at | TIMESTAMPTZ | NO | now() |  |
| updated_at | TIMESTAMPTZ | YES | NULL | set on edit |
| deleted_at | TIMESTAMPTZ | YES | NULL | soft delete |

Indexes: `(author_id, created_at DESC)`, `(created_at DESC)`.

### comments

| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | BIGINT identity | NO |  | PK |
| post_id | BIGINT | NO |  | FK → posts.id ON DELETE CASCADE |
| author_id | BIGINT | NO |  | FK → users.id |
| parent_comment_id | BIGINT | YES | NULL | FK → comments.id (self-reference); NULL = top-level |
| content | VARCHAR(300) | NO |  |  |
| created_at / updated_at / deleted_at | TIMESTAMPTZ |  |  | as in posts |

Indexes: `(post_id, created_at)`, `(parent_comment_id)`.

### post_likes

`user_id` FK users, `post_id` FK posts, `created_at`. **PK `(user_id, post_id)`**; index on `post_id`. Both FKs ON DELETE CASCADE.

### comment_likes

Same shape: **PK `(user_id, comment_id)`**, index on `comment_id`.

### reposts

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| id | BIGINT identity | NO | PK |
| user_id | BIGINT | NO | FK → users.id |
| original_post_id | BIGINT | NO | FK → posts.id ON DELETE CASCADE |
| quote_text | VARCHAR(280) | YES | optional |
| created_at | TIMESTAMPTZ | NO | now() |

**UNIQUE `(user_id, original_post_id)`**; index `(created_at DESC)`.

### bookmarks

`user_id`, `post_id`, `created_at`; **PK `(user_id, post_id)`**; FKs cascade; index `(user_id, created_at DESC)`.

### notifications

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| id | BIGINT identity | NO | PK |
| recipient_id | BIGINT | NO | FK → users.id CASCADE |
| actor_id | BIGINT | NO | FK → users.id CASCADE |
| type | VARCHAR(20) | NO | CHECK in (follow, post_like, comment, reply, mention) |
| post_id | BIGINT | YES | FK → posts.id CASCADE |
| comment_id | BIGINT | YES | FK → comments.id CASCADE |
| is_read | BOOLEAN | NO | default false |
| created_at | TIMESTAMPTZ | NO | now() |

Index: `(recipient_id, is_read, created_at DESC)`.

### blocks

`blocker_id`, `blocked_id` (both FK users, cascade), `created_at`; **PK `(blocker_id, blocked_id)`**; CHECK not equal; index on `blocked_id`.

### reports

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| id | BIGINT identity | NO | PK |
| reporter_id | BIGINT | NO | FK → users.id |
| reported_user_id | BIGINT | YES | FK → users.id |
| reported_post_id | BIGINT | YES | FK → posts.id |
| reported_comment_id | BIGINT | YES | FK → comments.id |
| reason | VARCHAR(20) | NO | enum-like CHECK |
| description | VARCHAR(500) | YES |  |
| status | VARCHAR(20) | NO | default 'open' |
| reviewed_by | BIGINT | YES | FK → users.id (admin) |
| created_at / resolved_at | TIMESTAMPTZ |  |  |

CHECK: exactly one of the three `reported_*` columns is not NULL. Index `(status, created_at)`.

### hashtags / post_hashtags

`hashtags(id PK, name VARCHAR(50) UNIQUE NOT NULL)`; `post_hashtags(post_id FK, hashtag_id FK, PK(post_id, hashtag_id))`, index on `hashtag_id`.

### mentions

`id PK`, `mentioned_user_id FK users`, `post_id FK NULL`, `comment_id FK NULL`, `created_at`; CHECK exactly one of post/comment; index on `mentioned_user_id`.

## Database Relationships

| Relationship | Type | Implemented by |
| --- | --- | --- |
| User → Posts | one-to-many | `posts.author_id` |
| User → Comments | one-to-many | `comments.author_id` |
| Post → Comments | one-to-many | `comments.post_id` |
| Comment → Replies | one-to-many (self) | `comments.parent_comment_id` |
| User ↔ User (follow) | many-to-many | `follows` |
| User ↔ Post (like) | many-to-many | `post_likes` |
| User ↔ Post (bookmark) | many-to-many | `bookmarks` |
| Post ↔ Hashtag | many-to-many | `post_hashtags` |

```mermaid
erDiagram
    USERS ||--o{ POSTS : creates
    USERS ||--o{ COMMENTS : writes
    USERS ||--o{ FOLLOWS : "follower"
    USERS ||--o{ FOLLOWS : "following"
    USERS ||--o{ POST_LIKES : gives
    USERS ||--o{ COMMENT_LIKES : gives
    USERS ||--o{ REPOSTS : makes
    USERS ||--o{ BOOKMARKS : saves
    USERS ||--o{ NOTIFICATIONS : receives
    USERS ||--o{ NOTIFICATIONS : triggers
    USERS ||--o{ BLOCKS : blocker
    USERS ||--o{ BLOCKS : blocked
    USERS ||--o{ REPORTS : files
    USERS ||--o{ MENTIONS : "is mentioned"
    POSTS ||--o{ COMMENTS : has
    COMMENTS ||--o{ COMMENTS : "has replies"
    POSTS ||--o{ POST_LIKES : receives
    COMMENTS ||--o{ COMMENT_LIKES : receives
    POSTS ||--o{ REPOSTS : "is reposted"
    POSTS ||--o{ BOOKMARKS : "is saved"
    POSTS ||--o{ POST_HASHTAGS : tagged
    HASHTAGS ||--o{ POST_HASHTAGS : used
    POSTS ||--o{ MENTIONS : contains
    COMMENTS ||--o{ MENTIONS : contains
    POSTS ||--o{ REPORTS : "reported in"
    COMMENTS ||--o{ REPORTS : "reported in"
    POSTS ||--o{ NOTIFICATIONS : about
    COMMENTS ||--o{ NOTIFICATIONS : about

    USERS {
        bigint id PK
        varchar username UK
        varchar email UK
        varchar password_hash
        varchar role
        boolean is_active
    }
    POSTS {
        bigint id PK
        bigint author_id FK
        varchar content
        timestamptz deleted_at
    }
    COMMENTS {
        bigint id PK
        bigint post_id FK
        bigint author_id FK
        bigint parent_comment_id FK
    }
    FOLLOWS {
        bigint follower_id PK
        bigint following_id PK
    }
    POST_LIKES {
        bigint user_id PK
        bigint post_id PK
    }
```

## Database Design Lessons

| Concept | In this project |
| --- | --- |
| **Primary key** | `users.id` uniquely identifies a user. |
| **Foreign key** | `posts.author_id` must match an existing user — the DB rejects orphan posts. |
| **Unique constraint** | `users.email` prevents two accounts with one email. |
| **Composite unique/PK** | `(user_id, post_id)` in `post_likes` prevents duplicate likes. |
| **Index** | `follows(following_id)` makes "list followers" fast, like a book's index. Indexes speed reads but slow writes and use space — add them for real query patterns. |
| **One-to-many** | One user, many posts. |
| **Many-to-many / junction table** | Follows, likes, bookmarks, post_hashtags. |
| **Cascade deletion** | `ON DELETE CASCADE` on `post_likes.post_id`: hard-deleting a post removes its likes automatically. Use deliberately — cascades can delete more than you expect. |
| **Nullable fields** | `bio`, `deleted_at`, `parent_comment_id` are nullable because "absent" is meaningful. Everything else is NOT NULL. |
| **Timestamps** | `created_at` is auditing gold; always store in UTC. |
| **Soft deletion** | `deleted_at` on posts/comments; every read query filters it. |

---

# PART D — API DESIGN

**Base path:** `/api/v1`. **Auth:** `Authorization: Bearer <JWT>`. **Format:** JSON. **IDs:** posts/comments by numeric id; users by `username` for reading (`/users/{username}`) and by `id` for actions.

## Status Codes

| Code | Meaning | Chirp example |
| --- | --- | --- |
| 200 OK | Success with body | GET post |
| 201 Created | New resource made | POST /posts |
| 204 No Content | Success, no body | DELETE like |
| 400 Bad Request | Request logically wrong | Follow yourself |
| 401 Unauthorized | Missing/invalid identity (really "unauthenticated") | No/expired token |
| 403 Forbidden | Known user, not allowed | Edit someone else's post |
| 404 Not Found | Doesn't exist (or hidden) | Deleted post |
| 409 Conflict | Clashes with current state | Duplicate like/username |
| 422 Unprocessable Entity | Body fails schema validation | Empty content |

## Endpoint Catalogue

**Legend:** 🔒 = token required, 🛡 = admin only.

### Health & Auth

| Method | Route | Purpose | Auth | Success | Common errors |
| --- | --- | --- | --- | --- | --- |
| GET | `/health` | Liveness check | – | 200 `{"status":"ok"}` | – |
| POST | `/auth/register` | Create account. Body: `email, username, password, display_name` | – | 201 user (public+email) | 409, 422 |
| POST | `/auth/login` | Body: `identifier, password` | – | 200 `{access_token, token_type}` | 401, 403 |
| POST | `/auth/logout` | Client discards token (server may no-op) | 🔒 | 204 | 401 |
| PUT | `/auth/password` | Body: `current_password, new_password` | 🔒 | 204 | 400, 401, 422 |
| POST | `/auth/deactivate` | Body: `password` | 🔒 | 204 | 401 |

### Users

| Method | Route | Purpose | Auth | Success | Errors |
| --- | --- | --- | --- | --- | --- |
| GET | `/users/me` | Own account (includes email) | 🔒 | 200 | 401 |
| PATCH | `/users/me` | Body: `display_name?, bio?` | 🔒 | 200 | 409, 422 |
| GET | `/users/{username}` | Public profile + counts + `is_following` | optional | 200 | 404 |
| GET | `/users/{username}/posts` | Personal posts. Query: `limit, offset` | optional | 200 page | 404 |

### Follows

| Method | Route | Purpose | Auth | Success | Errors |
| --- | --- | --- | --- | --- | --- |
| PUT | `/users/{user_id}/follow` | Follow (idempotent variant) | 🔒 | 201/204 | 400, 403, 404, 409 |
| DELETE | `/users/{user_id}/follow` | Unfollow | 🔒 | 204 | 404 |
| GET | `/users/{username}/followers` | List, paginated | optional | 200 | 404 |
| GET | `/users/{username}/following` | List, paginated | optional | 200 | 404 |

*(The assignment's `POST /users/{id}/follow` is fine too; PUT expresses "make this relationship exist" and teaches idempotency. The team picks one in the API contract.)*

### Posts

| Method | Route | Purpose | Auth | Success | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | `/posts` | Body: `content` | 🔒 | 201 post | 401, 422 |
| GET | `/posts/{post_id}` | Single post | optional | 200 | 404 |
| PATCH | `/posts/{post_id}` | Body: `content` | 🔒 owner | 200 | 403, 404, 422 |
| DELETE | `/posts/{post_id}` | Soft delete | 🔒 owner/admin | 204 | 403, 404 |
| POST | `/posts/{post_id}/repost` | Body: `quote_text?` | 🔒 | 201 | 403, 404, 409 |
| DELETE | `/posts/{post_id}/repost` | Undo repost | 🔒 | 204 | 404 |

### Comments

| Method | Route | Purpose | Auth | Success | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | `/posts/{post_id}/comments` | Body: `content, parent_comment_id?` | 🔒 | 201 | 400 (bad parent), 403, 404, 422 |
| GET | `/posts/{post_id}/comments` | Top-level comments; `limit, offset` | optional | 200 | 404 |
| GET | `/comments/{comment_id}/replies` | Replies | optional | 200 | 404 |
| PATCH | `/comments/{comment_id}` | Edit | 🔒 owner | 200 | 403, 404 |
| DELETE | `/comments/{comment_id}` | Soft delete | 🔒 owner/post owner/admin | 204 | 403, 404 |

### Likes

| Method | Route | Auth | Success | Errors |
| --- | --- | --- | --- | --- |
| POST / DELETE | `/posts/{post_id}/like` | 🔒 | 201 / 204 | 404, 409 (dup), 403 (blocked) |
| POST / DELETE | `/comments/{comment_id}/like` | 🔒 | 201 / 204 | same |

### Feed

| Method | Route | Query | Auth | Success |
| --- | --- | --- | --- | --- |
| GET | `/feed` | `limit` (≤50, default 20), `offset` | 🔒 | 200 page of posts/reposts |
| GET | `/feed/global` *(optional)* | same | optional | 200 |

### Bookmarks

`POST /posts/{post_id}/bookmark` (201, 409) · `DELETE /posts/{post_id}/bookmark` (204, 404) · `GET /bookmarks` (200 page). All 🔒.

### Notifications

`GET /notifications?unread_only=` · `GET /notifications/unread-count` · `PATCH /notifications/{id}/read` (204, 403, 404) · `POST /notifications/read-all` (204). All 🔒; users only see their own.

### Hashtags & Search

| Method | Route | Notes |
| --- | --- | --- |
| GET | `/hashtags/{name}/posts` | paginated |
| GET | `/hashtags/trending` *(optional)* | top N last 24h |
| GET | `/search/users?q=` | username/display name |
| GET | `/search/posts?q=` | text |
| GET | `/search/hashtags?q=` | name prefix |

`q` required, 2–50 chars (422 otherwise).

### Blocking

`PUT /users/{user_id}/block` (204; 400 self; 404) · `DELETE /users/{user_id}/block` (204; 404) · `GET /blocks` (200). 🔒

### Reports

`POST /reports` 🔒 — Body: `{target_type: "post|comment|user", target_id, reason, description?}` → 201; 404, 409 duplicate, 400 self-report.

### Admin 🛡 (403 for non-admin)

`GET /admin/reports?status=` · `PATCH /admin/reports/{id}` (`status`) · `POST /admin/users/{id}/deactivate` · `POST /admin/users/{id}/reactivate` · `DELETE /admin/posts/{id}` · `DELETE /admin/comments/{id}`.

## API Response Standards

**Single resource**

```json
{
  "id": 21,
  "content": "Learning FastAPI today!",
  "author": { "id": 4, "username": "ali", "display_name": "Ali" },
  "like_count": 3,
  "comment_count": 1,
  "share_count": 0,
  "liked_by_me": false,
  "bookmarked_by_me": false,
  "created_at": "2026-10-05T09:30:00Z",
  "updated_at": null
}
```

**Paginated list**

```json
{ "items": [ ], "limit": 20, "offset": 0, "total": 134 }
```

**Conventions:** `snake_case` keys; ISO-8601 UTC timestamps; never `null` for lists (use `[]`); same object shape everywhere a "post" appears.

**Why agree on the contract first?** The frontend can build screens against agreed JSON before the backend exists, and renaming `like_count` to `likes` silently breaks every screen that uses it.

---

# PART E — FASTAPI PROJECT STRUCTURE

```text
backend/
├── app/
│   ├── main.py            # creates FastAPI app, includes routers
│   ├── config.py          # settings from environment (.env)
│   ├── database.py        # engine, session, Base
│   ├── models/            # SQLAlchemy models (tables)
│   ├── schemas/           # Pydantic models (request/response shapes)
│   ├── routers/           # HTTP layer: URLs, params, status codes
│   ├── services/          # business rules (who may do what, notifications)
│   ├── repositories/      # database queries (optional layer; see note)
│   ├── dependencies/      # get_db, get_current_user, require_admin
│   ├── utils/             # regex helpers, pagination helpers
│   └── core/              # security (hashing, JWT), exceptions
├── tests/                 # mirrors app/ structure
├── migrations/            # Alembic versions
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
└── README.md
```

**Do not over-engineer:** `repositories/` is optional. Start with routers + services; add repositories if queries clutter services. Decide as a team and write it in the README.

| Thing | What it is | Where it lives |
| --- | --- | --- |
| **SQLAlchemy model** | Python class = database table | `models/` |
| **Pydantic schema** | Validates/serialises API data; hides fields like `password_hash` | `schemas/` |
| **Router (controller)** | Receives request, calls service, returns response. *No business rules, no raw queries.* | `routers/` |
| **Service (business logic)** | The rules: "can't follow yourself", "notify author on like" | `services/` |
| **Repository (DB logic)** | Queries: "get followers of user X" | `repositories/` |

**Rule of thumb:** a router should read like a short summary; if it's over \~20 lines, logic belongs in a service.

---

# PART F — TEAM STRUCTURE

| Team | Owns | Depends on |
| --- | --- | --- |
| Foundation/Auth | Config, DB session, users, JWT, `get_current_user` | – |
| Users/Profile | Profiles, `/users/me` | Auth |
| Posts | Posts CRUD, soft delete, hashtags/mentions parsing | Auth |
| Social Graph | Follow, block | Users |
| Interaction | Likes, reposts, bookmarks | Posts |
| Comments | Comments, replies, comment likes | Posts |
| Feed | Following/personal/global feeds | Posts, Social Graph |
| Notifications | Notification model + creation helpers | Interaction, Comments, Social Graph |
| Search | Search endpoints | Posts, Users |
| Safety/Admin | Reports, admin endpoints | Posts, Comments, Users |
| QA/Testing | Test plans, fixtures, CI-style checks, bug triage | All |

**Collaboration rules**

- Teams of 2–3 students; every student owns at least one module and **reviews** another team's PRs each week.
- **Rotate** modules at the end of each phase (e.g. swap Posts ↔ Comments) so nobody knows only one corner.
- Shared files (`models/`, `main.py`, migrations) need a heads-up in the team chat; two people changing the same table at once creates migration conflicts.
- Weekly 15-minute stand-up: *What did I finish? What am I doing? What blocks me?*

---

# PART G — GITHUB WORKFLOW

## Vocabulary

| Term | Meaning (Chirp example) |
| --- | --- |
| **Repository (repo)** | The project folder tracked by Git, with full history |
| **Local repository** | Your copy on your laptop |
| **Remote repository** | The shared copy on GitHub (`origin`) |
| **Clone** | Download the remote repo the first time |
| **Commit** | A saved snapshot with a message |
| **Push** | Upload your commits to GitHub |
| **Pull** | Download others' commits and merge them into yours |
| **Branch** | A parallel line of work, so your half-finished feature doesn't break others |
| **Merge** | Combine one branch into another |
| **Merge conflict** | Two people changed the same lines; Git asks a human to choose |
| **Pull Request (PR)** | A request to merge your branch, with a discussion page |
| **Code review** | A teammate reads your PR and gives feedback |
| **Issue** | A tracked task or bug |
| **Label** | Tag on issues/PRs: `feature`, `bug`, `phase-3`, `auth` |
| **Milestone** | Group of issues = a phase ("Phase 3 — Posts") |

## Branch Strategy

```text
main        ← stable, always works; only receives merges from develop
develop     ← integration branch; all finished features land here
feature/*   ← one feature each: feature/auth-register, feature/create-post
fix/*       ← one bug each: fix/duplicate-like
docs/*      ← documentation: docs/api-contract
```

**Protect `main` and `develop` on GitHub:** require a PR and at least 1 approval; block direct pushes.

## Feature Workflow

1. Pull latest `develop`
2. Create a feature branch
3. Work on one feature
4. Commit changes (small, meaningful)
5. Push the branch
6. Open a pull request into `develop`
7. Another student reviews
8. Fix review comments
9. Merge into `develop`
10. Delete the feature branch

```bash
git checkout develop
git pull origin develop

git checkout -b feature/create-post

# ...work...
git add app/routers/posts.py app/services/posts.py
git commit -m "feat: add create post endpoint"

git push origin feature/create-post
# then open a PR on GitHub
```

**If `develop` moved while you worked:**

```bash
git checkout develop && git pull origin develop
git checkout feature/create-post
git merge develop        # resolve conflicts, run tests, commit
```

**Resolving a conflict:** open the file, find `<<<<<<<`, `=======`, `>>>>>>>`, keep the right code (talk to the other author!), remove the markers, run tests, commit.

## Commit Message Convention

Format: `type: short imperative summary`

```text
feat: add user registration
fix: prevent duplicate likes
docs: update API documentation
test: add post creation tests
refactor: move auth logic into service
chore: add .env.example
```

**Why it matters:** history becomes a readable story; reviewers see intent; bugs can be traced to the commit that introduced them. `update`, `changes`, `asdf` tell no one anything.

## Pull Request Template (`.github/pull_request_template.md`)

```markdown
## What was added?

## Why was it needed?

## How was it implemented?

## How can it be tested?
(steps, or the pytest command, or the /docs endpoint to try)

## Which issue does it close?
Closes #

## Known limitations?

## Checklist
- [ ] Branch is up to date with develop
- [ ] Tests added/updated and passing
- [ ] Migration included (if DB changed)
- [ ] No secrets committed
- [ ] API matches the agreed contract
```

*(No screenshots required; backend is the focus.)* **Rule: at least one reviewer approval before merge. You may not approve your own PR.**

## Code Review Guide

**Reviewer checklist**

- Does it work (did you run it)?
- Is the logic understandable?
- Duplicate code? Meaningful names?
- Is input validated?
- Are permissions checked (owner? admin? blocked?)
- Are database queries correct (filters deleted rows)?
- Edge cases handled?
- Tests included and meaningful?
- Does the API match the contract?

**Review respectfully — ask questions, don't accuse**

| Instead of | Say |
| --- | --- |
| "This code is wrong." | "What happens if the user tries to like the same post twice?" |
| "Bad naming." | "Could `x` be renamed so we can tell it's the post id?" |
| "Why didn't you test this?" | "Could we add a test for an unauthenticated request?" |

Praise good work too: "Nice use of a dependency here." **Authors:** respond to every comment, don't take it personally, and explain decisions.

---

# PART H — GITHUB ISSUES AND TASK MANAGEMENT

**Example issue**

```text
Title: Implement Create Post API

Description:
Allow authenticated users to create text posts.

Acceptance Criteria:
- User must be logged in.
- Content cannot be empty.
- Maximum length (280) is enforced.
- Post is linked to current user.
- created_at is stored.
- API returns 201.

Endpoint: POST /posts

Tests:
- valid post
- empty post
- unauthenticated request
- oversized post
```

### Feature template (`.github/ISSUE_TEMPLATE/feature.md`)

```markdown
---
name: Feature
about: Propose or describe a new feature
labels: feature
---
## Summary
## User story
As a ___, I want ___, so that ___.
## Acceptance criteria
- [ ] 
## API (method, route, request, response, errors)
## Database changes
## Tests required
## Questions to discuss before coding
```

### Bug template

```markdown
---
name: Bug report
labels: bug
---
## What happened?
## What did you expect?
## Steps to reproduce
1. 
## Request / response (remove tokens and passwords!)
## Environment (OS, Python version, branch)
## Possible cause (optional)
```

### Refactor template

```markdown
---
name: Refactor
labels: refactor
---
## What code is being improved and why?
## Behaviour must NOT change — how will we prove it? (tests)
## Files affected
```

### Documentation template

```markdown
---
name: Documentation
labels: documentation
---
## What needs documenting?
## Where? (README, API docs, docstrings)
## Audience
```

**Suggested labels:** `feature`, `bug`, `refactor`, `documentation`, `good first issue`, `needs discussion`, `blocked`, `phase-N`, and one per team. **Milestones:** one per phase (Part I). **Board columns:** Backlog → Ready → In Progress → In Review → Done.

---

# PART I — DEVELOPMENT PHASES

| Phase | Build | Deliverable | Key learning |
| --- | --- | --- | --- |
| **0 — Environment & Git** | Git, GitHub, venv, FastAPI hello world, PostgreSQL, `.env` | `GET /health` | Tooling, first PR |
| **1 — Auth & Users** | `users` table, register, login, JWT, `/users/me`, profile view/update | Working login | Hashing, JWT, dependencies |
| **2 — Social Graph** | follow, unfollow, followers, following, counts | Follow endpoints | Many-to-many, constraints |
| **3 — Posts** | create, read, update, soft delete | Post CRUD | Ownership, soft delete |
| **4 — Interaction** | likes, comments, replies, reposts | Interaction endpoints | Uniqueness, self-reference |
| **5 — Feed** | following feed, personal posts, pagination | `/feed` | Joins, ordering, pagination |
| **6 — Social Features** | bookmarks, mentions, hashtags, notifications | Notifications working | Parsing, side effects, transactions |
| **7 — Search & Safety** | search, blocking, reporting, admin | Block & report | Policy consistency, RBAC |
| **8 — Quality** | tests, validation, refactoring, docs, error handling | ≥ agreed coverage | Maintainability |
| **9 — Integration** | Connect Next.js to FastAPI (CORS, auth header, errors) | Working end-to-end app | API contracts |

**Phase 9 note for students:** the browser blocks requests to a different origin unless the backend allows it. Enable **CORS** (Cross-Origin Resource Sharing) in FastAPI for the frontend's URL only. The frontend stores the token, sends `Authorization: Bearer ...`, and shows the `detail` message on errors.

---

# PART J — DEFINITION OF DONE

A feature is **Done** only when all are true:

- [ ] Requirements understood and acceptance criteria met
- [ ] Database changes completed and reviewed with the team
- [ ] Alembic migration exists and runs on a fresh database
- [ ] Endpoint works as per API contract
- [ ] Validation present (Pydantic + business rules)
- [ ] Permissions checked (auth, ownership, blocks, role)
- [ ] Expected errors return correct status + `detail`
- [ ] Tests written and passing (happy path + failure paths)
- [ ] Swagger `/docs` shows correct models, descriptions, status codes
- [ ] Code follows folder structure (no logic in routers, no secrets)
- [ ] PR reviewed (≥ 1 approval) and merged into `develop`
- [ ] Documentation/API contract updated
- [ ] Frontend notified of any contract change

---

# PART K — TESTING STRATEGY

| Type | What | Chirp example |
| --- | --- | --- |
| **Unit test** | One function in isolation | `extract_hashtags("hi #Python")` → `["python"]` |
| **API test** | Call an endpoint, check status + body | `POST /posts` returns 201 |
| **Integration test** | Several parts together, real test DB | Like → notification created |
| **Manual test** | You click through `/docs` | Try the happy path and 3 failures |

**Tools:** `pytest` runs tests; FastAPI's `TestClient` (or `httpx`) simulates requests; use a **separate test database** (never your dev data) and fixtures that create users/tokens. Each test must be independent: set up its own data.

**Test thinking:** for every endpoint ask — *works? bad input? not logged in? not allowed? does not exist? already exists?*

**Sample scenarios**

```text
AUTH
✓ Register with valid data returns 201 and no password field
✓ Duplicate email returns 409
✓ Wrong password returns 401
✓ Expired/invalid token returns 401

FOLLOW
✓ User can follow another user
✓ User cannot follow themselves
✓ Duplicate follow is rejected
✓ User can unfollow
✓ Unauthenticated user cannot follow
✓ Cannot follow a user who blocked you

POSTS
✓ Create valid post (201)   ✓ Empty/oversized rejected (422)
✓ Only owner can edit/delete (403 otherwise)
✓ Deleted post returns 404 and disappears from feed

LIKES
✓ Like works; second like → 409; unlike works; unlike when not liked → 404
✓ Like count changes correctly

COMMENTS & REPLIES
✓ Comment on existing post; on deleted post → 404
✓ Reply to top-level comment OK; reply from a different post's comment rejected

FEED
✓ Shows only followed users' posts, newest first
✓ Pagination: page 2 has no overlap with page 1
✓ Excludes deleted and blocked content

NOTIFICATIONS
✓ Like creates one notification for author; self-like creates none
✓ User cannot read another user's notifications
✓ Mark all read sets unread count to 0

BLOCK / REPORT / ADMIN
✓ Blocking removes follows both ways
✓ Normal user calling /admin/* gets 403
✓ Duplicate open report → 409
```

---

# PART L — ERROR HANDLING

**Standard error body**

```json
{ "detail": "You are already following this user." }
```

For validation (422), FastAPI returns a list of field errors; keep that default and document it.

| Category | Status | Guidance |
| --- | --- | --- |
| Validation | 422 / 400 | Say which field and why |
| Authentication | 401 | Generic: "Could not validate credentials" |
| Authorization | 403 | "You do not have permission to edit this post." |
| Not found | 404 | Also used to hide blocked/deleted content |
| Conflict | 409 | "Username already taken." |
| Unexpected | 500 | Generic: "Internal server error." **Log** details server-side |

**Never expose** stack traces, SQL, file paths, hashes, or whether an email exists. Use custom exceptions in `core/` and a global exception handler so services raise meaningful errors and routers stay clean.

---

# PART M — SECURITY BASICS

- **Password hashing:** use bcrypt/argon2 via `passlib` or `bcrypt`. Never plain text, never MD5/SHA-1.
- **JWT security:** strong random `SECRET_KEY`; short expiry (e.g. 30–60 min); include only `sub` (user id) and `exp`; verify signature and expiry on every request.
- **Secret keys & `.env`:** secrets and database passwords live in environment variables loaded from `.env`.
- **Why `.env` is never committed:** Git history is permanent and GitHub repos are shared (and bots scan public repos within minutes). A leaked key lets anyone forge tokens or read your database. Commit **`.env.example`** (fake values) instead, and add `.env` to `.gitignore`. If a secret is ever committed: **rotate it immediately**; deleting the file doesn't erase history.
- **SQL injection:** the ORM sends user values as *parameters*, not pasted into SQL. Never build SQL with f-strings from user input.
- **Authorization checks:** every write endpoint verifies ownership/role; identity comes from the token, not the request body.
- **Input validation:** Pydantic limits on every field.
- **Minimal data exposure:** separate response schemas (`UserPublic`, `UserMe`).
- **Rate limiting (optional):** limit login attempts per IP (`slowapi`).

**`.env.example`**

```env
APP_ENV=development
DATABASE_URL=postgresql+psycopg2://chirp_user:change_me@localhost:5432/chirp_db
TEST_DATABASE_URL=postgresql+psycopg2://chirp_user:change_me@localhost:5432/chirp_test_db
SECRET_KEY=replace-with-a-long-random-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:3000
```

Generate a key: `python -c "import secrets; print(secrets.token_urlsafe(48))"`

---

# PART N — API DOCUMENTATION

FastAPI generates **OpenAPI** documentation automatically; open **`/docs`** (Swagger UI) to read and try every endpoint, and `/redoc` for a reading-friendly view. The quality depends on what you write:

- **Request models** → documented body fields and constraints
- **`response_model`** → documented responses (and hides extra fields like `password_hash`)
- **`status_code=`, `responses={...}`** → documented codes
- **`summary`, `description`, `tags`** → readable grouped docs
- **Examples in schemas** → frontend developers see realistic JSON

To test protected routes: log in, click **Authorize** in `/docs`, paste the token. Treat `/docs` as part of the product: the frontend developer will read it daily.

---

# PART O — FRONTEND & BACKEND COLLABORATION

**API contract:** an agreement, written before coding, on URL, method, request data, response data, errors, and auth requirement. Keep contracts in `docs/api-contract.md` or as GitHub issue text and update through PRs.

**Example**

```http
GET /users/42
```

Hmm — Chirp reads users by username, so the final contract may be `GET /users/hamza`. The team decides, writes it down, and everyone follows it. Example response:

```json
{
  "id": 42,
  "username": "hamza",
  "display_name": "Hamza",
  "bio": "Python learner",
  "followers_count": 21,
  "following_count": 14,
  "posts_count": 8,
  "is_following": false
}
```

**Why random changes break things:** if the backend renames `followers_count` to `followers`, the frontend shows `undefined` or crashes. Rules:

1. Additive changes (new fields) are usually safe; renames/removals/type changes are **breaking**.
2. Breaking changes need an issue, agreement, and a heads-up.
3. Backend merges contract changes to `develop` *before* telling the frontend "ready".

---

# PART P — SOFTWARE DEVELOPMENT WORKFLOW (Create Post)

```mermaid
flowchart TD
    A[Product Requirement] --> B[GitHub Issue]
    B --> C[Discuss Requirements]
    C --> D[Database Design]
    D --> E[API Contract]
    E --> F[Create Feature Branch]
    F --> G[Implementation]
    G --> H[Local Testing via /docs]
    H --> I[Automated Tests]
    I --> J[Push to GitHub]
    J --> K[Pull Request]
    K --> L[Code Review]
    L --> M{Changes requested?}
    M -- Yes --> N[Fix Feedback]
    N --> L
    M -- No --> O[Merge into develop]
    O --> P[Frontend Integration]
```

**Create Post in practice:** the issue lists acceptance criteria → the team confirms `posts` table and 280-char limit → contract: `POST /posts` body `{content}`, 201 returns the post object → branch `feature/create-post` → write `PostCreate` schema, `create_post` service (also extracts hashtags/mentions later), router → try `/docs` → write four tests → PR with template → review → merge → frontend builds the compose box.

---

# PART Q — PROBLEM-SOLVING EXERCISES

Answer in your team doc **before coding**. ✅ = guidance provided; others → discuss with your mentor.

**Auth**

- What should happen if a token is valid but the user was deleted? ✅ *Treat as 401 — the dependency looks the user up.*
- Should email be case-sensitive? ✅ *Normalise to lowercase.*
- How long should a token live, and what is the trade-off?

**Users**

- Which fields go in `UserPublic` and which in `UserMe`?
- If usernames can change, what breaks (links, mentions)?

**Follow**

- Can a user follow themselves? What if the request is sent twice?
- Should deleting a user delete their follow relationships?
- How do we count followers efficiently?

**Posts**

- Soft or hard delete — and what happens to likes, comments, bookmarks, notifications?
- Does editing a post re-run hashtag/mention extraction? Do removed mentions un-notify?

**Likes**

- Should likes have their own ID? ✅ *Not necessary; the pair is already unique.*
- What stops duplicate likes? ✅ *A composite PK/unique constraint plus handling the IntegrityError.*
- Stored or calculated like count? What happens when a post is deleted?

**Comments**

- Who can edit a comment? Can the post owner edit someone else's comment? ✅ *No.*
- What happens to comments when a post is deleted?
- Can you reply to a reply? How do we enforce the one-level rule?

**Reposts**

- What does the feed show if the original is deleted?
- Can I repost the same post twice with different quote text?

**Feed**

- What if a user follows 10,000 people? (Where might the query slow down?)
- A post appears twice: once original, once as a repost — dedupe or show both?

**Notifications**

- Should liking your own post generate a notification? ✅ *No.*
- What if a user likes and immediately unlikes? What if the post is deleted?
- Should the notification insert be in the same transaction as the like? Why?

**Blocking**

- A follows B, then A blocks B. What happens to the follow rows? To B's old comments on A's posts?

**Reports/Admin**

- What if the reported post is deleted before an admin reviews it?
- Why must the first admin be created by a script and not an API?

---

# PART R — COMMON BEGINNER MISTAKES

| Mistake | Why it hurts |
| --- | --- |
| Storing plain-text passwords | One database leak exposes every user (and their other accounts) |
| Forgetting foreign keys | Orphan rows; posts pointing at nonexistent users |
| Trusting `user_id` sent from frontend | Anyone can act as anyone; use the token |
| Letting users edit others' posts | Missing ownership check = broken authorization |
| Duplicate likes/follows | No unique constraint; counts become wrong |
| One giant `main.py` | Merge conflicts, unreadable, untestable |
| Queries inside every route | Duplicate logic; hard to change or test |
| Returning `password_hash` | Use response schemas |
| Committing `.env` | Secrets exposed forever in history |
| Working directly on `main` | Breaks everyone's code; no review |
| Huge commits | Unreviewable, hard to undo |
| Meaningless commit messages | History is useless for debugging |
| Merging without review | Bugs ship; no knowledge sharing |
| Changing tables without migrations | Teammates' databases drift out of sync |
| Not pulling before starting | Painful merge conflicts, wasted work |
| Forgetting `deleted_at IS NULL` | Deleted content reappears |
| Catching all exceptions silently | Hides real bugs |
| Tests that depend on each other | Random failures |

---

# PART S — ENGINEERING RULES FOR STUDENTS

1. **Understand the problem before coding.** Ten minutes of thinking saves two hours of rewriting.
2. **Never code directly on `main`.**
3. **One branch, one problem.**
4. **One PR, one clear purpose.**
5. **Pull the latest code before you start.**
6. **Never commit secrets.**
7. **Never store plain-text passwords.**
8. **Test your endpoint before asking for review.**
9. **Read another student's code every week.**
10. **Ask *why* it works, not only *how*.**
11. **Don't copy AI-generated code without understanding it.**
12. **If AI helped, you must be able to explain every important line.**
13. **Discuss database changes before making them.**
14. **Don't change another team's API contract without discussion.**
15. **Bugs are normal — document them, don't hide them.**

> 🧠 *Memory trick:* **P-B-T-R** — **P**ull, **B**ranch, **T**est, **R**eview. Do it every time.

---

# PART T — AI USAGE POLICY FOR STUDENTS

> **If you cannot explain the code, you do not own the code yet.**

**Allowed:** explaining concepts and errors; brainstorming approaches; generating test *ideas*; reviewing your code; suggesting improvements; understanding documentation. **Not allowed:** having AI build a whole feature that you paste blindly; submitting code you can't explain; skipping the problem-solving steps; pasting secrets, `.env` contents, tokens, or real user data into AI tools.

| ✅ Ask | ❌ Don't ask |
| --- | --- |
| "Explain why this database relationship is many-to-many." | "Build my entire follow system." |
| "Why does this IntegrityError occur on my likes table?" | "Fix my code" (with no attempt or understanding) |
| "What edge cases should I test for creating comments?" | "Write all my tests" |

**Accountability:** in PRs, the author may be asked in review, "Why did you do it this way?" Mentors may ask students to explain or rewrite any section live. Mention significant AI help in the PR description ("AI helped me understand X").

---

# PART U — OPTIONAL ADVANCED FEATURES *(not part of the MVP)*

Cursor pagination · Redis caching · rate limiting · background tasks (FastAPI `BackgroundTasks`/Celery) · email notifications · recommendation feed · PostgreSQL full-text search · WebSocket live notifications · Docker/Docker Compose · CI/CD with GitHub Actions · deployment · query optimisation (`EXPLAIN ANALYZE`, indexes) · token refresh/denylist · audit log for admin actions · soft-delete cleanup jobs.

---

# PART V — MVP VS FUTURE FEATURES

| Feature | MVP | Later | Advanced |
| --- | --- | --- | --- |
| Register / login / JWT | ✅ |  |  |
| Logout (client-side discard) | ✅ |  |  |
| Password change | ✅ |  |  |
| Account deactivation | ✅ |  |  |
| Profiles (view/update) | ✅ |  |  |
| Follow / unfollow / lists | ✅ |  |  |
| Posts CRUD (soft delete) | ✅ |  |  |
| Comments | ✅ |  |  |
| Replies (1 level) | ✅ |  |  |
| Post likes | ✅ |  |  |
| Comment likes |  | ✅ |  |
| Reposts |  | ✅ |  |
| Quote reposts |  |  | ✅ |
| Following feed + offset pagination | ✅ |  |  |
| Personal posts | ✅ |  |  |
| Global feed |  | ✅ |  |
| Cursor pagination |  |  | ✅ |
| Bookmarks |  | ✅ |  |
| Notifications (synchronous) | ✅ |  |  |
| Mentions |  | ✅ |  |
| Hashtags |  | ✅ |  |
| Trending hashtags |  |  | ✅ |
| Basic search (`ILIKE`) |  | ✅ |  |
| Full-text search |  |  | ✅ |
| Blocking |  | ✅ |  |
| Reporting |  | ✅ |  |
| Admin role & moderation |  | ✅ |  |
| Admin audit log |  |  | ✅ |
| Automated tests | ✅ |  |  |
| Rate limiting |  |  | ✅ |
| Redis, WebSockets, Docker, CI/CD |  |  | ✅ |

*Suggested MVP cut:* Phases 0–5 plus basic notifications. Everything else follows as capacity allows.

---

# PART W — DEVELOPMENT ROADMAP

```text
Database Setup → Users → Authentication → Posts → Comments → Likes → Follow System → Feed
```

*(Follows can start right after Users; Feed needs both Posts and Follows.)*

```mermaid
flowchart TD
    DB[Database Setup + Alembic] --> U[Users]
    U --> A[Authentication]
    A --> P[Posts]
    A --> F[Follow System]
    A --> PR[Profiles]
    P --> C[Comments + Replies]
    P --> L[Likes]
    P --> R[Reposts]
    P --> B[Bookmarks]
    P --> H[Hashtags + Mentions]
    P --> S[Search]
    P --> FD[Feed]
    F --> FD
    F --> BL[Blocking]
    C --> N[Notifications]
    L --> N
    F --> N
    H --> N
    BL --> FD
    P --> RP[Reporting]
    C --> RP
    RP --> AD[Admin]
    FD --> Q[Quality: Testing + Docs]
    N --> Q
    AD --> Q
    Q --> INT[Next.js Integration]
```

**Parallel work (after Authentication):** Posts ‖ Follow System ‖ Profiles. **After Posts:** Comments ‖ Likes ‖ Bookmarks ‖ Hashtags ‖ Search ‖ Reposts. QA team works alongside everyone from Phase 1.

---

# PART X — STUDENT ONBOARDING CHECKLIST

- [ ] Clone the repository
- [ ] Create and activate a Python virtual environment
- [ ] Install dependencies (`uv sync` from `backend/`)
- [ ] Create `.env` from `.env.example`
- [ ] Install PostgreSQL and create the database + user
- [ ] Connect the app to PostgreSQL
- [ ] Run migrations (`uv run alembic upgrade head`)
- [ ] Start FastAPI (`uv run uvicorn app.main:app --reload`)
- [ ] Open Swagger docs at `/docs`
- [ ] Create a branch
- [ ] Commit code with a conventional message
- [ ] Push branch to GitHub
- [ ] Open a pull request
- [ ] Pull updates from `develop`
- [ ] Explain GET / POST / PATCH / DELETE
- [ ] Read and write basic JSON
- [ ] Explain primary key vs foreign key

---

# PART Y — FIRST WEEK PRACTICE

| # | Exercise | Learning |
| --- | --- | --- |
| 1 | `GET /health` → `{"status": "ok"}` | Routes, running the server, `/docs` |
| 2 | Temporary Users API using an in-memory Python list (`POST /users`, `GET /users`, `GET /users/{id}`) | Request bodies, path params, 404 |
| 3 | Move users into PostgreSQL (SQLAlchemy model + Alembic migration) | ORM, sessions, migrations |
| 4 | Add Pydantic validation (username length, email format) and duplicate-email 409 | Validation, status codes |
| 5 | Create a feature branch, submit the first PR, and review a classmate's PR | The full team workflow |

**Stretch:** write three pytest tests for exercise 4. **Reflection:** What broke? How did you find it? What would you do differently?

---

# PART Z — FINAL PROJECT ARCHITECTURE

```mermaid
flowchart TD
    U[User in Browser] --> FE[Next.js Frontend]
    FE -->|HTTP / REST + JWT in Authorization header| API[FastAPI Backend]

    subgraph Backend
        API --> AUTHDEP[Auth Dependency: verify JWT, load user, check role]
        AUTHDEP --> R[Routers]
        R --> S[Services: business logic]
        S --> ORM[SQLAlchemy ORM / Repositories]
        ORM --> DB[(PostgreSQL)]
        MIG[Alembic Migrations] --> DB
        S -.validates with.-> PYD[Pydantic Schemas]
    end

    API --> DOCS[/Swagger /docs/]

    subgraph Team Workflow
        DEV[Student Developer] --> BR[Feature Branch]
        BR --> PRQ[Pull Request + Review]
        PRQ --> DEVEL[develop]
        DEVEL --> MAIN[main]
        PRQ --> TESTS[pytest]
    end
    MAIN -.deployed or run locally.-> API
```

**One-sentence summary:** the browser talks to Next.js; Next.js calls the REST API with a JWT; FastAPI authenticates the request, a router hands it to a service, the service applies rules and uses SQLAlchemy to read/write PostgreSQL; and every line of that code reaches `main` only through branches, tests, and reviewed pull requests.

---

*End of document. Update this PRD through pull requests, like any other part of the project.*