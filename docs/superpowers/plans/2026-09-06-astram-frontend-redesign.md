# ASTraM Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a landing page at `/`, move the dashboard to `/console`, rebuild both surfaces on one verified token system, and fix the broken basemap.

**Architecture:** Flask serves two server-rendered templates. A new `tokens.css` layer defines every colour, type, and space value for both themes; `styles.css` (dashboard) and `landing.css` (landing) consume it and define no raw colours of their own. The landing page's headline figures are produced server-side by calling the prediction engine directly, so no client fetch can fail or drift. Severity colour resolves client-side from the semantic `severity` field through theme-aware CSS tokens.

**Tech Stack:** Flask 3, Jinja2, vanilla ES6, Leaflet 1.9.4, Three.js r128, IBM Plex Sans/Mono, pytest, Playwright (Chromium). No bundler, no framework, no build step.

**Spec:** `docs/superpowers/specs/2026-09-06-astram-frontend-redesign-design.md`

## Global Constraints

- **No build step.** No bundler, transpiler, framework, or `package.json` in the repo root. The Vercel deployment works by auto-detection; a build stage risks breaking it.
- **External resources stay on the current CDNs only:** `unpkg.com` (Leaflet), `cdnjs.cloudflare.com` (Three.js), `cdn.jsdelivr.net` (OrbitControls), `fonts.googleapis.com` / `fonts.gstatic.com`. Add no new hosts except the Esri tile server in Task 3.
- **Both themes always.** Every visual change works in dark and light. Theme is set by `data-theme` on `<html>`, persisted in `localStorage` under `btp_theme`.
- **Fonts already loaded.** IBM Plex Sans and IBM Plex Mono. Add no new font requests. DM Sans may be dropped once nothing references it.
- **No raw colour literals outside `tokens.css`.** Every other stylesheet and every inline style references `var(--token)`. Task 8 asserts this.
- **All numerics use `font-variant-numeric: tabular-nums`** so animated counters do not jitter.
- **Existing tests stay green.** The suite is 278 tests before this plan; never delete a test to make a change pass.
- **No `Co-Authored-By` trailers in commit messages.**
- **Exact token values** are fixed by the spec §6 and reproduced in Task 1. Do not invent or adjust colours; the contrast test will reject them.

---

## File Structure

**Created**

| File | Responsibility |
|---|---|
| `static/css/tokens.css` | Every design token, both themes. The only file containing colour literals. |
| `static/css/landing.css` | Landing page layout and components. Consumes tokens only. |
| `templates/landing.html` | Landing page markup. |
| `static/js/landing.js` | Landing-only behaviour: theme toggle and scroll reveal. Under 80 lines. |
| `tests/test_design_tokens.py` | Parses `tokens.css`, asserts WCAG AA for every pair. |
| `tests/test_landing.py` | Landing route, server-rendered figures, engine-failure fallback. |
| `tests/browser/conftest.py` | Live Flask server fixture and Playwright page fixture. |
| `tests/browser/test_dashboard.py` | Dashboard browser checks: basemap, themes, states, responsive. |
| `tests/browser/test_landing.py` | Landing browser checks: renders, CTA navigates, responsive. |

**Modified**

| File | Change |
|---|---|
| `app.py` | `/` serves landing with server-rendered figures; `/console` serves the dashboard. |
| `engine/impact_predictor.py` | Four severity hex values. |
| `templates/index.html` | Link `tokens.css`; markup for empty, loading, and error states. |
| `static/css/styles.css` | Rebuilt against tokens; own `:root` block removed. |
| `static/js/app.js` | Esri basemap, severity via tokens, inline errors, skeleton loading. |
| `requirements-dev.txt` | Add `pytest-playwright`. |
| `pytest.ini` | Register the `browser` marker; exclude it from the default run. |
| `.github/workflows/tests.yml` | Second job running browser tests with Chromium. |
| `README.md` | Deployment and local URLs point at `/console`. |

---

## Task 1: Design token layer

Foundation. No visual change ships in this task — `tokens.css` is created and proven correct, but nothing consumes it until Task 6.

**Files:**
- Create: `static/css/tokens.css`
- Test: `tests/test_design_tokens.py`

**Interfaces:**
- Consumes: nothing.
- Produces: CSS custom properties on `:root` and `[data-theme="light"]`, listed in the table below. Every later task references these names exactly. Also produces `parse_tokens(css_text) -> dict[str, dict[str, str]]` in the test module, returning `{"dark": {...}, "light": {...}}`.

- [ ] **Step 1: Write the failing contrast test**

Create `tests/test_design_tokens.py`:

```python
"""
Contrast tests for the design token layer.

Colour is defined once, in static/css/tokens.css. These tests parse that file
and assert every foreground/background pairing meets WCAG AA in both themes, so
a future palette edit that breaks legibility fails here rather than shipping.
"""

import re
from pathlib import Path

import pytest

TOKENS_CSS = Path(__file__).resolve().parent.parent / "static" / "css" / "tokens.css"

# WCAG AA: 4.5:1 for body text, 3:1 for large text and non-text marks.
BODY_MIN = 4.5
MARK_MIN = 3.0

SURFACES = ("--ground", "--surface-1", "--surface-2")
BODY_TEXT = ("--text-hi", "--text-mid")
SECONDARY = ("--text-lo", "--accent")
SEVERITIES = ("--sev-critical", "--sev-high", "--sev-moderate", "--sev-low")


def parse_tokens(css_text):
    """Extract the dark (:root) and light ([data-theme="light"]) token blocks."""
    blocks = {}
    for selector, key in ((r":root", "dark"), (r'\[data-theme="light"\]', "light")):
        match = re.search(selector + r"\s*\{(.*?)\}", css_text, re.S)
        assert match, f"no {key} token block found in tokens.css"
        blocks[key] = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9A-Fa-f]{6})\s*;", match.group(1)))
    # The light block only overrides what changes, so inherit the rest from dark.
    blocks["light"] = {**blocks["dark"], **blocks["light"]}
    return blocks


def _channel(value):
    value /= 255
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def luminance(hex_colour):
    hex_colour = hex_colour.lstrip("#")
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(foreground, background):
    a, b = luminance(foreground), luminance(background)
    high, low = max(a, b), min(a, b)
    return (high + 0.05) / (low + 0.05)


@pytest.fixture(scope="module")
def tokens():
    assert TOKENS_CSS.exists(), f"{TOKENS_CSS} does not exist"
    return parse_tokens(TOKENS_CSS.read_text())


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("surface", SURFACES)
@pytest.mark.parametrize("text", BODY_TEXT)
def test_body_text_meets_aa(tokens, theme, surface, text):
    ratio = contrast(tokens[theme][text], tokens[theme][surface])
    assert ratio >= BODY_MIN, f"{theme}: {text} on {surface} is {ratio:.2f}:1"


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("surface", SURFACES)
@pytest.mark.parametrize("text", SECONDARY)
def test_secondary_text_meets_aa_large(tokens, theme, surface, text):
    ratio = contrast(tokens[theme][text], tokens[theme][surface])
    assert ratio >= MARK_MIN, f"{theme}: {text} on {surface} is {ratio:.2f}:1"


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("surface", ["--ground", "--surface-2"])
@pytest.mark.parametrize("severity", SEVERITIES)
def test_severity_marks_are_distinguishable(tokens, theme, surface, severity):
    """Severity is the loudest signal on screen and must survive both themes."""
    ratio = contrast(tokens[theme][severity], tokens[theme][surface])
    assert ratio >= MARK_MIN, f"{theme}: {severity} on {surface} is {ratio:.2f}:1"


def test_light_theme_overrides_every_severity(tokens):
    """A single hex cannot serve both grounds, so light must override all four."""
    light_block = re.search(
        r'\[data-theme="light"\]\s*\{(.*?)\}', TOKENS_CSS.read_text(), re.S
    ).group(1)
    for severity in SEVERITIES:
        assert severity in light_block, f"{severity} has no light-theme override"
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `pytest tests/test_design_tokens.py -q`
Expected: FAIL — `static/css/tokens.css does not exist`.

- [ ] **Step 3: Create the token file**

Create `static/css/tokens.css`. Values are fixed by the spec; do not adjust them.

```css
/* ═══════════════════════════════════════════════════════
   ASTraM — Design Tokens
   The only file in this project containing colour literals.
   Every other stylesheet consumes these via var().
   ═══════════════════════════════════════════════════════ */

