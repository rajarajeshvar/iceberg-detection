import { useState, useEffect } from 'react';
import { 
  Globe as GlobeIcon, 
  Crosshair, 
  Columns, 
  Satellite, 
  Wind, 
  Droplets, 
  Compass, 
  AlertTriangle, 
  ShieldCheck, 
  Zap, 
  RefreshCw, 
  Layers, 
  FileCode 
} from 'lucide-react';
import GlobeView from '../components/GlobeView';
import TacticalRadar from '../components/TacticalRadar';
import SARSatelliteDeck from '../components/SARSatelliteDeck';
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

const DEFAULT_TARGETS_LIST = [
  {
    id: 'IB-S1-001',
    name: 'IB-S1-001 (Sentinel-1 SAR)',
    lat: 68.5736,
    lon: -32.5312,
    bearingDeg: 42,
    rangeNm: 3.2,
    length: 200,
    width: 160,
    area_km2: 0.0448,
    mass: '2.01 Mt',
    driftSpeed: 1.45,
    cpaNm: 1.8,
    tcpaHours: 3.2,
    risk: 'CRITICAL',
    leewayAngle: 28.4
  },
  {
    id: 'IB-S1-002',
    name: 'IB-S1-002 (Sentinel-1 SAR)',
    lat: 68.5221,
    lon: -32.5262,
    bearingDeg: 165,
    rangeNm: 4.8,
    length: 160,
    width: 120,
    area_km2: 0.028,
    mass: '1.26 Mt',
    driftSpeed: 0.95,
    cpaNm: 4.4,
    tcpaHours: 6.8,
    risk: 'MODERATE',
    leewayAngle: 24.1
  }
];

