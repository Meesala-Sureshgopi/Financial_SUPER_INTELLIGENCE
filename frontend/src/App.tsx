import React, { useEffect, useState } from 'react';
import Dashboard from './components/Dashboard';
// @ts-ignore
import PortfolioView from './components/PortfolioView';
// @ts-ignore
import ScenarioDemo from './components/ScenarioDemo';
// @ts-ignore
import CopilotChat from './components/CopilotChat';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="app">
      <header className={`app-header ${scrolled ? 'scrolled' : ''}`}>
        <div className="logo">
          <div className="logo-icon">✨</div>
          <div className="logo-text">
            <h1>AVALON</h1>
            <span>INTELLIGENCE ORCHESTRATOR</span>
          </div>
        </div>

        <nav className="nav-tabs">
          {[
            { id: 'dashboard', label: '📊 Intelligence' },
            { id: 'portfolio', label: '💼 Portfolio' }
          ].map((tab) => (
            <button
              key={tab.id}
              className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="header-right">
          <div className="live-indicator">
            <div className="live-dot"></div>
            Network Synchronized
          </div>
        </div>
      </header>

      <main className="app-content fade-in">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'portfolio' && <PortfolioView />}
      </main>

      <CopilotChat />

      <footer className="app-footer">
        <div className="footer-meta">
          <span>🧠 Neural Engine v2.0</span>
          <span>📡 Real-time NSE</span>
          <span>⚖️ Regulatory Guardrails</span>
        </div>
      </footer>

      <div className="bg-glow bg-glow-1"></div>
      <div className="bg-glow bg-glow-2"></div>
    </div>
  );
};

export default App;