:root {
    /* Surfaces */
    --ground: #08090B;
    --surface-1: #0F1114;
    --surface-2: #16191E;
    --border: #232830;
    --border-strong: #2F3641;

    /* Text */
    --text-hi: #E9ECEF;
    --text-mid: #98A0AA;
    --text-lo: #626B76;

    /* Accent — one only */
    --accent: #D4B071;
    --accent-dim: #8A7443;

    /* Severity */
    --sev-critical: #E5484D;
    --sev-high: #F2820D;
    --sev-moderate: #E0B400;
    --sev-low: #29A46A;

    /* Type families */
    --font-sans: 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
    --font-mono: 'IBM Plex Mono', ui-monospace, 'SF Mono', monospace;

    /* Type scale — size / line-height */
    --type-display: 700 44px/1.05 var(--font-sans);
    --type-h1: 700 32px/1.15 var(--font-sans);
    --type-h2: 600 22px/1.25 var(--font-sans);
    --type-h3: 600 16px/1.35 var(--font-sans);
    --type-body: 400 14px/1.6 var(--font-sans);
    --type-data-lg: 600 28px/1.1 var(--font-mono);
    --type-data-sm: 500 16px/1.2 var(--font-mono);
    --type-label: 600 11px/1.2 var(--font-mono);

    /* Space — 4px base */
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-6: 24px;
    --space-8: 32px;
    --space-12: 48px;
    --space-16: 64px;

    /* Radius */
    --radius-sm: 2px;
    --radius-md: 4px;
    --radius-pill: 999px;

    /* Elevation — the design leans on borders, not shadow */
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 8px 24px rgba(0, 0, 0, 0.24);

    /* Motion */
    --ease: cubic-bezier(0.4, 0, 0.2, 1);
    --dur-fast: 120ms;
    --dur-base: 200ms;
}

/* Only the values that change are redefined. */
[data-theme="light"] {
    --ground: #F7F6F3;
    --surface-1: #FFFFFF;
    --surface-2: #EFEDE8;
    --border: #DDD9D0;
    --border-strong: #C4BFB2;

    --text-hi: #16181C;
    --text-mid: #5A6069;
    --text-lo: #767C85;

    --accent: #8A6D2F;
    --accent-dim: #C7B183;

    --sev-critical: #C4282D;
    --sev-high: #A85A00;
    --sev-moderate: #8A6D00;
    --sev-low: #1B7F4F;

    --shadow: 0 1px 2px rgba(16, 18, 20, 0.06), 0 8px 24px rgba(16, 18, 20, 0.08);
}

/* Severity helpers, so markup never hardcodes a severity colour. */
.sev-CRITICAL { --sev: var(--sev-critical); }
.sev-HIGH     { --sev: var(--sev-high); }
.sev-MODERATE { --sev: var(--sev-moderate); }
.sev-LOW      { --sev: var(--sev-low); }

/* The hidden attribute must beat layout display values such as flex. */
[hidden] { display: none !important; }

/* Numerics must not jitter while counters animate. */
.tabular, [data-numeric] { font-variant-numeric: tabular-nums; }
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `pytest tests/test_design_tokens.py -q`
Expected: PASS — 53 tests.

- [ ] **Step 5: Run the full suite to confirm nothing regressed**

Run: `pytest`
Expected: PASS — 278 existing plus the new token tests.

- [ ] **Step 6: Commit**

```bash
git add static/css/tokens.css tests/test_design_tokens.py
git commit -m "feat(design): add token layer with contrast tests for both themes"
```

---

## Task 2: Severity palette in the engine

**Files:**
- Modify: `engine/impact_predictor.py` (the severity classification block, around lines 176-190)
- Test: `tests/test_impact_predictor.py`

**Interfaces:**
- Consumes: `--sev-*` dark values from Task 1's `tokens.css`.
- Produces: `junction_impacts[].color` now carries the refined dark-theme hex. The `severity` string is unchanged (`CRITICAL` / `HIGH` / `MODERATE` / `LOW`) and remains the field clients key off.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_impact_predictor.py`:

```python
# The engine's colour field is the canonical machine-readable severity value and
# carries the dark-theme hex. The dashboard resolves colour from CSS tokens
# instead, but exports and any non-dashboard consumer rely on this staying
# correct and in step with tokens.css.
SEVERITY_COLOURS = {
    "CRITICAL": "#E5484D",
    "HIGH": "#F2820D",
    "MODERATE": "#E0B400",
    "LOW": "#29A46A",
}


def test_junction_colour_matches_its_severity(impact):
    for junction in impact["junction_impacts"]:
        assert junction["color"] == SEVERITY_COLOURS[junction["severity"]]


def test_engine_colours_match_the_dark_theme_tokens():
    """The engine's hexes must not drift from the token layer."""
    import re
    from pathlib import Path

    tokens_css = Path(__file__).resolve().parent.parent / "static" / "css" / "tokens.css"
    root_block = re.search(r":root\s*\{(.*?)\}", tokens_css.read_text(), re.S).group(1)
    tokens = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9A-Fa-f]{6})\s*;", root_block))

    for severity, colour in SEVERITY_COLOURS.items():
        token = f"--sev-{severity.lower()}"
        assert tokens[token].upper() == colour.upper(), f"{token} drifted from the engine"
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `pytest tests/test_impact_predictor.py -k colour -q`
Expected: FAIL — the engine still returns `#ff1744`, `#ff6d00`, `#ffd600`, `#00e676`.

- [ ] **Step 3: Update the engine**

In `engine/impact_predictor.py`, in the severity classification block, replace the four colour literals:

```python
        # Severity classification — use combined delay + capacity ratio
        # Colours are the dark-theme severity tokens from static/css/tokens.css.
        # The dashboard resolves colour from CSS so it can adapt per theme; this
        # field is the canonical value for any other consumer.
        combined_score = capacity_ratio * 0.4 + (delay_min / 15.0) * 0.6
        if combined_score > 1.8 or capacity_ratio > 1.8:
            severity = "CRITICAL"
            color = "#E5484D"
        elif combined_score > 1.2 or capacity_ratio > 1.4:
            severity = "HIGH"
            color = "#F2820D"
        elif combined_score > 0.6 or capacity_ratio > 1.0:
            severity = "MODERATE"
            color = "#E0B400"
        else:
            severity = "LOW"
            color = "#29A46A"
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `pytest tests/test_impact_predictor.py -q`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `pytest`
Expected: PASS. No other test pins a severity hex; if one fails, it is asserting the old palette and should be updated, not deleted.

- [ ] **Step 6: Commit**

```bash
git add engine/impact_predictor.py tests/test_impact_predictor.py
git commit -m "feat(engine): refine severity palette to match the design tokens"
```

---

## Task 3: Fix the basemap, with browser test infrastructure

The dashboard loads CARTO's `dark_all` tiles, which now require an API key and return `HTTP 200` with a 1,970-byte "API KEY REQUIRED" watermark. It fails silently, so a status-code check will not catch it — the test asserts on tile *size*.

This task also stands up the Playwright infrastructure every later browser test uses.

**Files:**
- Modify: `static/js/app.js` (the `L.tileLayer` call, around line 853; and `applyTheme`, around line 70)
- Modify: `requirements-dev.txt`
- Modify: `pytest.ini`
- Create: `tests/browser/__init__.py` (empty)
- Create: `tests/browser/conftest.py`
- Create: `tests/browser/test_dashboard.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `BASEMAPS` object in `app.js` mapping theme name to `{url, attribution}`; `setBasemap(theme)` which swaps the active tile layer. Fixtures `live_server` (yields base URL string), `console_page` (a Playwright `Page` already navigated to `/console`, with `page.errors` collecting console and page errors), and `landing_page` (the same for `/`). Used by Tasks 5-8.

