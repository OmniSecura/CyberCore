import { useState, useEffect, useCallback } from 'react'
import { URLS, APP_VERSION } from '../config/constants'
import '../styles/overview.css'

// ─── Icon ────────────────────────────────────────────────────────────────────

const Icon = ({ name, size = 16, strokeWidth = 2, style }) => {
  const P = {
    shield:   <path d="M12 2L4 6v6c0 5 3.5 9.5 8 10 4.5-.5 8-5 8-10V6l-8-4z"/>,
    github:   <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 7.77 5.07 5.07 0 0 0 19.91 4S18.73 3.65 16 5.48a13.38 13.38 0 0 0-7 0C6.27 3.65 5.09 4 5.09 4A5.07 5.07 0 0 0 5 7.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 21.13V22"/>,
    arrow:    <><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></>,
    book:     <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></>,
    play:     <polygon points="6 4 20 12 6 20 6 4"/>,
    chevL:    <polyline points="15 18 9 12 15 6"/>,
    chevR:    <polyline points="9 18 15 12 9 6"/>,
    check:    <polyline points="20 6 9 17 4 12"/>,
    lock:     <><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></>,
    search:   <><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></>,
    code:     <><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></>,
    bug:      <><rect x="8" y="6" width="8" height="14" rx="4"/><path d="M19 7l-3 2M5 7l3 2M19 13h-3M8 13H5M19 19l-3-2M5 19l3-2M12 2v4"/></>,
    list:     <><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/></>,
    cpu:      <><rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/></>,
    bell:     <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M14 21a2 2 0 0 1-4 0"/></>,
    server:   <><rect x="2" y="3" width="20" height="8" rx="2"/><rect x="2" y="13" width="20" height="8" rx="2"/><line x1="6" y1="7" x2="6.01" y2="7"/><line x1="6" y1="17" x2="6.01" y2="17"/></>,
    zap:      <polygon points="13 2 4 14 11 14 10 22 19 10 12 10 13 2"/>,
    box:      <><path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.3 7 12 12 20.7 7"/><line x1="12" y1="22" x2="12" y2="12"/></>,
    download: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></>,
    terminal: <><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></>,
    layers:   <><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></>,
    package:  <><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.3 7 12 12 20.7 7"/><line x1="12" y1="22" x2="12" y2="12"/></>,
    cloud:    <path d="M18 10h-1.3A8 8 0 1 0 4 16.6 6 6 0 0 0 9 22h9a5 5 0 0 0 0-10z"/>,
    discord:  <path d="M20 4.5a18 18 0 0 0-4.5-1.4l-.2.4a14 14 0 0 0-4.7 0l-.2-.4A18 18 0 0 0 4 4.5C1.8 7.8 1.2 11 1.5 14a18 18 0 0 0 5.6 2.8l.4-.6a13 13 0 0 1-2-1l.5-.4a13 13 0 0 0 11 0l.5.4a13 13 0 0 1-2 1l.4.6c2-.5 4-1.4 5.6-2.8.4-3.7-.6-6.9-1.5-9.5zM8.7 12.5c-.9 0-1.6-.8-1.6-1.8s.7-1.8 1.6-1.8 1.6.8 1.6 1.8-.7 1.8-1.6 1.8zm6.6 0c-.9 0-1.6-.8-1.6-1.8s.7-1.8 1.6-1.8 1.6.8 1.6 1.8-.7 1.8-1.6 1.8z"/>,
  }
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" style={style}>
      {P[name]}
    </svg>
  )
}

// ─── Mini browser chrome (for coverflow slides) ───────────────────────────────

const MiniBrowser = ({ url, children }) => (
  <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', background: '#fff', borderRadius: 14, overflow: 'hidden' }}>
    <div style={{ height: 38, flexShrink: 0, background: '#ECF2F8', borderBottom: '1px solid #D6E4F0', display: 'flex', alignItems: 'center', gap: 10, padding: '0 14px' }}>
      <div style={{ display: 'flex', gap: 6 }}>
        <div style={{ width: 11, height: 11, borderRadius: '50%', background: '#FF5F57' }}/>
        <div style={{ width: 11, height: 11, borderRadius: '50%', background: '#FEBC2E' }}/>
        <div style={{ width: 11, height: 11, borderRadius: '50%', background: '#28C840' }}/>
      </div>
      <div style={{ flex: 1, maxWidth: 360, margin: '0 auto', height: 24, borderRadius: 999, background: '#fff', border: '1px solid #D6E4F0', display: 'flex', alignItems: 'center', gap: 7, padding: '0 12px', font: '400 11.5px/1 DM Sans', color: '#4A6080' }}>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#38A169" strokeWidth="2.4">
          <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{url}</span>
      </div>
      <div style={{ width: 60 }}/>
    </div>
    <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>{children}</div>
  </div>
)

// ─── Mockup shared helpers ────────────────────────────────────────────────────

const MkSidebarIcon = ({ name }) => {
  const paths = {
    grid:     <><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></>,
    search:   <><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></>,
    zap:      <path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"/>,
    list:     <><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></>,
    cpu:      <><rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/></>,
    bell:     <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M14 21a2 2 0 0 1-4 0"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3h.1a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8v.1a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z"/></>,
    book:     <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></>,
  }
  return <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>
}

const MkNavSection = ({ label }) => (
  <div style={{ padding: '12px 10px 4px', font: '600 9px/1 DM Sans', color: 'rgba(255,255,255,.22)', letterSpacing: '.14em', textTransform: 'uppercase' }}>{label}</div>
)
const MkNavItem = ({ icon, label, active }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '8px 10px', borderRadius: 7, font: '500 12px/1 DM Sans', background: active ? 'rgba(0,194,203,.14)' : 'transparent', color: active ? '#00C2CB' : 'rgba(255,255,255,.48)' }}>
    <MkSidebarIcon name={icon} />{label}
  </div>
)

