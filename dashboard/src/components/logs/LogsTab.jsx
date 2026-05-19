import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { logApi } from '../../api/endpoints'

// ─── Icons ────────────────────────────────────────────────────────────────────

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
const IconSearch = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="6.5" cy="6.5" r="4.5"/><path d="M10.5 10.5l3 3"/>
  </svg>
)
const IconList = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 4h10M3 8h7M3 12h5"/>
  </svg>
)
const IconClock = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="8" cy="8" r="6.2"/><path d="M8 4.5V8l2.4 1.5"/>
  </svg>
)
const IconDownload = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M8 2v8M4.5 7l3.5 3.5L11.5 7M2.5 13h11"/>
  </svg>
)
const IconX = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <path d="M3 3l10 10M13 3L3 13"/>
  </svg>
)
const IconHelp = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="8" cy="8" r="6.2"/>
    <path d="M6 6.2a2 2 0 1 1 2.6 1.9c-.4.2-.6.5-.6 1V9.5"/>
    <circle cx="8" cy="11.5" r=".5" fill="currentColor"/>
  </svg>
)

// ─── Constants ────────────────────────────────────────────────────────────────

const LEVELS = ['debug', 'info', 'warning', 'error', 'critical']

const LEVEL_COLOR = {
  debug:    { fg: '#64748B', bg: 'rgba(100,116,139,.18)' },
  info:     { fg: '#60A5FA', bg: 'rgba(96,165,250,.16)'  },
  warning:  { fg: '#FBBF24', bg: 'rgba(251,191,36,.16)'  },
  error:    { fg: '#F87171', bg: 'rgba(248,113,113,.18)' },
  critical: { fg: '#FFFFFF', bg: '#B91C1C'               },
}

const REFRESH_INTERVAL_MS = 5_000
const PAGE_SIZE = 200

// Time-range presets exposed as quick chips. Values are in seconds; `null`
// means "all time" — the server then receives no `since` parameter.
const TIME_RANGES = [
  { id: '15m', label: 'Last 15m',  seconds: 15 * 60 },
  { id: '1h',  label: 'Last 1h',   seconds: 60 * 60 },
  { id: '6h',  label: 'Last 6h',   seconds: 6 * 60 * 60 },
  { id: '24h', label: 'Last 24h',  seconds: 24 * 60 * 60 },
  { id: '7d',  label: 'Last 7d',   seconds: 7 * 24 * 60 * 60 },
  { id: 'all', label: 'All time',  seconds: null },
]

// ─── Splunk-ish query parser ──────────────────────────────────────────────────
//
// Accepts a single string and splits it into:
//   * `terms`   — key/value pairs like  level:error  project:my-backend
//   * `text`    — anything else, used for free-text matching against
//                 message / project / serialized fields.
//
// Quoting works:  message:"timeout while connecting"
// Negation works: -level:debug   |   NOT project:legacy
//
// The supported keys (`level`, `project`, `message`, plus any `field.<name>`)
// are documented in QUERY_HELP below.

const QUERY_KEYS = ['level', 'project', 'message', 'id']

function parseQuery(input) {
  const out = { terms: [], text: [] }
  if (!input) return out

  // Tokenise honouring "quoted strings".
  const tokens = []
  let buf = '', inQ = false
  for (let i = 0; i < input.length; i++) {
    const c = input[i]
    if (c === '"') { inQ = !inQ; buf += c; continue }
    if (!inQ && /\s/.test(c)) {
      if (buf) { tokens.push(buf); buf = '' }
    } else {
      buf += c
    }
  }
  if (buf) tokens.push(buf)

  for (let tok of tokens) {
    if (!tok) continue
    let negate = false
    if (tok.toUpperCase() === 'NOT') continue    // syntactic sugar — handled by next token
    if (tok.startsWith('-')) { negate = true; tok = tok.slice(1) }

    const m = tok.match(/^([a-zA-Z][a-zA-Z0-9_.]*):(.+)$/)
    if (m) {
      let [, key, val] = m
      // Strip surrounding quotes
      if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1)
      out.terms.push({ key, value: val, negate })
    } else {
      // Free text — also strip quotes
      let txt = tok
      if (txt.startsWith('"') && txt.endsWith('"')) txt = txt.slice(1, -1)
      out.text.push({ value: txt, negate })
    }
  }

  return out
}

