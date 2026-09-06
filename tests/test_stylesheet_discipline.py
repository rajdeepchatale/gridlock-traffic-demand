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


def test_no_stylesheet_references_an_undefined_token():
    """
    A bare var(--x) with no definition silently resolves to nothing, which is how
    a palette migration leaves invisible text rather than an error.

    Only bare references are checked. `var(--i, 0)` carries its own fallback and
    is safe by construction — that form is how the staggered entrances receive an
    index set from JavaScript at render time, which no stylesheet can declare.
    """
    defined = set()
    for sheet in CSS_DIR.glob("*.css"):
        defined |= set(re.findall(r"(--[\w-]+)\s*:", sheet.read_text()))

    missing = {}
    for sheet in CSS_DIR.glob("*.css"):
        # Group 2 is "," when a fallback follows, ")" when the reference is bare.
        bare = {
            name
            for name, terminator in re.findall(r"var\(\s*(--[\w-]+)\s*([,)])", sheet.read_text())
            if terminator == ")"
        }
        undefined = bare - defined
        if undefined:
            missing[sheet.name] = sorted(undefined)

    assert not missing, f"bare var() references with no definition: {missing}"


def test_templates_do_not_hardcode_colour():
    """Inline styles bypass the token layer and cannot follow the theme."""
    templates = Path(__file__).resolve().parent.parent / "templates"
    offenders = []
    for page in sorted(templates.glob("*.html")):
        for number, line in enumerate(page.read_text().splitlines(), start=1):
            # Only inline style attributes matter; SVG stroke/fill use
            # currentColor and are checked by eye, not here.
            if "style=" in line and COLOUR_LITERAL.search(line):
                offenders.append(f"{page.name}:{number}: {line.strip()[:100]}")
    assert not offenders, "hardcoded colour in a template:\n" + "\n".join(offenders)
