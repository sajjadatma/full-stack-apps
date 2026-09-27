# T18 — Visualizer Stepper Flow (design)

- Status: Approved (design review complete; four revisions incorporated)
- Date: 2026-09-28
- Depends on: T10, T17
- Spec of record: `docs/tilevision-mvp.md` §5 (workflow, validation, lifecycle, result presentation)

## 1. Goal

Give an authenticated customer one place to run the whole visualizer flow —
upload a room photo, choose `FLOOR`/`WALL`, search/select an eligible product,
review, generate, and view the result — without leaving the feature, on desktop
and mobile, in English and Farsi.

## 2. Scope

In scope:

- One authenticated `/visualizer` route with a six-step Material 3 wizard:
  1. Upload Room Photo → 2. Choose FLOOR/WALL → 3. Select Product →
  4. Review Selection → 5. Generate → 6. Result.
- Searchable/filterable product selection showing image, name, size, finish, color.
- Server-side surface eligibility filtering on `GET /products/`.
- URL-recoverable navigation state.
- Full MVP result: progress polling, side-by-side before/after, download, retry.
- English/Farsi strings, responsive layout, Playwright coverage with intercepted
  generation calls, backend filter tests.

Out of scope (explicit):

- History page and any history link in T18.
- Delete generation.
- "Visualize in a room" entry from a product detail page.
- Heavy before/after comparison-slider dependency.

## 3. Locked decisions

- **Single route, no nested step routes.** `frontend/src/routes/_layout/visualizer.tsx`.
- **Recoverable URL state** via search params: `step`, `project`, `surface`,
  `product`, `job`. Only stable IDs/state; never Blob URLs, raw bytes, or signed
  temporary URLs.
- **Explicit, duplicate-safe generation creation** (revision 1).
- **Combined permissions** (revision 2).
- **Server-side eligibility filter** with explicit `is_active=true` and
  primary-image requirement (revision 3).
- **Authenticated Blob image handling** for room photo, product images, and
  results (revision 4).

## 4. Backend change

`GET /products/` (`backend/app/api/routes/products.py`) gains:

- `suitable_surface: TargetSurface | None = None` — reuse the existing
  `TargetSurface` enum rather than a duplicate `Literal`.
- Filter: JSONB containment on the existing JSON-backed field, isolated to the
  query: `sa_cast(Product.suitable_surfaces, JSONB).contains([suitable_surface.value])`.
  Applied before count and pagination, combined with `q` and other filters.
- The domain field stays `sa_type=JSON`; no model or migration change.

The visualizer always requests `suitable_surface=<FLOOR|WALL>` **and**
`is_active=true`, so users holding `products.read_any` never receive inactive
products in the picker. A product without a primary `ProductImage` is not
selectable (hidden/disabled) because T15 rejects it.

## 5. Routing, state, and guards

- `validateSearch` (zod): `step` ∈ `upload|surface|product|review|generate|result`,
  optional UUIDs `project`/`product`/`job`, optional `surface` ∈ `FLOOR|WALL`.
- `beforeLoad` requires all of: `generations.create`, `generations.read_own`,
  and (`products.read` or `products.read_any`); otherwise redirect `/`.
  Backend stays authoritative.
- `useVisualizerFlow` centralizes param updates and prerequisite rules. If a
  requested step lacks its prerequisites, redirect to the earliest valid step:
  - `surface` needs `project`; `product` needs `project` + `surface`;
    `review` needs `project` + `surface` + `product`;
    `generate` needs `project` + `surface` + `product` + `job`;
    `result` needs `job`.
- Temporary UI state (chosen file, local search text, object URLs) stays in
  component state. Browser Back/Forward moves naturally between step states.

## 6. Step behavior

1. **Upload** — validates JPEG/PNG/WebP and size; calls
   `projectsCreateVisualizationProject`. On success writes `project`, clears
   downstream params, advances to `surface`. Re-upload creates a new project.
2. **Surface** — FLOOR/WALL selection; Next disabled until chosen.
3. **Product** — `readProducts({ q, suitable_surface, is_active: true, skip, limit })`;
   debounced search, pagination, empty/loading/error states; cards show primary
   image, name, size, finish, color. Products without a primary image are
   disabled/unselectable.
4. **Review** — read-only summary (room photo, surface, product) with back-links;
   owns the explicit **Generate** button.
5. **Generate** — consumes an existing `job` only; reads/polls `readGeneration`
   via TanStack Query `refetchInterval`, stopping on terminal status. Never
   creates a job as a render effect. No valid `job` → redirect to Review.
   `COMPLETED`/`FAILED` → `step=result`. Back is disabled once a job exists.
6. **Result** — Blob from `readGenerationResult` with correct create/revoke;
   side-by-side original vs result; product + surface summary; download;
   `Start New Visualization` resets to a clean `/visualizer`. On `FAILED`, show
   the safe backend message and Retry (T16 `retryGeneration`), which replaces
   `job` with the new attempt and returns to `step=generate`; the failed attempt
   is never overwritten.

Explicit Generate flow (revision 1):

1. Clicking Generate in Review calls `createGeneration`.
2. Writes `job=<new id>`.
3. Navigates to `step=generate`.
4. Generate step polls the existing job only.

## 7. Navigation, i18n, responsiveness

- Sidebar entry "Visualizer" gated on the same combined permissions.
- Strings under `visualizer.*` plus `navigation.visualizer` in `en.json` and
  `fa.json`; RTL-safe logical properties.
- Mobile: single-column steps, compact stepper, grid on desktop.

## 8. Testing

- Backend pytest: `suitable_surface=FLOOR|WALL` returns only eligible products
  with correct `count`, combined with `q`; actionable only after count/pagination;
  products with no primary image are still returned by the API (UI disables),
  invalid enum value → 422.
- Playwright `frontend/tests/visualizer.spec.ts` (no `OPENAI_API_KEY`; generation
  endpoints intercepted with `page.route`):
  - Happy path to COMPLETED: real upload → surface → product (created via API
    with a primary image and FLOOR eligibility) → review → generate →
    PROCESSING→COMPLETED → result, before/after, download.
  - FAILED → Retry → new job → COMPLETED; failed attempt unchanged.
  - Guard: `?step=product` without `project` redirects to upload.
  - Mobile viewport pass.

## 9. Verification

- `uv run pytest -q` (backend) and `uv run ruff check/format`.
- `bun run lint` and `bun run build` (frontend).
- Regenerate the client with `scripts/generate-client.sh` after the backend
  change.
