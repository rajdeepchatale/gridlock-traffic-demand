"""
Bengaluru Knowledge Base — Gridlock 2.0 Round 2
Real-world junction network, event venue data, and traffic topology
specific to Bengaluru's road network used by ASTraM / BTP.
"""

# ────────────────────────────────────────────────────────
# Major Junctions — Real Bengaluru intersections tracked by BTP
# Each junction has: name, lat, lon, base_capacity (vehicles/hr),
# typical_constables (normal day), road_type, zone
# ────────────────────────────────────────────────────────
JUNCTIONS = {
    "silk_board": {
        "name": "Silk Board Junction",
        "lat": 12.9172, "lon": 77.6228,
        "base_capacity": 8500, "typical_constables": 6,
        "road_type": "Highway", "zone": "South-East",
        "connects": ["hsr_layout", "btm_layout", "koramangala", "electronic_city"],
    },
    "kr_puram": {
        "name": "KR Puram Junction",
        "lat": 13.0048, "lon": 77.6970,
        "base_capacity": 7200, "typical_constables": 4,
        "road_type": "Highway", "zone": "East",
        "connects": ["whitefield", "mahadevapura", "old_airport_road"],
    },
    "hebbal": {
        "name": "Hebbal Flyover Junction",
        "lat": 13.0358, "lon": 77.5970,
        "base_capacity": 9000, "typical_constables": 5,
        "road_type": "Highway", "zone": "North",
        "connects": ["manyata", "yelahanka", "mekhri_circle"],
    },
    "mekhri_circle": {
        "name": "Mekhri Circle",
        "lat": 12.9988, "lon": 77.5802,
        "base_capacity": 5500, "typical_constables": 3,
        "road_type": "Highway", "zone": "North-Central",
        "connects": ["hebbal", "sadashivanagar", "palace_road"],
    },
    "mg_road": {
        "name": "MG Road / Trinity Circle",
        "lat": 12.9756, "lon": 77.6068,
        "base_capacity": 6000, "typical_constables": 4,
        "road_type": "Street", "zone": "Central",
        "connects": ["brigade_road", "residency_road", "cubbon_park"],
    },
    "brigade_road": {
        "name": "Brigade Road Junction",
        "lat": 12.9716, "lon": 77.6033,
        "base_capacity": 4000, "typical_constables": 3,
        "road_type": "Street", "zone": "Central",
        "connects": ["mg_road", "residency_road", "church_street"],
    },
    "majestic": {
        "name": "Majestic / Kempegowda Bus Station",
        "lat": 12.9779, "lon": 77.5724,
        "base_capacity": 10000, "typical_constables": 8,
        "road_type": "Highway", "zone": "Central-West",
        "connects": ["anand_rao_circle", "mysore_road", "seshadri_road"],
    },
    "anand_rao_circle": {
        "name": "Anand Rao Circle",
        "lat": 12.9850, "lon": 77.5720,
        "base_capacity": 5000, "typical_constables": 3,
        "road_type": "Street", "zone": "Central-West",
        "connects": ["majestic", "race_course_road", "mekhri_circle"],
    },
    "koramangala": {
        "name": "Koramangala / Sony Signal",
        "lat": 12.9352, "lon": 77.6245,
        "base_capacity": 5500, "typical_constables": 3,
        "road_type": "Street", "zone": "South-East",
        "connects": ["silk_board", "hsr_layout", "madiwala"],
    },
    "madiwala": {
        "name": "Madiwala Junction",
        "lat": 12.9226, "lon": 77.6166,
        "base_capacity": 6000, "typical_constables": 3,
        "road_type": "Street", "zone": "South",
        "connects": ["silk_board", "btm_layout", "koramangala"],
    },
    "whitefield": {
        "name": "Whitefield Main Road / ITPL",
        "lat": 12.9698, "lon": 77.7499,
        "base_capacity": 7500, "typical_constables": 4,
        "road_type": "Highway", "zone": "East",
        "connects": ["kr_puram", "marathahalli", "varthur"],
    },
    "marathahalli": {
        "name": "Marathahalli Bridge Junction",
        "lat": 12.9591, "lon": 77.7010,
        "base_capacity": 7000, "typical_constables": 4,
        "road_type": "Highway", "zone": "East",
        "connects": ["whitefield", "bellandur", "kr_puram"],
    },
    "bellandur": {
        "name": "Bellandur Junction",
        "lat": 12.9261, "lon": 77.6760,
        "base_capacity": 6500, "typical_constables": 3,
        "road_type": "Highway", "zone": "South-East",
        "connects": ["marathahalli", "sarjapur_road", "silk_board"],
    },
    "electronic_city": {
        "name": "Electronic City Toll / Flyover",
        "lat": 12.8500, "lon": 77.6657,
        "base_capacity": 8000, "typical_constables": 4,
        "road_type": "Highway", "zone": "South",
        "connects": ["silk_board", "hosur_road", "bommasandra"],
    },
    "manyata": {
        "name": "Manyata Tech Park Gate",
        "lat": 13.0451, "lon": 77.6210,
        "base_capacity": 6000, "typical_constables": 3,
        "road_type": "Street", "zone": "North",
        "connects": ["hebbal", "nagawara", "thanisandra"],
    },
    "yeshwanthpur": {
        "name": "Yeshwanthpur Circle",
        "lat": 13.0220, "lon": 77.5440,
        "base_capacity": 6500, "typical_constables": 4,
        "road_type": "Highway", "zone": "North-West",
        "connects": ["rajajinagar", "malleshwaram", "tumkur_road"],
    },
    "jayanagar": {
        "name": "Jayanagar 4th Block / Cool Joint",
        "lat": 12.9250, "lon": 77.5830,
        "base_capacity": 5000, "typical_constables": 3,
        "road_type": "Street", "zone": "South",
        "connects": ["south_end_circle", "jp_nagar", "lalbagh"],
    },
    "indiranagar": {
        "name": "Indiranagar 100ft Road / CMH",
        "lat": 12.9784, "lon": 77.6408,
        "base_capacity": 5500, "typical_constables": 3,
        "road_type": "Street", "zone": "East-Central",
        "connects": ["old_airport_road", "mg_road", "domlur"],
    },
    "rajajinagar": {
        "name": "Rajajinagar / Chord Road Junction",
        "lat": 12.9910, "lon": 77.5520,
        "base_capacity": 5500, "typical_constables": 3,
        "road_type": "Street", "zone": "West",
        "connects": ["yeshwanthpur", "majestic", "basaveshwaranagar"],
    },
    "bannerghatta_road": {
        "name": "Bannerghatta Road / Arekere",
        "lat": 12.8880, "lon": 77.5970,
        "base_capacity": 6000, "typical_constables": 3,
        "road_type": "Highway", "zone": "South",
        "connects": ["jayanagar", "jp_nagar", "gottigere"],
    },
    "mysore_road": {
        "name": "Mysore Road / Nayandahalli",
        "lat": 12.9570, "lon": 77.5270,
        "base_capacity": 7000, "typical_constables": 4,
        "road_type": "Highway", "zone": "West",
        "connects": ["majestic", "kengeri", "rajarajeshwari_nagar"],
    },
    "cubbon_park": {
        "name": "Cubbon Road / Kasturba Road Junction",
        "lat": 12.9763, "lon": 77.5929,
        "base_capacity": 4500, "typical_constables": 3,
        "road_type": "Street", "zone": "Central",
        "connects": ["mg_road", "vidhana_soudha", "palace_road"],
    },
    "vidhana_soudha": {
        "name": "Vidhana Soudha / Dr. Ambedkar Road",
        "lat": 12.9795, "lon": 77.5907,
        "base_capacity": 4000, "typical_constables": 4,
        "road_type": "Street", "zone": "Central",
        "connects": ["cubbon_park", "freedom_park", "high_court"],
    },
    "freedom_park": {
        "name": "Freedom Park / Seshadri Road",
        "lat": 12.9774, "lon": 77.5752,
        "base_capacity": 4000, "typical_constables": 2,
        "road_type": "Street", "zone": "Central",
        "connects": ["majestic", "vidhana_soudha", "anand_rao_circle"],
    },
    "sarjapur_road": {
        "name": "Sarjapur Road / Wipro Junction",
        "lat": 12.9100, "lon": 77.6850,
        "base_capacity": 5500, "typical_constables": 3,
        "road_type": "Street", "zone": "South-East",
        "connects": ["bellandur", "hsr_layout", "carmelaram"],
    },
    "hsr_layout": {
        "name": "HSR Layout / BDA Junction",
        "lat": 12.9116, "lon": 77.6474,
        "base_capacity": 5000, "typical_constables": 3,
        "road_type": "Street", "zone": "South-East",
        "connects": ["silk_board", "koramangala", "sarjapur_road"],
    },
    "btm_layout": {
        "name": "BTM Layout / Udupi Garden Junction",
        "lat": 12.9166, "lon": 77.6101,
        "base_capacity": 4500, "typical_constables": 2,
        "road_type": "Street", "zone": "South",
        "connects": ["silk_board", "madiwala", "jayanagar"],
    },
    "old_airport_road": {
        "name": "Old Airport Road / HAL",
        "lat": 12.9595, "lon": 77.6482,
        "base_capacity": 6500, "typical_constables": 4,
        "road_type": "Highway", "zone": "East-Central",
        "connects": ["indiranagar", "kr_puram", "domlur"],
    },
}


