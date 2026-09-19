def classify_alert_severity(
    event_type: str,
    cpa_km: float = 50.0,
    tcpa_hours: float = 72.0,
    has_intersection: bool = False,
    min_clearance_km: float = 50.0,
    sea_ice_concentration: float = 0.0
) -> str:
    """
    Classify alert priority/severity level:
    CRITICAL > HIGH > MEDIUM > LOW > INFO
    """
    if event_type == "ROUTE INTERSECTION" or (has_intersection and cpa_km < 5.0 and tcpa_hours <= 6.0):
        return "CRITICAL"

    if event_type == "HIGH COLLISION RISK" or cpa_km < 8.0 or min_clearance_km < 8.0:
        return "HIGH"

    if event_type == "SEA-ICE WARNING" and sea_ice_concentration >= 0.70:
        return "HIGH"

    if event_type == "ROUTE RECOMMENDATION CHANGE" or event_type == "SEA-ICE WARNING" or min_clearance_km < 18.0:
        return "MEDIUM"

    if event_type == "NEW ICEBERG":
        return "LOW" if min_clearance_km < 35.0 else "INFO"

    return "INFO"