const OperationsConsole = ({ onCalculateRoute, onInspectApi }) => {
  const [viewMode, setViewMode] = useState('globe');
  const [targets, setTargets] = useState(DEFAULT_TARGETS_LIST);
  const [selectedTarget, setSelectedTarget] = useState(DEFAULT_TARGETS_LIST[0]);
  const [selectedHorizon, setSelectedHorizon] = useState(HORIZONS[2]); // Default +24h
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
        const backendMapped = res.icebergs.map((ib, idx) => ({
          id: ib.iceberg_id,
          name: `${ib.iceberg_id} (Tracked)`,
          lat: Number(ib.latest_latitude),
          lon: Number(ib.latest_longitude),
          bearingDeg: Math.round(35 + idx * 45) % 360,
          rangeNm: Number((2.5 + (idx % 4) * 1.8).toFixed(1)),
          length: ib.size_m || 150,
          mass: `${((ib.size_m || 150) * 0.012).toFixed(2)} Mt`,
          driftSpeed: 1.25,
          cpaNm: 2.4,
          tcpaHours: 4.1,
          risk: 'CRITICAL',
          leewayAngle: 26.5
        }));
        const combined = [...backendMapped, ...DEFAULT_TARGETS_LIST];
        const unique = Array.from(new Map(combined.map(item => [item.id, item])).values());
        setTargets(unique);
      }
    }
    loadBackendIcebergs();
  }, []);

  // When target changes, query ML predictions from backend
  useEffect(() => {
    async function runMLPrediction() {
      if (!selectedTarget) return;
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

  // Handle ingestion of new SAR-detected icebergs with accurate polar and GPS mapping
  const handleIngestIcebergs = (detectedIcebergs, metadata) => {
    if (!detectedIcebergs || detectedIcebergs.length === 0) return;

    const mapped = detectedIcebergs.map((ib) => {
      const cx = ib.centroid_pixel ? ib.centroid_pixel.x : 128;
      const cy = ib.centroid_pixel ? ib.centroid_pixel.y : 128;
      
      const dxM = (cx - 128) * 40.0;
      const dyM = (128 - cy) * 40.0;
      const distM = Math.sqrt(dxM * dxM + dyM * dyM);
      const rangeNm = Math.max(0.4, Number((distM / 1852.0).toFixed(2)));
      const bearingDeg = Math.round((Math.atan2(dxM, dyM) * 180 / Math.PI + 360) % 360);

      const lat = Number(ib.latitude);
      const lon = Number(ib.longitude);

      return {
        id: ib.iceberg_id,
        name: `${ib.iceberg_id} (Sentinel-1 SAR)`,
        lat: lat,
        lon: lon,
        bearingDeg: bearingDeg,
        rangeNm: rangeNm,
        length: ib.length_m || ib.size_m || 120,
        width: ib.width_m || 80,
        area_km2: ib.area_km2,
        confidence: ib.confidence,
        mass: `${(ib.area_km2 * 45).toFixed(2)} Mt`,
        driftSpeed: 1.35,
        cpaNm: Number(Math.max(0.3, rangeNm * 0.45).toFixed(2)),
        tcpaHours: Number((rangeNm / 14.0).toFixed(1)),
        risk: rangeNm < 2.5 ? 'CRITICAL' : rangeNm < 6.0 ? 'MODERATE' : 'ADVISORY',
        leewayAngle: 28.0,
        source: 'SENTINEL-1-SAR',
        trajectory_predictions: ib.trajectory_predictions
      };
    });

    setTargets(prev => {
      const combined = [...mapped, ...prev];
      return Array.from(new Map(combined.map(item => [item.id, item])).values());
    });

    if (mapped.length > 0) {
      setSelectedTarget(mapped[0]);
    }
  };

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

  // Derived drift calculations
  const activePred = livePredictions?.predictions?.find(p => p.hours_ahead === selectedHorizon.hours);
  const predictedLat = activePred ? activePred.latitude.toFixed(4) : (selectedTarget.lat + (selectedTarget.lat >= 0 ? 1 : -1) * (selectedTarget.driftSpeed * selectedHorizon.hours * 0.006)).toFixed(4);
  const predictedLon = activePred ? activePred.longitude.toFixed(4) : (selectedTarget.lon + (selectedTarget.driftSpeed * selectedHorizon.hours * 0.012)).toFixed(4);
  const uncertaintyRadius = activePred ? activePred.uncertainty_radius_km : selectedHorizon.uncertaintyKm;
  const confidenceScore = activePred ? (activePred.confidence * 100).toFixed(1) : selectedHorizon.confidence;

  const tLat = selectedTarget ? Number(selectedTarget.lat) : 68.5736;
  const tLon = selectedTarget ? Number(selectedTarget.lon) : -32.5312;

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
                SENTINEL-1 SAR SEGFORMER + OCEANIC DRIFT ML + A* ROUTING + ARPA RADAR
              </span>
            </div>
          </div>

          {/* View Mode Toggle */}
          <div style={{
            display: 'flex',
            background: 'rgba(3, 7, 18, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '10px',
            padding: '4px',
            gap: '4px'
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
              <span>3D Globe Map</span>
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
              onClick={() => setViewMode('sar')}
              style={{
                background: viewMode === 'sar' ? 'rgba(0, 242, 254, 0.2)' : 'transparent',
                border: `1px solid ${viewMode === 'sar' ? 'var(--accent-cyan)' : 'transparent'}`,
                color: viewMode === 'sar' ? '#fff' : 'var(--text-muted)',
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
              <Satellite size={14} color={viewMode === 'sar' ? '#00f2fe' : 'currentColor'} />
              <span>Sentinel-1 SAR AI</span>
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
              <div style={{ height: '680px', width: '100%', position: 'relative' }}>
                <GlobeView
                  icebergs={targets}
                  selectedTargetId={selectedTarget.id}
                  selectedHorizon={selectedHorizon}
                  livePredictions={livePredictions}
                  onSelectIceberg={ib => {
                    const match = targets.find(t => (t.id === ib.id || t.id === ib.iceberg_id));
                    if (match) setSelectedTarget(match);
                  }}
                />
              </div>
            )}

            {viewMode === 'radar' && (
              <div style={{ height: '680px', width: '100%', position: 'relative' }}>
                <TacticalRadar
                  targets={targets}
                  selectedTargetId={selectedTarget.id}
                  onSelectTarget={t => {
                    const match = targets.find(tl => (tl.id === t.id || tl.id === t.iceberg_id));
                    if (match) setSelectedTarget(match);
                  }}
                />
              </div>
            )}

            {viewMode === 'sar' && (
              <BorderGlow
                edgeSensitivity={28}
                glowColor="185 100 65"
                backgroundColor="rgba(7, 19, 36, 0.9)"
                borderRadius={16}
                glowRadius={30}
                glowIntensity={1.2}
                coneSpread={28}
                colors={['#00f2fe', '#38bdf8', '#818cf8']}
              >
                <div style={{ height: '680px', width: '100%', overflow: 'hidden' }}>
                  <SARSatelliteDeck
                    onIngestIcebergs={handleIngestIcebergs}
                    onSelectTarget={(ib) => {
                      const match = targets.find(t => (t.id === ib.iceberg_id || t.id === ib.id));
                      if (match) setSelectedTarget(match);
                    }}
                  />
                </div>
              </BorderGlow>
            )}

            {viewMode === 'split' && (
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '20px',
                height: '660px',
                width: '100%',
                position: 'relative'
              }}>
                <div style={{ height: '100%', width: '100%', position: 'relative', overflow: 'hidden', borderRadius: '16px' }}>
                  <GlobeView
                    icebergs={targets}
                    selectedTargetId={selectedTarget.id}
                    selectedHorizon={selectedHorizon}
                    livePredictions={livePredictions}
                    onSelectIceberg={ib => {
                      const match = targets.find(t => (t.id === ib.id || t.id === ib.iceberg_id));
                      if (match) setSelectedTarget(match);
                    }}
                  />
                </div>
                <div style={{ height: '100%', width: '100%', position: 'relative', overflow: 'hidden', borderRadius: '16px' }}>
                  <TacticalRadar
                    targets={targets}
                    selectedTargetId={selectedTarget.id}
                    onSelectTarget={t => {
                      const match = targets.find(tl => (tl.id === t.id || tl.id === t.iceberg_id));
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
                    TARGET HAZARD SELECTION ({targets.length})
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

                <div style={{ display: 'flex', gap: '8px', marginBottom: '14px', flexWrap: 'wrap', maxHeight: '130px', overflowY: 'auto' }}>
                  {targets.map(t => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setSelectedTarget(t)}
                      style={{
                        flex: '1 1 30%',
                        minWidth: '95px',
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
                    <div style={{ color: 'var(--text-muted)' }}>GPS Coordinates</div>
                    <div style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>
                      {tLat >= 0 ? `${tLat.toFixed(4)}° N` : `${Math.abs(tLat).toFixed(4)}° S`},{' '}
                      {tLon >= 0 ? `${tLon.toFixed(4)}° E` : `${Math.abs(tLon).toFixed(4)}° W`}
                    </div>
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
                    Conf: {confidenceScore}%
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
                    <div className="value gradient-text-cyan" style={{ fontSize: '0.88rem' }}>
                      {Number(predictedLat) >= 0 ? `${Number(predictedLat).toFixed(3)}° N` : `${Math.abs(Number(predictedLat)).toFixed(3)}° S`},{' '}
                      {Number(predictedLon) >= 0 ? `${Number(predictedLon).toFixed(3)}° E` : `${Math.abs(Number(predictedLon)).toFixed(3)}° W`}
                    </div>
                  </div>
                  <div className="data-metric-box">
                    <div className="label">Uncertainty Radius (R_unc)</div>
                    <div className="value gradient-text-ice" style={{ fontSize: '1.05rem' }}>
                      {uncertaintyRadius} km
                    </div>
                  </div>
                </div>
              </div>
            </BorderGlow>

            {/* Hydrodynamic Drift Simulation Parameters */}
            <BorderGlow
              edgeSensitivity={28}
              glowColor="185 100 65"
              backgroundColor="rgba(7, 19, 36, 0.85)"
              borderRadius={16}
              glowRadius={30}
              glowIntensity={1.2}
              coneSpread={28}
              colors={['#00f2fe', '#818cf8', '#6366f1']}
            >
              <div style={{ padding: '20px' }}>
                <span style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', display: 'block', marginBottom: '14px' }}>
                  OCEANIC & ATMOSPHERIC DRAG FORCES
                </span>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      <span>Wind Speed:</span>
                      <span style={{ color: '#fff' }}>{windSpeed} KTS (W)</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="60"
                      value={windSpeed}
                      onChange={e => setWindSpeed(Number(e.target.value))}
                      style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
                    />
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      <span>Ocean Current Speed:</span>
                      <span style={{ color: '#fff' }}>{currentSpeed} M/S</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.05"
                      value={currentSpeed}
                      onChange={e => setCurrentSpeed(Number(e.target.value))}
                      style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
                    />
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      <span>Sea Ice Concentration:</span>
                      <span style={{ color: '#fff' }}>{seaIceConc}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={seaIceConc}
                      onChange={e => setSeaIceConc(Number(e.target.value))}
                      style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
                    />
                  </div>
                </div>

                <div style={{ marginTop: '16px' }}>
                  <SpecularButton
                    onClick={handleTriggerRouteOptimization}
                    disabled={loadingRoute}
                    variant="primary"
                    size="md"
                    icon={Zap}
                  >
                    {loadingRoute ? 'Computing A* Avoidance Route...' : 'Compute Dynamic Avoidance Route'}
                  </SpecularButton>
                </div>
              </div>
            </BorderGlow>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OperationsConsole;
