# T20 — Visualizer History UI Design

- Status: Conversational design approved; written spec pending review
- Date: 2026-09-29
- Depends on: T16, T19
- Product contract: `docs/tilevision-mvp.md`, especially §§4.4, 5.1, 5.4–5.5, 8.1–8.2

## 1. Goal and scope

Let an authenticated user revisit their own visualizer generations, inspect
their room and generated images, compare completed results, and retry failed
jobs when authorized.

In scope:

- Authenticated `/generations` history list and `/generations/$jobId` detail.
- Twenty jobs per page, with responsive cards showing room image, output image
  when completed, selected product, target surface, status, and date.
- Detail view with before/after comparison, selected product summary, target
  surface, status, result download, safe failure message, and authorized retry.
- Generation-scoped selected-product summary and primary-image delivery so
  inactive products remain represented in their existing history without
  becoming generally readable in the catalog.
- Loading, empty, error, and pagination states; English/Farsi localization.
- Focused backend and Playwright coverage.

Out of scope:

- Deleting generation jobs or visualization projects.
- Product snapshots/migrations. History shows currently referenced Product
  data; later product edits may affect its displayed name/specification.
- Changes to generation processing, AI provider behavior, authorization
  foundations, or unrelated routes.

## 2. Existing architecture and constraints

- `GET /api/v1/generations/` already returns a paginated `{data, count}` list,
  newest first, filtered to projects owned by the authenticated user and
  requiring `generations.read_own`.
- `GET /api/v1/generations/{job_id}` and `/result` use the shared readable-job
  check, allowing the owner with `generations.read_own` or privileged readers
  with `generations.read_any`.
- `GET /api/v1/visualization-projects/{project_id}/source-image` is
  authenticated and owner-scoped.
- Normal product and product-image reads hide inactive products from ordinary
  catalog readers. T20 must not broaden those permissions.
- The generated client and TanStack Query are the frontend data path. Routes
  live under the authenticated `_layout` route; localized strings live in
  `en.json` and `fa.json`.
- The existing T19 result page handles authenticated source/result Blobs,
  before/after presentation, failure recovery, retry, and download. T20 will
  extract a shared presentational result component rather than make the
  history route depend on visualizer wizard search state.

## 3. Backend/API design

### 3.1 Generation response product summary

Extend `GenerationJobPublic` with an optional, narrow read-only
`selected_product` summary containing:

- `id`, `name`, `sku`
- `width_mm`, `height_mm`, `thickness_mm`
- `finish`, `material`, `color_family`
- `is_active`
- `primary_image_id` when one exists

Return the summary in list and detail responses using the current referenced
Product record, including when inactive. Do not add a stored Product snapshot
or expose the full Product management schema.

Load product and primary-image metadata with eager loading/joins for the
paginated history query; do not issue one Product query per job. Existing count,
ordering, pagination, and owner filter remain unchanged.

### 3.2 Generation-scoped product image

Add authenticated `GET /api/v1/generations/{job_id}/product-image`:

- Reuse the readable-job authorization policy: owner with
  `generations.read_own` or privileged reader with `generations.read_any`.
- Resolve the referenced Product's primary ProductImage, including for an
  inactive Product, and stream its bytes with the persisted content type.
- Never return storage keys or grant general inactive-product access.
- Return a safe 404 if the referenced ProductImage or its stored bytes are
  unavailable.
- Apply private/no-store and content-sniffing protections consistent with
  other private image streams.

This is an API contract addition. Regenerate the frontend client; no database
migration is required.

## 4. Frontend design

### 4.1 Routes, permissions, and navigation

- Add authenticated `/generations` and `/generations/$jobId` routes.
- History route requires `generations.read_own`; backend ownership filtering is
  authoritative. A guessed foreign job ID must render the backend's not-found
  behavior, never another user's content.
- Show a `Generations` sidebar link only for `generations.read_own` users.
- Retry is available only when the user has both `generations.read_own` and
  `generations.create`; the backend retry endpoint remains authoritative.

### 4.2 History list

- Fetch 20 jobs per page using the existing `readGenerations` endpoint and its
  `skip`/`limit` parameters.
- Each card shows the authenticated room-photo thumbnail, selected product
  name/details from the embedded summary, target surface, status, localized
  creation date, and authenticated result thumbnail only for `COMPLETED` jobs.
- Use the generation-scoped product-image endpoint for product thumbnails;
  never fall back to normal Product/ProductImage reads for inactive products.
- Selecting a card navigates to `/generations/$jobId`.
- Include explicit loading, empty, recoverable error/retry, and pagination
  states. Use responsive cards and RTL-safe logical layout.

### 4.3 Shared result presentation and detail

Extract a route-independent `GenerationResultView` from the T19 result UI. It
receives generation data, image-fetch callbacks/identifiers, and optional
actions; it does not read or mutate route search state. It presents:

- Status and timestamps.
- Authenticated original room image and generated result in a responsive
  before/after comparison when completed.
- Embedded selected-product details and its generation-scoped primary image.
- Target surface, result download, and safe failure information.
- Retry action only when supplied by the containing route and authorized by
  frontend permission state.

The Visualizer `ResultStep` and history detail route both use this component.
Route-specific navigation stays outside it:

- Visualizer route owns wizard URL/search updates and Start New Visualization.
- History detail route owns return-to-history navigation and retry redirect to
  the new job's detail URL.

The detail route loads its job through `readGeneration`; source and result image
bytes use the existing authenticated project endpoint and generation result
endpoint as Blobs. Temporary object URLs are revoked using the existing hook.

## 5. Error and authorization behavior

- History list API errors show a retryable error state; no partial foreign data
  is rendered.
- Missing/unavailable source, result, or product image uses an existing image
  fallback. Failed jobs do not request or offer a result image/download.
- Foreign or missing job details follow the backend's 404 response behavior.
- Retry control is hidden without both required permissions; retry API failures
  are shown safely, and successful retry navigates to the new job without
  modifying the failed attempt.
- Product summary/image access is scoped to readable generations, not general
  catalog permission for inactive Products.

## 6. Tests

### Backend

- Generation list/detail include the selected-product summary for active and
  inactive referenced products.
- Product-image endpoint streams the expected primary image and content type
  for an authorized owner, supports `generations.read_any`, and denies/404s
  unauthorized or missing jobs/images according to the existing policy.
- Owner-scoped history does not return another user's jobs.
- Verify list query loading does not regress to per-row Product queries (use
  query-count/instrumentation coverage if stable in the existing test harness).

### Frontend Playwright

- History renders room/result thumbnails, product/surface/status/date, handles
  pagination and empty/error states, and opens a detail comparison.
- Inactive-product summary and thumbnail use generation-scoped endpoints.
- Failed detail exposes Retry only for permitted users; retry navigates to the
  new job detail and leaves the failed job available.
- A user cannot view another user's detail; API authorization remains the
  security boundary.
- Cover responsive history/detail layout and English/Farsi labels as practical
  within focused tests.

## 7. Verification

- Backend focused generation-route tests and Ruff checks.
- Frontend lint and production build.
- Focused Playwright history/detail tests, including owner isolation and retry
  behavior.
- `git diff --check`.

## 8. Review notes / decisions

- History displays live Product data, not a historical snapshot; this is an
  explicit T20 decision.
- Do not add delete controls even though deletion appears in the broader MVP
  history contract; T20's approved task scope does not include deletion.
- No changes to result/polling/retry behavior beyond extracting the shared view
  and wiring the detail route to the existing T16 endpoint.
