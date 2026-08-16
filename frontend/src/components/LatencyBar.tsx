import React from 'react';
import { DebugInfo } from '../types/api';

interface Props {
  totalMs: number;
  debug?: DebugInfo | null;
}

const fmt = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
};

export const LatencyBar: React.FC<Props> = ({ totalMs, debug }) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        fontSize: '0.75rem',
        color: 'var(--text-muted)',
        fontFamily: 'var(--font-mono)',
        marginTop: '0.5rem'
      }}
    >
      <span>⚡ Total: <strong>{fmt(totalMs)}</strong></span>
      {debug && (
        <>
          <span>🔍 Retrieval: {fmt(debug.retrieval_ms)}</span>
          <span>⚖️ Reranker: {fmt(debug.reranker_ms)}</span>
          <span>🤖 LLM: {fmt(debug.llm_ms)}</span>
        </>
      )}
    </div>
  );
};
