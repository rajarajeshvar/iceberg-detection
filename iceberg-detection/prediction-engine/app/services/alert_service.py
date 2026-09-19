import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from fastapi import WebSocket

from app.models.feature4_schemas import AlertItem
from app.decision.severity import classify_alert_severity
from app.utils.time import format_iso


class WebSocketConnectionManager:
    """
    Manages active WebSocket connections for broadcasting real-time navigation alerts.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_alert(self, alert_dict: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(alert_dict)
            except Exception:
                pass


class AlertService:
    """
    Real-Time Alert Engine providing deduplication, severity prioritization, and WebSocket broadcasting.
    """

    SEVERITY_ORDER = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1}

    def __init__(self, ws_manager: Optional[WebSocketConnectionManager] = None):
        self.ws_manager = ws_manager or WebSocketConnectionManager()
        self.alerts_store: Dict[str, AlertItem] = {}
        self.dedup_hashes: Set[str] = set()
        self.counter = 100

        # Initialize default seed alerts for demonstration
        self._seed_default_alerts()

    def _seed_default_alerts(self):
        now_str = format_iso(datetime.now(timezone.utc))

        a1 = AlertItem(
            alert_id="ALT_101",
            event_type="HIGH COLLISION RISK",
            severity="HIGH",
            title="🚨 HIGH COLLISION RISK",
            message="Predicted trajectory for IB001 approaches Original Route within 4.2 hours.",
            object_id="IB001",
            latitude=-64.231,
            longitude=42.512,
            timestamp=now_str,
            status="ACTIVE",
            cpa_km=4.2,
            tcpa_hours=3.8
        )

        a2 = AlertItem(
            alert_id="ALT_102",
            event_type="NEW ICEBERG",
            severity="LOW",
            title="🧊 NEW ICEBERG DETECTED",
            message="Iceberg IB001 detected 28 km away with 94% confidence.",
            object_id="IB001",
            latitude=-64.231,
            longitude=42.512,
            timestamp=now_str,
            status="ACKNOWLEDGED",
            cpa_km=18.2,
            tcpa_hours=12.0
        )

        a3 = AlertItem(
            alert_id="ALT_103",
            event_type="SEA-ICE WARNING",
            severity="MEDIUM",
            title="❄️ SEA-ICE WARNING",
            message="Moderate sea-ice concentration (55%) detected ahead of route sector.",
            object_id="SEA_ICE_01",
            latitude=-64.100,
            longitude=43.000,
            timestamp=now_str,
            status="ACTIVE",
            cpa_km=25.0,
            tcpa_hours=15.0
        )

        for a in [a1, a2, a3]:
            self.alerts_store[a.alert_id] = a
            dedup_key = f"{a.event_type}:{a.object_id}:{a.severity}"
            self.dedup_hashes.add(dedup_key)

    def create_alert(
        self,
        event_type: str,
        title: str,
        message: str,
        object_id: str = None,
        latitude: float = None,
        longitude: float = None,
        cpa_km: float = 50.0,
        tcpa_hours: float = 72.0,
        min_clearance_km: float = 50.0,
        sea_ice_concentration: float = 0.0
    ) -> Optional[AlertItem]:
        """
        Create a new alert with automatic deduplication and severity classification.
        """
        severity = classify_alert_severity(
            event_type=event_type,
            cpa_km=cpa_km,
            tcpa_hours=tcpa_hours,
            min_clearance_km=min_clearance_km,
            sea_ice_concentration=sea_ice_concentration
        )

        dedup_key = f"{event_type}:{object_id}:{severity}"
        if dedup_key in self.dedup_hashes:
            # Skip duplicate alert creation
            return None

        self.dedup_hashes.add(dedup_key)
        self.counter += 1
        alert_id = f"ALT_{self.counter}"
        now_str = format_iso(datetime.now(timezone.utc))

        alert = AlertItem(
            alert_id=alert_id,
            event_type=event_type,
            severity=severity,
            title=title,
            message=message,
            object_id=object_id,
            latitude=latitude,
            longitude=longitude,
            timestamp=now_str,
            status="ACTIVE",
            cpa_km=round(cpa_km, 1),
            tcpa_hours=round(tcpa_hours, 1)
        )

        self.alerts_store[alert_id] = alert

        # Broadcast via WebSocket async queue if active
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.ws_manager.broadcast_alert(alert.model_dump()))
        except Exception:
            pass

        return alert

    def get_active_alerts(self) -> List[AlertItem]:
        """
        Return active alerts sorted by severity priority (CRITICAL > HIGH > MEDIUM > LOW > INFO).
        """
        active = [a for a in self.alerts_store.values() if a.status == "ACTIVE"]
        return sorted(active, key=lambda a: self.SEVERITY_ORDER.get(a.severity, 0), reverse=True)

    def get_alert_history(self) -> List[AlertItem]:
        """
        Return complete alert history sorted by timestamp.
        """
        return sorted(list(self.alerts_store.values()), key=lambda a: a.timestamp, reverse=True)

    def acknowledge_alert(self, alert_id: str) -> Optional[AlertItem]:
        """
        Acknowledge an active alert.
        """
        if alert_id in self.alerts_store:
            alert = self.alerts_store[alert_id]
            alert.status = "ACKNOWLEDGED"
            return alert
        return None
