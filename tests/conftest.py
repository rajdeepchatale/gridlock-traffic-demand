"""Shared pytest fixtures and path setup for the ASTraM engine test suite."""

import os
import sys

import pytest

# Ensure the repository root is importable when pytest is invoked from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app  # noqa: E402
from engine.cost_analyzer import calculate_economic_impact  # noqa: E402
from engine.deployment_generator import generate_deployment_order  # noqa: E402
from engine.impact_predictor import predict_event_impact  # noqa: E402


# A peak-season IPL match at Chinnaswamy — the system's headline scenario.
BASELINE_EVENT = {
    "event_type": "ipl_match",
    "venue_id": "chinnaswamy",
    "event_date": "2026-04-15",
    "event_time": "19:30",
}


@pytest.fixture
def impact():
    """Impact prediction for the baseline peak-season IPL scenario."""
    return predict_event_impact(**BASELINE_EVENT)


@pytest.fixture
def deployment(impact):
    """Deployment order derived from the baseline impact prediction."""
    return generate_deployment_order(impact)


@pytest.fixture
def economics(impact, deployment):
    """Economic analysis derived from the baseline impact and deployment."""
    return calculate_economic_impact(impact, deployment)


@pytest.fixture
def client():
    """Flask test client for API-level tests."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as test_client:
        yield test_client