function matchEntry(entry, q) {
  // Apply key/value terms first.
  for (const t of q.terms) {
    const v = String(t.value).toLowerCase()
    let actual = ''
    if (t.key === 'level')          actual = String(entry.level || '').toLowerCase()
    else if (t.key === 'project')   actual = String(entry.project || '').toLowerCase()
    else if (t.key === 'message')   actual = String(entry.message || '').toLowerCase()
    else if (t.key === 'id')        actual = String(entry.id || '').toLowerCase()
    else if (t.key.startsWith('field.')) {
      const name = t.key.slice('field.'.length)
      actual = String(entry.fields?.[name] ?? '').toLowerCase()
    } else {
      // Unknown key — treat as free text "key:value".
      const hay = JSON.stringify(entry).toLowerCase()
      const hit = hay.includes(`${t.key}:${v}`)
      if (hit === t.negate) return false
      continue
    }
    const hit = actual.includes(v)
    if (hit === t.negate) return false
  }

  // Then free-text fragments against message + project + serialised fields.
  if (q.text.length) {
    const hay = (
      (entry.message || '') + ' ' +
      (entry.project || '') + ' ' +
      JSON.stringify(entry.fields || {})
    ).toLowerCase()
    for (const t of q.text) {
      const v = t.value.toLowerCase()
      const hit = hay.includes(v)
      if (hit === t.negate) return false
    }
  }
  return true
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtTime(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString('en', { hour12: false }) +
           '.' + String(d.getMilliseconds()).padStart(3, '0')
  } catch { return iso }
}
function fmtDateTime(iso) {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false,
  }).format(new Date(iso))
}

