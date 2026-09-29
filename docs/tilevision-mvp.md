# TileVision — MVP Product Domain

- **Document ID:** TV-MVP-000
- **Title:** TileVision MVP Product Domain (source of truth)
- **Version:** 1.3
- **Status:** Approved — authoritative for all TileVision tasks (T01+)
- **Owner:** Product
- **Date:** 2026-09-30
- **Applies to:** `full-stack-fastapi-template` (branch `TileVision`)
- **Supersedes:** none. This document is the single source of truth for the
  TileVision product domain. Where a later task and this document disagree,
  this document wins until it is amended with a version bump.

> How to use this document: every later task (models, APIs, frontend, tests)
> must conform to the vocabulary, entities, workflow, and rules defined here.
> Section 11 lists the assumptions and open questions that later tasks own.

---

## 1. Purpose

TileVision is a tile and ceramic catalog with an AI room visualizer, built for
tile showrooms, distributors, and their customers.

Two problems are solved:

1. **Catalog management.** Staff maintain the product catalog — what the tile
   is, its technical specifications, price, stock, and images — in one
   authoritative place.
2. **"What will it look like in my room?"** A customer uploads a photo of their
   own room and sees the selected product applied to the floor or the wall,
   without hiring a designer or installing the product. The preview must look
   like the *same room* with only that surface replaced.

The value is confidence: the customer recognizes their room and judges the
tile in context, and the showroom shortens the path from interest to order.

**Success looks like:** a customer uploads a room photo, picks a product,
generates a preview in which the room is visibly unchanged except the chosen
surface — and can return later to view that result.

---

## 2. Users and roles

### 2.1 Personas

| Persona | Description | Primary jobs |
|---|---|---|
| **Customer** | A registered, logged-in shopper. The default role for new accounts. | Browse the published catalog, view product details, upload a room photo, generate previews, revisit and delete their own generations. |
| **Catalog staff** | Showroom/warehouse staff who maintain the catalog. | Create and edit products, set pricing and stock, upload and order product images, publish/archive products. |
| **Administrator** | Owns the system: accounts, roles, and oversight. | Manage users and roles, grant staff access, inspect all products and generations for support/audit. |

The AI visualizer is the customer's tool. Staff and administrators may use it
too (they are authenticated users), but catalog management is staff-only.

### 2.2 Roles mapped to the existing RBAC model

TileVision reuses the application's existing authorization model
(`backend/app/core/rbac.py`, `docs/rbac.md`): **exactly one role per user**,
roles grant **application-defined permission codes**, authorization is enforced
by the backend on every request, and the frontend only hides controls it cannot
use.

| Persona | Role (MVP) | Notes |
|---|---|---|
| Administrator | protected `superuser` system role | Full access; unchanged from today. |
| Catalog staff | a `staff` system role (to be introduced) | Catalog management permissions; no account administration. |
| Customer | the default `user` system role | Browsing + visualizer + own generations. |

The following permission codes are the **proposed** MVP additions to the
catalog. The task that implements RBAC changes finalizes them; until then they
are the contract every other task codes against.

| Area | Permission code | Meaning |
|---|---|---|
| Products | `products.read` | Read the published catalog (customers). |
| Products | `products.read_any` | Read all products including drafts/archived (staff/admin). |
| Products | `products.create` | Create products. |
| Products | `products.update` | Edit product details, specs, pricing, and stock. |
| Products | `products.delete` | Delete products (guarded, see §4.1). |
| Images | `products.manage_images` | Upload, reorder, and delete product images. |
| Generations | `generations.create` | Create a generation (upload a room photo and run the visualizer). |
| Generations | `generations.read_own` | Read generations the user owns. |
| Generations | `generations.read_any` | Read any generation (support/audit). |
| Generations | `generations.delete_own` | Delete generations the user owns. |
| Generations | `generations.delete_any` | Delete any generation (support/audit). |

