import React from 'react';

interface Props {
  reason: string | null;
}

export const AbstainView: React.FC<Props> = ({ reason }) => {
  return (
    <div
      style={{
        backgroundColor: 'rgba(30, 41, 59, 0.6)',
        border: '1px solid rgba(148, 163, 184, 0.25)',
        borderRadius: '0.5rem',
        padding: '1.5rem',
        textAlign: 'center',
        marginTop: '1rem'
      }}
    >
      <div style={{ fontSize: '1.75rem', marginBottom: '0.5rem' }}>🛡️</div>
      <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
        Authoritative Abstention
      </h3>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '600px', margin: '0 auto 1rem' }}>
        {reason || 'The indexed 3GPP specifications do not contain sufficient authoritative evidence to reliably answer this query without hallucination.'}
      </p>
      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        Deterministic Grounding Gate: Query evidence score fell below threshold. No unsupported assertions were generated.
      </p>
    </div>
  );
};