- [ ] **Step 1: Add the test dependency and register the marker**

Append to `requirements-dev.txt`:

```
pytest-playwright>=0.5
```

Replace `pytest.ini` entirely:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q --strict-markers -m "not browser"
markers =
    browser: requires a running server and a Playwright browser (deselected by default; run with -m browser)
```

Then install:

```bash
pip install -r requirements-dev.txt
playwright install chromium
```

- [ ] **Step 2: Write the browser fixtures**

Create `tests/browser/__init__.py` as an empty file, then `tests/browser/conftest.py`:

```python
"""
Fixtures for browser-level tests.

The Flask app runs in a background thread on an ephemeral port. Werkzeug's
threaded server is enough here — these tests exercise rendering, not load.
"""

import socket
import threading

import pytest
from werkzeug.serving import make_server

from app import app as flask_app


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def live_server():
    """Run the real app in a thread and yield its base URL."""
    port = _free_port()
    server = make_server("127.0.0.1", port, flask_app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.fixture
def console_page(page, live_server):
    """A page already on the dashboard, with console errors collected."""
    page.errors = []
    page.on("console", lambda m: page.errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page.errors.append(f"pageerror: {e}"))
    page.goto(f"{live_server}/console", wait_until="networkidle")
    return page


@pytest.fixture
def landing_page(page, live_server):
    """A page already on the landing page, with console errors collected."""
    page.errors = []
    page.on("console", lambda m: page.errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page.errors.append(f"pageerror: {e}"))
    page.goto(f"{live_server}/", wait_until="networkidle")
    return page
```

- [ ] **Step 3: Write the failing basemap test**

Create `tests/browser/test_dashboard.py`:

```python
"""Browser-level checks for the dashboard."""

import pytest

pytestmark = pytest.mark.browser

# CARTO returns HTTP 200 with a ~2KB "API KEY REQUIRED" watermark tile, so a
# status check passes while the map is visibly broken. Real tiles for a dense
# city are several KB; this threshold separates the two.
MIN_REAL_TILE_BYTES = 3000


def test_basemap_serves_real_tiles(console_page):
    tiles = []

    def record(response):
        url = response.url
        if any(host in url for host in ("arcgisonline.com", "cartocdn.com", "tile.openstreetmap.org")):
            tiles.append(response)

    console_page.on("response", record)
    console_page.click("#predictBtn")
    console_page.wait_for_selector(".leaflet-tile-loaded", timeout=15000)

    assert tiles, "no basemap tiles were requested"
    assert all("cartocdn.com" not in t.url for t in tiles), "still requesting keyless CARTO tiles"

    sizes = [len(t.body()) for t in tiles if t.status == 200]
    assert sizes, "no basemap tile returned 200"
    assert max(sizes) > MIN_REAL_TILE_BYTES, (
        f"largest tile was {max(sizes)}b — looks like a placeholder, not real map data"
    )


def test_dashboard_has_no_console_errors(console_page):
    console_page.click("#predictBtn")
    console_page.wait_for_selector(".leaflet-tile-loaded", timeout=15000)
    assert console_page.errors == []
```

- [ ] **Step 4: Run it to make sure it fails**

Run: `pytest tests/browser/test_dashboard.py -m browser -q`
Expected: FAIL on `test_basemap_serves_real_tiles` with "still requesting keyless CARTO tiles".

- [ ] **Step 5: Swap the basemap**

In `static/js/app.js`, add near the other module constants at the top of the file:

```javascript
/*
 * Basemap providers. CARTO's keyless tiles were retired — they now return
 * HTTP 200 with an "API KEY REQUIRED" watermark, so the failure is invisible
 * to a status check. Esri's canvas basemaps need no key and ship a light and
 * a dark variant that match our two themes.
 */
const BASEMAPS = {
    dark: {
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        attribution: '© Esri, © OpenStreetMap contributors',
    },
    light: {
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        attribution: '© Esri, © OpenStreetMap contributors',
    },
};

let baseLayer = null;
```

Replace the existing `L.tileLayer(...).addTo(map);` call with:

```javascript
    setBasemap(currentTheme);
```

And add this function immediately after `renderMap`:

```javascript
// Swap the basemap to match the active theme, keeping every overlay in place.
function setBasemap(theme) {
    if (!map) return;
    const provider = BASEMAPS[theme] || BASEMAPS.dark;
    if (baseLayer) map.removeLayer(baseLayer);
    baseLayer = L.tileLayer(provider.url, {
        attribution: provider.attribution,
        maxZoom: 18,
    }).addTo(map);
    baseLayer.bringToBack();
}
```

- [ ] **Step 6: Make the basemap follow the theme**

In `applyTheme`, after the existing `map.invalidateSize()` block, add:

```javascript
    if (map) {
        setBasemap(theme);
    }
```

- [ ] **Step 7: Run the tests and make sure they pass**

Run: `pytest tests/browser -m browser -q`
Expected: PASS — 2 tests.

- [ ] **Step 8: Confirm the default suite is unaffected**

Run: `pytest`
Expected: PASS, browser tests deselected by the marker.

- [ ] **Step 9: Commit**

```bash
git add static/js/app.js requirements-dev.txt pytest.ini tests/browser/
git commit -m "fix(map): replace the keyless CARTO basemap with Esri canvas tiles"
```

---

## Task 4: Landing route with server-rendered figures

**Files:**
- Modify: `app.py`
- Create: `tests/test_landing.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `predict_event_impact`, `generate_deployment_order`, `calculate_economic_impact` — already imported in `app.py`.
- Produces: `landing_figures()` returning the dict below; route `/` rendering `landing.html` with `figures=`; route `/console` rendering `index.html`. Task 5 consumes `figures` in the template.

```python
{
  "crowd": int,            # expected attendance
  "junctions": int,        # junctions hit
  "delay_cut_pct": float,  # percentage delay reduction
  "savings_lakhs": float,  # net savings in lakhs
  "constables": int,       # extra constables required
  "is_live": bool,         # False when the fallback was used
}
```

- [ ] **Step 1: Write the failing route tests**

Create `tests/test_landing.py`:

```python
"""
Tests for the landing page route.

The headline figures are produced server-side by running the real engine, so
they cannot drift from the model or fail in the browser. The route must survive
an engine failure — a landing page that 500s is worse than one showing static
numbers.
"""

from unittest.mock import patch

import pytest

from app import FALLBACK_FIGURES, landing_figures


def test_landing_route_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ASTraM" in response.data


def test_console_route_serves_the_dashboard(client):
    response = client.get("/console")
    assert response.status_code == 200
    assert b"predictBtn" in response.data


def test_landing_figures_come_from_the_real_engine():
    figures = landing_figures()
    assert figures["is_live"] is True
    assert figures["crowd"] > 0
    assert figures["junctions"] > 0
    assert 0 < figures["delay_cut_pct"] <= 100
    assert figures["constables"] >= 0


def test_landing_renders_the_engine_figures(client):
    figures = landing_figures()
    body = client.get("/").get_data(as_text=True)
    assert f"{figures['junctions']}" in body


def test_landing_survives_an_engine_failure(client):
    """A broken engine must degrade to static copy, never a 500."""
    with patch("app.predict_event_impact", side_effect=RuntimeError("engine down")):
        response = client.get("/")
    assert response.status_code == 200


def test_fallback_figures_are_marked_not_live():
    assert FALLBACK_FIGURES["is_live"] is False


@pytest.mark.parametrize("key", ["crowd", "junctions", "delay_cut_pct", "savings_lakhs", "constables"])
def test_fallback_has_the_same_shape_as_live_figures(key):
    """The template reads one shape; the fallback must not omit a field."""
    assert key in FALLBACK_FIGURES
    assert key in landing_figures()
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `pytest tests/test_landing.py -q`
Expected: FAIL — `cannot import name 'FALLBACK_FIGURES' from 'app'`.

- [ ] **Step 3: Implement the route**

In `app.py`, replace the Page Routes section:

```python
# ────────────────────────────────────────────────────────
# Landing Figures
#
# The landing page quotes real numbers. They are produced here by running the
# engine at request time rather than fetched by the browser, so there is nothing
# to spin, nothing to fail, and no way for the headline to drift from the model.
# ────────────────────────────────────────────────────────

# Peak-season IPL at Chinnaswamy — the system's headline scenario.
LANDING_SCENARIO = {
    'event_type': 'ipl_match',
    'venue_id': 'chinnaswamy',
    'event_date': '2026-04-15',
    'event_time': '19:30',
}

# Used only when the engine raises. Values are illustrative and the template
# renders them without live framing.
FALLBACK_FIGURES = {
    'crowd': 34000,
    'junctions': 6,
    'delay_cut_pct': 48.0,
    'savings_lakhs': 3.6,
    'constables': 24,
    'is_live': False,
}


def landing_figures():
    """Run the canonical scenario and reduce it to the landing page's headline numbers."""
    impact = predict_event_impact(**LANDING_SCENARIO)
    deployment = generate_deployment_order(impact)
    economics = calculate_economic_impact(impact, deployment)
    summary = impact['impact_summary']

    return {
        'crowd': impact['event']['expected_crowd'],
        'junctions': summary['affected_junctions'],
        'delay_cut_pct': summary['delay_reduction_pct'],
        'savings_lakhs': economics['savings']['net_savings_lakhs'],
        'constables': deployment['resources']['extra_constables_needed'],
        'is_live': True,
    }


# ────────────────────────────────────────────────────────
# Page Routes
# ────────────────────────────────────────────────────────
@app.route('/')
def landing():
    """Marketing and explanation surface. Must never 500."""
    try:
        figures = landing_figures()
    except Exception:
        app.logger.exception("Landing figures failed; serving fallback copy")
        figures = FALLBACK_FIGURES
    return render_template('landing.html', figures=figures)


@app.route('/console')
def console():
    """The operational dashboard."""
    return render_template('index.html')
```

- [ ] **Step 4: Create a placeholder template so the route resolves**

Create `templates/landing.html` with just enough to pass — Task 5 builds it properly:

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head><meta charset="UTF-8"><title>ASTraM — Bengaluru Traffic Police</title></head>
<body>
  <h1>ASTraM</h1>
  <p data-numeric>{{ figures.junctions }} junctions</p>
  <a href="/console">Open console</a>
</body>
</html>
```

- [ ] **Step 5: Run the tests and make sure they pass**

Run: `pytest tests/test_landing.py -q`
Expected: PASS — 8 tests.

- [ ] **Step 6: Update the README URLs**

In `README.md`, change the local development line to note the two routes:

```markdown
The server starts on `http://127.0.0.1:5000` — the landing page at `/`, the
command console at `/console`. Configure it with environment variables:
```

- [ ] **Step 7: Run the full suite**

Run: `pytest`
Expected: PASS. `tests/test_api.py::test_index_serves_the_dashboard` will now FAIL because `/` no longer serves the dashboard. Update it rather than deleting it:

```python
def test_index_serves_the_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ASTraM" in response.data


def test_console_serves_the_dashboard(client):
    response = client.get("/console")
    assert response.status_code == 200
    assert b"predictBtn" in response.data
```

- [ ] **Step 8: Commit**

```bash
git add app.py templates/landing.html tests/test_landing.py tests/test_api.py README.md
git commit -m "feat(web): add landing route with server-rendered engine figures"
```

---

## Task 5: Build the landing page

Replaces the placeholder from Task 4 with the seven bands from spec §7.

**Files:**
- Modify: `templates/landing.html`
- Create: `static/css/landing.css`
- Create: `static/js/landing.js`
- Create: `tests/browser/test_landing.py`
- Modify: `tests/test_landing.py`

**Interfaces:**
- Consumes: `figures` dict from Task 4; tokens from Task 1.
- Produces: nothing later tasks depend on, except the shared theme-toggle contract — `localStorage.btp_theme` and `data-theme` on `<html>`, identical to the dashboard's, so the choice carries across both pages.

- [ ] **Step 1: Write the failing content tests**

Append to `tests/test_landing.py`:

```python
LANDING_BANDS = [
    "id=\"hero\"",
    "id=\"today\"",
    "id=\"how\"",
    "id=\"produces\"",
    "id=\"credibility\"",
    "id=\"cta\"",
]


@pytest.mark.parametrize("band", LANDING_BANDS)
def test_landing_has_every_band(client, band):
    assert band in client.get("/").get_data(as_text=True)


def test_landing_explains_the_eight_stage_pipeline(client):
    """The model's depth is the point of the page; the stages must be named."""
    body = client.get("/").get_data(as_text=True)
    for stage in ("Seasonality", "Spatial selection", "BPR", "Counterfactual", "Economics"):
        assert stage in body, f"pipeline stage '{stage}' is missing"


def test_landing_carries_the_prototype_disclaimer(client):
    body = client.get("/").get_data(as_text=True).lower()
    assert "prototype" in body
    assert "not affiliated" in body


def test_landing_links_to_the_console(client):
    assert 'href="/console"' in client.get("/").get_data(as_text=True)


def test_landing_uses_the_token_stylesheet(client):
    body = client.get("/").get_data(as_text=True)
    assert "tokens.css" in body
    assert "landing.css" in body
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `pytest tests/test_landing.py -q`
Expected: FAIL — the placeholder template has none of these.

- [ ] **Step 3: Write the landing template**

Replace `templates/landing.html` entirely. Bands carry the ids the tests assert.

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ASTraM — Event-Driven Congestion Intelligence</title>
  <meta name="description" content="Predicts junction-level traffic impact for large events in Bengaluru and generates bandobast deployment orders.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/tokens.css') }}">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/landing.css') }}">
</head>
<body>
  <header class="nav">
    <a class="nav-brand" href="/">
      <span class="badge">BTP</span>
      <span>ASTraM</span>
    </a>
    <nav class="nav-actions">
      <button id="themeToggle" class="btn btn-ghost" type="button" aria-label="Toggle colour theme">Theme</button>
      <a class="btn btn-primary" href="/console">Open console</a>
    </nav>
  </header>

  <main>
    <section id="hero" class="band band-hero">
      <p class="eyebrow">Bengaluru Traffic Police · Decision support</p>
      <h1 class="display">
        {{ '{:,}'.format(figures.crowd) }} people arrive at Chinnaswamy
        in ninety minutes. {{ figures.junctions }} junctions fail.
      </h1>
      <p class="lede">
        ASTraM forecasts which junctions choke, when, and by how much — then
        writes the bandobast order that prevents it.
      </p>
      <div class="hero-actions">
        <a class="btn btn-primary btn-lg" href="/console">Run a prediction</a>
        <a class="btn btn-ghost btn-lg" href="https://github.com/rajdeepchatale/gridlock-traffic-demand">View the source</a>
      </div>

      <dl class="figures" {% if not figures.is_live %}data-static="true"{% endif %}>
        <div class="figure">
          <dt>Expected crowd</dt>
          <dd data-numeric>{{ '{:,}'.format(figures.crowd) }}</dd>
        </div>
        <div class="figure">
          <dt>Junctions hit</dt>
          <dd data-numeric>{{ figures.junctions }}</dd>
        </div>
        <div class="figure">
          <dt>Delay reduced</dt>
          <dd data-numeric>{{ figures.delay_cut_pct }}%</dd>
        </div>
        <div class="figure">
          <dt>Net saving</dt>
          <dd data-numeric>₹{{ figures.savings_lakhs }}L</dd>
        </div>
      </dl>
      {% if figures.is_live %}
      <p class="figures-note">Computed live by the prediction engine for a peak-season IPL fixture.</p>
      {% endif %}
    </section>

    <section id="today" class="band">
      <h2>What happens today</h2>
      <div class="cols">
        <article><h3>Planned by hand</h3><p>Bandobast strength is set from experience and last year's paperwork, not from a forecast of this event at this venue at this hour.</p></article>
        <article><h3>No junction-level view</h3><p>Congestion is known to be coming, but not which of the 28 junctions around a venue will exceed capacity, or in what order.</p></article>
        <article><h3>No costed counterfactual</h3><p>There is no figure for what doing nothing costs, so deployment competes for resources without an argument.</p></article>
      </div>
    </section>

    <section id="how" class="band">
      <h2>How it works</h2>
      <p class="lede">Eight deterministic stages. No model artifact, no inference call — identical inputs always produce an identical, auditable order.</p>
      <ol class="pipeline">
        <li><span class="step">01</span><h3>Seasonality</h3><p>IPL outside April–May scales to a domestic baseline; June–August adds a monsoon delay multiplier.</p></li>
        <li><span class="step">02</span><h3>Crowd to vehicles</h3><p>Attendance becomes vehicle count at 2.5 occupancy, scaled by the event's vehicle ratio.</p></li>
        <li><span class="step">03</span><h3>Spatial selection</h3><p>A Haversine sweep selects junctions inside an impact radius that widens with turnout.</p></li>
        <li><span class="step">04</span><h3>Per-junction load</h3><p>Event traffic decays exponentially with distance and meets the hour's baseline road load.</p></li>
        <li><span class="step">05</span><h3>BPR delay</h3><p>A Bureau of Public Roads volume-delay curve, recalibrated to α 0.9 / β 4.5 for Indian mixed traffic.</p></li>
        <li><span class="step">06</span><h3>Counterfactual</h3><p>Signal override, constable presence and diversions are priced as a delay reduction, capped at 60%.</p></li>
        <li><span class="step">07</span><h3>Severity and staffing</h3><p>Capacity and delay combine into a four-level severity that sets extra constables per junction.</p></li>
        <li><span class="step">08</span><h3>Order and economics</h3><p>The result becomes a bandobast order and a costed comparison against doing nothing.</p></li>
      </ol>
    </section>

    <section id="produces" class="band">
      <h2>What it produces</h2>
      <div class="cols">
        <article><h3>Bandobast order</h3><p>Shift windows, per-junction constable assignments, barricade types and locations, signal overrides and diversion routes — grouped by division with the responsible inspector named.</p></article>
        <article><h3>Dispatch brief</h3><p>The same order compressed into a low-bandwidth WhatsApp message for constables in the field.</p></article>
        <article><h3>Cost of inaction</h3><p>Fuel, productivity, delivery SLA and emergency response priced with and without deployment, with the ROI of the intervention.</p></article>
      </div>
    </section>

    <section id="credibility" class="band band-tight">
      <ul class="stats">
        <li><strong data-numeric>28</strong><span>real junctions mapped</span></li>
        <li><strong data-numeric>8</strong><span>event types modelled</span></li>
        <li><strong data-numeric>10</strong><span>BTP divisions</span></li>
        <li><strong data-numeric>278</strong><span>automated tests</span></li>
      </ul>
    </section>

    <section id="cta" class="band band-cta">
      <h2>Open the console</h2>
      <p class="lede">Pick an event, a venue and a time. The order is ready in under a second.</p>
      <a class="btn btn-primary btn-lg" href="/console">Run a prediction</a>
    </section>
  </main>

  <footer class="foot">
    <p><strong>Prototype.</strong> Built for Gridlock Hackathon 2.0. Not an official Bengaluru Traffic Police system and not affiliated with or endorsed by BTP, Flipkart, or any event organiser. Orders and cost figures are illustrative model output, not operational instructions.</p>
    <nav>
      <a href="https://github.com/rajdeepchatale/gridlock-traffic-demand">Source</a>
      <a href="https://github.com/rajdeepchatale/gridlock-traffic-demand/blob/main/ARCHITECTURE.md">Architecture</a>
      <a href="/console">Console</a>
    </nav>
  </footer>

  <script src="{{ url_for('static', filename='js/landing.js') }}"></script>
</body>
</html>
```

- [ ] **Step 4: Write the landing stylesheet**

Create `static/css/landing.css`. It must contain **no colour literals** — Task 8 asserts this.

```css
/* ═══════════════════════════════════════════════════════
   ASTraM — Landing page
   Consumes static/css/tokens.css. Defines no colours of its own.
   ═══════════════════════════════════════════════════════ */

*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

body {
    background: var(--ground);
    color: var(--text-mid);
    font: var(--type-body);
    -webkit-font-smoothing: antialiased;
}

h1, h2, h3 { color: var(--text-hi); }
a { color: inherit; text-decoration: none; }

/* ── Navigation ── */
.nav {
    position: sticky; top: 0; z-index: 10;
    display: flex; align-items: center; justify-content: space-between;
    padding: var(--space-4) var(--space-6);
    background: color-mix(in srgb, var(--ground) 88%, transparent);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--border);
}
.nav-brand { display: flex; align-items: center; gap: var(--space-3); font: var(--type-h3); color: var(--text-hi); }
.badge {
    font: var(--type-label); letter-spacing: 0.08em;
    padding: var(--space-1) var(--space-2);
    background: var(--accent); color: var(--ground);
    border-radius: var(--radius-sm);
}
.nav-actions { display: flex; gap: var(--space-3); }

