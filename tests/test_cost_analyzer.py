"""
Tests for the economic model.

The cost-of-inaction figures are the system's argument for deploying resources,
so the arithmetic tying the two scenarios together is checked explicitly.
"""

import pytest

from engine.bengaluru_kb import ECONOMIC_CONSTANTS
from engine.cost_analyzer import calculate_economic_impact
from engine.deployment_generator import generate_deployment_order
from engine.impact_predictor import predict_event_impact

SCENARIO_FIELDS = (
    "fuel_waste", "productivity_loss", "flipkart_delivery_cost", "total_cost",
    "delayed_vehicles", "person_hours_lost", "deliveries_delayed",
    "emergency_response_min", "co2_emissions_kg", "deployment_cost",
)


def test_both_scenarios_report_the_same_fields(economics):
    for scenario in ("without_deployment", "with_deployment"):
        for field in SCENARIO_FIELDS:
            assert field in economics[scenario], f"{scenario} is missing '{field}'"


def test_no_cost_component_is_negative(economics):
    for scenario in ("without_deployment", "with_deployment"):
        for field in SCENARIO_FIELDS:
            assert economics[scenario][field] >= 0, f"{scenario}.{field} went negative"


def test_the_do_nothing_scenario_carries_no_deployment_cost(economics):
    assert economics["without_deployment"]["deployment_cost"] == 0


def test_deployment_reduces_delay_driven_harm(economics):
    without = economics["without_deployment"]
    with_deploy = economics["with_deployment"]

    assert with_deploy["delayed_vehicles"] <= without["delayed_vehicles"]
    assert with_deploy["person_hours_lost"] <= without["person_hours_lost"]
    assert with_deploy["co2_emissions_kg"] <= without["co2_emissions_kg"]
    assert with_deploy["emergency_response_min"] <= without["emergency_response_min"]


def test_emergency_response_never_beats_the_clear_road_baseline(economics):
    """Even fully deployed, response time cannot drop below the unobstructed baseline."""
    baseline = ECONOMIC_CONSTANTS["emergency_vehicle_base_response_min"]
    assert economics["with_deployment"]["emergency_response_min"] >= baseline


def test_investment_components_sum_to_the_total(economics):
    investment = economics["deployment_investment"]
    parts = investment["constable_cost"] + investment["barricade_cost"] + investment["signage_cost"]
    assert investment["total_investment"] == pytest.approx(parts, abs=1.0)


def test_deployment_cost_is_carried_into_the_with_deployment_total(economics):
    """The intervention must be charged for, or the comparison is dishonest."""
    with_deploy = economics["with_deployment"]
    components = (
        with_deploy["fuel_waste"]
        + with_deploy["productivity_loss"]
        + with_deploy["flipkart_delivery_cost"]
        + with_deploy["deployment_cost"]
    )
    assert with_deploy["total_cost"] == pytest.approx(components, abs=2.0)


def test_net_savings_is_the_difference_between_the_two_totals(economics):
    expected = economics["without_deployment"]["total_cost"] - economics["with_deployment"]["total_cost"]
    assert economics["savings"]["net_savings"] == pytest.approx(expected, abs=2.0)


def test_lakhs_conversion_is_consistent(economics):
    savings = economics["savings"]
    assert savings["net_savings_lakhs"] == pytest.approx(savings["net_savings"] / 100000, abs=0.02)


def test_roi_is_consistent_with_savings_and_investment(economics):
    savings = economics["savings"]
    investment = economics["deployment_investment"]["total_investment"]
    if investment > 0:
        expected = (savings["net_savings"] / investment) * 100
        assert savings["roi_percentage"] == pytest.approx(expected, rel=0.02)


def test_flipkart_deliveries_stay_within_the_bengaluru_network_size(economics):
    """Delayed deliveries cannot exceed the modelled citywide delivery volume."""
    ceiling = (
        ECONOMIC_CONSTANTS["flipkart_delivery_zones_bengaluru"]
        * ECONOMIC_CONSTANTS["flipkart_deliveries_per_zone_day"]
    )
    assert economics["without_deployment"]["deliveries_delayed"] <= ceiling


def test_a_negligible_event_does_not_divide_by_zero():
    """A tiny off-peak event may need no deployment at all — ROI must still compute."""
    impact = predict_event_impact("exhibition", "lalbagh", "2026-02-10", "04:00", expected_crowd=50)
    deployment = generate_deployment_order(impact)
    economics = calculate_economic_impact(impact, deployment)

    assert isinstance(economics["savings"]["roi_percentage"], float)
    assert economics["without_deployment"]["total_cost"] >= 0
