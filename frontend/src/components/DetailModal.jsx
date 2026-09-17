import { useState } from 'react';
import { X, CheckCircle2, ShieldCheck, FileJson, Navigation, AlertTriangle, ArrowRight, Route } from 'lucide-react';
import SpecularButton from './SpecularButton';

const SAMPLE_RESPONSE = {
  status: "success",
  iceberg_id: "ICE-A68-FRAG",
  detected_at: "2026-09-18T01:45:00Z",
  geometry: {
    length_m: 340.0,
    width_m: 210.0,
    estimated_draft_m: 145.0
  },
  horizons: [
    {
      horizon_hours: 6,
      predicted_lat: -64.285,
      predicted_lon: -59.715,
      uncertainty_radius_km: 1.8,
      confidence_score: 0.984,
      drift_speed_knots: 1.45
    },
    {
      horizon_hours: 12,
      predicted_lat: -64.340,
      predicted_lon: -59.590,
      uncertainty_radius_km: 3.4,
      confidence_score: 0.951,
      drift_speed_knots: 1.52
    },
    {
      horizon_hours: 24,
      predicted_lat: -64.448,
      predicted_lon: -59.340,
      uncertainty_radius_km: 6.2,
      confidence_score: 0.896,
      drift_speed_knots: 1.60
    }
  ],
  risk_assessment: {
    cpa_nm: 1.8,
    tcpa_hours: 3.2,
    severity: "CRITICAL_COLLISION_ALERT",
    recommended_action: "ALTER_COURSE_STARBOARD_18_DEG"
  }
};

