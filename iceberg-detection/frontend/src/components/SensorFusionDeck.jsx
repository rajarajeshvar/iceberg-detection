import { Satellite, Cpu, AlertCircle, Ship, ArrowRight, ExternalLink } from 'lucide-react';
import SpecularButton from './SpecularButton';

const STEPS = [
  {
    num: '01',
    icon: Satellite,
    badge: 'Feature 1',
    title: 'Detection & Morphology',
    desc: 'Dual-polarized SAR imagery pinpoints iceberg centroids, calculates perimeter length, surface area, and estimates submerged keel drafts.'
  },
  {
    num: '02',
    icon: Cpu,
    badge: 'Feature 2 (Prediction Engine)',
    title: 'Hydrodynamic Drift Forecasting',
    desc: 'Combines wind vectors, ocean currents, Coriolis deflection, and physical drag to calculate trajectories across +6h to +72h horizons.'
  },
  {
    num: '03',
    icon: AlertCircle,
    badge: 'Feature 3',
    title: 'CPA / TCPA Collision Risk',
    desc: 'Projects expanding uncertainty radii against vessel forward dead reckoning, identifying critical collision corridors.'
  },
  {
    num: '04',
    icon: Ship,
    badge: 'Feature 4',
    title: 'Bridge Decision Support',
    desc: 'Generates fuel-optimized safe navigation paths avoiding sea-ice pack concentrations (>60%) and drifting tabular fragments.'
  }
];

const SensorFusionDeck = ({ onInspectApi }) => {
  return (
    <section id="architecture" className="section">
      <div className="container">
        <div className="section-header">
          <div className="section-badge">
            <Cpu size={14} />
            <span>End-to-End Pipeline</span>
          </div>
          <h2 className="section-title">
            Integrated <span className="gradient-text-ice">System Architecture</span>
          </h2>
          <p className="section-desc">
            Directly connected to the Python FastAPI backend engine for continuous inference and sub-second calculation.
          </p>
        </div>

        <div className="fusion-deck">
          <div className="fusion-flow">
            {STEPS.map((s, idx) => {
              const Icon = s.icon;
              return (
                <div key={idx} className="flow-step">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <span className="step-num">{s.num}</span>
                    <span style={{
                      fontSize: '0.68rem',
                      fontFamily: 'var(--font-mono)',
                      background: 'rgba(0, 242, 254, 0.1)',
                      border: '1px solid rgba(0, 242, 254, 0.25)',
                      color: 'var(--accent-cyan)',
                      padding: '2px 8px',
                      borderRadius: '4px'
                    }}>
                      {s.badge}
                    </span>
                  </div>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '8px',
                    background: 'rgba(255, 255, 255, 0.05)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--accent-cyan)',
                    marginBottom: '14px'
                  }}>
                    <Icon size={20} />
                  </div>
                  <h4 className="step-title">{s.title}</h4>
                  <p className="step-desc">{s.desc}</p>
                </div>
              );
            })}
          </div>

          <div style={{
            marginTop: '36px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '16px',
            paddingTop: '24px',
            borderTop: '1px solid rgba(255, 255, 255, 0.06)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span className="status-dot"></span>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                FastAPI Prediction Engine: <code style={{ color: 'var(--accent-cyan)' }}>POST /api/v1/prediction/trajectory</code>
              </span>
            </div>

            <SpecularButton
              size="sm"
              radius={12}
              tint="#38bdf8"
              tintOpacity={0.1}
              lineColor="#38bdf8"
              baseColor="#1e293b"
              intensity={1.1}
              onClick={onInspectApi}
            >
              <ExternalLink size={14} />
              <span>Inspect API Spec & JSON Contract</span>
            </SpecularButton>
          </div>
        </div>
      </div>
    </section>
  );
};

export default SensorFusionDeck;
