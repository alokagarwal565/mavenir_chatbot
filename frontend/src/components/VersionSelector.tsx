interface VersionSelectorProps {
  selectedRelease: number | null;
  onSelectRelease: (rel: number | null) => void;
}

export const VersionSelector = ({
  selectedRelease,
  onSelectRelease,
}: VersionSelectorProps) => {
  const releases = [
    { label: 'All Releases', value: null, badge: '5GS' },
    { label: 'Rel-18', value: 18, badge: '5G-Adv' },
  ];

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
      
      <div className="segmented-control">
        {releases.map((r) => {
          const isActive = selectedRelease === r.value;
          return (
            <button
              key={r.label}
              type="button"
              onClick={() => onSelectRelease(r.value)}
              className={`segmented-btn ${isActive ? 'active' : ''}`}
            >
              <span>{r.label}</span>
              <span style={{
                marginLeft: '0.35rem',
                fontSize: '0.65rem',
                padding: '0.1rem 0.35rem',
                borderRadius: '0.25rem',
                background: isActive ? 'rgba(255,255,255,0.2)' : 'rgba(148, 163, 184, 0.15)',
                color: isActive ? '#ffffff' : 'var(--text-muted)'
              }}>
                {r.badge}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
