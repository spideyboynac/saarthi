import React from 'react';

export default function ResponseCard({ response, onSelectFollowup }) {
  if (!response) {
    return (
      <div className="response-card placeholder-card">
        <p className="placeholder-text">Press <strong>Action 1</strong> or tap the microphone button above to start your legal inquiry.</p>
      </div>
    );
  }

  const {
    action_name,
    question,
    user_question,
    answer,
    answer_text,
    sources,
    citations,
    literacy_tier,
    rag_executed,
    llm_route,
    socratic_followups
  } = response;

  const displayQuestion = question || user_question;
  const displayAnswer = answer || answer_text || response.text;
  const displaySources = (sources && sources.length > 0) ? sources : (citations || []);

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
        {/* 1. Question Block */}
        {displayQuestion && (
          <div className="response-block question-block">
            <div className="block-label">💬 Question:</div>
            <p className="question-text">{displayQuestion}</p>
          </div>
        )}

        {/* 2. Answer Block */}
        <div className="response-block answer-block">
          <div className="block-label">⚖️ Legal Explanation:</div>
          <p className="answer-text">{displayAnswer}</p>
        </div>

        {/* 3. Sources Block */}
        {displaySources && displaySources.length > 0 && (
          <div className="response-block sources-block">
            <div className="block-label">📜 Verified Sources:</div>
            <div className="sources-list">
              {displaySources.map((src, idx) => (
                <span key={idx} className="source-pill">
                  📌 {src}
                </span>
              ))}
            </div>
          </div>
        )}
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
