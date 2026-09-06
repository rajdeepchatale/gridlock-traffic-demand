"""
ASTraM Command Center — Server API Engine
Event-Driven Congestion Management System for Bengaluru Traffic Police (ASTraM)

Flask API server powering the command dashboard and prediction pipeline.
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime
import os

from engine.impact_predictor import predict_event_impact
from engine.deployment_generator import generate_deployment_order
from engine.cost_analyzer import calculate_economic_impact
from engine.bengaluru_kb import JUNCTIONS, VENUES, EVENT_TYPES, BTP_ZONES

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')


# ────────────────────────────────────────────────────────
# Request Validation
#
# The prediction endpoint is the only write-shaped surface, and its output
# is a deployment instruction. Inputs are bounded explicitly so that a bad
# request fails loudly with a usable message rather than silently producing
# an order built on nonsense.
# ────────────────────────────────────────────────────────

# Generous bounding box around the Bengaluru metropolitan region.
LAT_BOUNDS = (12.5, 13.5)
LON_BOUNDS = (77.0, 78.0)

# Above the largest gathering Bengaluru venues can physically host.
MAX_CROWD = 500_000


class ValidationError(ValueError):
    """Raised when a request cannot be turned into a well-formed prediction."""


def _require_choice(value, allowed, field):
    if value not in allowed:
        raise ValidationError(
            f"Unknown {field}: '{value}'. Expected one of: {', '.join(sorted(allowed))}"
        )
    return value


def _parse_crowd(value):
    """Crowd size is optional; when given it must be a positive, plausible integer."""
    if value in (None, ''):
        return None
    try:
        crowd = int(float(value))
    except (TypeError, ValueError):
        raise ValidationError(f"expected_crowd must be a number, got '{value}'")
    if crowd <= 0:
        raise ValidationError("expected_crowd must be greater than zero")
    if crowd > MAX_CROWD:
        raise ValidationError(f"expected_crowd must not exceed {MAX_CROWD:,}")
    return crowd


def _parse_coordinate(value, bounds, field):
    """Coordinates are optional; when given they must fall inside Bengaluru."""
    if value in (None, ''):
        return None
    try:
        coordinate = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number, got '{value}'")
    low, high = bounds
    if not low <= coordinate <= high:
        raise ValidationError(f"{field} must be between {low} and {high} (Bengaluru region)")
    return coordinate


def _parse_datetime(date_str, time_str):
    """
    Reject malformed timings rather than silently defaulting.

    The engine falls back to 18:00 today on a parse failure, which would hand
    an officer an order for the wrong time without ever signalling a problem.
    """
    try:
        datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        raise ValidationError(
            f"Invalid event timing '{date_str} {time_str}'. Expected date YYYY-MM-DD and time HH:MM."
        )
    return date_str, time_str


def validate_prediction_request(data):
    """Normalise and bound an incoming prediction request, or raise ValidationError."""
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")

    event_type = data.get('event_type') or 'ipl_match'
    venue_id = data.get('venue_id') or 'chinnaswamy'
    event_date = data.get('event_date') or '2026-06-28'
    event_time = data.get('event_time') or '19:30'

    _require_choice(event_type, EVENT_TYPES, 'event_type')
    _require_choice(venue_id, VENUES, 'venue_id')
    _parse_datetime(event_date, event_time)

    return {
        'event_type': event_type,
        'venue_id': venue_id,
        'event_date': event_date,
        'event_time': event_time,
        'expected_crowd': _parse_crowd(data.get('expected_crowd')),
        'custom_lat': _parse_coordinate(data.get('custom_lat'), LAT_BOUNDS, 'custom_lat'),
        'custom_lon': _parse_coordinate(data.get('custom_lon'), LON_BOUNDS, 'custom_lon'),
    }


# ────────────────────────────────────────────────────────
# Page Routes
# ────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


# ────────────────────────────────────────────────────────
# API Routes
# ────────────────────────────────────────────────────────
@app.route('/api/predict', methods=['POST'])
def api_predict():
    """
    Main prediction endpoint.
    Accepts event parameters and returns full impact analysis,
    deployment order, and economic cost breakdown.
    """
    try:
        params = validate_prediction_request(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    try:
        impact = predict_event_impact(**params)
        deployment = generate_deployment_order(impact)
        economics = calculate_economic_impact(impact, deployment)
    except ValueError as exc:
        # A domain rule rejected the request — the caller can act on this.
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception:
        # Anything else is a server fault. Log it, but never return internals.
        app.logger.exception("Prediction pipeline failed for %s", params)
        return jsonify({
            "success": False,
            "error": "Prediction failed due to an internal error.",
        }), 500

    return jsonify({
        "success": True,
        "impact": impact,
        "deployment": deployment,
        "economics": economics,
    })


@app.route('/api/metadata', methods=['GET'])
def api_metadata():
    """Returns available event types, venues, and junctions for the UI."""
    return jsonify({
        "event_types": {k: {"name": v["name"], "icon": v["icon"]} for k, v in EVENT_TYPES.items()},
        "venues": {k: {"name": v["name"], "lat": v["lat"], "lon": v["lon"], "capacity": v["capacity"]} for k, v in VENUES.items()},
        "junctions": {k: {"name": v["name"], "lat": v["lat"], "lon": v["lon"], "zone": v["zone"]} for k, v in JUNCTIONS.items()},
        "zones": BTP_ZONES,
    })


# ────────────────────────────────────────────────────────
# Entry Point
# ────────────────────────────────────────────────────────
def _env_flag(name, default=False):
    """Read a boolean from the environment, accepting the usual truthy spellings."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


if __name__ == '__main__':
    # Debug mode exposes the Werkzeug console, so it is opt-in via the
    # environment rather than hardcoded — it must never reach a public host.
    debug = _env_flag('FLASK_DEBUG', default=False)
    host = os.environ.get('HOST', '127.0.0.1' if not debug else '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))

    print("=" * 65)
    print("   ASTRAM — BENGALURU TRAFFIC POLICE COMMAND SYSTEM")
    print("=" * 65)
    print(f"→ Starting Command Center on http://{host}:{port}")
    print(f"→ Debug mode: {'ON' if debug else 'OFF'}")
    print("=" * 65)
    app.run(debug=debug, host=host, port=port)