**Authorization rules**

- All visualizer and generation endpoints require authentication.
- Ownership is enforced server-side, exactly like the existing items domain
  (`*_own` vs `*_any`; see `docs/rbac.md`).
- Customers can never read another user's room photos or generations.
- Room photos are private to their owner; product images are public to any
  authenticated user.
- Frontend controls are conveniences only; the backend is authoritative.

---

## 3. Glossary

| Term | Meaning |
|---|---|
| **Product** | A sellable tile/ceramic item with one SKU, technical specifications, price, stock, and images. |
| **SKU** | The staff-facing unique product code. |
| **Surface** | Which part of the room the product is applied to: `FLOOR` or `WALL`. Exactly one per generation job. |
| **Room photo** | The customer's uploaded photograph of a real room. It is the source image stored on a `VisualizationProject` and is private to the owner. |
| **VisualizationProject** | A user-owned workspace that stores the source room image and groups the generation jobs run against it. |
| **GenerationJob** | One request to apply one product to one surface of one room photo, producing one result image. The unit of history. |
| **Result image** | The AI-produced image: the original room with only the selected surface replaced. |
| **Preservation** | The requirement that everything except the selected surface is unchanged from the original room photo. |
| **Fail closed** | When the system cannot meet the preservation rules, it fails the generation with an explicit error instead of returning a degraded or misleading image. |
| **Provider** | The external (or self-hosted) AI image-editing service that performs the surface replacement. Swappable, configured server-side. |

---

## 4. Domain entities

Entities are listed with the attributes MVP requires. Storage types and exact
SQLModel definitions are decided by the implementing task; the **names and
meanings below are the contract**.

### 4.1 Product

A product is one SKU of tile/ceramic.

| Attribute | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Primary key. |
| `sku` | string(64) | yes | Unique, indexed, staff-facing code. |
| `name` | string(255) | yes | Display name. |
| `brand` | string(120) | no | Manufacturer/brand. |
| `collection` | string(120) | no | Series/collection name. |
| `description` | text | no | Marketing/description copy. |
| `category` | enum | yes | `floor_tile`, `wall_tile`, `mosaic`, `decorative`. |
| `material` | enum | yes | `ceramic`, `porcelain`, `stone`, `glass`, `other`. |
| `suitable_surfaces` | set of `FLOOR`/`WALL` | yes | At least one. Drives visualizer eligibility. |
| `width_mm` | integer | no | Nominal width. |
| `height_mm` | integer | no | Nominal height. |
| `thickness_mm` | integer | no | Nominal thickness. |
| `pieces_per_box` | integer | no | Packaging. |
| `sqm_per_box` | decimal | no | Coverage in square meters. |
| `kg_per_box` | decimal | no | Shipping weight. |
| `finish` | enum | no | `matte`, `glossy`, `polished`, `satin`, `textured`, `anti_slip`. |
| `color` | string(60) | no | Primary color/name. |
| `look` | string(60) | no | Visual family, e.g. marble, wood, stone, concrete. |
| `rectified` | boolean | no | Precision-cut edges. |
| `water_absorption_pct` | decimal | no | Technical spec. |
| `pei_rating` | enum | no | Wear rating `I`..`V`. |
| `slip_resistance` | string(16) | no | e.g. `R9`..`R13` or DCOF value. |
| `frost_resistant` | boolean | no | Technical spec. |
| `suitable_outdoor` | boolean | no | Technical spec. |
| `fire_rating` | string(32) | no | Technical spec. |
| `chemical_resistance` | string(32) | no | Technical spec. |
| `currency` | string(3) | yes when priced | ISO 4217; defaults to the app/company currency. |
| `price_per_unit` | decimal | no | Sell price. |
| `price_unit` | enum | yes when priced | `m2`, `box`, `piece`. |
| `compare_at_price` | decimal | no | Optional "was" price. |
| `stock_quantity` | decimal | yes | Non-negative. |
| `stock_unit` | enum | yes | `m2`, `box`, `piece`. |
| `low_stock_threshold` | integer | no | For the derived availability label. |
| `status` | enum | yes | `draft`, `published`, `archived`. |
| `created_at` / `updated_at` | timestamp | yes | UTC. |

