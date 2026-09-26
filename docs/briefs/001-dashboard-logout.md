# Product Brief 001 — Add Logout to the Dashboard

- **Product Contract ID:** PB-001 (brief form)
- **Title:** Always-visible logout affordance in the authenticated layout
- **Version:** 1.1
- **Status:** Approved for technical planning — OQ-1..OQ-4 resolved by ORC (requester resolution, 2026-09-26); implementation dispatched as kanban task `t_ad7856db`
- **Owner:** Product
- **Date:** 2026-09-26
- **Workspace:** `full-stack-fastapi-template`

---

## 1. Problem / Need

**Problem (verified in repo, 2026-09-26):** Logout is reachable today only through the sidebar
user dropdown — `frontend/src/components/Sidebar/User.tsx` (`data-testid="user-menu"` →
"Log Out" menuitem). The dashboard page (`frontend/src/routes/_layout/index.tsx`) and the
authenticated header (`frontend/src/routes/_layout.tsx`, which contains only the sidebar
trigger) expose no logout affordance. On mobile/narrow viewports the sidebar is collapsed
behind a toggle, so logout is effectively hidden. A user on a shared or borrowed machine who
lands on the dashboard (the first screen after login) has no visible way to end the session.

**Target users:** every authenticated user of the app (regular users and superusers alike);
no permission differentiation.

**Intended outcome:** an authenticated user can end their session with one visible click
from the dashboard, without hunting through menus, and with behavior identical to the
existing sidebar logout.

**Success definition:** QA can log out from the dashboard view via the new affordance, and
all existing logout tests still pass unmodified.

---

## 2. Chosen UX (approved — OQ-1 resolved in favor of header placement, ORC 2026-09-26)

### Placement

Top header bar of the authenticated layout (`frontend/src/routes/_layout.tsx`), on the
right ("end") side, opposite the existing sidebar trigger.

Rationale:

- The header persists across every authenticated page, so the dashboard gets the affordance
  and so do `/items`, `/settings`, and `/admin` (superusers).
- It stays visible on mobile (375px), where the sidebar user menu is hidden behind a toggle.
- No scrolling or menu opening required — one click.

**Scope consequence made explicit (OQ-1, resolved 2026-09-26):** header placement means the
affordance appears on *all* pages rendered inside the authenticated layout, not only the
dashboard. This is intentional, stated as in-scope below, and confirmed as the requested
interpretation of "add logout to dashboard" by the requester via ORC. The alternative (a
control inside the dashboard page body only, `frontend/src/routes/_layout/index.tsx`) was
rejected and remains documented under "Alternatives considered".

### Behavior (must be identical to the existing sidebar logout)

- Single click/tap; **no confirmation dialog** (matches existing sidebar behavior — logout
  is local and reversible by logging in again).
- **Reuse the existing `logout()`** from `frontend/src/hooks/useAuth.ts` (removes
  `access_token` from `localStorage` and navigates to `/login`). No new auth logic, no
  backend call.
- The affordance is a **direct control (button), not an item nested inside a menu**, and it
  exposes `data-testid="logout-button"`.
  Why this is a product requirement: existing Playwright locators target
  `getByRole("menuitem", { name: "Log out" })`
  (`frontend/tests/login.spec.ts:85,102`; `frontend/tests/utils/user.ts:33`). A second
  *menuitem* with the same accessible name would make those locators ambiguous (Playwright
  strict mode) and break the existing suite. A button with a dedicated testid keeps both
  affordances independently targetable.
- **Terminology:** accessible name "Log Out" — the same wording as the sidebar item.

### States

- **Visible** whenever the user is authenticated. The header only renders inside the
  protected `_layout`, whose `beforeLoad` already redirects logged-out users to `/login`,
  so no extra visibility gating is required.
- **Independent of user data:** the control must render and work even while/after the
  `currentUser` query is pending or has failed (it must not depend on `user` being loaded).
- **Focusable and keyboard-operable** (Enter and Space) with a visible focus indicator.

### Error and edge cases

| Case | Expected behavior |
|---|---|
| Expired/invalid token | Log Out still completes local logout (token removed, user on `/login`); no error toast/dialog blocks the flow — logout is client-side only. |
| Rapid double-click | Idempotent; no error; user ends on `/login`. |
| Browser Back after logout | Existing guard redirects to `/login` (no authenticated content shown). |
| User data failed to load | Control still visible and functional. |

### Alternatives considered

- **B. Control in the dashboard page body only** (`index.tsx`): satisfies the literal
  request but leaves other pages and mobile without a visible affordance; scrolly on small
  screens. Not recommended — kept as the OQ-1 fallback.
- **C. Second "Log Out" menuitem in an existing header dropdown**: rejected — collides with
  existing `menuitem` locators (see above) and still hides logout behind a menu open.

---

## 3. Scope

**In scope**

- One new logout affordance in the authenticated header, visible on all pages rendered by
  the `_layout` route — dashboard included.
- Reuse of the existing `logout()` logic; no new auth behavior.
- QA locatability: `data-testid="logout-button"` on the new control.
- New Playwright coverage for the affordance (may extend `frontend/tests/login.spec.ts`
  and/or `frontend/tests/utils/user.ts`).

**Out of scope**

- Any backend change; server-side token revocation/blacklisting (tokens remain valid
  server-side until expiry — same as today).
- Removing or modifying the sidebar user menu (stays as-is; see OQ-3).
- Confirmation dialog, "log out of all devices", session timeout warnings.
- Any change to the `/login` page or post-logout redirect target.
- Auth architecture (OIDC, roles, password flows).
- Changing the known `currentUser` query-cache behavior after logout (existing logout does
  not clear the React Query cache; parity is required, improvement is deferred).
