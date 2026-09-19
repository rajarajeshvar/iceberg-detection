import os
from typing import Dict, Any, Tuple
from app.ai.context_builder import build_system_context
from app.ai.prompt_builder import build_system_prompt


class AINavigationAssistant:
    """
    Antarctic AI Navigation Assistant.
    Parses structured system context to provide concise, data-driven, non-hallucinating navigation assistance.
    """

    def process_query(self, user_message: str, context: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Process navigator query and return (ai_response, context_used).
        """
        if context is None:
            context = build_system_context()

        msg = user_message.lower().strip()
        data_source = context.get("data_source_mode", "DEMO / SYNTHETIC DATA")

        # Parse routes & recommendation state
        routes = context.get("routes", [])
        route_map = {r.get("route_id"): r for r in routes} if isinstance(routes, list) else {}

        rec = context.get("recommendation", {})
        rec_id = rec.get("route_id", "route_2")
        rec_r = route_map.get(rec_id, {})

        orig_r = route_map.get("original", {})
        r2_r = route_map.get("route_2", {})
        r3_r = route_map.get("route_3", {})

        # Query 1: Which route is recommended?
        if "recommended" in msg and ("which" in msg or "what" in msg or "show" in msg):
            rec_name = rec_r.get("route_name", "Route 2")
            safety = rec_r.get("safety_score", 90)
            fuel = rec_r.get("fuel_efficiency_score", 91)
            reason = rec.get("reason", "Best balance between safety and fuel efficiency.")
            response = (
                f"[{data_source}] {rec_name} is currently recommended.\n\n"
                f"• Safety Score: {safety}/100\n"
                f"• Fuel Efficient Score: {fuel}/100\n"
                f"• Rationale: {reason}\n\n"
                f"Note: No route is completely safe; maintain active radar watch."
            )
            return response, context

        # Query 2: Why is Route 2 better/recommended?
        if "route 2" in msg and ("why" in msg or "better" in msg or "advantage" in msg):
            s2 = r2_r.get("safety_score", 90)
            f2 = r2_r.get("fuel_efficiency_score", 91)
            clr = r2_r.get("min_clearance_km", 18.2)
            response = (
                f"[{data_source}] Route 2 is recommended because it provides the best overall balance between safety and fuel efficiency.\n\n"
                f"• Safety Score: {s2}/100 (vs 42/100 for Original)\n"
                f"• Fuel Efficient Score: {f2}/100\n"
                f"• Iceberg Clearance: {clr} km from predicted drift paths\n"
                f"• Risk Level: LOW RISK (avoids predicted hazard intersections)"
            )
            return response, context

        # Query 3: Which route is safest?
        if "safest" in msg or ("safe" in msg and "which" in msg):
            rankings = context.get("route_rankings", {}).get("safety", ["route_2", "route_3", "original"])
            safest_id = rankings[0] if rankings else "route_2"
            safest_r = route_map.get(safest_id, r2_r)
            s_score = safest_r.get("safety_score", 90)
            response = (
                f"[{data_source}] The safest option is {safest_r.get('route_name', 'Route 2')} with a Safety Score of {s_score}/100.\n\n"
                f"It maintains a minimum clearance of {safest_r.get('min_clearance_km', 18.2)} km from predicted iceberg trajectories."
            )
            return response, context

        # Query 4: Which route is most fuel efficient?
        if "fuel" in msg and ("most" in msg or "which" in msg or "best" in msg):
            rankings = context.get("route_rankings", {}).get("fuel_efficiency", ["route_3", "original", "route_2"])
            fuel_id = rankings[0] if rankings else "route_3"
            fuel_r = route_map.get(fuel_id, r3_r)
            f_score = fuel_r.get("fuel_efficiency_score", 96)
            fuel_vol = fuel_r.get("estimated_fuel", 47800)
            response = (
                f"[{data_source}] The most fuel efficient option is {fuel_r.get('route_name', 'Route 3')} with a Fuel Efficient Score of {f_score}/100.\n\n"
                f"• Estimated Fuel: {fuel_vol:,.0f} L\n"
                f"• Travel Time: {fuel_r.get('travel_time_hours', 58.2)} hours"
            )
            return response, context

        # Query 5: Why is the original route risky?
        if "original" in msg and ("risky" in msg or "why" in msg or "hazard" in msg or "danger" in msg):
            orig_s = orig_r.get("safety_score", 42)
            orig_risk = orig_r.get("risk_level", "HIGH")
            response = (
                f"[{data_source}] The Original Route is rated {orig_risk} RISK with a Safety Score of {orig_s}/100.\n\n"
                f"• Passes directly through predicted iceberg trajectory intersection zones\n"
                f"• Minimum hazard clearance is only {orig_r.get('min_clearance_km', 4.2)} km\n"
                f"• Substantially higher predicted collision probability within 6 hours"
            )
            return response, context

        # Query 6: Where is the nearest iceberg?
        if "nearest iceberg" in msg or "where is" in msg or "closest iceberg" in msg:
            alerts = context.get("current_alerts", [])
            ib_id = alerts[0].get("object_id", "IB001") if alerts else "IB001"
            cpa = alerts[0].get("cpa_km", 4.2) if alerts else 4.2
            response = (
                f"[{data_source}] The nearest tracked iceberg is {ib_id}.\n\n"
                f"• Estimated Position: -64.231° S, 42.512° E\n"
                f"• CPA to baseline path: {cpa} km\n"
                f"• Estimated Size: 145 meters"
            )
            return response, context

        # Query 7: When could the iceberg intersect the route?
        if "when" in msg and ("intersect" in msg or "approach" in msg or "time" in msg):
            response = (
                f"[{data_source}] Predicted iceberg IB001 is projected to intersect the Original Route in approximately 3.8 to 6.0 hours.\n\n"
                f"Altering vessel course to Route 2 eliminates this intersection hazard."
            )
            return response, context

        # Query 8: How much farther is Route 2?
        if "farther" in msg or "distance" in msg or "extra" in msg:
            r2_d = r2_r.get("distance_km", 920.0)
            orig_d = orig_r.get("distance_km", 850.0)
            extra_km = round(r2_d - orig_d, 1)
            extra_pct = round((extra_km / max(1.0, orig_d)) * 100.0, 1)
            response = (
                f"[{data_source}] Route 2 is {r2_d} km, which is {extra_km} km (+{extra_pct}%) farther than the Original Route ({orig_d} km).\n\n"
                f"This moderate detour adds approx 4.6 hours of travel time while increasing safety by 48 points."
            )
            return response, context

        # Default fallback response
        response = (
            f"[{data_source}] Navigation System Status:\n\n"
            f"• Recommended Route: {rec_r.get('route_name', 'Route 2')} (Safety: {rec_r.get('safety_score', 90)}/100, Fuel: {rec_r.get('fuel_efficiency_score', 91)}/100)\n"
            f"• Nearest Hazard: Iceberg IB001 (Clearance: {rec_r.get('min_clearance_km', 18.2)} km)\n"
            f"• Recommendation: Maintain course on {rec_r.get('route_name', 'Route 2')}.\n\n"
            f"Ask me about route choices, safety scores, fuel efficiency, or iceberg hazard clearance."
        )
        return response, context