**Derived availability** (not stored as the source of truth):
`out_of_stock` when `stock_quantity == 0`; `low_stock` when
`0 < stock_quantity <= low_stock_threshold`; otherwise `in_stock`.

**Product rules**

- Only `published` products appear in the customer catalog and can be used for
  a generation.
- A product that is `archived` stays readable for staff and for existing
  generations' history, but is no longer selectable.
- Publishing a product requires at least one image and at least one suitable
  surface (see §4.2 and §5.2).
- Deleting a product is restricted while generation jobs reference it; staff
  **archive** instead of delete for products with history. (The exact
  constraint is finalized by the implementing task; archiving is the
  recommended path.)

### 4.2 Product image

A product has zero or more images; the order and the primary image matter to
the catalog and the visualizer.

| Attribute | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Primary key. |
| `product_id` | UUID | yes | FK → product, cascade delete. |
| `storage_key` | string | yes | Pointer to stored bytes. |
| `url` | string | yes | Delivery URL. |
| `alt_text` | string(255) | no | Accessibility. |
| `sort_order` | integer | yes | Display order. |
| `is_primary` | boolean | yes | Exactly one primary per product. |
| `content_type` | string(64) | yes | Validated MIME. |
| `width_px` / `height_px` | integer | no | Intrinsic size. |
| `created_at` | timestamp | yes | UTC. |

**Image rules**

- The primary image is the reference the visualizer shows to the customer and
  should depict the product's surface appearance clearly.
- At least one image is required to publish a product.
- Uploads accept JPEG, PNG, and WebP only. SVG and animated formats are
  rejected. Size and dimension limits are defined in §9.

### 4.3 VisualizationProject

A user-owned workspace. It stores the source room image and groups the
generation jobs run against that room.

| Attribute | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Primary key. |
| `owner_id` | UUID | yes | FK → user; cascade delete. |
| `name` | string(255) | no | Optional label for the project. |
| `source_image_key` | string | yes | Pointer to the stored room photo bytes. |
| `source_image_content_type` | string(64) | yes | Validated MIME. |
| `source_image_size_bytes` | integer | yes | Validated against the limit. |
| `source_image_width_px` / `source_image_height_px` | integer | yes | Validated; orientation normalized. |
| `source_image_url` | string | no | Owner-only delivery URL. |
| `created_at` / `updated_at` | timestamp | yes | UTC. |

**Room photo rules**

- The source room image belongs to its `VisualizationProject`; there is no
  separate room photo entity.
- Private to `owner_id`; never served publicly.
- JPEG, PNG, WebP only. Size/dimension limits in §9.
- Stored without relying on client-declared content type (server confirms).
- Deleted with its owning project, and the project is deleted when the owning
  account is deleted.
- A project may own many `GenerationJob`s; a user may own many projects.

### 4.4 GenerationJob

One visualizer run. This is the unit of history. It belongs to exactly one
`VisualizationProject`.

| Attribute | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Primary key. |
| `project_id` | UUID | yes | FK → visualization project; cascade delete. |
| `selected_product_id` | UUID | yes | FK → product (see deletion rule in §4.1). |
| `target_surface` | enum | yes | `FLOOR` or `WALL`. Exactly one. |
| `status` | enum | yes | `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`. |
| `provider` | string(64) | no | Provider name. |
| `provider_model` | string(120) | no | Model/version for audit. |
| `provider_params` | JSON | no | Non-secret parameters used. |
| `prompt_version` | string(64) | no | Prompt revision used for reproducibility. |
| `output_image_key` / `output_image_url` | string | yes when completed | The result. |
| `output_image_content_type` | string(64) | no | Validated MIME of the result. |
| `output_image_width_px` / `output_image_height_px` | integer | yes when completed | Must equal the room photo's dimensions. |
| `error_code` | string(64) | yes when failed | See §5.5. |
| `error_message` | string(500) | no | Safe, non-PII message. |
| `retry_count` | integer | yes | Defaults to `0`. |
| `created_at` / `updated_at` | timestamp | yes | UTC; `created_at` is when requested. |
| `started_at` / `completed_at` | timestamp | no | Lifecycle timestamps. |

