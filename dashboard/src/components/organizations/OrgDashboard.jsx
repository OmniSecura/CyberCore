import { useState, useEffect, useCallback } from 'react'
import { orgApi, memberApi, inviteApi } from '../../api/endpoints'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtDate(iso) {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(iso))
}

function initials(name = '') {
  return name.split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase() || '?'
}

const ROLE_LABEL = { owner: 'Owner', admin: 'Admin', member: 'Member', viewer: 'Viewer' }

const canManageOrg     = (role) => role === 'owner'                                       // edit / delete / transfer
const canManageMembers = (role) => role === 'owner' || role === 'admin'                   // invite / change roles / remove

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
const IconTrash = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2.5 4h11M6 4V2.5h4V4M5 4l.7 9.2A1 1 0 0 0 6.7 14h2.6a1 1 0 0 0 1-.8L11 4"/>
  </svg>
)
const IconX = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <path d="M3 3l10 10M13 3L3 13"/>
  </svg>
)
const IconErr = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="8" cy="8" r="6"/><path d="M8 5v3M8 11v.5"/>
  </svg>
)
const IconOk = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 8.5l3 3 7-7"/>
  </svg>
)

// ─── Alert ────────────────────────────────────────────────────────────────────

function Alert({ type = 'err', children }) {
  return (
    <div className={`cc-alert cc-alert--${type === 'ok' ? 'ok' : 'err'}`}>
      {type === 'ok' ? <IconOk /> : <IconErr />}
      {children}
    </div>
  )
}

// ─── Confirm modal ────────────────────────────────────────────────────────────

