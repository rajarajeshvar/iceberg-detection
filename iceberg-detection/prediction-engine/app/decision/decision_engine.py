from typing import List, Dict, Any
from app.decision.severity import classify_alert_severity
from app.decision.explanation import generate_explainable_recommendation_reason


class NavigationDecisionEngine:
    """
    Consumes outputs from Feature 1 (Detection), Feature 2 (Prediction), and Feature 3 (Risk & Routing).
    Converts raw system data into navigation decisions, alert assessments, and explainable recommendations.
    Does NOT recalculate pathfinding or primary ML models.
    """

    def evaluate_navigation_state(
        self,
        routes: List[Dict[str, Any]],
        recommendation: Dict[str, Any],
        icebergs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate overall navigation status: acceptability, review warnings, recommended route.
        """
        route_map = {r["route_id"]: r for r in routes}
        orig_r = route_map.get("original", {})
        rec_id = recommendation.get("route_id", "route_2")
        rec_r = route_map.get(rec_id, {})

        is_original_acceptable = orig_r.get("risk_level") == "LOW" and orig_r.get("safety_score", 0) >= 75
        should_review = not is_original_acceptable

        return {
            "is_current_route_acceptable": is_original_acceptable,
            "should_navigator_review": should_review,
            "recommended_route_id": rec_id,
            "recommended_route_name": rec_r.get("route_name", "Route 2"),
            "recommendation_reason": recommendation.get("reason", "Best balance between safety and fuel efficiency.")
        }
