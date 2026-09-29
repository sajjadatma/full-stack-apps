# T24 MVP Cleanup & Release Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retire the template Item UI without breaking its legacy API, make existing AI provider settings available to the Compose backend, document TileVision media/provider configuration, and establish the MVP release gate.

**Architecture:** Keep the `/items` TanStack route as a redirect and retain every backend Item compatibility surface. Forward the existing backend settings through Compose and extend the canonical environment example; do not introduce a second settings interface. Finish with the named static, backend, frontend, migration, Playwright, and bounded read-only security/release checks.

**Tech Stack:** FastAPI, SQLModel, Alembic, Pydantic Settings, Docker Compose, React, TypeScript, TanStack Router, Biome, Playwright, Ruff, Mypy, and ty.

**Spec:** `docs/superpowers/specs/2026-09-30-t24-mvp-cleanup-release-gate-design.md`

## Global Constraints

- Keep the legacy Item backend model, database table/data, API routes, migrations, and generated client wrappers unchanged.
- Remove the Item navigation entry and management UI; keep `/items` routable and redirect to `/products`.
- Do not create a destructive migration or change the legacy Item API contract.
- Use only existing setting names: `IMAGE_EDIT_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_IMAGE_MODEL`, `OPENAI_IMAGE_TIMEOUT_SECONDS`, and `OPENAI_IMAGE_PARAMETERS`.
- Keep OpenAI credentials backend-only; use safe placeholders and never commit secrets.
- Keep `.env.storage.example` as the single TileVision storage/provider configuration example.
- Update only the MVP contract passages needed to resolve OQ-3 and narrow AC-9.
- Do not regenerate or modify the API client; no API/schema change or database migration is planned.
- The full Playwright Chromium suite is authoritative; no test may make a paid AI request.
- If another genuine release blocker appears, stop before changing additional production behavior and request approval for the smallest fix.

## Review Focus

1. **Unauthenticated `/items` deep link:** parent auth must still redirect to login before the Item compatibility redirect. Test both authenticated `/items` → `/products` and unauthenticated `/items` → `/login` in Task 1.
2. **Legacy Item ownership/API compatibility:** management UI retirement must not change list/create/update/delete API behavior. Preserve and run `backend/tests/api/routes/test_items.py` in Task 3.
3. **Compose secret isolation and default interpolation:** AI settings must reach only the backend, with no committed key or accidental secret exposure in Playwright/frontend configuration. Validate resolved Compose JSON with a sentinel in Task 2.
4. **Generation media authorization parity:** source image, result image, and generation-scoped product-image authorization must agree with owner/read-any access. Review the existing named route tests in Task 3.
5. **Migration and metadata drift:** UI retirement and Compose changes must not create database drift or multiple migration heads. Run the Alembic graph and metadata checks in Task 3.

---

### Task 1: Retire Item UI and Resolve the MVP Contract

**Files:**
- Modify: `frontend/tests/items.spec.ts`
- Modify: `frontend/src/routes/_layout/items.tsx`
- Modify: `frontend/src/components/Sidebar/AppSidebar.tsx`
- Delete when confirmed unreferenced: `frontend/src/components/Items/AddItem.tsx`
- Delete when confirmed unreferenced: `frontend/src/components/Items/EditItem.tsx`
- Delete when confirmed unreferenced: `frontend/src/components/Items/DeleteItem.tsx`
- Delete when confirmed unreferenced: `frontend/src/components/Items/ItemActionsMenu.tsx`
- Delete when confirmed unreferenced: `frontend/src/components/Items/columns.tsx`
- Modify only for exclusively unused Item keys: `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/fa.json`
- Modify: `docs/tilevision-mvp.md`
- Preserve unchanged: `backend/app/models.py`, `backend/app/api/routes/items.py`, Item migrations, `frontend/src/client/*`, `backend/tests/api/routes/test_items.py`

**Interfaces:**
- Consumes: authenticated layout route guard; existing TanStack redirect API; existing `/products` route.
- Produces: `/items` remains addressable and redirects to `/products` after the parent authentication guard; Item backend/API contracts remain unchanged.

