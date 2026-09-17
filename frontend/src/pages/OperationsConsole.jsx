import { useState, useEffect } from 'react';
import { Globe as GlobeIcon, Crosshair, Columns, Wind, Droplets, Compass, AlertTriangle, ShieldCheck, Zap, RefreshCw, Layers, FileCode } from 'lucide-react';
import GlobeView from '../components/GlobeView';
import TacticalRadar from '../components/TacticalRadar';
import BorderGlow from '../components/BorderGlow';
import SpecularButton from '../components/SpecularButton';
import { getTrackedIcebergs, predictIcebergTrajectory, optimizeRoute } from '../services/api';

const HORIZONS = [
  { hours: 6, label: '+6h', uncertaintyKm: 1.8, confidence: 98.4 },
  { hours: 12, label: '+12h', uncertaintyKm: 3.4, confidence: 95.1 },
  { hours: 24, label: '+24h', uncertaintyKm: 6.2, confidence: 89.6 },
  { hours: 48, label: '+48h', uncertaintyKm: 10.8, confidence: 81.2 },
  { hours: 72, label: '+72h', uncertaintyKm: 16.5, confidence: 73.0 }
];

const TARGETS_LIST = [
  {
    id: 'ICE-A68-FRAG',
    name: 'A-68 Tabular Fragment',
    lat: -64.40,
    lon: -59.80,
    length: 340,
    mass: '4.82 Mt',
    driftSpeed: 1.45,
    cpaNm: 1.8,
    tcpaHours: 3.2,
    risk: 'CRITICAL',
    leewayAngle: 28.4
  },
  {
    id: 'ICE-B15-OMEGA',
    name: 'B-15 Calved Spire',
    lat: -66.10,
    lon: -62.40,
    length: 165,
    mass: '1.14 Mt',
    driftSpeed: 0.95,
    cpaNm: 5.4,
    tcpaHours: 7.8,
    risk: 'MODERATE',
    leewayAngle: 24.1
  },
  {
    id: 'BERGY-BIT-402',
    name: 'Bergy Bit Cluster',
    lat: -63.70,
    lon: -60.80,
    length: 42,
    mass: '0.06 Mt',
    driftSpeed: 1.80,
    cpaNm: 8.9,
    tcpaHours: 11.5,
    risk: 'ADVISORY',
    leewayAngle: 31.8
  }
];

