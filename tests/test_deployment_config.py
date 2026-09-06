"""
Tests for the Vercel deployment configuration.

The hosted build previously relied on platform auto-detection, with nothing in
the repository describing it. These pin the configuration that replaced it, and
guard the failure mode that matters most: `.vercelignore` excluding something
the application imports at request time, which would deploy cleanly and then
500 on the first request.
"""

import ast
import fnmatch
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VERCEL_JSON = ROOT / "vercel.json"
VERCEL_IGNORE = ROOT / ".vercelignore"
ENTRYPOINT = "app.py"

# Real files the running application loads. Checking concrete files rather than
# directory names is deliberate: a pattern like `templates/*.html` excludes every
# page while leaving the string "templates" untouched, so a name-only check would
# pass and the deployment would 500 on its first request.
RUNTIME_FILES = (
    "app.py",
    "requirements.txt",
    "engine/__init__.py",
    "engine/impact_predictor.py",
    "engine/deployment_generator.py",
    "engine/cost_analyzer.py",
    "engine/bengaluru_kb.py",
    "templates/index.html",
    "templates/landing.html",
    "static/css/tokens.css",
    "static/css/styles.css",
    "static/css/landing.css",
    "static/js/app.js",
    "static/js/landing.js",
)


def ignore_patterns():
    """The actual rules, with comments and blank lines stripped."""
    return [
        line.strip()
        for line in VERCEL_IGNORE.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def is_excluded(path, patterns):
    """
    Approximate gitignore semantics well enough to catch real mistakes.

    A path is excluded if a pattern matches the path itself, matches any parent
    directory of it, or globs onto it.
    """
    candidates = [path]
    parts = path.split("/")
    for i in range(1, len(parts)):
        candidates.append("/".join(parts[:i]))

    for pattern in patterns:
        bare = pattern.rstrip("/")
        for candidate in candidates:
            if candidate == bare or fnmatch.fnmatch(candidate, bare):
                return pattern
    return None


@pytest.fixture(scope="module")
def config():
    assert VERCEL_JSON.exists(), "vercel.json is missing — the build is not reproducible"
    return json.loads(VERCEL_JSON.read_text())


def test_vercel_json_is_valid_json(config):
    assert isinstance(config, dict)


def test_the_build_targets_the_flask_entrypoint(config):
    builds = config.get("builds", [])
    assert builds, "no build declared"
    assert any(b.get("src") == ENTRYPOINT for b in builds), f"nothing builds {ENTRYPOINT}"
    assert any("python" in b.get("use", "") for b in builds), "not using the Python runtime"


def test_every_request_routes_to_the_app(config):
    """
    Flask serves its own static files and 404s — confirmed against the live
    deployment — so a catch-all route is required, not just /api.
    """
    routes = config.get("routes", [])
    assert routes, "no routes declared"
    catch_all = [r for r in routes if r.get("src") in ("/(.*)", "/(.*)$", "(.*)")]
    assert catch_all, f"no catch-all route; got {[r.get('src') for r in routes]}"
    assert all(r.get("dest") == ENTRYPOINT for r in catch_all)


def test_the_entrypoint_exposes_a_wsgi_app():
    """Vercel's Python runtime looks for a module-level WSGI callable named `app`."""
    tree = ast.parse((ROOT / ENTRYPOINT).read_text())
    assigns = [
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    ]
    assert "app" in assigns, f"{ENTRYPOINT} does not assign a module-level `app`"


def test_vercelignore_exists():
    assert VERCEL_IGNORE.exists(), ".vercelignore is missing — the dataset would be bundled"


@pytest.mark.parametrize("runtime_file", RUNTIME_FILES)
def test_vercelignore_keeps_every_file_the_app_loads(runtime_file):
    """
    The dangerous failure: excluding a runtime path deploys fine and then 500s on
    the first request, because the module is simply absent from the bundle.
    """
    assert (ROOT / runtime_file).exists(), f"{runtime_file} is missing from the repo"
    offender = is_excluded(runtime_file, ignore_patterns())
    assert offender is None, f".vercelignore rule '{offender}' excludes {runtime_file}"


@pytest.mark.parametrize(
    "heavy_path",
    ["dataset/train.csv", "dataset/test.csv", "tests/test_api.py", "solution.py"],
)
def test_vercelignore_excludes_what_the_app_never_loads(heavy_path):
    """
    Checked against real paths rather than by grepping the file's text — the
    header comment mentions `dataset/`, so a substring check stayed green even
    with the actual rule deleted.
    """
    assert is_excluded(heavy_path, ignore_patterns()), f"{heavy_path} would be bundled"


def test_large_untracked_media_cannot_reach_the_bundle():
    """
    A `vercel` CLI deploy uploads the working tree, not the git tree. The repo
    directory holds a 184MB demo video, a PDF and a zip that only .gitignore
    keeps out today; against a 250MB function limit that is worth an explicit
    rule.
    """
    patterns = ignore_patterns()
    for path in ("demo.mp4", "Gridlock 2.0.pdf", "submission.zip", "screenshot.png"):
        assert is_excluded(path, patterns), f"{path} has no .vercelignore rule"
