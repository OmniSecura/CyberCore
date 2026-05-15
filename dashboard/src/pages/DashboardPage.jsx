import { useState, useEffect, useMemo, useCallback } from 'react'
import { CreateOrgModal } from '../components/organizations/CreateOrgModal'
import { OrgDashboard }   from '../components/organizations/OrgDashboard'
import { orgApi }         from '../api/endpoints'
import { OverviewPage }   from './OverviewPage'
import { APP_VERSION }    from '../config/constants'

// ─── Icons ────────────────────────────────────────────────────────────────────

const IconHome = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 7l7-5 7 5M2 7v7h4v-4h4v4h4V7"/>
  </svg>
)
const IconShield = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2l7 4v6c0 5-3.5 8.5-7 10-3.5-1.5-7-5-7-10V6l7-4z"/>
  </svg>
)
const IconBuilding = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="1" y="4" width="14" height="11" rx="2"/>
    <path d="M5 4V3a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v1M5 9h2M9 9h2M5 12h2M9 12h2"/>
  </svg>
)
const IconCpu = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="4" y="4" width="8" height="8" rx="1"/>
    <path d="M6 1v3M10 1v3M6 12v3M10 12v3M1 6h3M1 10h3M12 6h3M12 10h3"/>
  </svg>
)
const IconBell = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M8 1a5 5 0 0 1 5 5v3l1 2H2l1-2V6a5 5 0 0 1 5-5zM6.5 13a1.5 1.5 0 0 0 3 0"/>
  </svg>
)
const IconList = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 4h10M3 8h7M3 12h5"/>
  </svg>
)
const IconArrowLeft = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 3L5 8l5 5"/>
  </svg>
)
const IconChevronRight = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 3l5 5-5 5"/>
  </svg>
)
const IconLogout = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 11l3-3-3-3M13 8H6M6 3H3a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h3"/>
  </svg>
)
const IconMenu = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
    <path d="M2 4h12M2 8h12M2 12h12"/>
  </svg>
)
const IconSearch = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="6.5" cy="6.5" r="4.5"/><path d="M10.5 10.5l3 3"/>
  </svg>
)
const IconPlus = () => (
  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
    <path d="M8 2v12M2 8h12"/>
  </svg>
)
const IconReload = ({ spinning }) => (
  <svg
    viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8"
    strokeLinecap="round" strokeLinejoin="round"
    style={spinning ? { animation: 'cc-spin 700ms linear infinite' } : undefined}
  >
    <path d="M13.5 7a5.5 5.5 0 1 0-1.5 4.5"/>
    <path d="M13.5 3v4h-4"/>
  </svg>
)
const IconOffice = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="7" width="18" height="14" rx="2"/>
    <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
  </svg>
)
const IconChevronL = () => (
  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 3L5 8l5 5"/>
  </svg>
)
const IconChevronR = () => (
  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 3l5 5-5 5"/>
  </svg>
)

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(iso) {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(iso))
}

function initials(name = '') {
  return name.split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase() || '?'
}

const ROLE_LABEL = {
  owner:  'Owner',
  admin:  'Admin',
  member: 'Member',
  viewer: 'Viewer',
}

// ─── Sidebar ─────────────────────────────────────────────────────────────────