**GenerationJob rules**

- A generation job is immutable except for its lifecycle fields
  (`status`, output fields, timestamps, error fields). It is never edited back
  to an earlier status.
- One generation job produces exactly one result image and corresponds to
  exactly one target surface.
- A failed generation job can be retried only by creating a **new** generation
  job; failures never mutate into success.
- History is owner-scoped through the owning project's `owner_id`;
  `generations.read_any` allows staff/administrators to view for support, never
  to modify.

---

## 5. AI room visualizer

### 5.1 Workflow (customer)

1. **Open the visualizer.** The user is authenticated and opens the Visualizer
   (entry point: the visualizer route, or "Visualize in a room" on a product
   detail page with the product preselected).
2. **Upload a room photo.** The user provides a photograph of a real room. The
   system validates it (§5.2) and normalizes orientation.
3. **Choose the surface.** The user selects exactly one of `FLOOR` or `WALL`.
   This choice determines which region the AI may change and drives product
   eligibility.
4. **Select a product.** The user picks a product from the published catalog.
   The UI only offers products whose `suitable_surfaces` includes the chosen
   surface and that have at least one image. A product unsuitable for the
   chosen surface is not selectable and, if forced via the API, is rejected.
5. **Generate.** The user submits. The backend creates a `GenerationJob` in
   `PENDING` and begins processing. The UI shows progress on that generation
   job.
6. **View the result.** On success (`COMPLETED`) the UI shows the result image,
   with a before/after comparison against the original room photo, and offers
   download. On failure (`FAILED`) the UI shows the failure reason and offers
   retry (a new generation job).
7. **Revisit history.** The user opens the generation history, sees their past
   generation jobs (thumbnail, product, target surface, status, date), opens
   any past result, and may delete their own generation jobs.

Entry-point state (product preselected, surface preselected) may be carried
from the catalog, but each generation stores its own final `surface` and
`product_id`; later changes to a product never alter an existing generation.

### 5.2 Input validation

| Input | Rule |
|---|---|
| Room photo format | JPEG, PNG, or WebP. Anything else is rejected before processing. |
| Room photo size | Within the configured maximum (see §9). |
| Room photo dimensions | At least the configured minimum on the shorter side; at most the configured maximum. |
| Surface | Exactly one of `FLOOR`, `WALL`. Missing or unknown values are rejected. |
| Product | Must exist, be `published` at submit time, have at least one image, and `suitable_surfaces` must include the chosen surface. |
| Authorization | Authenticated user with `generations.create`. |

Validation failures return a clear error and never create a `COMPLETED`
generation job.

### 5.3 Generation lifecycle

```
PENDING ──► PROCESSING ──► COMPLETED
                  └──────► FAILED
```

- **PENDING**: record created; not yet sent to the provider.
- **PROCESSING**: provider call in flight (the only long-running state).
- **COMPLETED**: provider execution succeeded; the non-empty output has a
  supported image MIME type, matches the source room dimensions, is stored, and
  the terminal job update was persisted. This status does **not** mean that
  preservation outside the target surface was mechanically verified (§6.4).
- **FAILED**: no usable result; `error_code` explains why.

Transitions are one-way. A `GenerationJob` in `COMPLETED` or `FAILED` is
terminal. Processing is asynchronous from the user's perspective: the UI
observes progress (polling the generation job resource is acceptable for MVP)
and the user may leave and return later.

