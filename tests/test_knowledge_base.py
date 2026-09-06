"""
Integrity tests for the Bengaluru knowledge base.

The knowledge base is the static substrate the whole model rests on — a missing
field or a mistyped coordinate silently corrupts every downstream prediction
rather than raising, so it is checked structurally.
"""

import pytest

from engine.bengaluru_kb import (
    BTP_ZONES,
    ECONOMIC_CONSTANTS,
    EVENT_TYPES,
    JUNCTIONS,
    VENUES,
    get_nearby_junctions,
)

# Generous bounding box around Bengaluru — catches swapped or truncated coordinates.
BENGALURU_LAT = (12.7, 13.3)
BENGALURU_LON = (77.3, 77.9)

JUNCTION_FIELDS = ("name", "lat", "lon", "base_capacity", "typical_constables", "road_type", "zone")
EVENT_FIELDS = (
    "name", "icon", "peak_crowd_factor", "vehicle_ratio", "congestion_multiplier",
    "impact_radius_km", "pre_event_surge_hours", "post_event_surge_hours",
    "duration_hours", "barricade_type", "signal_override_needed", "predictability",
)


@pytest.mark.parametrize("junction_id", sorted(JUNCTIONS))
def test_junction_has_complete_record(junction_id):
    junction = JUNCTIONS[junction_id]
    for field in JUNCTION_FIELDS:
        assert field in junction, f"{junction_id} is missing '{field}'"


@pytest.mark.parametrize("junction_id", sorted(JUNCTIONS))
def test_junction_coordinates_are_inside_bengaluru(junction_id):
    junction = JUNCTIONS[junction_id]
    assert BENGALURU_LAT[0] < junction["lat"] < BENGALURU_LAT[1]
    assert BENGALURU_LON[0] < junction["lon"] < BENGALURU_LON[1]


@pytest.mark.parametrize("junction_id", sorted(JUNCTIONS))
def test_junction_capacity_and_staffing_are_positive(junction_id):
    junction = JUNCTIONS[junction_id]
    assert junction["base_capacity"] > 0, "capacity of 0 would divide by zero downstream"
    assert junction["typical_constables"] >= 0


@pytest.mark.parametrize("junction_id", sorted(JUNCTIONS))
def test_junction_zone_resolves_to_a_btp_station(junction_id):
    """Every junction's zone must map to a real division, or orders lose their inspector."""
    assert JUNCTIONS[junction_id]["zone"] in BTP_ZONES


@pytest.mark.parametrize("venue_id", sorted(VENUES))
def test_venue_has_usable_record(venue_id):
    venue = VENUES[venue_id]
    assert venue["name"]
    assert venue["capacity"] > 0
    assert BENGALURU_LAT[0] < venue["lat"] < BENGALURU_LAT[1]
    assert BENGALURU_LON[0] < venue["lon"] < BENGALURU_LON[1]


@pytest.mark.parametrize("event_type", sorted(EVENT_TYPES))
def test_event_template_is_complete(event_type):
    template = EVENT_TYPES[event_type]
    for field in EVENT_FIELDS:
        assert field in template, f"{event_type} is missing '{field}'"


@pytest.mark.parametrize("event_type", sorted(EVENT_TYPES))
def test_event_template_values_are_sane(event_type):
    template = EVENT_TYPES[event_type]
    assert template["impact_radius_km"] > 0
    assert template["congestion_multiplier"] > 0
    assert 0 <= template["vehicle_ratio"] <= 1
    assert template["duration_hours"] > 0
    assert isinstance(template["signal_override_needed"], bool)


@pytest.mark.parametrize("event_type", sorted(EVENT_TYPES))
def test_event_is_either_crowd_draw_or_pure_disruption(event_type):
    """
    Two families of event exist, and the distinction matters downstream.

    Crowd-draw events (matches, rallies, concerts) generate attendee vehicles,
    so both peak_crowd_factor and vehicle_ratio are positive. Disruption events
    (flooding, construction, VIP movement) draw no crowd at all and act purely
    through congestion_multiplier. A disruption event with a nonzero crowd
    factor — or a crowd event with none — would be a data entry error.
    """
    template = EVENT_TYPES[event_type]
    draws_crowd = template["peak_crowd_factor"] > 0

    if draws_crowd:
        assert template["vehicle_ratio"] > 0, "a crowd event must generate vehicles"
    else:
        assert template["vehicle_ratio"] == 0, "a disruption event must not generate vehicles"
        assert template["congestion_multiplier"] > 1, "a disruption event must still disrupt"


@pytest.mark.parametrize("zone_id", sorted(BTP_ZONES))
def test_zone_names_its_station_and_inspector(zone_id):
    zone = BTP_ZONES[zone_id]
    assert zone.get("station")
    assert zone.get("inspector")


@pytest.mark.parametrize("constant", sorted(ECONOMIC_CONSTANTS))
def test_economic_constants_are_positive(constant):
    """A zero or negative constant would invert the cost-of-inaction argument."""
    assert ECONOMIC_CONSTANTS[constant] > 0


def test_nearby_junctions_are_within_radius_and_distance_sorted():
    venue = VENUES["chinnaswamy"]
    nearby = get_nearby_junctions(venue["lat"], venue["lon"], radius_km=3.0)

    assert nearby, "Chinnaswamy should have junctions within 3km"
    distances = [dist for _, dist in nearby]
    assert all(dist <= 3.0 for dist in distances)
    assert distances == sorted(distances)
    assert all(junction_id in JUNCTIONS for junction_id, _ in nearby)


def test_nearby_junctions_radius_is_monotonic():
    """A wider search can never return fewer junctions."""
    venue = VENUES["chinnaswamy"]
    tight = get_nearby_junctions(venue["lat"], venue["lon"], radius_km=2.0)
    wide = get_nearby_junctions(venue["lat"], venue["lon"], radius_km=6.0)
    assert len(wide) >= len(tight)


def test_zero_radius_selects_nothing():
    venue = VENUES["chinnaswamy"]
    assert get_nearby_junctions(venue["lat"], venue["lon"], radius_km=0.0) == []