const DetailModal = ({ isOpen, onClose, defaultTab = 'route', liveRouteData = null, livePredictionData = null }) => {
  const [tab, setTab] = useState(defaultTab);
  const [dispatched, setDispatched] = useState(false);

  if (!isOpen) return null;

  // Use live data if available, fallback to mock
  const recommendedRoute = liveRouteData?.routes?.find(r => r.route_id === liveRouteData?.recommendation?.route_id) || liveRouteData?.routes?.[1];

  const displayedContract = liveRouteData || livePredictionData || SAMPLE_RESPONSE;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: '780px' }} onClick={e => e.stopPropagation()}>
        <button type="button" className="modal-close-btn" onClick={onClose}>
          <X size={18} />
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: 'rgba(0, 242, 254, 0.15)',
            border: '1px solid rgba(0, 242, 254, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-cyan)'
          }}>
            <ShieldCheck size={20} />
          </div>
          <div>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.3rem', color: '#fff' }}>
              Autonomous Decision & Collision Avoidance
            </h3>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              POLAR SAFETY ADVISORY • FASTAPI LIVE ENGINE
            </span>
          </div>
        </div>

        {/* Tab switcher */}
        <div className="horizon-tabs" style={{ marginBottom: '20px' }}>
          <button
            type="button"
            className={`horizon-tab ${tab === 'route' ? 'active' : ''}`}
            onClick={() => setTab('route')}
          >
            A* Optimal Route Advisory
          </button>
          <button
            type="button"
            className={`horizon-tab ${tab === 'api' ? 'active' : ''}`}
            onClick={() => setTab('api')}
          >
            FastAPI REST Contract {liveRouteData ? '(Live Response)' : ''}
          </button>
        </div>

        {tab === 'route' ? (
          <div>
            <div style={{
              background: 'rgba(244, 63, 94, 0.08)',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              borderRadius: '8px',
              padding: '14px 18px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginBottom: '20px'
            }}>
              <AlertTriangle size={20} color="#f43f5e" />
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f43f5e' }}>
                  {liveRouteData ? liveRouteData.recommendation?.label || 'Route Calculated by Engine' : 'Critical Collision Hazard Detected'}
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                  {liveRouteData
                    ? liveRouteData.recommendation?.reason || 'Engine found optimal safe passage around ice hazards.'
                    : 'Iceberg ICE-A68-FRAG intersects planned vessel trajectory at T+3.2h (CPA: 1.8 NM).'}
                </div>
              </div>
            </div>

            <div className="data-metrics-list" style={{ marginBottom: '20px' }}>
              <div className="data-metric-box">
                <div className="label">Recommended Maneuver</div>
                <div className="value gradient-text-cyan">
                  {recommendedRoute ? `Divert via ${recommendedRoute.route_name}` : 'Starboard +18.4°'}
                </div>
              </div>
              <div className="data-metric-box">
                <div className="label">Safety Score</div>
                <div className="value gradient-text-ice">
                  {recommendedRoute ? `${recommendedRoute.safety_score} / 100` : '95 / 100'}
                </div>
              </div>
              <div className="data-metric-box">
                <div className="label">Distance & Travel Time</div>
                <div className="value" style={{ fontSize: '1rem' }}>
                  {recommendedRoute ? `${recommendedRoute.distance_km} km (${recommendedRoute.travel_time_hours}h)` : '270.5 km (9.7h)'}
                </div>
              </div>
              <div className="data-metric-box">
                <div className="label">Fuel Score</div>
                <div className="value" style={{ color: 'var(--accent-emerald)' }}>
                  {recommendedRoute ? `${recommendedRoute.fuel_efficiency_score} / 100` : '92 / 100'}
                </div>
              </div>
            </div>

            {/* Waypoint Coordinates List */}
            <div style={{
              background: 'rgba(3, 7, 18, 0.7)',
              border: '1px solid rgba(0, 242, 254, 0.2)',
              borderRadius: '8px',
              padding: '12px 16px',
              fontSize: '0.78rem',
              color: 'var(--text-secondary)',
              marginBottom: '24px',
              fontFamily: 'var(--font-mono)',
              maxHeight: '110px',
              overflowY: 'auto'
            }}>
              <div style={{ color: 'var(--accent-cyan)', fontWeight: 600, marginBottom: '4px' }}>
                GENERATED A* WAYPOINT TRAJECTORY ({recommendedRoute?.points?.length || 3} WAYPOINTS):
              </div>
              {recommendedRoute?.points ? (
                recommendedRoute.points.map((pt, i) => (
                  <span key={i} style={{ marginRight: '8px' }}>
                    WP{i + 1}: [{pt.latitude.toFixed(3)}°S, {pt.longitude.toFixed(3)}°E]{i < recommendedRoute.points.length - 1 ? ' →' : ''}
                  </span>
                ))
              ) : (
                <span>WAYPOINTS: WP1 [-64.10°S, -60.80°W] → WP2_DIVERT [-64.22°S, -60.45°W] → WP3 [-64.55°S, -59.80°W]</span>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <SpecularButton
                size="md"
                radius={14}
                tint="#00f2fe"
                tintOpacity={0.15}
                lineColor="#00f2fe"
                baseColor="#083344"
                intensity={1.2}
                onClick={() => setDispatched(true)}
              >
                {dispatched ? (
                  <>
                    <CheckCircle2 size={16} color="#10b981" />
                    <span>Waypoints Transmitted to ECDIS Bridge</span>
                  </>
                ) : (
                  <>
                    <Navigation size={16} />
                    <span>Transmit Waypoints to Bridge</span>
                  </>
                )}
              </SpecularButton>
            </div>
          </div>
        ) : (
          <div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
              JSON payload served directly by FastAPI engine <code style={{ color: 'var(--accent-cyan)' }}>http://127.0.0.1:8000</code>:
            </p>
            <pre style={{
              background: '#020610',
              border: '1px solid rgba(0, 242, 254, 0.2)',
              borderRadius: '8px',
              padding: '16px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
              color: '#38bdf8',
              overflowX: 'auto',
              maxHeight: '300px'
            }}>
              {JSON.stringify(displayedContract, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default DetailModal;