**MVP execution limitation:** generation currently uses process-local
background tasks. A server restart can leave a job in `PENDING` or
`PROCESSING`; durable queue/recovery is deferred.

### 5.4 Result presentation

- The result is shown at the room photo's aspect ratio and dimensions.
- A before/after comparison (original vs result) is available, so the
  preservation of the untouched regions is visible.
- The result can be downloaded.
- The generation detail shows the product (name + primary image), the chosen
  surface, status, and timestamp.

### 5.5 Failure handling

Failed generation jobs store a stable `error_code`. MVP codes:

| `error_code` | Meaning |
|---|---|
| `invalid_room_photo` | File failed format/size/dimension validation. |
| `surface_not_detected` | The requested surface could not be identified in the photo. |
| `unsuitable_product` | Product is unpublished, image-less, or not suitable for the surface. |
| `provider_error` | Provider returned an error. |
| `provider_timeout` | Provider did not respond within the timeout. |
| `content_rejected` | Provider refused the content (safety/quality policy). |
| `no_change_detected` | The result was effectively identical to the original (nothing was applied). |
| `preservation_failed` | The result changed regions outside the selected surface beyond tolerance. |
| `internal_error` | Unexpected server error. |

Failure rules:

- Failures never yield a result image or a download.
- The failure message shown to the user is safe and contains no provider
  internals or PII.
- Retrying creates a new generation; the failed record remains in history.

---

## 6. AI preservation rules

These rules are the core product guarantee and are binding on the AI step,
the backend checks, and QA.

### 6.1 What must change

1. **Only the selected surface.** If the user chose `FLOOR`, only the floor
   region changes. If the user chose `WALL`, only the wall region changes.
2. **The product must be recognizable.** The changed surface must show the
   selected product's pattern, color, finish, and texture.
3. **Realistic tiling.** The product is rendered with:
   - correct scale relative to the room,
   - perspective and vanishing points consistent with the original camera,
   - grout lines/joints where the product implies them,
   - shading, shadows, and reflections consistent with the scene's existing
     lighting.

### 6.2 What must not change

4. **Every other region.** The non-selected surface (walls when the floor is
   chosen; floor when the wall is chosen), ceiling, baseboards/skirting,
   doors, windows, furniture, rugs, plants, decor, appliances, people, and
   pets must remain visually unchanged.
5. **Camera geometry.** Viewpoint, perspective, horizon, framing, orientation,
   aspect ratio, and pixel resolution must match the original room photo. The
   result image's width and height must equal the original's.
6. **Global lighting and color.** No global relighting, exposure, white
   balance, saturation, or color-grade changes to unchanged regions.
7. **No additions or removals.** No added or removed objects, architectural
   elements, text, watermarks, logos, or people.
8. **Surface boundaries.** The changed region must follow the original
   boundaries (floor–wall junction, baseboard, thresholds). Tile texture must
   not bleed onto walls, furniture, or ceilings, and the original surface must
   not leak into the tiled region.
9. **Photographic realism.** The result must read as a photograph of the same
   room, not an illustration or a hard-pasted composite; edges must be blended
   and shadows/reflections on the new surface plausible.

### 6.3 Fail-closed rule

10. The preservation rules in §6.2 remain mandatory instructions to the image
    provider. The MVP currently cannot mechanically determine whether the
    provider preserved every non-target pixel. `COMPLETED` reflects successful
    provider execution plus output format, dimension, storage, and terminal
    persistence checks described in §5.3; it is not a preservation
    verification result.
11. A result that is effectively identical to the original is a failure
    (`no_change_detected`), not a success.
12. The original room photo is never modified or overwritten; the result is a
    new, separate image.

### 6.4 Verification of preservation