function Sidebar({ open, onClose, user, onLogout, activeNav, onNavigate }) {
  const userName = user?.full_name || user?.email?.split('@')[0] || 'User'
  const avi = initials(userName)

  const nav = [
    { id: 'overview', label: 'Overview',       Icon: IconHome },
    { id: 'orgs',     label: 'Organizations',  Icon: IconBuilding },
    { id: 'agents',   label: 'Agents',         Icon: IconCpu,  disabled: true },
    { id: 'alerts',   label: 'Alerts',         Icon: IconBell, disabled: true },
    { id: 'logs',     label: 'Logs',           Icon: IconList, disabled: true },
  ]

  return (
    <aside className={`cc-sidebar${open ? '' : ' cc-sidebar--closed'}`}>
      <div className="cc-sb-logo">
        <div className="cc-sb-mark"><IconShield /></div>
        <span className="cc-sb-word">Cyber<em>Core</em></span>
        <button className="cc-sb-close" onClick={onClose} title="Collapse sidebar">
          <IconArrowLeft />
        </button>
      </div>

      <nav className="cc-sb-nav">
        <div className="cc-nav-section">Platform</div>
        {nav.map(({ id, label, Icon, disabled }) => (
          <button
            key={id}
            className={`cc-nav-btn${activeNav === id ? ' cc-nav-btn--active' : ''}`}
            onClick={() => !disabled && onNavigate(id)}
            disabled={disabled}
          >
            <Icon />
            {label}
            {disabled && <span className="cc-nav-soon">Soon</span>}
          </button>
        ))}
      </nav>

      <div className="cc-sb-footer">
        <div className="cc-user-row">
          <div className="cc-avatar">{avi}</div>
          <div className="cc-uinfo">
            <div className="cc-uname">{userName}</div>
            <div className="cc-uemail">{user?.email}</div>
          </div>
          <button className="cc-logout" onClick={onLogout} title="Log out">
            <IconLogout />
          </button>
        </div>
        <div className="cc-sb-version">{APP_VERSION}</div>
      </div>
    </aside>
  )
}

// ─── Skeleton rows ────────────────────────────────────────────────────────────

function SkeletonRows({ count = 5 }) {
  return (
    <>
      {[...Array(count)].map((_, i) => (
        <tr key={i}>
          <td>
            <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
              <span className="cc-skel" style={{ width: 34, height: 34, borderRadius: 9, flexShrink: 0 }} />
              <div>
                <span className="cc-skel" style={{ width: 140, height: 12, display: 'block', marginBottom: 6 }} />
                <span className="cc-skel" style={{ width: 88, height: 10, display: 'block' }} />
              </div>
            </div>
          </td>
          <td><span className="cc-skel" style={{ width: 44, height: 18, borderRadius: 99 }} /></td>
          <td><span className="cc-skel" style={{ width: 60, height: 12 }} /></td>
          <td><span className="cc-skel" style={{ width: 60, height: 12 }} /></td>
          <td><span className="cc-skel" style={{ width: 88, height: 12 }} /></td>
          <td><span className="cc-skel" style={{ width: 54, height: 26, borderRadius: 7 }} /></td>
        </tr>
      ))}
    </>
  )
}

// ─── Organizations view ───────────────────────────────────────────────────────

const PAGE_SIZE = 10

