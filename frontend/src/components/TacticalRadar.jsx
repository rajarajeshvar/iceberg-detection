import { useState, useEffect, useRef } from 'react';
import { Compass, AlertTriangle, ShieldCheck, Crosshair, ZoomIn, ZoomOut, Sliders, Volume2, VolumeX } from 'lucide-react';
import SpecularButton from './SpecularButton';

const TARGETS_DATA = [
  {
    id: 'ICE-A68-FRAG',
    name: 'A-68 Tabular Fragment',
    bearingDeg: 042,
    rangeNm: 4.2,
    speedKts: 1.45,
    headingDeg: 128,
    length: 340,
    width: 210,
    draft: 145,
    cpaNm: 1.8,
    tcpaHours: 3.2,
    risk: 'CRITICAL',
    type: 'Tabular Iceberg'
  },
  {
    id: 'ICE-B15-OMEGA',
    name: 'B-15 Calved Spire',
    bearingDeg: 215,
    rangeNm: 7.8,
    speedKts: 0.95,
    headingDeg: 142,
    length: 165,
    width: 90,
    draft: 85,
    cpaNm: 5.4,
    tcpaHours: 7.8,
    risk: 'MODERATE',
    type: 'Pinnacle Iceberg'
  },
  {
    id: 'BERGY-BIT-402',
    name: 'Bergy Bit Cluster',
    bearingDeg: 135,
    rangeNm: 9.6,
    speedKts: 1.80,
    headingDeg: 110,
    length: 42,
    width: 30,
    draft: 22,
    cpaNm: 8.9,
    tcpaHours: 11.5,
    risk: 'ADVISORY',
    type: 'Low-Freeboard Hazard'
  },
  {
    id: 'GROWLER-09',
    name: 'Submerged Growler',
    bearingDeg: 310,
    rangeNm: 2.9,
    speedKts: 0.60,
    headingDeg: 095,
    length: 18,
    width: 12,
    draft: 10,
    cpaNm: 2.1,
    tcpaHours: 2.4,
    risk: 'CRITICAL',
    type: 'Radar-Invisible Growler'
  }
];