/* ── Buttons ── */
.btn {
    display: inline-flex; align-items: center; justify-content: center;
    padding: var(--space-2) var(--space-4);
    font: var(--type-label); letter-spacing: 0.08em; text-transform: uppercase;
    border: 1px solid var(--border-strong); border-radius: var(--radius-md);
    background: transparent; color: var(--text-hi); cursor: pointer;
    transition: background var(--dur-fast) var(--ease), border-color var(--dur-fast) var(--ease);
}
.btn:hover { border-color: var(--accent); }
.btn-primary { background: var(--accent); border-color: var(--accent); color: var(--ground); }
.btn-primary:hover { filter: brightness(1.08); }
.btn-lg { padding: var(--space-3) var(--space-6); }

/* ── Bands ── */
.band { max-width: 1080px; margin: 0 auto; padding: var(--space-16) var(--space-6); border-bottom: 1px solid var(--border); }
.band-tight { padding-block: var(--space-8); }
.band h2 { font: var(--type-h1); margin-bottom: var(--space-4); }
.eyebrow { font: var(--type-label); letter-spacing: 0.12em; text-transform: uppercase; color: var(--accent); margin-bottom: var(--space-4); }
.display { font: var(--type-display); color: var(--text-hi); max-width: 20ch; }
.lede { font-size: 16px; line-height: 1.65; max-width: 62ch; margin-top: var(--space-4); }

