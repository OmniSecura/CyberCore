import { useState, useEffect, useCallback } from 'react'
import { apiKeyApi } from '../../api/endpoints'

// ─── Icons ────────────────────────────────────────────────────────────────────

const IconKey = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="6" r="3"/>
    <path d="M8.5 8.5L2 15h2v-2h2v-2h2"/>
  </svg>
)
const IconCopy = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <rect x="5" y="5" width="9" height="9" rx="1.5"/>
    <path d="M3 11V3.5A1.5 1.5 0 0 1 4.5 2H11"/>
  </svg>
)
const IconTrash = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2.5 4h11M6 4V2.5h4V4M5 4l.7 9.2A1 1 0 0 0 6.7 14h2.6a1 1 0 0 0 1-.8L11 4"/>
  </svg>
)
const IconPlus = () => (
  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
    <path d="M8 2v12M2 8h12"/>
  </svg>
)
const IconWarn = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M8 1.5l7 12H1z"/><path d="M8 6.5v3M8 12v.5"/>
  </svg>
)
const IconX = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <path d="M3 3l10 10M13 3L3 13"/>
  </svg>
)

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(iso) {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en', {
    month: 'short', day: 'numeric', year: 'numeric',
  }).format(new Date(iso))
}

function timeUntil(iso) {
  if (!iso) return 'Never expires'
  const ms = new Date(iso).getTime() - Date.now()
  if (ms <= 0) return 'Expired'
  const days = Math.floor(ms / 86_400_000)
  if (days >= 365) return `~${Math.floor(days / 365)}y left`
  if (days >= 30)  return `~${Math.floor(days / 30)}mo left`
  if (days >= 1)   return `${days}d left`
  return '<1d left'
}

// TTL presets surfaced to the user. Mapped to days.
const TTL_OPTIONS = [
  { id: 30,   label: '30 days' },
  { id: 90,   label: '90 days' },
  { id: 180,  label: '6 months' },
  { id: 365,  label: '1 year' },
  { id: 730,  label: '2 years' },
  { id: 0,    label: 'Never (not recommended)' },
]

// ─── Create modal ─────────────────────────────────────────────────────────────

