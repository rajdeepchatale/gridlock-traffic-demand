# ASTraM Frontend Redesign — Design Spec

**Date:** 2026-09-06
**Status:** Approved design, pending implementation plan
**Scope:** New landing page, full dashboard redesign, basemap fix

---

## 1. Context

ASTraM currently serves a single page: the command dashboard at `/`. There is no
landing page, so anyone opening the deployed link lands in a tool with no
explanation of what it is or why the model is interesting.

Two problems motivate this work:

1. **No narrative surface.** The project's substance — a modified BPR delay curve
   over 28 real junctions, seasonality logic, an economic counterfactual — is
   invisible to anyone who does not read the source.
2. **The map is visibly broken.** The dashboard loads CARTO's `dark_all` basemap,
   which now requires an API key. It returns `HTTP 200` with a 1,970-byte tile
   reading "API KEY REQUIRED", so it fails silently. Every map view on the live
   deployment is papered with that watermark.

## 2. Goals

- A landing page that makes the problem, the method, and the result legible in
  under a minute, and pulls the visitor into the live console.
- A dashboard that reads as credible operational software rather than a hackathon
  demo, while staying dense enough to actually use.
- A working basemap.
- One coherent design system across both surfaces, in both themes.

## 3. Non-goals

- Rewriting the Three.js tactical scene. Its ~900 lines of geometry builders are
  left alone; only its container and HUD are restyled.
- Introducing a build step, bundler, or frontend framework. The live Vercel
  deployment has no configuration tracked in this repository and works by
  auto-detection; adding a build stage risks breaking it for no visual gain.
- Changing the prediction model's behaviour. The only engine edit is the severity
  colour palette.
- Backend architecture changes. Routing gains one page; the API is untouched.

## 4. Audience and direction

**Audience:** hackathon judges first, BTP operators second. The landing page
argues; the dashboard works.

**Direction: "operations wall".** Disciplined and dense, in the register of real
operational software — near-black ground, a single restrained accent, severity
colours carrying all the loud signal, large tabular numeric readouts on a strong
grid. Credible rather than decorative.

## 5. Routes

| Route | Now | After |
|---|---|---|
| `/` | dashboard | landing page (`templates/landing.html`) |
| `/console` | — | dashboard (`templates/index.html`) |
| `/api/predict` | unchanged | unchanged |
| `/api/metadata` | unchanged | unchanged |

The README's deployment link and the landing CTA both point at `/console`.

### Server-rendered hero figures

The `/` route calls `predict_event_impact` directly for a canonical scenario
(peak-season IPL at Chinnaswamy, 19:30) and passes real figures into the
template. No client fetch: nothing to spin, nothing to fail, and the headline
numbers cannot drift from the engine.

If the engine raises, the route logs it and renders static fallback copy. The
landing page must never 500.

## 6. Design tokens

Replaces the current ad-hoc set of 69 custom properties. Defined on `:root`, with
`[data-theme="light"]` overriding only the values that change.

### Colour — dark (default)

| Token | Value | Use |
|---|---|---|
| `--ground` | `#08090B` | page background |
| `--surface-1` | `#0F1114` | panels, cards |
| `--surface-2` | `#16191E` | raised elements, inputs |
| `--border` | `#232830` | hairlines |
| `--border-strong` | `#2F3641` | active edges, dividers |
| `--text-hi` | `#E9ECEF` | headings, numerics |
| `--text-mid` | `#98A0AA` | body |
| `--text-lo` | `#626B76` | labels, captions |
| `--accent` | `#D4B071` | primary action, active state |
| `--accent-dim` | `#8A7443` | accent borders, muted marks |

### Colour — light

| Token | Value |
|---|---|
| `--ground` | `#F7F6F3` |
| `--surface-1` | `#FFFFFF` |
| `--surface-2` | `#EFEDE8` |
| `--border` | `#DDD9D0` |
| `--border-strong` | `#C4BFB2` |
| `--text-hi` | `#16181C` |
| `--text-mid` | `#5A6069` |
| `--text-lo` | `#767C85` |
| `--accent` | `#8A6D2F` |
| `--accent-dim` | `#C7B183` |

### Severity

A single hex cannot serve both themes. Contrast analysis of the first proposed
palette against the light ground returned 2.44:1 for HIGH, 1.82:1 for MODERATE
and 2.94:1 for LOW — all below the 3:1 required for non-text marks. Saturated
yellow on white is not rescuable by tuning.

So severity becomes **theme-aware on the client**, keyed off the semantic
`severity` field the engine already ships in every junction payload
(`CRITICAL` / `HIGH` / `MODERATE` / `LOW`). CSS resolves it to the correct value
for the active theme.

The engine's `color` field is still refined and remains the canonical
machine-readable value, carrying the dark-theme hex. Any consumer that is not
the dashboard — an export, a future PDF order — gets a usable colour without
needing the stylesheet.

| Severity | Current | Dark (engine `color`) | Light |
|---|---|---|---|
| CRITICAL | `#ff1744` | `#E5484D` | `#C4282D` |
| HIGH | `#ff6d00` | `#F2820D` | `#A85A00` |
| MODERATE | `#ffd600` | `#E0B400` | `#8A6D00` |
| LOW | `#00e676` | `#29A46A` | `#1B7F4F` |

