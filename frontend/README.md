# Chirp Frontend

Next.js (App Router) client for the Chirp API.

## Quick start

From the repository root, double-click **`run-frontend.bat`** (it installs
`node_modules` on first run), or:

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

The app runs at <http://localhost:3000> and talks to
`http://localhost:8000/api/v1` by default.

| Variable | Default | Notes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Include the `/api/v1` prefix |

The backend allows `http://localhost:3000` through CORS by default
(`CORS_ORIGINS` in `backend/.env`).

## What works

- **Auth (Phase 1):** register, login (email or username), logout, profile edit,
  account deactivation.
- **Profiles (Phase 1):** `/users/me` plus public profiles with live follower /
  following / post counts and an `is_following` flag.
- **Social graph & posts (Phase 2):** follow / unfollow, follower and following
  lists, create / edit / soft-delete posts, personal posts with pagination.

## Roadmap warnings

Every phase that is not built yet is represented by a warning screen instead of
a broken or fake page:

- `/modules` — the full phase-by-phase roadmap, with **Live** / **Not yet**
  badges.
- `/coming-soon/<feature>` — an explicit “not yet implemented” page listing the
  phase and the planned API endpoints.

The registry lives in `lib/features.js`, so completing a future phase means
flipping its status there (and building the real screen) in one place.

## Project structure

```text
app/
  layout.jsx                  shell + AuthProvider + sidebar
  page.jsx                    home / personal timeline
  login/, register/           auth screens
  profile/                    my account (edit, deactivate, my posts)
  u/[username]/               public profile, follow button, tabs
  posts/[id]/                 single post (edit / soft delete)
  modules/                    phase roadmap
  coming-soon/[slug]/         not-yet-implemented warning
components/                   AuthProvider, Nav, PostCard, PostComposer, FollowButton
lib/                          api client, formatting helpers, feature registry
```

## Theme

Defined as CSS variables in `app/globals.css`:

| Token | Colour |
| --- | --- |
| `--teal-600` / `--teal-700` | primary actions, links |
| `--brown-900` / `--brown-700` | typography |
| `--green-500` / `--green-700` | live/success states |
| `--skin-50` … `--skin-300` | warm background, borders, surfaces |
