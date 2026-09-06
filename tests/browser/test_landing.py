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


def test_content_is_visible_with_reduced_motion(browser, live_server):
    """
    The scroll reveal starts children at opacity 0 and the animation is what
    makes them visible. Cancelling animation outright under reduced motion —
    the obvious implementation — leaves the visitor looking at a blank page.
    """
    context = browser.new_context(reduced_motion="reduce")
    page = context.new_page()
    page.goto(f"{live_server}/", wait_until="networkidle")
    page.evaluate("() => document.getElementById('how').scrollIntoView()")
    page.wait_for_timeout(600)

    opacities = page.eval_on_selector_all(
        "#how > *", "els => els.map(e => parseFloat(getComputedStyle(e).opacity))"
    )
    assert opacities, "no children found in the pipeline band"
    assert all(o > 0.9 for o in opacities), f"content invisible under reduced motion: {opacities}"

    context.close()


def test_content_is_visible_without_javascript(browser, live_server):
    """The reveal is added from JS, so a no-JS visitor must still see everything."""
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    page.goto(f"{live_server}/", wait_until="domcontentloaded")

    opacities = page.eval_on_selector_all(
        "#how > *", "els => els.map(e => parseFloat(getComputedStyle(e).opacity))"
    )
    assert opacities, "no children found in the pipeline band"
    assert all(o > 0.9 for o in opacities), f"content hidden without JS: {opacities}"

    context.close()
