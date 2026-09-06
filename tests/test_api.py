"""
Tests for the Flask API surface.

These cover the contract the browser depends on: response shape, status codes,
and the metadata projection that populates the dashboard controls.
"""

from engine.bengaluru_kb import EVENT_TYPES, JUNCTIONS, VENUES

VALID_REQUEST = {
    "event_type": "ipl_match",
    "venue_id": "chinnaswamy",
    "event_date": "2026-04-15",
    "event_time": "19:30",
    "expected_crowd": 34000,
}


# ── Dashboard ────────────────────────────────────────────────────────────

def test_index_serves_the_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ASTraM" in response.data


# ── Prediction ───────────────────────────────────────────────────────────

def test_predict_returns_all_three_stages(client):
    response = client.post("/api/predict", json=VALID_REQUEST)
    assert response.status_code == 200

    body = response.get_json()
    assert body["success"] is True
    assert set(body) == {"success", "impact", "deployment", "economics"}


def test_predict_honours_the_requested_crowd(client):
    response = client.post("/api/predict", json={**VALID_REQUEST, "expected_crowd": 15000})
    assert response.get_json()["impact"]["event"]["expected_crowd"] == 15000


def test_predict_accepts_string_numerics_from_html_inputs(client):
    """Form fields arrive as strings, so the API must coerce them."""
    response = client.post("/api/predict", json={**VALID_REQUEST, "expected_crowd": "22000"})
    assert response.status_code == 200
    assert response.get_json()["impact"]["event"]["expected_crowd"] == 22000


def test_predict_applies_defaults_for_an_empty_body(client):
    response = client.post("/api/predict", json={})
    assert response.status_code == 200
    assert response.get_json()["impact"]["event"]["type"] == "ipl_match"


def test_unknown_event_type_returns_a_client_error(client):
    response = client.post("/api/predict", json={**VALID_REQUEST, "event_type": "teleportation"})
    assert response.status_code == 400

    body = response.get_json()
    assert body["success"] is False
    assert body["error"]


def test_error_responses_never_leak_a_stack_trace(client):
    response = client.post("/api/predict", json={**VALID_REQUEST, "event_type": "teleportation"})
    assert "Traceback" not in response.get_json()["error"]


def test_predict_is_deterministic(client):
    """Identical inputs must produce identical orders — the output is auditable."""
    first = client.post("/api/predict", json=VALID_REQUEST).get_json()
    second = client.post("/api/predict", json=VALID_REQUEST).get_json()

    assert first["impact"] == second["impact"]
    assert first["economics"] == second["economics"]


def test_every_event_type_can_be_predicted(client):
    for event_type in EVENT_TYPES:
        response = client.post("/api/predict", json={**VALID_REQUEST, "event_type": event_type})
        assert response.status_code == 200, f"{event_type} failed"


def test_every_venue_can_be_predicted(client):
    for venue_id in VENUES:
        response = client.post("/api/predict", json={**VALID_REQUEST, "venue_id": venue_id})
        assert response.status_code == 200, f"{venue_id} failed"


# ── Metadata ─────────────────────────────────────────────────────────────

def test_metadata_exposes_every_control_the_dashboard_needs(client):
    body = client.get("/api/metadata").get_json()
    assert set(body) == {"event_types", "venues", "junctions", "zones"}


def test_metadata_covers_the_full_knowledge_base(client):
    body = client.get("/api/metadata").get_json()
    assert set(body["event_types"]) == set(EVENT_TYPES)
    assert set(body["venues"]) == set(VENUES)
    assert set(body["junctions"]) == set(JUNCTIONS)


def test_metadata_venues_carry_what_the_map_needs(client):
    for venue in client.get("/api/metadata").get_json()["venues"].values():
        assert {"name", "lat", "lon", "capacity"} <= set(venue)


def test_metadata_withholds_internal_tuning_constants(client):
    """The projection must not expose model coefficients to the client."""
    body = client.get("/api/metadata").get_json()
    for event in body["event_types"].values():
        assert "congestion_multiplier" not in event
        assert "vehicle_ratio" not in event


# ── Server configuration ─────────────────────────────────────────────────

def test_debug_is_off_unless_the_environment_asks_for_it(monkeypatch):
    """The Werkzeug debugger is a remote code execution surface — never a default."""
    from app import _env_flag

    monkeypatch.delenv("FLASK_DEBUG", raising=False)
    assert _env_flag("FLASK_DEBUG") is False


def test_debug_flag_accepts_the_usual_truthy_spellings(monkeypatch):
    from app import _env_flag

    for value in ("1", "true", "TRUE", "yes", "on", " True "):
        monkeypatch.setenv("FLASK_DEBUG", value)
        assert _env_flag("FLASK_DEBUG") is True, f"{value!r} should enable debug"

    for value in ("0", "false", "no", "off", ""):
        monkeypatch.setenv("FLASK_DEBUG", value)
        assert _env_flag("FLASK_DEBUG") is False, f"{value!r} should not enable debug"
