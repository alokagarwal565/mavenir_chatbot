import { useState, useEffect, useRef } from 'react';
import { CustomDropdown, Option } from './CustomDropdown';
import { VersionSelector } from './VersionSelector';

interface Props {
  onSearch: (question: string, specFilter: string | null) => void;
  isLoading: boolean;
  initialQuery?: string;
  selectedRelease?: number | null;
  onSelectRelease?: (rel: number | null) => void;
}

const SPEC_OPTIONS: Option[] = [
  { value: 'ALL', label: 'All Core 5GS Specs', description: 'Complete 5G Suite (Rel-18)', minRelease: 18 },
  
  // Series 23: Architecture & Procedures
  { value: 'TS 23.501', label: 'TS 23.501', description: '5GS System Architecture', minRelease: 18 },
  { value: 'TS 23.502', label: 'TS 23.502', description: '5GS Procedures & Flows', minRelease: 18 },
  { value: 'TS 23.503', label: 'TS 23.503', description: 'Policy & QoS Framework', minRelease: 18 },
  { value: 'TS 23.548', label: 'TS 23.548', description: '5GS Edge Computing', minRelease: 18 },
  { value: 'TS 23.558', label: 'TS 23.558', description: 'Edge App Enablement', minRelease: 18 },

  // Series 24: Non-Access Stratum
  { value: 'TS 24.501', label: 'TS 24.501', description: '5GMM & 5GSM NAS Protocol', minRelease: 18 },
  { value: 'TS 24.502', label: 'TS 24.502', description: 'Non-3GPP Access to 5GC', minRelease: 18 },
  { value: 'TS 24.526', label: 'TS 24.526', description: 'URSP Rules & Policy', minRelease: 18 },

  // Series 38: 5G NR Radio
  { value: 'TS 38.300', label: 'TS 38.300', description: 'NR Overall Description', minRelease: 18 },
  { value: 'TS 38.331', label: 'TS 38.331', description: 'NR RRC Protocol', minRelease: 18 },
  { value: 'TS 38.401', label: 'TS 38.401', description: 'NG-RAN Architecture', minRelease: 18 },

  // Series 29: Service-Based Interfaces (SBI)
  { value: 'TS 29.502', label: 'TS 29.502', description: 'Nsmf SMF Services', minRelease: 18 },
  { value: 'TS 29.503', label: 'TS 29.503', description: 'Nudm UDM Services', minRelease: 18 },
  { value: 'TS 29.510', label: 'TS 29.510', description: 'Nnrf NRF Services', minRelease: 18 },
  { value: 'TS 29.518', label: 'TS 29.518', description: 'Namf AMF Services', minRelease: 18 },
  { value: 'TS 29.571', label: 'TS 29.571', description: 'Common Data Types', minRelease: 18 },
];

const SAMPLE_QUERIES = [
  { icon: '⚙️', text: 'What is the structure of the 5G GUTI defined in TS 23.501?' },
  { icon: '🔐', text: 'What HTTP status codes are returned by Namf_Communication in TS 29.518?' },
  { icon: '⏱️', text: 'What is the default value of periodic registration timer T3512 in TS 24.501?' },
  { icon: '📡', text: 'How does NRF service discovery work per TS 29.510?' },
  { icon: '🌐', text: 'Explain PDU Session Establishment flow per TS 23.502 and TS 29.502' },
];

