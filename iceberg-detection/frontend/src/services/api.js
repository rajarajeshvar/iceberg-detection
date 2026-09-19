const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('[API] Health check failed, using fallback:', err.message);
    return null;
  }
}

export async function getTrackedIcebergs() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/prediction/icebergs`, { signal: AbortSignal.timeout(4000) });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('[API] Fetch icebergs failed:', err.message);
    return null;
  }
}

export async function predictIcebergTrajectory(params) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/prediction/trajectory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        iceberg_id: params.iceberg_id || params.id || 'ICE-A68-FRAG',
        timestamp: params.timestamp || new Date().toISOString(),
        latitude: Number(params.latitude || params.lat || -64.40),
        longitude: Number(params.longitude || params.lon || -59.80),
        size_m: Number(params.size_m || params.length || 340),
        source: params.source || 'SENTINEL-1-SAR'
      }),
      signal: AbortSignal.timeout(8000)
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('[API] Predict trajectory failed, using fallback:', err.message);
    return null;
  }
}

export async function optimizeRoute(params) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/route/optimize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_lat: params.start_lat || -63.5,
        start_lon: params.start_lon || -61.5,
        end_lat: params.end_lat || -65.5,
        end_lon: params.end_lon || -58.0,
        vessel_speed_knots: params.vessel_speed_knots || 14.0,
        vessel_ice_class: params.vessel_ice_class || 'PC6',
        icebergs: params.icebergs || [
          {
            id: params.targetId || 'ICE-A68-FRAG',
            latitude: Number(params.lat || -64.4),
            longitude: Number(params.lon || -59.8),
            size_m: Number(params.size_m || 340)
          }
        ]
      }),
      signal: AbortSignal.timeout(10000)
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('[API] Optimize route failed, using fallback:', err.message);
    return null;
  }
}

// ==========================================
// SEGFORMER SAR SEGMENTATION & INGESTION
// ==========================================

export async function getSARSamples() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/segmentation/samples`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('[API] Fetch SAR samples failed:', err.message);
    return { samples: [], total_available: 0 };
  }
}

export async function analyzeSARSample(filename, autoPredict = true) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/segmentation/analyze-sample`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: filename,
        auto_predict_trajectories: autoPredict
      }),
      signal: AbortSignal.timeout(20000)
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('[API] SAR Segmentation failed:', err.message);
    throw err;
  }
}

export async function analyzeSARUpload(formData) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/segmentation/analyze-upload`, {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(30000)
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('[API] SAR Upload analysis failed:', err.message);
    throw err;
  }
}