function OrgsView({ onOpenOrg }) {
  const [data, setData]             = useState({ items: [], total: 0, page: 1, page_size: PAGE_SIZE, total_pages: 0 })
  const [loading, setLoading]       = useState(true)
  const [reloading, setReloading]   = useState(false)
  const [error, setError]           = useState(null)
  const [search, setSearch]         = useState('')
  const [filter, setFilter]         = useState('all')
  const [page, setPage]             = useState(1)
  const [showCreate, setShowCreate] = useState(false)
  const [capStatus, setCapStatus]   = useState(null) // { owned, max, can_create }

  const fetchOrgs = useCallback((targetPage = page, soft = false) => {
    if (soft) setReloading(true); else setLoading(true)
    setError(null)
    return orgApi.list({ page: targetPage, pageSize: PAGE_SIZE })
      .then(res => {
        // Backward compat — old endpoint returned plain array
        if (Array.isArray(res)) {
          setData({ items: res, total: res.length, page: 1, page_size: res.length, total_pages: 1 })
        } else {
          setData(res)
        }
      })
      .catch(err => setError(err?.data?.detail || 'Failed to load organizations.'))
      .finally(() => { setLoading(false); setReloading(false) })
  }, [page])

  const fetchCapStatus = useCallback(() => {
    orgApi.freeCapStatus()
      .then(setCapStatus)
      .catch(() => setCapStatus(null)) // non-fatal — UI just won't gate
  }, [])

  useEffect(() => { fetchOrgs(page) /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [page])
  useEffect(() => { fetchCapStatus() }, [fetchCapStatus])

  // Client-side search + filter on the current page (cheap, just the slice)
  const filtered = useMemo(() => {
    let list = data.items
    if (filter === 'active')   list = list.filter(o => o.is_active)
    if (filter === 'inactive') list = list.filter(o => !o.is_active)
    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter(o =>
        (o.organization_name || '').toLowerCase().includes(q) ||
        (o.organization_slug || '').toLowerCase().includes(q) ||
        (o.organization_description || '').toLowerCase().includes(q)
      )
    }
    return list
  }, [data.items, filter, search])

  function handleCreated() {
    setShowCreate(false)
    setPage(1)
    fetchOrgs(1, true)
    fetchCapStatus()
  }

  const atFreeCap = !!capStatus && !capStatus.can_create
  const capTitle  = atFreeCap
    ? `You already own the maximum of ${capStatus.max} free-plan organizations`
    : undefined

  const filters = [
    { id: 'all',      label: 'All' },
    { id: 'active',   label: 'Active' },
    { id: 'inactive', label: 'Inactive' },
  ]

  const totalPages = data.total_pages || 1
  const showingFrom = data.total === 0 ? 0 : (data.page - 1) * data.page_size + 1
  const showingTo   = Math.min(data.page * data.page_size, data.total)

  return (
    <>
      <div className="cc-ph">
        <div className="cc-ph-left">
          <h1 className="cc-ph-title">Organizations</h1>
          <p className="cc-ph-sub">
            Manage the workspaces you belong to.
            {capStatus && (
              <> Free orgs owned: <strong>{capStatus.owned}/{capStatus.max}</strong>.</>
            )}
          </p>
        </div>
        <button
          className="cc-btn cc-btn-md cc-btn-primary"
          onClick={() => setShowCreate(true)}
          disabled={atFreeCap}
          title={capTitle}
        >
          <IconPlus />
          New organization
        </button>
      </div>

      <div className="cc-toolbar">
        <div className="cc-search-wrap">
          <IconSearch />
          <input
            className="cc-search" type="text"
            placeholder="Search organizations…"
            value={search} onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="cc-filters">
          {filters.map(f => (
            <button key={f.id}
              className={`cc-chip${filter === f.id ? ' cc-chip--on' : ''}`}
              onClick={() => setFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <button
          className="cc-icon-btn"
          onClick={() => fetchOrgs(page, true)}
          disabled={reloading || loading}
          title="Reload organizations"
        >
          <IconReload spinning={reloading} />
        </button>
      </div>

      {error && (
        <div className="cc-alert cc-alert--err">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="8" cy="8" r="6"/><path d="M8 5v3M8 11v.5"/>
          </svg>
          {error}
        </div>
      )}

      <div className="cc-table-card">
        <table className="cc-table">
          <thead>
            <tr>
              <th>Organization</th>
              <th>Plan</th>
              <th>Role</th>
              <th>Status</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <SkeletonRows />
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: 0 }}>
                  <div className="cc-empty">
                    <div className="cc-empty-icon"><IconOffice /></div>
                    {data.total === 0 ? (
                      <>
                        <div className="cc-empty-title">No organizations yet</div>
                        <div className="cc-empty-sub">Create your first organization to get started with CyberCore.</div>
                        <button
                          className="cc-btn cc-btn-md cc-btn-primary"
                          onClick={() => setShowCreate(true)}
                          disabled={atFreeCap}
                          title={capTitle}
                        >
                          Create organization
                        </button>
                      </>
                    ) : (
                      <>
                        <div className="cc-empty-title">No results found</div>
                        <div className="cc-empty-sub">No organizations match your search or active filter.</div>
                        <button className="cc-btn cc-btn-md cc-btn-ghost"
                          onClick={() => { setSearch(''); setFilter('all') }}>
                          Clear filters
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              filtered.map(org => (
                <tr
                  key={org.id || org.organization_slug}
                  className={org.is_active ? undefined : 'cc-row--inactive'}
                  onClick={() => onOpenOrg(org)}
                >
                  <td>
                    <div className="cc-org-cell">
                      <div className="cc-org-icon">{initials(org.organization_name)}</div>
                      <div>
                        <div className="cc-org-name">{org.organization_name}</div>
                        <div className="cc-org-slug">{org.organization_slug}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className={`cc-badge cc-badge--${org.plan || 'free'}`}>
                      {org.plan || 'free'}
                    </span>
                  </td>
                  <td>
                    <span className={`cc-role-pill cc-role-${org.role || 'viewer'}`}>
                      {ROLE_LABEL[org.role] || 'Viewer'}
                    </span>
                  </td>
                  <td>
                    <span className={`cc-status${org.is_active ? ' cc-status--active' : ''}`}>
                      <span className="cc-status-dot" />
                      {org.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td style={{ color: '#8899AA', fontSize: 13 }}>{fmtDate(org.created_at)}</td>
                  <td onClick={e => e.stopPropagation()}>
                    <button className="cc-row-btn" onClick={() => onOpenOrg(org)}>
                      <IconChevronRight />
                      Open
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {!loading && data.total > 0 && (
          <div className="cc-table-foot">
            <span>
              Showing {showingFrom}–{showingTo} of {data.total} organization{data.total !== 1 ? 's' : ''}
            </span>
            {totalPages > 1 && (
              <div className="cc-pager">
                <button
                  className="cc-page-btn"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={data.page <= 1 || reloading}
                  title="Previous page"
                ><IconChevronL /></button>
                <span className="cc-page-info">
                  Page {data.page} of {totalPages}
                </span>
                <button
                  className="cc-page-btn"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={data.page >= totalPages || reloading}
                  title="Next page"
                ><IconChevronR /></button>
              </div>
            )}
          </div>
        )}
      </div>

      {showCreate && (
        <CreateOrgModal
          capStatus={capStatus}
          onClose={() => setShowCreate(false)}
          onCreate={handleCreated}
        />
      )}
    </>
  )
}

// ─── Root dashboard ──────────────────────────────────────────────────────────

export function DashboardPage({ user, onLogout }) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [nav, setNav]                 = useState('overview')
  const [activeOrg, setActiveOrg]     = useState(null)

  const breadcrumb = activeOrg
    ? activeOrg.organization_name
    : nav === 'overview'
      ? 'Overview'
      : 'Organizations'

  return (
    <div className="cc-shell">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        user={user}
        onLogout={onLogout}
        activeNav={nav}
        onNavigate={v => { setNav(v); setActiveOrg(null) }}
      />

      <div className={`cc-content${sidebarOpen ? '' : ' cc-content--wide'}`}>
        <div className="cc-topbar">
          {!sidebarOpen && (
            <button className="cc-menu-btn" onClick={() => setSidebarOpen(true)} title="Open sidebar">
              <IconMenu />
            </button>
          )}
          <span className="cc-breadcrumb">
            CyberCore
            <span className="cc-breadcrumb-sep">/</span>
            <span className="cc-breadcrumb-cur">{breadcrumb}</span>
          </span>
        </div>

        {nav === 'overview' && !activeOrg
          ? <OverviewPage onNavigate={v => { setNav(v); setActiveOrg(null) }} />
          : (
            <div className="cc-main">
              {activeOrg
                ? <OrgDashboard
                    org={activeOrg}
                    currentUserId={user?.id}
                    onBack={() => setActiveOrg(null)}
                    onOrgChanged={updated => setActiveOrg(updated)}
                  />
                : <OrgsView onOpenOrg={setActiveOrg} />
              }
            </div>
          )
        }
      </div>
    </div>
  )
}
