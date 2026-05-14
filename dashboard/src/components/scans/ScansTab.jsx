import { useState, useEffect, useCallback, useRef } from 'react'
import { scanApi } from '../../api/endpoints'
import '../../styles/scans.css'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(iso) {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(new Date(iso))
}

function fmtDateShort(iso) {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(iso))
}

function fmtDuration(start, end) {
  const ms = new Date(end) - new Date(start)
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  return `${m}m ${s % 60}s`
}

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info']

// ─── Icons ────────────────────────────────────────────────────────────────────

const IconBack = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 3L5 8l5 5"/>
  </svg>
)
const IconPlus = () => (
  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
    <path d="M8 2v12M2 8h12"/>
  </svg>
)
const IconErr = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="8" cy="8" r="6"/><path d="M8 5v3M8 11v.5"/>
  </svg>
)
const IconX = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <path d="M3 3l10 10M13 3L3 13"/>
  </svg>
)
const IconTrash = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2.5 4h11M6 4V2.5h4V4M5 4l.7 9.2A1 1 0 0 0 6.7 14h2.6a1 1 0 0 0 1-.8L11 4"/>
  </svg>
)
const IconCancel = () => (
  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="8" cy="8" r="6"/><path d="M5.5 5.5l5 5M10.5 5.5l-5 5"/>
  </svg>
)
const IconRefresh = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M13.5 2.5v4h-4"/><path d="M2.5 8A5.5 5.5 0 0 1 13.1 5.4"/>
    <path d="M2.5 13.5v-4h4"/><path d="M13.5 8A5.5 5.5 0 0 1 2.9 10.6"/>
  </svg>
)
const IconScan = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="2" width="5" height="5" rx="1"/><rect x="9" y="2" width="5" height="5" rx="1"/>
    <rect x="2" y="9" width="5" height="5" rx="1"/>
    <path d="M9 11.5h4M11 9.5v4"/>
  </svg>
)
const IconChevron = ({ open }) => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"
    style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 150ms', flexShrink: 0 }}>
    <path d="M4 6l4 4 4-4"/>
  </svg>
)
const IconCode = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 4L1 8l4 4M11 4l4 4-4 4M9.5 2.5l-3 11"/>
  </svg>
)
const IconGit = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="5" cy="4" r="1.5"/><circle cx="11" cy="12" r="1.5"/><circle cx="11" cy="4" r="1.5"/>
    <path d="M5 5.5v5a1.5 1.5 0 0 0 1.5 1.5H9.5"/>
  </svg>
)
const IconZip = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 2h7l3 3v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z"/>
    <path d="M10 2v3h3M7 6v1M7 9v1M7 12v1M8 7h1v1H8zM8 10h1v1H8z"/>
  </svg>
)
const IconWarn = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M8 1.5l7 12H1z"/><path d="M8 6.5v3M8 12v.5"/>
  </svg>
)

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_META = {
  queued:    { label: 'Queued',    cls: 'sc-status--queued' },
  running:   { label: 'Running',   cls: 'sc-status--running' },
  completed: { label: 'Completed', cls: 'sc-status--completed' },
  failed:    { label: 'Failed',    cls: 'sc-status--failed' },
  cancelled: { label: 'Cancelled', cls: 'sc-status--cancelled' },
}

function StatusBadge({ status }) {
  const meta = STATUS_META[status] || { label: status, cls: '' }
  return (
    <span className={`sc-status ${meta.cls}`}>
      {status === 'running' && <span className="sc-status-pulse" />}
      {meta.label}
    </span>
  )
}

// ─── Severity badge ───────────────────────────────────────────────────────────

function SevBadge({ severity }) {
  const s = (severity || 'info').toLowerCase()
  return <span className={`sc-sev sc-sev--${s}`}>{s}</span>
}

// ─── Create scan modal ────────────────────────────────────────────────────────

const FREE_SCAN_LIMIT = 3

