# TileVision Product Domain Model — T01 Design

- **Status:** Approved in conversation; awaiting written-spec review
- **Date:** 2026-09-26
- **Scope:** T01 — Category, Brand, Product, ProductImage models and schemas

## Goal and constraints

Implement the tile/ceramic catalog persistence domain described by
`docs/tilevision-mvp.md` and T01. Add only domain models, schemas, a migration,
required tests, and the requested correction from `m2_per_box` to
`sqm_per_box` in the MVP document. Do not add routes, storage implementation,
frontend work, generated-client changes, AI/masking/rate-limit behavior, or
sample `Item` cleanup.

Dimensions are integer millimeters. `price`, `sqm_per_box`, and `kg_per_box`
use Python `Decimal` and SQL `Numeric`; `stock_quantity` is an `Integer`.
Do not add currency to Product. Preserve the existing authentication,
authorization, and SQLModel/Alembic foundations.

## Models and relationships

Add the table models to `backend/app/models.py`, where the existing SQLModel
tables and API schemas live:

- **Category:** UUID id, unique name and slug, optional description, active
  flag, creation timestamp, and a one-to-many relationship to products.
- **Brand:** UUID id, unique name and slug, optional description, active flag,
  creation timestamp, and a one-to-many relationship to products.
- **Product:** UUID id; required name, SKU, slug, and category; optional brand;
  description; product type, material, finish, usage area, color family;
  dimensions in mm; rectified flag; anti-slip rating; water absorption percent;
  pieces per box; `sqm_per_box`; `kg_per_box`; country of origin; price;
  integer stock quantity; active/featured flags; timestamps. SKU and slug are
  unique. Classification values remain bounded strings because T00 does not
  provide complete enumerations for the T01 fields.
- **ProductImage:** UUID id, product FK, storage key and optional URL metadata,
  optional alt text, sort order, primary flag, and creation timestamp. A
  product owns multiple images; deleting a product cascades to its images.

Use nullable foreign keys only for optional brand; category is required. Keep
numeric database precision explicit and validate corresponding API values as
Decimal. Stock quantity is integer-valued.

## Schemas

Follow the existing split SQLModel schema pattern in `models.py`. Provide
Create, all-optional Update, Public, and plural List envelope schemas for
Category, Brand, Product, and ProductImage. List schemas use `{data, count}`.
Public Product/Image relationships should be represented without recursive
serialization; expose related category/brand through compact public summaries
only if needed by the model/schema pattern, not by adding API routes.

## Migration

Add one Alembic revision creating category, brand, product, and product_image
tables, with UUID primary keys, indexes/unique constraints for category and
brand identities and product SKU/slug, numeric/integer columns, timestamps,
and foreign keys. Category deletion is restricted while referenced; optional
brand deletion is restricted while referenced; product deletion cascades to
its images. Include a reversible downgrade. Do not alter the existing `item`
table or introduce data/storage migrations.

## Verification

Add focused tests for schema validation and Decimal/integer field behavior,
relationships and uniqueness metadata, and ProductImage multiple-image
association. Run the backend test suite and the Alembic upgrade/check against
the configured test/development database where available. Confirm no routes,
frontend files, generated client, or unrelated foundations changed.

## Approved revision

The requester explicitly approved that `stock_quantity` is an Integer, not a
Decimal/Numeric. `price`, `sqm_per_box`, and `kg_per_box` remain
Decimal/Numeric.
