import Hero from '../components/Hero';
import FeaturesGrid from '../components/FeaturesGrid';
import SensorFusionDeck from '../components/SensorFusionDeck';
import TrajectorySimulator from '../components/TrajectorySimulator';
import Footer from '../components/Footer';

const LandingPage = ({ onNavigateToConsole, onCalculateRoute, onInspectApi, onSelectPreset, activePreset }) => {
  return (
    <div className="landing-page-container">
      {/* Hero Section */}
      <Hero
        onOpenSimulator={onNavigateToConsole}
        onOpenCustomizer={onInspectApi}
        onSelectPreset={onSelectPreset}
        activePreset={activePreset}
      />

      {/* Quick Operational Trajectory Simulator Preview */}
      <TrajectorySimulator onCalculateRoute={onCalculateRoute} />

      {/* Feature Capabilities with BorderGlow */}
      <FeaturesGrid />

      {/* 4-Stage Architecture Fusion Deck */}
      <SensorFusionDeck onInspectApi={onInspectApi} />

      {/* Pre-footer and Footer */}
      <Footer onOpenSimulator={onNavigateToConsole} />
    </div>
  );
};

export default LandingPage;
