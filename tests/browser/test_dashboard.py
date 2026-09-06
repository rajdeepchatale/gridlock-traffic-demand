"""Browser-level checks for the dashboard.

NOTE: the brief's fixtures include `console_page`, which navigates to
`/console` — a route Task 4 has not created yet. Until that route exists,
these tests use `landing_page` (`/`) instead, which serves the same
dashboard template and has the same `#predictBtn` / map behaviour. Swap
back to `console_page` once Task 4 lands.
"""

import pytest

pytestmark = pytest.mark.browser

# CARTO returns HTTP 200 with a ~2KB "API KEY REQUIRED" watermark tile, so a
# status check passes while the map is visibly broken. Real tiles for a dense
# city are several KB; this threshold separates the two.
MIN_REAL_TILE_BYTES = 3000


def test_basemap_serves_real_tiles(landing_page):
    tiles = []

    def record(response):
        url = response.url
        if any(host in url for host in ("arcgisonline.com", "cartocdn.com", "tile.openstreetmap.org")):
            tiles.append(response)

    landing_page.on("response", record)
    landing_page.click("#predictBtn")
    landing_page.wait_for_selector(".leaflet-tile-loaded", timeout=15000)

    assert tiles, "no basemap tiles were requested"
    assert all("cartocdn.com" not in t.url for t in tiles), "still requesting keyless CARTO tiles"

    sizes = [len(t.body()) for t in tiles if t.status == 200]
    assert sizes, "no basemap tile returned 200"
    assert max(sizes) > MIN_REAL_TILE_BYTES, (
        f"largest tile was {max(sizes)}b — looks like a placeholder, not real map data"
    )


def test_dashboard_has_no_console_errors(landing_page):
    landing_page.click("#predictBtn")
    landing_page.wait_for_selector(".leaflet-tile-loaded", timeout=15000)
    assert landing_page.errors == []


def test_basemap_does_not_request_zoom_levels_esri_lacks(landing_page):
    """
    Esri's canvas basemaps have no tiles above z16 — above it they return a
    light-grey "Map data not yet available" placeholder with HTTP 200, which is
    the same silent failure the CARTO watermark had. maxNativeZoom tells Leaflet
    to upscale z16 tiles instead of requesting levels that do not exist, so the
    map stays usable at the zoom fitBounds picks for a tight junction cluster.
    """
    landing_page.click("#predictBtn")
    landing_page.wait_for_selector(".leaflet-tile-loaded", timeout=15000)

    max_native = landing_page.evaluate(
        """() => {
            const layer = Object.values(map._layers || {})
                .find(l => l._url && l._url.includes('arcgisonline'));
            return layer ? layer.options.maxNativeZoom : null;
        }"""
    )
    assert max_native == 16, f"maxNativeZoom is {max_native!r}; Esri has no tiles above z16"