function ConfirmModal({ title, message, confirmLabel, danger, onConfirm, onClose, loading }) {
  return (
    <div className="cc-overlay" onClick={e => e.target === e.currentTarget && !loading && onClose()}>
      <div className="cc-modal" role="dialog" aria-modal="true">
        <div className="cc-modal-head">
          <div>
            <div className="cc-modal-title">{title}</div>
            <div className="cc-modal-sub">{message}</div>
          </div>
          <button className="cc-modal-x" onClick={onClose} disabled={loading} aria-label="Close">
            <IconX />
          </button>
        </div>
        <div className="cc-modal-foot">
          <button className="cc-btn cc-btn-md cc-btn-ghost" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button
            className={`cc-btn cc-btn-md ${danger ? 'cc-btn-danger' : 'cc-btn-primary'}`}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading
              ? <><span className="cc-spin" style={danger ? { borderTopColor: '#C53030', borderColor: 'rgba(229,62,62,.25)' } : undefined} /> Working…</>
              : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Invite modal ─────────────────────────────────────────────────────────────

function InviteModal({ slug, onClose, onCreated }) {
  const [email, setEmail]     = useState('')
  const [role, setRole]       = useState('member')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  async function submit(e) {
    e.preventDefault()
    if (!email.trim()) return
    setLoading(true)
    setError(null)
    try {
      await inviteApi.create(slug, email.trim().toLowerCase(), role)
      onCreated()
    } catch (err) {
      if (err.status === 409) setError('This email is already a member or has a pending invite.')
      else if (err.status === 400) setError('Please enter a valid email address.')
      else setError(err?.data?.detail || 'Failed to send invite.')
      setLoading(false)
    }
  }

  return (
    <div className="cc-overlay" onClick={e => e.target === e.currentTarget && !loading && onClose()}>
      <div className="cc-modal" role="dialog" aria-modal="true">
        <div className="cc-modal-head">
          <div>
            <div className="cc-modal-title">Invite team member</div>
            <div className="cc-modal-sub">They'll receive an email with a link to join.</div>
          </div>
          <button className="cc-modal-x" onClick={onClose} disabled={loading} aria-label="Close">
            <IconX />
          </button>
        </div>
        <form onSubmit={submit}>
          <div className="cc-modal-body">
            {error && <Alert>{error}</Alert>}
            <div className="cc-mfield">
              <label htmlFor="inv-email">Email <span style={{ color: '#E53E3E' }}>*</span></label>
              <input
                id="inv-email" type="email"
                placeholder="colleague@company.com"
                value={email} onChange={e => setEmail(e.target.value)}
                autoFocus autoComplete="off"
              />
            </div>
            <div className="cc-mfield">
              <label htmlFor="inv-role">Role</label>
              <select
                id="inv-role"
                value={role} onChange={e => setRole(e.target.value)}
                className="cc-role-select"
                style={{ height: 42, fontSize: 14, padding: '0 32px 0 12px', borderRadius: 9, width: '100%' }}
              >
                <option value="admin">Admin — full access</option>
                <option value="member">Member — can manage members</option>
                <option value="viewer">Viewer — read only</option>
              </select>
            </div>
          </div>
          <div className="cc-modal-foot">
            <button type="button" className="cc-btn cc-btn-md cc-btn-ghost" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="cc-btn cc-btn-md cc-btn-primary" disabled={loading || !email.trim()}>
              {loading ? <><span className="cc-spin" /> Sending…</> : 'Send invite'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Overview tab ─────────────────────────────────────────────────────────────

function OverviewTab({ org }) {
  const plan = org.plan || 'free'

  const stats = [
    { label: 'Members', value: org.member_count ?? '—', note: ROLE_LABEL[org.role] ? `You: ${ROLE_LABEL[org.role]}` : '' },
    { label: 'Agents',  value: '0', note: 'Coming soon' },
    { label: 'Alerts',  value: '0', note: 'Coming soon' },
    { label: 'Logs',    value: '0', note: 'Coming soon' },
  ]

  return (
    <>
      <div className="cc-stats">
        {stats.map(s => (
          <div key={s.label} className="cc-stat-card">
            <div className="cc-stat-label">{s.label}</div>
            <div className="cc-stat-val">{s.value}</div>
            <div className="cc-stat-note">{s.note}</div>
          </div>
        ))}
      </div>

      <div className="cc-section">
        <div className="cc-section-head">Details</div>
        <div className="cc-info-row">
          <span className="cc-info-k">Name</span>
          <span className="cc-info-v">{org.organization_name}</span>
        </div>
        <div className="cc-info-row">
          <span className="cc-info-k">Slug</span>
          <span className="cc-info-v cc-info-v--mono">{org.organization_slug}</span>
        </div>
        <div className="cc-info-row">
          <span className="cc-info-k">Description</span>
          <span className={`cc-info-v${!org.organization_description ? ' cc-info-v--muted' : ''}`}>
            {org.organization_description || 'No description'}
          </span>
        </div>
        <div className="cc-info-row">
          <span className="cc-info-k">Plan</span>
          <span className="cc-info-v"><span className={`cc-badge cc-badge--${plan}`}>{plan}</span></span>
        </div>
        <div className="cc-info-row">
          <span className="cc-info-k">Status</span>
          <span className="cc-info-v">
            <span className={`cc-status${org.is_active ? ' cc-status--active' : ''}`}>
              <span className="cc-status-dot" />
              {org.is_active ? 'Active' : 'Inactive'}
            </span>
          </span>
        </div>
        <div className="cc-info-row">
          <span className="cc-info-k">Created</span>
          <span className="cc-info-v">{fmtDate(org.created_at)}</span>
        </div>
      </div>
    </>
  )
}

// ─── Members tab ─────────────────────────────────────────────────────────────

function MembersTab({ org, currentRole, ownerId, currentUserId }) {
  const [members, setMembers]     = useState([])
  const [invites, setInvites]     = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [showInvite, setShowInv]  = useState(false)
  const [confirmRm, setConfirmRm] = useState(null)
  const [confirmRevoke, setConfirmRevoke] = useState(null)
  const [busy, setBusy]           = useState(false)

  const canManage = canManageMembers(currentRole)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const mRes = await memberApi.list(org.organization_slug)
      setMembers(Array.isArray(mRes) ? mRes : [])

      if (canManage) {
        const iRes = await inviteApi.list(org.organization_slug)
        setInvites(Array.isArray(iRes) ? iRes : [])
      } else {
        setInvites([])
      }
    } catch (err) {
      setError(err?.data?.detail || 'Failed to load members.')
    } finally {
      setLoading(false)
    }
  }, [org.organization_slug, canManage])

  useEffect(() => { reload() }, [reload])

  async function changeRole(userId, newRole) {
    try {
      await memberApi.updateRole(org.organization_slug, userId, newRole)
      setMembers(prev => prev.map(m => m.user_id === userId ? { ...m, role: newRole } : m))
    } catch (err) {
      setError(err?.data?.detail || 'Failed to update role.')
    }
  }

  async function doRemove() {
    if (!confirmRm) return
    setBusy(true)
    try {
      await memberApi.remove(org.organization_slug, confirmRm.user_id)
      setMembers(prev => prev.filter(m => m.user_id !== confirmRm.user_id))
      setConfirmRm(null)
    } catch (err) {
      setError(err?.data?.detail || 'Failed to remove member.')
    } finally {
      setBusy(false)
    }
  }

  async function doRevoke() {
    if (!confirmRevoke) return
    setBusy(true)
    try {
      await inviteApi.revoke(org.organization_slug, confirmRevoke.id)
      setInvites(prev => prev.filter(i => i.id !== confirmRevoke.id))
      setConfirmRevoke(null)
    } catch (err) {
      setError(err?.data?.detail || 'Failed to revoke invite.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {error && <Alert>{error}</Alert>}

      <div className="cc-section">
        <div className="cc-section-head cc-section-head--row">
          <span>Members ({members.length + 1})</span>
          {canManage && (
            <button className="cc-btn cc-btn-sm cc-btn-primary" onClick={() => setShowInv(true)}>
              <IconPlus />
              Invite
            </button>
          )}
        </div>

        {loading ? (
          <div className="cc-empty cc-empty--inline">
            <span className="cc-skel" style={{ width: 200, height: 14, display: 'inline-block' }} />
          </div>
        ) : (
          <div className="cc-mlist">
            {/* Owner row — synthetic, always shown */}
            <div className="cc-mrow">
              <div className="cc-mrow-avatar">{initials('Owner')}</div>
              <div className="cc-mrow-main">
                <div className="cc-mrow-title">
                  {ownerId === currentUserId ? 'You' : 'Organization owner'}
                </div>
                <div className="cc-mrow-sub">{ownerId}</div>
              </div>
              <span className="cc-role-pill cc-role-owner">Owner</span>
            </div>

            {members.map(m => {
              const isSelf = m.user_id === currentUserId
              const youCanEditThis = canManage && !isSelf
              return (
                <div key={m.user_id} className="cc-mrow">
                  <div className="cc-mrow-avatar">{initials(m.user_id)}</div>
                  <div className="cc-mrow-main">
                    <div className="cc-mrow-title">
                      {isSelf ? 'You' : 'Member'}
                    </div>
                    <div className="cc-mrow-sub">{m.user_id}</div>
                  </div>
                  {youCanEditThis ? (
                    <select
                      className="cc-role-select"
                      value={m.role}
                      onChange={e => changeRole(m.user_id, e.target.value)}
                    >
                      <option value="admin">Admin</option>
                      <option value="member">Member</option>
                      <option value="viewer">Viewer</option>
                    </select>
                  ) : (
                    <span className={`cc-role-pill cc-role-${m.role}`}>
                      {ROLE_LABEL[m.role] || m.role}
                    </span>
                  )}
                  {(canManage || isSelf) && (
                    <button
                      className="cc-icon-danger"
                      onClick={() => setConfirmRm(m)}
                      title={isSelf ? 'Leave organization' : 'Remove member'}
                    >
                      <IconTrash />
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {canManage && (
        <div className="cc-section" style={{ marginTop: 16 }}>
          <div className="cc-section-head">Pending invites ({invites.length})</div>
          {loading ? null : invites.length === 0 ? (
            <div className="cc-empty cc-empty--inline">
              <div className="cc-empty-sub" style={{ margin: 0 }}>No pending invites.</div>
            </div>
          ) : (
            <div className="cc-mlist">
              {invites.map(inv => (
                <div key={inv.id} className="cc-mrow">
                  <div className="cc-mrow-avatar">{initials(inv.invited_email)}</div>
                  <div className="cc-mrow-main">
                    <div className="cc-mrow-title">{inv.invited_email}</div>
                    <div className="cc-mrow-sub">Expires {fmtDate(inv.expires_at)}</div>
                  </div>
                  <span className={`cc-role-pill cc-role-${inv.role}`}>
                    {ROLE_LABEL[inv.role] || inv.role}
                  </span>
                  <button
                    className="cc-icon-danger"
                    onClick={() => setConfirmRevoke(inv)}
                    title="Revoke invite"
                  >
                    <IconX />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {showInvite && (
        <InviteModal
          slug={org.organization_slug}
          onClose={() => setShowInv(false)}
          onCreated={() => { setShowInv(false); reload() }}
        />
      )}

      {confirmRm && (
        <ConfirmModal
          title={confirmRm.user_id === currentUserId ? 'Leave organization?' : 'Remove member?'}
          message={confirmRm.user_id === currentUserId
            ? 'You will lose access to this organization.'
            : 'This member will lose access to the organization.'}
          confirmLabel={confirmRm.user_id === currentUserId ? 'Leave' : 'Remove'}
          danger
          loading={busy}
          onConfirm={doRemove}
          onClose={() => setConfirmRm(null)}
        />
      )}

      {confirmRevoke && (
        <ConfirmModal
          title="Revoke invite?"
          message={`The invite to ${confirmRevoke.invited_email} will be canceled.`}
          confirmLabel="Revoke"
          danger
          loading={busy}
          onConfirm={doRevoke}
          onClose={() => setConfirmRevoke(null)}
        />
      )}
    </>
  )
}

// ─── Settings tab ─────────────────────────────────────────────────────────────

function SettingsTab({ org, currentRole, onUpdated, onDeleted }) {
  const canEdit = canManageOrg(currentRole)

  const [name, setName]   = useState(org.organization_name)
  const [slug, setSlug]   = useState(org.organization_slug)
  const [desc, setDesc]   = useState(org.organization_description || '')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg]     = useState(null)
  const [confirmDel, setConfirmDel] = useState(false)
  const [deleting, setDeleting]   = useState(false)

  if (!canEdit) {
    return (
      <div className="cc-section">
        <div className="cc-section-head">Settings</div>
        <div className="cc-empty cc-empty--inline">
          <div className="cc-empty-title">Owner only</div>
          <div className="cc-empty-sub">Only the organization owner can change settings or delete the organization.</div>
        </div>
      </div>
    )
  }

  async function save(e) {
    e.preventDefault()
    setSaving(true)
    setMsg(null)
    try {
      await orgApi.update(org.organization_slug, {
        organization_name: name.trim() !== org.organization_name ? name.trim() : undefined,
        organization_slug: slug.trim() !== org.organization_slug ? slug.trim() : undefined,
        organization_description: desc.trim() !== (org.organization_description || '') ? (desc.trim() || null) : undefined,
      })
      setMsg({ type: 'ok', text: 'Changes saved.' })
      onUpdated({
        ...org,
        organization_name: name.trim(),
        organization_slug: slug.trim(),
        organization_description: desc.trim() || null,
      })
    } catch (err) {
      setMsg({ type: 'err', text: err?.data?.detail || 'Failed to save changes.' })
    } finally {
      setSaving(false)
    }
  }

  async function doDelete() {
    setDeleting(true)
    try {
      await orgApi.remove(org.organization_slug)
      onDeleted()
    } catch (err) {
      setMsg({ type: 'err', text: err?.data?.detail || 'Failed to delete organization.' })
      setDeleting(false)
      setConfirmDel(false)
    }
  }

  return (
    <>
      <div className="cc-section">
        <div className="cc-section-head">General</div>
        <form onSubmit={save}>
          <div className="cc-form-grid">
            {msg && <Alert type={msg.type}>{msg.text}</Alert>}
            <div className="cc-mfield">
              <label htmlFor="s-name">Organization name</label>
              <input
                id="s-name" type="text" value={name}
                onChange={e => setName(e.target.value)}
                maxLength={80}
              />
            </div>
            <div className="cc-mfield">
              <label htmlFor="s-slug">Slug</label>
              <input
                id="s-slug" type="text" value={slug}
                onChange={e => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                maxLength={100}
              />
            </div>
            <div className="cc-mfield">
              <label htmlFor="s-desc">Description</label>
              <textarea
                id="s-desc" value={desc}
                onChange={e => setDesc(e.target.value)}
                rows={3} maxLength={400}
                placeholder="What does this organization do?"
              />
            </div>
          </div>
          <div className="cc-form-actions">
            <button
              type="submit"
              className="cc-btn cc-btn-md cc-btn-primary"
              disabled={saving || (
                name.trim() === org.organization_name &&
                slug.trim() === org.organization_slug &&
                desc.trim() === (org.organization_description || '')
              )}
            >
              {saving ? <><span className="cc-spin" /> Saving…</> : 'Save changes'}
            </button>
          </div>
        </form>
      </div>

      <div className="cc-section cc-section--danger" style={{ marginTop: 16 }}>
        <div className="cc-section-head">Danger zone</div>
        <div className="cc-form-grid">
          <p style={{ font: '400 13px/1.55 var(--font-body)', color: '#4A6080', margin: 0 }}>
            Deleting this organization removes access for all members and hides its workspace.
            This action can be reversed by reactivating the organization, but membership history may be lost.
          </p>
        </div>
        <div className="cc-form-actions">
          <button
            type="button"
            className="cc-btn cc-btn-md cc-btn-danger"
            onClick={() => setConfirmDel(true)}
          >
            Delete organization
          </button>
        </div>
      </div>

      {confirmDel && (
        <ConfirmModal
          title={`Delete "${org.organization_name}"?`}
          message="This will hide the organization for all members. Only the owner can reactivate it later."
          confirmLabel="Delete organization"
          danger
          loading={deleting}
          onConfirm={doDelete}
          onClose={() => setConfirmDel(false)}
        />
      )}
    </>
  )
}

// ─── OrgDashboard root ────────────────────────────────────────────────────────

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'members',  label: 'Members'  },
  { id: 'settings', label: 'Settings' },
]

export function OrgDashboard({ org: initialOrg, onBack, onOrgChanged, currentUserId }) {
  const [org, setOrg] = useState(initialOrg)
  const [tab, setTab] = useState('overview')
  const [fresh, setFresh] = useState(null)
  const [freshErr, setFreshErr] = useState(null)

  // Refetch org to get authoritative role + member_count
  useEffect(() => {
    let cancelled = false
    orgApi.get(initialOrg.organization_slug)
      .then(detail => {
        if (!cancelled) {
          setFresh(detail)
          setOrg(prev => ({ ...prev, ...detail }))
        }
      })
      .catch(err => {
        if (!cancelled) setFreshErr(err?.data?.detail || 'Failed to load organization details.')
      })
    return () => { cancelled = true }
  }, [initialOrg.organization_slug])

  const role = org.role || 'viewer'
  const plan = org.plan || 'free'

  function handleUpdated(updated) {
    setOrg(prev => ({ ...prev, ...updated }))
    onOrgChanged?.({ ...org, ...updated })
  }

  return (
    <div>
      <button className="cc-back" onClick={onBack}>
        <IconBack />
        Organizations
      </button>

      <div className="cc-org-head">
        <div className="cc-org-head-icon">{initials(org.organization_name)}</div>
        <div className="cc-org-head-info">
          <div className="cc-org-head-name">{org.organization_name}</div>
          <div className="cc-org-head-meta">
            <span className="cc-org-head-slug">{org.organization_slug}</span>
            <span className={`cc-badge cc-badge--${plan}`}>{plan}</span>
            <span className={`cc-role-pill cc-role-${role}`}>{ROLE_LABEL[role] || 'Viewer'}</span>
            <span className={`cc-status${org.is_active ? ' cc-status--active' : ''}`}>
              <span className="cc-status-dot" />
              {org.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>
      </div>

      <div className="cc-tabs" role="tablist">
        {TABS.filter(t => t.id !== 'settings' || canManageOrg(role)).map(t => (
          <button
            key={t.id}
            className={`cc-tab${tab === t.id ? ' cc-tab--on' : ''}`}
            onClick={() => setTab(t.id)}
            role="tab" aria-selected={tab === t.id}
          >
            {t.label}
          </button>
        ))}
      </div>

      {freshErr && <Alert>{freshErr}</Alert>}

      {tab === 'overview' && <OverviewTab org={org} />}
      {tab === 'members'  && (
        <MembersTab
          org={org}
          currentRole={role}
          ownerId={org.owner_id}
          currentUserId={currentUserId}
        />
      )}
      {tab === 'settings' && canManageOrg(role) && (
        <SettingsTab
          org={org}
          currentRole={role}
          onUpdated={handleUpdated}
          onDeleted={onBack}
        />
      )}
    </div>
  )
}
