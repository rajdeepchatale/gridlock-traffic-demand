"""
Gridlock 2.0 — Round 2 Prototype Server
Event-Driven Congestion Management System for Bengaluru Traffic Police (ASTraM)

Flask API server powering the dashboard and prediction engine.
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
import os

from engine.impact_predictor import predict_event_impact
from engine.deployment_generator import generate_deployment_order
from engine.cost_analyzer import calculate_economic_impact
from engine.bengaluru_kb import JUNCTIONS, VENUES, EVENT_TYPES, BTP_ZONES

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')


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
        data = request.get_json()
        
        event_type = data.get('event_type', 'ipl_match')
        venue_id = data.get('venue_id', 'chinnaswamy')
        event_date = data.get('event_date', '2026-06-28')
        event_time = data.get('event_time', '19:30')
        expected_crowd = data.get('expected_crowd', None)
        custom_lat = data.get('custom_lat', None)
        custom_lon = data.get('custom_lon', None)
        
        if expected_crowd:
            expected_crowd = int(expected_crowd)
        if custom_lat:
            custom_lat = float(custom_lat)
        if custom_lon:
            custom_lon = float(custom_lon)
        
        # Run prediction pipeline
        impact = predict_event_impact(
            event_type=event_type,
            venue_id=venue_id,
            event_date=event_date,
            event_time=event_time,
            expected_crowd=expected_crowd,
            custom_lat=custom_lat,
            custom_lon=custom_lon,
        )
        
        # Generate deployment order
        deployment = generate_deployment_order(impact)
        
        # Calculate economic impact
        economics = calculate_economic_impact(impact, deployment)
        
        return jsonify({
            "success": True,
            "impact": impact,
            "deployment": deployment,
            "economics": economics,
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
        }), 400


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
if __name__ == '__main__':
    import os
    print("=" * 65)
    print("   GRIDLOCK 2.0 — EVENT-DRIVEN CONGESTION MANAGEMENT SYSTEM")
    print("   Bengaluru Traffic Police (ASTraM) Prototype")
    print("=" * 65)
    print("→ Starting Command Center production server")
    print("=" * 65)
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
