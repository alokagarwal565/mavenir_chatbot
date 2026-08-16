import { useState, useEffect, useRef } from 'react';
import { QueryInput } from './components/QueryInput';
import { AnswerPanel } from './components/AnswerPanel';
import { ThinkingIndicator } from './components/ThinkingIndicator';
import { UserMessageBubble } from './components/UserMessageBubble';
import { StreamStatusBar } from './components/StreamStatusBar';
import { checkHealth, getDocuments } from './api/client';
import { Message, ConversationHistory, StreamCallbacks } from './types/chat';
import { useStreamingQuery } from './hooks/useStreamingQuery';

const DOMAIN_STARTERS = [
  {
    icon: '🏗️',
    title: '5GS Architecture & Flows',
    desc: 'TS 23.501 & TS 23.502 Registration, PDU Session & Slicing',
    prompt: 'How does AMF handle Registration Request procedures per TS 23.502?'
  },
  {
    icon: '📱',
    title: 'NAS Signaling & URSP',
    desc: 'TS 24.501 & TS 24.526 5GMM/5GSM states & Route Selection',
    prompt: 'What is the default value of periodic registration timer T3512 in TS 24.501?'
  },
  {
    icon: '🛡️',
    title: 'Security & 5G-AKA',
    desc: 'TS 33.501 & TS 33.535 SUCI de-concealment, AUSF & AKMA',
    prompt: 'Explain 5G-AKA primary authentication and SUCI concealing per TS 33.501'
  },
  {
    icon: '🌐',
    title: 'Service Based APIs',
    desc: 'TS 29.500 & TS 29.518 Namf, Nsmf, Nudm REST HTTP/2 JSON',
    prompt: 'What HTTP status codes are returned by Namf_Communication in TS 29.518?'
  }
];

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamStatus, setStreamStatus] = useState<string | null>(null);
  
  const [backendHealth, setBackendHealth] = useState<string>('Checking...');
  const [, setDocuments] = useState<any[]>([]);
  const [selectedRelease, setSelectedRelease] = useState<number | null>(18);
  const chatBottomRef = useRef<HTMLDivElement>(null);
  
  const abortControllerRef = useRef<AbortController | null>(null);
  const { streamQuery } = useStreamingQuery();

  useEffect(() => {
    checkHealth()
      .then((h) => setBackendHealth(h.status === 'ok' ? '5GS Core Active' : 'Degraded'))
      .catch(() => setBackendHealth('Standby (Connecting...)'));

    getDocuments()
      .then((docs) => setDocuments(docs))
      .catch(() => {});
      
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming, streamStatus]);

  const handleSearch = async (question: string, specFilter: string | null) => {
    if (!question.trim() || isStreaming) return;
    
    // Cancel any existing request (though button should be disabled)
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();

    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;

    const userMessage: Message = {
      id: userMsgId,
      role: 'user',
      content: question.trim(),
      specFilter: specFilter === 'ALL' ? null : specFilter,
      releaseFilter: selectedRelease,
    };

    const assistantMessage: Message = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      isStreaming: true,
    };

    // Calculate history to send (latest completed messages)
    const history: ConversationHistory[] = messages
      .filter(m => !m.isStreaming && !m.error)
      .map(m => {
        let content = m.content;
        if (m.role === 'assistant') {
          try {
            const parsed = JSON.parse(m.content);
            content = parsed.answer || m.content;
          } catch (e) {
            const match = m.content.match(/"answer"\s*:\s*"([\s\S]*?)(?:",\s*"\w+"\s*:|"$)/);
            if (match && match[1]) {
              content = match[1].replace(/\\n/g, '\n').replace(/\\"/g, '"').replace(/\\\\/g, '\\');
            }
          }
        }
        return { role: m.role, content };
      })
      .slice(-12);

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setIsStreaming(true);
    setStreamStatus('Connecting to 3GPP Knowledge Base...');

    const callbacks: StreamCallbacks = {
      onStatus: (_stage, message) => {
        setStreamStatus(message);
      },
      onToken: (text) => {
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMsgId ? { ...msg, content: msg.content + text } : msg
        ));
      },
      onCitations: (claims, citations, confidence, abstained) => {
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMsgId ? { ...msg, claims, citations, confidence, abstained } : msg
        ));
      },
      onMetadata: (metadata) => {
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMsgId ? { ...msg, metadata } : msg
        ));
      },
      onAbstain: (reason, confidence) => {
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMsgId ? { ...msg, error: reason, confidence, abstained: true } : msg
        ));
      },
      onFastReply: (message) => {
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMsgId ? { ...msg, content: message, messageType: 'fast_reply' } : msg
        ));
      },
      onDecline: (message) => {
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMsgId ? { ...msg, content: message, messageType: 'decline' } : msg
        ));
      },
      onClarify: (message) => {
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMsgId ? { ...msg, content: message, messageType: 'clarify' } : msg
        ));
      },
      onError: (message) => {
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMsgId ? { ...msg, error: message, isStreaming: false } : msg
        ));
      },
      onDone: () => {
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMsgId ? { ...msg, isStreaming: false } : msg
        ));
        setIsStreaming(false);
        setStreamStatus(null);
        abortControllerRef.current = null;
      }
    };

    streamQuery(
      question.trim(),
      history,
      specFilter === 'ALL' ? undefined : specFilter || undefined,
      selectedRelease || 18,
      callbacks,
      abortControllerRef.current.signal
    );
  };

  const handleClearChat = () => {
    abortControllerRef.current?.abort();
    setMessages([]);
    setIsStreaming(false);
    setStreamStatus(null);
  };

  return (
    <div style={{ minHeight: '100vh', padding: '0 1.5rem 190px 1.5rem', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Sleek Unified Sticky Navigation Bar */}
      <header
        className="glass-panel"
        style={{
          position: 'sticky',
          top: '1rem',
          zIndex: 40,
          padding: '0.75rem 1.5rem',
          margin: '1rem 0 2rem 0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          backdropFilter: 'blur(20px)',
          border: '1px solid var(--border-glass)',
          boxShadow: '0 8px 30px rgba(0,0,0,0.5)'
        }}
      >
        {/* Brand & Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '0.5rem',
              background: 'linear-gradient(135deg, #2563eb 0%, #06b6d4 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.2rem',
              boxShadow: '0 4px 12px rgba(37, 99, 235, 0.35)',
              flexShrink: 0
            }}
          >
            📡
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h1 style={{
                fontSize: '1.15rem',
                fontWeight: 800,
                letterSpacing: '-0.02em',
                background: 'linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}>
                3GPP Standards Intelligence
              </h1>
              <span style={{
                fontSize: '0.625rem',
                fontWeight: 700,
                color: 'var(--accent-cyan)',
                background: 'rgba(6, 182, 212, 0.12)',
                border: '1px solid rgba(6, 182, 212, 0.3)',
                padding: '0.1rem 0.35rem',
                borderRadius: '0.25rem',
                fontFamily: 'var(--font-mono)'
              }}>
                v2.3 Core 5GS
              </span>
            </div>
          </div>
        </div>

        {/* Status Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>

          {messages.length > 0 && (
            <button
              type="button"
              onClick={handleClearChat}
              title="Clear conversation session"
              style={{
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#fca5a5',
                fontSize: '0.725rem',
                fontWeight: 600,
                padding: '0.35rem 0.65rem',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              🗑️ New Chat
            </button>
          )}

          {/* Live Status Capsule */}
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
              border: '1px solid var(--border-glass)'
            }}
          >
            <div
              className="pulse-dot"
              style={{
                backgroundColor: backendHealth.includes('Active') ? 'var(--accent-emerald)' : 'var(--accent-amber)'
              }}
            />
            <span style={{ color: backendHealth.includes('Active') ? '#6ee7b7' : '#fcd34d' }}>
              {backendHealth}
            </span>
          </div>
        </div>
      </header>

      {/* Main Conversational Workspace */}
      <main>
        {/* Welcome Hero State when no messages yet */}
        {messages.length === 0 && (
          <div className="animate-fade-in" style={{ marginTop: '3rem' }}>
            <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
              <h2 style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.03em', marginBottom: '0.6rem' }}>
                Ask Anything Across 3GPP 5G Standards
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', maxWidth: '680px', margin: '0 auto', lineHeight: 1.6 }}>
                Deterministic citation validation, exact clause breadcrumbs, parameter tables, and reconstructed call flow sequence diagrams.
              </p>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: '1.25rem',
              maxWidth: '1100px',
              margin: '0 auto'
            }}>
              {DOMAIN_STARTERS.map((card, idx) => (
                <div
                  key={idx}
                  onClick={() => handleSearch(card.prompt, null)}
                  className="glass-card"
                  style={{
                    padding: '1.5rem',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    minHeight: '150px'
                  }}
                >
                  <div>
                    <div style={{ fontSize: '1.75rem', marginBottom: '0.65rem' }}>{card.icon}</div>
                    <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.4rem' }}>
                      {card.title}
                    </h3>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                      {card.desc}
                    </p>
                  </div>
                  <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--accent-cyan)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <span>Query Domain</span>
                    <span>→</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Chronological Chat Stream Feed */}
        {messages.map((msg, index) => {
          if (msg.role === 'user') {
            return (
              <UserMessageBubble
                key={msg.id}
                question={msg.content}
                timestamp={new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                specFilter={msg.specFilter}
                releaseFilter={msg.releaseFilter ?? selectedRelease}
              />
            );
          }

          const isLastMessage = index === messages.length - 1;

          if (msg.error && !msg.content) {
            return (
              <div
                key={msg.id}
                className="animate-fade-in"
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.85rem',
                  marginBottom: '2rem',
                  width: '100%'
                }}
              >
                <div
                  style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.1rem',
                    boxShadow: '0 0 16px rgba(239, 68, 68, 0.4)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    flexShrink: 0
                  }}
                >
                  ⚠️
                </div>

                <div
                  className="glass-panel"
                  style={{
                    flex: 1,
                    backgroundColor: 'rgba(239, 68, 68, 0.12)',
                    border: '1px solid var(--accent-rose)',
                    borderRadius: '0.25rem 1rem 1rem 1rem',
                    padding: '1.25rem 1.5rem',
                    boxShadow: '0 8px 24px rgba(239, 68, 68, 0.15)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
                    <strong style={{ color: '#fff', fontSize: '0.95rem' }}>Unable to Answer</strong>
                  </div>
                  <p style={{ color: '#fecdd3', fontSize: '0.9rem', lineHeight: 1.5, marginBottom: '0.5rem' }}>
                    {msg.error}
                  </p>
                  {msg.error.includes('Failed to fetch') && (
                    <div style={{
                      fontSize: '0.75rem',
                      color: '#fca5a5',
                      background: 'rgba(15, 23, 42, 0.6)',
                      padding: '0.5rem 0.75rem',
                      borderRadius: '0.35rem',
                      border: '1px solid rgba(239, 68, 68, 0.25)',
                      fontFamily: 'var(--font-mono)'
                    }}>
                      💡 Tip: Ensure the FastAPI backend server is running on port 7860
                    </div>
                  )}
                </div>
              </div>
            );
          }

          return (
            <div key={msg.id} style={{ marginBottom: '2rem' }}>
              {isLastMessage && msg.isStreaming && !msg.content && (
                <ThinkingIndicator />
              )}
              {isLastMessage && (isStreaming || streamStatus) && msg.content && (
                <StreamStatusBar status={streamStatus} isStreaming={isStreaming} />
              )}
              {/* Only show panel if we have some content or it's done initializing */}
              {(msg.content || !msg.isStreaming) && (
                <AnswerPanel message={msg} />
              )}
            </div>
          );
        })}

        <div ref={chatBottomRef} />
      </main>

      {/* Fixed Bottom Query Console Dock */}
      <div
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          background: 'linear-gradient(180deg, rgba(5, 8, 17, 0) 0%, rgba(5, 8, 17, 0.85) 15%, #050811 100%)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderTop: '1px solid var(--border-glass)',
          padding: '1rem 1.5rem 1.25rem 1.5rem',
          zIndex: 50,
          boxShadow: '0 -15px 35px rgba(0, 0, 0, 0.7)'
        }}
      >
        <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
          <QueryInput
            onSearch={handleSearch}
            isLoading={isStreaming}
            selectedRelease={selectedRelease}
            onSelectRelease={(rel) => setSelectedRelease(rel)}
          />
        </div>
      </div>
    </div>
  );
}