const mkSidebar = (active) => (
  <div style={{ width: 200, background: '#0A1628', display: 'flex', flexDirection: 'column', flexShrink: 0, borderRight: '1px solid rgba(255,255,255,.05)' }}>
    <div style={{ padding: '16px 14px 14px', display: 'flex', alignItems: 'center', gap: 9, borderBottom: '1px solid rgba(255,255,255,.07)' }}>
      <div style={{ width: 26, height: 26, borderRadius: 7, background: 'linear-gradient(135deg,#00C2CB,#1A6EF5)', display: 'grid', placeItems: 'center', boxShadow: '0 4px 12px rgba(0,194,203,.3)' }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.4"><path d="M12 2L4 6v6c0 5 3.5 9.5 8 10 4.5-.5 8-5 8-10V6l-8-4z"/></svg>
      </div>
      <span style={{ font: '700 15px/1 Syne', color: '#fff', letterSpacing: '-.2px' }}>Cyber<em style={{ color: '#00C2CB', fontStyle: 'normal' }}>Core</em></span>
    </div>
    <div style={{ flex: 1, padding: 8, display: 'flex', flexDirection: 'column', gap: 1 }}>
      <MkNavSection label="Workspace" />
      <MkNavItem icon="grid" label="Organizations" active={active === 'orgs'} />
      <MkNavItem icon="search" label="Scans" active={active === 'scans'} />
      <MkNavItem icon="zap" label="Findings" active={active === 'findings'} />
      <MkNavItem icon="list" label="Logs" active={active === 'logs'} />
      <MkNavItem icon="cpu" label="Agents" active={active === 'agents'} />
      <MkNavSection label="Account" />
      <MkNavItem icon="bell" label="Alerts" />
      <MkNavItem icon="settings" label="Settings" />
      <MkNavItem icon="book" label="Manual" />
    </div>
    <div style={{ padding: '8px 8px 12px', borderTop: '1px solid rgba(255,255,255,.07)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '8px 8px' }}>
        <div style={{ width: 26, height: 26, borderRadius: '50%', background: 'linear-gradient(135deg,#00C2CB,#1A6EF5)', display: 'grid', placeItems: 'center', font: '600 10px/1 DM Sans', color: '#fff' }}>JK</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ font: '500 11.5px/1.2 DM Sans', color: 'rgba(255,255,255,.85)' }}>J. Kowalski</div>
          <div style={{ font: '400 9.5px/1.3 DM Sans', color: 'rgba(255,255,255,.28)' }}>jakub@omnisecura.io</div>
        </div>
      </div>
    </div>
  </div>
)

const mkTopbar = (crumbs) => (
  <div style={{ height: 44, display: 'flex', alignItems: 'center', gap: 10, padding: '0 22px', borderBottom: '1px solid #D6E4F0', background: '#fff' }}>
    <button style={{ width: 26, height: 26, borderRadius: 7, border: '1.5px solid #D6E4F0', background: '#fff', display: 'grid', placeItems: 'center', color: '#4A6080' }}>
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
        <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
      </svg>
    </button>
    <div style={{ font: '500 11.5px/1 DM Sans', color: '#8899AA' }}>
      {crumbs.map((c, i) => (
        <span key={i}>
          {i > 0 && <span style={{ color: '#D6E4F0', margin: '0 4px' }}>/</span>}
          <span style={{ color: i === crumbs.length - 1 ? '#0A1628' : '#8899AA' }}>{c}</span>
        </span>
      ))}
    </div>
    <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ height: 26, padding: '0 10px 0 26px', border: '1.5px solid #D6E4F0', borderRadius: 7, background: '#F4F8FC', position: 'relative', display: 'flex', alignItems: 'center', font: '400 11px/1 DM Sans', color: '#8899AA', width: 180 }}>
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#8899AA" strokeWidth="2" style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)' }}><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
        Search…
      </div>
    </div>
  </div>
)

// ─── Mockup screens ───────────────────────────────────────────────────────────