function CreateScanModal({ slug, plan, activeCount, onCreated, onClose }) {
  // scanType: 'sast' | 'dast' — top-level switch determines the rest of the form
  const [scanType, setScanType] = useState('sast')
  // SAST source: 'git' | 'zip'
  const [mode, setMode]       = useState('git')
  // DAST profile: 'passive' | 'active'
  const [profile, setProfile] = useState('passive')
  // DAST endpoint discovery: 'spider' | 'ajax_spider' | 'openapi'
  const [discoveryMode, setDiscoveryMode] = useState('spider')
  const [openapiUrl, setOpenapiUrl]       = useState('')
  // Multi-line textarea; we split on newlines when submitting so the user
  // can paste a list naturally.
  const [excludePaths, setExcludePaths]   = useState('')
  const [name, setName]       = useState('')
  const [url, setUrl]         = useState('')   // shared by SAST git-mode and DAST
  const [file, setFile]       = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr]         = useState(null)
  const fileRef               = useRef(null)

  const isFree       = plan === 'free'
  const limitReached = isFree && activeCount >= FREE_SCAN_LIMIT

  const canSubmit = !loading && !limitReached && name.trim() && (
    scanType === 'dast'
      ? (url.trim() && (discoveryMode !== 'openapi' || openapiUrl.trim()))
      : (mode === 'git' ? url.trim() : !!file)
  )

  async function submit(e) {
    e.preventDefault()
    if (!canSubmit) return
    setLoading(true); setErr(null)
    try {
      let job
      if (scanType === 'dast') {
        // Split the textarea on newlines AND commas — both feel natural and
        // there's no ambiguity since neither belongs in a URL path.
        const excludeList = excludePaths
          .split(/[\n,]/)
          .map(s => s.trim())
          .filter(Boolean)
        const payload = {
          name: name.trim(),
          target_url: url.trim(),
          profile,
          discovery_mode: discoveryMode,
          exclude_paths: excludeList,
        }
        if (discoveryMode === 'openapi') {
          payload.openapi_url = openapiUrl.trim()
        }
        job = await scanApi.submitWeb(slug, payload)
      } else if (mode === 'git') {
        job = await scanApi.submitGit(slug, { name: name.trim(), target_url: url.trim() })
      } else {
        job = await scanApi.submitUpload(slug, name.trim(), file)
      }
      onCreated(job)
    } catch (ex) {
      setErr(ex?.data?.detail || 'Failed to submit scan.')
      setLoading(false)
    }
  }

  // Switching scan type resets the inner mode/inputs so we don't carry over
  // a SAST git URL into a DAST form by accident.
  function pickScanType(t) {
    setScanType(t)
    setErr(null)
    setUrl('')
    setFile(null)
    setOpenapiUrl('')
    setExcludePaths('')
    setDiscoveryMode('spider')
    if (fileRef.current) fileRef.current.value = ''
  }

  function handleFile(e) {
    const f = e.target.files?.[0]
    if (!f) return
    if (!f.name.toLowerCase().endsWith('.zip')) {
      setErr('Only .zip files are accepted.')
      e.target.value = ''
      return
    }
    setErr(null)
    setFile(f)
  }

  return (
    <div className="cc-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="cc-modal sc-modal">
        {/* Header */}
        <div className="cc-modal-head">
          <div>
            <div className="cc-modal-title">
              New {scanType === 'dast' ? 'DAST' : 'SAST'} Scan
            </div>
            <div className="cc-modal-sub">
              {scanType === 'dast'
                ? 'Test a running web application for security issues'
                : 'Detect security vulnerabilities in your code'}
            </div>
          </div>
          <button className="cc-modal-x" onClick={onClose} type="button"><IconX /></button>
        </div>

        <form onSubmit={submit}>
          <div className="cc-modal-body">
            {/* Free plan limit warning */}
            {limitReached && (
              <div className="cc-alert sc-alert--warn">
                <IconWarn />
                <span>
                  Free plan limit reached — you can have at most {FREE_SCAN_LIMIT} active scans at once.
                  Wait for a running scan to finish or cancel one.
                </span>
              </div>
            )}

            {isFree && !limitReached && (
              <div className="sc-plan-note">
                <IconWarn />
                Free plan: {FREE_SCAN_LIMIT - activeCount} of {FREE_SCAN_LIMIT} concurrent scan slot{FREE_SCAN_LIMIT - activeCount !== 1 ? 's' : ''} available
              </div>
            )}

            {err && <div className="cc-alert cc-alert--err"><IconErr />{err}</div>}

            {/* Scan type selector — top-level choice between SAST and DAST */}
            <div className="sc-mode-tabs" style={{ marginBottom: 16 }}>
              <button
                type="button"
                className={`sc-mode-tab${scanType === 'sast' ? ' sc-mode-tab--on' : ''}`}
                onClick={() => pickScanType('sast')}
              >
                <IconCode /> SAST · Source code
              </button>
              <button
                type="button"
                className={`sc-mode-tab${scanType === 'dast' ? ' sc-mode-tab--on' : ''}`}
                onClick={() => pickScanType('dast')}
              >
                <IconScan /> DAST · Running app
              </button>
            </div>

            {/* SAST source-type tabs (git / zip) — only visible for SAST */}
            {scanType === 'sast' && (
              <div className="sc-mode-tabs">
                <button
                  type="button"
                  className={`sc-mode-tab${mode === 'git' ? ' sc-mode-tab--on' : ''}`}
                  onClick={() => { setMode('git'); setErr(null) }}
                >
                  <IconGit /> Git URL
                </button>
                <button
                  type="button"
                  className={`sc-mode-tab${mode === 'zip' ? ' sc-mode-tab--on' : ''}`}
                  onClick={() => { setMode('zip'); setErr(null) }}
                >
                  <IconZip /> ZIP Archive
                </button>
              </div>
            )}

            {/* Scan name */}
            <div className="cc-mfield">
              <label>Scan name</label>
              <input
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder={scanType === 'dast'
                  ? 'e.g. Production app — staging URL'
                  : 'e.g. Main branch — sprint 42'}
                required
                autoFocus
                disabled={limitReached}
              />
            </div>

            {/* DAST: target URL + profile */}
            {scanType === 'dast' && (
              <>
                <div className="cc-mfield">
                  <label>Target URL</label>
                  <input
                    value={url}
                    onChange={e => setUrl(e.target.value)}
                    placeholder="https://app.example.com"
                    required
                    disabled={limitReached}
                  />
                  <div style={{
                    font: '400 12px/1.4 var(--font-body)',
                    color: '#8899AA',
                    marginTop: 6,
                  }}>
                    Only scan applications you own or have written permission to test.
                  </div>
                </div>

                <div className="cc-mfield">
                  <label>Scan profile</label>
                  <div className="sc-mode-tabs" style={{ marginTop: 4 }}>
                    <button
                      type="button"
                      className={`sc-mode-tab${profile === 'passive' ? ' sc-mode-tab--on' : ''}`}
                      onClick={() => setProfile('passive')}
                      disabled={limitReached}
                    >
                      Passive (safe)
                    </button>
                    <button
                      type="button"
                      className={`sc-mode-tab${profile === 'active' ? ' sc-mode-tab--on' : ''}`}
                      onClick={() => setProfile('active')}
                      disabled={limitReached}
                    >
                      Active (sends attack payloads)
                    </button>
                  </div>
                  <div style={{
                    font: '400 12px/1.5 var(--font-body)',
                    color: '#8899AA',
                    marginTop: 8,
                  }}>
                    {profile === 'passive'
                      ? 'Crawls the app and inspects headers, cookies, TLS, and form structure. No attack payloads are sent.'
                      : 'In addition to the passive checks, ZAP will send real attack payloads (XSS, SQLi, command injection, SSRF, …) to discovered endpoints. Use only on apps you own.'}
                  </div>
                </div>

                {/* Discovery mode — how ZAP finds endpoints to scan */}
                <div className="cc-mfield">
                  <label>Endpoint discovery</label>
                  <div className="sc-mode-tabs" style={{ marginTop: 4 }}>
                    <button
                      type="button"
                      className={`sc-mode-tab${discoveryMode === 'spider' ? ' sc-mode-tab--on' : ''}`}
                      onClick={() => setDiscoveryMode('spider')}
                      disabled={limitReached}
                    >
                      Spider
                    </button>
                    <button
                      type="button"
                      className={`sc-mode-tab${discoveryMode === 'ajax_spider' ? ' sc-mode-tab--on' : ''}`}
                      onClick={() => setDiscoveryMode('ajax_spider')}
                      disabled={limitReached}
                    >
                      AJAX spider (SPA)
                    </button>
                    <button
                      type="button"
                      className={`sc-mode-tab${discoveryMode === 'openapi' ? ' sc-mode-tab--on' : ''}`}
                      onClick={() => setDiscoveryMode('openapi')}
                      disabled={limitReached}
                    >
                      OpenAPI
                    </button>
                  </div>
                  <div style={{
                    font: '400 12px/1.5 var(--font-body)',
                    color: '#8899AA',
                    marginTop: 8,
                  }}>
                    {discoveryMode === 'spider' && 'Classic HTTP crawler. Fast, but misses pages rendered by JavaScript.'}
                    {discoveryMode === 'ajax_spider' && 'Runs a headless browser to find routes in SPAs (React, Vue, Angular). ~5× slower than the regular spider.'}
                    {discoveryMode === 'openapi' && 'Imports an OpenAPI/Swagger spec from a URL — gives full API coverage without crawling.'}
                  </div>
                </div>

                {/* OpenAPI spec URL — only when openapi discovery is picked */}
                {discoveryMode === 'openapi' && (
                  <div className="cc-mfield">
                    <label>OpenAPI spec URL</label>
                    <input
                      value={openapiUrl}
                      onChange={e => setOpenapiUrl(e.target.value)}
                      placeholder="https://app.example.com/openapi.json"
                      required
                      disabled={limitReached}
                    />
                    <div style={{
                      font: '400 12px/1.4 var(--font-body)',
                      color: '#8899AA',
                      marginTop: 6,
                    }}>
                      FastAPI auto-publishes this at <code>/openapi.json</code>. Other frameworks may use <code>/swagger.json</code>.
                    </div>
                  </div>
                )}

                {/* Advanced: exclude paths */}
                <div className="cc-mfield">
                  <label>Exclude paths <span style={{ color: '#8899AA', fontWeight: 400 }}>(optional)</span></label>
                  <textarea
                    value={excludePaths}
                    onChange={e => setExcludePaths(e.target.value)}
                    placeholder={'/logout\n/admin/delete-*\n/users/me'}
                    rows={3}
                    disabled={limitReached}
                    style={{
                      width: '100%',
                      font: '400 13px/1.5 var(--font-mono)',
                      padding: '8px 10px',
                      border: '1px solid #D5DFEA',
                      borderRadius: 6,
                      resize: 'vertical',
                      background: '#fff',
                      color: '#0A1628',
                    }}
                  />
                  <div style={{
                    font: '400 12px/1.5 var(--font-body)',
                    color: '#8899AA',
                    marginTop: 6,
                  }}>
                    One pattern per line. Use <code>/path</code> or <code>/path/*</code> globs to keep destructive endpoints out of scope (especially important for active scans).
                  </div>
                </div>
              </>
            )}

            {/* Git URL mode (SAST only) */}
            {scanType === 'sast' && mode === 'git' && (
              <div className="cc-mfield">
                <label>Repository URL</label>
                <input
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                  placeholder="https://github.com/org/repo"
                  required
                  disabled={limitReached}
                />
              </div>
            )}

            {/* ZIP mode (SAST only) */}
            {scanType === 'sast' && mode === 'zip' && (
              <div className="cc-mfield">
                <label>ZIP archive</label>
                <div
                  className={`sc-dropzone${file ? ' sc-dropzone--has-file' : ''}`}
                  onClick={() => !limitReached && fileRef.current?.click()}
                  onDragOver={e => e.preventDefault()}
                  onDrop={e => {
                    e.preventDefault()
                    const f = e.dataTransfer.files?.[0]
                    if (f) {
                      if (!f.name.toLowerCase().endsWith('.zip')) {
                        setErr('Only .zip files are accepted.')
                      } else {
                        setErr(null); setFile(f)
                      }
                    }
                  }}
                >
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".zip"
                    style={{ display: 'none' }}
                    onChange={handleFile}
                  />
                  {file ? (
                    <>
                      <IconZip />
                      <div className="sc-dropzone-name">{file.name}</div>
                      <div className="sc-dropzone-size">{(file.size / 1024 / 1024).toFixed(1)} MB</div>
                      <button
                        type="button"
                        className="sc-dropzone-clear"
                        onClick={e => { e.stopPropagation(); setFile(null); fileRef.current.value = '' }}
                      ><IconX /></button>
                    </>
                  ) : (
                    <>
                      <IconZip />
                      <div className="sc-dropzone-label">Drop a .zip file here or click to browse</div>
                      <div className="sc-dropzone-hint">Source code archive (.zip only)</div>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="cc-modal-foot">
            <button type="button" className="cc-btn cc-btn-md cc-btn-ghost" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="cc-btn cc-btn-md cc-btn-primary" disabled={!canSubmit}>
              {loading ? <><span className="cc-spin" />Starting…</> : 'Start scan'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Scan list ────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20
const STATUS_FILTERS = ['queued', 'running', 'completed', 'failed', 'cancelled']

function ScanList({ slug, plan, has, onSelect }) {
  const [scans, setScans]           = useState([])
  const [total, setTotal]           = useState(0)
  const [activeCount, setActiveCount] = useState(0)
  const [loading, setLoading]       = useState(true)
  const [err, setErr]               = useState(null)
  const [page, setPage]             = useState(1)
  const [statusFilter, setFilter]   = useState(null)
  const [showCreate, setShowCreate] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    // Two calls instead of three: the dedicated /stats endpoint returns all
    // status counts in a single GROUP BY, replacing two extra list() calls
    // (each of which previously triggered the full auth + privilege + org
    // resolve chain — six inter-service hops dropped per refresh).
    Promise.all([
      scanApi.list(slug, { offset: (page - 1) * PAGE_SIZE, limit: PAGE_SIZE, status: statusFilter }),
      scanApi.stats(slug),
    ])
      .then(([main, stats]) => {
        setScans(main.items)
        setTotal(main.total)
        setActiveCount((stats.queued || 0) + (stats.running || 0))
        setLoading(false)
      })
      .catch(ex => { setErr(ex?.data?.detail || 'Failed to load scans.'); setLoading(false) })
  }, [slug, page, statusFilter])

  useEffect(() => { load() }, [load])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  function changeFilter(f) { setFilter(f); setPage(1) }

  return (
    <>
      <div className="cc-section-head--row" style={{ marginBottom: 16 }}>
        <div>
          <div style={{ font: '600 15px/1 var(--font-display)', color: '#0A1628' }}>Security Scans</div>
          <div style={{ font: '400 13px/1.5 var(--font-body)', color: '#8899AA', marginTop: 4 }}>
            Run SAST on source code or DAST on a live web target
          </div>
        </div>
        {has('scans.run') && (
          <button className="cc-btn cc-btn-md cc-btn-primary" onClick={() => setShowCreate(true)}>
            <IconPlus /> New Scan
          </button>
        )}
      </div>

      <div className="cc-toolbar">
        <div className="cc-filters">
          <button
            className={`cc-chip${!statusFilter ? ' cc-chip--on' : ''}`}
            onClick={() => changeFilter(null)}
          >All</button>
          {STATUS_FILTERS.map(s => (
            <button
              key={s}
              className={`cc-chip${statusFilter === s ? ' cc-chip--on' : ''}`}
              onClick={() => changeFilter(s)}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
        <button className="cc-icon-btn" onClick={load} title="Refresh" disabled={loading}>
          <IconRefresh />
        </button>
      </div>

      {err && <div className="cc-alert cc-alert--err"><IconErr />{err}</div>}

      {loading ? (
        <div className="cc-table-card">
          {[0, 1, 2].map(i => (
            <div key={i} style={{ padding: '16px 18px', borderBottom: '1px solid #E6EEF6', display: 'flex', gap: 12 }}>
              <span className="cc-skel" style={{ height: 14, width: '35%', display: 'block' }} />
              <span className="cc-skel" style={{ height: 14, width: '15%', display: 'block' }} />
              <span className="cc-skel" style={{ height: 14, width: '20%', display: 'block', marginLeft: 'auto' }} />
            </div>
          ))}
        </div>
      ) : scans.length === 0 ? (
        <div className="cc-table-card">
          <div className="cc-empty">
            <div className="cc-empty-icon"><IconScan /></div>
            <div className="cc-empty-title">No scans yet</div>
            <div className="cc-empty-sub">
              {has('scans.run')
                ? 'Start a scan to detect security vulnerabilities in your repositories.'
                : 'No scans have been run for this organization.'}
            </div>
            {has('scans.run') && (
              <button className="cc-btn cc-btn-md cc-btn-primary" onClick={() => setShowCreate(true)} style={{ marginTop: 4 }}>
                <IconPlus /> New Scan
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="cc-table-card">
          <table className="cc-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Status</th>
                <th>Target</th>
                <th>Findings</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {scans.map(scan => (
                <tr key={scan.id} onClick={() => onSelect(scan.id)}>
                  <td>
                    <div style={{ font: '500 14px/1.2 var(--font-body)', color: '#0A1628' }}>{scan.name}</div>
                    <div style={{ font: '400 11px/1 var(--font-mono)', color: '#8899AA', marginTop: 3 }}>
                      {scan.id.slice(0, 8)}…
                    </div>
                  </td>
                  <td><span className="sc-type-badge">{(scan.scan_type || 'sast').toUpperCase()}</span></td>
                  <td><StatusBadge status={scan.status} /></td>
                  <td>
                    <div className="sc-target-cell">
                      {scan.target_url || scan.target_path || '—'}
                    </div>
                  </td>
                  <td>
                    {scan.status === 'completed'
                      ? <span className={`sc-count${(scan.findings_count ?? 0) > 0 ? ' sc-count--warn' : ' sc-count--ok'}`}>
                          {scan.findings_count ?? 0}
                        </span>
                      : <span style={{ color: '#8899AA' }}>—</span>
                    }
                  </td>
                  <td style={{ font: '400 13px/1 var(--font-body)', color: '#8899AA', whiteSpace: 'nowrap' }}>
                    {fmtDateShort(scan.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {total > PAGE_SIZE && (
            <div className="cc-table-foot">
              <span>{total} scans total</span>
              <div className="cc-pager">
                <button className="cc-page-btn" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>‹</button>
                <span className="cc-page-info">{page} / {totalPages}</span>
                <button className="cc-page-btn" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>›</button>
              </div>
            </div>
          )}
        </div>
      )}

      {showCreate && (
        <CreateScanModal
          slug={slug}
          plan={plan}
          activeCount={activeCount}
          onClose={() => setShowCreate(false)}
          onCreated={job => { setShowCreate(false); onSelect(job.id) }}
        />
      )}
    </>
  )
}

// ─── Finding row (expandable) ─────────────────────────────────────────────────

function splitFilePath(filePath) {
  if (!filePath) return { dir: '', filename: '' }
  const normalized = filePath.replace(/\\/g, '/')
  const idx = normalized.lastIndexOf('/')
  if (idx === -1) return { dir: '', filename: normalized }
  return { dir: normalized.slice(0, idx + 1), filename: normalized.slice(idx + 1) }
}

function FindingRow({ finding }) {
  const [open, setOpen]       = useState(false)
  const [copied, setCopied]   = useState(false)
  const { dir, filename }     = splitFilePath(finding.file_path)

  function copyPath() {
    navigator.clipboard.writeText(finding.file_path || '').then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div className={`sc-finding${open ? ' sc-finding--open' : ''}`}>
      <button className="sc-finding-head" onClick={() => setOpen(o => !o)}>
        <SevBadge severity={finding.severity} />
        <span className="sc-finding-title">{finding.title || finding.rule_id}</span>
        <span className="sc-finding-file">
          {dir && <span className="sc-finding-fdir">{dir}</span>}
          <span className="sc-finding-fname">{filename || finding.file_path}</span>
          {finding.line_start != null && (
            <span className="sc-finding-line">:{finding.line_start}</span>
          )}
        </span>
        <IconChevron open={open} />
      </button>

      {open && (
        <div className="sc-finding-body">
          {/* Full path row */}
          <div className="sc-finding-path">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M2 3.5A1.5 1.5 0 013.5 2h2.379a1.5 1.5 0 011.06.44l.622.621A1.5 1.5 0 008.62 3.5H12.5A1.5 1.5 0 0114 5v7a1.5 1.5 0 01-1.5 1.5h-9A1.5 1.5 0 012 12.5v-9z"/>
            </svg>
            <span className="sc-finding-path-text">{finding.file_path}</span>
            {finding.line_start != null && (
              <span className="sc-finding-path-line">
                line {finding.line_start}
                {finding.line_end != null && finding.line_end !== finding.line_start
                  ? `–${finding.line_end}` : ''}
              </span>
            )}
            <button className="sc-copy-btn" onClick={copyPath} title="Copy path">
              {copied
                ? <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 8l3 3 7-7"/></svg>
                : <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="5" y="5" width="8" height="8" rx="1.5"/><path d="M3 11V3.5A1.5 1.5 0 014.5 2H11"/></svg>
              }
            </button>
          </div>

          {finding.message && <p className="sc-finding-msg">{finding.message}</p>}
          {finding.code_snippet && (
            <pre className="sc-code"><code>{finding.code_snippet}</code></pre>
          )}
          <div className="sc-finding-meta">
            {finding.rule_id    && <span className="sc-meta-tag"><b>Rule</b> {finding.rule_id}</span>}
            {finding.cwe        && <span className="sc-meta-tag"><b>CWE</b> {finding.cwe}</span>}
            {finding.owasp      && <span className="sc-meta-tag"><b>OWASP</b> {finding.owasp}</span>}
            {finding.confidence && <span className="sc-meta-tag"><b>Confidence</b> {finding.confidence}</span>}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Findings content ─────────────────────────────────────────────────────────

const FINDINGS_PAGE_SIZE = 100

function FindingsContent({ slug, jobId, scan }) {
  const [findings, setFindings]         = useState([])
  const [total, setTotal]               = useState(0)
  const [page, setPage]                 = useState(1)
  const [severityCounts, setSevCounts]  = useState({})
  const [loading, setLoading]           = useState(true)
  const [err, setErr]                   = useState(null)
  const [toolFilter, setToolFilter]     = useState(null)
  const [sevFilter, setSevFilter]       = useState(null)

  const isTerminal = scan.status === 'completed' || scan.status === 'failed'
  const totalPages = Math.max(1, Math.ceil(total / FINDINGS_PAGE_SIZE))

  // Reset to page 1 whenever filters change, otherwise we'd land on an empty
  // page when narrowing down.
  useEffect(() => { setPage(1) }, [toolFilter, sevFilter])

  useEffect(() => {
    if (!isTerminal) { setLoading(false); return }
    setLoading(true)
    scanApi
      .findings(slug, jobId, {
        offset: (page - 1) * FINDINGS_PAGE_SIZE,
        limit: FINDINGS_PAGE_SIZE,
        tool: toolFilter || undefined,
        severity: sevFilter || undefined,
      })
      .then(data => {
        setFindings(data.items)
        setTotal(data.total)
        setSevCounts(data.severity_counts || {})
        setLoading(false)
      })
      .catch(ex => { setErr(ex?.data?.detail || 'Failed to load findings.'); setLoading(false) })
  }, [slug, jobId, toolFilter, sevFilter, page, isTerminal])

  if (scan.status === 'queued' || scan.status === 'running') {
    return (
      <div className="cc-empty">
        <div className="sc-spin-wrap">
          <span className="sc-big-spin" />
        </div>
        <div className="cc-empty-title">Scan in progress…</div>
        <div className="cc-empty-sub">Findings will appear here once the scan completes.</div>
      </div>
    )
  }

  if (scan.status === 'cancelled') {
    return (
      <div className="cc-empty">
        <div className="cc-empty-icon"><IconCancel /></div>
        <div className="cc-empty-title">Scan cancelled</div>
        <div className="cc-empty-sub">No findings were collected.</div>
      </div>
    )
  }

  // Group by tool
  const byTool = {}
  for (const f of findings) {
    if (!byTool[f.tool]) byTool[f.tool] = []
    byTool[f.tool].push(f)
  }
  const tools = Object.keys(byTool)

  // Severity totals for the summary bar
  const hasCounts = SEVERITY_ORDER.some(s => severityCounts[s] > 0)

  return (
    <div>
      {/* Severity summary bar */}
      <div className="sc-sev-bar">
        {hasCounts ? (
          SEVERITY_ORDER.map(s => severityCounts[s] > 0 && (
            <button
              key={s}
              className={`sc-sev-chip sc-sev--${s}${sevFilter === s ? ' sc-sev-chip--on' : ''}`}
              onClick={() => setSevFilter(f => f === s ? null : s)}
            >
              <span className="sc-sev-chip-num">{severityCounts[s]}</span>
              {s}
            </button>
          ))
        ) : (
          !loading && (
            <span className="sc-sev-ok">✓ No findings</span>
          )
        )}
        {sevFilter && (
          <button className="sc-clear-filter" onClick={() => setSevFilter(null)}>
            <IconX /> Clear filter
          </button>
        )}
      </div>

      {/* Tool filter tabs — always visible when more than one tool present.
          The two filters are independent: severity narrows by severity AND
          tool narrows by tool, both applied server-side. */}
      {tools.length > 1 && (
        <div className="sc-tool-tabs">
          <button className={`sc-tool-tab${!toolFilter ? ' sc-tool-tab--on' : ''}`} onClick={() => setToolFilter(null)}>
            All <span className="sc-tool-count">{total}</span>
          </button>
          {tools.map(tool => (
            <button
              key={tool}
              className={`sc-tool-tab${toolFilter === tool ? ' sc-tool-tab--on' : ''}`}
              onClick={() => setToolFilter(t => t === tool ? null : tool)}
            >
              {tool} <span className="sc-tool-count">{byTool[tool].length}</span>
            </button>
          ))}
        </div>
      )}

      {err && <div className="cc-alert cc-alert--err"><IconErr />{err}</div>}

      {loading ? (
        <div style={{ padding: '24px 0', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[0, 1, 2].map(i => (
            <span key={i} className="cc-skel" style={{ height: 46, display: 'block', borderRadius: 8 }} />
          ))}
        </div>
      ) : findings.length === 0 ? (
        <div className="cc-empty cc-empty--inline">
          <div className="cc-empty-icon"><IconCode /></div>
          <div className="cc-empty-title" style={{ color: '#276749' }}>No findings</div>
          <div className="cc-empty-sub">
            {sevFilter
              ? `No ${sevFilter} severity findings.`
              : 'Great — no security issues were detected.'}
          </div>
        </div>
      ) : (
        /* When filtered by tool show flat list; otherwise group by tool */
        toolFilter || tools.length === 1 ? (
          <div className="sc-tool-section">
            <div className="sc-tool-head">
              <span className="sc-tool-name">{toolFilter || tools[0]}</span>
              <span className="sc-tool-badge">{findings.length} finding{findings.length !== 1 ? 's' : ''}</span>
            </div>
            {[...findings]
              .sort((a, b) => SEVERITY_ORDER.indexOf(a.severity?.toLowerCase()) - SEVERITY_ORDER.indexOf(b.severity?.toLowerCase()))
              .map(f => <FindingRow key={f.id} finding={f} />)
            }
          </div>
        ) : (
          tools.map(tool => (
            <div key={tool} className="sc-tool-section">
              <div className="sc-tool-head">
                <span className="sc-tool-name">{tool}</span>
                <span className="sc-tool-badge">{byTool[tool].length} finding{byTool[tool].length !== 1 ? 's' : ''}</span>
              </div>
              {[...byTool[tool]]
                .sort((a, b) => SEVERITY_ORDER.indexOf(a.severity?.toLowerCase()) - SEVERITY_ORDER.indexOf(b.severity?.toLowerCase()))
                .map(f => <FindingRow key={f.id} finding={f} />)
              }
            </div>
          ))
        )
      )}

      {!loading && total > FINDINGS_PAGE_SIZE && (
        <div className="cc-table-foot">
          <span>
            Showing {((page - 1) * FINDINGS_PAGE_SIZE + 1).toLocaleString()}–
            {Math.min(page * FINDINGS_PAGE_SIZE, total).toLocaleString()} of {total.toLocaleString()} findings
          </span>
          <div className="cc-pager">
            <button className="cc-page-btn" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>‹</button>
            <span className="cc-page-info">{page} / {totalPages}</span>
            <button className="cc-page-btn" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>›</button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Overview content ─────────────────────────────────────────────────────────

function OverviewContent({ scan }) {
  const steps = [
    { label: 'Queued',    time: scan.created_at,   done: true },
    { label: 'Running',   time: scan.started_at,   done: !!scan.started_at },
    {
      label: scan.status === 'failed' ? 'Failed' : scan.status === 'cancelled' ? 'Cancelled' : 'Completed',
      time: scan.completed_at,
      done: !!scan.completed_at,
      terminal: true,
    },
  ]

  const currentStep =
    scan.status === 'queued'    ? 0 :
    scan.status === 'running'   ? 1 : 2

  return (
    <div className="sc-overview-grid">
      {/* Left: timeline + target */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div className="cc-section">
          <div className="cc-section-head">Task Progress</div>
          <div className="sc-timeline">
            {steps.map((step, i) => {
              const isActive  = i === currentStep
              const isPast    = i < currentStep
              const isFail    = step.terminal && (scan.status === 'failed' || scan.status === 'cancelled')
              return (
                <div
                  key={i}
                  className={[
                    'sc-step',
                    isActive && !isFail ? 'sc-step--active' : '',
                    isPast              ? 'sc-step--done'   : '',
                    isFail && isActive  ? 'sc-step--fail'   : '',
                  ].filter(Boolean).join(' ')}
                >
                  <div className="sc-step-connector">
                    <div className="sc-step-dot" />
                    {i < steps.length - 1 && <div className="sc-step-line" />}
                  </div>
                  <div className="sc-step-info">
                    <div className="sc-step-label">{step.label}</div>
                    {step.time && <div className="sc-step-time">{fmtDate(step.time)}</div>}
                  </div>
                </div>
              )
            })}
          </div>

          {scan.error_message && (
            <div style={{ padding: '0 18px 14px' }}>
              <div className="cc-alert cc-alert--err" style={{ marginBottom: 0 }}>
                <IconErr />{scan.error_message}
              </div>
            </div>
          )}
        </div>

        <div className="cc-section">
          <div className="cc-section-head">Target</div>
          <div className="cc-info-row">
            <div className="cc-info-k">Source</div>
            <div className="cc-info-v">
              {scan.target_type === 'git_url'
                ? 'Git Repository'
                : scan.target_type === 'web_url'
                  ? 'Web Application'
                  : 'ZIP Upload'}
            </div>
          </div>
          {scan.target_url && (
            <div className="cc-info-row">
              <div className="cc-info-k">URL</div>
              <div className="cc-info-v cc-info-v--mono" style={{ wordBreak: 'break-all' }}>
                {scan.target_url}
              </div>
            </div>
          )}
          {scan.scan_type === 'dast' && scan.extra?.profile && (
            <div className="cc-info-row">
              <div className="cc-info-k">Profile</div>
              <div className="cc-info-v" style={{ textTransform: 'capitalize' }}>
                {scan.extra.profile}
              </div>
            </div>
          )}
          {scan.scan_type === 'dast' && scan.extra?.discovery_mode && (
            <div className="cc-info-row">
              <div className="cc-info-k">Discovery</div>
              <div className="cc-info-v">
                {scan.extra.discovery_mode === 'ajax_spider' ? 'AJAX spider (SPA)'
                  : scan.extra.discovery_mode === 'openapi' ? 'OpenAPI import'
                  : 'Spider'}
              </div>
            </div>
          )}
          {scan.scan_type === 'dast' && scan.extra?.openapi_url && (
            <div className="cc-info-row">
              <div className="cc-info-k">OpenAPI</div>
              <div className="cc-info-v cc-info-v--mono" style={{ wordBreak: 'break-all' }}>
                {scan.extra.openapi_url}
              </div>
            </div>
          )}
          {scan.scan_type === 'dast' && scan.extra?.exclude_paths?.length > 0 && (
            <div className="cc-info-row">
              <div className="cc-info-k">Excludes</div>
              <div className="cc-info-v cc-info-v--mono" style={{ fontSize: 12 }}>
                {scan.extra.exclude_paths.join(', ')}
              </div>
            </div>
          )}
          {scan.status === 'running' && scan.scan_type === 'dast' && scan.extra && (
            <div className="cc-info-row">
              <div className="cc-info-k">Phase</div>
              <div className="cc-info-v">
                <span style={{ textTransform: 'capitalize' }}>
                  {scan.extra.current_phase || 'starting'}
                </span>
                {typeof scan.extra.progress === 'number' && (
                  <span style={{ color: '#8899AA', marginLeft: 8 }}>
                    {scan.extra.progress}%
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right: metadata */}
      <div className="cc-section">
        <div className="cc-section-head">Details</div>
        <div className="cc-info-row">
          <div className="cc-info-k">Scan ID</div>
          <div className="cc-info-v cc-info-v--mono" style={{ fontSize: 11, wordBreak: 'break-all' }}>{scan.id}</div>
        </div>
        <div className="cc-info-row">
          <div className="cc-info-k">Type</div>
          <div className="cc-info-v"><span className="sc-type-badge">{(scan.scan_type || 'sast').toUpperCase()}</span></div>
        </div>
        <div className="cc-info-row">
          <div className="cc-info-k">Celery task</div>
          <div className="cc-info-v cc-info-v--mono" style={{ fontSize: 11, wordBreak: 'break-all' }}>
            {scan.celery_task_id || '—'}
          </div>
        </div>
        <div className="cc-info-row">
          <div className="cc-info-k">Queued</div>
          <div className="cc-info-v">{fmtDate(scan.created_at)}</div>
        </div>
        {scan.started_at && (
          <div className="cc-info-row">
            <div className="cc-info-k">Started</div>
            <div className="cc-info-v">{fmtDate(scan.started_at)}</div>
          </div>
        )}
        {scan.completed_at && (
          <div className="cc-info-row">
            <div className="cc-info-k">Finished</div>
            <div className="cc-info-v">{fmtDate(scan.completed_at)}</div>
          </div>
        )}
        {scan.started_at && scan.completed_at && (
          <div className="cc-info-row">
            <div className="cc-info-k">Duration</div>
            <div className="cc-info-v">{fmtDuration(scan.started_at, scan.completed_at)}</div>
          </div>
        )}
        {scan.status === 'completed' && (
          <div className="cc-info-row">
            <div className="cc-info-k">Findings</div>
            <div className="cc-info-v">
              <span className={`sc-count${(scan.findings_count ?? 0) > 0 ? ' sc-count--warn' : ' sc-count--ok'}`}>
                {scan.findings_count ?? 0}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Scan detail ──────────────────────────────────────────────────────────────

function ScanDetail({ slug, jobId, has, onBack }) {
  const [scan, setScan]           = useState(null)
  const [loading, setLoading]     = useState(true)
  const [err, setErr]             = useState(null)
  const [tab, setTab]             = useState('overview')
  const [cancelling, setCancelling] = useState(false)
  const [deleting, setDeleting]   = useState(false)
  const [confirmDel, setConfirmDel] = useState(false)
  const pollRef = useRef(null)

  const load = useCallback(() => {
    return scanApi.get(slug, jobId)
      .then(data => { setScan(data); setLoading(false) })
      .catch(ex => { setErr(ex?.data?.detail || 'Failed to load scan.'); setLoading(false) })
  }, [slug, jobId])

  useEffect(() => {
    load()
    return () => clearTimeout(pollRef.current)
  }, [load])

  // Poll while the scan is active, with exponential backoff capped at 15 s.
  // The old constant 3 s interval blasted the API throughout long-running
  // scans; backing off keeps short scans snappy and long ones cheap.
  useEffect(() => {
    clearTimeout(pollRef.current)
    if (!scan || (scan.status !== 'queued' && scan.status !== 'running')) return

    let cancelled = false
    let delay = 3000
    const MAX_DELAY = 15000

    const tick = () => {
      pollRef.current = setTimeout(async () => {
        if (cancelled) return
        try {
          const data = await scanApi.get(slug, jobId)
          if (cancelled) return
          setScan(data)
          if (data.status === 'queued' || data.status === 'running') {
            delay = Math.min(Math.round(delay * 1.5), MAX_DELAY)
            tick()
          }
        } catch {
          if (!cancelled) {
            delay = Math.min(Math.round(delay * 1.5), MAX_DELAY)
            tick()
          }
        }
      }, delay)
    }
    tick()

    return () => { cancelled = true; clearTimeout(pollRef.current) }
  }, [scan?.status, slug, jobId])

  async function doCancel() {
    setCancelling(true)
    try {
      const updated = await scanApi.cancel(slug, jobId)
      setScan(updated)
    } catch (ex) {
      alert(ex?.data?.detail || 'Failed to cancel scan.')
    } finally {
      setCancelling(false)
    }
  }

  async function doDelete() {
    setDeleting(true)
    try {
      await scanApi.remove(slug, jobId)
      onBack()
    } catch (ex) {
      alert(ex?.data?.detail || 'Failed to delete scan.')
      setDeleting(false)
      setConfirmDel(false)
    }
  }

  if (loading) return (
    <div style={{ padding: '48px 0', textAlign: 'center', color: '#8899AA', font: '400 13.5px/1 var(--font-body)' }}>
      Loading scan…
    </div>
  )
  if (err) return <div className="cc-alert cc-alert--err"><IconErr />{err}</div>
  if (!scan) return null

  const isActive = scan.status === 'queued' || scan.status === 'running'

  return (
    <div>
      <button className="cc-back" onClick={onBack}>
        <IconBack /> Scans
      </button>

      {/* Header */}
      <div className="sc-detail-head">
        <div className="sc-detail-icon">
          <IconScan />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="sc-detail-name">{scan.name}</div>
          <div className="sc-detail-meta">
            <StatusBadge status={scan.status} />
            <span className="sc-type-badge">{(scan.scan_type || 'sast').toUpperCase()}</span>
            {scan.target_url && (
              <span className="sc-detail-url">{scan.target_url}</span>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          {isActive && has('scans.manage') && (
            <button className="cc-btn cc-btn-md cc-btn-ghost" onClick={doCancel} disabled={cancelling}>
              {cancelling
                ? <span className="cc-spin" style={{ borderColor: 'rgba(74,96,128,.3)', borderTopColor: '#4A6080' }} />
                : <IconCancel />
              }
              Cancel
            </button>
          )}
          {!isActive && has('scans.manage') && (
            <button className="cc-btn cc-btn-md cc-btn-danger" onClick={() => setConfirmDel(true)} disabled={deleting}>
              Delete
            </button>
          )}
        </div>
      </div>

      {/* Sub-tabs */}
      <div className="cc-tabs">
        <button
          className={`cc-tab${tab === 'overview' ? ' cc-tab--on' : ''}`}
          onClick={() => setTab('overview')}
        >Overview</button>
        <button
          className={`cc-tab${tab === 'findings' ? ' cc-tab--on' : ''}`}
          onClick={() => setTab('findings')}
        >
          Findings
          {scan.status === 'completed' && scan.findings_count > 0 && (
            <span className="sc-tab-badge">{scan.findings_count}</span>
          )}
        </button>
      </div>

      {tab === 'overview' && <OverviewContent scan={scan} />}
      {tab === 'findings' && <FindingsContent slug={slug} jobId={jobId} scan={scan} />}

      {/* Delete confirm */}
      {confirmDel && (
        <div className="cc-overlay" onClick={e => e.target === e.currentTarget && setConfirmDel(false)}>
          <div className="cc-modal">
            <div className="cc-modal-head">
              <div>
                <div className="cc-modal-title">Delete scan?</div>
                <div className="cc-modal-sub">
                  This will permanently delete <strong>{scan.name}</strong> and all its findings.
                </div>
              </div>
              <button className="cc-modal-x" onClick={() => setConfirmDel(false)}><IconX /></button>
            </div>
            <div className="cc-modal-foot">
              <button className="cc-btn cc-btn-md cc-btn-ghost" onClick={() => setConfirmDel(false)} disabled={deleting}>
                Cancel
              </button>
              <button className="cc-btn cc-btn-md cc-btn-danger" onClick={doDelete} disabled={deleting}>
                {deleting
                  ? <span className="cc-spin" style={{ borderColor: 'rgba(197,48,48,.25)', borderTopColor: '#C53030' }} />
                  : null
                }
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── ScansTab (public export) ─────────────────────────────────────────────────

export function ScansTab({ org, has }) {
  const [selectedId, setSelectedId] = useState(null)

  if (selectedId) {
    return (
      <ScanDetail
        slug={org.organization_slug}
        jobId={selectedId}
        has={has}
        onBack={() => setSelectedId(null)}
      />
    )
  }

  return (
    <ScanList
      slug={org.organization_slug}
      plan={org.plan || 'free'}
      has={has}
      onSelect={setSelectedId}
    />
  )
}
