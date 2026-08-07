import React from 'react';

export default function ResponseCard({ response, onSelectFollowup }) {
  if (!response) {
    return (
      <div className="response-card placeholder-card">
        <p className="placeholder-text">Press <strong>Action 1</strong> or tap the microphone button above to start your legal inquiry.</p>
      </div>
    );
  }

  const { action_name, answer_text, literacy_tier, rag_executed, llm_route, socratic_followups } = response;

  return (
    <div className="response-card">
      <div className="card-header">
        <div className="card-title-group">
          <span className="card-badge">{action_name}</span>
          <span className={`rag-badge ${rag_executed ? 'rag-enabled' : 'rag-bypassed'}`}>
            {rag_executed ? '🔍 Dual-RAG Executed' : '⚡ STRICT RAG Bypass'}
          </span>
        </div>
        <span className="route-tag">Route: {llm_route}</span>
      </div>

      <div className="card-body">
        <p className="response-text">{answer_text}</p>
      </div>

      {socratic_followups && socratic_followups.length > 0 && (
        <div className="socratic-container">
          <h4 className="socratic-title">❓ Recommended Socratic Follow-Up Questions:</h4>
          <div className="socratic-list">
            {socratic_followups.map((q, idx) => (
              <button
                key={idx}
                className="socratic-chip"
                onClick={() => onSelectFollowup(q)}
              >
                <span>{q}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