- **Mechanical preservation verification (deferred).** The current MVP has no
  target-surface mask, segmentation, or preservation comparator. It therefore
  cannot mechanically compare unchanged pixels outside the requested surface,
  and a `COMPLETED` job must not claim that such a comparison passed. Add this
  verification when masks/segmentation and a target-region comparator are
  available. At that point, outside-region differences must remain below a
  configured tolerance and target-region differences must exceed a configured
  minimum; failures must use `preservation_failed` or `no_change_detected`.
- **Golden-example QA (required for product quality).** Human side-by-side
  review remains useful, but it is not represented as a backend verification
  score or persisted as a preservation result in the MVP.

### 6.5 Auditability

Each generation records the provider, model/version, and non-secret parameters
so a result can be explained and reproduced where the provider allows it.

---

## 7. MVP scope

### 7.1 In scope

- **Catalog (staff):** create, read, update, archive/delete products; all
  attributes in §4.1; pricing and stock; upload, reorder, set primary, and
  delete product images.
- **Catalog (customer):** browse and search published products; product detail
  with images, specifications, price, and availability.
- **Room photos:** upload, validate, store privately, and delete.
- **Visualizer:** surface selection (`FLOOR`/`WALL`), product selection with
  suitability filtering, generation, progress, result display, before/after
  comparison, and download.
- **History:** owner-scoped list and detail of past generation jobs; delete own
  generation jobs; staff read-any for support.
- **Preservation:** T14 encodes the §6 rules in provider instructions; MVP
  completion validates output format, dimensions, storage, and persisted state
  but does not mechanically verify non-target pixels (§6.4).
- **Authorization:** the roles and permission codes in §2.2, enforced by the
  backend.
- **Localization:** all new UI in English and Farsi, with correct RTL layout.
- **Quality:** backend API tests and Playwright flows for the MVP paths.

### 7.2 Non-goals (explicit)

- **Template Item domain:** Items are not part of the TileVision product UI.
  The legacy Item backend model, table/data, API, and migrations remain
  temporarily for compatibility; they are not a TileVision catalog surface.
- Applying the product to **both** floor and wall in a single generation
  (multi-surface runs are out of scope).
- **Manual masking** or region editing by the user; surface region selection
  is automatic from the chosen `FLOOR`/`WALL`.
- **3D rendering**, room measurement, floor-plan import, or AR/preview-in-place.
- **Product variants** (per-size/per-color SKUs), **multi-currency**,
  **multi-warehouse**, supplier/purchase-order management, barcodes, or ERP
  integration.
- **Commerce:** cart, checkout, payments, orders, shipping, quotations, or
  invoices.
- **Anonymous/public visualizer:** login is required.
- **Social features:** sharing, likes, comments, public galleries.
- **Recommendations/personalization** and automated product import/scraping.
- **Multiple result variants** per generation; one generation yields one
  result.
- **Video** generation or animated previews.
- **Provider marketplace / model training / fine-tuning**; a single configured
  provider.
- **Watermarking or branding** of results.
- **Native mobile apps**, offline mode, or real-time collaboration.
- **Changing the existing authentication, RBAC, theming, i18n, or generated
  API-client foundations** — these are reused, not rebuilt.
- **Analytics/reporting dashboards** beyond the generation history.

---

## 8. Fit with the existing architecture

TileVision reuses the project's foundations. Implementations must fit these
patterns rather than introduce parallel ones.

### 8.1 Backend

- **Models:** SQLModel entities in `backend/app/models.py` (or a domain module)
  following existing conventions (UUID primary keys, `created_at`, relationship
  names). Pydantic schemas for create/update/public variants as done today.
- **Migrations:** an Alembic migration under
  `backend/app/alembic/versions/` per schema change (no manual DDL).
- **Routes:** routers under `backend/app/api/routes/` (e.g. `products.py`,
  `generations.py`), mounted in `backend/app/api/main.py`.
- **Authorization:** permission constants and policy helpers in
  `backend/app/core/rbac.py`; request dependencies in `backend/app/api/deps.py`,
  mirroring the items ownership patterns (`*_own` / `*_any`).
