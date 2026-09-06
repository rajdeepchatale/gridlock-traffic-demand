"""
Tests for the Vercel deployment configuration.

The hosted build previously relied on platform auto-detection, with nothing in
the repository describing it. These pin the configuration that replaced it, and
guard the failure mode that matters most: `.vercelignore` excluding something
the application imports at request time, which would deploy cleanly and then
500 on the first request.
"""

import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VERCEL_JSON = ROOT / "vercel.json"
VERCEL_IGNORE = ROOT / ".vercelignore"
ENTRYPOINT = "app.py"

# Everything the running application reads. Excluding any of these from the
# bundle would deploy successfully and fail at request time.
RUNTIME_PATHS = ("app.py", "engine/", "templates/", "static/", "requirements.txt")


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


@pytest.mark.parametrize("runtime_path", RUNTIME_PATHS)
def test_vercelignore_keeps_everything_the_app_needs(runtime_path):
    """
    The dangerous failure: excluding a runtime path deploys fine and then 500s on
    the first request, because the module is simply absent from the bundle.
    """
    patterns = [
        line.strip()
        for line in VERCEL_IGNORE.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    normalised = runtime_path.rstrip("/")
    for pattern in patterns:
        assert pattern.rstrip("/") != normalised, (
            f".vercelignore excludes '{pattern}', which the app needs at runtime"
        )


def test_vercelignore_excludes_the_dataset():
    """The dataset is ~96% of the repository and the serving engine never reads it."""
    patterns = VERCEL_IGNORE.read_text()
    assert "dataset/" in patterns, "the dataset would be bundled into the function"