const TacticalRadar = ({ onSelectTarget, selectedTargetId }) => {
  const canvasRef = useRef(null);
  const [rangeScale, setRangeScale] = useState(12); // 3, 6, 12, 24 NM
  const [orientation, setOrientation] = useState('NORTH_UP'); // NORTH_UP or HEAD_UP
  const [vectorMode, setVectorMode] = useState('RELATIVE'); // TRUE or RELATIVE
  const [selectedTarget, setSelectedTarget] = useState(TARGETS_DATA[0]);
  const [gain, setGain] = useState(85);
  const [seaClutter, setSeaClutter] = useState(15);
  const [audioEnabled, setAudioEnabled] = useState(false);

  useEffect(() => {
    if (selectedTargetId) {
      const match = TARGETS_DATA.find(t => t.id === selectedTargetId);
      if (match) setSelectedTarget(match);
    }
  }, [selectedTargetId]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animId;
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
      const radius = Math.min(cx, cy) - 36;

      // Dark background with slight phosphor persistence
      ctx.fillStyle = 'rgba(2, 6, 18, 0.25)';
      ctx.fillRect(0, 0, w, h);

      // Radar Concentric Range Rings
      const numRings = 4;
      for (let i = 1; i <= numRings; i++) {
        const r = (radius / numRings) * i;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.strokeStyle = i === numRings ? 'rgba(0, 242, 254, 0.45)' : 'rgba(0, 242, 254, 0.18)';
        ctx.lineWidth = i === numRings ? 1.5 : 1;
        ctx.setLineDash(i === numRings ? [] : [2, 4]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Ring distance labels
        const distLabel = ((rangeScale / numRings) * i).toFixed(1) + ' NM';
        ctx.fillStyle = 'rgba(0, 242, 254, 0.6)';
        ctx.font = '9px JetBrains Mono';
        ctx.fillText(distLabel, cx + r - 22, cy - 4);
      }

      // 360° Azimuth Dial with Degree Markings
      ctx.save();
      ctx.translate(cx, cy);
      for (let deg = 0; deg < 360; deg += 5) {
        const rad = (deg - 90) * (Math.PI / 180);
        const isMajor = deg % 30 === 0;
        const isSemi = deg % 10 === 0;
        const tickLength = isMajor ? 10 : (isSemi ? 6 : 3);

        const x1 = Math.cos(rad) * radius;
        const y1 = Math.sin(rad) * radius;
        const x2 = Math.cos(rad) * (radius + tickLength);
        const y2 = Math.sin(rad) * (radius + tickLength);

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle = isMajor ? 'rgba(0, 242, 254, 0.8)' : (isSemi ? 'rgba(0, 242, 254, 0.4)' : 'rgba(0, 242, 254, 0.2)');
        ctx.lineWidth = isMajor ? 1.5 : 1;
        ctx.stroke();

        if (isMajor) {
          const textRad = radius + 18;
          const tx = Math.cos(rad) * textRad;
          const ty = Math.sin(rad) * textRad;
          ctx.fillStyle = 'rgba(0, 242, 254, 0.75)';
          ctx.font = '9px JetBrains Mono';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          const degStr = deg.toString().padStart(3, '0') + '°';
          ctx.fillText(degStr, tx, ty);
        }
      }
      ctx.restore();

      // Cardinal Indicators
      const cardinalRadius = radius - 14;
      const cardinals = [
        { label: 'N', deg: 0, color: '#f43f5e' },
        { label: 'E', deg: 90, color: '#00f2fe' },
        { label: 'S', deg: 180, color: '#00f2fe' },
        { label: 'W', deg: 270, color: '#00f2fe' }
      ];
      cardinals.forEach(c => {
        const rad = (c.deg - 90) * (Math.PI / 180);
        const tx = cx + Math.cos(rad) * cardinalRadius;
        const ty = cy + Math.sin(rad) * cardinalRadius;
        ctx.fillStyle = c.color;
        ctx.font = 'bold 11px Space Grotesk';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(c.label, tx, ty);
      });

      // Crosshairs
      ctx.strokeStyle = 'rgba(0, 242, 254, 0.12)';
      ctx.beginPath();
      ctx.moveTo(cx - radius, cy);
      ctx.lineTo(cx + radius, cy);
      ctx.moveTo(cx, cy - radius);
      ctx.lineTo(cx, cy + radius);
      ctx.stroke();

      // Vessel Heading Vector (Own Ship @ Center)
      const ownHeadingRad = (045 - 90) * (Math.PI / 180);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(ownHeadingRad) * (radius * 0.95), cy + Math.sin(ownHeadingRad) * (radius * 0.95));
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.5)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Rotating Radar Beam with Realistic Phosphor Sweep Trail
      sweepAngle = (sweepAngle + 0.025) % (Math.PI * 2);
      ctx.save();
      const sweepGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
      sweepGrad.addColorStop(0, 'rgba(0, 242, 254, 0.02)');
      sweepGrad.addColorStop(0.7, 'rgba(0, 242, 254, 0.12)');
      sweepGrad.addColorStop(1, 'rgba(0, 242, 254, 0.35)');

      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, radius, sweepAngle - 0.45, sweepAngle);
      ctx.closePath();
      ctx.fillStyle = sweepGrad;
      ctx.fill();

      // Sharp Leading Edge
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(sweepAngle) * radius, cy + Math.sin(sweepAngle) * radius);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.restore();

      // Own Ship Symbol
      ctx.fillStyle = '#00f2fe';
      ctx.beginPath();
      ctx.arc(cx, cy, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy - 10);
      ctx.lineTo(cx + 6, cy + 6);
      ctx.lineTo(cx, cy + 3);
      ctx.lineTo(cx - 6, cy + 6);
      ctx.closePath();
      ctx.stroke();

      // Iceberg Target Blips and Echoes
      TARGETS_DATA.forEach(t => {
        // Compute pixel position from polar (bearing, range)
        const scaleFactor = radius / rangeScale;
        const targetDistPx = Math.min(t.rangeNm * scaleFactor, radius);
        const targetRad = (t.bearingDeg - 90) * (Math.PI / 180);
        const tx = cx + Math.cos(targetRad) * targetDistPx;
        const ty = cy + Math.sin(targetRad) * targetDistPx;
        const isSelected = selectedTarget && selectedTarget.id === t.id;

        // Proximity glow to sweep
        const angleDiff = Math.abs(((targetRad - sweepAngle + Math.PI * 3) % (Math.PI * 2)) - Math.PI);
        const isRecentlySwept = angleDiff < 0.6;

        // Target Velocity Vector
        const vectorRad = (t.headingDeg - 90) * (Math.PI / 180);
        const vectorLength = t.speedKts * 18;
        const vx = tx + Math.cos(vectorRad) * vectorLength;
        const vy = ty + Math.sin(vectorRad) * vectorLength;

        // Draw vector line
        ctx.beginPath();
        ctx.moveTo(tx, ty);
        ctx.lineTo(vx, vy);
        ctx.strokeStyle = isSelected ? '#00f2fe' : 'rgba(255, 255, 255, 0.4)';
        ctx.lineWidth = isSelected ? 2 : 1;
        ctx.stroke();

        // Arrow tip
        ctx.beginPath();
        ctx.arc(vx, vy, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = isSelected ? '#00f2fe' : '#ffffff';
        ctx.fill();

        // Echo bloom
        const bloomRad = isSelected ? 8 : (isRecentlySwept ? 6 : 4);
        ctx.beginPath();
        ctx.arc(tx, ty, bloomRad, 0, Math.PI * 2);
        ctx.fillStyle = t.risk === 'CRITICAL' ? '#f43f5e' : (t.risk === 'MODERATE' ? '#f59e0b' : '#38bdf8');
        ctx.shadowColor = t.risk === 'CRITICAL' ? '#f43f5e' : '#00f2fe';
        ctx.shadowBlur = isRecentlySwept ? 14 : 6;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Acquisition Target Bracket
        if (isSelected) {
          const bSize = 14;
          ctx.strokeStyle = '#00f2fe';
          ctx.lineWidth = 1.5;
          // Four corners around target
          ctx.beginPath();
          ctx.moveTo(tx - bSize, ty - bSize + 5);
          ctx.lineTo(tx - bSize, ty - bSize);
          ctx.lineTo(tx - bSize + 5, ty - bSize);

          ctx.moveTo(tx + bSize - 5, ty - bSize);
          ctx.lineTo(tx + bSize, ty - bSize);
          ctx.lineTo(tx + bSize, ty - bSize + 5);

          ctx.moveTo(tx + bSize, ty + bSize - 5);
          ctx.lineTo(tx + bSize, ty + bSize);
          ctx.lineTo(tx + bSize - 5, ty + bSize);

          ctx.moveTo(tx - bSize + 5, ty + bSize);
          ctx.lineTo(tx - bSize, ty + bSize);
          ctx.lineTo(tx - bSize, ty + bSize - 5);
          ctx.stroke();

          // Target Info Label
          ctx.fillStyle = '#ffffff';
          ctx.font = '10px JetBrains Mono';
          ctx.textAlign = 'left';
          ctx.fillText(`[${t.id}] CPA: ${t.cpaNm}NM`, tx + 18, ty - 4);
          ctx.fillStyle = t.risk === 'CRITICAL' ? '#fda4af' : '#94a3b8';
          ctx.fillText(`TCPA: ${t.tcpaHours}h • ${t.speedKts}kts`, tx + 18, ty + 8);
        }
      });

      animId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, [rangeScale, orientation, vectorMode, selectedTarget]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      minHeight: '620px',
      background: '#030816',
      border: '1px solid rgba(0, 242, 254, 0.25)',
      borderRadius: '18px',
      overflow: 'hidden',
      position: 'relative'
    }}>
      {/* Top Tactical Status Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 18px',
        background: 'rgba(6, 16, 36, 0.95)',
        borderBottom: '1px solid rgba(0, 242, 254, 0.2)',
        fontFamily: 'var(--font-mono)',
        fontSize: '0.8rem',
        color: 'var(--text-secondary)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Crosshair size={16} color="var(--accent-cyan)" />
          <span style={{ color: '#fff', fontWeight: 600 }}>ARPA TACTICAL RADAR</span>
          <span style={{ color: 'var(--accent-cyan)' }}>RANGE: {rangeScale} NM</span>
          <span>MODE: {orientation}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="status-dot"></span>
          <span style={{ color: '#38bdf8' }}>BAND: 9.4 GHz X-BAND / 3.0 GHz S-BAND</span>
        </div>
      </div>

      {/* Main Radar Screen */}
      <div style={{ position: 'relative', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />

        {/* Floating Quick Stats Panel */}
        <div style={{
          position: 'absolute',
          top: 16,
          left: 16,
          background: 'rgba(3, 10, 24, 0.85)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(0, 242, 254, 0.2)',
          borderRadius: '10px',
          padding: '10px 14px',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.72rem',
          color: 'var(--text-secondary)',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>OWN SHIP: R/V POLARIS</span>
          <span>HDG: 045.0° T | SPD: 12.4 KTS</span>
          <span>LAT: 64° 25.4' S | LON: 059° 50.2' W</span>
          <span style={{ color: '#f43f5e' }}>ALERT: 2 TARGETS WITHIN COLLISION CORRIDOR</span>
        </div>
      </div>

      {/* Bottom Tactical Controls Strip */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 18px',
        background: 'rgba(6, 16, 36, 0.95)',
        borderTop: '1px solid rgba(0, 242, 254, 0.2)',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        {/* Range Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>RANGE:</span>
          {[3, 6, 12, 24].map(r => (
            <button
              key={r}
              type="button"
              onClick={() => setRangeScale(r)}
              style={{
                background: rangeScale === r ? 'rgba(0, 242, 254, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                border: `1px solid ${rangeScale === r ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.1)'}`,
                color: rangeScale === r ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '0.72rem',
                fontFamily: 'var(--font-mono)',
                cursor: 'pointer'
              }}
            >
              {r}NM
            </button>
          ))}
        </div>

        {/* Orientation Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            type="button"
            onClick={() => setOrientation(orientation === 'NORTH_UP' ? 'HEAD_UP' : 'NORTH_UP')}
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: 'var(--text-secondary)',
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '0.72rem',
              fontFamily: 'var(--font-mono)',
              cursor: 'pointer'
            }}
          >
            {orientation === 'NORTH_UP' ? 'NORTH UP' : 'HEAD UP'}
          </button>

          <button
            type="button"
            onClick={() => setVectorMode(vectorMode === 'RELATIVE' ? 'TRUE' : 'RELATIVE')}
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: 'var(--text-secondary)',
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '0.72rem',
              fontFamily: 'var(--font-mono)',
              cursor: 'pointer'
            }}
          >
            VECTORS: {vectorMode}
          </button>
        </div>

        {/* Target Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {TARGETS_DATA.map(t => (
            <button
              key={t.id}
              type="button"
              onClick={() => {
                setSelectedTarget(t);
                if (onSelectTarget) onSelectTarget(t);
              }}
              style={{
                background: selectedTarget && selectedTarget.id === t.id ? 'rgba(0, 242, 254, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                border: `1px solid ${selectedTarget && selectedTarget.id === t.id ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.08)'}`,
                color: selectedTarget && selectedTarget.id === t.id ? '#fff' : 'var(--text-muted)',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '0.7rem',
                fontFamily: 'var(--font-mono)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: t.risk === 'CRITICAL' ? '#f43f5e' : '#f59e0b' }} />
              {t.id}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TacticalRadar;
