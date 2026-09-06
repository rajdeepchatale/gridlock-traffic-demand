"""
Tests for the spatial-temporal impact model.

These pin the model's *invariants* — the relationships that must hold for the
output to be coherent — rather than specific delay figures, which are tuning
constants expected to change.
"""

import pytest

from engine.bengaluru_kb import JUNCTIONS, VENUES
from engine.impact_predictor import (
    _hour_load_profile,
    _time_decay_factor,
    predict_event_impact,
)

DELAY_CAP_MIN = 90.0
SEVERITIES = {"CRITICAL", "HIGH", "MODERATE", "LOW"}


# ── Structure ────────────────────────────────────────────────────────────

def test_returns_all_top_level_sections(impact):
    assert set(impact) == {"event", "seasonality", "impact_summary", "junction_impacts", "timeline"}


def test_unknown_event_type_is_rejected():
    with pytest.raises(ValueError, match="Unknown event type"):
        predict_event_impact("teleportation", "chinnaswamy", "2026-04-15", "19:30")


def test_unparseable_datetime_falls_back_instead_of_raising():
    """A malformed date must degrade to a default rather than break the request."""
    result = predict_event_impact("ipl_match", "chinnaswamy", "not-a-date", "99:99")
    assert result["impact_summary"]["affected_junctions"] >= 0


# ── Spatial behaviour ────────────────────────────────────────────────────

def test_affected_junctions_are_real_and_within_radius(impact):
    radius = impact["event"]["impact_radius_km"]
    for junction in impact["junction_impacts"]:
        assert junction["junction_id"] in JUNCTIONS
        assert junction["distance_km"] <= radius


def test_impact_decays_with_distance(impact):
    """Two junctions at different distances cannot have equal decay."""
    by_distance = sorted(impact["junction_impacts"], key=lambda j: j["distance_km"])
    decays = [j["impact_decay"] for j in by_distance]
    assert decays == sorted(decays, reverse=True), "decay must fall as distance grows"


def test_larger_crowd_widens_the_impact_radius():
    small = predict_event_impact("ipl_match", "chinnaswamy", "2026-04-15", "19:30", expected_crowd=5000)
    large = predict_event_impact("ipl_match", "chinnaswamy", "2026-04-15", "19:30", expected_crowd=60000)
    assert large["event"]["impact_radius_km"] > small["event"]["impact_radius_km"]
    assert len(large["junction_impacts"]) >= len(small["junction_impacts"])


def test_custom_venue_coordinates_are_honoured():
    """Whitefield is far from the city centre, so it must select different junctions."""
    default = predict_event_impact("concert", "custom", "2026-04-15", "19:30")
    whitefield = predict_event_impact(
        "concert", "custom", "2026-04-15", "19:30", custom_lat=12.9698, custom_lon=77.7500
    )
    assert whitefield["event"]["venue_lat"] == 12.9698
    assert default["event"]["venue_lat"] == VENUES["custom"]["lat"]

    default_ids = {j["junction_id"] for j in default["junction_impacts"]}
    whitefield_ids = {j["junction_id"] for j in whitefield["junction_impacts"]}
    assert default_ids != whitefield_ids


# ── Delay model ──────────────────────────────────────────────────────────

def test_delay_never_exceeds_the_cap(impact):
    for junction in impact["junction_impacts"]:
        assert junction["delay_without_deployment_min"] <= DELAY_CAP_MIN


def test_deployment_always_helps_and_never_fully_eliminates_delay(impact):
    """Effectiveness is capped at 60%, so delay must fall but stay positive."""
    for junction in impact["junction_impacts"]:
        without = junction["delay_without_deployment_min"]
        with_deploy = junction["delay_with_deployment_min"]
        assert with_deploy <= without
        if without > 0:
            assert with_deploy > 0
            assert with_deploy >= without * 0.40 - 0.05


