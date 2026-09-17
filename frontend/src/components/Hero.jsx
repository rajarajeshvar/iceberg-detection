import { useState } from 'react';
import { Compass, ShieldAlert, Sparkles, Sliders, Waves, Layers } from 'lucide-react';
import GhostFibers from './GhostFibers';
import SpecularButton from './SpecularButton';

const PRESETS = {
  sarRadar: {
    id: 'sarRadar',
    name: 'Arctic SAR Radar',
    icon: Waves,
    config: {
      lineColor: '#07203d',
      glowColor: '#00d2ff',
      speed: 0.18,
      scale: 2.2,
      rotation: 15,
      rotationSpeed: 0.18,
      layers: 5,
      waveAmplitude: 0.018,
      waveFrequency: 3.2,
      waveSpeed: 0.16,
      layerSpeed: 0.08,
      twist: 0.14,
      twistFrequency: 5.5,
      twistSpeed: 1.1,
      lineFrequency: 5,
      lineSpacing: 2,
      lineSharpness: 17,
      glowFalloff: 9,
      glowIntensity: 1.8,
      brightness: 2.1,
      blueBoost: 1.35,
      vignette: 0.75,
      grain: 0.045
    }
  },
  deepAbyss: {
    id: 'deepAbyss',
    name: 'Deep Oceanic',
    icon: Layers,
    config: {
      lineColor: '#051026',
      glowColor: '#38bdf8',
      speed: 0.12,
      scale: 1.9,
      rotation: 0,
      rotationSpeed: 0.12,
      layers: 4,
      waveAmplitude: 0.014,
      waveFrequency: 2.6,
      waveSpeed: 0.12,
      layerSpeed: 0.06,
      twist: 0.09,
      twistFrequency: 4.5,
      twistSpeed: 0.9,
      lineFrequency: 4.5,
      lineSpacing: 1.8,
      lineSharpness: 15,
      glowFalloff: 10,
      glowIntensity: 1.5,
      brightness: 1.9,
      blueBoost: 1.4,
      vignette: 0.8,
      grain: 0.04
    }
  },
  aurora: {
    id: 'aurora',
    name: 'Polar Aurora',
    icon: Sparkles,
    config: {
      lineColor: '#072a24',
      glowColor: '#10b981',
      speed: 0.22,
      scale: 2.3,
      rotation: 30,
      rotationSpeed: 0.22,
      layers: 6,
      waveAmplitude: 0.02,
      waveFrequency: 3.8,
      waveSpeed: 0.18,
      layerSpeed: 0.09,
      twist: 0.18,
      twistFrequency: 6.0,
      twistSpeed: 1.3,
      lineFrequency: 5.5,
      lineSpacing: 2.2,
      lineSharpness: 18,
      glowFalloff: 8.5,
      glowIntensity: 2.0,
      brightness: 2.2,
      blueBoost: 1.1,
      vignette: 0.7,
      grain: 0.05
    }
  }
};

const Hero = ({ onOpenSimulator, onOpenCustomizer, onSelectPreset, activePreset = 'sarRadar' }) => {
  const [activePresetKey, setActivePresetKey] = useState(activePreset);

  const handlePresetClick = (key) => {
    setActivePresetKey(key);
    if (onSelectPreset) onSelectPreset(key);
  };

  return (
    <section id="top" className="hero-section">
      {/* Subtle Radial Vignette Gradient */}
      <div className="hero-vignette-overlay" />

      {/* Main Foreground Content */}
      <div className="container hero-content">
        <div className="hero-pill">
          <span className="status-dot"></span>
          <span>SIH26059 • ANTARCTIC AUTONOMOUS NAVIGATION</span>
        </div>

        <h1 className="hero-title">
          Autonomous Satellite <br />
          <span className="glow-text">Iceberg Trajectory</span> AI
        </h1>

        <p className="hero-subtitle">
          Fusing Synthetic Aperture Radar (SAR), Coriolis hydrodynamic drift modeling, 
          and physics-informed machine learning to predict iceberg vectors across 
          <strong> +72-hour horizons</strong> with time-decaying uncertainty bounds.
        </p>

        {/* Specular Buttons CTAs */}
        <div className="hero-ctas">
          <SpecularButton
            size="lg"
            radius={22}
            tint="#00f2fe"
            tintOpacity={0.12}
            blur={10}
            textColor="#ffffff"
            lineColor="#00f2fe"
            baseColor="#083344"
            intensity={1.4}
            shineSize={12}
            shineFade={35}
            thickness={1.3}
            followMouse={true}
            proximity={300}
            onClick={onOpenSimulator}
          >
            <Compass size={18} />
            <span>Launch Trajectory Radar</span>
          </SpecularButton>

          <SpecularButton
            size="lg"
            radius={22}
            tint="#0a192f"
            tintOpacity={0.5}
            blur={12}
            textColor="#e0f2fe"
            lineColor="#38bdf8"
            baseColor="#1e293b"
            intensity={1.0}
            shineSize={14}
            shineFade={45}
            thickness={1.0}
            followMouse={true}
            proximity={250}
            onClick={() => {
              const el = document.getElementById('radar-simulator');
              el?.scrollIntoView({ behavior: 'smooth' });
            }}
          >
            <ShieldAlert size={18} />
            <span>View CPA Collision Risk</span>
          </SpecularButton>
        </div>

        {/* Live Metrics Row */}
        <div className="hero-specs-row">
          <div className="spec-item">
            <span className="spec-val gradient-text-cyan">99.4%</span>
            <span className="spec-label">SAR Detection Accuracy</span>
          </div>
          <div className="spec-item">
            <span className="spec-val gradient-text-ice">+72h</span>
            <span className="spec-label">Forecast Horizon</span>
          </div>
          <div className="spec-item">
            <span className="spec-val gradient-text-cyan">&lt; 1.8 km</span>
            <span className="spec-label">6h Uncertainty Radius</span>
          </div>
          <div className="spec-item">
            <span className="spec-val gradient-text-ice">Coriolis + Ekman</span>
            <span className="spec-label">Hydrodynamic Drag</span>
          </div>
        </div>

        {/* Interactive GhostFibers Preset Selector Dock */}
        <div className="shader-control-dock">
          <span className="dock-label">
            <Sliders size={13} />
            Shader Wavefield:
          </span>
          {Object.values(PRESETS).map(preset => {
            const Icon = preset.icon;
            const isActive = activePresetKey === preset.id;
            return (
              <button
                key={preset.id}
                type="button"
                className={`dock-btn ${activePresetKey === preset.id ? 'active' : ''}`}
                onClick={() => handlePresetClick(preset.id)}
              >
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                  <Icon size={12} />
                  {preset.name}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default Hero;
