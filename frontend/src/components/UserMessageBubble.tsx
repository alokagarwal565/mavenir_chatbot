import React from 'react';

interface Props {
  question: string;
  timestamp: string;
  specFilter?: string | null;
  releaseFilter?: number | null;
}

export const UserMessageBubble: React.FC<Props> = ({
  question,
  timestamp,
  specFilter,
  releaseFilter,
}) => {
  return (
    <div
      className="animate-fade-in"
      style={{
        display: 'flex',
        justifyContent: 'flex-end',
        alignItems: 'flex-start',
        gap: '0.85rem',
        marginBottom: '2rem',
        width: '100%'
      }}
    >
      <div
        style={{
          maxWidth: '80%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-end',
          gap: '0.4rem'
        }}
      >
        {/* User Metadata Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
          <span style={{
            fontSize: '0.675rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-dim)'
          }}>
            {timestamp}
          </span>

          <span style={{
            fontSize: '0.675rem',
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            color: 'var(--accent-cyan)',
            background: 'rgba(6, 182, 212, 0.12)',
            border: '1px solid rgba(6, 182, 212, 0.25)',
            padding: '0.1rem 0.4rem',
            borderRadius: '0.25rem'
          }}>
            {releaseFilter ? `Rel-${releaseFilter}` : 'All Releases'}
          </span>

          <span style={{
            fontSize: '0.675rem',
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            color: '#a5b4fc',
            background: 'rgba(99, 102, 241, 0.12)',
            border: '1px solid rgba(99, 102, 241, 0.25)',
            padding: '0.1rem 0.4rem',
            borderRadius: '0.25rem'
          }}>
            {specFilter ? specFilter : 'All Core 5GS'}
          </span>
        </div>

        {/* User Query Bubble */}
        <div
          style={{
            background: 'linear-gradient(135deg, #1e3a8a 0%, #1e293b 100%)',
            border: '1px solid rgba(59, 130, 246, 0.35)',
            borderRadius: '1.1rem 0.25rem 1.1rem 1.1rem',
            padding: '1rem 1.25rem',
            color: '#ffffff',
            fontSize: '0.95rem',
            lineHeight: 1.6,
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.35), 0 0 12px rgba(59, 130, 246, 0.2)'
          }}
        >
          {question}
        </div>
      </div>

      {/* User Avatar Circle */}
      <div
        style={{
          width: '38px',
          height: '38px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1rem',
          color: '#ffffff',
          boxShadow: '0 4px 12px rgba(59, 130, 246, 0.4)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
          flexShrink: 0,
          marginTop: '1.25rem'
        }}
        title="Telecom Engineer"
      >
        👤
      </div>
    </div>
  );
};
