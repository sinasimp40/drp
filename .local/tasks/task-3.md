---
title: Admin Panel Redesign — Sidebar SaaS
---
# Admin Panel Redesign — Sidebar SaaS

## What & Why
Replace the current flat orange-on-dark Flask admin templates with the **Sidebar SaaS Console** mockup the user picked from the canvas (`artifacts/mockup-sandbox/src/components/mockups/admin-redesign/SidebarSaas.tsx`). The redesign gives the operator a real left sidebar nav, a KPI summary strip on the dashboard, refined data tables with hover row-actions, and a polished modern dark theme. All current functionality (forms, POST endpoints, JS auto-refresh, bulk-edit modal, OTA workflow, suspended-recovery flow, bulk Rebuild Selected, single-row Rebuild) must keep working exactly as today — only the look changes.

The mockup is React + Tailwind, but the live admin is Flask + Jinja2 with hand-written CSS. We will translate the visual design into vanilla CSS in `base.html` and update each template's markup to match — no React, no Tailwind, no build step. Lucide icons will be inlined as SVG (or loaded from a single CDN script tag) so we don't add dependencies.

While in those templates we also fix one real bug uncovered during the mockup work: the dashboard route crashes with `TypeError: unsupported operand type(s) for -: 'NoneType' and 'float'` whenever an `active` license has `expires_at = NULL` (data-corruption edge case from the recent CDN-suspension recovery). Same guard applies to `/api/dashboard_data`.

## Done looks like
- Logging in shows the new layout: persistent left sidebar (DPRS Admin logo + nav: Dashboard / History / Builds / Create Key, Logout pinned to bottom) and a top header inside the main area.
- Dashboard shows a 4-card KPI strip above the table: Total Licenses, Online Now (with a small live pulse), Suspended, Expiring < 24h — counts are computed server-side from real data.
- The licenses table keeps every column and every action it has today (Unsuspend / Revoke / Delete + the bulk Recover Suspended (CDN fix) and + Create Key buttons), but the row actions appear as icon buttons that fade in on row hover.
- Status badges, time-remaining color coding (green / amber / red), key chip, and registered-IP sub-text all match the mockup.
- History, Builds, Create, Build Config Form, and Login pages share the same header / sidebar / card / form / button styling — no orphan old-look pages.
- Layout is responsive: at ≤900px the sidebar collapses to a top hamburger drawer, the KPI strip stacks 2×2 then 1×4, and the licenses table scrolls horizontally inside its card (no broken overflow on phones).
- All existing JS (`/api/dashboard_data` polling, search filter, builds bulk-edit modal, single-row Rebuild button, builds checkbox selection, Rebuild Selected) still works on the new markup — class names and `id`s the JS depends on are preserved or the JS is updated in lockstep.
- Dashboard no longer 500s when an active license has `expires_at = NULL`; that row renders with a `-` time-remaining instead.
- Visual smoke check on desktop (1280×900) and mobile (390×844) shows no broken layout, no horizontal page scroll, and no console errors.

## Out of scope
- Changing any backend route, DB schema, license logic, build/OTA pipeline, or Bunny/CDN behavior.
- Adding a real charting library — KPI sparkline stays a simple inline SVG / CSS-bar like in the mockup.
- Building a Customers or Infrastructure page (the mockup shows them in the sidebar but they don't exist in the app yet — we will only render nav items for routes that actually exist).
- Any change to `launcher.py`, the PyInstaller build flow, or the Roblox sync.
- Light mode.

## Tasks

1. **Rebuild `base.html` shell** — Replace the current top-navbar + container layout with the new sidebar + main-area shell. Translate the mockup's color tokens, typography, badges, buttons, cards, table, and form styles into vanilla CSS in `base.html`'s `<style>` block. Inline lucide SVG icons for the sidebar items. Add a mobile breakpoint that turns the sidebar into a slide-in drawer toggled by a hamburger in the header. Keep the existing flash-message rendering. Only render sidebar links for routes that exist (Dashboard, History, Builds, Create Key, Logout) — drop the mockup's Customers / Infrastructure stubs.

2. **Redesign `dashboard.html` + dashboard route** — Update the route to also compute the four KPI counts (total, online_now, suspended, expiring_within_24h) and pass them to the template. Add the guard `row["expires_at"] is not None` before the `expires_at - now` subtraction in both `dashboard()` and `api_dashboard_data()` so a NULL expires_at no longer 500s. Render the KPI strip and the redesigned licenses table; preserve all existing data attributes, IDs (`#licenses-table`, `#license-tbody`, `#dashboard-search`, `.time-remaining`, `.live-indicator`), the live-polling JS, the search filter, the Recover Suspended (CDN fix) form, and the per-row Unsuspend / Revoke / Delete forms (kept as icon buttons that still POST to the same endpoints with the same confirm prompts).

3. **Restyle remaining pages** — Apply the new card/form/table/button styles to `history.html`, `builds.html` (including the bulk-edit modal, the Rebuild Selected button, the single-row Rebuild button, and the bulk-checkbox selection), `create.html`, `build_config_form.html`, and `login.html`. No JS behavior changes — only class additions / markup tweaks needed for the new look. Verify every form still submits to the same endpoint and every JS hook still binds.

4. **Cross-page verification pass** — Manually walk every page (login → dashboard → create → builds → bulk edit → rebuild selected → history → unsuspend → recover suspended → logout), confirm forms still work, polling still updates the table without flicker, and the page is usable + good-looking at 390px and 1280px wide. Then run an end-to-end test pass with the testing skill covering: login, dashboard render with mixed-status rows, create-key flow, builds bulk-edit + rebuild flow, recover-suspended flow, mobile layout sanity.

## Relevant files
- `license_server/templates/base.html`
- `license_server/templates/dashboard.html`
- `license_server/templates/history.html`
- `license_server/templates/builds.html`
- `license_server/templates/create.html`
- `license_server/templates/build_config_form.html`
- `license_server/templates/login.html`
- `license_server/server.py:526-569`
- `license_server/server.py:840-883`
- `artifacts/mockup-sandbox/src/components/mockups/admin-redesign/SidebarSaas.tsx`