def test_capacity_ratio_matches_reported_vehicle_counts(impact):
    for junction in impact["junction_impacts"]:
        expected = junction["total_vehicles_hr"] / junction["capacity"]
        assert junction["capacity_ratio"] == pytest.approx(expected, abs=0.01)


def test_vehicle_counts_are_internally_consistent(impact):
    for junction in impact["junction_impacts"]:
        assert junction["total_vehicles_hr"] == (
            junction["normal_vehicles_hr"] + junction["event_vehicles_hr"]
        )


# ── Severity and staffing ────────────────────────────────────────────────

def test_severity_values_are_from_the_known_set(impact):
    assert {j["severity"] for j in impact["junction_impacts"]} <= SEVERITIES


def test_junctions_are_sorted_most_severe_first(impact):
    order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}
    ranks = [order[j["severity"]] for j in impact["junction_impacts"]]
    assert ranks == sorted(ranks)


def test_low_severity_junctions_need_no_extra_staff(impact):
    for junction in impact["junction_impacts"]:
        if junction["severity"] == "LOW":
            assert junction["extra_constables_needed"] == 0


def test_total_constables_is_normal_plus_extra(impact):
    for junction in impact["junction_impacts"]:
        assert junction["total_constables"] == (
            junction["typical_constables"] + junction["extra_constables_needed"]
        )


def test_summary_counts_match_the_junction_list(impact):
    summary = impact["impact_summary"]
    junctions = impact["junction_impacts"]
    assert summary["affected_junctions"] == len(junctions)
    assert summary["critical_junctions"] == sum(1 for j in junctions if j["severity"] == "CRITICAL")
    assert summary["high_junctions"] == sum(1 for j in junctions if j["severity"] == "HIGH")
    assert summary["total_extra_constables"] == sum(j["extra_constables_needed"] for j in junctions)


# ── Crowd and seasonality ────────────────────────────────────────────────

def test_explicit_crowd_overrides_the_venue_model():
    result = predict_event_impact("ipl_match", "chinnaswamy", "2026-04-15", "19:30", expected_crowd=12345)
    assert result["event"]["expected_crowd"] == 12345


def test_ipl_off_season_scales_the_crowd_down():
    peak = predict_event_impact("ipl_match", "chinnaswamy", "2026-04-15", "19:30")
    off = predict_event_impact("ipl_match", "chinnaswamy", "2026-09-15", "19:30")

    assert peak["seasonality"]["is_official_season"] is True
    assert off["seasonality"]["is_official_season"] is False
    assert off["event"]["expected_crowd"] < peak["event"]["expected_crowd"]
    assert off["seasonality"]["notes"], "an off-season adjustment must be explained to the officer"


# All Wednesdays in 2026, so the weekend factor cannot confound the comparison —
# it feeds the BPR term at the fourth power and swamps the monsoon effect.
DRY_WEDNESDAY = "2026-02-11"
MONSOON_WEDNESDAYS = ["2026-06-17", "2026-07-15", "2026-08-12"]


@pytest.mark.parametrize("monsoon_date", MONSOON_WEDNESDAYS)
def test_monsoon_months_raise_the_delay_multiplier(monsoon_date):
    monsoon = predict_event_impact("concert", "palace_grounds", monsoon_date, "19:30")
    dry = predict_event_impact("concert", "palace_grounds", DRY_WEDNESDAY, "19:30")

    assert monsoon["seasonality"]["monsoon_factor"] == 1.20
    assert dry["seasonality"]["monsoon_factor"] == 1.0
    assert (
        monsoon["impact_summary"]["avg_delay_without_deployment_min"]
        > dry["impact_summary"]["avg_delay_without_deployment_min"]
    )


