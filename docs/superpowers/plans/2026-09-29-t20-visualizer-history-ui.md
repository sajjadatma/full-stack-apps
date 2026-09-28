# T20 Visualizer History UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let authenticated users list and revisit their own visualizer generations, compare images, and retry failed jobs when authorized.

**Architecture:** Extend the existing generation list/detail responses with a narrow current-product summary, eagerly load Product/image metadata, and stream the primary product image through a generation-authorized endpoint. Add owner-scoped history list/detail routes and extract a route-independent `GenerationResultView` shared by the visualizer and history detail. Keep image bytes authenticated and transient as Blob URLs.

**Tech Stack:** FastAPI + SQLModel + SQLAlchemy, OpenAPI generated TypeScript client, TanStack Router/Query, React, existing Material 3 components, i18next, pytest, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-29-t20-visualizer-history-ui-design.md`

## Global Constraints

- History list is owner-filtered and requires `generations.read_own`; detail/image access follows generation readable-job authorization.
- Retry requires both `generations.read_own` and `generations.create`; backend remains authoritative.
- Never broaden ordinary catalog access to inactive products; use only the generation-scoped product summary/image for history.
- Return the current referenced Product data; do not add a Product snapshot migration.
- Keep page size at 20; provide loading, empty, error, and pagination states.
- Share result presentation without coupling `GenerationResultView` to either route's navigation/search state.
- Keep authenticated image bytes out of URLs; create and revoke Blob URLs using existing image hooks/patterns.
- No generation/project deletion and no dependencies beyond the existing stack.
- Add English/Farsi strings and use responsive, RTL-safe layout.

## Review Focus

- **Foreign job IDs / another user's list data:** pin owner scoping in existing API tests and detail/image endpoint tests; the frontend never trusts route IDs as authorization.
- **Inactive referenced Products:** a generation owner can read only the Product summary/image through their generation, while ordinary product/product-image reads still deny inactive products; cover both APIs in backend tests.
- **Missing image bytes or missing primary image:** generation-scoped product image returns safe 404; history UI renders existing placeholder behavior and does not fail the page.
- **Pending/failed jobs:** result image/download are only presented for completed jobs; retry is hidden without both permissions and remains a new attempt.
- **Pagination/empty/error boundary states:** cover empty results, last-page navigation, recoverable list error, and page size 20 in frontend tests.

---

### Task 1: Generation product summary and scoped image API

**Files:**
- Modify: `backend/app/models.py` — narrow `GenerationProductSummaryPublic`, optional `GenerationJobPublic.selected_product`.
- Modify: `backend/app/api/routes/generations.py` — populated summaries, eager loading, product-image streaming endpoint.
- Test: `backend/tests/api/routes/test_generations.py`.

**Interfaces:**
- Produces `GenerationProductSummaryPublic` with `id`, `name`, `sku`, dimensions, `finish`, `material`, `color_family`, `is_active`, and optional `primary_image_id`.
- `GenerationJobPublic.selected_product` is optional so absent/deleted historical relation handling remains explicit.
- Adds `GET /api/v1/generations/{job_id}/product-image`, authorized through `_readable_job`; success is a private binary stream with the ProductImage MIME type, missing job/image/storage is a safe 404.

- [x] **Step 1: Add failing API tests** for summary serialization in list/detail, including inactive Product; authorized owner and `generations.read_any` product-image reads; denied foreign job; missing primary image/storage 404; and ordinary inactive product/image reads remain unavailable to non-privileged catalog readers.
- [x] **Step 2: Add failing list-query efficiency coverage** comparing SQL query counts for a one-job page and a multi-job page with Products/images, asserting the Product/image query count does not grow per row.
- [x] **Step 3: Run the focused tests and confirm the expected failures.**

Run: `cd backend && uv run pytest tests/api/routes/test_generations.py -q`

- [x] **Step 4: Implement the summary and endpoint.** Eager-load `GenerationJob.selected_product` and its `images` for paginated rows; select `is_primary` metadata; use the readable-job policy for the stream, not catalog permissions; do not return storage keys.
- [x] **Step 5: Rerun focused generation tests and backend formatting/lint.**

Run: `cd backend && uv run pytest tests/api/routes/test_generations.py -q && uv run ruff check app tests && uv run ruff format --check app tests`

- [x] **Step 6: Commit the backend API change.**

```bash
git add backend/app/models.py backend/app/api/routes/generations.py backend/tests/api/routes/test_generations.py
git commit -m "T20: expose generation-scoped product details"
```

### Task 2: Regenerate the frontend API client

**Files:**
- Modify generated files under: `frontend/src/client/`.
- Run: `scripts/generate-client.sh`.

**Interfaces:**
- Consumes Task 1 OpenAPI changes.
- Produces typed `GenerationJobPublic.selected_product` and `GenerationsService.readGenerationProductImage({path: {job_id}})` with binary response typing.

- [x] **Step 1: Regenerate the client** with `bash scripts/generate-client.sh`.
- [x] **Step 2: Inspect generated types/SDK** to verify summary fields and authenticated `responseType: 'blob'` operation are present; run `git diff --check`.
- [x] **Step 3: Commit generated API client changes.**

```bash
git add frontend/src/client
git commit -m "T20: regenerate client for generation history"
```

### Task 3: Extract the shared GenerationResultView

**Files:**
- Create: `frontend/src/components/Visualizer/GenerationResultView.tsx` — route-independent status/result presentation.
- Modify: `frontend/src/components/Visualizer/ResultStep.tsx` — retain visualizer route wrapper, polling, retry mutation callback, and Start New callback.
- Modify: `frontend/tests/visualizer.spec.ts` — include embedded summary and intercept the generation-scoped product image for existing result coverage.

**Interfaces:**
- `GenerationResultView` consumes `job: GenerationJobPublic`, optional `canRetry`, and optional `onRetry`; it owns the shared result display/actions only, not Start New, Back to History, TanStack Router state, or route navigation.
- For a completed job, the view loads source via the existing project source endpoint, result via `readGenerationResult`, and product image via the generation-scoped endpoint. All are authenticated Blobs with URL cleanup.
- `ResultStep` obtains the current job with `useGenerationJob(jobId)` and passes it and the optional retry action to the view; its Start New button remains in the route-specific wrapper.

- [x] **Step 1: Update the completed-result Playwright mock** to supply `selected_product`, fulfill `GET /api/v1/generations/{job_id}/product-image` with the fixture Blob, and record requests to the scoped image endpoint and normal product/product-image endpoints. Assert the product summary image is visible, the generation-scoped endpoint was requested, and ordinary catalog/product-image endpoints were not requested for that summary.
- [x] **Step 2: Run the focused visualizer test and confirm failure** because the current `ResultStep` still fetches the product through the normal product API and does not call the generation-scoped image endpoint.
- [x] **Step 3: Extract the display from `ResultStep`** into `GenerationResultView`; move product display to embedded summary and generation-scoped image endpoint; preserve existing before/after, safe failure, download, and action behavior.
- [x] **Step 4: Run all visualizer Playwright tests** and confirm existing progress/result/retry behavior remains intact.

Run: `cd frontend && bunx playwright test tests/visualizer.spec.ts --project=chromium --reporter=list`

- [x] **Step 5: Commit the shared result view.**

```bash
git add frontend/src/components/Visualizer/GenerationResultView.tsx frontend/src/components/Visualizer/ResultStep.tsx frontend/tests/visualizer.spec.ts
git commit -m "T20: extract shared generation result view"
```

### Task 4: Owner-scoped history list

**Files:**
- Create: `frontend/src/routes/_layout/generations.tsx` — authenticated permission-guarded parent route with `<Outlet />`.
- Create: `frontend/src/routes/_layout/generations.index.tsx` — list query and page state at `/generations`.
- Create: `frontend/src/components/Generations/GenerationHistoryCard.tsx` — one responsive history card.
- Modify: `frontend/src/components/Sidebar/AppSidebar.tsx` — permission-gated Generations link.
- Modify: `frontend/src/i18n/locales/en.json` and `frontend/src/i18n/locales/fa.json` — history strings.
- Generated: `frontend/src/routeTree.gen.ts` — regenerated by the router plugin.
- Test: `frontend/tests/generations-history.spec.ts` — list states and row content.

**Interfaces:**
- Route requires `generations.read_own` in `beforeLoad` and requests `readGenerations({query: {skip, limit: 20}})`.
- Card consumes one `GenerationJobPublic` plus localized date formatting and links to `/generations/$jobId`.
- Source/result thumbnails use authenticated endpoints and temporary Blob URLs; product title/details come from the embedded summary and product image comes only from the generation-scoped endpoint.

- [x] **Step 1: Add failing Playwright list tests** for loading, empty, recoverable error, 20-item pagination, last-page controls, and cards showing room/output images (output only for completed), product, surface, status, and localized date.
- [x] **Step 2: Run the focused test and verify it fails** because the history route/card is missing.
- [x] **Step 3: Implement the list route and card** with explicit loading/empty/error/pagination states and responsive card layout; add permission-gated navigation and English/Farsi labels.
- [x] **Step 4: Run the focused history Playwright test** and verify the list and authorization gate.
- [x] **Step 5: Commit the history list.**

```bash
git add frontend/src/routes/_layout/generations.tsx frontend/src/routes/_layout/generations.index.tsx frontend/src/components/Generations/GenerationHistoryCard.tsx frontend/src/components/Sidebar/AppSidebar.tsx frontend/src/i18n/locales/en.json frontend/src/i18n/locales/fa.json frontend/src/routeTree.gen.ts frontend/tests/generations-history.spec.ts
git commit -m "T20: add owner-scoped generation history"
```

### Task 5: Generation detail and permitted retry

**Files:**
- Create: `frontend/src/routes/_layout/generations.$jobId.tsx` — detail query, retry mutation, route navigation, permission checks.
- Test: `frontend/tests/generations-history.spec.ts` — detail, owner isolation, and retry conditions.
- Generated: `frontend/src/routeTree.gen.ts` — route plugin output.

**Interfaces:**
- Detail validates `$jobId` as UUID in TanStack Router params and calls authenticated `readGeneration`.
- Detail passes job and actions to `GenerationResultView`; back-to-history and retry navigation stay in the route.
- Retry calls `GenerationsService.retryGeneration({path: {job_id}})` only when `generations.read_own` and `generations.create` are present; success navigates to `/generations/$jobId` with the new ID.

- [x] **Step 1: Add failing detail Playwright tests** for completed before/after rendering, selected-product summary/image, target surface/date/status, failed safe error, retry available only to permitted users, and retry navigation to a different job ID.
- [x] **Step 2: Run focused detail tests and verify expected failures.**
- [x] **Step 3: Implement the detail route** with loading/error/not-found states, shared result view, permission-conditional retry, history navigation, and retry-to-new-detail navigation.
- [x] **Step 4: Verify a foreign job ID receives only the backend not-found outcome** and no image/content is rendered; keep backend ownership as the authority.
- [x] **Step 5: Run focused generation history and visualizer Playwright suites.**

Run: `cd frontend && bunx playwright test tests/generations-history.spec.ts tests/visualizer.spec.ts --project=chromium --reporter=list`

- [x] **Step 6: Commit the detail route.**

```bash
git add 'frontend/src/routes/_layout/generations.$jobId.tsx' frontend/src/routeTree.gen.ts frontend/tests/generations-history.spec.ts
git commit -m "T20: add generation history detail and retry"
```

### Task 6: Full T20 verification

**Files:** No additional files unless a focused regression is found.

- [x] **Step 1: Run backend tests and Ruff.**

Run: `cd backend && uv run pytest -q && uv run ruff check app tests && uv run ruff format --check app tests`

- [x] **Step 2: Run frontend lint/build.**

Run: `cd frontend && bun run lint && bun run build`

- [x] **Step 3: Run focused generation history and visualizer Playwright suites.**

Run: `cd frontend && bunx playwright test tests/generations-history.spec.ts tests/visualizer.spec.ts --project=chromium --reporter=list`

- [x] **Step 4: Run `git diff --check` and review final status/diff** to confirm only T20 implementation and approved generated API/route files are changed.

## Self-review coverage map

- Backend summary, inactive product visibility, and bounded image auth/MIME/404: Task 1.
- Query efficiency: Task 1 list-query comparison test.
- OpenAPI/client synchronization: Task 2.
- Shared result component with visualizer regression protection: Task 3.
- Owner list, required content, pagination, loading/empty/error, responsive/i18n: Task 4.
- Detail comparison, foreign ID denial, safe failure, retry permissions/new job: Task 5.
- Full suite/lint/build/Playwright/diff verification: Task 6.