export const QueryInput = ({ onSearch, isLoading, initialQuery = '', selectedRelease = null, onSelectRelease }: Props) => {
  const [query, setQuery] = useState(initialQuery);
  const [specFilter, setSpecFilter] = useState<string>('ALL');
  const [isFocused, setIsFocused] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-reset spec filter if the selected spec is not applicable in the chosen release
  useEffect(() => {
    if (selectedRelease && specFilter !== 'ALL') {
      const specOpt = SPEC_OPTIONS.find((s) => s.value === specFilter);
      if (specOpt && specOpt.minRelease && selectedRelease < specOpt.minRelease) {
        setSpecFilter('ALL');
      }
    }
  }, [selectedRelease, specFilter]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      setIsSending(true);
      onSearch(query.trim(), specFilter === 'ALL' ? null : specFilter);
      setQuery('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
      setTimeout(() => setIsSending(false), 200);
    }
  };

  return (
    <div style={{ width: '100%' }}>
      {/* Quick Suggested Prompt Chips */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.45rem',
        marginBottom: '0.75rem',
        overflowX: 'auto',
        paddingBottom: '0.25rem'
      }}>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', whiteSpace: 'nowrap' }}>
          Suggested:
        </span>
        {SAMPLE_QUERIES.map((sq, i) => (
          <button
            key={i}
            type="button"
            onClick={() => {
              onSearch(sq.text, specFilter === 'ALL' ? null : specFilter);
            }}
            style={{
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '9999px',
              padding: '0.25rem 0.65rem',
              color: 'var(--text-muted)',
              fontSize: '0.725rem',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
              backdropFilter: 'blur(8px)',
              whiteSpace: 'nowrap',
              transition: 'all 0.15s ease',
              flexShrink: 0
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-glow)';
              e.currentTarget.style.color = '#ffffff';
              e.currentTarget.style.background = 'rgba(30, 41, 59, 0.95)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-subtle)';
              e.currentTarget.style.color = 'var(--text-muted)';
              e.currentTarget.style.background = 'rgba(15, 23, 42, 0.85)';
            }}
          >
            <span>{sq.icon}</span>
            <span>{sq.text.length > 40 ? `${sq.text.slice(0, 40)}...` : sq.text}</span>
          </button>
        ))}
      </div>

      {/* Main Search Bar Capsule */}
      <form
        onSubmit={handleSubmit}
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '0.65rem'
        }}
      >
        <div style={{
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: 'rgba(11, 17, 32, 0.95)',
          border: isFocused ? '1px solid var(--border-cyan-glow)' : '1px solid var(--border-glass)',
          borderRadius: '1rem',
          boxShadow: isFocused ? '0 0 20px rgba(6, 182, 212, 0.25)' : 'var(--shadow-sm)',
          transition: 'all 0.2s ease',
          padding: '0.75rem 1rem 0.5rem 1rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', width: '100%' }}>
            <span style={{ fontSize: '1.1rem', color: isFocused ? 'var(--accent-cyan)' : 'var(--text-dim)', marginRight: '0.75rem', marginTop: '0.1rem', transition: 'color 0.2s ease' }}>
              🔍
            </span>
            <textarea
              ref={textareaRef}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                e.target.style.height = '24px';
                e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
              }}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e as unknown as React.FormEvent);
                }
              }}
              placeholder="Ask a technical 3GPP question (e.g. 'How does AMF handle Registration in TS 23.502?')..."
              rows={1}
              style={{
                flex: 1,
                padding: '0',
                backgroundColor: 'transparent',
                border: 'none',
                color: 'var(--text-main)',
                fontSize: '0.95rem',
                outline: 'none',
                fontFamily: 'var(--font-sans)',
                resize: 'none',
                overflowY: 'auto',
                maxHeight: '150px',
                minHeight: '24px',
                lineHeight: '1.5'
              }}
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery('')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-dim)',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  padding: '0.25rem',
                  marginLeft: '0.5rem'
                }}
              >
                ✕
              </button>
            )}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <CustomDropdown
                options={SPEC_OPTIONS}
                value={specFilter}
                onChange={(val) => setSpecFilter(val)}
                direction="up"
                selectedRelease={selectedRelease}
              />
              {onSelectRelease && (
                <VersionSelector
                  selectedRelease={selectedRelease ?? null}
                  onSelectRelease={onSelectRelease}
                />
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: (!query.trim() || isLoading) ? 'rgba(255, 255, 255, 0.1)' : 'var(--accent-cyan)',
                color: (!query.trim() || isLoading) ? 'var(--text-muted)' : '#000',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: 'none',
                cursor: (!query.trim() || isLoading) ? 'not-allowed' : 'pointer',
                transform: isSending ? 'scale(0.92)' : 'scale(1)',
                transition: 'all 0.15s ease',
                flexShrink: 0
              }}
            >
              {isLoading ? (
                <span style={{ display: 'inline-block', width: '16px', height: '16px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
              ) : (
                <span style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>↑</span>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};
