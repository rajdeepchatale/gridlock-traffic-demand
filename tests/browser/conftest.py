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