const OperationsConsole = ({ onCalculateRoute, onInspectApi }) => {
  const [viewMode, setViewMode] = useState('globe');
  const [targets, setTargets] = useState(TARGETS_LIST);
  const [selectedTarget, setSelectedTarget] = useState(TARGETS_LIST[0]);
  const [selectedHorizon, setSelectedHorizon] = useState(HORIZONS[0]);
  const [livePredictions, setLivePredictions] = useState(null);
  const [loadingRoute, setLoadingRoute] = useState(false);

  // Hydrodynamic parameters
  const [windSpeed, setWindSpeed] = useState(24);
  const [windDir, setWindDir] = useState(270);
  const [currentSpeed, setCurrentSpeed] = useState(0.48);
  const [seaIceConc, setSeaIceConc] = useState(42);

  // On mount: fetch registered icebergs from FastAPI backend
  useEffect(() => {
    async function loadBackendIcebergs() {
      const res = await getTrackedIcebergs();
      if (res && res.icebergs && res.icebergs.length > 0) {
        const backendMapped = res.icebergs.map(ib => ({
          id: ib.iceberg_id,
          name: `${ib.iceberg_id} (Tracked)`,
          lat: ib.latest_latitude,
          lon: ib.latest_longitude,
          length: ib.size_m || 150,
          mass: `${((ib.size_m || 150) * 0.012).toFixed(2)} Mt`,
          driftSpeed: 1.25,
          cpaNm: 2.4,
          tcpaHours: 4.1,
          risk: 'CRITICAL',
          leewayAngle: 26.5
        }));
        const combined = [...TARGETS_LIST, ...backendMapped];
        const unique = Array.from(new Map(combined.map(item => [item.id, item])).values());
        setTargets(unique);
      }
    }
    loadBackendIcebergs();
  }, []);

  // When target changes, optionally query ML predictions from backend
  useEffect(() => {
    async function runMLPrediction() {
      const res = await predictIcebergTrajectory({
        iceberg_id: selectedTarget.id,
        latitude: selectedTarget.lat,
        longitude: selectedTarget.lon,
        size_m: selectedTarget.length
      });
      if (res) {
        setLivePredictions(res);
      }
    }
    runMLPrediction();
  }, [selectedTarget]);

  // Handle route calculation via live backend A* engine
  const handleTriggerRouteOptimization = async () => {
    setLoadingRoute(true);
    const result = await optimizeRoute({
      targetId: selectedTarget.id,
      lat: selectedTarget.lat,
      lon: selectedTarget.lon,
      size_m: selectedTarget.length
    });
    setLoadingRoute(false);
    if (onCalculateRoute) {
      onCalculateRoute(result, livePredictions);
    }
  };

  // Derived drift calculations (using live predictions if available)
  const activePred = livePredictions?.predictions?.find(p => p.hours_ahead === selectedHorizon.hours);
  const predictedLat = activePred ? activePred.latitude.toFixed(3) : (selectedTarget.lat - (selectedTarget.driftSpeed * selectedHorizon.hours * 0.008)).toFixed(3);
  const predictedLon = activePred ? activePred.longitude.toFixed(3) : (selectedTarget.lon + (selectedTarget.driftSpeed * selectedHorizon.hours * 0.015)).toFixed(3);
  const uncertaintyRadius = activePred ? activePred.uncertainty_radius_km : selectedHorizon.uncertaintyKm;
  const confidenceScore = activePred ? (activePred.confidence * 100).toFixed(1) : selectedHorizon.confidence;

  return (
    <div className="console-container" style={{ paddingTop: '86px', paddingBottom: '60px', minHeight: '100vh' }}>
      <div className="container" style={{ maxWidth: '1440px' }}>
        {/* Top Operational Command Bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
          marginBottom: '24px',
          padding: '16px 24px',
          background: 'rgba(6, 16, 36, 0.85)',
          backdropFilter: 'blur(16px)',
          border: '1px solid rgba(0, 242, 254, 0.25)',
          borderRadius: '16px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, rgba(0, 242, 254, 0.2), rgba(99, 102, 241, 0.2))',
              border: '1px solid rgba(0, 242, 254, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-cyan)'
            }}>
              <Compass size={22} />
            </div>
            <div>
              <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', fontWeight: 700, color: '#fff', margin: 0 }}>
                Operations Console & Autonomous Decision Deck
              </h1>
              <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                FEATURE 2 PREDICTION ENGINE • CORIOLIS + EKMAN DRIFT + A* ROUTING
              </span>
            </div>
          </div>

          {/* View Mode Toggle: 3D Globe vs Tactical Radar vs Split */}
          <div style={{
            display: 'flex',
            background: 'rgba(3, 7, 18, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '10px',
            padding: '4px'
          }}>
            <button
              type="button"
              onClick={() => setViewMode('globe')}
              style={{
                background: viewMode === 'globe' ? 'rgba(0, 242, 254, 0.2)' : 'transparent',
                border: `1px solid ${viewMode === 'globe' ? 'var(--accent-cyan)' : 'transparent'}`,
                color: viewMode === 'globe' ? '#fff' : 'var(--text-muted)',
                borderRadius: '8px',
                padding: '8px 14px',
                fontSize: '0.8rem',
                fontFamily: 'var(--font-mono)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <GlobeIcon size={14} color={viewMode === 'globe' ? '#00f2fe' : 'currentColor'} />
              <span>3D Globe (react-globe.gl)</span>
            </button>

            <button
              type="button"
              onClick={() => setViewMode('radar')}
              style={{
                background: viewMode === 'radar' ? 'rgba(0, 242, 254, 0.2)' : 'transparent',
                border: `1px solid ${viewMode === 'radar' ? 'var(--accent-cyan)' : 'transparent'}`,
                color: viewMode === 'radar' ? '#fff' : 'var(--text-muted)',
                borderRadius: '8px',
                padding: '8px 14px',
                fontSize: '0.8rem',
                fontFamily: 'var(--font-mono)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <Crosshair size={14} color={viewMode === 'radar' ? '#00f2fe' : 'currentColor'} />
              <span>ARPA Tactical Radar</span>
            </button>

            <button
              type="button"
              onClick={() => setViewMode('split')}
              style={{
                background: viewMode === 'split' ? 'rgba(0, 242, 254, 0.2)' : 'transparent',
                border: `1px solid ${viewMode === 'split' ? 'var(--accent-cyan)' : 'transparent'}`,
                color: viewMode === 'split' ? '#fff' : 'var(--text-muted)',
                borderRadius: '8px',
                padding: '8px 14px',
                fontSize: '0.8rem',
                fontFamily: 'var(--font-mono)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <Columns size={14} color={viewMode === 'split' ? '#00f2fe' : 'currentColor'} />
              <span>Dual Split View</span>
            </button>
          </div>
        </div>

        {/* Main Workstation Layout */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: viewMode === 'split' ? '1fr' : '1.75fr 1fr',
          gap: '24px'
        }}>
          {/* Left Column: Visualizers */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {viewMode === 'globe' && (
              <div style={{ height: '660px', width: '100%' }}>
                <GlobeView onSelectIceberg={ib => {
                  const match = TARGETS_LIST.find(t => t.id === ib.id);
                  if (match) setSelectedTarget(match);
                }} />
              </div>
            )}

            {viewMode === 'radar' && (
              <div style={{ height: '660px', width: '100%' }}>
                <TacticalRadar
                  selectedTargetId={selectedTarget.id}
                  onSelectTarget={t => {
                    const match = TARGETS_LIST.find(tl => tl.id === t.id);
                    if (match) setSelectedTarget(match);
                  }}
                />
              </div>
            )}

            {viewMode === 'split' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', minHeight: '600px' }}>
                <div style={{ height: '600px' }}>
                  <GlobeView onSelectIceberg={ib => {
                    const match = TARGETS_LIST.find(t => t.id === ib.id);
                    if (match) setSelectedTarget(match);
                  }} />
                </div>
                <div style={{ height: '600px' }}>
                  <TacticalRadar
                    selectedTargetId={selectedTarget.id}
                    onSelectTarget={t => {
                      const match = TARGETS_LIST.find(tl => tl.id === t.id);
                      if (match) setSelectedTarget(match);
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Hydrodynamic Controls & Prediction Engine */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Target Selection Bar */}
            <BorderGlow
              edgeSensitivity={28}
              glowColor="185 100 65"
              backgroundColor="rgba(7, 19, 36, 0.85)"
              borderRadius={16}
              glowRadius={30}
              glowIntensity={1.2}
              coneSpread={28}
              colors={['#00f2fe', '#38bdf8', '#818cf8']}
            >
              <div style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <span style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                    TARGET HAZARD SELECTION
                  </span>
                  <span style={{
                    fontSize: '0.7rem',
                    fontFamily: 'var(--font-mono)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    backgroundColor: selectedTarget.risk === 'CRITICAL' ? 'rgba(244, 63, 94, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                    color: selectedTarget.risk === 'CRITICAL' ? '#f43f5e' : '#f59e0b',
                    border: `1px solid ${selectedTarget.risk === 'CRITICAL' ? 'rgba(244, 63, 94, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`
                  }}>
                    {selectedTarget.risk} RISK
                  </span>
                </div>

                <div style={{ display: 'flex', gap: '8px', marginBottom: '14px', flexWrap: 'wrap' }}>
                  {targets.map(t => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setSelectedTarget(t)}
                      style={{
                        flex: '1 1 30%',
                        minWidth: '90px',
                        background: selectedTarget.id === t.id ? 'rgba(0, 242, 254, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                        border: `1px solid ${selectedTarget.id === t.id ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.08)'}`,
                        color: selectedTarget.id === t.id ? '#fff' : 'var(--text-muted)',
                        borderRadius: '8px',
                        padding: '8px 6px',
                        fontSize: '0.72rem',
                        fontFamily: 'var(--font-mono)',
                        cursor: 'pointer'
                      }}
                    >
                      {t.id}
                    </button>
                  ))}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>
                  <div style={{ background: 'rgba(3, 7, 18, 0.4)', padding: '8px', borderRadius: '6px' }}>
                    <div style={{ color: 'var(--text-muted)' }}>Dimensions</div>
                    <div style={{ color: '#fff', fontWeight: 600 }}>{selectedTarget.length}m • {selectedTarget.mass}</div>
                  </div>
                  <div style={{ background: 'rgba(3, 7, 18, 0.4)', padding: '8px', borderRadius: '6px' }}>
                    <div style={{ color: 'var(--text-muted)' }}>Current Coords</div>
                    <div style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>{selectedTarget.lat}° S, {selectedTarget.lon}° W</div>
                  </div>
                </div>
              </div>
            </BorderGlow>

            {/* Trajectory Prediction Horizons */}
            <BorderGlow
              edgeSensitivity={28}
              glowColor="195 95 65"
              backgroundColor="rgba(7, 19, 36, 0.85)"
              borderRadius={16}
              glowRadius={30}
              glowIntensity={1.2}
              coneSpread={28}
              colors={['#38bdf8', '#00f2fe', '#06b6d4']}
            >
              <div style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                    PREDICTION HORIZON (+6h TO +72h)
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                    Conf: {selectedHorizon.confidence}%
                  </span>
                </div>

                <div className="horizon-tabs" style={{ marginBottom: '16px' }}>
                  {HORIZONS.map(h => (
                    <button
                      key={h.hours}
                      type="button"
                      className={`horizon-tab ${selectedHorizon.hours === h.hours ? 'active' : ''}`}
                      onClick={() => setSelectedHorizon(h)}
                    >
                      {h.label}
                    </button>
                  ))}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div className="data-metric-box">
                    <div className="label">Predicted Coordinates</div>
                    <div className="value gradient-text-cyan" style={{ fontSize: '0.95rem' }}>
                      {predictedLat}° S, {predictedLon}° W
                    </div>
                  </div>
                  <div className="data-metric-box">
                    <div className="label">Uncertainty Radius (R_unc)</div>
                    <div className="value gradient-text-ice" style={{ fontSize: '1.05rem' }}>
                      {selectedHorizon.uncertaintyKm} km
                    </div>
                  </div>
                </div>
              </div>
            </BorderGlow>

            {/* Hydrodynamic Environmental Model Variables */}
            <BorderGlow
              edgeSensitivity={28}
              glowColor="235 90 70"
              backgroundColor="rgba(7, 19, 36, 0.85)"
              borderRadius={16}
              glowRadius={30}
              glowIntensity={1.2}
              coneSpread={28}
              colors={['#818cf8', '#c084fc', '#38bdf8']}
            >
              <div style={{ padding: '20px' }}>
                <span style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', display: 'block', marginBottom: '14px' }}>
                  HYDRODYNAMIC DRAG & FORCING INPUTS
                </span>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', marginBottom: '4px' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-secondary)' }}>
                        <Wind size={12} /> Wind Speed & Deflection
                      </span>
                      <span style={{ color: 'var(--accent-cyan)' }}>{windSpeed} kts @ {windDir}° (Leeway {selectedTarget.leewayAngle}°)</span>
                    </div>
                    <input
                      type="range"
                      min="5"
                      max="60"
                      value={windSpeed}
                      onChange={e => setWindSpeed(Number(e.target.value))}
                      style={{ width: '100%', accentColor: '#00f2fe' }}
                    />
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', marginBottom: '4px' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-secondary)' }}>
                        <Droplets size={12} /> Ocean Current Speed
                      </span>
                      <span style={{ color: 'var(--accent-cyan)' }}>{currentSpeed} m/s</span>
                    </div>
                    <input
                      type="range"
                      min="0.1"
                      max="2.0"
                      step="0.05"
                      value={currentSpeed}
                      onChange={e => setCurrentSpeed(Number(e.target.value))}
                      style={{ width: '100%', accentColor: '#00f2fe' }}
                    />
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', marginBottom: '4px' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Sea-Ice Concentration Pack</span>
                      <span style={{ color: seaIceConc > 60 ? '#f43f5e' : '#38bdf8' }}>{seaIceConc}% Concentration</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={seaIceConc}
                      onChange={e => setSeaIceConc(Number(e.target.value))}
                      style={{ width: '100%', accentColor: seaIceConc > 60 ? '#f43f5e' : '#38bdf8' }}
                    />
                  </div>
                </div>
              </div>
            </BorderGlow>

            {/* Actions & Decision Support Button */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '4px' }}>
              <SpecularButton
                size="lg"
                radius={16}
                tint="#00f2fe"
                tintOpacity={0.16}
                blur={8}
                textColor="#ffffff"
                lineColor="#00f2fe"
                baseColor="#083344"
                intensity={1.3}
                shineSize={14}
                thickness={1.3}
                onClick={handleTriggerRouteOptimization}
                disabled={loadingRoute}
                style={{ width: '100%' }}
              >
                <Zap size={18} />
                <span>{loadingRoute ? 'Computing A* Route via FastAPI...' : 'Calculate A* Collision Avoidance Route'}</span>
              </SpecularButton>

              <SpecularButton
                size="md"
                radius={16}
                tint="#0a192f"
                tintOpacity={0.4}
                blur={10}
                textColor="#e0f2fe"
                lineColor="#38bdf8"
                baseColor="#1e293b"
                intensity={1.0}
                onClick={onInspectApi}
                style={{ width: '100%' }}
              >
                <FileCode size={16} />
                <span>Inspect FastAPI REST Contract & Schema</span>
              </SpecularButton>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OperationsConsole;
