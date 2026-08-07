import React from 'react';

export default function Header({ llmRoute, literacyTier, isRecording }) {
  const isOnline = llmRoute.includes('CLOUD') || llmRoute.includes('CLAUDE');

  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="logo-icon">⚖️</div>
        <div>
          <h1 className="header-title">NYAYA-DHWANI</h1>
          <p className="header-subtitle">Legal Literacy Conversational Agent</p>
        </div>
      </div>
      
      <div className="header-status-badges">
        {/* Network & LLM Hybrid Route Status Badge */}
        <div className={`status-pill ${isOnline ? 'pill-online' : 'pill-offline'}`}>
          <span className="status-dot"></span>
          <span>{isOnline ? 'ONLINE (Cloud Claude API)' : 'OFFLINE (Local Ollama LLM)'}</span>
        </div>

        {/* Literacy Tier Badge */}
        <div className="tier-badge">
          <span className="badge-label">Literacy Tier:</span>
          <span className={`badge-value tier-${literacyTier.toLowerCase()}`}>{literacyTier}</span>
        </div>

        {/* Live Audio Recording Badge */}
        {isRecording && (
          <div className="recording-badge">
            <span className="pulse-dot"></span>
            <span>RECORDING AUDIO</span>
          </div>
        )}
      </div>
    </header>
  );
}
