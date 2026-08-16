import { useState, useRef, useEffect } from 'react';

export interface Option {
  value: string;
  label: string;
  description?: string;
  minRelease?: number;
}

interface Props {
  options: Option[];
  value: string;
  onChange: (value: string) => void;
  direction?: 'up' | 'down';
  selectedRelease?: number | null;
}

export const CustomDropdown = ({
  options,
  value,
  onChange,
  direction = 'up',
  selectedRelease = null,
}: Props) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const selectedOption = options.find((o) => o.value === value) || options[0];

  // Auto-focus search input on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 50);
    } else {
      setSearchTerm('');
    }
  }, [isOpen]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getSeriesColor = (val: string) => {
    if (val.includes('23.')) return { bg: 'rgba(59, 130, 246, 0.15)', text: '#60a5fa', border: 'rgba(59, 130, 246, 0.3)' };
    if (val.includes('24.')) return { bg: 'rgba(6, 182, 212, 0.15)', text: '#22d3ee', border: 'rgba(6, 182, 212, 0.3)' };
    if (val.includes('38.')) return { bg: 'rgba(139, 92, 246, 0.15)', text: '#c084fc', border: 'rgba(139, 92, 246, 0.3)' };
    if (val.includes('33.')) return { bg: 'rgba(239, 68, 68, 0.15)', text: '#f87171', border: 'rgba(239, 68, 68, 0.3)' };
    if (val.includes('29.')) return { bg: 'rgba(16, 185, 129, 0.15)', text: '#34d399', border: 'rgba(16, 185, 129, 0.3)' };
    return { bg: 'rgba(148, 163, 184, 0.15)', text: '#cbd5e1', border: 'rgba(148, 163, 184, 0.25)' };
  };

  const filteredOptions = options.filter((opt) => {
    // If selectedRelease is strictly lower than the specification's inaugural release, filter out
    if (selectedRelease && opt.minRelease && selectedRelease < opt.minRelease) {
      return false;
    }
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      opt.label.toLowerCase().includes(term) ||
      opt.value.toLowerCase().includes(term) ||
      (opt.description && opt.description.toLowerCase().includes(term))
    );
  });

  return (
    <div ref={dropdownRef} style={{ position: 'relative', minWidth: '240px' }}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '100%',
          height: '100%',
          padding: '0.75rem 1rem',
          backgroundColor: 'rgba(15, 23, 42, 0.95)',
          border: isOpen ? '1px solid var(--border-glow)' : '1px solid var(--border-glass)',
          borderRadius: '0.625rem',
          color: 'var(--text-main)',
          fontSize: '0.85rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
          boxShadow: isOpen ? '0 0 16px rgba(59, 130, 246, 0.25)' : 'var(--shadow-sm)',
          transition: 'all 0.2s ease',
          outline: 'none',
          backdropFilter: 'blur(12px)',
          fontFamily: 'var(--font-sans)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', overflow: 'hidden' }}>
          <span style={{
            fontSize: '0.65rem',
            fontWeight: 700,
            padding: '0.15rem 0.45rem',
            borderRadius: '0.35rem',
            background: getSeriesColor(selectedOption.value).bg,
            color: getSeriesColor(selectedOption.value).text,
            border: `1px solid ${getSeriesColor(selectedOption.value).border}`
          }}>
            {selectedOption.value === 'ALL' ? 'CORE' : selectedOption.value.replace('TS ', '')}
          </span>
          <span style={{ fontWeight: 600, color: 'var(--text-main)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {selectedOption.label}
          </span>
        </div>

        <svg
          style={{
            width: '14px',
            height: '14px',
            transform: direction === 'up' 
              ? (isOpen ? 'rotate(180deg)' : 'rotate(0deg)')
              : (isOpen ? 'rotate(180deg)' : 'rotate(0deg)'),
            transition: 'transform 0.2s ease',
            color: 'var(--text-muted)',
            flexShrink: 0,
            marginLeft: '0.5rem'
          }}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          {direction === 'up' ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 15l7-7 7 7" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
          )}
        </svg>
      </button>

      {isOpen && (
        <div
          className="animate-fade-in"
          style={{
            position: 'absolute',
            ...(direction === 'up'
              ? { bottom: 'calc(100% + 8px)', top: 'auto' }
              : { top: 'calc(100% + 8px)', bottom: 'auto' }),
            left: 0,
            minWidth: '350px',
            backgroundColor: 'rgba(11, 17, 32, 0.98)',
            border: '1px solid var(--border-glow)',
            borderRadius: '0.75rem',
            boxShadow: '0 -20px 40px -8px rgba(0, 0, 0, 0.8), 0 0 24px rgba(59, 130, 246, 0.25)',
            zIndex: 1000,
            backdropFilter: 'blur(24px)',
            padding: '0.5rem',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          {/* Search / Filter Input Bar inside dropdown */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: 'rgba(15, 23, 42, 0.9)',
            border: '1px solid var(--border-glass)',
            borderRadius: '0.5rem',
            padding: '0.4rem 0.65rem',
            marginBottom: '0.4rem',
            gap: '0.4rem'
          }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>🔍</span>
            <input
              ref={searchInputRef}
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && filteredOptions.length > 0) {
                  onChange(filteredOptions[0].value);
                  setIsOpen(false);
                }
              }}
              placeholder="Filter specs (e.g. 29.518, NAS, security)..."
              style={{
                width: '100%',
                background: 'transparent',
                border: 'none',
                color: 'var(--text-main)',
                fontSize: '0.8rem',
                outline: 'none',
                fontFamily: 'var(--font-sans)'
              }}
            />
            {searchTerm && (
              <button
                type="button"
                onClick={() => setSearchTerm('')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-dim)',
                  cursor: 'pointer',
                  fontSize: '0.75rem'
                }}
              >
                ✕
              </button>
            )}
          </div>

          {/* Release active info badge */}
          {selectedRelease && (
            <div style={{
              fontSize: '0.625rem',
              color: 'var(--accent-cyan)',
              padding: '0.2rem 0.5rem',
              marginBottom: '0.35rem',
              fontFamily: 'var(--font-mono)',
              background: 'rgba(6, 182, 212, 0.08)',
              borderRadius: '0.25rem',
              border: '1px solid rgba(6, 182, 212, 0.2)'
            }}>
              Showing specs applicable to Rel-{selectedRelease}
            </div>
          )}

          {/* Scrollable list */}
          <div
            className="custom-scrollbar"
            style={{
              maxHeight: '280px',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.15rem'
            }}
          >
            {filteredOptions.length === 0 ? (
              <div style={{
                padding: '1.5rem',
                textAlign: 'center',
                color: 'var(--text-dim)',
                fontSize: '0.8rem'
              }}>
                No specifications match "{searchTerm}" in Rel-{selectedRelease || 'All'}
              </div>
            ) : (
              filteredOptions.map((opt) => {
                const isSelected = opt.value === value;
                const colors = getSeriesColor(opt.value);
                return (
                  <div
                    key={opt.value}
                    onClick={() => {
                      onChange(opt.value);
                      setIsOpen(false);
                    }}
                    style={{
                      padding: '0.55rem 0.75rem',
                      cursor: 'pointer',
                      borderRadius: '0.45rem',
                      backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.25)' : 'transparent',
                      color: isSelected ? '#ffffff' : 'var(--text-main)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      transition: 'all 0.15s ease',
                      gap: '0.75rem'
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.backgroundColor = 'rgba(30, 41, 59, 0.85)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.backgroundColor = 'transparent';
                      }
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexShrink: 0 }}>
                      <span style={{
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        padding: '0.15rem 0.4rem',
                        borderRadius: '0.3rem',
                        background: colors.bg,
                        color: colors.text,
                        border: `1px solid ${colors.border}`,
                        minWidth: '46px',
                        textAlign: 'center'
                      }}>
                        {opt.value === 'ALL' ? 'CORE' : opt.value.replace('TS ', '')}
                      </span>
                      <span style={{ fontSize: '0.85rem', fontWeight: isSelected ? 700 : 500 }}>
                        {opt.label}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', minWidth: 0, flex: 1, justifyContent: 'flex-end' }}>
                      {opt.minRelease && opt.minRelease > 15 && (
                        <span style={{
                          fontSize: '0.6rem',
                          padding: '0.1rem 0.3rem',
                          borderRadius: '0.2rem',
                          background: 'rgba(99, 102, 241, 0.15)',
                          color: '#a5b4fc',
                          border: '1px solid rgba(99, 102, 241, 0.3)',
                          fontFamily: 'var(--font-mono)'
                        }}>
                          Rel-{opt.minRelease}+
                        </span>
                      )}
                      {opt.description && (
                        <span style={{
                          fontSize: '0.72rem',
                          color: isSelected ? '#93c5fd' : 'var(--text-dim)',
                          textAlign: 'right',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis'
                        }}>
                          {opt.description}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};
