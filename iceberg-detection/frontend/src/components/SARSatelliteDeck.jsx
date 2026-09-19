import { useState, useEffect } from 'react';
import { 
  Satellite, 
  Layers, 
  Cpu, 
  Navigation, 
  AlertTriangle, 
  CheckCircle2, 
  UploadCloud, 
  Eye, 
  Compass, 
  Zap, 
  Maximize2,
  RefreshCw,
  Sliders,
  Radio,
  FileCheck,
  Crosshair,
  Maximize,
  ShieldAlert,
  Activity
} from 'lucide-react';
import SpecularButton from './SpecularButton';
import { getSARSamples, analyzeSARSample, analyzeSARUpload } from '../services/api';

const SARSatelliteDeck = ({ onIngestIcebergs, onSelectTarget }) => {
  const [samples, setSamples] = useState([]);
  const [selectedSample, setSelectedSample] = useState('');
  const [loading, setLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [activeImageView, setActiveImageView] = useState('overlay'); // 'overlay', 'sar', 'probability_map', 'predicted_mask'
  const [autoPredict, setAutoPredict] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);
  const [uploadFile, setUploadFile] = useState(null);
  const [selectedIbId, setSelectedIbId] = useState(null);

  useEffect(() => {
    loadSamples();
  }, []);

  const loadSamples = async () => {
    try {
      const data = await getSARSamples();
      if (data && data.samples && data.samples.length > 0) {
        setSamples(data.samples);
        setSelectedSample(data.samples[0].filename);
        runSegmentation(data.samples[0].filename);
      }
    } catch (err) {
      console.error('Failed to load SAR samples:', err);
    }
  };

  const runSegmentation = async (filename) => {
    const fname = filename || selectedSample;
    if (!fname) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await analyzeSARSample(fname, autoPredict);
      setAnalysisResult(res);
      if (res.icebergs && res.icebergs.length > 0) {
        setSelectedIbId(res.icebergs[0].iceberg_id);
      }
      if (res.has_detections && onIngestIcebergs) {
        onIngestIcebergs(res.icebergs, res.metadata);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Error executing SegFormer inference');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploadFile(file.name);
    setLoading(true);
    setErrorMsg(null);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('auto_predict_trajectories', autoPredict);

    try {
      const res = await analyzeSARUpload(formData);
      setAnalysisResult(res);
      if (res.icebergs && res.icebergs.length > 0) {
        setSelectedIbId(res.icebergs[0].iceberg_id);
      }
      if (res.has_detections && onIngestIcebergs) {
        onIngestIcebergs(res.icebergs, res.metadata);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Error processing uploaded GeoTIFF');
    } finally {
      setLoading(false);
    }
  };

  const handleManualIngest = () => {
    if (analysisResult && analysisResult.has_detections && onIngestIcebergs) {
      onIngestIcebergs(analysisResult.icebergs, analysisResult.metadata);
    }
  };

  const handleCardClick = (ib) => {
    setSelectedIbId(ib.iceberg_id);
    if (onSelectTarget) onSelectTarget(ib);
  };

  const currentMeta = analysisResult?.metadata || {};

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      width: '100%',
      padding: '16px',
      gap: '14px',
      background: 'rgba(3, 7, 18, 0.95)',
      fontFamily: 'var(--font-main)',
      color: 'var(--text-primary)',
      boxSizing: 'border-box',
      overflow: 'hidden'
    }}>
      {/* Top Cockpit Telemetry Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        padding: '12px 18px',
        background: 'linear-gradient(135deg, rgba(6, 16, 36, 0.95), rgba(10, 25, 47, 0.85))',
        border: '1px solid rgba(0, 242, 254, 0.25)',
        borderRadius: '12px',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6)'
      }}>
        {/* Title & Satellite Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '38px',
            height: '38px',
            borderRadius: '8px',
            background: 'rgba(0, 242, 254, 0.15)',
            border: '1px solid rgba(0, 242, 254, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-cyan)'
          }}>
            <Satellite size={20} className="animate-pulse" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ fontSize: '0.95rem', fontWeight: 700, fontFamily: 'var(--font-display)', margin: 0, color: '#fff', letterSpacing: '0.05em' }}>
                SENTINEL-1 SAR AI SEGMENTATION DECK
              </h2>
              <span style={{
                fontSize: '0.68rem',
                fontFamily: 'var(--font-mono)',
                padding: '2px 8px',
                borderRadius: '4px',
                background: 'rgba(0, 242, 254, 0.15)',
                color: '#00f2fe',
                border: '1px solid rgba(0, 242, 254, 0.3)'
              }}>
                SegFormer-B0 (MIT-B0)
              </span>
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
              SWATH: 10.24 km × 10.24 km • RES: 40m/px • CRS: {currentMeta.crs || 'EPSG:3996'} • POL: {currentMeta.polarization || 'HH+HV'}
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {/* Sample Scene Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>SCENE:</span>
            <select
              value={selectedSample}
              onChange={(e) => {
                setSelectedSample(e.target.value);
                runSegmentation(e.target.value);
              }}
              disabled={loading}
              style={{
                background: 'rgba(6, 16, 36, 0.95)',
                color: 'var(--accent-cyan)',
                border: '1px solid rgba(0, 242, 254, 0.35)',
                borderRadius: '6px',
                padding: '6px 10px',
                fontSize: '0.74rem',
                fontFamily: 'var(--font-mono)',
                outline: 'none',
                maxWidth: '210px',
                cursor: 'pointer'
              }}
            >
              {samples.map((s, idx) => (
                <option key={idx} value={s.filename} style={{ background: '#030712', color: '#fff' }}>
                  {s.sensor} ({s.polarization}) - {s.start_time ? s.start_time.split('T')[0] : `Sample #${idx+1}`}
                </option>
              ))}
            </select>
          </div>

          {/* Upload Button */}
          <label style={{
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            borderRadius: '6px',
            padding: '6px 12px',
            fontSize: '0.74rem',
            fontFamily: 'var(--font-mono)',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}>
            <UploadCloud size={14} color="var(--accent-cyan)" />
            <span>{uploadFile ? uploadFile.slice(0, 10) + '...' : 'Upload .TIF'}</span>
            <input type="file" accept=".tif,.tiff" onChange={handleFileUpload} style={{ display: 'none' }} />
          </label>

          {/* Run Inference Button */}
          <SpecularButton
            onClick={() => runSegmentation(selectedSample)}
            disabled={loading}
            variant="primary"
            size="sm"
            icon={RefreshCw}
          >
            {loading ? 'Segmenting...' : 'Execute AI'}
          </SpecularButton>
        </div>
      </div>

      {/* Main Workstation: Left Viewport (7.2 cols) + Right Telemetry (4.8 cols) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1.45fr 1fr',
        gap: '14px',
        flex: 1,
        minHeight: 0,
        overflow: 'hidden'
      }}>
        {/* Left Side: Multi-Spectral SAR Viewport */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          background: 'rgba(6, 16, 36, 0.85)',
          border: '1px solid rgba(0, 242, 254, 0.2)',
          borderRadius: '12px',
          padding: '12px',
          overflow: 'hidden',
          boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
        }}>
          {/* Layer Selector Switcher */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingBottom: '10px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            marginBottom: '10px'
          }}>
            <div style={{ display: 'flex', gap: '6px' }}>
              {[
                { key: 'overlay', label: 'AI Detection Overlay', icon: Eye },
                { key: 'sar', label: 'Raw SAR (HH/HV)', icon: Radio },
                { key: 'probability_map', label: 'Confidence Heatmap', icon: Cpu },
                { key: 'predicted_mask', label: 'Binary Mask', icon: Layers }
              ].map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setActiveImageView(key)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '5px 10px',
                    borderRadius: '6px',
                    fontSize: '0.72rem',
                    fontFamily: 'var(--font-mono)',
                    cursor: 'pointer',
                    background: activeImageView === key ? 'rgba(0, 242, 254, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                    border: `1px solid ${activeImageView === key ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.08)'}`,
                    color: activeImageView === key ? '#fff' : 'var(--text-muted)',
                    transition: 'all 0.2s'
                  }}
                >
                  <Icon size={12} color={activeImageView === key ? '#00f2fe' : 'currentColor'} />
                  <span>{label}</span>
                </button>
              ))}
            </div>

            <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
              256 × 256 RASTER
            </span>
          </div>

          {/* Darkroom Imagery Display Viewport */}
          <div style={{
            position: 'relative',
            flex: 1,
            background: '#010409',
            borderRadius: '8px',
            border: '1px solid rgba(0, 242, 254, 0.25)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden'
          }}>
            {/* Corner Reticle Brackets */}
            <div style={{ position: 'absolute', top: '8px', left: '8px', width: '12px', height: '12px', borderTop: '2px solid #00f2fe', borderLeft: '2px solid #00f2fe', zIndex: 4 }} />
            <div style={{ position: 'absolute', top: '8px', right: '8px', width: '12px', height: '12px', borderTop: '2px solid #00f2fe', borderRight: '2px solid #00f2fe', zIndex: 4 }} />
            <div style={{ position: 'absolute', bottom: '8px', left: '8px', width: '12px', height: '12px', borderBottom: '2px solid #00f2fe', borderLeft: '2px solid #00f2fe', zIndex: 4 }} />
            <div style={{ position: 'absolute', bottom: '8px', right: '8px', width: '12px', height: '12px', borderBottom: '2px solid #00f2fe', borderRight: '2px solid #00f2fe', zIndex: 4 }} />

            {/* Loading Overlay */}
            {loading && (
              <div style={{
                position: 'absolute',
                inset: 0,
                background: 'rgba(3, 7, 18, 0.85)',
                backdropFilter: 'blur(4px)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '10px',
                zIndex: 10
              }}>
                <RefreshCw size={28} className="animate-spin" color="#00f2fe" />
                <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#00f2fe', letterSpacing: '0.1em' }}>
                  SEGFORMER INFERENCE PROCESSING...
                </span>
              </div>
            )}

            {/* Error Message */}
            {errorMsg && (
              <div style={{ color: '#f43f5e', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', textAlign: 'center', padding: '16px' }}>
                <AlertTriangle size={24} color="#f43f5e" style={{ margin: '0 auto 8px' }} />
                <div>{errorMsg}</div>
              </div>
            )}

            {/* Rendered SAR Image */}
            {analysisResult?.images && analysisResult.images[activeImageView] ? (
              <img
                src={`data:image/png;base64,${analysisResult.images[activeImageView]}`}
                alt="SAR AI Imagery"
                style={{
                  maxHeight: '100%',
                  maxWidth: '100%',
                  objectFit: 'contain',
                  imageRendering: 'crisp-edges',
                  boxShadow: '0 0 20px rgba(0, 242, 254, 0.15)'
                }}
              />
            ) : (
              !loading && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>No SAR imagery loaded. Select a scene above.</div>
            )}

            {/* Bottom HUD Overlay Badge */}
            {analysisResult && (
              <div style={{
                position: 'absolute',
                bottom: '10px',
                left: '10px',
                background: 'rgba(6, 16, 36, 0.9)',
                backdropFilter: 'blur(8px)',
                border: '1px solid rgba(0, 242, 254, 0.3)',
                borderRadius: '6px',
                padding: '4px 10px',
                fontSize: '0.7rem',
                fontFamily: 'var(--font-mono)',
                color: '#00f2fe',
                zIndex: 5
              }}>
                🎯 DETECTIONS: <span style={{ color: '#fff', fontWeight: 700 }}>{analysisResult.total_detected} Iceberg(s)</span>
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Geospatial Target Metadata Table */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          background: 'rgba(6, 16, 36, 0.85)',
          border: '1px solid rgba(0, 242, 254, 0.2)',
          borderRadius: '12px',
          padding: '14px',
          overflow: 'hidden',
          boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
        }}>
          {/* Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingBottom: '10px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            marginBottom: '10px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={16} color="var(--accent-cyan)" />
              <h3 style={{ fontSize: '0.82rem', fontFamily: 'var(--font-display)', fontWeight: 700, margin: 0, color: '#fff', letterSpacing: '0.04em' }}>
                EXTRACTED GEOSPATIAL TARGETS ({analysisResult?.total_detected || 0})
              </h3>
            </div>
            <span style={{
              fontSize: '0.65rem',
              fontFamily: 'var(--font-mono)',
              padding: '2px 8px',
              borderRadius: '4px',
              fontWeight: 700,
              background: analysisResult?.total_detected > 0 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
              color: analysisResult?.total_detected > 0 ? '#10b981' : '#f59e0b',
              border: `1px solid ${analysisResult?.total_detected > 0 ? '#10b981' : '#f59e0b'}`
            }}>
              {analysisResult?.total_detected > 0 ? 'ACTIVE' : 'NO TARGETS'}
            </span>
          </div>

          {/* Scrollable Target Cards List */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            paddingRight: '4px'
          }}>
            {analysisResult?.icebergs && analysisResult.icebergs.length > 0 ? (
              analysisResult.icebergs.map((ib, idx) => {
                const isSelected = selectedIbId === ib.iceberg_id;
                return (
                  <div
                    key={idx}
                    onClick={() => handleCardClick(ib)}
                    style={{
                      background: isSelected ? 'rgba(0, 242, 254, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                      border: `1px solid ${isSelected ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.08)'}`,
                      borderRadius: '8px',
                      padding: '10px 12px',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      boxShadow: isSelected ? '0 0 16px rgba(0, 242, 254, 0.2)' : 'none'
                    }}
                  >
                    {/* Card Title & Confidence */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <span style={{ fontSize: '0.8rem', fontWeight: 700, color: isSelected ? '#00f2fe' : '#fff', fontFamily: 'var(--font-mono)' }}>
                        🧊 {ib.iceberg_id}
                      </span>
                      <span style={{
                        fontSize: '0.65rem',
                        fontFamily: 'var(--font-mono)',
                        padding: '1px 6px',
                        borderRadius: '4px',
                        background: 'rgba(0, 242, 254, 0.2)',
                        color: '#00f2fe',
                        border: '1px solid rgba(0, 242, 254, 0.4)'
                      }}>
                        CONF: {(ib.confidence * 100).toFixed(1)}%
                      </span>
                    </div>

                    {/* Coordinates */}
                    <div style={{ fontSize: '0.72rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)', marginBottom: '6px' }}>
                      GPS: {ib.latitude >= 0 ? `${ib.latitude.toFixed(4)}° N` : `${Math.abs(ib.latitude).toFixed(4)}° S`}, {ib.longitude >= 0 ? `${ib.longitude.toFixed(4)}° E` : `${Math.abs(ib.longitude).toFixed(4)}° W`}
                    </div>

                    {/* Dimensions Matrix */}
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr',
                      gap: '6px',
                      fontSize: '0.68rem',
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--text-muted)'
                    }}>
                      <div style={{ background: 'rgba(3, 7, 18, 0.5)', padding: '4px 6px', borderRadius: '4px' }}>
                        LEN: <span style={{ color: '#fff', fontWeight: 600 }}>{ib.length_m} m</span>
                      </div>
                      <div style={{ background: 'rgba(3, 7, 18, 0.5)', padding: '4px 6px', borderRadius: '4px' }}>
                        WID: <span style={{ color: '#fff', fontWeight: 600 }}>{ib.width_m} m</span>
                      </div>
                      <div style={{ background: 'rgba(3, 7, 18, 0.5)', padding: '4px 6px', borderRadius: '4px' }}>
                        AREA: <span style={{ color: '#fff', fontWeight: 600 }}>{ib.area_km2} km²</span>
                      </div>
                      <div style={{ background: 'rgba(3, 7, 18, 0.5)', padding: '4px 6px', borderRadius: '4px' }}>
                        PIXELS: <span style={{ color: '#fff', fontWeight: 600 }}>{ib.area_pixels} px</span>
                      </div>
                    </div>

                    {/* Trajectory Status */}
                    {ib.trajectory_predictions && (
                      <div style={{
                        marginTop: '6px',
                        paddingTop: '6px',
                        borderTop: '1px solid rgba(255, 255, 255, 0.06)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: '0.65rem',
                        fontFamily: 'var(--font-mono)',
                        color: '#10b981'
                      }}>
                        <span>✓ 6h-72h Trajectory Computed</span>
                        <span>Horizons: {ib.trajectory_predictions.length}</span>
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '180px',
                color: 'var(--text-muted)',
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                textAlign: 'center'
              }}>
                <CheckCircle2 size={24} color="#64748b" style={{ marginBottom: '8px' }} />
                <div>{analysisResult ? 'No icebergs detected in this SAR scene.' : 'Awaiting SAR analysis...'}</div>
              </div>
            )}
          </div>

          {/* Bottom Action Footer */}
          <div style={{
            marginTop: '10px',
            paddingTop: '10px',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px'
          }}>
            <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
              Auto-Sync with Radar & Globe
            </div>
            <SpecularButton
              onClick={handleManualIngest}
              disabled={!analysisResult?.has_detections}
              variant="primary"
              size="sm"
              icon={Navigation}
            >
              Deploy to Radar & Map
            </SpecularButton>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SARSatelliteDeck;
