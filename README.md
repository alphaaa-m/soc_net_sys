# Chirp

A small, text-first social network built one phase at a time with **FastAPI +
PostgreSQL** on the backend and **Next.js** on the frontend.

- Source of truth for features and schema: [`Chirp PRD & Engineering Guide.md`](Chirp%20PRD%20%26%20Engineering%20Guide.md)
- Execution order: [`Chirp Project Management Plan.md`](Chirp%20Project%20Management%20Plan.md)

## What is live

| Phase | Module | Status |
| --- | --- | --- |
| 1 | Register / login / logout, change password, deactivate, profiles | ✅ Live |
| 2 | Follow / unfollow, followers / following, people search, posts CRUD + soft delete | ✅ Live |
| 3 | Likes, reposts, comments & replies | ⚠ Not yet implemented |
| 4 | Feed, bookmarks, notifications | ⚠ Not yet implemented |
| 5 | Post / hashtag / mention search, hashtags, mentions | ⚠ Not yet implemented |
| 6 | Blocking, reporting, admin | ⚠ Not yet implemented |

Anything that is not built yet is shown in the UI as a **warning screen** with
the phase and the planned endpoints — never as fake data. Open `/modules` in
the app to see the whole roadmap.

## Run it (Windows)

Double-click:

- **`run-all.bat`** — starts the backend **and** the frontend in two windows.
- **`run-backend.bat`** — applies migrations and starts FastAPI on
  <http://localhost:8000> (docs at `/docs`).
- **`run-frontend.bat`** — installs packages if needed and starts Next.js on
  <http://localhost:3000>.

The scripts also create missing virtual-environments / `node_modules` on first
run, so no commands have to be typed by hand.

### Manual run

```powershell
# backend
cd backend
python -m uv sync --python 3.13
python -m uv run alembic upgrade head
python -m uv run uvicorn app.main:app --reload

# frontend (second terminal)
cd frontend
npm install
npm run dev
```

Prerequisites: PostgreSQL running with the `CHIRP` database, and
`backend/.env` filled in (copy from `backend/.env.example`).

## Repository layout

```text
backend/     FastAPI app, SQLAlchemy models, Alembic migrations, pytest tests
frontend/    Next.js app (App Router) with the Chirp UI and roadmap warnings
demo/        Standalone teaching demo (not part of the real app)
run-*.bat    One-click launchers for Windows
```

## Theme

The frontend uses a **teal / brown / green / skin** palette defined as CSS
variables in `frontend/app/globals.css`: warm skin backgrounds, teal primary
actions, green success/live states and brown typography.

## Tests

```powershell
cd backend
python -m uv run pytest -q
python -m uv run ruff check app tests
```