const ScreenOrgs = () => {
  const rows = [
    { initials: 'OS', name: 'OmniSecura',   slug: 'omnisecura',  plan: 'enterprise', role: 'owner',  active: true },
    { initials: 'AC', name: 'Acme Corp',    slug: 'acme-corp',   plan: 'pro',        role: 'admin',  active: true },
    { initials: 'PL', name: 'Pinelabs',     slug: 'pinelabs-io', plan: 'pro',        role: 'admin',  active: true },
    { initials: 'NV', name: 'Northvault',   slug: 'northvault',  plan: 'free',       role: 'member', active: true },
    { initials: 'BX', name: 'BlackBox Labs',slug: 'blackbox',    plan: 'enterprise', role: 'viewer', active: false },
  ]
  return (
    <div style={{ display: 'flex', height: '100%', background: '#F4F8FC' }}>
      {mkSidebar('orgs')}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {mkTopbar(['CyberCore', 'Organizations'])}
        <div style={{ padding: '20px 24px', flex: 1, overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
            <div>
              <div style={{ font: '700 18px/1.15 Syne', color: '#0A1628', letterSpacing: '-.3px' }}>Your organizations</div>
              <div style={{ font: '400 12px/1.5 DM Sans', color: '#8899AA', marginTop: 3 }}>Manage teams, members and permissions.</div>
            </div>
            <button style={{ height: 30, padding: '0 13px', borderRadius: 8, background: 'linear-gradient(135deg,#00C2CB,#1A6EF5)', color: '#fff', font: '600 11.5px/1 DM Sans', border: 'none', boxShadow: '0 4px 14px rgba(0,194,203,.3)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              New organization
            </button>
          </div>
          <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
            {['All · 5', 'Active · 4', 'Owner'].map((t, i) => (
              <div key={t} style={{ height: 28, padding: '0 11px', borderRadius: 999, background: i === 0 ? '#0A1628' : '#fff', border: i === 0 ? 'none' : '1.5px solid #D6E4F0', color: i === 0 ? '#fff' : '#4A6080', font: '500 11px/1 DM Sans', display: 'grid', placeItems: 'center' }}>{t}</div>
            ))}
          </div>
          <div style={{ background: '#fff', border: '1px solid #E6EEF6', borderRadius: 11, boxShadow: '0 1px 3px rgba(10,22,40,.05)', overflow: 'hidden' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '2.4fr .8fr .8fr .9fr', padding: '9px 16px', background: '#F4F8FC', borderBottom: '1px solid #E6EEF6', font: '600 9.5px/1 DM Sans', color: '#8899AA', letterSpacing: '.1em', textTransform: 'uppercase' }}>
              <div>Organization</div><div>Plan</div><div>Role</div><div>Status</div>
            </div>
            {rows.map((r) => (
              <div key={r.slug} style={{ display: 'grid', gridTemplateColumns: '2.4fr .8fr .8fr .9fr', padding: '12px 16px', borderBottom: '1px solid #E6EEF6', alignItems: 'center', opacity: r.active ? 1 : .65 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ width: 30, height: 30, borderRadius: 8, background: 'linear-gradient(135deg,#E0FAFA,#E8F0FE)', color: '#009EA6', display: 'grid', placeItems: 'center', font: '700 11px/1 Syne' }}>{r.initials}</div>
                  <div>
                    <div style={{ font: '500 12.5px/1.2 DM Sans', color: '#0A1628' }}>{r.name}</div>
                    <div style={{ font: '400 10px/1 JetBrains Mono', color: '#8899AA', marginTop: 2 }}>{r.slug}</div>
                  </div>
                </div>
                <div><span style={{ height: 18, padding: '0 7px', borderRadius: 999, font: '600 9px/1 DM Sans', textTransform: 'uppercase', display: 'inline-flex', alignItems: 'center', background: r.plan === 'enterprise' ? '#E8F0FE' : r.plan === 'pro' ? '#E0FAFA' : '#ECF2F8', color: r.plan === 'enterprise' ? '#1457C8' : r.plan === 'pro' ? '#009EA6' : '#4A6080' }}>{r.plan}</span></div>
                <div><span style={{ height: 18, padding: '0 7px', borderRadius: 999, font: '600 9px/1 DM Sans', textTransform: 'uppercase', display: 'inline-flex', alignItems: 'center', background: r.role === 'owner' ? 'linear-gradient(135deg,#E0FAFA,#E8F0FE)' : r.role === 'admin' ? '#E8F0FE' : '#ECF2F8', color: r.role === 'owner' ? '#1457C8' : r.role === 'admin' ? '#1457C8' : '#4A6080' }}>{r.role}</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: r.active ? '#38A169' : '#8899AA', boxShadow: r.active ? '0 0 0 2.5px rgba(56,161,105,.2)' : 'none' }}/>
                  <span style={{ font: '400 11.5px/1 DM Sans', color: r.active ? '#276749' : '#8899AA' }}>{r.active ? 'active' : 'paused'}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

const ScreenScans = () => {
  const findings = [
    { sev: 'critical', tool: 'semgrep',  title: 'SQL Injection in user_router.py',        loc: 'services/auth/routers/user_router.py:142', conf: .94 },
    { sev: 'high',     tool: 'bandit',   title: 'Hardcoded subprocess shell=True',         loc: 'workers/scan_worker/runner.py:88',          conf: .82 },
    { sev: 'high',     tool: 'gitleaks', title: 'AWS Access Key found in commit',           loc: 'infra/.env.example:7',                      conf: 1   },
    { sev: 'medium',   tool: 'trivy',    title: 'CVE-2024-21345 — openssl 3.0.10',         loc: 'services/dast/Dockerfile',                  conf: .9  },
    { sev: 'medium',   tool: 'hadolint', title: 'DL3008 — package version not pinned',     loc: 'agent/Dockerfile:14',                       conf: .7  },
    { sev: 'low',      tool: 'semgrep',  title: 'Debug logger left in production',         loc: 'services/log/main.py:201',                  conf: .65 },
  ]
  const sevColor = { critical: '#B83249', high: '#E53E3E', medium: '#DD6B20', low: '#D69E2E' }
  return (
    <div style={{ display: 'flex', height: '100%', background: '#F4F8FC' }}>
      {mkSidebar('findings')}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {mkTopbar(['OmniSecura', 'Scans', 'scan-3f81a2 · SAST'])}
        <div style={{ padding: '20px 24px', flex: 1, overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
            <div>
              <div style={{ font: '700 17px/1.2 Syne', color: '#0A1628', letterSpacing: '-.3px' }}>cybercore/services/auth-service</div>
              <div style={{ font: '400 11.5px/1.5 DM Sans', color: '#8899AA', marginTop: 3 }}>main · commit 4f8e21c · 14:32, May 14 2026 · 1m 47s</div>
            </div>
            <button style={{ height: 30, padding: '0 13px', borderRadius: 7, background: 'linear-gradient(135deg,#00C2CB,#1A6EF5)', color: '#fff', font: '600 11px/1 DM Sans', border: 'none', boxShadow: '0 4px 12px rgba(0,194,203,.3)' }}>Re-scan</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, marginBottom: 14 }}>
            {[{ label: 'CRITICAL', val: 1, c: '#B83249' }, { label: 'HIGH', val: 4, c: '#E53E3E' }, { label: 'MEDIUM', val: 9, c: '#DD6B20' }, { label: 'LOW', val: 12, c: '#D69E2E' }, { label: 'INFO', val: 28, c: '#1A6EF5' }].map((s) => (
              <div key={s.label} style={{ background: '#fff', border: '1px solid #E6EEF6', borderRadius: 9, padding: '11px 14px', position: 'relative', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: s.c }}/>
                <div style={{ font: '600 9px/1 DM Sans', color: '#8899AA', letterSpacing: '.1em', marginBottom: 7 }}>{s.label}</div>
                <div style={{ font: '700 22px/1 Syne', color: '#0A1628', letterSpacing: '-.5px' }}>{s.val}</div>
              </div>
            ))}
          </div>
          <div style={{ background: '#fff', border: '1px solid #E6EEF6', borderRadius: 11, boxShadow: '0 1px 3px rgba(10,22,40,.05)', overflow: 'hidden' }}>
            {findings.map((f, i) => (
              <div key={i} style={{ padding: '11px 16px', borderBottom: i === findings.length - 1 ? 'none' : '1px solid #E6EEF6', display: 'grid', gridTemplateColumns: '70px 1fr 80px 60px', gap: 12, alignItems: 'center' }}>
                <div><span style={{ height: 18, padding: '0 7px', borderRadius: 4, font: '700 9px/1 DM Sans', letterSpacing: '.08em', textTransform: 'uppercase', background: sevColor[f.sev] + '18', color: sevColor[f.sev], border: `1px solid ${sevColor[f.sev]}30`, display: 'inline-flex', alignItems: 'center' }}>{f.sev}</span></div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ font: '500 12.5px/1.3 DM Sans', color: '#0A1628' }}>{f.title}</div>
                  <div style={{ font: '400 10.5px/1.3 JetBrains Mono', color: '#8899AA', marginTop: 3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.loc}</div>
                </div>
                <div><span style={{ font: '500 10px/1 JetBrains Mono', color: '#4A6080', background: '#ECF2F8', padding: '3px 7px', borderRadius: 4 }}>{f.tool}</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <div style={{ width: 36, height: 4, borderRadius: 2, background: '#ECF2F8', position: 'relative', overflow: 'hidden' }}>
                    <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${f.conf * 100}%`, background: '#00C2CB' }}/>
                  </div>
                  <span style={{ font: '500 10px/1 JetBrains Mono', color: '#4A6080' }}>{Math.round(f.conf * 100)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

const DonutSvg = () => (
  <svg width="88" height="88" viewBox="0 0 100 100">
    <circle cx="50" cy="50" r="36" fill="none" stroke="#F4F8FC" strokeWidth="14"/>
    <circle cx="50" cy="50" r="36" fill="none" stroke="#D69E2E" strokeWidth="14" strokeDasharray="226 226" strokeDashoffset="0" transform="rotate(-90 50 50)"/>
    <circle cx="50" cy="50" r="36" fill="none" stroke="#DD6B20" strokeWidth="14" strokeDasharray="106 226" strokeDashoffset="-120" transform="rotate(-90 50 50)"/>
    <circle cx="50" cy="50" r="36" fill="none" stroke="#E53E3E" strokeWidth="14" strokeDasharray="38 226" strokeDashoffset="-82" transform="rotate(-90 50 50)"/>
    <circle cx="50" cy="50" r="36" fill="none" stroke="#B83249" strokeWidth="14" strokeDasharray="12 226" strokeDashoffset="-44" transform="rotate(-90 50 50)"/>
    <text x="50" y="46" textAnchor="middle" style={{ font: '700 18px Syne', fill: '#0A1628' }}>76</text>
    <text x="50" y="60" textAnchor="middle" style={{ font: '500 8px DM Sans', fill: '#8899AA' }}>findings</text>
  </svg>
)

const ScreenOrgDashboard = () => (
  <div style={{ display: 'flex', height: '100%', background: '#F4F8FC' }}>
    {mkSidebar('orgs')}
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      {mkTopbar(['CyberCore', 'Organizations', 'OmniSecura'])}
      <div style={{ padding: '20px 24px', flex: 1, overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <div style={{ width: 44, height: 44, borderRadius: 11, background: 'linear-gradient(135deg,#00C2CB,#1A6EF5)', display: 'grid', placeItems: 'center', font: '700 16px/1 Syne', color: '#fff', boxShadow: '0 4px 14px rgba(0,194,203,.35)' }}>OS</div>
          <div>
            <div style={{ font: '700 19px/1.15 Syne', color: '#0A1628', letterSpacing: '-.3px' }}>OmniSecura</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4 }}>
              <span style={{ font: '400 11px/1 JetBrains Mono', color: '#8899AA' }}>omnisecura</span>
              <span style={{ height: 18, padding: '0 7px', borderRadius: 999, background: '#E8F0FE', color: '#1457C8', font: '600 9px/1 DM Sans', textTransform: 'uppercase', display: 'inline-flex', alignItems: 'center' }}>enterprise</span>
            </div>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 14 }}>
          {[{ label: 'ACTIVE SCANS', val: '3', sub: 'running now' }, { label: 'PROJECTS', val: '17', sub: '+4 this week' }, { label: 'ALERTS 24H', val: '8', sub: '2 critical', warn: true }, { label: 'LOGS/SEC', val: '1.2k', sub: '↑ 12%' }].map((s) => (
            <div key={s.label} style={{ background: '#fff', border: '1px solid #E6EEF6', borderRadius: 9, padding: '13px 15px' }}>
              <div style={{ font: '600 9px/1 DM Sans', color: '#8899AA', letterSpacing: '.1em', marginBottom: 8 }}>{s.label}</div>
              <div style={{ font: '700 22px/1 Syne', letterSpacing: '-.5px', color: s.warn ? '#C53030' : '#0A1628' }}>{s.val}</div>
              <div style={{ font: '400 10.5px/1 DM Sans', color: '#8899AA', marginTop: 4 }}>{s.sub}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 14 }}>
          <div style={{ background: '#fff', border: '1px solid #E6EEF6', borderRadius: 11, overflow: 'hidden' }}>
            <div style={{ padding: '10px 16px', borderBottom: '1px solid #E6EEF6', font: '600 11.5px/1 DM Sans', color: '#0A1628', display: 'flex', justifyContent: 'space-between' }}>
              <span>Recent activity</span><span style={{ font: '500 10.5px/1 DM Sans', color: '#009EA6' }}>live</span>
            </div>
            {[{ d: '#B83249', t: 'SQL Injection detected', m: 'auth-service · semgrep', tm: '2 min ago' }, { d: '#38A169', t: 'SAST scan completed', m: 'log-service · 14 findings', tm: '14 min' }, { d: '#1A6EF5', t: 'New member joined', m: 'm.nowak@omnisecura.io', tm: '38 min' }, { d: '#DD6B20', t: 'Agent lost connection', m: 'prod-eu-1.omnisecura.io', tm: '1 h' }, { d: '#009EA6', t: 'Alert rule updated', m: 'CRITICAL → slack #sec-ops', tm: '2 h' }].map((a, i) => (
              <div key={i} style={{ padding: '10px 16px', borderBottom: i === 4 ? 'none' : '1px solid #F0F4F8', display: 'flex', alignItems: 'center', gap: 11 }}>
                <div style={{ width: 8, height: 8, borderRadius: 999, background: a.d, flexShrink: 0 }}/>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ font: '500 12.5px/1.3 DM Sans', color: '#0A1628' }}>{a.t}</div>
                  <div style={{ font: '400 10.5px/1.3 JetBrains Mono', color: '#8899AA', marginTop: 2 }}>{a.m}</div>
                </div>
                <span style={{ font: '400 10.5px/1 DM Sans', color: '#8899AA' }}>{a.tm}</span>
              </div>
            ))}
          </div>
          <div style={{ background: '#fff', border: '1px solid #E6EEF6', borderRadius: 11, padding: 16 }}>
            <div style={{ font: '600 11px/1 DM Sans', color: '#0A1628', marginBottom: 12 }}>Severity breakdown</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <DonutSvg />
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[{ c: '#B83249', l: 'Critical', n: 3 }, { c: '#E53E3E', l: 'High', n: 11 }, { c: '#DD6B20', l: 'Medium', n: 24 }, { c: '#D69E2E', l: 'Low', n: 38 }].map(s => (
                  <div key={s.l} style={{ display: 'flex', alignItems: 'center', gap: 6, font: '400 11px/1 DM Sans', color: '#4A6080' }}>
                    <span style={{ width: 7, height: 7, borderRadius: 2, background: s.c }}/>
                    <span style={{ flex: 1 }}>{s.l}</span>
                    <span style={{ fontWeight: 600, color: '#0A1628' }}>{s.n}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
)

const ScreenLogs = () => {
  const logs = [
    { ts: '14:32:08.221', lvl: 'INFO',  svc: 'auth-service',       msg: 'User logged in',            meta: 'user_id=2f9b81…' },
    { ts: '14:32:08.118', lvl: 'INFO',  svc: 'scan-orchestrator',  msg: 'Scan started',              meta: 'scan_id=3f81a2 type=SAST' },
    { ts: '14:32:07.984', lvl: 'WARN',  svc: 'agent-service',      msg: 'Unusual outbound connection',meta: 'ip=185.220.x.x port=8333' },
    { ts: '14:32:07.812', lvl: 'ERROR', svc: 'dast-worker',        msg: 'ZAP daemon timeout',        meta: 'retry=2/3' },
    { ts: '14:32:07.554', lvl: 'INFO',  svc: 'log-consumer',       msg: 'Batch flushed',             meta: 'rows=2148 partition=p3' },
    { ts: '14:32:07.331', lvl: 'INFO',  svc: 'sast-worker',        msg: 'Semgrep ruleset loaded',    meta: 'rules=4218' },
    { ts: '14:32:07.014', lvl: 'CRIT',  svc: 'alert-service',      msg: 'CRITICAL finding pushed',   meta: 'channel=slack#sec-ops' },
    { ts: '14:32:06.891', lvl: 'INFO',  svc: 'tenant-service',     msg: 'Project created',           meta: 'org=omnisecura' },
    { ts: '14:32:06.701', lvl: 'DEBUG', svc: 'ml-worker',          msg: 'Baseline updated',          meta: 'sigma=0.42' },
    { ts: '14:32:06.503', lvl: 'INFO',  svc: 'auth-service',       msg: 'MFA challenge passed',      meta: 'method=totp' },
  ]
  const lvlColor = { DEBUG: '#8899AA', INFO: '#1A6EF5', WARN: '#DD6B20', ERROR: '#E53E3E', CRIT: '#B83249' }
  return (
    <div style={{ display: 'flex', height: '100%', background: '#F4F8FC' }}>
      {mkSidebar('logs')}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {mkTopbar(['CyberCore', 'Logs', 'live · prod'])}
        <div style={{ padding: '14px 20px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <div>
            <div style={{ font: '700 17px/1.15 Syne', color: '#0A1628', letterSpacing: '-.3px' }}>Log stream · prod</div>
            <div style={{ font: '400 11.5px/1.5 DM Sans', color: '#8899AA', marginTop: 2 }}>9 projects · 1.2k events/s</div>
          </div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: 26, padding: '0 10px', borderRadius: 7, background: 'rgba(56,161,105,.1)', color: '#276749', border: '1px solid #C6F6D5', font: '600 11px/1 DM Sans' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#38A169' }}/>LIVE
          </div>
        </div>
        <div style={{ margin: '0 20px 10px', background: '#0A1628', border: '1px solid #1B2C4A', borderRadius: 10, overflow: 'hidden', flex: 1 }}>
          {logs.map((l, i) => (
            <div key={i} style={{ padding: '6px 14px', display: 'grid', gridTemplateColumns: '100px 52px 130px 1fr', gap: 10, alignItems: 'center', font: '500 10.5px/1.4 JetBrains Mono', borderBottom: i === logs.length - 1 ? 'none' : '1px solid rgba(255,255,255,.04)', color: 'rgba(255,255,255,.55)' }}>
              <span style={{ color: 'rgba(255,255,255,.35)' }}>{l.ts}</span>
              <span style={{ color: lvlColor[l.lvl], fontWeight: 700 }}>{l.lvl}</span>
              <span style={{ color: '#00C2CB' }}>{l.svc}</span>
              <span style={{ color: 'rgba(255,255,255,.82)' }}>{l.msg}<span style={{ color: 'rgba(255,255,255,.35)', marginLeft: 8 }}>{l.meta}</span></span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const MetricChart = ({ label, val, peak }) => (
  <div style={{ background: '#fff', border: '1px solid #E6EEF6', borderRadius: 10, padding: '12px 14px', position: 'relative', overflow: 'hidden' }}>
    <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8 }}>
      <span style={{ font: '600 9.5px/1 DM Sans', color: '#8899AA', letterSpacing: '.1em' }}>{label}</span>
      <span style={{ font: '500 10.5px/1 JetBrains Mono', color: '#8899AA' }}>peak {peak}</span>
    </div>
    <div style={{ font: '700 22px/1 Syne', color: '#0A1628', marginBottom: 8, letterSpacing: '-.5px' }}>{val}</div>
    <svg viewBox="0 0 200 36" style={{ display: 'block', width: '100%', height: 36 }}>
      <defs><linearGradient id={`g-${label}`} x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#00C2CB" stopOpacity=".35"/><stop offset="100%" stopColor="#00C2CB" stopOpacity="0"/></linearGradient></defs>
      <path d="M0 22 L15 18 L30 24 L45 14 L60 20 L75 10 L90 16 L105 6 L120 14 L135 20 L150 12 L165 22 L180 16 L200 8 L200 36 L0 36 Z" fill={`url(#g-${label})`}/>
      <path d="M0 22 L15 18 L30 24 L45 14 L60 20 L75 10 L90 16 L105 6 L120 14 L135 20 L150 12 L165 22 L180 16 L200 8" fill="none" stroke="#00C2CB" strokeWidth="1.5"/>
    </svg>
  </div>
)

const ScreenAgent = () => (
  <div style={{ display: 'flex', height: '100%', background: '#F4F8FC' }}>
    {mkSidebar('agents')}
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      {mkTopbar(['CyberCore', 'Agents', 'prod-eu-1.omnisecura.io'])}
      <div style={{ padding: '20px 24px', flex: 1, overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 }}>
          <div style={{ width: 44, height: 44, borderRadius: 11, background: '#0A1628', display: 'grid', placeItems: 'center', border: '1px solid #1B2C4A', color: '#00C2CB' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/></svg>
          </div>
          <div>
            <div style={{ font: '700 18px/1.15 Syne', color: '#0A1628', letterSpacing: '-.3px' }}>prod-eu-1.omnisecura.io</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4 }}>
              <span style={{ font: '400 11px/1 JetBrains Mono', color: '#8899AA' }}>Ubuntu 22.04 · v0.8.2 · uptime 14d 6h</span>
              <span style={{ height: 18, padding: '0 8px', borderRadius: 999, background: '#F0FFF4', color: '#276749', border: '1px solid #C6F6D5', font: '600 9px/1 DM Sans', textTransform: 'uppercase', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#38A169' }}/>online
              </span>
            </div>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 14 }}>
          <MetricChart label="CPU" val="38%" peak="61%"/>
          <MetricChart label="RAM" val="4.2 GB" peak="7.8 GB"/>
          <MetricChart label="NETWORK" val="14 MB/s" peak="42 MB/s"/>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 12 }}>
          <div style={{ background: '#fff', border: '1px solid #E6EEF6', borderRadius: 11, overflow: 'hidden' }}>
            <div style={{ padding: '10px 16px', borderBottom: '1px solid #E6EEF6', font: '600 11.5px/1 DM Sans', color: '#0A1628', display: 'flex', justifyContent: 'space-between' }}>Processes <span style={{ color: '#8899AA', fontWeight: 400 }}>top 6</span></div>
            {[{ p: 'systemd', pid: 1, cpu: 0.4, sus: false }, { p: 'postgres', pid: 4218, cpu: 12.4, sus: false }, { p: 'cybercore-agent', pid: 4901, cpu: 3.1, sus: false }, { p: 'minerd', pid: 7714, cpu: 88.3, sus: true }, { p: 'nginx', pid: 4422, cpu: 1.8, sus: false }, { p: 'redis-server', pid: 4501, cpu: 2.2, sus: false }].map((p, i) => (
              <div key={i} style={{ padding: '8px 16px', display: 'grid', gridTemplateColumns: '1.6fr 60px 1fr', gap: 10, alignItems: 'center', borderBottom: i === 5 ? 'none' : '1px solid #F0F4F8', background: p.sus ? '#FFF5F5' : 'transparent' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  {p.sus && <span style={{ width: 14, height: 14, borderRadius: 4, background: '#E53E3E', color: '#fff', display: 'grid', placeItems: 'center', font: '700 9px/1 DM Sans' }}>!</span>}
                  <span style={{ font: '500 12px/1 JetBrains Mono', color: p.sus ? '#C53030' : '#0A1628' }}>{p.p}</span>
                </div>
                <span style={{ font: '400 10.5px/1 JetBrains Mono', color: '#8899AA' }}>pid {p.pid}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 36, height: 4, background: '#ECF2F8', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{ width: `${Math.min(p.cpu, 100)}%`, height: '100%', background: p.cpu > 50 ? '#E53E3E' : '#00C2CB' }}/>
                  </div>
                  <span style={{ font: '500 10.5px/1 JetBrains Mono', color: '#4A6080' }}>{p.cpu}%</span>
                </div>
              </div>
            ))}
          </div>
          <div style={{ background: '#fff', border: '1px solid #E6EEF6', borderRadius: 11, overflow: 'hidden' }}>
            <div style={{ padding: '10px 16px', borderBottom: '1px solid #E6EEF6', font: '600 11.5px/1 DM Sans', color: '#0A1628', display: 'flex', justifyContent: 'space-between' }}>ML anomalies <span style={{ color: '#C53030' }}>3 new</span></div>
            {[{ c: '#B83249', t: 'High CPU · process "minerd"', s: 'sigma 4.2 · started 12 min ago' }, { c: '#E53E3E', t: 'Outbound on port 8333', s: 'first observed · TOR exit node' }, { c: '#DD6B20', t: 'Unusual process tree', s: 'nginx → bash → curl' }, { c: '#1A6EF5', t: 'Baseline updated', s: '14:24 · done' }].map((a, i) => (
              <div key={i} style={{ padding: '10px 16px', borderBottom: i === 3 ? 'none' : '1px solid #F0F4F8', display: 'flex', gap: 11 }}>
                <div style={{ width: 8, height: 8, borderRadius: 999, background: a.c, marginTop: 5, flexShrink: 0 }}/>
                <div>
                  <div style={{ font: '500 12px/1.3 DM Sans', color: '#0A1628' }}>{a.t}</div>
                  <div style={{ font: '400 10.5px/1.3 DM Sans', color: '#8899AA', marginTop: 2 }}>{a.s}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  </div>
)

// ─── Slide definitions ────────────────────────────────────────────────────────

const SLIDES = [
  { id: 'orgs',  url: 'cybercore.app/orgs',               title: 'Organizations & teams',    sub: 'Multi-tenant with RBAC — roles, plans and invites from a single view.', Comp: ScreenOrgs },
  { id: 'scans', url: 'cybercore.app/scans/3f81a2',       title: 'SAST · unified findings',  sub: 'Semgrep, Bandit, Trivy, Gitleaks — one consistent finding format.',       Comp: ScreenScans },
  { id: 'dash',  url: 'cybercore.app/orgs/omnisecura',    title: 'Organization dashboard',   sub: 'Stats, severity breakdown and real-time activity stream.',                Comp: ScreenOrgDashboard },
  { id: 'logs',  url: 'cybercore.app/logs/live',          title: 'Centralized logs',         sub: 'Live stream with per-project isolation. Filters, severity, retention.',   Comp: ScreenLogs },
  { id: 'agent', url: 'cybercore.app/agents/prod-eu-1',   title: 'Agent · host monitoring',  sub: 'Processes, connections and ML-detected anomalies on the machine.',        Comp: ScreenAgent },
]

// ─── Sections ─────────────────────────────────────────────────────────────────

const FEATURES = [
  { icon: 'lock',     title: 'Auth Service',      text: 'Full identity: MFA (TOTP), OAuth2 with Google and GitHub, JWT with refresh-token rotation. Rate-limit and lockout out of the box.',              tags: ['MFA', 'OAuth2', 'UUID', 'JWT'] },
  { icon: 'search',   title: 'Scan Service',      text: 'Central orchestrator for every scan. Normalizes SAST, DAST and agent results into a single finding format.',                                     tags: ['SAST', 'DAST', 'AGENT', 'unified'] },
  { icon: 'code',     title: 'SAST',              text: 'Scan code from a ZIP or a public git repo. Semgrep, Bandit, Gitleaks, Trivy, Hadolint, pip-audit, npm audit, gosec.',                           tags: ['Python', 'JS/TS', 'Go', 'Java', '+7'] },
  { icon: 'bug',      title: 'DAST',              text: 'Attacks your running app — SQLi, XSS, IDOR, SSRF, API fuzzing. Powered by OWASP ZAP under the hood.',                                           tags: ['OWASP ZAP', 'crawler', 'fuzzer'] },
  { icon: 'list',     title: 'Log Service',       text: 'Centralized logs with per-project isolation. SDKs for Python, JS and Go. Full-text search and webhook on ERROR/CRITICAL.',                      tags: ['pip', 'npm', 'go get'] },
  { icon: 'cpu',      title: 'Agent + ML',        text: 'Host telemetry: processes, network, FS, DNS. The ML worker computes a baseline and flags anomalies before they become incidents.',               tags: ['anomaly', 'baseline', 'C++'] },
  { icon: 'bell',     title: 'Alert Service',     text: 'Unified notification layer: email, webhook, Slack, Discord, Telegram. Deduplication, escalations, severity thresholds.',                         tags: ['Slack', 'Discord', 'webhook'] },
  { icon: 'box',      title: 'Tenant Service',    text: 'Multi-tenant management. Organizations, projects, custom roles (RBAC). Invites and ownership transfer.',                                         tags: ['RBAC', 'invites', 'multi-tenant'] },
  { icon: 'server',   title: 'Self-hosted stack', text: 'Postgres, TimescaleDB, Redis, Kafka, Prometheus, Grafana, Loki, Jaeger. All in one Docker Compose or Helm chart.',                              tags: ['Docker', 'k3s', 'Helm', 'Argo CD'] },
]

// ─── OverviewPage ─────────────────────────────────────────────────────────────

export function OverviewPage() {
  const [idx, setIdx]       = useState(0)
  const [paused, setPaused] = useState(false)
  const total = SLIDES.length

  useEffect(() => {
    if (paused) return
    const t = setInterval(() => setIdx(i => (i + 1) % total), 5800)
    return () => clearInterval(t)
  }, [paused, total])

  const go = useCallback((n) => setIdx(cur => ((cur + n) % total + total) % total), [total])

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'ArrowLeft')  go(-1)
      if (e.key === 'ArrowRight') go(1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [go])

  return (
    <div className="lp-page">

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section className="lp-hero" id="lp-top">
        <div className="lp-hero-bg"/>
        <div className="lp-hero-grid"/>
        <div className="lp-hero-orb lp-hero-orb--a"/>
        <div className="lp-hero-orb lp-hero-orb--b"/>
        <div className="lp-container">
          <div className="lp-hero-eyebrow">
            <span className="lp-hero-eyebrow-dot"/>
            <span><strong>{APP_VERSION}</strong> · open-source release</span>
            <span className="lp-sep">·</span>
            <span>MIT licensed</span>
          </div>
          <h1>
            Your own <span className="lp-grad">SOC</span><br/>
            Without the <span className="lp-strike">enterprise</span> contract.
          </h1>
          <p className="lp-lead">
            <strong>CyberCore</strong> is a self-hosted platform for security monitoring, vulnerability scanning
            and threat detection — it combines SAST, DAST, system agents and centralized logs into a single
            dashboard. Full control over your data.
          </p>
          <div className="lp-hero-cta-row">
            <a href="#lp-start" className="lp-btn-pri">
              <Icon name="terminal" size={14}/>
              Deploy in 2 minutes
            </a>
            <a href={URLS.github} className="lp-btn-ghost" target="_blank" rel="noopener noreferrer">
              <Icon name="github" size={16}/>
              View on GitHub
            </a>
          </div>
          <div className="lp-hero-meta">
            <div className="lp-hero-meta-item">
              <Icon name="check" size={16}/> <span><strong>8</strong> open-source tools in one</span>
            </div>
            <div className="lp-hero-meta-item">
              <Icon name="check" size={16}/> <span>Self-hosted · <strong>GDPR-ready</strong></span>
            </div>
            <div className="lp-hero-meta-item">
              <Icon name="check" size={16}/> <span>Docker · k3s · Helm</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── Gallery / Coverflow ───────────────────────────────────────────── */}
      <section className="lp-gallery" id="lp-gallery">
        <div className="lp-container">
          <div className="lp-gallery-head">
            <div className="lp-section-eyebrow">
              <span className="lp-section-eyebrow-bar"/> Product gallery
            </div>
            <h2 className="lp-section-title">A full tour of the dashboard</h2>
            <p className="lp-section-sub">
              Five key views — from organizations to host monitoring. Click or use arrow keys to navigate.
            </p>
          </div>

          <div className="lp-coverflow" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
            <div className="lp-coverflow-stage">
              {SLIDES.map((s, i) => {
                let d = i - idx
                if (d > total / 2) d -= total
                if (d < -total / 2) d += total
                const abs = Math.abs(d)
                if (abs > 2) return null
                const isCenter = d === 0
                const tx    = d * 280
                const ry    = d * -34
                const tz    = -abs * 240
                const scale = isCenter ? 1 : 0.92 - abs * 0.04
                const opacity = 1 - abs * 0.22
                const zIndex  = 50 - abs
                return (
                  <div key={s.id}
                    className={`lp-cf-slide${isCenter ? ' lp-is-center' : ''}`}
                    style={{ transform: `translate(-50%, -50%) translateX(${tx}px) translateZ(${tz}px) rotateY(${ry}deg) scale(${scale})`, opacity, zIndex }}
                    onClick={() => setIdx(i)}
                  >
                    <div className="lp-cf-slide-inner">
                      <MiniBrowser url={s.url}>
                        <s.Comp/>
                      </MiniBrowser>
                    </div>
                    <div className="lp-cf-caption">
                      <div className="lp-cf-caption-title">{s.title}</div>
                      <div className="lp-cf-caption-sub">{s.sub}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          <div className="lp-cf-controls">
            <button className="lp-cf-arrow" onClick={() => go(-1)} aria-label="Previous">
              <Icon name="chevL" size={16}/>
            </button>
            <div className="lp-cf-dots">
              {SLIDES.map((s, i) => (
                <button key={s.id} className={`lp-cf-dot${i === idx ? ' lp-is-on' : ''}`}
                  onClick={() => setIdx(i)} aria-label={s.title}/>
              ))}
            </div>
            <button className="lp-cf-arrow" onClick={() => go(1)} aria-label="Next">
              <Icon name="chevR" size={16}/>
            </button>
          </div>

          <div className="lp-cf-progress">
            <div className="lp-cf-progress-bar" key={`${idx}-${paused}`}
              style={{ animation: paused ? 'none' : 'lp-cfProgress 5.8s linear' }}/>
          </div>
        </div>
      </section>

      {/* ── About ─────────────────────────────────────────────────────────── */}
      <section className="lp-about" id="lp-what">
        <div className="lp-container">
          <div className="lp-about-head">
            <div className="lp-section-eyebrow">
              <span className="lp-section-eyebrow-bar"/> What is CyberCore
            </div>
            <h2 className="lp-section-title">Your private SOC — modular and open</h2>
            <p className="lp-section-sub" style={{ color: 'var(--slate)' }}>
              Static code analysis, dynamic app testing, system monitoring and centralized logs —
              all in one coherent platform you can deploy on your own infra in minutes.
            </p>
          </div>

          <div className="lp-about-grid">
            <div>
              <div className="lp-about-pills">
                <span className="lp-about-pill">SAST</span>
                <span className="lp-about-pill">DAST</span>
                <span className="lp-about-pill lp-about-pill--blue">Agent</span>
                <span className="lp-about-pill lp-about-pill--blue">Logs</span>
                <span className="lp-about-pill lp-about-pill--slate">Alerts</span>
                <span className="lp-about-pill lp-about-pill--slate">RBAC</span>
              </div>
              <h2>Security <em>you control</em> — not somebody else's cloud.</h2>
              <p className="lp-about-lead">
                CyberCore stitches the best open-source security tools into one modular stack.
                Each component is independently deployable. Fully integrated through a shared finding format.
              </p>
              <div className="lp-about-bullets">
                {[
                  { icon: 'lock',   title: 'Self-hosted from day one',  text: 'Your data never leaves your infrastructure. Docker Compose in dev, Helm + k3s in production.' },
                  { icon: 'layers', title: 'Modular architecture',      text: '9 independently deployable microservices. Use only what you need — the rest stays dormant.' },
                  { icon: 'zap',    title: 'One finding format',        text: 'Semgrep, ZAP, Trivy, Bandit, Gitleaks — they all land in the same table.' },
                ].map(b => (
                  <div key={b.title} className="lp-about-bullet">
                    <div className="lp-about-bullet-icon"><Icon name={b.icon} size={17}/></div>
                    <div>
                      <div className="lp-about-bullet-title">{b.title}</div>
                      <div className="lp-about-bullet-text">{b.text}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="lp-about-stats">
              <div className="lp-about-stats-grid">
                <div className="lp-about-stat">
                  <div className="lp-about-stat-label">Open-source tools</div>
                  <div className="lp-about-stat-val">8 <small>tools</small></div>
                  <div className="lp-about-stat-foot">Semgrep · Bandit · Trivy · ZAP …</div>
                </div>
                <div className="lp-about-stat">
                  <div className="lp-about-stat-label">Severity buckets</div>
                  <div className="lp-about-stat-val">5</div>
                  <div className="lp-about-stat-foot">CRITICAL → INFO</div>
                </div>
                <div className="lp-about-stat">
                  <div className="lp-about-stat-label">SDKs</div>
                  <div className="lp-about-stat-val">3</div>
                  <div className="lp-about-stat-foot">Python · JS · Go</div>
                </div>
                <div className="lp-about-stat">
                  <div className="lp-about-stat-label">Deploy</div>
                  <div className="lp-about-stat-val">~2 <small>min</small></div>
                  <div className={`lp-about-stat-foot lp-about-stat-foot--up`}>
                    <Icon name="check" size={11}/> Docker compose ready
                  </div>
                </div>
              </div>
              <div className="lp-about-stats-spark">
                <div className="lp-about-stats-spark-label">
                  <span>cybercore_events / s · last 60s</span>
                  <strong>↑ 12%</strong>
                </div>
                <div className="lp-about-stats-spark-bars">
                  {Array.from({ length: 28 }).map((_, i) => (
                    <i key={i} style={{ animationDelay: `${i * 80}ms` }}/>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ──────────────────────────────────────────────────────── */}
      <section className="lp-features" id="lp-features">
        <div className="lp-container">
          <div className="lp-features-head">
            <div className="lp-section-eyebrow">
              <span className="lp-section-eyebrow-bar"/> Platform components
            </div>
            <h2 className="lp-section-title" style={{ color: 'var(--navy)' }}>9 microservices, one platform</h2>
            <p className="lp-section-sub" style={{ color: 'var(--slate)' }}>
              Every service is independently deployable. Run only what you need —
              the rest waits for its moment.
            </p>
          </div>
          <div className="lp-features-grid">
            {FEATURES.map(f => (
              <div key={f.title} className="lp-feature-card">
                <div className="lp-feature-icon"><Icon name={f.icon} size={20}/></div>
                <h3>{f.title}</h3>
                <p>{f.text}</p>
                <div className="lp-feature-tags">
                  {f.tags.map(t => <span key={t} className="lp-feature-tag">{t}</span>)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How (Quick start) ─────────────────────────────────────────────── */}
      <section className="lp-how" id="lp-start">
        <div className="lp-container">
          <div className="lp-how-head">
            <div className="lp-section-eyebrow">
              <span className="lp-section-eyebrow-bar"/> Quick start
            </div>
            <h2 className="lp-section-title" style={{ color: '#fff' }}>From zero to a running SOC in 3 steps</h2>
            <p className="lp-section-sub">
              Docker + Compose is all you need to start. Production goes through Helm on k3s.
            </p>
          </div>
          <div className="lp-how-steps">
            <div className="lp-how-step">
              <div className="lp-how-step-num">1</div>
              <h3>Clone & configure</h3>
              <p>Clone the repo, copy <code style={{ color: '#FFD3A0' }}>.env.example</code> and set the Postgres password and JWT secret.</p>
              <code className="lp-how-step-code">
                <span className="lp-c"># 30 seconds</span>{'\n'}
                <span className="lp-k">git</span> clone <span className="lp-s">github.com/OmniSecura/CyberCore</span>{'\n'}
                <span className="lp-k">cd</span> CyberCore && <span className="lp-k">cp</span> .env.example .env
              </code>
            </div>
            <div className="lp-how-step">
              <div className="lp-how-step-num">2</div>
              <h3>Boot the stack</h3>
              <p>Three profiles to choose from: <strong style={{ color: '#fff' }}>core</strong>, <strong style={{ color: '#fff' }}>scanning</strong> or the full <strong style={{ color: '#fff' }}>full</strong>.</p>
              <code className="lp-how-step-code">
                <span className="lp-c"># full stack</span>{'\n'}
                <span className="lp-k">docker</span> compose --profile <span className="lp-s">full</span> up{'\n'}
                <span className="lp-c"># dashboard at :3000</span>
              </code>
            </div>
            <div className="lp-how-step">
              <div className="lp-how-step-num">3</div>
              <h3>First scan</h3>
              <p>Create an organization, paste a public git repo and trigger your first SAST scan — results in 30 seconds.</p>
              <code className="lp-how-step-code">
                <span className="lp-c"># or from the CLI</span>{'\n'}
                <span className="lp-k">curl</span> -X POST localhost:8000/api/scans{'\n'}
                {'  '}-d <span className="lp-s">'{`{"repo":"…"}`}'</span>
              </code>
            </div>
          </div>
        </div>
      </section>

      {/* ── Manual / Docs ─────────────────────────────────────────────────── */}
      <section className="lp-manual" id="lp-manual">
        <div className="lp-container">
          <div className="lp-manual-card">
            <div className="lp-manual-card-grid">
              <div>
                <div className="lp-section-eyebrow" style={{ color: '#00C2CB' }}>
                  <span className="lp-section-eyebrow-bar" style={{ background: '#00C2CB' }}/> Documentation
                </div>
                <h2>Full manual, <em>step by step</em>.</h2>
                <p>
                  From environment setup, through configuring every service, to deploying to production.
                  SDKs, examples, API reference — all in one place.
                </p>
                <div className="lp-manual-actions">
                  <a href={URLS.documentation} className="lp-btn-pri">
                    <Icon name="book" size={14}/> Open the manual
                  </a>
                  <a href={URLS.github} className="lp-btn-ghost" target="_blank" rel="noopener noreferrer">
                    <Icon name="github" size={16}/> Repository
                  </a>
                </div>
              </div>
              <div className="lp-manual-docs">
                {[
                  { ic: 'play',    t: 'Getting Started',    s: 'First-time setup · 5 min',      href: URLS.documentation },
                  { ic: 'package', t: 'Architecture Guide', s: '9 microservices in detail',     href: URLS.documentation },
                  { ic: 'code',    t: 'SDK Reference',      s: 'Python · JavaScript · Go',      href: URLS.sdks },
                  { ic: 'cloud',   t: 'Deployment on k3s',  s: 'Helm chart + Argo CD',          href: URLS.selfHosting },
                ].map(d => (
                  <a key={d.t} href={d.href} className="lp-manual-doc">
                    <div className="lp-manual-doc-icon"><Icon name={d.ic} size={16}/></div>
                    <div className="lp-manual-doc-main">
                      <div className="lp-manual-doc-title">{d.t}</div>
                      <div className="lp-manual-doc-sub">{d.s}</div>
                    </div>
                    <div className="lp-manual-doc-arrow"><Icon name="arrow" size={14}/></div>
                  </a>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer className="lp-footer">
        <div className="lp-container">
          <div className="lp-foot-grid">
            <div className="lp-foot-brand">
              <div className="lp-foot-brand-logo">
                <div className="lp-foot-mark">
                  <Icon name="shield" size={15} strokeWidth={2.2}/>
                </div>
                <span style={{ font: '700 17px/1 Syne', color: '#fff' }}>
                  Cyber<em style={{ color: '#00C2CB', fontStyle: 'normal' }}>Core</em>
                </span>
              </div>
              <p>Self-hosted, open-source cybersecurity platform. Built with the belief that security tooling shouldn't require an enterprise contract.</p>
            </div>
            <div className="lp-foot-col">
              <h4>Product</h4>
              <a href="#lp-what">What is CyberCore</a>
              <a href="#lp-features">Features</a>
              <a href="#lp-gallery">Gallery</a>
              <a href={URLS.roadmap}>Roadmap</a>
              <a href={URLS.changelog}>Changelog</a>
            </div>
            <div className="lp-foot-col">
              <h4>Docs</h4>
              <a href="#lp-start">Quick start</a>
              <a href={URLS.documentation}>Manual</a>
              <a href={URLS.sdks}>SDKs</a>
              <a href={URLS.apiReference}>API Reference</a>
              <a href={URLS.selfHosting}>Self-hosting</a>
            </div>
            <div className="lp-foot-col">
              <h4>Community</h4>
              <a href={URLS.github} target="_blank" rel="noopener noreferrer">GitHub</a>
              <a href={URLS.discord}>Discord</a>
              <a href={URLS.contributing}>Contributing</a>
              <a href={URLS.securityPolicy}>Security policy</a>
              <a href={URLS.vulnerability}>Report a vulnerability</a>
            </div>
          </div>
          <div className="lp-foot-bottom">
            <div className="lp-foot-bottom-left">
              <span className="lp-foot-status-dot"/>
              All systems operational · <span style={{ fontFamily: 'var(--font-mono)', color: 'rgba(255,255,255,.6)' }}>{APP_VERSION}</span>
            </div>
            <div>© 2026 OmniSecura · MIT License · Built in EU 🇪🇺</div>
          </div>
        </div>
      </footer>
    </div>
  )
}
