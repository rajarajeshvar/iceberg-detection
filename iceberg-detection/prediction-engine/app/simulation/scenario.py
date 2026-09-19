from typing import Dict, Any


def get_scenario_definition(scenario_type: str, change_percent: float = 20.0) -> Dict[str, Any]:
    """
    Returns scenario definition metadata.
    """
    scenarios = {
        "iceberg_speed": {
            "name": f"Iceberg Speed +{int(change_percent)}%",
            "description": f"Simulates iceberg drifting {int(change_percent)}% faster due to intensified ocean currents."
        },
        "iceberg_heading": {
            "name": "Iceberg Drift Heading Shift",
            "description": "Simulates 15 degree eastward drift angle shift driven by wind gusts."
        },
        "sea_ice": {
            "name": "Sea-Ice Concentration Spike (+20%)",
            "description": "Simulates sea-ice density increasing from 40% to 60% across sector."
        },
        "original_route": {
            "name": "Continue on Original Route",
            "description": "Evaluates hazard exposure and collision risk if vessel stays on baseline course."
        }
    }

    return scenarios.get(scenario_type, {
        "name": f"Custom Scenario ({scenario_type})",
        "description": "Simulated what-if navigational perturbation."
    })
