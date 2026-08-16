import { useState } from 'react';
import { Message } from '../types/chat';
import { ConfidenceBadge } from './ConfidenceBadge';
import { CitationCard } from './CitationCard';
import { AbstainView } from './AbstainView';
import { LatencyBar } from './LatencyBar';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';


interface Props {
  message: Message;
}

// Simple conversational bubble for fast-path responses
const ConversationalBubble = ({ message, type }: { message: Message; type: string }) => {
  const isDecline = type === 'decline';
  const isClarify = type === 'clarify';
  return (
    <div
      className="animate-fade-in"
      style={{
        display: 'flex',
        gap: '0.85rem',
        alignItems: 'flex-start',
        marginBottom: '2rem',
      }}
    >
      <div style={{
        width: '34px', height: '34px', borderRadius: '50%', flexShrink: 0,
        background: isDecline
          ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
          : isClarify
          ? 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)'
          : 'linear-gradient(135deg, #06b6d4 0%, #2563eb 100%)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.9rem',
      }}>
        {isDecline ? '⚠️' : isClarify ? '❓' : '💬'}
      </div>
      <div style={{
        background: isDecline ? 'rgba(245, 158, 11, 0.08)' : isClarify ? 'rgba(139, 92, 246, 0.08)' : 'rgba(6, 182, 212, 0.06)',
        border: `1px solid ${isDecline ? 'rgba(245,158,11,0.25)' : isClarify ? 'rgba(139,92,246,0.25)' : 'rgba(6,182,212,0.2)'}`,
        borderRadius: '0.25rem 0.75rem 0.75rem 0.75rem',
        padding: '0.85rem 1.1rem',
        color: 'var(--text-main)',
        fontSize: '0.925rem',
        lineHeight: 1.65,
        maxWidth: '680px',
        whiteSpace: 'pre-line',
      }}>
        {message.content}
      </div>
    </div>
  );
};