- **Response shape:** list endpoints keep the existing `{ "data": [...],
  "count": N }` envelope.
- **API contract → client:** after any API change, regenerate the frontend
  client with `scripts/generate-client.sh` so `frontend/src/client` stays in
  sync.

### 8.2 Frontend

- **Routing:** TanStack Router routes under `_layout` (authenticated), e.g.
  `/catalog`, `/catalog/$productId`, `/visualizer`, `/generations`; staff
  management under the admin area. Route `beforeLoad` guards mirror the
  existing permission checks.
- **Data:** TanStack Query with the generated client; invalidate the relevant
  query keys after mutations.
- **UI:** the project's Material 3 design system and shared components;
  destructive actions confirmed; loading/empty/error states provided.
- **Testability:** stable `data-testid` hooks for Playwright.
- **i18n:** all strings in `frontend/src/i18n/locales/en.json` and `fa.json`,
  with logical-direction (RTL-safe) styling.

### 8.3 Media storage

Product images and room photos need persistent storage.

- **MVP:** a small storage interface (`save`, `read`, `delete`, with
  content-type and size validation) backed by a persistent local volume;
  bytes are not stored in the database. Room photos are served only to their
  owner; product images to any authenticated user.
- **Non-goal for MVP:** object storage/CDN and signed-URL delivery. Choosing a
  storage backend is an open question (§11).

### 8.4 AI provider

- The visualizer talks to a **provider-agnostic interface**: given the room
  photo, the product reference (primary image + relevant specs), the chosen
  surface, and parameters, it returns a single edited image plus, when
  available, a mask of the changed region.
- The provider is selected **server-side** via configuration. No provider
  credentials or provider-specific fields ever reach the browser.
- Bounded timeouts; a timeout yields `provider_timeout`. Retry API/behavior is
  deferred.
- Mechanical preservation verification is deferred because the current
  provider interface supplies no target mask and no local comparator exists
  (§6.4). The preservation instructions in §5–§6 remain mandatory.

---

## 9. Non-functional requirements

