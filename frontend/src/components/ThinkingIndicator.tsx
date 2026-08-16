import { useState, useEffect } from 'react';

const STAGES = [
  { icon: '🔍', text: 'Scanning 3GPP specifications database...' },
  { icon: '⚖️', text: 'Ranking and filtering relevant sections...' },
  { icon: '📊', text: 'Evaluating citations and extracting call flows...' },
  { icon: '⚡', text: 'Synthesizing final response...' }
];

export const ThinkingIndicator = () => {
  const [currentStage, setCurrentStage] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStage((prev) => (prev + 1) % STAGES.length);
    }, 1800);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      className="glass-panel animate-fade-in"
      style={{
        padding: '1.25rem 1.5rem',
        marginBottom: '1.75rem',
        border: '1px solid var(--border-cyan-glow)',
        boxShadow: '0 0 24px rgba(6, 182, 212, 0.15)',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        maxWidth: '850px'
      }}
    >
      <div
        style={{
          width: '38px',
          height: '38px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #2563eb 0%, #06b6d4 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 16px rgba(6, 182, 212, 0.4)',
          flexShrink: 0
        }}
      >
        <span style={{
          display: 'inline-block',
          width: '18px',
          height: '18px',
          border: '2px solid #ffffff',
          borderTopColor: 'transparent',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite'
        }} />
      </div>

      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)' }}>
            3GPP Standards Intelligence Pipeline
          </span>
          <span style={{
            fontSize: '0.65rem',
            fontWeight: 700,
            color: 'var(--accent-cyan)',
            background: 'rgba(6, 182, 212, 0.15)',
            border: '1px solid rgba(6, 182, 212, 0.3)',
            padding: '0.1rem 0.35rem',
            borderRadius: '0.25rem',
            fontFamily: 'var(--font-mono)'
          }}>
            Step {currentStage + 1}/4
          </span>
        </div>

        <div style={{
          fontSize: '0.8rem',
          color: 'var(--accent-cyan)',
          fontFamily: 'var(--font-mono)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          transition: 'all 0.3s ease'
        }}>
          <span>{STAGES[currentStage].icon}</span>
          <span>{STAGES[currentStage].text}</span>
        </div>
      </div>
    </div>
  );
};