@pytest.mark.parametrize("monsoon_date", MONSOON_WEDNESDAYS)
def test_monsoon_uplift_matches_the_factor_reported_to_the_officer(monsoon_date):
    """
    The seasonality note tells the officer delay rises 20%, so the realised
    delay must rise by exactly that — no more.

    The uplift was previously applied twice (once inside the proximity term and
    again to the combined delay), producing a 31-43% rise against a stated 20%.
    Junctions pinned to the 90 minute cap are excluded, since the cap truncates
    the ratio rather than the model understating it.
    """
    monsoon = predict_event_impact("concert", "palace_grounds", monsoon_date, "19:30")
    dry = predict_event_impact("concert", "palace_grounds", DRY_WEDNESDAY, "19:30")

    dry_by_id = {j["junction_id"]: j for j in dry["junction_impacts"]}
    compared = 0

    for junction in monsoon["junction_impacts"]:
        baseline = dry_by_id[junction["junction_id"]]["delay_without_deployment_min"]
        wet = junction["delay_without_deployment_min"]
        if wet >= DELAY_CAP_MIN or baseline == 0:
            continue
        assert wet / baseline == pytest.approx(1.20, abs=0.02), junction["junction_id"]
        compared += 1

    assert compared, "no uncapped junctions were available to compare"


def test_disruption_events_generate_no_attendee_vehicles():
    flooding = predict_event_impact("rain_flooding", "chinnaswamy", "2026-07-15", "18:00")
    assert flooding["event"]["vehicles_generated"] == 0
    assert flooding["impact_summary"]["affected_junctions"] > 0, "flooding must still cause impact"


# ── Timeline ─────────────────────────────────────────────────────────────

def test_timeline_covers_the_full_event_window(impact):
    phases = [entry["phase"] for entry in impact["timeline"]]
    assert "Pre-Event Surge" in phases
    assert "Event Active" in phases
    assert "Post-Event Dispersal" in phases


def test_timeline_load_factors_are_bounded(impact):
    for entry in impact["timeline"]:
        assert 0.0 <= entry["load_factor"] <= 1.0


# ── Helper functions ─────────────────────────────────────────────────────

def test_decay_is_one_at_the_centre_and_falls_to_the_edge():
    assert _time_decay_factor(0.0, 5.0) == pytest.approx(1.0)
    assert _time_decay_factor(5.0, 5.0) < _time_decay_factor(1.0, 5.0)


def test_decay_handles_a_zero_radius_without_dividing_by_zero():
    assert _time_decay_factor(1.0, 0.0) == 0.0


@pytest.mark.parametrize("hour", range(24))
def test_hourly_load_profile_is_bounded(hour):
    assert 0.0 < _hour_load_profile(hour) <= 1.0


def test_evening_peak_is_the_busiest_hour():
    assert _hour_load_profile(18) == max(_hour_load_profile(h) for h in range(24))


def test_hour_profile_wraps_instead_of_failing():
    assert _hour_load_profile(24) == _hour_load_profile(0)


# ── Severity colour palette ──────────────────────────────────────────────────

# The engine's colour field is the canonical machine-readable severity value and
# carries the dark-theme hex. The dashboard resolves colour from CSS tokens
# instead, but exports and any non-dashboard consumer rely on this staying
# correct and in step with tokens.css.
SEVERITY_COLOURS = {
    "CRITICAL": "#E5484D",
    "HIGH": "#F2820D",
    "MODERATE": "#E0B400",
    "LOW": "#29A46A",
}


def test_junction_colour_matches_its_severity(impact):
    for junction in impact["junction_impacts"]:
        assert junction["color"] == SEVERITY_COLOURS[junction["severity"]]


def test_engine_colours_match_the_dark_theme_tokens():
    """The engine's hexes must not drift from the token layer."""
    import re
    from pathlib import Path

    tokens_css = Path(__file__).resolve().parent.parent / "static" / "css" / "tokens.css"
    root_block = re.search(r":root\s*\{(.*?)\}", tokens_css.read_text(), re.S).group(1)
    tokens = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9A-Fa-f]{6})\s*;", root_block))

    for severity, colour in SEVERITY_COLOURS.items():
        token = f"--sev-{severity.lower()}"
        assert tokens[token].upper() == colour.upper(), f"{token} drifted from the engine"