# ────────────────────────────────────────────────────────
# Event Venues — Real Bengaluru venues where events happen
# ────────────────────────────────────────────────────────
VENUES = {
    "chinnaswamy": {
        "name": "M. Chinnaswamy Stadium",
        "lat": 12.9788, "lon": 77.5996,
        "capacity": 40000,
        "type": "stadium",
        "nearby_junctions": ["mg_road", "cubbon_park", "brigade_road", "vidhana_soudha"],
        "typical_events": ["IPL Cricket", "International Cricket", "Concerts"],
    },
    "kanteerava": {
        "name": "Kanteerava Indoor Stadium",
        "lat": 12.9730, "lon": 77.5958,
        "capacity": 6000,
        "type": "stadium",
        "nearby_junctions": ["mg_road", "cubbon_park", "brigade_road"],
        "typical_events": ["Pro Kabaddi", "Badminton", "Indoor Sports"],
    },
    "palace_grounds": {
        "name": "Palace Grounds",
        "lat": 12.9988, "lon": 77.5802,
        "capacity": 50000,
        "type": "open_ground",
        "nearby_junctions": ["mekhri_circle", "hebbal", "yeshwanthpur", "rajajinagar"],
        "typical_events": ["Concerts", "Exhibitions", "Trade Fairs", "Political Rallies"],
    },
    "freedom_park_venue": {
        "name": "Freedom Park",
        "lat": 12.9774, "lon": 77.5752,
        "capacity": 15000,
        "type": "open_ground",
        "nearby_junctions": ["freedom_park", "majestic", "vidhana_soudha", "anand_rao_circle"],
        "typical_events": ["Political Rallies", "Protests", "Cultural Events"],
    },
    "vidhana_soudha_venue": {
        "name": "Vidhana Soudha",
        "lat": 12.9795, "lon": 77.5907,
        "capacity": 10000,
        "type": "government",
        "nearby_junctions": ["vidhana_soudha", "cubbon_park", "freedom_park"],
        "typical_events": ["Political Events", "Government Functions", "Protests"],
    },
    "lalbagh": {
        "name": "Lalbagh Botanical Garden",
        "lat": 12.9507, "lon": 77.5848,
        "capacity": 25000,
        "type": "park",
        "nearby_junctions": ["jayanagar", "btm_layout", "madiwala"],
        "typical_events": ["Flower Show (Republic Day / Independence Day)", "Festivals"],
    },
    "commercial_street": {
        "name": "Commercial Street",
        "lat": 12.9830, "lon": 77.6082,
        "capacity": 20000,
        "type": "market",
        "nearby_junctions": ["mg_road", "indiranagar", "cubbon_park"],
        "typical_events": ["Festival Shopping Rush", "Sale Events"],
    },
    "dharmaraya_temple": {
        "name": "Dharmaraya Swamy Temple",
        "lat": 12.9621, "lon": 77.5775,
        "capacity": 50000,
        "type": "temple",
        "nearby_junctions": ["majestic", "jayanagar", "btm_layout", "mg_road"],
        "typical_events": ["Karaga Festival (Annual April)", "Religious Processions"],
    },
    "ulsoor_lake": {
        "name": "Ulsoor Lake / Halasuru",
        "lat": 12.9826, "lon": 77.6195,
        "capacity": 15000,
        "type": "open_ground",
        "nearby_junctions": ["mg_road", "indiranagar", "old_airport_road"],
        "typical_events": ["Ganesh Visarjan", "Boating Events"],
    },
    "custom": {
        "name": "Custom Location",
        "lat": 12.9716, "lon": 77.5946,
        "capacity": 10000,
        "type": "custom",
        "nearby_junctions": ["mg_road"],
        "typical_events": [],
    },
}


