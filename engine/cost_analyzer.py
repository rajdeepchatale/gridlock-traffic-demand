"""
Economic Cost Analyzer — Gridlock 2.0 Round 2
Calculates the real-world economic cost of traffic disruption and 
the ROI of deploying BTP resources. Includes Flipkart delivery impact.
"""

from engine.bengaluru_kb import ECONOMIC_CONSTANTS


def calculate_economic_impact(impact_result, deployment_order):
    """
    Computes economic cost analysis comparing scenarios:
    1. No deployment (let traffic chaos happen)
    2. With recommended deployment
    
    Args:
        impact_result: Output from impact_predictor
        deployment_order: Output from deployment_generator
    
    Returns:
        dict with full cost breakdown
    """
    event = impact_result["event"]
    summary = impact_result["impact_summary"]
    junctions = impact_result["junction_impacts"]
    resources = deployment_order["resources"]
    ec = ECONOMIC_CONSTANTS
    
    duration_hours = event["duration_hours"]
    
    # ── Scenario 1: WITHOUT deployment ──
    
    # Fuel waste
    delayed_vehicles = summary["total_delayed_vehicles"]
    avg_delay_hrs = summary["avg_delay_without_deployment_min"] / 60.0
    fuel_waste_no_deploy = delayed_vehicles * avg_delay_hrs * ec["avg_fuel_cost_per_idle_hour"]
    
    # Productivity loss (person-hours)
    person_hours_lost_no_deploy = summary["total_delay_person_hours"]
    productivity_loss_no_deploy = person_hours_lost_no_deploy * ec["avg_wage_per_hour"]
    
    # Flipkart delivery impact
    # Calculate affected delivery zones (zones within impact radius)
    affected_zones_count = min(
        ec["flipkart_delivery_zones_bengaluru"],
        max(1, int(summary["affected_junctions"] * 1.5))  # Each junction affects ~1.5 delivery zones
    )
    deliveries_affected_no_deploy = affected_zones_count * ec["flipkart_deliveries_per_zone_day"]
    # Not all deliveries are delayed — only those during event window
    event_window_fraction = min(1.0, (duration_hours + 2) / 12.0)  # fraction of delivery day affected
    deliveries_delayed_no_deploy = int(deliveries_affected_no_deploy * event_window_fraction * 0.7)
    flipkart_cost_no_deploy = deliveries_delayed_no_deploy * ec["flipkart_delay_cost_per_order"]
    
    # Emergency vehicle delay risk
    emergency_delay_no_deploy = ec["emergency_vehicle_base_response_min"] + summary["avg_delay_without_deployment_min"] * 0.4
    
    # CO2 emissions
    co2_no_deploy = delayed_vehicles * avg_delay_hrs * ec["co2_per_idle_vehicle_hour_kg"]
    
    total_cost_no_deploy = fuel_waste_no_deploy + productivity_loss_no_deploy + flipkart_cost_no_deploy
    
    # ── Scenario 2: WITH deployment ──
    
    # Reduced delays
    avg_delay_with_hrs = summary["avg_delay_with_deployment_min"] / 60.0
    reduction_factor = 1 - (summary["delay_reduction_pct"] / 100.0)
    
    delayed_vehicles_with = int(delayed_vehicles * reduction_factor)
    fuel_waste_with_deploy = delayed_vehicles_with * avg_delay_with_hrs * ec["avg_fuel_cost_per_idle_hour"]
    
    person_hours_with = person_hours_lost_no_deploy * reduction_factor
    productivity_loss_with_deploy = person_hours_with * ec["avg_wage_per_hour"]
    
    deliveries_delayed_with_deploy = int(deliveries_delayed_no_deploy * reduction_factor)
    flipkart_cost_with_deploy = deliveries_delayed_with_deploy * ec["flipkart_delay_cost_per_order"]
    
    emergency_delay_with_deploy = ec["emergency_vehicle_base_response_min"] + summary["avg_delay_with_deployment_min"] * 0.2
    
    co2_with_deploy = delayed_vehicles_with * avg_delay_with_hrs * ec["co2_per_idle_vehicle_hour_kg"]
    
    # Deployment cost (investment)
    shift_hours = deployment_order["shift"]["total_hours"]
    constable_shifts = resources["extra_constables_needed"] * (shift_hours / 8.0)
    deployment_cost = (
        constable_shifts * ec["constable_cost_per_shift"] +
        resources["barricades"] * ec["barricade_setup_cost"] +
        resources["diversion_routes"] * ec["diversion_board_cost"]
    )
    
    total_cost_with_deploy = fuel_waste_with_deploy + productivity_loss_with_deploy + flipkart_cost_with_deploy + deployment_cost
    
    # ── ROI ──
    net_savings = total_cost_no_deploy - total_cost_with_deploy
    roi_percentage = (net_savings / max(deployment_cost, 1)) * 100
    
    return {
        "without_deployment": {
            "fuel_waste": round(fuel_waste_no_deploy),
            "productivity_loss": round(productivity_loss_no_deploy),
            "flipkart_delivery_cost": round(flipkart_cost_no_deploy),
            "total_cost": round(total_cost_no_deploy),
            "delayed_vehicles": delayed_vehicles,
            "person_hours_lost": round(person_hours_lost_no_deploy),
            "deliveries_delayed": deliveries_delayed_no_deploy,
            "emergency_response_min": round(emergency_delay_no_deploy, 1),
            "co2_emissions_kg": round(co2_no_deploy, 1),
            "deployment_cost": 0,
        },
        "with_deployment": {
            "fuel_waste": round(fuel_waste_with_deploy),
            "productivity_loss": round(productivity_loss_with_deploy),
            "flipkart_delivery_cost": round(flipkart_cost_with_deploy),
            "total_cost": round(total_cost_with_deploy),
            "delayed_vehicles": delayed_vehicles_with,
            "person_hours_lost": round(person_hours_with),
            "deliveries_delayed": deliveries_delayed_with_deploy,
            "emergency_response_min": round(emergency_delay_with_deploy, 1),
            "co2_emissions_kg": round(co2_with_deploy, 1),
            "deployment_cost": round(deployment_cost),
        },
        "savings": {
            "net_savings": round(net_savings),
            "net_savings_lakhs": round(net_savings / 100000, 2),
            "roi_percentage": round(roi_percentage, 1),
            "fuel_saved": round(fuel_waste_no_deploy - fuel_waste_with_deploy),
            "productivity_recovered": round(productivity_loss_no_deploy - productivity_loss_with_deploy),
            "flipkart_deliveries_saved": deliveries_delayed_no_deploy - deliveries_delayed_with_deploy,
            "person_hours_recovered": round(person_hours_lost_no_deploy - person_hours_with),
            "emergency_response_improvement_min": round(emergency_delay_no_deploy - emergency_delay_with_deploy, 1),
            "co2_reduced_kg": round(co2_no_deploy - co2_with_deploy, 1),
        },
        "deployment_investment": {
            "constable_cost": round(constable_shifts * ec["constable_cost_per_shift"]),
            "barricade_cost": round(resources["barricades"] * ec["barricade_setup_cost"]),
            "signage_cost": round(resources["diversion_routes"] * ec["diversion_board_cost"]),
            "total_investment": round(deployment_cost),
        },
    }
