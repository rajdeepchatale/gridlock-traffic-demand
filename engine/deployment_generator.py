"""
Bandobast Order Generator — Gridlock 2.0 Round 2
Generates actionable deployment orders that BTP Traffic Inspectors
can directly use for field operations during events.
"""

from datetime import datetime, timedelta
from engine.bengaluru_kb import JUNCTIONS, BTP_ZONES, EVENT_TYPES


def generate_deployment_order(impact_result):
    """
    Transforms impact prediction into a structured deployment order (bandobast).
    
    Args:
        impact_result: Output from impact_predictor.predict_event_impact()
    
    Returns:
        dict with complete deployment order details
    """
    event = impact_result["event"]
    summary = impact_result["impact_summary"]
    junctions = impact_result["junction_impacts"]
    event_template = EVENT_TYPES.get(event["type"], {})
    
    # Parse event datetime
    try:
        event_dt = datetime.strptime(f"{event['date']} {event['time']}", "%Y-%m-%d %H:%M")
    except ValueError:
        event_dt = datetime.now()
    
    # Generate order reference number
    order_ref = f"BTP/SPECIAL/{event_dt.strftime('%Y%m%d')}/{event['type'].upper()[:4]}"
    
    # Determine shift timings based on event window
    pre_hours = event_template.get("pre_event_surge_hours", 2.0)
    post_hours = event_template.get("post_event_surge_hours", 1.5)
    duration = event_template.get("duration_hours", 4)
    
    shift_start = event_dt - timedelta(hours=pre_hours + 0.5)  # 30 min buffer
    shift_end = event_dt + timedelta(hours=duration + post_hours + 0.5)
    
    # Calculate total shift hours
    total_shift_hours = (shift_end - shift_start).total_seconds() / 3600
    
    # Junction assignments
    assignments = []
    barricade_locations = []
    signal_overrides = []
    zones_affected = set()
    
    for junc in junctions:
        if junc["extra_constables_needed"] <= 0 and junc["severity"] == "LOW":
            continue
        
        zones_affected.add(junc["zone"])
        
        # Determine specific instructions per junction
        instructions = []
        
        if junc["severity"] == "CRITICAL":
            instructions.append("Manual traffic regulation mandatory")
            instructions.append(f"Deploy {event['barricade_type']} barricade at approach roads")
            if event["signal_override_needed"]:
                instructions.append("Signal timing override: extend green phase by 30s on primary corridor")
                signal_overrides.append({
                    "junction": junc["name"],
                    "junction_id": junc["junction_id"],
                    "override_type": "Extended green on primary corridor (+30s)",
                })
            barricade_locations.append({
                "junction": junc["name"],
                "junction_id": junc["junction_id"],
                "type": event["barricade_type"],
                "lat": junc["lat"],
                "lon": junc["lon"],
            })
        elif junc["severity"] == "HIGH":
            instructions.append("Active traffic management — prioritize event dispersal corridor")
            if event["signal_override_needed"]:
                instructions.append("Signal timing override: extend green phase by 15s")
                signal_overrides.append({
                    "junction": junc["name"],
                    "junction_id": junc["junction_id"],
                    "override_type": "Extended green on primary corridor (+15s)",
                })
        elif junc["severity"] == "MODERATE":
            instructions.append("Monitor and assist — redirect overflow to alternate routes")
        
        assignment = {
            "junction_id": junc["junction_id"],
            "junction_name": junc["name"],
            "zone": junc["zone"],
            "lat": junc["lat"],
            "lon": junc["lon"],
            "severity": junc["severity"],
            "total_constables": junc["total_constables"],
            "extra_constables": junc["extra_constables_needed"],
            "normal_constables": junc["typical_constables"],
            "shift_start": shift_start.strftime("%H:%M"),
            "shift_end": shift_end.strftime("%H:%M"),
            "instructions": instructions,
            "expected_delay_with": junc["delay_with_deployment_min"],
            "expected_delay_without": junc["delay_without_deployment_min"],
            "capacity_ratio": junc["capacity_ratio"],
        }
        assignments.append(assignment)
    
    # Generate diversion routes
    diversions = _generate_diversion_routes(junctions, event)
    
    # Aggregate resource requirements
    total_constables = sum(a["total_constables"] for a in assignments)
    extra_constables = sum(a["extra_constables"] for a in assignments)
    total_barricades = len(barricade_locations)
    total_signal_overrides = len(signal_overrides)
    
    # Zone-wise breakdown
    zone_breakdown = {}
    for a in assignments:
        z = a["zone"]
        if z not in zone_breakdown:
            zone_breakdown[z] = {
                "zone": z,
                "station": BTP_ZONES.get(z, {}).get("station", "Unknown Station"),
                "inspector": BTP_ZONES.get(z, {}).get("inspector", "TI Unknown"),
                "junctions": 0,
                "constables": 0,
                "critical": 0,
            }
        zone_breakdown[z]["junctions"] += 1
        zone_breakdown[z]["constables"] += a["total_constables"]
        if a["severity"] == "CRITICAL":
            zone_breakdown[z]["critical"] += 1
    
    # WhatsApp alert message
    whatsapp_alert = _generate_whatsapp_alert(event, summary, shift_start, shift_end, assignments)
    
    return {
        "order_reference": order_ref,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "event": event,
        "shift": {
            "start": shift_start.strftime("%H:%M"),
            "end": shift_end.strftime("%H:%M"),
            "total_hours": round(total_shift_hours, 1),
            "date": event_dt.strftime("%d %B %Y"),
            "day": event["day_name"],
        },
        "resources": {
            "total_constables": total_constables,
            "extra_constables_needed": extra_constables,
            "barricades": total_barricades,
            "signal_overrides": total_signal_overrides,
            "diversion_routes": len(diversions),
            "zones_affected": len(zones_affected),
        },
        "assignments": assignments,
        "barricade_locations": barricade_locations,
        "signal_overrides": signal_overrides,
        "diversions": diversions,
        "zone_breakdown": list(zone_breakdown.values()),
        "whatsapp_alert": whatsapp_alert,
    }