- i18n/localization of the label; renaming any existing testid or accessible name.

**Unaffected workflows:** login, signup, password recovery, user settings, item CRUD,
sidebar navigation.

---

## 4. Acceptance Criteria

Numbered and independently verifiable by QA (Playwright). Preconditions shared by AC-1..AC-2,
AC-6..AC-8: a user is logged in (e.g. the first superuser via `/login`).

**AC-1 — Header logout is visible on the dashboard**
Precondition: logged in.
Action: navigate to `/` and observe the header.
Expected: a control with accessible name "Log Out" and `data-testid="logout-button"` is
visible in the header and clickable without opening any menu. The same control is visible on
every authenticated page (`/`, `/items`, `/settings`, and `/admin` for a superuser) and at
375px viewport width with the sidebar collapsed.

**AC-2 — Header logout ends the session locally, exactly like the sidebar logout**
Precondition: logged in, on `/`.
Action: click `data-testid="logout-button"`.
Expected: URL becomes `/login`; `localStorage` no longer contains `access_token`; no
confirmation dialog appeared; no backend request is needed for the logout itself.

**AC-3 — Protected routes stay guarded after header logout**
Precondition: logged out via AC-2.
Action: `page.goto("/settings")`.
Expected: user is redirected to `/login`.

**AC-4 — Back navigation after header logout**
Precondition: logged out via the header control from `/`.
Action: browser Back.
Expected: user ends on `/login`, with no authenticated content rendered.

**AC-5 — No regression to existing logout paths**
Action: run the existing Playwright suite unmodified.
Expected: all existing tests pass, including "Successful log out" and "Logged-out user cannot
access protected routes" (`frontend/tests/login.spec.ts`). The new control is a button (not a
`menuitem`), so it does not match the existing `getByRole("menuitem", { name: "Log out" })`
locators — no strict-mode ambiguity. The sidebar user-menu "Log Out" keeps working.

**AC-6 — Keyboard operability**
Precondition: logged in, on `/`.
Action: Tab until the header logout control is focused; press Enter (separately: Space).
Expected: the control shows a visible focus indicator while focused; both keys trigger
logout with the same result as AC-2.

**AC-7 — Idempotent rapid clicks**
Precondition: logged in, on `/`.
Action: click `data-testid="logout-button"` twice in quick succession.
Expected: no error is shown; user ends on `/login` with the token removed.

**AC-8 — Independent of user profile data**
Precondition: logged in, on `/`, with the `currentUser` profile request stalled or failed
(e.g. via Playwright route interception). Note: the sidebar user widget disappears while
the profile is unloaded (`Sidebar/User.tsx` renders `null` until `user` is set) — the header
control must not repeat that behavior.
Action: observe the header; click `data-testid="logout-button"`.
Expected: the control is visible while the profile is pending or failed, and clicking it
logs out with the same result as AC-2.

---

## 5. Golden Examples

**Success:** A superuser logs in, lands on the dashboard, and clicks "Log Out" in the
header. They immediately see `/login`; the stored token is gone. Pressing Back does not
expose dashboard content. *Exclusion:* no confirmation dialog appears.

**Edge:** On a 375px-wide phone the sidebar is collapsed; the header "Log Out" is still
visible and one tap logs the user out.

**Failure:** The user's token has expired and profile data failed to load. The header
"Log Out" is still present; clicking it clears the local token and lands the user on
`/login` with no blocking error.

---

## 6. Assumptions → Open Questions

Every material assumption is flagged below; none are silently treated as decided. All four
were resolved by ORC on 2026-09-26 — see section 7 for the resolutions.

- A-1 (placement) → OQ-1
- A-2 (label form) → OQ-2
- A-3 (sidebar logout kept) → OQ-3
- A-4 (testid naming) → OQ-4

## 7. Open Questions

**OQ-1 — Placement — RESOLVED (ORC, 2026-09-26): header of the authenticated layout.**
The affordance is confirmed for all authenticated pages including the dashboard; the
dashboard-page-body-only alternative is rejected. No longer blocking technical planning.

**OQ-2 — Label form — RESOLVED (ORC adopts default, 2026-09-26): text + icon,** accessible
name "Log Out" (icon-only-with-tooltip was not chosen).

**OQ-3 — Sidebar logout's fate — RESOLVED (ORC, 2026-09-26): keep** the sidebar
"Log Out" alongside the new header control (zero regression; AC-5 assumes this).

**OQ-4 — Testid naming — RESOLVED (ORC adopts default, 2026-09-26): `logout-button`.**

---

## 8. Risks and Constraints

- **Locator collision (highest risk):** a same-named second `menuitem` would break three
  existing Playwright call sites. Mitigated by the button + dedicated testid requirement
  (AC-5).
- **Redundancy feel:** two logout affordances may look duplicated — resolved by OQ-3.
- **Small-header width:** the control must fit in the header next to the sidebar trigger at
  375px (covered by AC-1).
- **Template consumers:** this repo is a starter template; behavior must stay conventional
  and minimal (no config surface added).

---

## 9. Change History

- v1.0 (2026-09-26): Initial brief. AC-1..AC-8, OQ-1..OQ-4.
- v1.1 (2026-09-26): ORC resolution recorded — OQ-1 = header placement (all authenticated
  pages); OQ-2 = text + icon "Log Out"; OQ-3 = keep sidebar logout; OQ-4 = testid
  `logout-button`. Status: Proposed → Approved for technical planning. No acceptance
  criteria modified (AC-1..AC-8 unchanged). Implementation dispatched as `t_ad7856db`.
