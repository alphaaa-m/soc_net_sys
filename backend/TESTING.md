# Testing Guide — Phase 1 Team B User Profiles

This guide covers the profile endpoints delivered for Phase 1 Team B. Authentication itself is
owned by Team A; profile API tests use the shared test fixtures to mint a token without depending
on Team A's login endpoints.

## Run the tests

Run from `backend/`:

```powershell
uv run pytest tests/test_users.py -q
```

Run all backend tests and lint as CI does:

```powershell
uv run pytest -q
uv run ruff check app tests scripts create_tables.py migrations
```

`tests/conftest.py` provisions an isolated in-memory SQLite database for every test. The test
client overrides the normal database dependency, creates a fresh schema, and removes it after
each test. These commands do not read or modify the development database.

## Automated coverage

| Scenario | Expected result |
| --- | --- |
| Read `/users/me` with the owner token | `200`; email is present, password hash and internal account fields are absent |
| Read `/users/me` without a token | `401` |
| Read an active user's public profile | `200`; only public fields and zero-valued count stubs are returned |
| Look up a username using different casing | `200`; lookup is case-insensitive |
| Read an unknown or deactivated public profile | `404` |
| Update display name and bio | `200`; values are persisted; surrounding display-name whitespace is trimmed |
| Clear the bio with JSON `null` | `200`; bio becomes `null` |
| Submit an empty patch, blank/oversized display name, or oversized bio | `422` |
| Try to set email or another unsupported field through PATCH | `422`; only profile fields are accepted |
| Update `/users/me` without a token | `401` |

Run the focused suite after profile changes. If a profile test fails, first check that any user
fixture needed by that test is explicitly requested as a test argument; fixtures are not
automatically created for a test unless requested.

## Manual API checks in Swagger

Start the API using the setup instructions in [README.md](README.md), then open
<http://localhost:8000/docs>.

> Team A's `/auth/register` and `/auth/login` endpoints are separate Phase 1 work. Once those
> endpoints are integrated, create and log in as a user in Swagger, click **Authorize**, and enter
> the access token. Until then, the automated tests cover authenticated profile calls by using the
> mentor-owned JWT helper and shared token fixture.

1. **Public profile:** call `GET /api/v1/users/{username}` for an active account. Check for `id`,
   `username`, `display_name`, `bio`, `created_at`, and all three `*_count` values. Confirm the
   response has no `email`, `password_hash`, `role`, or `is_active`.
2. **Private profile:** after authorizing, call `GET /api/v1/users/me`. Check that `email` appears,
   while `password_hash`, `role`, and `is_active` do not.
3. **Profile update:** call `PATCH /api/v1/users/me` with:

   ```json
   {
     "display_name": "Updated Name",
     "bio": "Learning with Chirp"
   }
   ```

   Expect `200`, then repeat the private-profile GET to verify persistence. Try
   `{"bio": null}` to clear the bio.
4. **Validation:** try `{"display_name": ""}`, a display name longer than 50 characters, a bio
   longer than 160 characters, an empty object, and an unsupported field such as `{"email":
   "new@example.test"}`. Each request should return `422`.
5. **Authentication:** remove the authorization token and call either `/users/me` endpoint.
   Expect `401`. Public profile GET remains available without a token.
6. **Not found:** request an unknown username. Expect `404`.

The count fields deliberately return `0` in Phase 1. Their follow/post backing data is wired in
later phases; do not treat nonzero counts as an acceptance criterion yet.
