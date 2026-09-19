import { useState, useEffect } from 'react';
import { Radar, Compass, Activity, ShieldCheck, Terminal, Globe, Home, CheckCircle, AlertCircle } from 'lucide-react';
import SpecularButton from './SpecularButton';
import { checkBackendHealth } from '../services/api';

const Navbar = ({ activePage, onNavigate }) => {
  const [scrolled, setScrolled] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 40);
    };
    window.addEventListener('scroll', handleScroll);

    const checkStatus = async () => {
      const data = await checkBackendHealth();
      setBackendOnline(!!data && data.status === 'healthy');
    };
    checkStatus();
    const interval = setInterval(checkStatus, 10000);

    return () => {
      window.removeEventListener('scroll', handleScroll);
      clearInterval(interval);
    };
  }, []);

  return (
    <header className={`navbar ${scrolled ? 'scrolled' : ''}`}>
      <div className="container nav-content">
        <button
          type="button"
          onClick={() => onNavigate('landing')}
          className="brand-logo"
          style={{ background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left', padding: 0 }}
        >
          <div className="brand-icon">
            <Radar size={22} />
          </div>
          <span>CryoPulse <span className="gradient-text-cyan">AI</span></span>
        </button>

        {/* Page Switcher Tabs */}
        <div style={{
          display: 'flex',
          background: 'rgba(5, 12, 24, 0.8)',
          border: '1px solid rgba(0, 242, 254, 0.25)',
          borderRadius: '9999px',
          padding: '4px'
        }}>
          <button
            type="button"
            onClick={() => onNavigate('landing')}
            style={{
              background: activePage === 'landing' ? 'rgba(0, 242, 254, 0.2)' : 'transparent',
              border: `1px solid ${activePage === 'landing' ? 'var(--accent-cyan)' : 'transparent'}`,
              color: activePage === 'landing' ? '#fff' : 'var(--text-muted)',
              borderRadius: '9999px',
              padding: '6px 16px',
              fontSize: '0.8rem',
              fontFamily: 'var(--font-mono)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s'
            }}
          >
            <Home size={13} />
            <span>Landing Page</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('console')}
            style={{
              background: activePage === 'console' ? 'rgba(0, 242, 254, 0.2)' : 'transparent',
              border: `1px solid ${activePage === 'console' ? 'var(--accent-cyan)' : 'transparent'}`,
              color: activePage === 'console' ? '#fff' : 'var(--text-muted)',
              borderRadius: '9999px',
              padding: '6px 16px',
              fontSize: '0.8rem',
              fontFamily: 'var(--font-mono)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s'
            }}
          >
            <Globe size={13} color={activePage === 'console' ? '#00f2fe' : 'currentColor'} />
            <span>Operations Console</span>
          </button>
        </div>

        <div className="nav-actions">
          <div className="badge-stream" style={{
            borderColor: backendOnline ? 'rgba(16, 185, 129, 0.4)' : 'rgba(245, 158, 11, 0.4)',
            background: backendOnline ? 'rgba(16, 185, 129, 0.08)' : 'rgba(245, 158, 11, 0.08)',
            color: backendOnline ? '#34d399' : '#fbbf24'
          }}>
            <span className="status-dot" style={{
              backgroundColor: backendOnline ? '#10b981' : '#f59e0b'
            }}></span>
            <span>{backendOnline ? 'FastAPI :8000 Connected' : 'Engine Connecting...'}</span>
          </div>

          <SpecularButton
            size="sm"
            radius={14}
            tint="#00f2fe"
            tintOpacity={0.1}
            lineColor="#00f2fe"
            baseColor="#0e3a5a"
            intensity={1.2}
            shineSize={14}
            thickness={1.2}
            onClick={() => onNavigate(activePage === 'landing' ? 'console' : 'landing')}
          >
            <Terminal size={14} />
            <span>{activePage === 'landing' ? 'Launch Console' : 'View Landing Page'}</span>
          </SpecularButton>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