- [ ] **Step 1: Replace obsolete Item UI E2E coverage with redirect coverage.**

  Replace the Item management assertions in `frontend/tests/items.spec.ts` with:
  - an authenticated test that opens `/items`, expects URL `/products`, and verifies the Product catalog heading;
  - an unauthenticated test using empty storage state that opens `/items` and expects `/login`.
  Do not delete backend Item API tests.

- [ ] **Step 2: Run the replacement tests to verify the authenticated redirect fails before implementation.**

  Run from `frontend/`:

  ```bash
  bunx playwright test tests/items.spec.ts --project=chromium --reporter=list
  ```

  Expected: the unauthenticated guard test passes; the authenticated test fails because the existing Items page stays on `/items`.

- [ ] **Step 3: Retire frontend navigation and Item management components.**

  In `frontend/src/components/Sidebar/AppSidebar.tsx`, remove the Items entry and its now-unused icon/import. In `frontend/src/routes/_layout/items.tsx`, remove Item data/UI imports and component code, retaining the route and implement `beforeLoad` as a redirect to `/products`. Search the frontend before deleting each Item component or translation key; remove only files/keys with no remaining consumers. Keep all generated `ItemsService` wrappers.

- [ ] **Step 4: Resolve OQ-3 and narrow AC-9 in the MVP contract.**

  In `docs/tilevision-mvp.md`, bump version to 1.3 and update the document date/change history. State narrowly that Items are not part of the TileVision UI and the legacy backend/API/table remain temporarily for compatibility. Resolve OQ-3 and change AC-9 so retained Item backend/API regression coverage is required but obsolete Item management UI is not. Do not rewrite unrelated contract sections.

- [ ] **Step 5: Run Item redirect, authentication, and product-route checks.**

  Run the Item spec and the focused frontend products/dashboard specs. Expected: both redirect cases pass, `/products` renders after the authenticated redirect, and dashboard/product navigation remains intact.

- [ ] **Step 6: Regenerate only TanStack route metadata if the build requires it, then inspect the diff.**

  Use the repository's Vite/TanStack generation path. Expected: route metadata still includes `/items` as a path and no API client files change.

---

### Task 2: Forward AI Settings and Document TileVision Configuration

**Files:**
- Modify: `compose.yml`
- Modify: `.env.storage.example`
- Preserve unchanged: `backend/app/core/config.py`, `compose.override.yml` Playwright environment, frontend environment/configuration

**Interfaces:**
- Consumes: Pydantic Settings names/defaults in `backend/app/core/config.py`.
- Produces: backend Compose service receives all supported AI settings via ordinary Compose interpolation; no frontend or Playwright service receives `OPENAI_API_KEY`.

- [ ] **Step 1: Add the existing provider settings to the backend Compose environment.**

  In the `backend` service of `compose.yml`, forward `IMAGE_EDIT_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_IMAGE_MODEL`, `OPENAI_IMAGE_TIMEOUT_SECONDS`, and `OPENAI_IMAGE_PARAMETERS`. Preserve defaults from `Settings` (`openai`, `gpt-image-1.5`, `180`, and `{}` respectively); leave the API key unset by default. Do not add any of these values to frontend or Playwright services and do not hardcode credentials.

- [ ] **Step 2: Extend the canonical environment example with provider configuration and operational notes.**

  Keep `.env.storage.example` as the single example. Retain its existing local/S3 storage options and add the provider settings with safe placeholder values. State that a real `OPENAI_API_KEY` is required only for a deployment that enables real OpenAI generation; it is optional for tests/stubbed flows. Explain the existing defaults, local persistent-volume behavior, and that S3 static credentials may be omitted when workload identity supplies credentials.

- [ ] **Step 3: Validate Compose interpolation and backend-only secret placement.**

  Run `docker compose config --quiet`, then render Compose JSON with a non-secret sentinel supplied as `OPENAI_API_KEY`. Parse the JSON without printing it and assert:
  - the backend environment contains the sentinel and all five expected setting names;
  - default provider/model/timeout/parameters resolve as documented when not overridden;
  - `OPENAI_API_KEY` is absent from every non-backend service.

  Expected: config validation exits zero and assertions pass without exposing the resolved configuration or any real credential in command output.

