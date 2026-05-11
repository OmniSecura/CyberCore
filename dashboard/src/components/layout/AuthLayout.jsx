const SHIELD = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>

const LANG_LABELS = { en: 'English', pl: 'Polski' }

export function AuthLayout({ lang, setLang, children }) {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="logo">
          <div className="mark">{SHIELD}</div>
          <div className="word">Cyber<em>Core</em></div>
        </div>
        <div className="meta">
          <select
            className="lang-select"
            value={lang}
            onChange={e => setLang(e.target.value)}
            aria-label="Language"
          >
            {Object.entries(LANG_LABELS).map(([code, label]) => (
              <option key={code} value={code}>{label}</option>
            ))}
          </select>
        </div>
      </header>
      <div className="center-area">{children}</div>
      <footer className="foot">
        <div className="left"><span className="dot" /><span>All systems operational</span></div>
        <div>
          <a href="#">Docs</a>
          &nbsp;·&nbsp;
          <a href="#">GitHub</a>
          &nbsp;·&nbsp;
          <span>v0.4 · self-hosted</span>
        </div>
      </footer>
    </div>
  )
}
