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
