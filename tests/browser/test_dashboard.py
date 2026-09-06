"""Browser-level checks for the dashboard, served at /console."""

import pytest

pytestmark = pytest.mark.browser

# CARTO returns HTTP 200 with a ~2KB "API KEY REQUIRED" watermark tile, so a
# status check passes while the map is visibly broken. Real tiles for a dense
# city are several KB; this threshold separates the two.
MIN_REAL_TILE_BYTES = 3000


# The console is a fixed-chrome operations layout, not a responsive marketing
# page; these are the widths it is expected to be usable at.
VIEWPORTS_DASH = [(768, 1024), (1280, 800), (1440, 900)]


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


# The max-zoom tile check lives in tests/test_basemap_config.py. It ran here as
# a browser test, but pulled a fresh viewport of tiles from datacenter IPs on
# every CI push — which OpenStreetMap's usage policy prohibits and their servers
# answer with 429. It is now an offline config check plus an opt-in live fetch of
# a single tile.


def _bg(page, selector):
    return page.eval_on_selector(selector, "el => getComputedStyle(el).backgroundColor")


@pytest.mark.parametrize("theme,expected_rgb", [
    ("dark", "rgb(8, 9, 11)"),        # --ground dark  #08090B
    ("light", "rgb(247, 246, 243)"),  # --ground light #F7F6F3
])
def test_dashboard_paints_the_token_ground(console_page, theme, expected_rgb):
    console_page.evaluate(
        "t => { localStorage.setItem('btp_theme', t); document.documentElement.setAttribute('data-theme', t); }",
        theme,
    )
    # body carries `transition: background-color 0.2s` (styles.css), so sampling
    # the computed style immediately returns an intermediate blend rather than
    # the token value. Wait the transition out before asserting.
    console_page.wait_for_timeout(400)
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


def test_3d_view_renders_and_resizes(console_page):
    """The WebGL canvas sizes from its container, so restyling it can break it."""
    console_page.click("#predictBtn")
    console_page.wait_for_selector(".leaflet-tile-loaded", timeout=15000)

    console_page.click("[data-view='3d']")
    canvas = console_page.locator("#tactical3DCanvas canvas")
    canvas.wait_for(state="visible", timeout=15000)

    before = canvas.bounding_box()
    assert before["width"] > 100 and before["height"] > 100, "3D canvas collapsed"

    console_page.set_viewport_size({"width": 1100, "height": 800})
    console_page.wait_for_timeout(600)
    after = canvas.bounding_box()
    assert after["width"] != before["width"], "3D canvas did not resize with its container"
    assert after["height"] > 100


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
    """
    A "bandobast" mention alone did not discriminate — the previous decorative
    copy contained it too. What distinguishes a teaching empty state is that it
    names which inputs matter and what each one changes.
    """
    welcome = console_page.locator("#mapWelcome")
    body = welcome.inner_text().lower()

    assert "bandobast" in body or "order" in body
    hints = welcome.locator(".welcome-hints li")
    assert hints.count() >= 3, "the empty state should teach which inputs matter"

    hint_text = " ".join(hints.nth(i).inner_text().lower() for i in range(hints.count()))
    for control in ("event type", "time", "date"):
        assert control in hint_text, f"the empty state does not explain '{control}'"


@pytest.mark.parametrize("width,height", VIEWPORTS_DASH)
def test_dashboard_never_scrolls_horizontally(console_page, width, height):
    console_page.set_viewport_size({"width": width, "height": height})
    overflow = console_page.evaluate(
        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0, f"{width}px viewport overflows by {overflow}px"
