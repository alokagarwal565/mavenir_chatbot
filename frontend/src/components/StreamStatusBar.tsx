import React from 'react';

export const StreamStatusBar: React.FC<{
  status: string | null;
  isStreaming: boolean;
}> = ({ status, isStreaming }) => {
  if (!status && !isStreaming) return null;

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.5rem',
        fontSize: '0.7rem',
        fontFamily: 'var(--font-mono)',
        fontWeight: 600,
        background: 'rgba(11, 17, 32, 0.9)',
        padding: '0.35rem 0.7rem',
        borderRadius: '9999px',
        border: '1px solid var(--border-glass)',
        marginBottom: '1rem'
      }}
    >
      <div
        className={isStreaming ? "pulse-dot" : ""}
        style={{
          backgroundColor: isStreaming ? 'var(--accent-cyan)' : 'var(--accent-emerald)',
          width: '8px',
          height: '8px',
          borderRadius: '50%'
        }}
      />
      <span style={{ color: isStreaming ? 'var(--accent-cyan)' : 'var(--accent-emerald)' }}>
        {status || 'Stream complete'}
      </span>
    </div>
  );
};
