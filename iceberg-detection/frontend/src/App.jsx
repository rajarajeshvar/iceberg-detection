import { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import GhostFibers from './components/GhostFibers';
import LandingPage from './pages/LandingPage';
import OperationsConsole from './pages/OperationsConsole';
import DetailModal from './components/DetailModal';

const PRESETS = {
  sarRadar: {
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
    vignette: 0.8,
    grain: 0.045
  },
  deepAbyss: {
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
    vignette: 0.85,
    grain: 0.04
  },
  aurora: {
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
    vignette: 0.75,
    grain: 0.05
  }
};

function App() {
  const [activePage, setActivePage] = useState(() => {
    return window.location.hash === '#console' ? 'console' : 'landing';
  });
  const [activePreset, setActivePreset] = useState('sarRadar');
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTab, setModalTab] = useState('route');

  useEffect(() => {
    const handleHashChange = () => {
      setActivePage(window.location.hash === '#console' ? 'console' : 'landing');
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleNavigate = (page) => {
    setActivePage(page);
    window.location.hash = page === 'console' ? '#console' : '#landing';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const [liveRouteData, setLiveRouteData] = useState(null);
  const [livePredictionData, setLivePredictionData] = useState(null);

  const handleCalculateRoute = (routeResult = null, predResult = null) => {
    if (routeResult) setLiveRouteData(routeResult);
    if (predResult) setLivePredictionData(predResult);
    setModalTab('route');
    setModalOpen(true);
  };

  const handleInspectApi = (predResult = null) => {
    if (predResult) setLivePredictionData(predResult);
    setModalTab('api');
    setModalOpen(true);
  };

  return (
    <div className="app-root">
      {/* 
        Fixed Fullscreen GhostFibers Background 
        Undulates behind all pages, cards, and sections! 
      */}
      <div style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
        opacity: activePage === 'console' ? 0.45 : 0.85,
        transition: 'opacity 0.5s ease'
      }}>
        <GhostFibers {...PRESETS[activePreset]} />
      </div>

      {/* Global Vignette and Readability Gradient */}
      <div style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1,
        pointerEvents: 'none',
        background: 'radial-gradient(circle at 50% 40%, rgba(3, 7, 18, 0.25) 0%, rgba(3, 7, 18, 0.7) 60%, rgba(3, 7, 18, 0.95) 100%)'
      }} />

      {/* Foreground Content Container */}
      <div style={{ position: 'relative', zIndex: 10 }}>
        <Navbar
          activePage={activePage}
          onNavigate={handleNavigate}
        />

        <main>
          {activePage === 'landing' ? (
            <LandingPage
              onNavigateToConsole={() => handleNavigate('console')}
              onCalculateRoute={handleCalculateRoute}
              onInspectApi={handleInspectApi}
              onSelectPreset={setActivePreset}
              activePreset={activePreset}
            />
          ) : (
            <OperationsConsole
              onCalculateRoute={handleCalculateRoute}
              onInspectApi={handleInspectApi}
            />
          )}
        </main>
      </div>

      {/* Decision Support & REST API Modal */}
      <DetailModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        defaultTab={modalTab}
        liveRouteData={liveRouteData}
        livePredictionData={livePredictionData}
      />
    </div>
  );
}

export default App;
