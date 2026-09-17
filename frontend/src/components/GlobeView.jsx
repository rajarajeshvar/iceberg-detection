import { useEffect, useRef, useState, useMemo } from 'react';
import Globe from 'react-globe.gl';
import { Compass, Eye, RotateCw, ZoomIn, ZoomOut, Satellite, ShieldAlert, Layers } from 'lucide-react';
import SpecularButton from './SpecularButton';

// Antarctic Tracked Icebergs
const ICEBERGS_DATA = [
  {
    id: 'ICE-A68-FRAG',
    name: 'A-68A Fragment',
    lat: -64.4,
    lng: -59.8,
    size: 2.2,
    color: '#f43f5e',
    risk: 'CRITICAL',
    length: 340,
    area: '115,600 m²',
    speed: '1.45 kts @ 128°',
    cpa: '1.8 NM (TCPA: 3.2h)'
  },
  {
    id: 'ICE-B15-OMEGA',
    name: 'B-15 Calved Spire',
    lat: -66.1,
    lng: -62.4,
    size: 1.6,
    color: '#f59e0b',
    risk: 'MODERATE',
    length: 165,
    area: '27,225 m²',
    speed: '0.95 kts @ 142°',
    cpa: '5.4 NM (TCPA: 7.8h)'
  },
  {
    id: 'ICE-A76-NORTH',
    name: 'A-76A Tabular Body',
    lat: -62.8,
    lng: -54.2,
    size: 2.8,
    color: '#38bdf8',
    risk: 'MONITORED',
    length: 480,
    area: '230,400 m²',
    speed: '1.10 kts @ 095°',
    cpa: '14.2 NM (TCPA: 18h)'
  },
  {
    id: 'BERGY-BIT-402',
    name: 'Bergy Bit Clustered',
    lat: -63.7,
    lng: -60.8,
    size: 1.1,
    color: '#00f2fe',
    risk: 'ADVISORY',
    length: 42,
    area: '1,760 m²',
    speed: '1.80 kts @ 110°',
    cpa: '8.9 NM (TCPA: 11.5h)'
  }
];

// Predictive Drift Trajectory Arcs (+6h to +72h)
const TRAJECTORY_ARCS = [
  {
    startLat: -64.4,
    startLng: -59.8,
    endLat: -64.7,
    endLng: -59.2,
    color: ['#f43f5e', '#fb7185'],
    name: 'A-68 Fragment +24h Drift Arc'
  },
  {
    startLat: -64.7,
    startLng: -59.2,
    endLat: -65.2,
    endLng: -58.4,
    color: ['#fb7185', '#fda4af'],
    name: 'A-68 Fragment +72h Drift Arc'
  },
  {
    startLat: -66.1,
    startLng: -62.4,
    endLat: -66.5,
    endLng: -61.5,
    color: ['#f59e0b', '#fbbf24'],
    name: 'B-15 Spire +48h Drift Arc'
  },
  {
    startLat: -62.8,
    startLng: -54.2,
    endLat: -62.6,
    endLng: -52.8,
    color: ['#38bdf8', '#00f2fe'],
    name: 'A-76A Tabular +72h Drift Arc'
  },
  // Vessel Route Trajectory
  {
    startLat: -63.5,
    startLng: -61.5,
    endLat: -64.1,
    endLng: -60.5,
    color: ['#10b981', '#34d399'],
    name: 'R/V Polarstern Navigational Path'
  },
  {
    startLat: -64.1,
    startLng: -60.5,
    endLat: -64.8,
    endLng: -59.0,
    color: ['#34d399', '#6ee7b7'],
    name: 'A* Diverted Avoidance Corridor'
  }
];

// Orbiting Satellites (Sentinel-1 & Radarsat)
const SATELLITES = [
  { id: 'S1A', name: 'Sentinel-1A (C-Band SAR)', lat: -45, lng: -55, alt: 0.28, color: '#00f2fe' },
  { id: 'S1B', name: 'Sentinel-1C (Polar Orbit)', lat: -72, lng: -40, alt: 0.28, color: '#38bdf8' },
  { id: 'RCM1', name: 'RCM-1 (Constellation)', lat: -58, lng: -75, alt: 0.32, color: '#818cf8' }
];