# ────────────────────────────────────────────────────────
# Event Type Templates — Historical patterns for Bengaluru
# ────────────────────────────────────────────────────────
EVENT_TYPES = {
    "ipl_match": {
        "name": "IPL Cricket Match",
        "icon": "🏏",
        "duration_hours": 5,
        "pre_event_surge_hours": 2.5,
        "post_event_surge_hours": 2.0,
        "peak_crowd_factor": 0.85,        # % of venue capacity that shows up
        "vehicle_ratio": 0.35,             # % of crowd arriving by personal vehicle
        "public_transit_ratio": 0.45,      # % using metro/bus
        "walking_ratio": 0.20,
        "impact_radius_km": 3.0,
        "congestion_multiplier": 2.8,      # times normal traffic
        "predictability": "HIGH",
        "typical_day_time": "evening",
        "barricade_type": "Type-B (Heavy)",
        "signal_override_needed": True,
        "historical_avg_delay_min": 94,
    },
    "political_rally": {
        "name": "Political Rally / Protest March",
        "icon": "📢",
        "duration_hours": 4,
        "pre_event_surge_hours": 1.5,
        "post_event_surge_hours": 1.0,
        "peak_crowd_factor": 0.90,
        "vehicle_ratio": 0.20,
        "public_transit_ratio": 0.30,
        "walking_ratio": 0.50,
        "impact_radius_km": 2.5,
        "congestion_multiplier": 3.5,       # Processions block roads
        "predictability": "MEDIUM",
        "typical_day_time": "morning",
        "barricade_type": "Type-A (Standard)",
        "signal_override_needed": True,
        "historical_avg_delay_min": 65,
    },
    "religious_festival": {
        "name": "Religious Festival / Procession",
        "icon": "🛕",
        "duration_hours": 8,
        "pre_event_surge_hours": 2.0,
        "post_event_surge_hours": 3.0,
        "peak_crowd_factor": 0.95,
        "vehicle_ratio": 0.15,
        "public_transit_ratio": 0.25,
        "walking_ratio": 0.60,
        "impact_radius_km": 4.0,
        "congestion_multiplier": 4.0,       # Procession routes fully blocked
        "predictability": "HIGH",
        "typical_day_time": "all_day",
        "barricade_type": "Type-C (Full Closure)",
        "signal_override_needed": True,
        "historical_avg_delay_min": 120,
    },
    "concert": {
        "name": "Concert / Entertainment Event",
        "icon": "🎵",
        "duration_hours": 4,
        "pre_event_surge_hours": 2.0,
        "post_event_surge_hours": 1.5,
        "peak_crowd_factor": 0.80,
        "vehicle_ratio": 0.50,
        "public_transit_ratio": 0.30,
        "walking_ratio": 0.20,
        "impact_radius_km": 2.0,
        "congestion_multiplier": 2.2,
        "predictability": "HIGH",
        "typical_day_time": "evening",
        "barricade_type": "Type-A (Standard)",
        "signal_override_needed": False,
        "historical_avg_delay_min": 55,
    },
    "exhibition": {
        "name": "Exhibition / Trade Fair",
        "icon": "🎪",
        "duration_hours": 10,
        "pre_event_surge_hours": 1.0,
        "post_event_surge_hours": 1.0,
        "peak_crowd_factor": 0.60,
        "vehicle_ratio": 0.55,
        "public_transit_ratio": 0.30,
        "walking_ratio": 0.15,
        "impact_radius_km": 2.0,
        "congestion_multiplier": 1.8,
        "predictability": "HIGH",
        "typical_day_time": "all_day",
        "barricade_type": "Type-A (Standard)",
        "signal_override_needed": False,
        "historical_avg_delay_min": 35,
    },
    "rain_flooding": {
        "name": "Heavy Rain / Urban Flooding",
        "icon": "🌧️",
        "duration_hours": 6,
        "pre_event_surge_hours": 0.5,
        "post_event_surge_hours": 2.0,
        "peak_crowd_factor": 0.0,
        "vehicle_ratio": 0.0,
        "public_transit_ratio": 0.0,
        "walking_ratio": 0.0,
        "impact_radius_km": 5.0,
        "congestion_multiplier": 5.0,       # Waterlogging = standstill
        "predictability": "LOW",
        "typical_day_time": "afternoon",
        "barricade_type": "Type-C (Full Closure)",
        "signal_override_needed": True,
        "historical_avg_delay_min": 150,
    },
    "construction": {
        "name": "Metro/Road Construction",
        "icon": "🚧",
        "duration_hours": 12,
        "pre_event_surge_hours": 0.0,
        "post_event_surge_hours": 0.0,
        "peak_crowd_factor": 0.0,
        "vehicle_ratio": 0.0,
        "public_transit_ratio": 0.0,
        "walking_ratio": 0.0,
        "impact_radius_km": 1.5,
        "congestion_multiplier": 2.5,
        "predictability": "HIGH",
        "typical_day_time": "all_day",
        "barricade_type": "Type-B (Heavy)",
        "signal_override_needed": True,
        "historical_avg_delay_min": 40,
    },
    "vip_movement": {
        "name": "VIP / VVIP Motorcade",
        "icon": "🚔",
        "duration_hours": 2,
        "pre_event_surge_hours": 1.0,
        "post_event_surge_hours": 0.5,
        "peak_crowd_factor": 0.0,
        "vehicle_ratio": 0.0,
        "public_transit_ratio": 0.0,
        "walking_ratio": 0.0,
        "impact_radius_km": 3.0,
        "congestion_multiplier": 6.0,       # Complete road clearance
        "predictability": "LOW",
        "typical_day_time": "any",
        "barricade_type": "Type-C (Full Closure)",
        "signal_override_needed": True,
        "historical_avg_delay_min": 45,
    },
}


