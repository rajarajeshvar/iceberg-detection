import { Satellite, Waves, ShieldAlert, Route, Cpu, Target, Orbit, Compass } from 'lucide-react';
import BorderGlow from './BorderGlow';
import SpecularButton from './SpecularButton';

const FEATURES = [
  {
    icon: Satellite,
    title: 'Dual-Band SAR Constellation Fusion',
    desc: 'Real-time ingestion of Sentinel-1 C-band SAR and Radarsat Constellation Mission (RCM) radar data with adaptive Constant False Alarm Rate (CFAR) filtering.',
    tags: ['Sentinel-1', 'SAR Polarization', 'All-Weather Vision', 'CFAR Engine'],
    colors: ['#00f2fe', '#38bdf8', '#6366f1'],
    glowColor: '185 100 65'
  },
  {
    icon: Waves,
    title: 'Coriolis Hydrodynamic Drift Engine',
    desc: 'Simulates leeway angle deflection, Ekman spiral currents, wind drag, and wave radiation stress tailored to Antarctic southern hemisphere physics.',
    tags: ['Ekman Drift', 'Wind Leeway', 'Drag Coefficients', 'Ocean Currents'],
    colors: ['#38bdf8', '#00f2fe', '#06b6d4'],
    glowColor: '195 95 65'
  },
  {
    icon: ShieldAlert,
    title: 'Multi-Horizon Uncertainty Bounds',
    desc: 'Dynamic error propagation modeling expanding radii (+6h to +72h) calibrated with historical Antarctic tracking to quantify confidence metrics.',
    tags: ['Kalman Filter', 'Uncertainty Radii', 'Decay Curves', '+72h Forecast'],
    colors: ['#818cf8', '#c084fc', '#38bdf8'],
    glowColor: '235 90 70'
  },
  {
    icon: Route,
    title: 'A* Fuel & Safety Route Optimization',
    desc: 'Evaluates Closest Point of Approach (CPA) and Time to CPA (TCPA) against vessel navigational parameters to steer safely through sea-ice channels.',
    tags: ['CPA / TCPA', 'Fuel Minimization', 'Sea-Ice Avoidance', 'SOLAS Compliant'],
    colors: ['#10b981', '#38bdf8', '#00f2fe'],
    glowColor: '160 85 65'
  },
  {
    icon: Cpu,
    title: 'Physics-Informed XGBoost + ODEs',
    desc: 'Combines deterministic differential equations of floating bodies with gradient boosted ensembles to capture chaotic wave-ice interactions.',
    tags: ['XGBoost Engine', 'Physics-Informed', 'Ablation Decay', 'Sub-second Latency'],
    colors: ['#00f2fe', '#818cf8', '#38bdf8'],
    glowColor: '190 95 65'
  },
  {
    icon: Target,
    title: 'Automated Maritime REST Contracts',
    desc: 'Direct JSON schema integration with Electronic Chart Display and Information Systems (ECDIS) and bridge decision support consoles.',
    tags: ['REST API', 'GeoJSON Polygons', 'ECDIS Stream', 'ISO Maritime Standard'],
    colors: ['#38bdf8', '#00f2fe', '#a855f7'],
    glowColor: '200 90 65'
  }
];

const FeaturesGrid = () => {
  return (
    <section id="features" className="section" style={{ backgroundColor: 'rgba(2, 6, 16, 0.6)' }}>
      <div className="container">
        <div className="section-header">
          <div className="section-badge">
            <Orbit size={14} />
            <span>Autonomous Intelligence Suite</span>
          </div>
          <h2 className="section-title">
            Engineered for <span className="gradient-text-cyan">Extreme Polar Seas</span>
          </h2>
          <p className="section-desc">
            Standard radar fails against stealthy bergy bits and low-freeboard ice hazards. 
            CryoPulse AI provides continuous, multi-satellite situational awareness. Hover near card edges to activate edge-sensing vector radar glow.
          </p>
        </div>

        <div className="features-grid">
          {FEATURES.map((feat, idx) => {
            const Icon = feat.icon;
            return (
              <BorderGlow
                key={idx}
                edgeSensitivity={28}
                glowColor={feat.glowColor}
                backgroundColor="rgba(7, 19, 36, 0.85)"
                borderRadius={20}
                glowRadius={38}
                glowIntensity={1.2}
                coneSpread={28}
                colors={feat.colors}
              >
                <div className="feature-card" style={{ height: '100%' }}>
                  <div className="feature-icon-wrapper">
                    <Icon size={24} />
                  </div>
                  <h3 className="feature-card-title">{feat.title}</h3>
                  <p className="feature-card-desc">{feat.desc}</p>
                  <div className="feature-tag-list">
                    {feat.tags.map((t, i) => (
                      <span key={i} className="feature-tag">{t}</span>
                    ))}
                  </div>
                </div>
              </BorderGlow>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default FeaturesGrid;
