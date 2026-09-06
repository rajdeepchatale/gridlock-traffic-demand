"""
Guards the basemap configuration without hammering a public tile server.

Two providers have now failed the same way, both with HTTP 200: CARTO served an
"API KEY REQUIRED" watermark after its keyless tiles were retired, and Esri a
"Map data not yet available" placeholder above z16. A status check catches
neither. The property worth guarding is that the map never requests a zoom level
its provider does not actually serve.

The obvious test — drive a browser to maximum zoom and inspect the tiles — was
tried and withdrawn. It pulled a fresh viewport of tiles on every CI push from
datacenter IPs, which OpenStreetMap's tile usage policy specifically prohibits
and which their servers answer with 429. So the default check is offline and
reads the configuration; the live check is opt-in.
"""

import re
from pathlib import Path

import pytest

APP_JS = Path(__file__).resolve().parent.parent / "static" / "js" / "app.js"

# Documented maximum zoom each provider actually serves. Requesting past this is
# how both previous providers failed, silently, with HTTP 200.
PROVIDER_MAX_ZOOM = {
    "tile.openstreetmap.org": 19,
    "server.arcgisonline.com": 16,
    "basemaps.cartocdn.com": 20,
}

# A tile smaller than this is not plausible map data at any zoom; both known
# placeholders were under 2.6KB. This is a floor, not the real discriminator —
# see test_the_provider_really_serves_tiles_at_the_configured_maximum.
MIN_PLAUSIBLE_TILE_BYTES = 500


@pytest.fixture(scope="module")
def basemap():
    """The provider URL and maxZoom as configured in app.js."""
    source = APP_JS.read_text()
    block = re.search(r"const BASEMAPS = \{(.*?)\};", source, re.S)
    assert block, "BASEMAPS block not found in app.js"

    url = re.search(r"url:\s*'([^']+)'", block.group(1))
    max_zoom = re.search(r"maxZoom:\s*(\d+)", block.group(1))
    assert url and max_zoom, "BASEMAPS must declare a url and a maxZoom"

    return {"url": url.group(1), "max_zoom": int(max_zoom.group(1))}


def test_the_provider_is_a_known_one(basemap):
    host = next((h for h in PROVIDER_MAX_ZOOM if h in basemap["url"]), None)
    assert host, (
        f"unknown tile provider in {basemap['url']!r}. Add its documented maximum "
        f"zoom to PROVIDER_MAX_ZOOM so the ceiling below is actually checked."
    )


def test_configured_zoom_stays_within_what_the_provider_serves(basemap):
    host = next(h for h in PROVIDER_MAX_ZOOM if h in basemap["url"])
    ceiling = PROVIDER_MAX_ZOOM[host]
    assert basemap["max_zoom"] <= ceiling, (
        f"maxZoom {basemap['max_zoom']} exceeds what {host} serves ({ceiling}); "
        f"above its ceiling a provider returns a placeholder with HTTP 200"
    )


def test_the_retired_carto_endpoint_is_not_in_use(basemap):
    """Its keyless tiles now return a watermark, not map data."""
    assert "cartocdn.com" not in basemap["url"]


@pytest.mark.network
def test_the_provider_really_serves_tiles_at_the_configured_maximum(basemap):
    """
    Opt-in live check — two requests, not a browser viewport. Run with
    `pytest -m network`.

    Discriminates by content rather than size. A placeholder is one image the
    provider returns for every coordinate, so two distant tiles come back
    byte-identical — Esri answered both z17 and z18 with exactly 2,521 bytes.
    Real tiles always differ. Size alone is a poor test at high zoom, where a
    legitimate tile covers a tiny area and is genuinely small.
    """
    import math
    import urllib.request

    zoom = basemap["max_zoom"]

    def tile_bytes(lat, lon):
        n = 2**zoom
        x = int((lon + 180) / 360 * n)
        y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
        url = (
            basemap["url"]
            .replace("{z}", str(zoom))
            .replace("{x}", str(x))
            .replace("{y}", str(y))
        )
        request = urllib.request.Request(url, headers={"User-Agent": "ASTraM-test/1.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read()

    # Two well-separated points: Chinnaswamy, and Whitefield ~15km east.
    first = tile_bytes(12.9788, 77.5996)
    second = tile_bytes(12.9698, 77.7500)

    for body in (first, second):
        assert body.startswith(b"\x89PNG"), "provider did not return a PNG"
        assert len(body) > MIN_PLAUSIBLE_TILE_BYTES, f"tile was {len(body)}b"

    assert first != second, (
        f"two distant tiles at z{zoom} are byte-identical ({len(first)}b) — the "
        f"provider is serving one placeholder for every coordinate"
    )
