import { useState } from 'react';
import { DebugInfo } from '../types/api';

interface Props {
  debug: DebugInfo;
}

export const DebugPanel = ({ debug }: Props) => {
  const [open, setOpen] = useState(false);

  return (
    <div style={{ marginTop: '1.5rem', border: '1px solid var(--border)', borderRadius: '0.5rem', overflow: 'hidden' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: '100%',
          padding: '0.6rem 1rem',
          background: 'var(--bg-card)',
          border: 'none',
          color: 'var(--text-secondary)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
          fontSize: '0.8rem',
          fontFamily: 'var(--font-mono)'
        }}
      >
        <span>🛠️ Evidence & Diagnostic Pipeline ({debug.top_chunks.length} chunks analyzed)</span>
        <span>{open ? '▲ Collapse' : '▼ Expand'}</span>
      </button>

      {open && (
        <div style={{ padding: '1rem', backgroundColor: 'var(--bg-input)', fontSize: '0.8rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '1rem' }}>
            <div style={{ background: 'var(--bg-card)', padding: '0.5rem', borderRadius: '0.25rem' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>EVIDENCE SCORE</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--accent-blue)' }}>{debug.evidence_score}</div>
            </div>
            <div style={{ background: 'var(--bg-card)', padding: '0.5rem', borderRadius: '0.25rem' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>CANDIDATES RETRIEVED</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>{debug.retrieval_count}</div>
            </div>
            <div style={{ background: 'var(--bg-card)', padding: '0.5rem', borderRadius: '0.25rem' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>CHUNKS RERANKED</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--accent-purple)' }}>{debug.reranked_count}</div>
            </div>
          </div>

          <h4 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem', fontSize: '0.85rem' }}>Top Scored Evidence Chunks</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {debug.top_chunks.map((chunk) => (
              <div
                key={chunk.chunk_id}
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  borderRadius: '0.25rem',
                  padding: '0.6rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--accent-cyan)', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
                  <span>{chunk.spec_number} Clause {chunk.section_number || 'N/A'}</span>
                  <span>RRF: {chunk.rrf_score.toFixed(4)} {chunk.reranker_score !== null ? `| Rerank: ${chunk.reranker_score.toFixed(3)}` : ''}</span>
                </div>
                <p style={{ color: '#cbd5e1', fontSize: '0.75rem', marginTop: '0.25rem' }}>{chunk.text_preview}...</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