# ────────────────────────────────────────────────────────
# Economic Constants for Bengaluru
# ────────────────────────────────────────────────────────
ECONOMIC_CONSTANTS = {
    "avg_fuel_cost_per_idle_hour": 85.0,      # ₹ per vehicle per hour idling
    "avg_wage_per_hour": 250.0,               # ₹ per person-hour (Bengaluru avg)
    "avg_vehicles_per_junction_peak": 3500,    # vehicles/hour at peak
    "flipkart_deliveries_per_zone_day": 180,   # avg deliveries per delivery zone per day
    "flipkart_delay_cost_per_order": 45.0,     # ₹ cost of delay per order
    "flipkart_delivery_zones_bengaluru": 82,   # total delivery zones
    "emergency_vehicle_base_response_min": 8,  # normal response time (minutes)
    "constable_cost_per_shift": 1800.0,        # ₹ per constable per 8-hour shift
    "barricade_setup_cost": 2500.0,            # ₹ per barricade installation
    "diversion_board_cost": 800.0,             # ₹ per diversion signage
    "co2_per_idle_vehicle_hour_kg": 2.3,       # kg CO2 per vehicle per hour idling
}


# ────────────────────────────────────────────────────────
# BTP Zone Mapping
# ────────────────────────────────────────────────────────
BTP_ZONES = {
    "Central": {"station": "Cubbon Park Traffic Station", "inspector": "TI Central Division"},
    "North": {"station": "Hebbal Traffic Station", "inspector": "TI North Division"},
    "South": {"station": "Jayanagar Traffic Station", "inspector": "TI South Division"},
    "East": {"station": "Whitefield Traffic Station", "inspector": "TI East Division"},
    "West": {"station": "Rajajinagar Traffic Station", "inspector": "TI West Division"},
    "South-East": {"station": "HSR Traffic Station", "inspector": "TI South-East Division"},
    "East-Central": {"station": "Indiranagar Traffic Station", "inspector": "TI East-Central Division"},
    "North-Central": {"station": "Sadashivanagar Traffic Station", "inspector": "TI North-Central Division"},
    "Central-West": {"station": "Majestic Traffic Station", "inspector": "TI Central-West Division"},
    "North-West": {"station": "Yeshwanthpur Traffic Station", "inspector": "TI North-West Division"},
}


def get_nearby_junctions(lat, lon, radius_km=3.0):
    """Find all junctions within radius_km of a given lat/lon using Haversine approx."""
    import math
    nearby = []
    for jid, jdata in JUNCTIONS.items():
        dlat = math.radians(jdata["lat"] - lat)
        dlon = math.radians(jdata["lon"] - lon)
        a = (math.sin(dlat/2)**2 +
             math.cos(math.radians(lat)) * math.cos(math.radians(jdata["lat"])) *
             math.sin(dlon/2)**2)
        dist_km = 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        if dist_km <= radius_km:
            nearby.append((jid, dist_km))
    nearby.sort(key=lambda x: x[1])
    return nearby
