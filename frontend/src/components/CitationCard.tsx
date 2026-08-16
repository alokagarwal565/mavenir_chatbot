import { useState } from 'react';
import { ClaimSource } from '../types/api';

interface Props {
  source: ClaimSource;
  index: number;
}

export const CitationCard = ({ source, index }: Props) => {
  const [copied, setCopied] = useState(false);

  const copyCitation = () => {
    const citationText = `3GPP ${source.spec_number} Rel-${source.release} v${source.version}, Clause ${source.section_number || 'N/A'}${source.section_title ? ` ("${source.section_title}")` : ''}`;
    navigator.clipboard.writeText(citationText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="glass-card"
      style={{
        padding: '1.1rem',
        marginBottom: '0.85rem',
        border: '1px solid var(--border-glass)',
        borderRadius: '0.75rem',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span
            style={{
              backgroundColor: 'var(--accent-blue)',
              color: '#ffffff',
              fontSize: '0.7rem',
              fontWeight: 700,
              padding: '0.15rem 0.5rem',
              borderRadius: '0.35rem',
              fontFamily: 'var(--font-mono)',
              boxShadow: '0 2px 6px rgba(59, 130, 246, 0.4)'
            }}
          >
            [{index + 1}]
          </span>
          <span style={{ fontWeight: 700, color: 'var(--text-main)', fontSize: '0.95rem', letterSpacing: '-0.01em' }}>
            {source.spec_number}
          </span>
          <span
            style={{
              fontSize: '0.725rem',
              fontWeight: 600,
              color: 'var(--accent-cyan)',
              backgroundColor: 'rgba(6, 182, 212, 0.12)',
              border: '1px solid rgba(6, 182, 212, 0.3)',
              padding: '0.1rem 0.5rem',
              borderRadius: '0.35rem',
              fontFamily: 'var(--font-mono)'
            }}
          >
            Rel-{source.release} v{source.version}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {source.section_number && (
            <span style={{
              fontSize: '0.775rem',
              fontWeight: 600,
              color: '#93c5fd',
              background: 'rgba(30, 58, 138, 0.35)',
              padding: '0.2rem 0.5rem',
              borderRadius: '0.35rem',
              border: '1px solid rgba(59, 130, 246, 0.25)',
              fontFamily: 'var(--font-mono)'
            }}>
              Clause {source.section_number} {source.page_start ? `· p.${source.page_start}` : ''}
            </span>
          )}

          <button
            type="button"
            onClick={copyCitation}
            title="Copy standard citation reference"
            style={{
              background: copied ? 'rgba(16, 185, 129, 0.2)' : 'rgba(15, 23, 42, 0.6)',
              border: copied ? '1px solid var(--accent-emerald)' : '1px solid var(--border-subtle)',
              color: copied ? 'var(--accent-emerald)' : 'var(--text-dim)',
              fontSize: '0.7rem',
              fontWeight: 600,
              padding: '0.2rem 0.5rem',
              borderRadius: '0.35rem',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            {copied ? '✓ Copied' : '📋 Copy Ref'}
          </button>
        </div>
      </div>

      {source.section_title && (
        <p style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.6rem' }}>
          {source.section_title}
        </p>
      )}

      {/* Normative Text Excerpt */}
      <div
        style={{
          backgroundColor: 'rgba(11, 17, 32, 0.75)',
          borderLeft: '3px solid var(--accent-blue)',
          padding: '0.75rem 0.9rem',
          borderRadius: '0 0.5rem 0.5rem 0',
          fontSize: '0.825rem',
          color: '#cbd5e1',
          lineHeight: 1.6,
          border: '1px solid rgba(148, 163, 184, 0.08)',
          borderLeftWidth: '3px',
          borderLeftColor: 'var(--accent-blue)'
        }}
      >
        "{source.excerpt}"
      </div>

      {/* 7-Layer Tag Pills if available */}
      {source.tags && source.tags.length > 0 && (
        <div style={{ display: 'flex', gap: '0.35rem', marginTop: '0.6rem', flexWrap: 'wrap' }}>
          {source.tags.map((tag) => (
            <span
              key={tag}
              style={{
                fontSize: '0.65rem',
                fontWeight: 600,
                color: 'var(--text-muted)',
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid var(--border-subtle)',
                padding: '0.1rem 0.4rem',
                borderRadius: '0.25rem',
                fontFamily: 'var(--font-mono)'
              }}
            >
              #{tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