def _generate_diversion_routes(junctions, event):
    """Generate smart diversion route suggestions based on affected junctions."""
    diversions = []
    
    critical_junctions = [j for j in junctions if j["severity"] in ("CRITICAL", "HIGH")]
    
    # Pre-defined Bengaluru diversion knowledge
    diversion_db = {
        "mg_road": [
            {"from": "MG Road (westbound)", "via": "Lavelle Road → Vittal Mallya Road", "saves_min": 15},
            {"from": "MG Road (eastbound)", "via": "Richmond Road → Residency Road", "saves_min": 12},
        ],
        "silk_board": [
            {"from": "Hosur Road (northbound)", "via": "BTM Layout → Bannerghatta Road", "saves_min": 20},
            {"from": "ORR (westbound)", "via": "Sarjapur Road → HSR Layout", "saves_min": 18},
        ],
        "majestic": [
            {"from": "Seshadri Road (eastbound)", "via": "Race Course Road → Palace Road", "saves_min": 10},
            {"from": "Mysore Road (eastbound)", "via": "Chord Road → Rajajinagar", "saves_min": 15},
        ],
        "hebbal": [
            {"from": "Bellary Road (southbound)", "via": "Thanisandra Road → Hennur", "saves_min": 12},
            {"from": "ORR (eastbound)", "via": "Tumkur Road → Yeshwanthpur", "saves_min": 15},
        ],
        "cubbon_park": [
            {"from": "Kasturba Road (northbound)", "via": "Museum Road → Lavelle Road", "saves_min": 8},
            {"from": "Cubbon Road (southbound)", "via": "Vittal Mallya Road → Richmond Circle", "saves_min": 10},
        ],
        "vidhana_soudha": [
            {"from": "Dr. Ambedkar Road", "via": "Race Course Road → Seshadri Road", "saves_min": 10},
        ],
        "freedom_park": [
            {"from": "Seshadri Road (westbound)", "via": "Kasturba Road → Museum Road", "saves_min": 8},
        ],
        "mekhri_circle": [
            {"from": "Bellary Road (southbound)", "via": "Sankey Road → Sadashivanagar", "saves_min": 10},
        ],
        "koramangala": [
            {"from": "80ft Road (eastbound)", "via": "Sarjapur Road → Bellandur", "saves_min": 12},
        ],
        "indiranagar": [
            {"from": "100ft Road (eastbound)", "via": "Old Airport Road → HAL", "saves_min": 10},
        ],
        "whitefield": [
            {"from": "Whitefield Main Road", "via": "Varthur Road → Sarjapur", "saves_min": 15},
        ],
        "kr_puram": [
            {"from": "Old Madras Road", "via": "Hoodi → Marathahalli Bridge", "saves_min": 12},
        ],
        "marathahalli": [
            {"from": "ORR (eastbound)", "via": "Kundalahalli → Brookefield", "saves_min": 10},
        ],
        "brigade_road": [
            {"from": "Brigade Road (southbound)", "via": "Church Street → Rest House Road", "saves_min": 8},
        ],
    }
    
    for cj in critical_junctions:
        jid = cj["junction_id"]
        if jid in diversion_db:
            for div in diversion_db[jid]:
                diversions.append({
                    "junction": cj["name"],
                    "junction_id": jid,
                    "from_direction": div["from"],
                    "via_route": div["via"],
                    "estimated_time_saved_min": div["saves_min"],
                    "lat": cj["lat"],
                    "lon": cj["lon"],
                })
    
    return diversions


def _generate_whatsapp_alert(event, summary, shift_start, shift_end, assignments):
    """Generate a WhatsApp-formatted alert message for field constables."""
    
    critical_names = [a["junction_name"] for a in assignments if a["severity"] == "CRITICAL"]
    high_names = [a["junction_name"] for a in assignments if a["severity"] == "HIGH"]
    
    alert = f"""⚠️ *BTP SPECIAL ALERT — {event['type_name'].upper()}*

📍 *{event['venue']}*
📅 {event['date']} ({event['day_name']})
⏰ Event: {event['time']} | Duty: {shift_start.strftime('%H:%M')} - {shift_end.strftime('%H:%M')}
👥 Expected crowd: {event['expected_crowd']:,}

🔴 *CRITICAL Junctions:*
{chr(10).join(f'  • {n}' for n in critical_names) if critical_names else '  None'}

🟠 *HIGH Impact Junctions:*
{chr(10).join(f'  • {n}' for n in high_names) if high_names else '  None'}

👮 Extra constables needed: {summary['total_extra_constables']}
⏱️ Est. delay WITHOUT deployment: {summary['avg_delay_without_deployment_min']} min
✅ Est. delay WITH deployment: {summary['avg_delay_with_deployment_min']} min
📉 Reduction: {summary['delay_reduction_pct']}%

_Report to assigned junction 30 min before shift start._
_Issued by: ASTraM Traffic Control, BTP_"""
    
    return alert
