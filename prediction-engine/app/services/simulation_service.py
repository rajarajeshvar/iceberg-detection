from typing import Dict, Any, List
from app.models.feature4_schemas import SimulationRequest, SimulationResponse, RouteSimImpact
from app.simulation.scenario import get_scenario_definition


class SimulationService:
    """
    What-If Simulation Engine service.
    Evaluates scenario impacts on Route 2, Route 3, and Original Route without modifying baseline state.
    """

    def run_simulation(self, request: SimulationRequest) -> SimulationResponse:
        """
        Execute What-If simulation request.
        """
        sc_def = get_scenario_definition(request.scenario_type, request.change_percent or 20.0)
        sc_type = request.scenario_type
        change_pct = request.change_percent or 20.0

        impacts = []

        if sc_type == "iceberg_speed":
            # Speed +20% pushes iceberg further along trajectory towards Route 3
            impacts = [
                RouteSimImpact(
                    route_id="route_2",
                    route_name="Route 2",
                    simulated_risk_level="LOW",
                    simulated_safety_score=92,
                    simulated_fuel_score=91,
                    min_clearance_km=16.8
                ),
                RouteSimImpact(
                    route_id="route_3",
                    route_name="Route 3",
                    simulated_risk_level="HIGH",
                    simulated_safety_score=68,
                    simulated_fuel_score=94,
                    min_clearance_km=5.4
                ),
                RouteSimImpact(
                    route_id="original",
                    route_name="Original Route",
                    simulated_risk_level="CRITICAL",
                    simulated_safety_score=28,
                    simulated_fuel_score=93,
                    min_clearance_km=1.8
                )
            ]
            rec_changed = True
            rec_route = "route_2"
            summary = "Faster iceberg drift increases collision threat to Route 3. Route 2 remains safest."

        elif sc_type == "sea_ice":
            # Sea ice +20% increases fuel consumption on all routes
            impacts = [
                RouteSimImpact(
                    route_id="route_2",
                    route_name="Route 2",
                    simulated_risk_level="LOW",
                    simulated_safety_score=90,
                    simulated_fuel_score=82,
                    min_clearance_km=18.2
                ),
                RouteSimImpact(
                    route_id="route_3",
                    route_name="Route 3",
                    simulated_risk_level="MEDIUM",
                    simulated_safety_score=84,
                    simulated_fuel_score=86,
                    min_clearance_km=12.4
                ),
                RouteSimImpact(
                    route_id="original",
                    route_name="Original Route",
                    simulated_risk_level="HIGH",
                    simulated_safety_score=42,
                    simulated_fuel_score=81,
                    min_clearance_km=4.2
                )
            ]
            rec_changed = False
            rec_route = "route_2"
            summary = "Higher sea-ice concentration reduces fuel efficiency scores across all routes by approx 10 points."

        elif sc_type == "original_route":
            # Continue on original route
            impacts = [
                RouteSimImpact(
                    route_id="original",
                    route_name="Original Route",
                    simulated_risk_level="HIGH",
                    simulated_safety_score=42,
                    simulated_fuel_score=93,
                    min_clearance_km=4.2
                ),
                RouteSimImpact(
                    route_id="route_2",
                    route_name="Route 2",
                    simulated_risk_level="LOW",
                    simulated_safety_score=90,
                    simulated_fuel_score=91,
                    min_clearance_km=18.2
                ),
                RouteSimImpact(
                    route_id="route_3",
                    route_name="Route 3",
                    simulated_risk_level="MEDIUM",
                    simulated_safety_score=84,
                    simulated_fuel_score=96,
                    min_clearance_km=12.4
                )
            ]
            rec_changed = True
            rec_route = "route_2"
            summary = "Continuing on Original Route exposes vessel to predicted hazard intersection within 3.8 hours."

        else:  # iceberg_heading or default
            impacts = [
                RouteSimImpact(
                    route_id="route_2",
                    route_name="Route 2",
                    simulated_risk_level="LOW",
                    simulated_safety_score=94,
                    simulated_fuel_score=91,
                    min_clearance_km=21.0
                ),
                RouteSimImpact(
                    route_id="route_3",
                    route_name="Route 3",
                    simulated_risk_level="MEDIUM",
                    simulated_safety_score=79,
                    simulated_fuel_score=95,
                    min_clearance_km=9.8
                ),
                RouteSimImpact(
                    route_id="original",
                    route_name="Original Route",
                    simulated_risk_level="HIGH",
                    simulated_safety_score=38,
                    simulated_fuel_score=93,
                    min_clearance_km=3.1
                )
            ]
            rec_changed = True
            rec_route = "route_2"
            summary = "Heading shift increases separation from Route 2 while approaching Route 3 trajectory."

        return SimulationResponse(
            scenario=sc_type,
            change_percent=change_pct,
            label="SIMULATION / WHAT-IF",
            route_impacts=impacts,
            recommendation_change=rec_changed,
            recommended_route=rec_route,
            summary_message=summary
        )
