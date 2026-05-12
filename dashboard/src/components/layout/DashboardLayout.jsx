export function DashboardLayout({ user, onLogout, activeNav, onNavigate, children }) {
  const initials = user?.display_name
    ? user.display_name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
    : user?.email?.[0]?.toUpperCase() ?? '?'

  const navItems = [
    {
      id: 'orgs',
      label: 'Organizations',
      icon: (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="1" y="4" width="14" height="11" rx="2"/>
          <path d="M5 4V3a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v1"/>
          <path d="M8 9v2M5 9v2M11 9v2"/>
        </svg>
      ),
    },
    {
      id: 'agents',
      label: 'Agents',
      disabled: true,
      icon: (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="8" cy="8" r="6"/>
          <path d="M8 5v3l2 2"/>
        </svg>
      ),
    },
    {
      id: 'alerts',
      label: 'Alerts',
      disabled: true,
      icon: (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M8 2l1.5 4.5H14l-3.5 2.5 1.5 4.5L8 11l-4 2.5 1.5-4.5L2 6.5h4.5Z"/>
        </svg>
      ),
    },
    {
      id: 'logs',
      label: 'Logs',
      disabled: true,
      icon: (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 4h10M3 8h7M3 12h5"/>
        </svg>
      ),
    },
  ]

  return (
    <div className="dash-shell">
      <aside className="dash-sidebar">
        <div className="sidebar-logo">
          <div className="mark">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2l7 4v6c0 5-3.5 8.5-7 10-3.5-1.5-7-5-7-10V6l7-4z"/>
            </svg>
          </div>
          <span className="word">Cyber<em>Core</em></span>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section-label">Platform</div>
          {navItems.map(item => (
            <button
              key={item.id}
              className={`nav-item${activeNav === item.id ? ' active' : ''}`}
              onClick={() => !item.disabled && onNavigate(item.id)}
              disabled={item.disabled}
              style={item.disabled ? { cursor: 'default' } : undefined}
            >
              {item.icon}
              {item.label}
              {item.disabled && <span className="soon-badge">Soon</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-row">
            <div className="user-avatar">{initials}</div>
            <div className="user-info">
              <div className="user-name">{user?.display_name || 'User'}</div>
              <div className="user-email">{user?.email}</div>
            </div>
            <button className="logout-btn" onClick={onLogout} title="Log out">
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10 11l3-3-3-3M13 8H6M6 3H3a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h3"/>
              </svg>
            </button>
          </div>
        </div>
      </aside>

      <main className="dash-main">
        <div className="dash-content">
          {children}
        </div>
      </main>
    </div>
  )
}
