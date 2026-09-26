# Role-based access control

This application uses **one role per user**. Roles grant a set of application-
defined permission codes. Permissions are evaluated by the backend on each API
request; JWTs contain identity only, not cached grants. The frontend uses the
effective permissions returned by `GET /api/v1/users/me` to shape navigation
and controls, but the backend remains authoritative.

## Built-in roles

- `user` is assigned by default to new registrations and accounts.
- `superuser` is the protected full-access role. The existing
  `is_superuser` field remains as a compatibility mirror during the RBAC
  transition.
- Built-in roles are seeded at startup, are read-only through the API, and
  cannot be deleted. Custom roles can be managed by users with the appropriate
  role-management permissions.

Custom roles may grant only permission codes present in the application
catalog. A user with `roles.assign` may grant only a permission set contained
in their own effective permission set. The protected `superuser` role can only
be assigned by an existing superuser. Users cannot change their own role, and
the final active superuser cannot be deactivated, demoted, or deleted.

## Permission catalog

| Permission | Meaning |
|---|---|
| `users.read` | Read any user's account |
| `users.create` | Create accounts |
| `users.update` | Update any account (role assignment remains separately gated) |
| `users.delete` | Delete any account |
| `users.read_self` | Read own account through the ID endpoint |
| `users.update_self` | Update own profile and password |
| `users.delete_self` | Delete own account, except protected superusers |
| `items.read_own` / `items.read_any` | Read own items / all items |
| `items.create` | Create items owned by the authenticated user |
| `items.update_own` / `items.update_any` | Update own items / all items |
| `items.delete_own` / `items.delete_any` | Delete own items / all items |
| `products.read` | Read active catalog reference data and published products |
| `products.read_any` | Read active and inactive catalog data |
| `products.create` / `products.update` / `products.delete` | Manage product catalog data |
| `roles.read` | Read roles and the permission catalog |
| `roles.create` / `roles.update` / `roles.delete` | Manage custom roles |
| `roles.assign` | Assign a role to another user |
| `utils.send_test_email` | Send a test email |
| `utils.read_password_recovery_html` | Preview password recovery email HTML |

The default `user` role can manage its own account, create/read/update/delete
its own items, and read active product catalog data. The `superuser` role
receives the complete catalog.

## Endpoint authorization matrix

| Endpoint family | Required access |
|---|---|
| Login, signup, password recovery/reset, health check | Public; recovery responses avoid account enumeration |
| `GET /users/me`, `POST /login/test-token` | Authenticated active user |
| `PATCH /users/me`, `PATCH /users/me/password` | `users.update_self` |
| `DELETE /users/me` | `users.delete_self`; protected superusers cannot self-delete |
| `GET /users/{user_id}` | Own record: `users.read_self`; another user: `users.read` |
| `GET /users/` | `users.read` |
| `POST /users/` | `users.create`; non-default role selection also requires `roles.assign` |
| `PATCH /users/{user_id}` | `users.update`; role changes additionally require `roles.assign` |
| `DELETE /users/{user_id}` | `users.delete`; cannot remove the final active superuser |
| `GET /items/`, `GET /items/{id}` | `items.read_own` filters rows/count by owner; `items.read_any` reads all |
| `POST /items/` | `items.create`; owner is always set by the server |
| `PUT /items/{id}` | `items.update_own` for own items or `items.update_any` for any item |
| `DELETE /items/{id}` | `items.delete_own` for own items or `items.delete_any` for any item |
| `GET /categories/`, `GET /brands/` and detail endpoints | `products.read` sees active records; `products.read_any` sees all records |
| Create category/brand | `products.create` |
| Update category/brand | `products.update` |
| Delete category/brand | `products.delete`; records referenced by products cannot be deleted |
| Role read/catalog endpoints | `roles.read` |
| Role create/update/delete endpoints | Corresponding `roles.create`, `roles.update`, `roles.delete` |
| `PUT /users/{user_id}/role` | `roles.assign`; cannot target the caller |
| `POST /utils/test-email/` | `utils.send_test_email` |
| Password recovery HTML preview | `utils.read_password_recovery_html` |
| `/private/*` | No auth by design, but mounted only when `FASTAPI_ENV=development` |

## API

- `GET /roles/`, `GET /roles/{role_id}`, `GET /roles/permissions` require
  `roles.read`.
- `POST /roles/` requires `roles.create`.
- `PATCH /roles/{role_id}` requires `roles.update`.
- `DELETE /roles/{role_id}` requires `roles.delete`; assigned roles cannot be
  deleted.
- `PUT /users/{user_id}/role` accepts `{ "role_id": "..." }`, replaces the
  user's single role, and requires `roles.assign`.
- `GET /users/me` includes one role summary and the user's effective permission
  codes.

Role lists use the existing `data` / `count` pagination envelope. Permission
keys are stable application contracts; administrators choose from those keys
but cannot create new permission codes.

## Migration and operations

Apply Alembic migrations before starting the application. The RBAC migration
creates the permission catalog and protected roles, maps existing superusers
to `superuser` and all other existing users to `user`, then enforces a
non-null indexed role foreign key. Startup seeding is idempotent. The bootstrap
superuser configured in the environment is still created through the existing
initial-data path.

The TileVision catalog-permissions migration adds the `products.*` permission
codes and grants `products.read` to the default `user` role. Startup seeding
remains authoritative for the built-in role grants.

The migration is transactional on PostgreSQL. Rollback removes the RBAC schema
and `role_id` while retaining the legacy `is_superuser` column. Rolling back
application code does not preserve the custom-role authorization semantics;
coordinate backend and frontend releases and keep a recovery backup.

## Security notes

- Missing grants deny access. Authenticated users without a grant receive 403;
  invalid or expired access tokens receive 401.
- Item list rows and counts are both owner-filtered for own-only roles.
- Assigning a role replaces, rather than accumulates, permissions.
- Never rely on hidden frontend controls as access control.
- The `/private/*` router is development-only and is not part of the
  production API surface.
- This system does not implement multi-tenancy, multiple roles per user,
  inherited roles, direct user grants, or per-item ACLs.
