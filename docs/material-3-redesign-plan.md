# Material 3 redesign — task plan (implemented)

## Goal and boundaries

Redesign the React frontend using [Material Design 3](https://m3.material.io/) as the visual and interaction reference. Preserve the existing FastAPI API, routes, RBAC rules, user flows, English/Farsi translations, RTL support, and light/dark/system preferences. This is a design-system adaptation, not a migration to a different frontend framework or an automatic replacement of every Radix component.

**Decisions taken:** the existing teal brand is the seed color; the current React/Radix foundation is kept and restyled; Lucide icons are retained; light and dark palettes are intentional (no dynamic/device color).

## Tasks

- [x] **M3-01 — Audit and visual specification.** Inventoried all screens and shared controls and mapped them to Material 3 patterns (navigation drawer, top app bar, cards, data tables, forms, menus, dialogs, feedback). Captured the target color roles, type scale, shape, elevation, states, and responsive behavior before changing code.
- [x] **M3-02 — Design tokens and theme.** Defined Material 3 color roles, state layers, type scale, shape scale, and elevation tokens in `frontend/src/index.css` for light and dark themes. Added Roboto (Latin) and kept Vazirmatn (Farsi). Legacy semantic tokens were kept as aliases so components migrated safely. See `docs/material-3.md`.
- [x] **M3-03 — Shared primitives.** Restyled buttons, inputs, password inputs, checkboxes, selects, cards, badges, dialogs, sheets, dropdown menus, tabs, tables, alerts, skeletons, tooltips, labels, and the loading button. Public props and accessible Radix behavior were preserved; `Button` gained an `elevated` variant, and `loading-button` now reuses the shared `buttonVariants`.
- [x] **M3-04 — App shell and navigation.** Reworked the top app bar (`routes/_layout.tsx`), navigation drawer (`components/ui/sidebar.tsx`, `components/Sidebar/`), and auth layout for M3 surfaces, pill navigation with a secondary-container active indicator, and a brand panel. RBAC visibility, active-route indication, mobile drawer, logout, theme/language controls, and RTL mirroring are preserved.
- [x] **M3-05 — Screen rollout.** Applied the system to login, signup, password recovery/reset, dashboard (new account and quick-links cards), items, users (`/admin` including bulk selection), roles, and settings. Form validation, destructive confirmations, table pagination/selection, empty/loading/error states, and all endpoint calls are unchanged.
- [x] **M3-06 — Accessibility, localization, and regression QA.** Verified keyboard/focus states, labels, contrast, touch targets, mobile drawer, dark mode, and English/Farsi RTL by capturing screenshots through headless Playwright. Frontend lint/build pass. Full browser suite: **81 passed**, with 2 failures that require Mailpit (not running in this environment). Fixed two pre-existing test-isolation issues (see below).

## Implementation notes

- `frontend/src/index.css` is the single source of truth for the palette, type scale, shape, and elevation. New role utilities (`bg-surface-container`, `text-on-surface-variant`, `bg-primary-container`, ...) sit alongside the legacy token aliases.
- M3 shape mapping: buttons/icon buttons are full pills; text fields and menus use 4px; cards and tables 12px; auth/side sheets and dialogs 28px.
- M3 type scale utilities: `text-display-small`, `text-headline-small`, `text-title-large`, `text-title-medium`, `text-body-large`, `text-body-medium`, `text-label-large`, `text-label-medium`.
- Elevation utilities: `shadow-elevation-1/2/3`.
- No backend, API, or RBAC behavior changed.

## Deviations and follow-ups

- **Icons:** Lucide is retained instead of Material Symbols, per the agreed "retain product identity" decision.
- **Text fields:** use the outlined variant with an external label rather than the M3 floating-label filled field, to reuse the existing react-hook-form structure.
- **Test fixes:** `tests/language.spec.ts` now runs anonymously (it opens `/login` and was previously redirected by the shared auth state), and `tests/roles.spec.ts` waits for the menu close and the language change to persist, so the Farsi test no longer leaks locale into later tests.
- **Mailpit:** `tests/reset-password.spec.ts` needs `MAILPIT_HOST` (http://localhost:8025). Those two tests fail when Mailpit is unavailable and are unrelated to this redesign.

## Acceptance criteria

- Consistent M3-inspired color roles, typography, shape, elevation, navigation, and component states across all listed screens. ✔
- Usable at narrow and wide widths in both LTR and RTL, with light and dark themes. ✔
- No loss of authentication, RBAC, admin bulk delete, CRUD, or accessibility behavior. ✔
- Lint/build and relevant browser tests pass; planned visual deviations are documented. ✔
