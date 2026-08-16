import React, { useEffect, useRef } from 'react';

interface MermaidViewerProps {
  syntax: string;
  title?: string;
  figureNumber?: string;
}

export const MermaidViewer: React.FC<MermaidViewerProps> = ({
  syntax,
  title,
  figureNumber,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let isMounted = true;

    const renderDiagram = async () => {
      if (!containerRef.current || !syntax) return;

      try {
        // Load mermaid dynamically if available on window or display formatted sequence AST
        const win = window as any;
        if (win.mermaid) {
          const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
          const { svg } = await win.mermaid.render(id, syntax);
          if (isMounted && containerRef.current) {
            containerRef.current.innerHTML = svg;
          }
        } else {
          // If mermaid script not loaded, render clean formatted diagram box
          if (isMounted && containerRef.current) {
            containerRef.current.innerHTML = `
              <div style="font-family: monospace; font-size: 0.8rem; background: #0b132b; color: #60a5fa; padding: 1rem; border-radius: 0.5rem; border: 1px solid #1e3a8a; white-space: pre-wrap;">
                ${syntax.replace(/</g, '&lt;').replace(/>/g, '&gt;')}
              </div>
            `;
          }
        }
      } catch (err) {
        if (isMounted && containerRef.current) {
          containerRef.current.innerHTML = `
            <div style="font-family: monospace; font-size: 0.75rem; color: #fbbf24; background: #1e293b; padding: 0.75rem; border-radius: 0.375rem;">
              ${syntax.replace(/</g, '&lt;').replace(/>/g, '&gt;')}
            </div>
          `;
        }
      }
    };

    renderDiagram();

    return () => {
      isMounted = false;
    };
  }, [syntax]);

  return (
    <div
      style={{
        margin: '0.75rem 0',
        padding: '1rem',
        borderRadius: '0.5rem',
        backgroundColor: 'var(--bg-panel)',
        border: '1px solid var(--border)',
      }}
    >
      {(figureNumber || title) && (
        <div style={{ marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-blue)' }}>
            {figureNumber || 'Call Flow Diagram'}
          </span>
          {title && <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{title}</span>}
        </div>
      )}
      <div ref={containerRef} style={{ overflowX: 'auto' }} />
    </div>
  );
};
