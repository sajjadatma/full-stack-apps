# T24 — MVP Cleanup & Release Gate

## Status and intent

- **Task:** T24 (depends on T23)
- **Status:** Design approved in chat; awaiting spec review
- **Product contract:** `docs/tilevision-mvp.md` v1.2, to be amended narrowly to
  v1.3 by this task
- **Goal:** retire the unrelated template Item UI, close the Compose AI
  configuration gap, document TileVision media/provider configuration, and
  verify the existing MVP release surface without broad refactoring.

## Decisions and scope

### Item compatibility

- Remove the Item navigation entry and Item-only frontend management
  components that become unused.
- Keep `/items` as an authenticated TanStack route whose `beforeLoad` redirects
  to `/products`.
- Keep the Item SQLModel, database table/data, backend endpoints, migrations,
  and generated frontend Item client operations unchanged. Do not add a
  destructive migration or alter the Item API contract.
- Replace obsolete Item management UI Playwright cases with `/items` redirect
  coverage. Preserve backend Item API regression tests.
- Update MVP contract v1.3 to resolve OQ-3: Item is not in the TileVision
  product UI; its legacy backend/API/storage remain temporarily for
  compatibility. Narrow AC-9 to preserve authentication, RBAC, administration,
  settings, and retained Item API/backend regression coverage without requiring
  the retired Item UI.

### Provider and media configuration

- In `compose.yml`, pass through the exact existing Settings names for
  `IMAGE_EDIT_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_IMAGE_MODEL`,
  `OPENAI_IMAGE_TIMEOUT_SECONDS`, and `OPENAI_IMAGE_PARAMETERS`.
- Keep values supplied by environment interpolation, preserve application
  defaults, and never place the key in frontend service configuration or source.
- Extend the existing `.env.storage.example` as the single TileVision
  configuration example. Document local persistent storage and optional S3
  settings, plus the provider settings and defaults. Identify the OpenAI key as
  required only when production AI generation is enabled; credentials remain
  placeholders. S3 credentials are optional when the runtime supplies AWS
  credentials by role/workload identity.

### Dead-code and release audit

- Remove only verified-unused Item frontend components and their exclusively
  used imports/translations. Keep generated Item wrappers and all backend
  compatibility code.
- Inspect the TileVision route/client surface for broken routes or duplicate
  hand-written wrappers; do not remove generated API operations that remain
  required by the backend contract.
- No API schema/client regeneration or database migration is planned.

## Verification and release gate

Run and report each gate independently:

1. Backend static checks: `bash scripts/lint.sh` from `backend/` (Mypy, `ty`,
   Ruff lint, Ruff formatting check).
2. Full backend suite: repository-standard `pytest`/`scripts/tests-start.sh`
   command with the configured database and required services.
3. Frontend Biome lint and production build/type validation.
4. Full Playwright Chromium suite with database, backend, and Mailpit available;
   explicitly confirm TileVision product, visualizer, history, and T23 journey
   specs are included.
5. Alembic consistency: inspect heads/history and run migrations against the
   test database; verify model metadata has no unapplied migration with
   `alembic check` where supported.
6. Repository checks: `git diff --check`, no stale generated-client changes,
   no secrets/debug logging, and no test-only production code.

If a new genuine production release blocker appears, stop before changing
additional production behavior; report the evidence and smallest proposed fix
for approval. Existing unrelated type-check failures, if any, will be
identified separately and will not expand T24 scope.

## Expected files and compatibility impact

Expected changes are limited to the TileVision MVP contract, the existing
configuration example, Compose provider environment forwarding, Item frontend
route/navigation/components/tests, and generated route metadata if the router
updates it. There is no intended API schema change, generated client change,
database migration, data deletion, or committed secret.

## Self-review

- **Scope:** bounded to the approved Item retirement, Compose wiring, focused
  configuration docs, route/client audit, and named release gates.
- **Compatibility:** Item persistence and API contracts remain intact; `/items`
  stays routable and redirects rather than becoming a broken route.
- **Configuration:** uses only existing `Settings` names and defaults; key is
  backend-only and no credential is checked in.
- **Contract consistency:** resolves OQ-3 and changes only the AC-9 wording
  needed to describe retained backend compatibility rather than obsolete UI.
- **Migration/API impact:** none planned. Any discovered requirement to alter
  these would be raised before implementation.
- **Uncertainty:** actual route/dead-code inventory, Alembic graph status, and
  baseline release-check outcomes remain to be verified during implementation.
