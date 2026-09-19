import { Radar, Compass, Shield, ArrowUp, Cpu } from 'lucide-react';
import SpecularButton from './SpecularButton';

const Footer = ({ onOpenSimulator }) => {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <>
      {/* Pre-footer CTA Section */}
      <section className="section" style={{ paddingTop: 0 }}>
        <div className="container">
          <div className="cta-banner">
            <div className="cta-banner-content">
              <h2 className="cta-title">
                Safeguarding Maritime Routes in the <span className="gradient-text-cyan">Southern Ocean</span>
              </h2>
              <p className="cta-desc">
                Deploy autonomous satellite radar intelligence, hydrodynamic drift physics, 
                and predictive collision alerting directly to your fleet management operations.
              </p>
              <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', flexWrap: 'wrap' }}>
                <SpecularButton
                  size="lg"
                  radius={20}
                  tint="#00f2fe"
                  tintOpacity={0.15}
                  blur={10}
                  textColor="#ffffff"
                  lineColor="#00f2fe"
                  baseColor="#083344"
                  intensity={1.3}
                  thickness={1.2}
                  onClick={onOpenSimulator}
                >
                  <Radar size={18} />
                  <span>Launch Trajectory Engine</span>
                </SpecularButton>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Main Footer */}
      <footer className="footer">
        <div className="container">
          <div className="footer-grid">
            <div className="footer-brand">
              <div className="brand-logo">
                <div className="brand-icon">
                  <Radar size={20} />
                </div>
                <span>CryoPulse <span className="gradient-text-cyan">AI</span></span>
              </div>
              <p style={{ maxWidth: '320px', lineHeight: '1.6', fontSize: '0.85rem' }}>
                Autonomous Satellite Iceberg Detection, Coriolis Hydrodynamic Trajectory Prediction, 
                and Sea-Ice Maritime Decision Engine.
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
                <span className="status-dot"></span>
                <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                  SIH26059 System Specification v2.4
                </span>
              </div>
            </div>

            <div>
              <h5 className="footer-col-title">Navigation</h5>
              <ul className="footer-links">
                <li><a href="#top" className="footer-link">Home Overview</a></li>
                <li><a href="#radar-simulator" className="footer-link">Drift Simulator</a></li>
                <li><a href="#features" className="footer-link">SAR Detection</a></li>
                <li><a href="#architecture" className="footer-link">System Architecture</a></li>
              </ul>
            </div>

            <div>
              <h5 className="footer-col-title">Scientific Models</h5>
              <ul className="footer-links">
                <li><span className="footer-link">Coriolis Leeway Physics</span></li>
                <li><span className="footer-link">Ekman Layer Spiral</span></li>
                <li><span className="footer-link">Kalman Error Ellipses</span></li>
                <li><span className="footer-link">A* Fuel Optimization</span></li>
              </ul>
            </div>

            <div>
              <h5 className="footer-col-title">Components</h5>
              <ul className="footer-links">
                <li><span className="footer-link">React Bits GhostFibers</span></li>
                <li><span className="footer-link">React Bits SpecularButton</span></li>
                <li><span className="footer-link">OGL WebGL 2 Engine</span></li>
                <li><span className="footer-link">FastAPI Python Engine</span></li>
              </ul>
            </div>
          </div>

          <div className="footer-bottom">
            <span>© 2026 CryoPulse AI • Iceberg Detection & Maritime Trajectory Engine. All rights reserved.</span>
            <button
              type="button"
              onClick={scrollToTop}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                color: 'var(--text-secondary)',
                padding: '6px 14px',
                borderRadius: 'var(--radius-full)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.78rem'
              }}
            >
              <ArrowUp size={13} />
              <span>Back to Top</span>
            </button>
          </div>
        </div>
      </footer>
    </>
  );
};

export default Footer;
