import { useEffect, useRef, useState, useMemo } from 'react';
import Globe from 'react-globe.gl';
import { 
  Compass, 
  RotateCw, 
  ZoomIn, 
  ZoomOut, 
  Satellite, 
  Layers, 
  Crosshair, 
  AlertTriangle, 
  ShieldCheck, 
  Navigation,
  Ship,
  Eye,
  Activity,
  Radio,
  Wind,
  MapPin,
  Anchor
} from 'lucide-react';
import SpecularButton from './SpecularButton';

const GlobeView = ({ 
  onSelectIceberg, 
  icebergs = [], 
  selectedTargetId, 
  selectedHorizon = { hours: 24, label: '+24h', uncertaintyKm: 6.2 },
  livePredictions
}) => {
  const containerRef = useRef(null);
  const globeEl = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 600 });
  const [autoRotate, setAutoRotate] = useState(false);
  const [showArcs, setShowArcs] = useState(true);
  const [selectedVesselId, setSelectedVesselId] = useState('VESSEL-01');

  // ResizeObserver ensures WebGL canvas matches parent container exactly
  useEffect(() => {
    if (!containerRef.current) return;
    const updateSize = () => {
      if (containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current;
        if (clientWidth > 50 && clientHeight > 50) {
          setDimensions({ width: clientWidth, height: clientHeight });
        }
      }
    };
    updateSize();
    const ro = new ResizeObserver(updateSize);
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // Primary active iceberg coordinate reference
  const primaryTarget = useMemo(() => {
    if (icebergs && icebergs.length > 0) {
      if (selectedTargetId) {
        const match = icebergs.find(ib => (ib.id === selectedTargetId || ib.iceberg_id === selectedTargetId));
        if (match) return match;
      }
      return icebergs[0];
    }
    return { lat: 68.57, lon: -32.53, id: 'IB-S1-001' };
  }, [icebergs, selectedTargetId]);

  const targetLat = Number(primaryTarget.lat ?? primaryTarget.latitude ?? 68.57);
  const targetLon = Number(primaryTarget.lon ?? primaryTarget.longitude ?? -32.53);

  // 4 Realistic Mock Vessels widely separated across distinct oceanic corridors
  const mockVessels = useMemo(() => {
    return [
      {
        id: 'VESSEL-01',
        name: 'R/V Polarstern',
        callsign: 'DBLH',
        type: 'Research Icebreaker',
        lat: targetLat - 7.5,
        lon: targetLon - 8.0,
        speedKts: 14.5,
        headingDeg: 35, // Northeast
        color: '#10b981' // Single Uniform Emerald
      },
      {
        id: 'VESSEL-02',
        name: 'M/V Nordic Barents',
        callsign: 'LNZQ',
        type: 'Bulk Carrier (Ice Class 1A)',
        lat: targetLat + 8.5,
        lon: targetLon + 14.0,
        speedKts: 12.5,
        headingDeg: 210, // South-Southwest
        color: '#f59e0b' // Single Uniform Amber
      },
      {
        id: 'VESSEL-03',
        name: 'S/V Arctic Explorer',
        callsign: 'C6VX7',
        type: 'Expedition Cruise Ship',
        lat: targetLat - 8.0,
        lon: targetLon + 12.5,
        speedKts: 13.0,
        headingDeg: 295, // West-Northwest
        color: '#38bdf8' // Single Uniform Sky Blue
      },
      {
        id: 'VESSEL-04',
        name: 'C/V Polar Star',
        callsign: 'V3TK',
        type: 'Container / Supply Ship',
        lat: targetLat + 4.5,
        lon: targetLon - 20.0,
        speedKts: 15.0,
        headingDeg: 145, // Southeast
        color: '#a855f7' // Single Uniform Purple
      }
    ];
  }, [targetLat, targetLon]);

  // Stepped Multi-Horizon Iceberg Drift Trajectory (from Oceanic & Weather ML Model)
  const icebergDriftSteps = useMemo(() => {
    const maxHours = selectedHorizon?.hours || 24;
    if (livePredictions?.predictions && livePredictions.predictions.length > 0) {
      return livePredictions.predictions
        .filter(p => p.hours_ahead <= maxHours)
        .sort((a, b) => a.hours_ahead - b.hours_ahead);
    }
    // Hydrodynamic drift fallback
    const hours = [6, 12, 24, 48, 72].filter(h => h <= maxHours);
    return hours.map(h => ({
      hours_ahead: h,
      latitude: targetLat + (targetLat >= 0 ? 1 : -1) * (0.04 * (h / 6)),
      longitude: targetLon + (0.075 * (h / 6)),
      confidence: Math.max(0.65, 0.98 - h * 0.004),
      uncertainty_radius_km: 2.0 + h * 0.35
    }));
  }, [selectedHorizon, livePredictions, targetLat, targetLon]);

  // Generate Trajectory Arcs with 100% UNIFORM SINGLE COLOR per Trajectory + Final Endpoints
  const { trajectoryArcs, vesselRisks, collisionBeacon, vesselEndpoints } = useMemo(() => {
    const arcs = [];
    const maxHours = selectedHorizon?.hours || 24;
    const hourSteps = [6, 12, 24, 48, 72].filter(h => h <= maxHours);

    // 1. Iceberg Drift Trajectory (Uniform #00f2fe Electric Cyan)
    let ibPrevLat = targetLat;
    let ibPrevLon = targetLon;
    icebergDriftSteps.forEach((step) => {
      arcs.push({
        id: `ib-arc-${step.hours_ahead}`,
        type: 'ICEBERG_DRIFT',
        startLat: ibPrevLat,
        startLng: ibPrevLon,
        endLat: step.latitude,
        endLng: step.longitude,
        color: '#00f2fe',
        altitude: 0.008,
        stroke: 0.8,
        dashLength: 0.18,
        dashGap: 0.28,
        dashAnimateTime: 4800,
        name: `🧊 Iceberg +${step.hours_ahead}h Drift Path`
      });
      ibPrevLat = step.latitude;
      ibPrevLon = step.longitude;
    });

    // 2. Trajectories for each of the 4 Mock Vessels
    const risks = [];
    const endpoints = [];
    let beacon = null;

    mockVessels.forEach((v) => {
      let vPrevLat = v.lat;
      let vPrevLon = v.lon;
      const radHdg = (v.headingDeg * Math.PI) / 180;
      let minCpaNm = 999;
      let cpaHour = null;
      let cpaCoords = null;

      // Project vessel waypoints over timeline
      const vWaypoints = hourSteps.map(h => {
        const distKm = v.speedKts * 1.852 * h;
        const distDeg = distKm / 111.0;
        const lat = v.lat + distDeg * Math.cos(radHdg);
        const lon = v.lon + (distDeg * Math.sin(radHdg)) / Math.cos((v.lat * Math.PI) / 180);
        return { hours_ahead: h, lat, lon };
      });

      // Final destination waypoint for this vessel at selected horizon
      const finalWpt = vWaypoints[vWaypoints.length - 1] || { lat: v.lat, lon: v.lon, hours_ahead: maxHours };
      endpoints.push({
        vesselId: v.id,
        vesselName: v.name,
        color: v.color,
        lat: finalWpt.lat,
        lon: finalWpt.lon,
        hours: finalWpt.hours_ahead
      });

      // Calculate CPA relative to iceberg predicted positions
      vWaypoints.forEach(vPt => {
        const matchingIb = icebergDriftSteps.find(ib => ib.hours_ahead === vPt.hours_ahead);
        if (matchingIb) {
          const dLat = (matchingIb.latitude - vPt.lat) * 60;
          const dLon = (matchingIb.longitude - vPt.lon) * 60 * Math.cos((matchingIb.latitude * Math.PI) / 180);
          const distNm = Math.sqrt(dLat * dLat + dLon * dLon);
          if (distNm < minCpaNm) {
            minCpaNm = distNm;
            cpaHour = vPt.hours_ahead;
            cpaCoords = { lat: (matchingIb.latitude + vPt.lat) / 2, lon: (matchingIb.longitude + vPt.lon) / 2 };
          }
        }
      });

      const isCritical = minCpaNm < 15.0;
      const isCaution = minCpaNm >= 15.0 && minCpaNm < 45.0;
      const riskLevel = isCritical ? 'CRITICAL' : isCaution ? 'CAUTION' : 'SAFE';

      if (isCritical && !beacon) {
        beacon = {
          lat: cpaCoords.lat,
          lon: cpaCoords.lon,
          vesselName: v.name,
          cpaNm: Number(minCpaNm.toFixed(1)),
          cpaHour
        };
      }

      risks.push({
        vessel: v,
        minCpaNm: Number(minCpaNm.toFixed(1)),
        cpaHour,
        riskLevel
      });

      // Add vessel trajectory segments (Uniform Single Color)
      const vesselUniformColor = isCritical ? '#f43f5e' : v.color;

      vWaypoints.forEach((wpt) => {
        arcs.push({
          id: `${v.id}-arc-${wpt.hours_ahead}`,
          type: 'VESSEL_ROUTE',
          startLat: vPrevLat,
          startLng: vPrevLon,
          endLat: wpt.lat,
          endLng: wpt.lon,
          altitude: 0.008,
          color: vesselUniformColor,
          stroke: 0.7,
          dashLength: 0.15,
          dashGap: 0.30,
          dashAnimateTime: 5200,
          name: `🚢 ${v.name} Route (+${wpt.hours_ahead}h)`
        });
        vPrevLat = wpt.lat;
        vPrevLon = wpt.lon;
      });
    });

    return { 
      trajectoryArcs: arcs, 
      vesselRisks: risks, 
      collisionBeacon: beacon,
      vesselEndpoints: endpoints 
    };
  }, [selectedHorizon, icebergDriftSteps, mockVessels, targetLat, targetLon]);

  // Clean HTML DOM Markers for Globe (Origins + Dynamic Trajectory Endpoints)
  const htmlMarkers = useMemo(() => {
    const markers = [];
    const horizonLabel = selectedHorizon?.label || '+24h';

    // 1. Iceberg Origin Marker (Cyan Diamond)
    markers.push({
      lat: targetLat,
      lng: targetLon,
      type: 'ICEBERG_ORIGIN',
      id: primaryTarget.id || 'IB-S1-001',
      html: `
        <div style="position: relative; display: flex; flex-direction: column; align-items: center; pointer-events: auto; cursor: pointer; transform: translate(-50%, -50%);">
          <div style="width: 10px; height: 10px; background: #00f2fe; border: 1.5px solid #ffffff; border-radius: 2px; transform: rotate(45deg); box-shadow: 0 0 8px #00f2fe;"></div>
          <div style="margin-top: 4px; background: rgba(6, 16, 36, 0.9); border: 1px solid #00f2fe; border-radius: 4px; padding: 1px 5px; font-family: monospace; font-size: 8.5px; font-weight: bold; color: #ffffff; white-space: nowrap; box-shadow: 0 2px 8px rgba(0,0,0,0.5);">
            🧊 ${primaryTarget.id || 'IB-S1-001'} (Origin)
          </div>
        </div>
      `
    });

    // 2. Iceberg Trajectory Final Endpoint at Current Timeline
    if (icebergDriftSteps.length > 0) {
      const finalIb = icebergDriftSteps[icebergDriftSteps.length - 1];
      markers.push({
        lat: finalIb.latitude,
        lng: finalIb.longitude,
        type: 'ICEBERG_ENDPOINT',
        id: 'IB-ENDPOINT',
        html: `
          <div style="position: relative; display: flex; flex-direction: column; align-items: center; pointer-events: auto; transform: translate(-50%, -50%);">
            <div style="position: absolute; width: 22px; height: 22px; border-radius: 50%; border: 1px dashed #00f2fe; animation: spin 6s linear infinite; opacity: 0.8;"></div>
            <div style="width: 8px; height: 8px; background: #00f2fe; border: 1.5px solid #ffffff; border-radius: 50%; box-shadow: 0 0 8px #00f2fe;"></div>
            <div style="margin-top: 4px; background: rgba(0, 242, 254, 0.2); backdrop-filter: blur(4px); border: 1px solid #00f2fe; border-radius: 4px; padding: 1px 5px; font-family: monospace; font-size: 8px; font-weight: bold; color: #00f2fe; white-space: nowrap;">
              📍 IB Target (${horizonLabel})
            </div>
          </div>
        `
      });
    }

    // 3. 4 Mock Vessel Origin Markers
    mockVessels.forEach(v => {
      const vRisk = vesselRisks.find(r => r.vessel.id === v.id);
      const isCrit = vRisk?.riskLevel === 'CRITICAL';
      const badgeColor = isCrit ? '#f43f5e' : v.color;

      markers.push({
        lat: v.lat,
        lng: v.lon,
        type: 'VESSEL_ORIGIN',
        id: v.id,
        html: `
          <div style="position: relative; display: flex; flex-direction: column; align-items: center; pointer-events: auto; cursor: pointer; transform: translate(-50%, -50%);">
            <div style="width: 9px; height: 9px; background: ${badgeColor}; border: 1.5px solid #ffffff; border-radius: 50%; box-shadow: 0 0 8px ${badgeColor};"></div>
            <div style="margin-top: 3px; background: rgba(6, 16, 36, 0.9); border: 1px solid ${badgeColor}; border-radius: 4px; padding: 1px 5px; font-family: monospace; font-size: 8px; font-weight: 600; color: #ffffff; white-space: nowrap; box-shadow: 0 2px 8px rgba(0,0,0,0.5);">
              🚢 ${v.name.split(' ')[1] || v.name} (${v.speedKts}k)
            </div>
          </div>
        `
      });
    });

    // 4. 4 Vessel Trajectory Final Endpoints at Current Timeline
    vesselEndpoints.forEach(ve => {
      markers.push({
        lat: ve.lat,
        lng: ve.lon,
        type: 'VESSEL_ENDPOINT',
        id: `${ve.vesselId}-ENDPOINT`,
        html: `
          <div style="position: relative; display: flex; flex-direction: column; align-items: center; pointer-events: auto; transform: translate(-50%, -50%);">
            <div style="width: 7px; height: 7px; background: ${ve.color}; border: 1px solid #ffffff; border-radius: 2px; transform: rotate(45deg); box-shadow: 0 0 6px ${ve.color};"></div>
            <div style="margin-top: 3px; background: rgba(6, 16, 36, 0.85); border: 1px solid ${ve.color}; border-radius: 4px; padding: 1px 4px; font-family: monospace; font-size: 7.5px; font-weight: 600; color: ${ve.color}; white-space: nowrap;">
              ⚓ ${ve.vesselName.split(' ')[1] || ve.vesselName} (${horizonLabel})
            </div>
          </div>
        `
      });
    });

    return markers;
  }, [targetLat, targetLon, primaryTarget, mockVessels, vesselRisks, icebergDriftSteps, vesselEndpoints, selectedHorizon]);

  // Initial Camera Target
  useEffect(() => {
    if (globeEl.current) {
      globeEl.current.pointOfView({ lat: targetLat, lng: targetLon, altitude: 1.85 }, 1200);
      globeEl.current.controls().autoRotate = autoRotate;
      globeEl.current.controls().autoRotateSpeed = 0.5;
    }
  }, [targetLat, targetLon]);

  const handleResetScene = () => {
    if (globeEl.current) {
      globeEl.current.pointOfView({ lat: targetLat, lng: targetLon, altitude: 1.85 }, 1000);
    }
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: '400px',
        background: 'radial-gradient(circle at center, #07152d 0%, #030712 100%)',
        borderRadius: '16px',
        overflow: 'hidden',
        border: '1px solid rgba(0, 242, 254, 0.25)',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8)'
      }}
    >
      {/* 3D WebGL Globe Canvas */}
      <Globe
        ref={globeEl}
        width={dimensions.width}
        height={dimensions.height}
        globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
        bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
        backgroundImageUrl="//unpkg.com/three-globe/example/img/night-sky.png"
        
        // Minimalist HTML Elements for Origins & Timeline Endpoints
        htmlElementsData={htmlMarkers}
        htmlLat="lat"
        htmlLng="lng"
        htmlAltitude={0.01}
        htmlElement={d => {
          const el = document.createElement('div');
          el.innerHTML = d.html;
          el.onclick = () => {
            if (d.type.includes('ICEBERG') && onSelectIceberg) {
              const match = icebergs.find(ib => (ib.id === d.id || ib.iceberg_id === d.id));
              if (match) onSelectIceberg(match);
            } else if (d.type.includes('VESSEL')) {
              const cleanId = d.id.replace('-ENDPOINT', '');
              setSelectedVesselId(cleanId);
            }
          };
          return el;
        }}

        // Clean, 2D Surface-Hugging Trajectory Arcs with Single Uniform Color
        arcsData={showArcs ? trajectoryArcs : []}
        arcStartLat="startLat"
        arcStartLng="startLng"
        arcEndLat="endLat"
        arcEndLng="endLng"
        arcAltitude="altitude"
        arcColor="color"
        arcStroke="stroke"
        arcDashLength="dashLength"
        arcDashGap="dashGap"
        arcDashAnimateTime="dashAnimateTime"
      />

      {/* Top Left Toolbar */}
      <div style={{
        position: 'absolute',
        top: '14px',
        left: '14px',
        display: 'flex',
        flexWrap: 'wrap',
        gap: '8px',
        background: 'rgba(6, 16, 36, 0.88)',
        backdropFilter: 'blur(12px)',
        padding: '6px 12px',
        borderRadius: '10px',
        border: '1px solid rgba(0, 242, 254, 0.2)',
        zIndex: 10
      }}>
        <SpecularButton
          onClick={handleResetScene}
          variant="secondary"
          size="sm"
          icon={Crosshair}
        >
          Reset Regional View
        </SpecularButton>

        {/* Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', paddingLeft: '8px', borderLeft: '1px solid rgba(255,255,255,0.1)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: '#00f2fe' }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#00f2fe' }} />
            <span>Iceberg Drift</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: '#10b981' }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981' }} />
            <span>Vessel Routes</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
            <span>📍/⚓ Endpoints ({selectedHorizon?.label})</span>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setAutoRotate(!autoRotate)}
          style={{
            background: autoRotate ? 'rgba(0, 242, 254, 0.2)' : 'transparent',
            border: `1px solid ${autoRotate ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.1)'}`,
            color: autoRotate ? '#00f2fe' : 'var(--text-muted)',
            borderRadius: '6px',
            padding: '4px 8px',
            fontSize: '0.7rem',
            fontFamily: 'var(--font-mono)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          <RotateCw size={11} className={autoRotate ? 'animate-spin' : ''} />
          <span>Rotate</span>
        </button>
      </div>

      {/* Top Right Fleet Collision Risk Deck */}
      <div style={{
        position: 'absolute',
        top: '14px',
        right: '14px',
        background: 'rgba(6, 16, 36, 0.92)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(0, 242, 254, 0.25)',
        borderRadius: '12px',
        padding: '10px 14px',
        width: '270px',
        zIndex: 10,
        boxShadow: '0 10px 30px rgba(0,0,0,0.6)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '6px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Activity size={14} color="#00f2fe" />
            <span style={{ fontSize: '0.74rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#fff' }}>
              REGIONAL FLEET CPA ({selectedHorizon?.label})
            </span>
          </div>
        </div>

        {/* 4 Vessel Risk Rows */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {vesselRisks.map((vr) => {
            const isCrit = vr.riskLevel === 'CRITICAL';
            const isCaut = vr.riskLevel === 'CAUTION';
            return (
              <div
                key={vr.vessel.id}
                onClick={() => setSelectedVesselId(vr.vessel.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '5px 8px',
                  borderRadius: '6px',
                  background: isCrit 
                    ? 'rgba(244, 63, 94, 0.15)' 
                    : isCaut 
                    ? 'rgba(245, 158, 11, 0.12)' 
                    : 'rgba(255, 255, 255, 0.03)',
                  border: `1px solid ${isCrit ? 'rgba(244, 63, 94, 0.5)' : isCaut ? 'rgba(245, 158, 11, 0.4)' : 'rgba(255, 255, 255, 0.06)'}`,
                  cursor: 'pointer'
                }}
              >
                <div>
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, color: '#fff', fontFamily: 'var(--font-mono)' }}>
                    {vr.vessel.name.split(' ')[0]} {vr.vessel.name.split(' ')[1]}
                  </div>
                  <div style={{ fontSize: '0.64rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {vr.vessel.speedKts} kts @ {vr.vessel.headingDeg}°
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <span style={{
                    fontSize: '0.62rem',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                    padding: '1px 5px',
                    borderRadius: '4px',
                    background: isCrit ? '#f43f5e' : isCaut ? '#f59e0b' : '#10b981',
                    color: '#030712'
                  }}>
                    CPA {vr.minCpaNm} NM
                  </span>
                  <div style={{ fontSize: '0.6rem', color: isCrit ? '#f43f5e' : isCaut ? '#f59e0b' : '#10b981', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                    {vr.riskLevel}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom Floating Telemetry Bar */}
      <div style={{
        position: 'absolute',
        bottom: '14px',
        left: '14px',
        right: '14px',
        background: 'rgba(6, 16, 36, 0.92)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(0, 242, 254, 0.3)',
        borderRadius: '12px',
        padding: '10px 16px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
        zIndex: 10
      }}>
        {/* Iceberg Telemetry */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#00f2fe', boxShadow: '0 0 8px #00f2fe' }} />
          <div>
            <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#fff', fontFamily: 'var(--font-mono)' }}>
              🧊 ACTIVE TARGET: {primaryTarget.id || 'IB-S1-001'}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
              GPS: {targetLat >= 0 ? `${targetLat.toFixed(4)}° N` : `${Math.abs(targetLat).toFixed(4)}° S`},{' '}
              {targetLon >= 0 ? `${targetLon.toFixed(4)}° E` : `${Math.abs(targetLon).toFixed(4)}° W`} • LEN: {primaryTarget.length || primaryTarget.size_m || 150}m
            </div>
          </div>
        </div>

        {/* Selected Vessel Telemetry */}
        {(() => {
          const selVessel = mockVessels.find(v => v.id === selectedVesselId) || mockVessels[0];
          const vRisk = vesselRisks.find(r => r.vessel.id === selVessel.id);
          return (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '7px', height: '7px', borderRadius: '50%', background: selVessel.color, boxShadow: `0 0 8px ${selVessel.color}` }} />
              <div>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#fff', fontFamily: 'var(--font-mono)' }}>
                  🚢 {selVessel.name} ({selVessel.callsign})
                </div>
                <div style={{ fontSize: '0.7rem', color: '#fff', fontFamily: 'var(--font-mono)' }}>
                  HEADING: {selVessel.headingDeg}° • SPD: {selVessel.speedKts} KTS • STATUS: <span style={{ color: vRisk?.riskLevel === 'CRITICAL' ? '#f43f5e' : '#10b981', fontWeight: 700 }}>{vRisk?.riskLevel}</span>
                </div>
              </div>
            </div>
          );
        })()}

        {/* Timeline Horizon Badge */}
        <div style={{ display: 'flex', gap: '12px', fontFamily: 'var(--font-mono)', fontSize: '0.72rem' }}>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>TIMELINE: </span>
            <span style={{ color: '#00f2fe', fontWeight: 700 }}>{selectedHorizon?.label || '+24h'}</span>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>MODEL: </span>
            <span style={{ color: '#10b981', fontWeight: 600 }}>EKMAN / CORIOLIS DRIFT</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GlobeView;
