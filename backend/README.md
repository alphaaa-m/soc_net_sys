# Chirp Backend — Phase 0

Text-only social network API. Python · FastAPI · SQLAlchemy · Alembic · PostgreSQL · JWT · pytest.

Source of truth for features, API and schema: the **Chirp PRD** (`../Chirp PRD & Engineering Guide.md`).
Execution order: the **Project Management Plan** (`../Chirp Project Management Plan.md`).

## Setup (10 commands or fewer)

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/) (one-time install:
`irm https://astral.sh/uv/install.ps1 | iex` on Windows,
`curl -LsSf astral.sh/uv/install.sh | sh` on macOS/Linux).

```powershell
cd backend
uv sync
copy .env.example .env
# edit .env: DATABASE_URL, SECRET_KEY (generate below)
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
# create postgres DB (once):
#   CREATE DATABASE "CHIRP" OWNER postgres;
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
uv run pytest -q
```

Open Swagger: http://localhost:8000/docs — `GET /health` returns `{"status":"ok"}`.

## .env variables

| Variable | Example | Notes |
| --- | --- | --- |
| `APP_ENV` | `development` | `development` / `test` / `production` |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:change_me@localhost:5432/CHIRP` | the single database |
| `SECRET_KEY` | long random string | JWT signing key. Generate: `uv run python -c "import secrets; print(secrets.token_urlsafe(48))"`. Never commit. |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | token lifetime |
| `CORS_ORIGINS` | `http://localhost:3000` | comma-separated frontend origins (Phase 9) |

Copy `.env.example` to `.env` and fill in real values. `.env` is git-ignored; only `.env.example` (fake values) is committed.

## Database commands

Run from `backend/` (all commands via `uv run`, which uses the synced `.venv`):

| Goal | Command |
| --- | --- |
| Apply migrations (create/update tables) | `uv run alembic upgrade head` |
| Drop all versioned tables | `uv run alembic downgrade base` |
| Create a new migration (after editing `app/models.py`) | `uv run alembic revision --autogenerate -m "add xyz"` |
| List migrations | `uv run alembic history` |
| Show current DB revision | `uv run alembic current` |
| Quick create tables WITHOUT migration history (dev only) | `uv run python create_tables.py` |
| Quick drop + recreate (DESTROYS data) | `uv run python create_tables.py --drop` |
| Create first admin (never a public endpoint) | `uv run python -m scripts.seed --email you@x.com --username you --password "..." --admin` |
| Demo data (admin + 2 users + posts) | `uv run python -m scripts.seed --demo` |

Migration policy: mentor owns history. Never edit a migration already in `develop` — create a new one. Before a schema PR: `uv run alembic upgrade head` on a fresh DB must succeed.

## Project layout

```text
backend/
├── app/
│   ├── main.py          # app factory, /health, CORS, exception handlers
│   ├── config.py        # settings from .env
│   ├── database.py      # engine, SessionLocal, Base, get_db
│   ├── models.py        # all tables (PRD Part C)
│   ├── security.py      # bcrypt hashing + JWT helpers
│   ├── deps.py          # get_current_user, require_admin
│   ├── pagination.py    # shared limit/offset params
│   ├── text_utils.py    # hashtag/mention extraction (Phase 5)
│   ├── routers/         # one file per module (URL space reserved)
│   ├── services/        # business rules (Phases 1+)
│   └── schemas/         # Pydantic request/response models (Phases 1+)
├── tests/               # conftest (client, auth_headers) + test_health/test_security
├── migrations/versions/ # 0001_initial_all_tables.py
├── scripts/seed.py      # admin + demo data CLI
├── create_tables.py     # dev shortcut (no history)
├── alembic.ini
├── pyproject.toml       # dependencies + ruff/pytest config (uv)
├── uv.lock              # locked dependency versions (commit this)
├── .env.example
└── README.md
```

## How auth works (summary)

Passwords hashed with bcrypt; never stored or returned in plain text. Login issues a JWT (`sub` = user id, `exp` = expiry). Requests send `Authorization: Bearer <token>`. `get_current_user` verifies signature + expiry, loads the user, rejects deleted users (401) and deactivated users (403). `require_admin` additionally requires `role == "admin"`. Logout is client-side token discard.
