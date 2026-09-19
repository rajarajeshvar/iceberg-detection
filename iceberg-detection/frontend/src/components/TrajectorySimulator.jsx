import { useState, useEffect, useRef } from 'react';
import { Compass, Navigation, AlertTriangle, Wind, Droplets, Clock, Zap, ArrowUpRight } from 'lucide-react';
import BorderGlow from './BorderGlow';
import SpecularButton from './SpecularButton';

const TARGETS = [
  {
    id: 'ICE-A68-FRAG',
    name: 'A-68 Fragment (Tabular)',
    type: 'Very Large Tabular Iceberg',
    length: 340,
    area: '115,600 m²',
    mass: '4.82 Mt',
    lat: -64.218,
    lon: -59.842,
    speedKts: 1.45,
    headingDeg: 128,
    risk: 'CRITICAL',
    cpaNm: 1.8,
    tcpaHours: 3.2,
    radarX: 0.62,
    radarY: 0.38
  },
  {
    id: 'ICE-B15-OMEGA',
    name: 'B-15 Calved Spire',
    type: 'Medium Pinnacle Iceberg',
    length: 165,
    area: '27,225 m²',
    mass: '1.14 Mt',
    lat: -64.405,
    lon: -60.120,
    speedKts: 0.95,
    headingDeg: 142,
    risk: 'MODERATE',
    cpaNm: 5.4,
    tcpaHours: 7.8,
    radarX: 0.35,
    radarY: 0.65
  },
  {
    id: 'BERGY-BIT-402',
    name: 'Bergy Bit Clustered',
    type: 'Submerged Low-Freeboard Hazard',
    length: 42,
    area: '1,760 m²',
    mass: '0.06 Mt',
    lat: -64.110,
    lon: -60.450,
    speedKts: 1.80,
    headingDeg: 110,
    risk: 'ADVISORY',
    cpaNm: 8.9,
    tcpaHours: 11.5,
    radarX: 0.78,
    radarY: 0.72
  }
];

const HORIZONS = [
  { hours: 6, label: '+6h', uncertaintyKm: 1.8, confidence: 98.4 },
  { hours: 12, label: '+12h', uncertaintyKm: 3.4, confidence: 95.1 },
  { hours: 24, label: '+24h', uncertaintyKm: 6.2, confidence: 89.6 },
  { hours: 48, label: '+48h', uncertaintyKm: 10.8, confidence: 81.2 },
  { hours: 72, label: '+72h', uncertaintyKm: 16.5, confidence: 73.0 }
];