function CreateKeyModal({ orgId, onClose, onCreated }) {
  const [name, setName]     = useState('')
  const [ttl, setTtl]       = useState(365)
  const [busy, setBusy]     = useState(false)
  const [err, setErr]       = useState(null)

  async function submit(e) {
    e.preventDefault()
    if (!name.trim()) return
    setBusy(true); setErr(null)
    try {
      const created = await apiKeyApi.create(orgId, {
        name: name.trim(),
        ttl_days: ttl,
      })
      onCreated(created)
    } catch (ex) {
      setErr(ex?.data?.detail || 'Failed to create API key.')
      setBusy(false)
    }
  }

  return (
    <div className="cc-overlay" onClick={e => e.target === e.currentTarget && !busy && onClose()}>
      <div className="cc-modal" role="dialog" aria-modal="true">
        <div className="cc-modal-head">
          <div>
            <div className="cc-modal-title">New API key</div>
            <div className="cc-modal-sub">
              Used by the <code>cyberlog</code> Python client to ship logs to this organization.
            </div>
          </div>
          <button className="cc-modal-x" onClick={onClose} disabled={busy} aria-label="Close"><IconX /></button>
        </div>

        <form onSubmit={submit} className="cc-modal-body">
          {err && (
            <div className="cc-alert cc-alert--err"><IconWarn />{err}</div>
          )}

          <div className="cc-mfield">
            <label htmlFor="ak-name">Label</label>
            <input
              id="ak-name" type="text" autoFocus
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="production, staging, ci…"
              maxLength={120}
              required
            />
            <div className="cc-mfield-hint">
              Free-form name shown in the dashboard. The key itself is generated automatically.
            </div>
          </div>

          <div className="cc-mfield">
            <label>Valid for</label>
            <div className="cc-ttl-grid">
              {TTL_OPTIONS.map(opt => (
                <button
                  type="button"
                  key={opt.id}
                  className={`cc-ttl-chip${ttl === opt.id ? ' cc-ttl-chip--on' : ''}`}
                  onClick={() => setTtl(opt.id)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <div className="cc-mfield-hint">
              When the key expires you'll need to generate a new one and update your client.
            </div>
          </div>
        </form>

        <div className="cc-modal-foot">
          <button className="cc-btn cc-btn-md cc-btn-ghost" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button className="cc-btn cc-btn-md cc-btn-primary"
            onClick={submit}
            disabled={busy || !name.trim()}
          >
            {busy ? <><span className="cc-spin" /> Creating…</> : 'Create key'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── One-time reveal modal ────────────────────────────────────────────────────

function RevealKeyModal({ created, onClose }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(created.plaintext_key)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* ignore — user can still copy manually */
    }
  }

  return (
    <div className="cc-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="cc-modal" role="dialog" aria-modal="true">
        <div className="cc-modal-head">
          <div>
            <div className="cc-modal-title">Save your new key</div>
            <div className="cc-modal-sub">
              This is the <strong>only time</strong> the full key will be shown. Store it somewhere safe — if you lose it you'll need to generate a new one.
            </div>
          </div>
        </div>

        <div className="cc-modal-body">
          <div className="cc-key-reveal">
            <code className="cc-key-reveal__code">{created.plaintext_key}</code>
            <button
              type="button"
              className="cc-key-reveal__copy"
              onClick={copy}
              title="Copy to clipboard"
            >
              <IconCopy />
              <span>{copied ? 'Copied!' : 'Copy'}</span>
            </button>
          </div>

          <div className="cc-alert cc-alert--warn" style={{ marginTop: 12 }}>
            <IconWarn />
            We've stored only a hashed version of this key. It cannot be recovered later.
          </div>

          <div style={{ marginTop: 16, font: '400 13px/1.55 var(--font-body)', color: '#4A6080' }}>
            Use it in your code:
            <pre className="cc-code">{`from cyberlog import CyberLogCore

log = CyberLogCore(
    api_key="${created.plaintext_key}",
    project="my-backend",
)`}</pre>
          </div>
        </div>

        <div className="cc-modal-foot">
          <button className="cc-btn cc-btn-md cc-btn-primary" onClick={onClose}>
            I've saved it — close
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Revoke confirm ───────────────────────────────────────────────────────────

function RevokeConfirm({ keyName, onCancel, onConfirm, loading }) {
  return (
    <div className="cc-overlay" onClick={e => e.target === e.currentTarget && !loading && onCancel()}>
      <div className="cc-modal" role="dialog" aria-modal="true">
        <div className="cc-modal-head">
          <div>
            <div className="cc-modal-title">Revoke "{keyName}"?</div>
            <div className="cc-modal-sub">
              Any client still using this key will stop being able to ship logs. This cannot be undone.
            </div>
          </div>
          <button className="cc-modal-x" onClick={onCancel} disabled={loading} aria-label="Close"><IconX /></button>
        </div>
        <div className="cc-modal-foot">
          <button className="cc-btn cc-btn-md cc-btn-ghost" onClick={onCancel} disabled={loading}>Cancel</button>
          <button className="cc-btn cc-btn-md cc-btn-danger" onClick={onConfirm} disabled={loading}>
            {loading ? <><span className="cc-spin" /> Revoking…</> : 'Revoke key'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Main section ─────────────────────────────────────────────────────────────

export function ApiKeysSection({ org }) {
  const orgId = org.id

  const [keys, setKeys]     = useState([])
  const [loading, setLoad]  = useState(true)
  const [err, setErr]       = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [reveal, setReveal]         = useState(null)   // CreateApiKeyResponse
  const [revokeTarget, setRevokeTarget] = useState(null) // ApiKeyResponse
  const [revoking, setRevoking]     = useState(false)

  const fetchKeys = useCallback(() => {
    setLoad(true); setErr(null)
    apiKeyApi.list(orgId)
      .then(setKeys)
      .catch(ex => setErr(ex?.data?.detail || 'Failed to load API keys.'))
      .finally(() => setLoad(false))
  }, [orgId])

  useEffect(() => { fetchKeys() }, [fetchKeys])

  function onCreated(created) {
    setShowCreate(false)
    setReveal(created)
    fetchKeys()
  }

  async function doRevoke() {
    setRevoking(true)
    try {
      await apiKeyApi.revoke(orgId, revokeTarget.id)
      setRevokeTarget(null)
      fetchKeys()
    } catch (ex) {
      setErr(ex?.data?.detail || 'Failed to revoke key.')
    } finally {
      setRevoking(false)
    }
  }

  const active = keys.filter(k => k.is_active)

  return (
    <div className="cc-section" style={{ marginTop: 16 }}>
      <div className="cc-section-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>API keys</span>
        <button className="cc-btn cc-btn-sm cc-btn-primary" onClick={() => setShowCreate(true)}>
          <IconPlus />
          New key
        </button>
      </div>

      <div className="cc-form-grid">
        <p style={{ font: '400 13px/1.55 var(--font-body)', color: '#4A6080', margin: 0 }}>
          API keys authenticate the <code>cyberlog</code> Python client when it ships
          logs to this organization. Keep them secret — anyone holding a valid key can write
          logs as you. You can keep multiple keys (e.g. one per environment) so a leaked one
          can be revoked without taking the others down.
        </p>

        {err && (
          <div className="cc-alert cc-alert--err"><IconWarn />{err}</div>
        )}

        {loading ? (
          <div className="cc-empty cc-empty--inline">
            <span className="cc-spin" /> Loading keys…
          </div>
        ) : keys.length === 0 ? (
          <div className="cc-empty cc-empty--inline">
            <div className="cc-empty-icon"><IconKey /></div>
            <div className="cc-empty-title">No API keys yet</div>
            <div className="cc-empty-sub">Generate one to start shipping logs from your projects.</div>
          </div>
        ) : (
          <div className="cc-table-card" style={{ marginTop: 4 }}>
            <table className="cc-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Key</th>
                  <th>Status</th>
                  <th>Last used</th>
                  <th>Expires</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {keys.map(k => {
                  const expired = k.expires_at && new Date(k.expires_at).getTime() <= Date.now()
                  return (
                    <tr key={k.id} className={(!k.is_active || expired) ? 'cc-row--inactive' : undefined}>
                      <td>
                        <div className="cc-org-cell">
                          <div className="cc-key-icon"><IconKey /></div>
                          <div>
                            <div className="cc-org-name">{k.name}</div>
                          </div>
                        </div>
                      </td>
                      <td><code style={{ fontSize: 12, color: '#4A6080' }}>{k.key_prefix}…</code></td>
                      <td>
                        {!k.is_active ? (
                          <span className="cc-status"><span className="cc-status-dot" /> Revoked</span>
                        ) : expired ? (
                          <span className="cc-status"><span className="cc-status-dot" /> Expired</span>
                        ) : (
                          <span className="cc-status cc-status--active"><span className="cc-status-dot" /> Active</span>
                        )}
                      </td>
                      <td style={{ color: '#8899AA', fontSize: 13 }}>{k.last_used_at ? fmtDate(k.last_used_at) : 'Never'}</td>
                      <td style={{ color: '#8899AA', fontSize: 13 }}>
                        {k.expires_at
                          ? <>{fmtDate(k.expires_at)}<br/><span style={{ fontSize: 11 }}>{timeUntil(k.expires_at)}</span></>
                          : 'Never'
                        }
                      </td>
                      <td style={{ color: '#8899AA', fontSize: 13 }}>{fmtDate(k.created_at)}</td>
                      <td>
                        {k.is_active && (
                          <button
                            className="cc-row-btn"
                            onClick={() => setRevokeTarget(k)}
                            title="Revoke key"
                          >
                            <IconTrash />
                            Revoke
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showCreate && (
        <CreateKeyModal
          orgId={orgId}
          onClose={() => setShowCreate(false)}
          onCreated={onCreated}
        />
      )}
      {reveal && (
        <RevealKeyModal created={reveal} onClose={() => setReveal(null)} />
      )}
      {revokeTarget && (
        <RevokeConfirm
          keyName={revokeTarget.name}
          loading={revoking}
          onCancel={() => setRevokeTarget(null)}
          onConfirm={doRevoke}
        />
      )}
    </div>
  )
}
