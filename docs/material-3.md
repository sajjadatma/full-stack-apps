# Material 3 design system

The frontend uses a Material Design 3 inspired design system layered on the existing React + Tailwind v4 + Radix stack. All tokens live in `frontend/src/index.css` and are consumed through Tailwind utilities.

## Color roles

The palette is generated from the teal brand seed. Both light (`:root`) and dark (`.dark`) schemes define the same role names.

| Category | Roles |
| --- | --- |
| Primary | `primary`, `on-primary`, `primary-container`, `on-primary-container` |
| Secondary | `secondary`, `on-secondary`, `secondary-container`, `on-secondary-container` |
| Tertiary | `tertiary`, `on-tertiary`, `tertiary-container`, `on-tertiary-container` |
| Error | `error`, `on-error`, `error-container`, `on-error-container` |
| Surface | `surface`, `on-surface`, `background`, `on-background`, `surface-variant`, `on-surface-variant` |
| Surface containers | `surface-container-lowest`, `surface-container-low`, `surface-container`, `surface-container-high`, `surface-container-highest` |
| Other | `outline`, `outline-variant`, `inverse-surface`, `inverse-on-surface`, `scrim` |

Utilities follow the role name: `bg-primary`, `text-on-surface`, `bg-surface-container-high`, `border-outline-variant`, `text-on-surface-variant`, and so on. Opacity modifiers such as `bg-primary/8` are used for M3 state layers.

Legacy semantic tokens (`card`, `popover`, `muted`, `accent`, `destructive`, `border`, `input`, `ring`, `sidebar-*`) remain as aliases so older classes keep working.

## Typography

Roboto (Latin) and Vazirmatn (Farsi, applied via `html[lang="fa"]`) are bundled with `@fontsource-variable`. M3-named size utilities:

`text-display-small`, `text-headline-small`, `text-title-large`, `text-title-medium`, `text-body-large`, `text-body-medium`, `text-label-large`, `text-label-medium`.

## Shape

| Token | Use |
| --- | --- |
| `rounded-xs` (4px) | Text fields, menu items |
| `rounded-sm` (8px) | Menus, popovers |
| `rounded-md` (12px) | Cards, tables |
| `rounded-lg` (16px) | Grouped surfaces |
| `rounded-xl` (28px) | Dialogs, sheets |
| `rounded-full` | Buttons, badges, navigation items, avatars |

## Elevation

`shadow-elevation-1`, `shadow-elevation-2`, `shadow-elevation-3` model M3 elevation levels for cards, menus, and dialogs.

## Components

- **Buttons** are pill-shaped with M3 variants: `default` (filled), `secondary` (tonal), `outline`, `elevated`, `ghost` (text), `destructive` (filled error), `link`.
- **Text fields** are outlined with a 4px corner, primary focus border/ring, and error styling via `aria-invalid`.
- **Navigation** uses a pill active indicator (`secondary-container` / `on-secondary-container`) in the sidebar drawer and a sticky top app bar.
- **Data tables** render on `surface-container-lowest` with a `surface-container` header and hover state layers.
- **Dialogs and menus** use `surface-container-high`, 28px/8px corners, and elevation shadows.
- **Tabs** use the M3 secondary (pill) style with a filled active indicator.

## Theming

`components/theme-provider.tsx` toggles the `.dark` class on `<html>`; the `@custom-variant dark` rule in `index.css` drives dark-mode utilities. Language switching sets `lang` and `dir` on `<html>`, so RTL is handled with logical properties (`ms-*`, `me-*`, `ps-*`, `pe-*`, `text-start`, `text-end`) and `rtl:` variants.