Every value above is verified at or above 3:1 against its own theme's ground and
surface-2. The client prefers the CSS token and falls back to the payload's
`color` if a severity string is ever unrecognised.

### Typography

Both families are already loaded; no new network requests.

- **IBM Plex Mono** — labels, data, all numerics, with `font-variant-numeric:
  tabular-nums` so figures do not jitter as they animate.
- **IBM Plex Sans** — prose and headings.

| Role | Size / line | Family |
|---|---|---|
| display | 44 / 1.05 | Sans, 700 |
| h1 | 32 / 1.15 | Sans, 700 |
| h2 | 22 / 1.25 | Sans, 600 |
| h3 | 16 / 1.35 | Sans, 600 |
| body | 14 / 1.6 | Sans, 400 |
| data-lg | 28 / 1.1 | Mono, 600, tabular |
| data-sm | 16 / 1.2 | Mono, 500, tabular |
| label | 11 / 1.2 | Mono, 600, uppercase, `0.08em` tracking |

### Space

4px base: `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64`. Radius: `2` (inputs), `4`
(cards), `999` (pills). One shadow token; the design leans on borders, not
elevation.

## 7. Landing page

Single scroll, seven bands.

1. **Hero** — the problem in one concrete sentence carrying real numbers
   ("34,000 people arrive at Chinnaswamy in 90 minutes. Six junctions fail.").
   Primary CTA to `/console`, secondary to the repository.
2. **Live figures strip** — server-rendered from the canonical scenario:
   expected crowd, junctions hit, delay reduction, net savings.
3. **What happens today** — the status quo the system replaces: manual bandobast
   planning, no junction-level forecast, no costed counterfactual.
4. **How it works** — the eight-stage pipeline made legible: event and
   seasonality → crowd to vehicles → spatial selection → per-junction load →
   BPR delay → deployment counterfactual → severity and staffing → order and
   economics. The section most hackathon entries cannot fill.
5. **What it produces** — the three real artifacts: bandobast order, WhatsApp
   dispatch brief, economic comparison.
6. **Credibility strip** — 28 junctions, 8 event types, 10 BTP zones, BPR
   α 0.9 / β 4.5, 278 tests.
7. **CTA and footer** — console link, repository, architecture doc, and the
   prototype disclaimer (not affiliated with BTP or Flipkart; output is
   illustrative).

Fully responsive; single column under 768px.

## 8. Dashboard

The left-rail-plus-stage skeleton is kept — it suits the task — and rebuilt on
the tokens.

| Area | Change |
|---|---|
| Basemap | Esri Dark Gray Canvas (dark) / Light Gray Canvas (light), verified serving real tiles with no API key |
| Empty state | Replaces the generic splash with a state that teaches: what a prediction produces, and the three inputs that matter |
| Loading | Skeleton placeholders in the panels being filled, replacing the full-screen spinner overlay |
| Errors | Inline, dismissible error surface replacing `alert()`, which blocks the page and looks broken |
| Numerics | Larger tabular readouts with explicit units; severity is the only saturated colour on screen |
| Rail and tabs | Rebuilt spacing and type on the token scale |
| 3D view | Container, HUD, and controls restyled; scene internals untouched |

All four views (2D map, analytics, operations, 3D tactical) are retained.

## 9. Error handling

| Case | Behaviour |
|---|---|
| Landing engine failure | Log server-side, render static fallback figures. Never 500. |
| Prediction 400 | Inline error naming the field, form stays populated |
| Prediction 500 | Inline generic error, retry affordance |
| Network failure | Inline offline message, retry affordance |
| Basemap tiles fail | Map still renders markers, radius, and legend over the ground colour |
| Metadata fetch fails | Existing fallback: dropdowns keep their markup options |

## 10. Testing

- **Python:** new route tests — `/` returns 200 and contains the server-rendered
  figures, `/console` serves the dashboard, the landing route survives an engine
  failure. All 278 existing tests stay green.
- **Browser (Playwright):** both pages, both themes — no console errors, CTA
  navigates, a prediction completes end to end, the basemap requests return real
  tiles rather than the watermark, and the layout does not scroll horizontally at
  375px, 768px, and 1440px.
- **Contrast:** every text-on-surface and severity-on-surface pair asserted
  against WCAG AA in both themes (4.5:1 body text, 3:1 secondary text and marks)
  by a test that parses the tokens from the stylesheet, so a future palette edit
  that breaks contrast fails CI rather than shipping.

## 11. Risks

| Risk | Mitigation |
|---|---|
| `/` changing meaning breaks existing links | `/console` is the documented dashboard route; README and landing CTA updated together |
| Severity palette change ripples into map, 3D, and tables | Client keys off the semantic `severity` field, so markers, beacons and tables resolve through one CSS token set; the engine test covering `color` is updated alongside |
| Esri tile service could also start requiring a key | Verified working at time of writing; the map degrades to markers over the ground colour rather than a watermark |
| Restyling the 3D container breaks the canvas sizing | Playwright check that the 3D view renders and resizes |
| Large CSS rewrite regresses the light theme | Contrast test covers both themes; Playwright captures both |

## 12. Out of scope, noted for later

- Rewriting the Three.js scene or extracting `app.js` module state
- Wiring `predictions.csv` into the serving engine as a baseline load
- Authentication, persistence, or a deploy configuration