- [ ] **Step 4: Check for secrets and configuration duplication.**

  Search tracked changes for key-like values and compare the canonical example against the exact names/defaults in `backend/app/core/config.py`. Expected: placeholders only, no additional configuration convention, and no frontend secret reference.

---

### Task 3: Run the Release Gate and Bounded Read-Only Audit

**Files:**
- No planned production-code changes. If a check finds another genuine production blocker, stop and report it for approval before making a fix.

**Interfaces:**
- Consumes: the Item retirement and Compose/configuration behavior from Tasks 1–2.
- Produces: recorded pass/fail evidence for each release gate; no API schema, generated-client, or database migration output.

- [ ] **Step 1: Run backend lint, formatting, and static/type checks.**

  From `backend/`, run:

  ```bash
  uv run bash scripts/lint.sh
  ```

  This runs Mypy, `ty check app`, Ruff lint, and Ruff format check. Report pre-existing failures separately; do not expand the task into unrelated type debt.

- [ ] **Step 2: Run the full backend test suite.**

  With the configured test database/services available, from `backend/` run:

  ```bash
  FASTAPI_ENV=development uv run pytest tests/
  ```

  Expected: all backend tests pass, including `tests/api/routes/test_items.py`, product/image tests, visualizer project ownership tests, and generation lifecycle/history/media authorization tests. Avoid teardown commands that remove unrelated persistent volumes.

- [ ] **Step 3: Verify Alembic graph and database/model consistency.**

  From `backend/`, run `uv run alembic heads`, `uv run alembic history`, `uv run alembic upgrade head`, and `uv run alembic check` against the test database. Expected: one consistent head, successful upgrade, and no ungenerated metadata differences. Do not create a migration for this task.

- [ ] **Step 4: Run frontend lint and production build/type validation.**

  From `frontend/`, run:

  ```bash
  bun run lint
  bun run build
  ```

  Expected: Biome succeeds; TypeScript build validation and Vite production build succeed. Inspect status for unintended formatter or generated-client changes.

- [ ] **Step 5: Run the full Chromium Playwright suite with its dependencies.**

  Start required database, backend, and Mailpit services without deleting persistent volumes, apply migrations as needed, then from `frontend/` run:

  ```bash
  bunx playwright test --project=chromium --reporter=list
  ```

  The full suite is authoritative. Confirm its discovered tests include `dashboard.spec.ts`, `products.spec.ts`, `visualizer.spec.ts` (including result/retry), `generations-history.spec.ts` (including result/retry), `tilevision-mvp-journey.spec.ts`, and the replacement `items.spec.ts`.

- [ ] **Step 6: Perform the bounded read-only media/auth sanity audit.**

  Inspect the routes and tests without changing authorization behavior. Confirm evidence for:
  - source image owner/read-any scoping: `backend/tests/api/routes/test_visualization_projects.py::test_project_and_source_image_are_hidden_from_other_users` and owner streaming coverage;
  - result image authentication/scoping: `backend/tests/api/routes/test_generations.py::test_result_endpoint_requires_authentication` and `test_owner_and_read_any_can_read_job_and_stream_result`;
  - generation-scoped product image access through generation permissions: `test_generation_scoped_product_image_uses_generation_permissions`;
  - standalone product-image content remains authenticated/catalog-authorized: `backend/tests/api/routes/test_product_images.py::test_image_content_requires_catalog_read_and_streams_with_mime_type`;
  - list/detail/media authorization consistency using the existing history/read-any/owner tests.

  Also search tracked files for committed API keys/secrets, temporary debug logging, T24-related TODO/FIXME markers, and test-only production endpoints. This is a sanity audit, not penetration testing or a security refactor.

- [ ] **Step 7: Run repository integrity checks and report all gate results.**

  Run `git diff --check`; confirm `frontend/src/client/` is unchanged, no migration files were added, no secrets/debug logging/test-only production endpoints were introduced, and enumerate any static/type failures as pre-existing or T24 regressions with evidence.

---

## Implementation stop condition

If verification uncovers an additional genuine release blocker outside the already-approved Compose provider forwarding and Item UI retirement, stop before changing that behavior. Report the exact failing command/route/test and the smallest proposed fix, then wait for approval.
