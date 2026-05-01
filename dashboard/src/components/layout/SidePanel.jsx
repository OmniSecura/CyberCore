export function SidePanel({ lang, setLang }) {
  return (
    <div className="side">
      <div className="side-grid" />
      <div className="side-top">
        <div className="logo">
          <div className="logo-mark">
            <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <div className="logo-text">Cyber<span>Core</span></div>
        </div>

        <div className="lang-switcher">
          {['en', 'pl'].map(l => (
            <button key={l} className={`lang-btn${lang === l ? ' active' : ''}`} onClick={() => setLang(l)}>
              {l.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="side-headline">
          Unified Security<br /><em>Intelligence</em><br />Platform
        </div>
        <div className="side-desc">
          Monitor, scan, and respond to threats across your entire infrastructure in real time.
        </div>
      </div>

      <div className="side-features">
        {[
          { label: 'SAST & DAST Scanning',    icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg> },
          { label: 'Real-time Log Monitoring', icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg> },
          { label: 'Anomaly Detection (ML)',   icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> },
        ].map(f => (
          <div key={f.label} className="feat">
            <div className="feat-icon">{f.icon}</div>
            <div className="feat-label">{f.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