/* ── Hero ── */
.hero-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-8); }
.figures {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 1px; margin-top: var(--space-12);
    background: var(--border); border: 1px solid var(--border);
    border-radius: var(--radius-md); overflow: hidden;
}
.figure { background: var(--surface-1); padding: var(--space-6) var(--space-4); }
.figure dt { font: var(--type-label); letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-lo); }
.figure dd { font: var(--type-data-lg); color: var(--accent); margin-top: var(--space-2); }
.figures-note { font: var(--type-label); color: var(--text-lo); margin-top: var(--space-3); }

/* ── Columns ── */
.cols { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-6); margin-top: var(--space-8); }
.cols article { padding: var(--space-6); background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--radius-md); }
.cols h3 { font: var(--type-h3); margin-bottom: var(--space-3); }

/* ── Pipeline ── */
.pipeline { list-style: none; display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-6); margin-top: var(--space-8); }
.pipeline li { padding: var(--space-6); background: var(--surface-1); border: 1px solid var(--border); border-left: 2px solid var(--accent-dim); border-radius: var(--radius-md); }
.pipeline .step { font: var(--type-label); color: var(--accent); letter-spacing: 0.08em; }
.pipeline h3 { font: var(--type-h3); margin: var(--space-2) 0 var(--space-2); }

/* ── Stats ── */
.stats { list-style: none; display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-6); text-align: center; }
.stats strong { display: block; font: var(--type-data-lg); color: var(--text-hi); }
.stats span { font: var(--type-label); letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-lo); }

