import { useState, useEffect, useRef } from 'react';
import { Compass, AlertTriangle, ShieldCheck, Crosshair, ZoomIn, ZoomOut, Sliders, Volume2, VolumeX, Navigation } from 'lucide-react';
import SpecularButton from './SpecularButton';

const DEFAULT_TARGETS = [
  {
    id: 'ICE-A68-FRAG',
    name: 'A-68 Tabular Fragment',
    lat: -64.40,
    lon: -59.80,
    bearingDeg: 42,
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
    lat: -66.10,
    lon: -62.40,
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
  }
];

const TacticalRadar = ({ onSelectTarget, selectedTargetId, targets = [] }) => {
  const targetsData = targets && targets.length > 0 ? targets : DEFAULT_TARGETS;
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const [rangeScale, setRangeScale] = useState(12); // 3, 6, 12, 24 NM
  const [orientation, setOrientation] = useState('NORTH_UP');
  const [vectorMode, setVectorMode] = useState('RELATIVE');
  const [selectedTarget, setSelectedTarget] = useState(targetsData[0]);
  const [gain, setGain] = useState(85);
  const [seaClutter, setSeaClutter] = useState(15);

  useEffect(() => {
    if (selectedTargetId) {
      const match = targetsData.find(t => (t.id === selectedTargetId || t.iceberg_id === selectedTargetId));
      if (match) setSelectedTarget(match);
    } else if (targetsData.length > 0) {
      setSelectedTarget(targetsData[0]);
    }
  }, [selectedTargetId, targetsData]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animId;
    let sweepAngle = 0;

    const resize = () => {
      if (canvas.parentElement) {
        const w = canvas.parentElement.clientWidth;
        const h = canvas.parentElement.clientHeight;
        if (w > 20 && h > 20) {
          canvas.width = w;
          canvas.height = h;
        }
      }
    };
    resize();
    window.addEventListener('resize', resize);

    const draw = () => {
      const w = canvas.width;
      const h = canvas.height;
      if (w === 0 || h === 0) return;

      const cx = w / 2;
      const cy = h / 2;
      const radius = Math.max(30, Math.min(cx, cy) - 36);

      // Dark background with phosphor persistence
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

      // 360 Azimuth Dial with Degree Markings
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

      // Rotating Radar Beam
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

      // Leading Edge
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(sweepAngle) * radius, cy + Math.sin(sweepAngle) * radius);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.restore();

      // Draw Dynamic Iceberg Target Blips with Exact Polar Coordinates
      targetsData.forEach((t, idx) => {
        const bearing = t.bearingDeg ?? (45 + idx * 40);
        const range = t.rangeNm ?? (2.0 + idx * 1.5);
        const speed = t.speedKts ?? 1.2;
        const heading = t.headingDeg ?? (bearing + 30);

        const scaleFactor = radius / rangeScale;
        const targetDistPx = Math.min(Math.max(15, range * scaleFactor), radius - 10);
        const targetRad = (bearing - 90) * (Math.PI / 180);
        const tx = cx + Math.cos(targetRad) * targetDistPx;
        const ty = cy + Math.sin(targetRad) * targetDistPx;
        const isSelected = selectedTarget && (selectedTarget.id === t.id || selectedTarget.iceberg_id === t.id);

        // Proximity glow to sweep
        const angleDiff = Math.abs(((targetRad - sweepAngle + Math.PI * 3) % (Math.PI * 2)) - Math.PI);
        const isRecentlySwept = angleDiff < 0.6;

        // Target Velocity Vector
        const vectorRad = (heading - 90) * (Math.PI / 180);
        const vectorLength = speed * 18;
        const vx = tx + Math.cos(vectorRad) * vectorLength;
        const vy = ty + Math.sin(vectorRad) * vectorLength;

        // Vector line
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

        // Target Acquisition Tag
        if (isSelected) {
          const bSize = 14;
          ctx.strokeStyle = '#00f2fe';
          ctx.lineWidth = 1.5;

          ctx.beginPath();
          ctx.moveTo(tx - bSize, ty - bSize / 2);
          ctx.lineTo(tx - bSize, ty - bSize);
          ctx.lineTo(tx - bSize / 2, ty - bSize);
          ctx.stroke();

          ctx.beginPath();
          ctx.moveTo(tx + bSize / 2, ty - bSize);
          ctx.lineTo(tx + bSize, ty - bSize);
          ctx.lineTo(tx + bSize, ty - bSize / 2);
          ctx.stroke();

          ctx.beginPath();
          ctx.moveTo(tx - bSize, ty + bSize / 2);
          ctx.lineTo(tx - bSize, ty + bSize);
          ctx.lineTo(tx - bSize / 2, ty + bSize);
          ctx.stroke();

          ctx.beginPath();
          ctx.moveTo(tx + bSize / 2, ty + bSize);
          ctx.lineTo(tx + bSize, ty + bSize);
          ctx.lineTo(tx + bSize, ty + bSize / 2);
          ctx.stroke();

          // Target Callout Tag
          ctx.fillStyle = 'rgba(6, 16, 36, 0.9)';
          ctx.fillRect(tx + 16, ty - 22, 105, 42);
          ctx.strokeStyle = '#00f2fe';
          ctx.lineWidth = 1;
          ctx.strokeRect(tx + 16, ty - 22, 105, 42);

          ctx.fillStyle = '#ffffff';
          ctx.font = 'bold 9px JetBrains Mono';
          ctx.textAlign = 'left';
          ctx.fillText(t.id || t.iceberg_id, tx + 20, ty - 10);

          ctx.fillStyle = 'rgba(0, 242, 254, 0.9)';
          ctx.font = '8px JetBrains Mono';
          ctx.fillText(`RNG: ${range.toFixed(2)} NM`, tx + 20, ty + 2);
          ctx.fillText(`BRG: ${Math.round(bearing)}°`, tx + 20, ty + 12);
        }
      });

      animId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, [rangeScale, orientation, vectorMode, selectedTarget, targetsData, gain, seaClutter]);

  const handleSelect = (t) => {
    setSelectedTarget(t);
    if (onSelectTarget) onSelectTarget(t);
  };

  const selLat = selectedTarget ? Number(selectedTarget.lat ?? selectedTarget.latitude ?? -64.4) : -64.4;
  const selLon = selectedTarget ? Number(selectedTarget.lon ?? selectedTarget.longitude ?? -59.8) : -59.8;

  return (
    <div
      ref={containerRef}
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 340px',
        height: '100%',
        minHeight: '400px',
        background: 'rgba(3, 7, 18, 0.95)',
        borderRadius: '16px',
        overflow: 'hidden',
        border: '1px solid rgba(0, 242, 254, 0.2)',
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.8)'
      }}
    >
      {/* Radar PPI Screen */}
      <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />

        {/* Dynamic Telemetry Overlay Showing Selected Iceberg's GPS Coordinates */}
        <div style={{
          position: 'absolute',
          top: '16px',
          left: '16px',
          display: 'flex',
          gap: '12px',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.75rem',
          color: 'var(--accent-cyan)',
          background: 'rgba(6, 16, 36, 0.85)',
          backdropFilter: 'blur(8px)',
          padding: '8px 14px',
          borderRadius: '8px',
          border: '1px solid rgba(0, 242, 254, 0.25)',
          zIndex: 5
        }}>
          <div>TARGET: <span style={{ color: '#fff', fontWeight: 600 }}>{selectedTarget?.id || 'NO TARGET'}</span></div>
          <div>
            GPS: <span style={{ color: '#00f2fe', fontWeight: 600 }}>
              {selLat >= 0 ? `${selLat.toFixed(4)}° N` : `${Math.abs(selLat).toFixed(4)}° S`},{' '}
              {selLon >= 0 ? `${selLon.toFixed(4)}° E` : `${Math.abs(selLon).toFixed(4)}° W`}
            </span>
          </div>
          <div>RANGE: <span style={{ color: '#fff', fontWeight: 600 }}>{(selectedTarget?.rangeNm ?? 4.2).toFixed(2)} NM</span></div>
        </div>

        {/* Bottom Range Scaling */}
        <div style={{
          position: 'absolute',
          bottom: '16px',
          left: '16px',
          display: 'flex',
          gap: '8px',
          zIndex: 5
        }}>
          {[3, 6, 12, 24].map(scale => (
            <button
              key={scale}
              onClick={() => setRangeScale(scale)}
              style={{
                background: rangeScale === scale ? 'var(--accent-cyan)' : 'rgba(6, 16, 36, 0.75)',
                color: rangeScale === scale ? '#030712' : 'var(--text-muted)',
                border: '1px solid rgba(0, 242, 254, 0.3)',
                borderRadius: '6px',
                padding: '4px 10px',
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {scale} NM
            </button>
          ))}
        </div>
      </div>

      {/* Target ARPA Acquisition Sidebar */}
      <div style={{
        background: 'rgba(6, 16, 36, 0.95)',
        borderLeft: '1px solid rgba(0, 242, 254, 0.15)',
        display: 'flex',
        flexDirection: 'column',
        padding: '16px',
        overflowY: 'auto'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Crosshair size={16} color="var(--accent-cyan)" />
            <h3 style={{ fontSize: '0.85rem', fontFamily: 'var(--font-display)', fontWeight: 700, margin: 0, color: '#fff' }}>
              ARPA TRACKED ({targetsData.length})
            </h3>
          </div>
        </div>

        {/* Target List Items */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1, overflowY: 'auto' }}>
          {targetsData.map((t, idx) => {
            const isSel = selectedTarget && (selectedTarget.id === t.id || selectedTarget.iceberg_id === t.id);
            const tLat = Number(t.lat ?? t.latitude ?? -64.4);
            const tLon = Number(t.lon ?? t.longitude ?? -59.8);
            const tRange = Number(t.rangeNm ?? (2.0 + idx * 1.5));
            const tBearing = Math.round(t.bearingDeg ?? (45 + idx * 40));

            return (
              <div
                key={t.id || t.iceberg_id || idx}
                onClick={() => handleSelect(t)}
                style={{
                  background: isSel ? 'rgba(0, 242, 254, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                  border: `1px solid ${isSel ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.08)'}`,
                  borderRadius: '8px',
                  padding: '10px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 600, color: isSel ? '#00f2fe' : '#fff', fontFamily: 'var(--font-mono)' }}>
                    {t.id || t.iceberg_id}
                  </span>
                  <span style={{
                    fontSize: '0.65rem',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontWeight: 700,
                    fontFamily: 'var(--font-mono)',
                    background: t.risk === 'CRITICAL' ? 'rgba(244, 63, 94, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                    color: t.risk === 'CRITICAL' ? '#f43f5e' : '#38bdf8',
                    border: `1px solid ${t.risk === 'CRITICAL' ? '#f43f5e' : '#38bdf8'}`
                  }}>
                    {t.risk || 'TRACKED'}
                  </span>
                </div>

                <div style={{ fontSize: '0.68rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)', marginBottom: '4px' }}>
                  GPS: {tLat >= 0 ? `${tLat.toFixed(3)}°N` : `${Math.abs(tLat).toFixed(3)}°S`}, {tLon >= 0 ? `${tLon.toFixed(3)}°E` : `${Math.abs(tLon).toFixed(3)}°W`}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  <div>BRG: <span style={{ color: '#fff' }}>{tBearing}°</span></div>
                  <div>RNG: <span style={{ color: '#fff' }}>{tRange.toFixed(2)} NM</span></div>
                  <div>LEN: <span style={{ color: '#fff' }}>{t.length || t.size_m || 150}m</span></div>
                  <div>CPA: <span style={{ color: '#f43f5e' }}>{(t.cpaNm ?? 1.8).toFixed(1)} NM</span></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default TacticalRadar;
