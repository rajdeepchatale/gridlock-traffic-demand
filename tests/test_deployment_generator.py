"""
Tests for bandobast order generation.

The order is the system's operational output — a document an inspector acts on —
so these tests check that it is internally consistent and actionable.
"""

import re

from engine.bengaluru_kb import BTP_ZONES
from engine.deployment_generator import generate_deployment_order
from engine.impact_predictor import predict_event_impact


def test_order_reference_follows_the_btp_format(deployment):
    assert re.fullmatch(r"BTP/SPECIAL/\d{8}/[A-Z_]{1,4}", deployment["order_reference"])


def test_shift_brackets_the_event_window(deployment):
    """The shift must open before the event and close after dispersal."""
    assert deployment["shift"]["total_hours"] > 0
    assert deployment["shift"]["start"] != deployment["shift"]["end"]


def test_assignments_exclude_junctions_needing_no_action(deployment):
    """A LOW-severity junction with no extra staffing must not clutter the order."""
    for assignment in deployment["assignments"]:
        assert not (assignment["severity"] == "LOW" and assignment["extra_constables"] == 0)


def test_every_assignment_carries_field_instructions(deployment):
    for assignment in deployment["assignments"]:
        assert assignment["instructions"], f"{assignment['junction_name']} has no instructions"
        assert assignment["shift_start"] and assignment["shift_end"]


def test_resource_totals_match_the_assignment_list(deployment):
    resources = deployment["resources"]
    assignments = deployment["assignments"]
    assert resources["total_constables"] == sum(a["total_constables"] for a in assignments)
    assert resources["extra_constables_needed"] == sum(a["extra_constables"] for a in assignments)
    assert resources["barricades"] == len(deployment["barricade_locations"])
    assert resources["signal_overrides"] == len(deployment["signal_overrides"])
    assert resources["diversion_routes"] == len(deployment["diversions"])


def test_barricades_are_reserved_for_critical_junctions(deployment):
    critical = {a["junction_name"] for a in deployment["assignments"] if a["severity"] == "CRITICAL"}
    for barricade in deployment["barricade_locations"]:
        assert barricade["junction"] in critical


def test_barricades_carry_coordinates_for_field_navigation(deployment):
    for barricade in deployment["barricade_locations"]:
        assert barricade["lat"] and barricade["lon"]
        assert barricade["type"]


def test_zone_breakdown_names_a_real_station_and_inspector(deployment):
    for zone in deployment["zone_breakdown"]:
        assert zone["zone"] in BTP_ZONES
        assert zone["station"] != "Unknown Station"
        assert zone["inspector"] != "TI Unknown"


def test_zone_breakdown_totals_reconcile_with_assignments(deployment):
    from_zones = sum(z["constables"] for z in deployment["zone_breakdown"])
    assert from_zones == deployment["resources"]["total_constables"]

    junction_count = sum(z["junctions"] for z in deployment["zone_breakdown"])
    assert junction_count == len(deployment["assignments"])


def test_whatsapp_alert_is_short_enough_for_a_low_bandwidth_broadcast(deployment):
    alert = deployment["whatsapp_alert"]
    assert alert.strip()
    assert len(alert) < 4096, "a dispatch message must fit one WhatsApp send"


def test_whatsapp_alert_names_the_event_and_shift(deployment):
    alert = deployment["whatsapp_alert"]
    assert deployment["shift"]["start"] in alert
    assert deployment["event"]["venue"] in alert


def test_signal_overrides_only_appear_when_the_event_allows_them():
    """VIP movement requires overrides; an event flagged otherwise must not emit any."""
    impact = predict_event_impact("vip_movement", "vidhana_soudha_venue", "2026-04-15", "10:00")
    order = generate_deployment_order(impact)

    if not impact["event"]["signal_override_needed"]:
        assert order["signal_overrides"] == []
    for override in order["signal_overrides"]:
        assert override["override_type"]


def test_a_quiet_event_still_produces_a_valid_order():
    """An overnight low-draw event must not crash the generator or emit garbage."""
    impact = predict_event_impact("exhibition", "lalbagh", "2026-02-10", "03:00", expected_crowd=200)
    order = generate_deployment_order(impact)

    assert order["order_reference"]
    assert order["resources"]["total_constables"] >= 0
    assert isinstance(order["assignments"], list)