const TrajectorySimulator = ({ onCalculateRoute }) => {
  const [selectedTarget, setSelectedTarget] = useState(TARGETS[0]);
  const [selectedHorizon, setSelectedHorizon] = useState(HORIZONS[0]);
  const canvasRef = useRef(null);

  // Radar animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let sweepAngle = 0;

    const resize = () => {
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const draw = () => {
      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2;
      const cy = h / 2;
      const radius = Math.min(cx, cy) - 25;

      ctx.clearRect(0, 0, w, h);

      // Radar Concentric Circles
      ctx.strokeStyle = 'rgba(0, 242, 254, 0.15)';
      ctx.lineWidth = 1;
      for (let r = 1; r <= 4; r++) {
        ctx.beginPath();
        ctx.arc(cx, cy, (radius / 4) * r, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Range labels
      ctx.fillStyle = 'rgba(0, 242, 254, 0.4)';
      ctx.font = '10px JetBrains Mono';
      ctx.fillText('3 NM', cx + (radius / 4) + 4, cy - 4);
      ctx.fillText('6 NM', cx + (radius / 2) + 4, cy - 4);
      ctx.fillText('9 NM', cx + (radius * 0.75) + 4, cy - 4);
      ctx.fillText('12 NM', cx + radius - 20, cy - 4);

      // Radial Crosshairs
      ctx.strokeStyle = 'rgba(0, 242, 254, 0.1)';
      ctx.beginPath();
      ctx.moveTo(cx - radius, cy);
      ctx.lineTo(cx + radius, cy);
      ctx.moveTo(cx, cy - radius);
      ctx.lineTo(cx, cy + radius);
      ctx.stroke();

      // Sweeping Beam
      sweepAngle = (sweepAngle + 0.02) % (Math.PI * 2);
      const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
      gradient.addColorStop(0, 'rgba(0, 242, 254, 0)');
      gradient.addColorStop(1, 'rgba(0, 242, 254, 0.25)');

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, radius, sweepAngle - 0.35, sweepAngle);
      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();
      ctx.restore();

      // Vessel at Center
      ctx.fillStyle = '#38bdf8';
      ctx.beginPath();
      ctx.arc(cx, cy, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#e0f2fe';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(cx, cy - 12);
      ctx.lineTo(cx + 6, cy + 6);
      ctx.lineTo(cx - 6, cy + 6);
      ctx.closePath();
      ctx.stroke();

      // Draw Iceberg Targets
      TARGETS.forEach(target => {
        const tx = cx - radius * 0.7 + target.radarX * radius * 1.4;
        const ty = cy - radius * 0.7 + target.radarY * radius * 1.4;
        const isSelected = target.id === selectedTarget.id;

        // Vector line from target based on heading
        const radHeading = (target.headingDeg - 90) * (Math.PI / 180);
        const vectorLen = target.speedKts * selectedHorizon.hours * 2.8;
        const endX = tx + Math.cos(radHeading) * vectorLen;
        const endY = ty + Math.sin(radHeading) * vectorLen;

        // Uncertainty Ellipse at Horizon
        const uncertaintyPx = selectedHorizon.uncertaintyKm * 2.6;
        ctx.beginPath();
        ctx.ellipse(endX, endY, uncertaintyPx, uncertaintyPx * 0.65, radHeading, 0, Math.PI * 2);
        ctx.fillStyle = isSelected ? 'rgba(0, 242, 254, 0.14)' : 'rgba(255, 255, 255, 0.04)';
        ctx.fill();
        ctx.strokeStyle = isSelected ? 'rgba(0, 242, 254, 0.5)' : 'rgba(255, 255, 255, 0.15)';
        ctx.setLineDash([3, 3]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Drift trajectory line
        ctx.beginPath();
        ctx.moveTo(tx, ty);
        ctx.lineTo(endX, endY);
        ctx.strokeStyle = isSelected ? '#00f2fe' : 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = isSelected ? 2 : 1;
        ctx.stroke();

        // Target marker
        ctx.beginPath();
        ctx.arc(tx, ty, isSelected ? 6 : 4, 0, Math.PI * 2);
        ctx.fillStyle = target.risk === 'CRITICAL' ? '#f43f5e' : (target.risk === 'MODERATE' ? '#f59e0b' : '#38bdf8');
        ctx.fill();

        // Rings around selected target
        if (isSelected) {
          ctx.beginPath();
          ctx.arc(tx, ty, 11, 0, Math.PI * 2);
          ctx.strokeStyle = '#00f2fe';
          ctx.lineWidth = 1;
          ctx.stroke();

          // Label
          ctx.fillStyle = '#f8fafc';
          ctx.font = '10px JetBrains Mono';
          ctx.fillText(`${target.id} (${selectedHorizon.label})`, tx + 14, ty + 3);
        }
      });

      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', resize);
    };
  }, [selectedTarget, selectedHorizon]);

  return (
    <section id="radar-simulator" className="section">
      <div className="container">
        <div className="section-header">
          <div className="section-badge">
            <Compass size={14} />
            <span>Interactive Operational Console</span>
          </div>
          <h2 className="section-title">
            Real-Time Antarctic <span className="gradient-text-cyan">Trajectory Engine</span>
          </h2>
          <p className="section-desc">
            Simulate future drift paths calculated by the physics-informed leeway & Coriolis prediction model.
            Examine expanding uncertainty ellipses and Closest Point of Approach (CPA) calculations.
          </p>
        </div>

        <div className="simulator-panel">
          {/* Radar Visual Display */}
          <div className="radar-screen-container">
            <div className="radar-header">
              <span>SAR RADAR SCREEN • LAT {selectedTarget.lat.toFixed(3)}° S | LON {selectedTarget.lon.toFixed(3)}° W</span>
              <span className="status-dot"></span>
            </div>

            <div className="radar-body">
              <canvas ref={canvasRef} className="radar-sweep-canvas" />
            </div>

            {/* Target Selector Toolbar */}
            <div style={{
              display: 'flex',
              gap: '8px',
              padding: '12px 18px',
              background: 'rgba(5, 12, 24, 0.9)',
              borderTop: '1px solid rgba(0, 242, 254, 0.15)',
              overflowX: 'auto'
            }}>
              {TARGETS.map(t => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setSelectedTarget(t)}
                  style={{
                    background: selectedTarget.id === t.id ? 'rgba(0, 242, 254, 0.18)' : 'rgba(255, 255, 255, 0.04)',
                    border: `1px solid ${selectedTarget.id === t.id ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.08)'}`,
                    color: selectedTarget.id === t.id ? '#fff' : 'var(--text-muted)',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    fontSize: '0.75rem',
                    fontFamily: 'var(--font-mono)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    whiteSpace: 'nowrap'
                  }}
                >
                  <span style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: t.risk === 'CRITICAL' ? '#f43f5e' : (t.risk === 'MODERATE' ? '#f59e0b' : '#38bdf8')
                  }} />
                  {t.id}
                </button>
              ))}
            </div>
          </div>

          {/* Telemetry & Horizons Control Panel */}
          <div className="simulator-controls">
            {/* Horizon Horizon Selection */}
            <BorderGlow
              edgeSensitivity={25}
              glowColor="190 95 65"
              backgroundColor="rgba(10, 25, 47, 0.75)"
              borderRadius={16}
              glowRadius={30}
              glowIntensity={1.1}
              coneSpread={26}
              colors={['#00f2fe', '#38bdf8', '#818cf8']}
            >
              <div className="telemetry-card" style={{ border: 'none', background: 'transparent' }}>
                <div className="telemetry-header">
                  <span className="telemetry-title">Prediction Horizon</span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                    Confidence: {selectedHorizon.confidence}%
                  </span>
                </div>
                <div className="horizon-tabs">
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

                <div className="data-metrics-list">
                  <div className="data-metric-box">
                    <div className="label">Uncertainty Radius (R_unc)</div>
                    <div className="value gradient-text-cyan">{selectedHorizon.uncertaintyKm} km</div>
                  </div>
                  <div className="data-metric-box">
                    <div className="label">Time to CPA (TCPA)</div>
                    <div className="value gradient-text-ice">{selectedTarget.tcpaHours} hrs</div>
                  </div>
                </div>
              </div>
            </BorderGlow>

            {/* Target Telemetry Card */}
            <BorderGlow
              edgeSensitivity={25}
              glowColor="205 90 65"
              backgroundColor="rgba(10, 25, 47, 0.75)"
              borderRadius={16}
              glowRadius={30}
              glowIntensity={1.1}
              coneSpread={26}
              colors={['#38bdf8', '#00f2fe', '#6366f1']}
            >
              <div className="telemetry-card" style={{ border: 'none', background: 'transparent' }}>
                <div className="telemetry-header">
                  <span className="telemetry-title">Hydrodynamic Parameters</span>
                  <span style={{
                    fontSize: '0.72rem',
                    fontFamily: 'var(--font-mono)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    backgroundColor: selectedTarget.risk === 'CRITICAL' ? 'rgba(244, 63, 94, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                    color: selectedTarget.risk === 'CRITICAL' ? '#f43f5e' : '#f59e0b',
                    border: `1px solid ${selectedTarget.risk === 'CRITICAL' ? 'rgba(244, 63, 94, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`
                  }}>
                    RISK: {selectedTarget.risk}
                  </span>
                </div>

                <div className="data-metrics-list" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
                  <div className="data-metric-box">
                    <div className="label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Wind size={11} /> Leeway Deflection
                    </div>
                    <div className="value">28.4° Coriolis</div>
                  </div>
                  <div className="data-metric-box">
                    <div className="label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Droplets size={11} /> Ocean Current
                    </div>
                    <div className="value">0.48 m/s @ 125°</div>
                  </div>
                  <div className="data-metric-box">
                    <div className="label">Iceberg Length / Mass</div>
                    <div className="value" style={{ fontSize: '1rem' }}>{selectedTarget.length}m • {selectedTarget.mass}</div>
                  </div>
                  <div className="data-metric-box">
                    <div className="label">CPA Distance</div>
                    <div className="value gradient-text-cyan">{selectedTarget.cpaNm} NM</div>
                  </div>
                </div>
              </div>
            </BorderGlow>

            {/* Action SpecularButton */}
            <div style={{ marginTop: 'auto', paddingTop: '8px' }}>
              <SpecularButton
                size="md"
                radius={16}
                tint="#00f2fe"
                tintOpacity={0.15}
                blur={8}
                textColor="#ffffff"
                lineColor="#00f2fe"
                baseColor="#083344"
                intensity={1.3}
                shineSize={12}
                thickness={1.2}
                onClick={onCalculateRoute}
                className="w-full"
                style={{ width: '100%' }}
              >
                <Zap size={16} />
                <span>Calculate A* Avoidance Route & CPA</span>
              </SpecularButton>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default TrajectorySimulator;