/* ── CTA and footer ── */
.band-cta { text-align: center; }
.band-cta .lede { margin-inline: auto; }
.band-cta .btn { margin-top: var(--space-8); }
.foot { max-width: 1080px; margin: 0 auto; padding: var(--space-8) var(--space-6) var(--space-16); display: grid; gap: var(--space-4); }
.foot p { font-size: 13px; color: var(--text-lo); max-width: 80ch; }
.foot nav { display: flex; gap: var(--space-6); font: var(--type-label); letter-spacing: 0.08em; text-transform: uppercase; }
.foot nav a:hover { color: var(--accent); }

/* ── Responsive ── */
@media (max-width: 900px) {
    .figures, .stats { grid-template-columns: repeat(2, 1fr); }
    .cols, .pipeline { grid-template-columns: 1fr; }
}
@media (max-width: 560px) {
    .band { padding: var(--space-12) var(--space-4); }
    .display { font-size: 30px; }
    .figures { grid-template-columns: 1fr; }
}

@media (prefers-reduced-motion: reduce) {
    * { animation: none !important; transition: none !important; }
}
```

- [ ] **Step 5: Write the landing script**

Create `static/js/landing.js`:

```javascript
/*
 * Landing page behaviour. Deliberately tiny — the page is server-rendered and
 * needs no data fetching. The theme contract matches the dashboard exactly, so
 * a visitor's choice carries across both pages.
 */
(function () {
    'use strict';

    const STORAGE_KEY = 'btp_theme';

    function readTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY) || 'dark';
        } catch (err) {
            return 'dark';
        }
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
    }

    applyTheme(readTheme());

    document.getElementById('themeToggle').addEventListener('click', () => {
        const next = readTheme() === 'dark' ? 'light' : 'dark';
        try {
            localStorage.setItem(STORAGE_KEY, next);
        } catch (err) {
            /* Private browsing — the toggle still works for this page view. */
        }
        applyTheme(next);
    });
})();
```

- [ ] **Step 6: Run the content tests**

Run: `pytest tests/test_landing.py -q`
Expected: PASS.

- [ ] **Step 7: Write and run the browser test**

Create `tests/browser/test_landing.py`:

```python
"""Browser-level checks for the landing page."""

import pytest

pytestmark = pytest.mark.browser

VIEWPORTS = [(375, 812), (768, 1024), (1440, 900)]


def test_landing_renders_without_console_errors(landing_page):
    assert landing_page.errors == []


def test_cta_navigates_to_the_console(landing_page, live_server):
    landing_page.click("#cta a.btn-primary")
    landing_page.wait_for_url(f"{live_server}/console")
    assert landing_page.locator("#predictBtn").is_visible()


def test_theme_toggle_persists_to_the_console(landing_page, live_server):
    """A visitor who picks light mode should not be flashed dark on the console."""
    landing_page.click("#themeToggle")
    assert landing_page.locator("html").get_attribute("data-theme") == "light"

    landing_page.goto(f"{live_server}/console", wait_until="networkidle")
    assert landing_page.locator("html").get_attribute("data-theme") == "light"


