import React from 'react';

export default function ActionGrid({ onActionTrigger, isRecording, isPlaying }) {
  const actions = [
    {
      code: 1,
      name: "Ask New Question",
      icon: "🎙️",
      actionText: "RECORD",
      color: "btn-primary",
      tooltip: "Action 1: Tap to record your legal query (Executes Dual-RAG)",
      badge: "RAG Active"
    },
    {
      code: 2,
      name: "Voice Input Over",
      icon: "⏹️",
      actionText: "SUBMIT",
      color: "btn-secondary",
      tooltip: "Action 2: Stop recording audio and submit for AI processing",
      badge: "RAG Active"
    },
    {
      code: 3,
      name: "Repeat Answer",
      icon: "🔄",
      actionText: "REPLAY",
      color: "btn-info",
      tooltip: "Action 3: Replay last answer from call session memory (Strict RAG Bypass)",
      badge: "RAG Bypass"
    },
    {
      code: 4,
      name: "Simplify Text",
      icon: "💡",
      actionText: "SIMPLIFY",
      color: "btn-warning",
      tooltip: "Action 4: Drop literacy tier & simplify explanation (Strict RAG Bypass)",
      badge: "RAG Bypass"
    },
    {
      code: 5,
      name: "Recommend Questions",
      icon: "❓",
      actionText: "SOCRATIC",
      color: "btn-accent",
      tooltip: "Action 5: Generate recommended Socratic follow-up questions (Strict RAG Bypass)",
      badge: "RAG Bypass"
    },
    {
      code: 6,
      name: "Stop Playback",
      icon: "🖐️",
      actionText: "BARGE-IN",
      color: "btn-danger",
      tooltip: "Action 6: Instantly stop audio response playback",
      badge: "Interrupt"
    }
  ];

  return (
    <section className="action-grid-section">
      <h2 className="section-heading">6-ACTION VOICE CONTROL CENTER</h2>
      <div className="action-grid-container">
        {actions.map((act) => (
          <div key={act.code} className="action-btn-wrapper">
            <button
              className={`massive-action-btn ${act.color} ${isRecording && act.code === 2 ? 'btn-active-recording' : ''}`}
              onClick={() => onActionTrigger(act.code)}
              aria-label={act.name}
            >
              <div className="btn-icon">{act.icon}</div>
              <div className="btn-details">
                <span className="btn-code">ACTION {act.code}</span>
                <span className="btn-name">{act.name}</span>
              </div>
              <span className={`btn-rag-tag ${act.badge === 'RAG Active' ? 'tag-rag-on' : 'tag-rag-off'}`}>
                {act.badge}
              </span>
            </button>
            
            {/* Non-Overlapping Tooltip element with isolated z-index container */}
            <div className="action-btn-tooltip" role="tooltip">
              <div className="tooltip-arrow"></div>
              <span>{act.tooltip}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
