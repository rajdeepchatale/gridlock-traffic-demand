"""
Tests for the landing page route.

The headline figures are produced server-side by running the real engine, so
they cannot drift from the model or fail in the browser. The route must survive
an engine failure — a landing page that 500s is worse than one showing static
numbers.
"""

from unittest.mock import patch

import pytest

from app import FALLBACK_FIGURES, landing_figures


def test_landing_route_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ASTraM" in response.data


def test_console_route_serves_the_dashboard(client):
    response = client.get("/console")
    assert response.status_code == 200
    assert b"predictBtn" in response.data


def test_landing_figures_come_from_the_real_engine():
    figures = landing_figures()
    assert figures["is_live"] is True
    assert figures["crowd"] > 0
    assert figures["junctions"] > 0
    assert 0 < figures["delay_cut_pct"] <= 100
    assert figures["constables"] >= 0


def test_landing_renders_the_engine_figures(client):
    figures = landing_figures()
    body = client.get("/").get_data(as_text=True)
    assert f"{figures['junctions']}" in body


def test_landing_survives_an_engine_failure(client):
    """A broken engine must degrade to static copy, never a 500."""
    with patch("app.predict_event_impact", side_effect=RuntimeError("engine down")):
        response = client.get("/")
    assert response.status_code == 200


def test_fallback_figures_are_marked_not_live():
    assert FALLBACK_FIGURES["is_live"] is False


@pytest.mark.parametrize("key", ["crowd", "junctions", "delay_cut_pct", "savings_lakhs", "constables"])
def test_fallback_has_the_same_shape_as_live_figures(key):
    """The template reads one shape; the fallback must not omit a field."""
    assert key in FALLBACK_FIGURES
    assert key in landing_figures()


LANDING_BANDS = [
    "id=\"hero\"",
    "id=\"today\"",
    "id=\"how\"",
    "id=\"produces\"",
    "id=\"credibility\"",
    "id=\"cta\"",
]


@pytest.mark.parametrize("band", LANDING_BANDS)
def test_landing_has_every_band(client, band):
    assert band in client.get("/").get_data(as_text=True)


def test_landing_explains_the_eight_stage_pipeline(client):
    """The model's depth is the point of the page; the stages must be named."""
    # Compared case-insensitively: the test verifies each stage is named, and
    # must not dictate the heading's capitalisation.
    body = client.get("/").get_data(as_text=True).lower()
    for stage in ("seasonality", "spatial selection", "bpr", "counterfactual", "economics"):
        assert stage in body, f"pipeline stage '{stage}' is missing"


def test_landing_carries_the_prototype_disclaimer(client):
    body = client.get("/").get_data(as_text=True).lower()
    assert "prototype" in body
    assert "not affiliated" in body


def test_landing_links_to_the_console(client):
    assert 'href="/console"' in client.get("/").get_data(as_text=True)


def test_landing_uses_the_token_stylesheet(client):
    body = client.get("/").get_data(as_text=True)
    assert "tokens.css" in body
    assert "landing.css" in body


def test_credibility_strip_matches_the_knowledge_base(client):
    """
    These counts were hardcoded in the template and drifted within one task of
    being written. They are now derived, and this pins them to the real data.
    """
    from engine.bengaluru_kb import BTP_ZONES, EVENT_TYPES, JUNCTIONS

    body = client.get("/").get_data(as_text=True)
    for count in (len(JUNCTIONS), len(EVENT_TYPES), len(BTP_ZONES)):
        assert f">{count}</strong>" in body, f"credibility strip is missing {count}"