const GlobeView = ({ onSelectIceberg }) => {
  const globeEl = useRef();
  const [selectedIceberg, setSelectedIceberg] = useState(ICEBERGS_DATA[0]);
  const [showArcs, setShowArcs] = useState(true);
  const [showSatellites, setShowSatellites] = useState(true);
  const [autoRotate, setAutoRotate] = useState(false);

  // Set initial camera to Antarctica (Lat: -65, Lng: -60, altitude: 1.6)
  useEffect(() => {
    if (globeEl.current) {
      globeEl.current.pointOfView({ lat: -64.5, lng: -60, altitude: 1.65 }, 1200);
      globeEl.current.controls().autoRotate = autoRotate;
      globeEl.current.controls().autoRotateSpeed = 0.6;
    }
  }, []);

  useEffect(() => {
    if (globeEl.current) {
      globeEl.current.controls().autoRotate = autoRotate;
    }
  }, [autoRotate]);

  const handleFocusAntarctica = () => {
    if (globeEl.current) {
      globeEl.current.pointOfView({ lat: -64.5, lng: -60, altitude: 1.4 }, 1500);
    }
  };

  const handleFocusTarget = (iceberg) => {
    setSelectedIceberg(iceberg);
    if (onSelectIceberg) onSelectIceberg(iceberg);
    if (globeEl.current) {
      globeEl.current.pointOfView({ lat: iceberg.lat, lng: iceberg.lng, altitude: 0.8 }, 1200);
    }
  };

  const handleResetGlobal = () => {
    if (globeEl.current) {
      globeEl.current.pointOfView({ lat: -30, lng: -50, altitude: 2.5 }, 1500);
    }
  };

  // Ring ripples around icebergs
  const ringsData = useMemo(() => {
    return ICEBERGS_DATA.map(d => ({
      lat: d.lat,
      lng: d.lng,
      maxR: d.size * 2.2,
      propagationSpeed: 1.5,
      repeatPeriod: 1200,
      color: d.color
    }));
  }, []);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: '620px', overflow: 'hidden', borderRadius: '18px', background: '#020612' }}>
      {/* 3D Globe Canvas Container */}
      <Globe
        ref={globeEl}
        globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
        bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
        backgroundImageUrl="//unpkg.com/three-globe/example/img/night-sky.png"
        atmosphereColor="#00f2fe"
        atmosphereAltitude={0.22}
        // Icebergs as HTML / Points
        pointsData={ICEBERGS_DATA}
        pointLat="lat"
        pointLng="lng"
        pointColor="color"
        pointAltitude={0.015}
        pointRadius="size"
        pointResolution={32}
        onPointClick={handleFocusTarget}
        pointLabel={d => `
          <div style="background: rgba(3,7,18,0.95); border: 1px solid ${d.color}; padding: 8px 12px; border-radius: 6px; font-family: JetBrains Mono; font-size: 11px; color: #fff; box-shadow: 0 0 15px rgba(0,242,254,0.4)">
            <b style="color: ${d.color}">${d.id}</b> — ${d.name}<br/>
            <span>Coords: ${d.lat}° S, ${d.lng}° W</span><br/>
            <span>Length: ${d.length}m | Mass: ${d.area}</span><br/>
            <span>Velocity: ${d.speed}</span><br/>
            <span style="color: #fda4af">CPA: ${d.cpa}</span>
          </div>
        `}
        // Rings pulsing from ice hazards
        ringsData={ringsData}
        ringColor="color"
        ringMaxRadius="maxR"
        ringPropagationSpeed="propagationSpeed"
        ringRepeatPeriod="repeatPeriod"
        // Trajectory and Route Arcs
        arcsData={showArcs ? TRAJECTORY_ARCS : []}
        arcColor="color"
        arcDashLength={0.4}
        arcDashGap={0.2}
        arcDashAnimateTime={2000}
        arcStroke={1.5}
        arcAltitude={0.08}
      />

      {/* Top Floating Telemetry Overlay */}
      <div style={{
        position: 'absolute',
        top: 16,
        left: 16,
        background: 'rgba(3, 10, 24, 0.85)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(0, 242, 254, 0.25)',
        borderRadius: '12px',
        padding: '12px 18px',
        color: '#fff',
        zIndex: 10,
        maxWidth: '360px',
        boxShadow: '0 8px 24px rgba(0,0,0,0.6)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="status-dot"></span>
            <span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
              ANTARCTIC 3D OBSERVATION
            </span>
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            WGS84 GEODETIC
          </span>
        </div>

        <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f8fafc', marginBottom: '4px' }}>
          {selectedIceberg.id} — {selectedIceberg.name}
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span>Lat: {selectedIceberg.lat.toFixed(2)}° S | Lon: {selectedIceberg.lng.toFixed(2)}° W</span>
          <span>Kinematics: {selectedIceberg.speed}</span>
          <span style={{ color: selectedIceberg.risk === 'CRITICAL' ? '#f43f5e' : '#f59e0b' }}>
            Risk Index: {selectedIceberg.risk} ({selectedIceberg.cpa})
          </span>
        </div>
      </div>

      {/* Camera & Layer Controls Toolbar */}
      <div style={{
        position: 'absolute',
        bottom: 16,
        left: 16,
        display: 'flex',
        gap: '8px',
        zIndex: 10,
        flexWrap: 'wrap'
      }}>
        <button
          type="button"
          onClick={handleFocusAntarctica}
          style={{
            background: 'rgba(6, 16, 32, 0.85)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(0, 242, 254, 0.3)',
            color: '#fff',
            padding: '8px 14px',
            borderRadius: '8px',
            fontSize: '0.75rem',
            fontFamily: 'var(--font-mono)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <Compass size={14} color="#00f2fe" />
          Focus Antarctic Peninsula
        </button>

        <button
          type="button"
          onClick={handleResetGlobal}
          style={{
            background: 'rgba(6, 16, 32, 0.85)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            color: 'var(--text-secondary)',
            padding: '8px 14px',
            borderRadius: '8px',
            fontSize: '0.75rem',
            fontFamily: 'var(--font-mono)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <Eye size={14} />
          Global View
        </button>

        <button
          type="button"
          onClick={() => setAutoRotate(!autoRotate)}
          style={{
            background: autoRotate ? 'rgba(0, 242, 254, 0.2)' : 'rgba(6, 16, 32, 0.85)',
            backdropFilter: 'blur(8px)',
            border: `1px solid ${autoRotate ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.1)'}`,
            color: autoRotate ? 'var(--accent-cyan)' : 'var(--text-secondary)',
            padding: '8px 14px',
            borderRadius: '8px',
            fontSize: '0.75rem',
            fontFamily: 'var(--font-mono)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <RotateCw size={14} />
          {autoRotate ? 'Orbit: ON' : 'Orbit: OFF'}
        </button>

        <button
          type="button"
          onClick={() => setShowArcs(!showArcs)}
          style={{
            background: showArcs ? 'rgba(0, 242, 254, 0.2)' : 'rgba(6, 16, 32, 0.85)',
            backdropFilter: 'blur(8px)',
            border: `1px solid ${showArcs ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.1)'}`,
            color: showArcs ? 'var(--accent-cyan)' : 'var(--text-secondary)',
            padding: '8px 14px',
            borderRadius: '8px',
            fontSize: '0.75rem',
            fontFamily: 'var(--font-mono)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <Layers size={14} />
          Drift Vectors
        </button>
      </div>

      {/* Target Quick Select Bar on Right */}
      <div style={{
        position: 'absolute',
        top: 16,
        right: 16,
        background: 'rgba(3, 10, 24, 0.85)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '12px',
        padding: '10px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        zIndex: 10
      }}>
        <span style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', paddingLeft: '4px' }}>
          TRACKED TARGETS
        </span>
        {ICEBERGS_DATA.map(ib => (
          <button
            key={ib.id}
            type="button"
            onClick={() => handleFocusTarget(ib)}
            style={{
              background: selectedIceberg.id === ib.id ? 'rgba(0, 242, 254, 0.18)' : 'rgba(255, 255, 255, 0.03)',
              border: `1px solid ${selectedIceberg.id === ib.id ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.06)'}`,
              borderRadius: '6px',
              padding: '6px 10px',
              fontSize: '0.72rem',
              fontFamily: 'var(--font-mono)',
              color: selectedIceberg.id === ib.id ? '#fff' : 'var(--text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              textAlign: 'left'
            }}
          >
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: ib.color }} />
            {ib.id}
          </button>
        ))}
      </div>
    </div>
  );
};

export default GlobeView;
