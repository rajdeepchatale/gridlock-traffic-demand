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