function downloadJson(filename, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

// ─── Query help popover ───────────────────────────────────────────────────────

function QueryHelp({ onClose }) {
  return (
    <div className="cc-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="cc-modal cc-modal--lg" role="dialog" aria-modal="true">
        <div className="cc-modal-head">
          <div>
            <div className="cc-modal-title">Query syntax</div>
            <div className="cc-modal-sub">
              Search like in Splunk — combine key/value filters with free-text matching.
            </div>
          </div>
          <button className="cc-modal-x" onClick={onClose} aria-label="Close"><IconX /></button>
        </div>

        <div className="cc-modal-body">
          <h4 className="cc-help-h">Field filters</h4>
          <ul className="cc-help-list">
            <li><code>level:error</code> — match a level (debug, info, warning, error, critical).</li>
            <li><code>project:my-backend</code> — match a project name.</li>
            <li><code>message:"timeout while connecting"</code> — substring of the log message. Use quotes for phrases with spaces.</li>
            <li><code>id:8f3a…</code> — match an entry ID prefix.</li>
            <li><code>field.user_id:abc123</code> — any structured field passed to the client.</li>
          </ul>

          <h4 className="cc-help-h">Combining</h4>
          <ul className="cc-help-list">
            <li>Terms are joined with implicit AND. <code>level:error project:api</code> matches both.</li>
            <li>Free text matches against message, project, and fields. <code>timeout retry</code> finds entries containing both words anywhere.</li>
            <li>Prefix with <code>-</code> or <code>NOT</code> to negate. <code>-level:debug</code> hides debug entries.</li>
          </ul>

          <h4 className="cc-help-h">Examples</h4>
          <pre className="cc-code">{`level:error
level:warning project:scan-worker
field.order_id:xyz -level:debug
"connection refused"`}</pre>
        </div>

        <div className="cc-modal-foot">
          <button className="cc-btn cc-btn-md cc-btn-primary" onClick={onClose}>Got it</button>
        </div>
      </div>
    </div>
  )
}

// ─── Single log row ───────────────────────────────────────────────────────────

function LogRow({ entry, expanded, onToggle }) {
  const color = LEVEL_COLOR[entry.level] || LEVEL_COLOR.info
  const hasFields = entry.fields && Object.keys(entry.fields).length > 0

  return (
    <>
      <tr
        className={`cc-log-row${expanded ? ' cc-log-row--open' : ''}`}
        onClick={hasFields ? onToggle : undefined}
        style={{ cursor: hasFields ? 'pointer' : 'default' }}
      >
        <td className="cc-log-time">{fmtTime(entry.timestamp)}</td>
        <td>
          <span className="cc-log-level" style={{ color: color.fg, background: color.bg }}>
            {entry.level.toUpperCase()}
          </span>
        </td>
        <td className="cc-log-project">{entry.project}</td>
        <td className="cc-log-msg">
          {entry.message}
          {hasFields && (
            <span className="cc-log-tags">
              {Object.entries(entry.fields).slice(0, 4).map(([k, v]) => (
                <span key={k} className="cc-log-tag">
                  {k}=<em>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</em>
                </span>
              ))}
              {Object.keys(entry.fields).length > 4 && (
                <span className="cc-log-tag cc-log-tag--more">
                  +{Object.keys(entry.fields).length - 4} more
                </span>
              )}
            </span>
          )}
        </td>
      </tr>
      {expanded && hasFields && (
        <tr className="cc-log-expand">
          <td colSpan={4}>
            <pre className="cc-log-json">{JSON.stringify(entry.fields, null, 2)}</pre>
            <div className="cc-log-meta">
              Received {fmtDateTime(entry.ingested_at)} · id {entry.id}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

// ─── Main tab ─────────────────────────────────────────────────────────────────

export function LogsTab({ org }) {
  const orgId = org.id

  // Query + filters
  const [query, setQuery]         = useState('')
  const [timeRange, setTimeRange] = useState('1h')

  // Live mode (auto-refresh every 5s)
  const [live, setLive]           = useState(true)

  // Pagination — only when live is off.
  const [offset, setOffset]       = useState(0)

  // Data
  const [items, setItems]         = useState([])
  const [total, setTotal]         = useState(0)
  const [loading, setLoading]     = useState(true)
  const [refreshing, setRefr]     = useState(false)
  const [err, setErr]             = useState(null)
  const [expanded, setExpanded]   = useState(() => new Set())
  const [showHelp, setShowHelp]   = useState(false)

  // Latest-fetch guard.
  const reqIdRef = useRef(0)

  // Parse the query once whenever it changes — used for client-side filtering.
  const parsedQuery = useMemo(() => parseQuery(query), [query])

  // Server-side accelerators: if the query contains a single `level:` or
  // `project:` term, send it down so the DB does the heavy lifting before
  // client-side filtering kicks in.
  const serverHints = useMemo(() => {
    const find = (key) => {
      const matches = parsedQuery.terms.filter(t => t.key === key && !t.negate)
      return matches.length === 1 ? matches[0].value : undefined
    }
    return { level: find('level'), project: find('project') }
  }, [parsedQuery])

  const sinceIso = useMemo(() => {
    const range = TIME_RANGES.find(r => r.id === timeRange)
    if (!range || range.seconds == null) return undefined
    return new Date(Date.now() - range.seconds * 1000).toISOString()
  }, [timeRange])

  const fetchLogs = useCallback(async (soft = false) => {
    const myReq = ++reqIdRef.current
    if (soft) setRefr(true); else setLoading(true)
    setErr(null)
    try {
      const res = await logApi.list(orgId, {
        level:   LEVELS.includes(serverHints.level) ? serverHints.level : undefined,
        project: serverHints.project,
        since:   sinceIso,
        limit:   PAGE_SIZE,
        offset:  live ? 0 : offset,
      })
      if (myReq !== reqIdRef.current) return
      setItems(res.items || [])
      setTotal(res.total || 0)
    } catch (ex) {
      if (myReq !== reqIdRef.current) return
      setErr(ex?.data?.detail || 'Failed to load logs.')
    } finally {
      if (myReq === reqIdRef.current) { setLoading(false); setRefr(false) }
    }
  }, [orgId, serverHints, sinceIso, offset, live])

  useEffect(() => { fetchLogs(false) }, [fetchLogs])

  useEffect(() => {
    if (!live) return
    const t = setInterval(() => fetchLogs(true), REFRESH_INTERVAL_MS)
    return () => clearInterval(t)
  }, [live, fetchLogs])

  // Client-side filtering using the parsed query — applies on top of the
  // server-side level/project narrowing for free text, multi-term, and
  // field.* filters.
  const filtered = useMemo(() => {
    if (!parsedQuery.terms.length && !parsedQuery.text.length) return items
    return items.filter(e => matchEntry(e, parsedQuery))
  }, [items, parsedQuery])

  function toggleExpanded(id) {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  // Quick "click a level chip" — appends/toggles `level:<x>` in the query box.
  function toggleLevelInQuery(lvl) {
    const re = new RegExp(`(^|\\s)level:${lvl}(?=\\s|$)`, 'i')
    if (re.test(query)) {
      setQuery(query.replace(re, '').trim().replace(/\s+/g, ' '))
    } else {
      // Replace any existing level:* with the new one (mutually exclusive).
      const cleaned = query.replace(/(^|\s)level:[a-z]+/gi, '').trim()
      setQuery((cleaned ? cleaned + ' ' : '') + `level:${lvl}`)
    }
    setOffset(0)
  }

  const activeLevel = (() => {
    const m = query.match(/(?:^|\s)level:([a-z]+)/i)
    return m ? m[1].toLowerCase() : null
  })()

  function clearQuery() {
    setQuery('')
    setOffset(0)
  }

  function exportJson() {
    downloadJson(
      `${org.organization_slug || 'logs'}-${new Date().toISOString().slice(0,19).replace(/[:T]/g,'-')}.json`,
      filtered
    )
  }

  const totalPages   = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const currentPage  = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <>
      <div className="cc-section cc-logs-section">
        {/* ── Header row ───────────────────────────────────────────────── */}
        <div className="cc-logs-head">
          <div className="cc-logs-head__title">
            <span>Log stream</span>
            <span className="cc-logs-head__sub">
              {loading
                ? 'Loading…'
                : <>{total.toLocaleString()} event{total === 1 ? '' : 's'} · {filtered.length} shown</>}
            </span>
          </div>

          <div className="cc-logs-head__actions">
            <button
              type="button"
              className="cc-btn cc-btn-sm cc-btn-ghost"
              onClick={exportJson}
              disabled={filtered.length === 0}
              title="Download current view as JSON"
            >
              <IconDownload />
              Export
            </button>
            <button
              type="button"
              className={`cc-live-btn${live ? ' cc-live-btn--on' : ''}`}
              onClick={() => setLive(v => !v)}
              title={live ? 'Pause live refresh' : 'Resume live refresh'}
            >
              <span className="cc-live-dot" />
              {live ? 'LIVE' : 'PAUSED'}
            </button>
          </div>
        </div>

        {/* ── Query bar ────────────────────────────────────────────────── */}
        <div className="cc-logs-querybar">
          <div className="cc-logs-querybar__input">
            <IconSearch />
            <input
              type="text"
              placeholder="level:error project:my-backend &quot;timeout&quot;  — see syntax →"
              value={query}
              onChange={e => { setQuery(e.target.value); setOffset(0) }}
              spellCheck={false}
              autoCorrect="off"
              autoCapitalize="off"
            />
            {query && (
              <button className="cc-logs-querybar__clear" onClick={clearQuery} title="Clear query">
                <IconX />
              </button>
            )}
          </div>
          <button
            type="button"
            className="cc-btn cc-btn-sm cc-btn-ghost cc-logs-help"
            onClick={() => setShowHelp(true)}
            title="Query syntax"
          >
            <IconHelp />
            Syntax
          </button>
          <button
            type="button"
            className="cc-icon-btn"
            onClick={() => fetchLogs(true)}
            disabled={refreshing || loading}
            title="Refresh"
          >
            <IconReload spinning={refreshing} />
          </button>
        </div>

        {/* ── Filter chips ─────────────────────────────────────────────── */}
        <div className="cc-logs-filters">
          <div className="cc-logs-filters__group">
            <span className="cc-logs-filters__label">Level</span>
            {LEVELS.map(l => {
              const c = LEVEL_COLOR[l]
              const on = activeLevel === l
              return (
                <button
                  key={l}
                  type="button"
                  className={`cc-level-chip${on ? ' cc-level-chip--on' : ''}`}
                  style={on ? { color: c.fg, background: c.bg, borderColor: c.fg + '55' } : undefined}
                  onClick={() => toggleLevelInQuery(l)}
                >
                  {l}
                </button>
              )
            })}
          </div>

          <div className="cc-logs-filters__group">
            <span className="cc-logs-filters__label"><IconClock /> Time</span>
            {TIME_RANGES.map(r => (
              <button
                key={r.id}
                type="button"
                className={`cc-chip${timeRange === r.id ? ' cc-chip--on' : ''}`}
                onClick={() => { setTimeRange(r.id); setOffset(0) }}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        {err && (
          <div className="cc-alert cc-alert--err" style={{ marginTop: 8 }}>{err}</div>
        )}

        {/* ── Table ────────────────────────────────────────────────────── */}
        <div className="cc-table-card cc-logs-card">
          <table className="cc-table cc-logs-table">
            <thead>
              <tr>
                <th style={{ width: 110 }}>Time</th>
                <th style={{ width: 80 }}>Level</th>
                <th style={{ width: 160 }}>Project</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {loading && items.length === 0 ? (
                <tr><td colSpan={4} style={{ padding: 0 }}>
                  <div className="cc-empty"><span className="cc-spin" /> Loading logs…</div>
                </td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={4} style={{ padding: 0 }}>
                  <div className="cc-empty">
                    <div className="cc-empty-icon"><IconList /></div>
                    <div className="cc-empty-title">
                      {total === 0 ? 'No logs yet' : 'No matches'}
                    </div>
                    <div className="cc-empty-sub">
                      {total === 0
                        ? 'Once your apps start sending logs with the cyberlog client, they\'ll show up here in real time.'
                        : 'Adjust the query, level filter, or time range to widen the search.'}
                    </div>
                  </div>
                </td></tr>
              ) : (
                filtered.map(entry => (
                  <LogRow
                    key={entry.id}
                    entry={entry}
                    expanded={expanded.has(entry.id)}
                    onToggle={() => toggleExpanded(entry.id)}
                  />
                ))
              )}
            </tbody>
          </table>

          {!loading && total > 0 && (
            <div className="cc-table-foot">
              <span>
                {live
                  ? <>Showing latest {filtered.length} of {total} events · auto-refresh every 5 s</>
                  : <>Page {currentPage} of {totalPages} · {total} total</>}
              </span>
              {!live && totalPages > 1 && (
                <div className="cc-pager">
                  <button className="cc-page-btn"
                    onClick={() => setOffset(o => Math.max(0, o - PAGE_SIZE))}
                    disabled={offset <= 0 || refreshing}>Newer</button>
                  <span className="cc-page-info">Page {currentPage}/{totalPages}</span>
                  <button className="cc-page-btn"
                    onClick={() => setOffset(o => o + PAGE_SIZE)}
                    disabled={offset + PAGE_SIZE >= total || refreshing}>Older</button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {showHelp && <QueryHelp onClose={() => setShowHelp(false)} />}
    </>
  )
}
