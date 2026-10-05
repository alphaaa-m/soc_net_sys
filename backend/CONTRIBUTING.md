# Contributing

1. Pull latest `develop`, create one branch per issue: `feature/<n>-name`, `fix/<n>-name`, `docs/...`, `wiring/...`.
2. One PR → one purpose, target `develop`, fill the PR template, link `Closes #n`.
3. CI must be green (`ruff` + `pytest`). Run locally: `uv run ruff check app tests scripts create_tables.py migrations` and `uv run pytest -q`. Add new libraries with `uv add <pkg>` (updates `pyproject.toml` + `uv.lock` — never edit `uv.lock` by hand).
4. Every PR needs 1 cross-team student approval + mentor approval. Never approve your own PR.
5. Routers stay thin (no business logic, no raw queries); rules live in `services/`.
6. Schema change? Open a `schema-change` issue and wait for mentor approval before writing the migration. Never edit a merged migration.
7. Never commit `.env`, tokens, or passwords. Commit messages: `type: short summary` (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