@pytest.mark.parametrize("width,height", VIEWPORTS)
def test_landing_never_scrolls_horizontally(landing_page, width, height):
    landing_page.set_viewport_size({"width": width, "height": height})
    overflow = landing_page.evaluate(
        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0, f"{width}px viewport overflows by {overflow}px"
```

Run: `pytest tests/browser -m browser -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add templates/landing.html static/css/landing.css static/js/landing.js tests/test_landing.py tests/browser/test_landing.py
git commit -m "feat(landing): build the landing page on the token system"
```

---

## Task 6: Rebuild the dashboard on the tokens

The dashboard keeps its layout — a left configuration rail beside a view stage suits the task. What changes is that every colour, size, and space value now resolves through `tokens.css`, and severity resolves per theme.

**Files:**
- Modify: `static/css/styles.css`
- Modify: `templates/index.html`
- Modify: `static/js/app.js` (severity colour resolution)
- Modify: `tests/browser/test_dashboard.py`

**Interfaces:**
- Consumes: every token from Task 1; `setBasemap` from Task 3.
- Produces: `severityColour(severity)` in `app.js`, returning the resolved CSS token value for the active theme with the payload `color` as fallback. Task 7 uses it for the error surface severity chips.

- [ ] **Step 1: Write the failing theme test**

Append to `tests/browser/test_dashboard.py`:

```python
def _bg(page, selector):
    return page.eval_on_selector(selector, "el => getComputedStyle(el).backgroundColor")


@pytest.mark.parametrize("theme,expected_rgb", [
    ("dark", "rgb(8, 9, 11)"),      # --ground dark  #08090B
    ("light", "rgb(247, 246, 243)"),  # --ground light #F7F6F3
])
def test_dashboard_paints_the_token_ground(console_page, theme, expected_rgb):
    console_page.evaluate(
        "t => { localStorage.setItem('btp_theme', t); document.documentElement.setAttribute('data-theme', t); }",
        theme,
    )
    assert _bg(console_page, "body") == expected_rgb


def test_severity_colour_follows_the_theme(console_page):
    """A single hex cannot serve both grounds, so the two themes must differ."""
    def critical_for(theme):
        return console_page.evaluate(
            """t => {
                document.documentElement.setAttribute('data-theme', t);
                return getComputedStyle(document.documentElement)
                    .getPropertyValue('--sev-critical').trim().toUpperCase();
            }""",
            theme,
        )

    assert critical_for("dark") == "#E5484D"
    assert critical_for("light") == "#C4282D"
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `pytest tests/browser -m browser -q`
Expected: FAIL — `styles.css` still paints its own `--asphalt` ground and does not define `--sev-critical`.

- [ ] **Step 3: Link the token stylesheet**

In `templates/index.html`, immediately **before** the existing `styles.css` link, add:

```html
  <link rel="stylesheet" href="{{ url_for('static', filename='css/tokens.css') }}">
```

- [ ] **Step 4: Replace the stylesheet's own token blocks**

In `static/css/styles.css`, delete the entire `:root, [data-theme="dark"] { ... }` block and the entire `[data-theme="light"] { ... }` block. Also delete the `.config-row`-adjacent `[hidden]` rule, now provided by `tokens.css`.

Then apply this mapping across the remainder of the file. These are the old names currently in use; every occurrence is replaced by the token on the right.

| Old | New |
|---|---|
| `--khaki` | `--accent` |
| `--khaki-bright` | `--accent` |
| `--khaki-dim` | `--accent-dim` |
| `--khaki-mid` | `--accent-dim` |
| `--asphalt` | `--ground` |
| `--asphalt-light` | `--surface-1` |
| `--concrete` | `--surface-2` |
| `--concrete-light` | `--surface-2` |
| `--chalk` | `--text-hi` |
| `--chalk-muted` | `--text-mid` |
| `--chalk-dim` | `--text-lo` |

Find every remaining hard-coded colour with:

```bash
grep -nE '#[0-9A-Fa-f]{3,8}\b|rgba?\(' static/css/styles.css
```

Replace each with the nearest token. Severity literals become `var(--sev-critical)`, `var(--sev-high)`, `var(--sev-moderate)`, `var(--sev-low)`. Translucent overlays become `color-mix(in srgb, var(--token) N%, transparent)`.

Then bring spacing, radius, and type onto the scale: replace ad-hoc `px` paddings and margins with the nearest `--space-*`, radii with `--radius-*`, and font shorthands on headings, labels, and numerics with the `--type-*` tokens. Add `font-variant-numeric: tabular-nums` to every rule displaying a figure.

- [ ] **Step 5: Resolve severity from tokens in JS**

In `static/js/app.js`, add near the other helpers:

```javascript
/*
 * Severity colour resolves from CSS so it can differ per theme — a single hex
 * cannot meet contrast on both the near-black and off-white grounds. The
 * payload's own colour is the fallback for an unrecognised severity.
 */
function severityColour(severity, fallback) {
    const token = getComputedStyle(document.documentElement)
        .getPropertyValue(`--sev-${String(severity).toLowerCase()}`)
        .trim();
    return token || fallback || 'currentColor';
}
```

Replace the two payload-colour reads:

- Around line 342, in `showSpotlight`, `background:${junction.color}` becomes `background:${severityColour(junction.severity, junction.color)}`.
- Around line 902, in the marker loop, `const color = j.color;` becomes `const color = severityColour(j.severity, j.color);`.

In `applyTheme`, after the `setBasemap(theme)` call added in Task 3, re-render markers so they pick up the new severity values:

```javascript
    if (map && currentResult) {
        renderMap(currentResult);
    }
```

- [ ] **Step 6: Restyle the 3D view chrome**

Only the container, HUD, and controls — the scene's geometry builders are out of scope and must not be touched.

In `static/css/styles.css`, bring the 3D view's wrapper, overlay panel, and toggle buttons onto the tokens, matching the 2D map's overlay treatment:

```css
/* ── 3D tactical view chrome ── */
#tacticalView .view-canvas { background: var(--ground); }
#tacticalView .tactical-hud {
    background: color-mix(in srgb, var(--surface-1) 88%, transparent);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: var(--space-3);
    font: var(--type-label);
    letter-spacing: 0.08em;
    color: var(--text-mid);
}
#tacticalView .tactical-controls { display: flex; gap: var(--space-2); }
#tacticalView .tactical-controls button {
    padding: var(--space-2) var(--space-3);
    background: var(--surface-2);
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm);
    color: var(--text-hi);
    font: var(--type-label);
    letter-spacing: 0.08em;
    cursor: pointer;
}
#tacticalView .tactical-controls button:hover { border-color: var(--accent); }
```

Match the selectors to the actual class names in `templates/index.html`; if the HUD or controls carry different classes, use those rather than renaming the markup.

- [ ] **Step 7: Verify the 3D canvas still sizes correctly**

Restyling the container is the one change here that can break the WebGL canvas, which sizes itself from its parent. Append to `tests/browser/test_dashboard.py`:

```python
def test_3d_view_renders_and_resizes(console_page):
    """The WebGL canvas sizes from its container, so restyling it can break it."""
    console_page.click("#predictBtn")
    console_page.wait_for_selector(".leaflet-tile-loaded", timeout=15000)

    console_page.click("[data-view='tactical']")
    canvas = console_page.locator("#tacticalView canvas")
    canvas.wait_for(state="visible", timeout=10000)

    before = canvas.bounding_box()
    assert before["width"] > 100 and before["height"] > 100, "3D canvas collapsed"

    console_page.set_viewport_size({"width": 1100, "height": 800})
    console_page.wait_for_timeout(500)
    after = canvas.bounding_box()
    assert after["width"] != before["width"], "3D canvas did not resize with its container"
    assert after["height"] > 100
```

If the view switcher uses a different attribute than `data-view`, read the actual selector from `templates/index.html` and use it.

- [ ] **Step 8: Run the tests and make sure they pass**

Run: `pytest tests/browser -m browser -q`
Expected: PASS.

- [ ] **Step 9: Run the full suite**

Run: `pytest`
Expected: PASS — 278 plus the token and landing tests.

- [ ] **Step 10: Commit**

```bash
git add static/css/styles.css templates/index.html static/js/app.js tests/browser/test_dashboard.py
git commit -m "refactor(ui): rebuild the dashboard on the design token layer"
```

---

## Task 7: Empty, loading, and error states

Three blocking `alert()` calls are replaced with an inline surface, the spinner overlay with skeletons, and the generic splash with an empty state that teaches.

**Files:**
- Modify: `templates/index.html`
- Modify: `static/js/app.js` (lines 637, 693, 708 hold the `alert()` calls)
- Modify: `static/css/styles.css`
- Modify: `tests/browser/test_dashboard.py`

**Interfaces:**
- Consumes: tokens from Task 1. The error surface styles itself from `--sev-critical` and `--sev-high` directly in CSS, so it does not need `severityColour`.
- Produces: `showError(message, kind)` and `clearError()` in `app.js`, where `kind` is `'client'` or `'server'`; and `setLoading(isLoading)`, which toggles the skeleton class on the panels being filled.

- [ ] **Step 1: Write the failing test**

Append to `tests/browser/test_dashboard.py`:

```python
def test_a_rejected_prediction_shows_an_inline_error_not_an_alert(console_page):
    """alert() blocks the page and reads as a crash; errors belong in the layout."""
    dialogs = []
    console_page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

    # 99,000,000 exceeds the server's MAX_CROWD, so validation rejects it.
    console_page.fill("#expectedCrowd", "99000000")
    console_page.click("#predictBtn")

    error = console_page.locator("#errorSurface")
    error.wait_for(state="visible", timeout=5000)
    assert dialogs == [], f"a blocking dialog was raised: {dialogs}"
    assert "crowd" in error.inner_text().lower()


def test_the_error_clears_on_a_successful_prediction(console_page):
    console_page.fill("#expectedCrowd", "99000000")
    console_page.click("#predictBtn")
    console_page.locator("#errorSurface").wait_for(state="visible", timeout=5000)

    console_page.fill("#expectedCrowd", "34000")
    console_page.click("#predictBtn")
    console_page.wait_for_selector(".leaflet-tile-loaded", timeout=15000)
    assert console_page.locator("#errorSurface").is_hidden()


def test_the_empty_state_explains_what_a_prediction_produces(console_page):
    body = console_page.locator("#mapWelcome").inner_text().lower()
    assert "bandobast" in body or "order" in body
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `pytest tests/browser -m browser -q`
Expected: FAIL — `#errorSurface` does not exist and a dialog is raised.

- [ ] **Step 3: Add the error surface markup**

In `templates/index.html`, immediately after the `<button class="predict-btn" ...>` element inside the config form, add:

```html
                        <div class="error-surface" id="errorSurface" role="alert" aria-live="polite" hidden>
                            <span class="error-text" id="errorText"></span>
                            <button class="error-dismiss" type="button" onclick="clearError()" aria-label="Dismiss error">×</button>
                        </div>
```

- [ ] **Step 4: Replace the alerts**

In `static/js/app.js`, add these functions near the other helpers:

```javascript
/*
 * Errors render inline beside the control that caused them. alert() blocks the
 * page, cannot be styled, and in a control room reads as a crash rather than a
 * rejected input.
 */
function showError(message, kind) {
    const surface = document.getElementById('errorSurface');
    const text = document.getElementById('errorText');
    if (!surface || !text) return;
    text.textContent = message;
    surface.dataset.kind = kind || 'client';
    surface.hidden = false;
}

function clearError() {
    const surface = document.getElementById('errorSurface');
    if (surface) surface.hidden = true;
}
```

Then replace the three call sites:

- Line ~637 in `triggerWhatsAppDispatch`:
  `alert('Please run a prediction first before broadcasting alerts.');`
  becomes
  `showError('Run a prediction before broadcasting a dispatch alert.', 'client');`

- Line ~693 in `runPrediction`:
  `alert('Prediction failed: ' + (data.error || 'Unknown error'));`
  becomes
  `showError(data.error || 'The prediction was rejected.', resp.status >= 500 ? 'server' : 'client');`

- Line ~708 in `runPrediction`:
  `alert('Error connecting to server: ' + err.message);`
  becomes
  `showError('Could not reach the server. Check your connection and try again.', 'server');`

At the start of the `try` block in `runPrediction`, add `clearError();` so a retry clears the previous message.

- [ ] **Step 5: Rewrite the empty state**

In `templates/index.html`, replace the contents of `#mapWelcome` with:

```html
                    <div class="welcome-inner">
                        <h2>No prediction yet</h2>
                        <p>Choose an event, a venue and a time, then run a prediction. ASTraM returns which junctions will exceed capacity, a bandobast order with per-junction constable strength, and the cost of doing nothing.</p>
                        <ul class="welcome-hints">
                            <li><strong>Event type</strong> sets crowd draw and impact radius</li>
                            <li><strong>Time</strong> decides the baseline road load it lands on</li>
                            <li><strong>Date</strong> applies IPL season and monsoon adjustments</li>
                        </ul>
                    </div>
```

- [ ] **Step 6: Style the new states**

Append to `static/css/styles.css` — tokens only, no literals:

```css
/* ── Error surface ── */
.error-surface {
    display: flex; align-items: flex-start; gap: var(--space-3);
    margin-top: var(--space-3); padding: var(--space-3);
    background: color-mix(in srgb, var(--sev-critical) 12%, var(--surface-1));
    border: 1px solid var(--sev-critical);
    border-radius: var(--radius-md);
}
.error-surface[data-kind="server"] { border-color: var(--sev-high); background: color-mix(in srgb, var(--sev-high) 12%, var(--surface-1)); }
.error-text { flex: 1; font-size: 13px; line-height: 1.5; color: var(--text-hi); }
.error-dismiss { background: none; border: 0; color: var(--text-mid); font-size: 16px; line-height: 1; cursor: pointer; padding: 0 var(--space-1); }
.error-dismiss:hover { color: var(--text-hi); }

/* ── Empty state ── */
.welcome-inner { max-width: 52ch; text-align: left; }
.welcome-inner h2 { font: var(--type-h2); margin-bottom: var(--space-3); }
.welcome-inner p { color: var(--text-mid); line-height: 1.65; }
.welcome-hints { list-style: none; margin-top: var(--space-6); display: grid; gap: var(--space-2); }
.welcome-hints li { font-size: 13px; color: var(--text-lo); padding-left: var(--space-4); border-left: 2px solid var(--accent-dim); }
.welcome-hints strong { color: var(--text-mid); }

/* ── Skeleton loading ── */
.skeleton {
    background: linear-gradient(90deg,
        var(--surface-1) 0%, var(--surface-2) 50%, var(--surface-1) 100%);
    background-size: 200% 100%;
    animation: skeleton-sweep 1.2s var(--ease) infinite;
    border-radius: var(--radius-sm);
}
@keyframes skeleton-sweep { from { background-position: 200% 0; } to { background-position: -200% 0; } }
```

- [ ] **Step 7: Swap the spinner for skeletons**

In `runPrediction`, replace `loader.classList.add('active')` with a call that marks the stats and zone panels as loading, and the matching removal in `finally`:

```javascript
function setLoading(isLoading) {
    ['statsGrid', 'zoneList', 'junctionGrid'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('skeleton', isLoading);
    });
}
```

Call `setLoading(true)` where the overlay was activated and `setLoading(false)` in the `finally` block. Leave the overlay element in the markup but stop activating it.

- [ ] **Step 8: Run the tests and make sure they pass**

Run: `pytest tests/browser -m browser -q` then `pytest`
Expected: PASS for both.

- [ ] **Step 9: Commit**

```bash
git add templates/index.html static/js/app.js static/css/styles.css tests/browser/test_dashboard.py
git commit -m "feat(ui): add inline errors, skeleton loading, and a teaching empty state"
```

---

## Task 8: Enforce the system, verify responsively, and wire CI

**Files:**
- Create: `tests/test_stylesheet_discipline.py`
- Modify: `tests/browser/test_dashboard.py`
- Modify: `.github/workflows/tests.yml`
- Modify: `README.md`, `ARCHITECTURE.md`

**Interfaces:**
- Consumes: everything above.
- Produces: nothing; this task closes the system.

- [ ] **Step 1: Write the failing discipline test**

Create `tests/test_stylesheet_discipline.py`:

```python
"""
Guards the single-source-of-colour rule.

tokens.css is the only file allowed to contain colour literals. Everything else
references var(--token), so a theme change is one edit and the contrast tests in
test_design_tokens.py actually cover what ships.
"""

import re
from pathlib import Path

import pytest

CSS_DIR = Path(__file__).resolve().parent.parent / "static" / "css"
TOKENS = CSS_DIR / "tokens.css"

# Hex colours, and rgb()/rgba()/hsl() with literal channel values.
COLOUR_LITERAL = re.compile(r"#[0-9A-Fa-f]{3,8}\b|\b(?:rgba?|hsla?)\(\s*\d")

# Shadows and scrims are intentionally raw: they are alpha over whatever sits
# beneath, not palette colours, and tokenising them buys nothing.
ALLOWED_PROPERTIES = ("box-shadow", "text-shadow", "--shadow", "filter", "backdrop-filter")


def _offending_lines(path):
    offenders = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        stripped = line.split("/*")[0]
        if not COLOUR_LITERAL.search(stripped):
            continue
        if any(prop in stripped for prop in ALLOWED_PROPERTIES):
            continue
        offenders.append(f"{path.name}:{number}: {line.strip()}")
    return offenders


@pytest.mark.parametrize(
    "stylesheet",
    [p for p in sorted(CSS_DIR.glob("*.css")) if p.name != "tokens.css"],
    ids=lambda p: p.name,
)
def test_stylesheet_uses_tokens_not_literals(stylesheet):
    offenders = _offending_lines(stylesheet)
    assert not offenders, "colour literals outside tokens.css:\n" + "\n".join(offenders)


def test_tokens_file_is_the_one_that_holds_colour():
    assert COLOUR_LITERAL.search(TOKENS.read_text()), "tokens.css should define colours"
```

- [ ] **Step 2: Run it and fix what it finds**

Run: `pytest tests/test_stylesheet_discipline.py -q`
Expected: FAIL initially, listing any literal Task 6 missed. Replace each with the nearest token until it passes. Do not add exemptions to `ALLOWED_PROPERTIES` to silence it.

- [ ] **Step 3: Add the responsive check**

Append to `tests/browser/test_dashboard.py`:

```python
@pytest.mark.parametrize("width,height", VIEWPORTS_DASH)
def test_dashboard_never_scrolls_horizontally(console_page, width, height):
    console_page.set_viewport_size({"width": width, "height": height})
    overflow = console_page.evaluate(
        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0, f"{width}px viewport overflows by {overflow}px"
```

Add near the top of the file, beside the existing constants:

```python
VIEWPORTS_DASH = [(768, 1024), (1280, 800), (1440, 900)]
```

Fix any overflow the test reports in `styles.css` before moving on.

- [ ] **Step 4: Add the browser job to CI**

In `.github/workflows/tests.yml`, append a second job:

```yaml
  browser:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Install Chromium
        run: playwright install --with-deps chromium

      - name: Run browser tests
        run: pytest -m browser
```

- [ ] **Step 5: Update the documentation**

In `README.md`, add the routes to the layout tree and note the two surfaces:

```markdown
├── templates/
│   ├── landing.html           # Landing page (/)
│   └── index.html             # Command console (/console)
├── static/css/
│   ├── tokens.css             # Design tokens — the only file with colour literals
│   ├── landing.css
│   └── styles.css
```

In `ARCHITECTURE.md`, update §5 Routes to list `/` and `/console`, and move "Frontend is untested" from the gaps table into the Resolved table, describing the Playwright coverage.

- [ ] **Step 6: Run everything**

```bash
pytest && pytest -m browser
```

Expected: both PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/test_stylesheet_discipline.py tests/browser/test_dashboard.py .github/workflows/tests.yml README.md ARCHITECTURE.md
git commit -m "test: enforce token discipline, verify responsiveness, run browser tests in CI"
```

---

## Definition of Done

- [ ] `pytest` passes — 278 original tests plus token, landing, and discipline tests
- [ ] `pytest -m browser` passes in Chromium
- [ ] `/` serves the landing page, `/console` serves the dashboard
- [ ] Basemap renders real tiles in both themes, no watermark
- [ ] Every token pair meets WCAG AA in both themes, asserted by test
- [ ] No colour literal outside `tokens.css`, asserted by test
- [ ] No `alert()` remains in `static/js/app.js`
- [ ] Neither page scrolls horizontally at 375, 768, 1280, or 1440px
- [ ] No build step, no new CDN host beyond the Esri tile server