export const AnswerPanel = ({ message }: Props) => {
  const [copied, setCopied] = useState(false);

  // Fast-path messages render as simple conversational bubbles
  if (message.messageType === 'fast_reply' || message.messageType === 'clarify' || message.messageType === 'decline') {
    return <ConversationalBubble message={message} type={message.messageType} />;
  }

  const getAnswerText = (content: string) => {
    if (!content) return '';
    try {
      const parsed = JSON.parse(content);
      return parsed.answer || content;
    } catch (e) {
      const match = content.match(/"answer"\s*:\s*"([\s\S]*?)(?:",\s*"\w+"\s*:|"$)/);
      if (match && match[1]) {
        return match[1].replace(/\\n/g, '\n').replace(/\\"/g, '"').replace(/\\\\/g, '\\');
      }
      return content.includes('"answer"') ? '' : content;
    }
  };

  const copyAnswer = () => {
    const textToCopy = getAnswerText(message.content);
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="glass-panel animate-fade-in"
      style={{
        padding: '1.75rem',
        marginBottom: '2rem',
        border: '1px solid var(--border-glass)',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.4)'
      }}
    >
      {/* AI Assistant Avatar & Title Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.25rem',
        paddingBottom: '1rem',
        borderBottom: '1px solid var(--border-subtle)',
        flexWrap: 'wrap',
        gap: '0.75rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          {/* AI Avatar Circle */}
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #06b6d4 0%, #2563eb 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.1rem',
              boxShadow: '0 0 16px rgba(6, 182, 212, 0.4)',
              border: '1px solid rgba(255, 255, 255, 0.25)',
              flexShrink: 0
            }}
          >
            📡
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.02em' }}>
                3GPP Standards Intelligence
              </h2>
              <span 
                title="This answer is grounded by retrieving official 3GPP specifications from the database."
                style={{
                fontSize: '0.625rem',
                fontWeight: 700,
                color: 'var(--accent-cyan)',
                background: 'rgba(6, 182, 212, 0.12)',
                border: '1px solid rgba(6, 182, 212, 0.3)',
                padding: '0.1rem 0.4rem',
                borderRadius: '0.25rem',
                cursor: 'help',
                fontFamily: 'var(--font-mono)'
              }}>
                Grounded
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {!message.abstained && message.content && (
            <button
              type="button"
              onClick={copyAnswer}
              disabled={message.isStreaming}
              style={{
                background: copied ? 'rgba(16, 185, 129, 0.2)' : 'rgba(15, 23, 42, 0.6)',
                border: copied ? '1px solid var(--accent-emerald)' : '1px solid var(--border-glass)',
                color: copied ? 'var(--accent-emerald)' : 'var(--text-muted)',
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '0.35rem 0.7rem',
                borderRadius: '0.375rem',
                cursor: message.isStreaming ? 'not-allowed' : 'pointer',
                opacity: message.isStreaming ? 0.5 : 1,
                transition: 'all 0.15s ease'
              }}
            >
              {copied ? '✓ Copied' : '📄 Copy Response'}
            </button>
          )}
          {message.confidence && <ConfidenceBadge confidence={message.confidence} />}
        </div>
      </div>

      {message.abstained ? (
        <AbstainView reason={message.error || "Insufficient evidence to answer the query"} />
      ) : (
        <div>
          {/* Main Grounded Answer Text */}
          <div
            className="markdown-body"
            style={{
              fontSize: '0.95rem',
              color: 'var(--text-main)',
              lineHeight: 1.75,
              backgroundColor: 'rgba(11, 17, 32, 0.85)',
              border: '1px solid var(--border-glass)',
              padding: '1.35rem',
              borderRadius: '0.75rem',
              marginBottom: '1.5rem',
              boxShadow: 'inset 0 2px 4px rgba(0, 0, 0, 0.2)'
            }}
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({node, ...props}) => <p style={{ marginBottom: '1rem', marginTop: 0 }} {...props} />,
                ul: ({node, ...props}) => <ul style={{ marginBottom: '1rem', paddingLeft: '1.5rem', listStyleType: 'disc' }} {...props} />,
                ol: ({node, ...props}) => <ol style={{ marginBottom: '1rem', paddingLeft: '1.5rem', listStyleType: 'decimal' }} {...props} />,
                li: ({node, ...props}) => <li style={{ marginBottom: '0.5rem' }} {...props} />,
                h3: ({node, ...props}) => <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '1.5rem', marginBottom: '0.75rem', color: 'var(--text-main)' }} {...props} />,
                h4: ({node, ...props}) => <h4 style={{ fontSize: '1rem', fontWeight: 600, marginTop: '1.25rem', marginBottom: '0.75rem', color: 'var(--text-main)' }} {...props} />,
                pre: ({node, ...props}) => (
                  <pre style={{ display: 'block', backgroundColor: 'rgba(15, 23, 42, 0.8)', padding: '1rem', borderRadius: '0.5rem', overflowX: 'auto', border: '1px solid var(--border-glass)', margin: '1rem 0' }} {...props} />
                ),
                code: ({node, className, children, ...props}: any) => {
                  const isBlock = String(children).includes('\n') || className?.includes('language-');
                  if (isBlock) {
                    return <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85em', color: '#e2e8f0' }} className={className} {...props}>{children}</code>;
                  }
                  return (
                    <code style={{ backgroundColor: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', padding: '0.15rem 0.35rem', borderRadius: '0.25rem', fontFamily: 'var(--font-mono)', fontSize: '0.85em' }} className={className} {...props}>
                      {children}
                    </code>
                  );
                },
                blockquote: ({node, ...props}) => (
                  <blockquote style={{
                    borderLeft: '4px solid var(--accent-cyan)',
                    backgroundColor: 'rgba(6, 182, 212, 0.08)',
                    padding: '0.75rem 1rem',
                    margin: '1rem 0',
                    borderRadius: '0 0.5rem 0.5rem 0',
                    color: 'var(--text-muted)'
                  }} {...props} />
                ),
                table: ({node, ...props}) => (
                  <div style={{ overflowX: 'auto', margin: '1.5rem 0', borderRadius: '0.5rem', border: '1px solid var(--border-glass)' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }} {...props} />
                  </div>
                ),
                th: ({node, ...props}) => <th style={{ backgroundColor: 'rgba(15, 23, 42, 0.8)', padding: '0.75rem 1rem', borderBottom: '1px solid var(--border-glass)', fontWeight: 600, color: 'var(--text-main)' }} {...props} />,
                td: ({node, ...props}) => <td style={{ padding: '0.75rem 1rem', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }} {...props} />
              }}
            >
              {(() => {
                let answerText = getAnswerText(message.content);
                if (message.isStreaming) {
                  answerText += ' \u258C';
                }
                return answerText;
              })()}
            </ReactMarkdown>
          </div>

          {/* Citations List */}
          {message.citations && message.citations.length > 0 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.85rem' }}>
                <span style={{ fontSize: '1rem' }}>📚</span>
                <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-main)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Verified 3GPP Specification Citations ({message.citations.length})
                </h3>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {message.citations.map((src: any, i: number) => (
                  <CitationCard key={src.chunk_id} source={src} index={i} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {message.metadata && <LatencyBar totalMs={message.metadata.total_ms} debug={undefined} />}
    </div>
  );
};