- **Security:** server-side validation of every upload (content sniffing, not
  the client's declared type); authorization and ownership enforced on every
  request; no provider secrets in the frontend.
- **Privacy:** room photos may show private spaces or people. They are
  private, never public, deletable by the owner, and removed when the account
  is deleted. Logs must not contain image bytes or PII.
- **Limits (configurable):** room photo and product image max size and
  dimension bounds; allowed formats (JPEG/PNG/WebP); a per-user cap on
  concurrent generations and a daily generation cap to protect provider cost.
  Exact numbers are set by the implementing task.
- **Performance:** catalog lists are paginated; images have thumbnails for
  lists; generation is long-running and never blocks the UI.
- **Observability:** structured lifecycle logs for generations (state changes,
  error codes, provider latency) without image content.
- **Compatibility:** PostgreSQL + Alembic, the existing test harnesses
  (pytest for backend, Playwright for frontend), and the existing dev/deploy
  compose setup.

---

## 10. MVP acceptance criteria

Numbered and independently verifiable.

- **AC-1 — Catalog management.** Catalog staff can create, read, update,
  archive, and delete products with the §4.1 attributes, prices, stock, and
  images; customers cannot.
- **AC-2 — Catalog browsing.** A customer can browse/search the published
  catalog and open a product detail showing images, specifications, price, and
  availability. Draft/archived products are invisible to customers.
- **AC-3 — Room photo upload.** A logged-in customer can upload a valid room
  photo; invalid format/size/dimensions are rejected with a clear message.
- **AC-4 — Generation.** A customer can choose `FLOOR` or `WALL`, select a
  surface-suitable published product, and generate a preview. The result's
  dimensions and orientation equal the original's.
- **AC-5 — Preservation.** T14 instructions encode the §6.2 preservation rules
  and the provider is expected to follow them. MVP `COMPLETED` status does not
  mechanically certify preservation outside the target surface; mechanical
  verification is deferred until target masks/segmentation and a comparator
  are available. Invalid outputs still fail rather than completing.
- **AC-6 — History.** A customer can list their generation jobs, reopen a past
  result (before/after), and delete their own generation jobs; another customer
  cannot see them.
- **AC-7 — Authorization.** Permission codes in §2.2 are enforced by the
  backend; unauthorized requests receive 403 and cross-user access is denied.
- **AC-8 — Localization.** All new UI is available in English and Farsi with
  correct RTL layout.
- **AC-9 — No regressions.** Existing authentication, RBAC, admin, settings,
  and retained legacy Item backend/API compatibility tests continue to pass.
  The retired template Item management UI is not required to remain exposed.

---

## 11. Assumptions and open questions

Assumptions are flagged, not silently decided. Each is owned by the task that
implements the relevant area.

- **A-1 → OQ-1 (AI provider/model).** Assume a swappable provider interface;
  the specific provider/model is undecided.
- **A-2 → OQ-2 (media storage).** Assume the local-volume storage interface in
  §8.3 for MVP; object storage is deferred.
- **A-3 / OQ-3 (resolved in v1.3).** The sample `Item` domain is not part of the
  TileVision product UI. Its legacy backend model, table/data, API, and
  migrations remain temporarily for compatibility; no destructive migration is
  part of the TileVision MVP.
- **A-4 → OQ-4 (pricing/stock defaults).** Assume a single company currency
  and a decimal price with a `price_unit`; defaults are finalized later.
- **A-5 → OQ-5 (limits/retention).** Assume configurable size/format/
  dimension limits, a per-user concurrency cap, and a daily generation cap.
- **A-6 → OQ-6 (mask source).** Mechanical preservation verification is
  deferred; selection of a provider-supplied mask or local segmentation is
  unresolved and is not required for MVP completion.
- **A-7 → OQ-7 (`staff` role).** Assume a new `staff` system role is added to
  the existing RBAC catalog; exact permission packaging is finalized there.

**Open questions**

- **OQ-1** — Which AI provider and model perform surface replacement? (Drives
  cost, latency, quality, and the mask source.)
- **OQ-2** — Local volume or object storage for images and results?
- **OQ-4** — Default currency and price/stock units.
- **OQ-5** — Concrete upload limits and generation rate caps.
- **OQ-6** — When mechanical preservation verification is implemented, should
  its target mask be provider-supplied or computed locally?
- **OQ-7** — Final permission codes and the definition of the `staff` role.

---

## 12. Change history

- v1.3 (2026-09-30): Resolves OQ-3: the template `Item` domain is not part of
  the TileVision UI, while its backend/API/data remain temporarily for
  compatibility. Narrows AC-9 to require the retained backend/API regressions,
  not the retired management UI.
- v1.2 (2026-09-28): Defines MVP `COMPLETED` semantics as provider success,
  validated output format/dimensions, successful storage, and persisted
  terminal state. Clarifies that mechanical preservation verification is
  deferred because the current system has no mask/segmentation/comparator, and
  documents process-local background-task restart limitations.
- v1.1 (2026-09-27): Reconciled the visualizer domain with the T11 data model.
  The canonical entities are `VisualizationProject` (owner-scoped, stores the
  source room image) and `GenerationJob` (belongs to a project). Generation
  statuses are `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`; target surfaces
  are `FLOOR` and `WALL`. The separate `RoomPhoto` and `Generation` entities are
  superseded; there is no `queued`/`succeeded` status.
- v1.0 (2026-09-26): Initial TileVision MVP product domain document (T00).
  Defines purpose, roles, glossary, entities, visualizer workflow,
  preservation rules, MVP scope and non-goals, architecture fit,
  non-functional requirements, acceptance criteria, and open questions.
