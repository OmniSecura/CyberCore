import { useState, useEffect, useCallback } from 'react'
import { orgApi, memberApi, inviteApi, userApi, roleApi } from '../../api/endpoints'
import { TransferOwnershipModal } from './TransferOwnershipModal'
import { ScansTab } from '../scans/ScansTab'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtDate(iso) {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(iso))
}

function initials(name = '') {
  return name
    .split(/[\s@._-]/)
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0])
    .join('')
    .toUpperCase() || '?'
}

// Compact member/owner row used by MembersTab.
function MemberRow({ displayName, email, avatarSeed, roleSlot, actionSlot }) {
  return (
    <div className="cc-mrow">
      <div className="cc-mrow-avatar">{initials(avatarSeed || displayName)}</div>
      <div className="cc-mrow-main">
        <div className="cc-mrow-title">{displayName}</div>
        {email && <div className="cc-mrow-sub">{email}</div>}
      </div>
      {roleSlot}
      {actionSlot}
    </div>
  )
}

const ROLE_LABEL = { owner: 'Owner', admin: 'Admin', member: 'Member', viewer: 'Viewer' }

const canManageOrg = (role) => role === 'owner'

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
const IconWarn = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M8 1.5l7 12H1z"/><path d="M8 6.5v3M8 12v.5"/>
  </svg>
)
const IconPower = () => (
  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
    <path d="M8 1.5v6"/><path d="M11.5 3.5a5 5 0 1 1-7 0"/>
  </svg>
)
const IconEdit = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 2l3 3-8 8H3v-3z"/>
  </svg>
)
const IconShield = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M8 1.5L2 4v4c0 3.5 2.7 5.8 6 6.5 3.3-.7 6-3 6-6.5V4z"/>
  </svg>
)

// ─── Inactive banner ──────────────────────────────────────────────────────────

function InactiveBanner({ org, role, onReactivated }) {
  const [busy, setBusy]   = useState(false)
  const [error, setError] = useState(null)
  const isOwner = role === 'owner'

  async function reactivate() {
    setBusy(true)
    setError(null)
    try {
      await orgApi.reactivate(org.id)
      onReactivated()
    } catch (err) {
      setError(err?.data?.detail || 'Failed to reactivate organization.')
      setBusy(false)
    }
  }

  return (
    <>
      <div className="cc-banner">
        <div className="cc-banner__icon"><IconWarn /></div>
        <div className="cc-banner__body">
          <div className="cc-banner__title">This organization is inactive</div>
          <div className="cc-banner__sub">
            {isOwner
              ? 'Members can no longer be invited and integrations are paused. You can reactivate it at any time.'
              : 'The owner deactivated this workspace. Some actions are unavailable until it is reactivated.'}
          </div>
        </div>
        {isOwner && (
          <button className="cc-btn cc-btn-md cc-btn-primary" onClick={reactivate} disabled={busy}>
            {busy ? <><span className="cc-spin" /> Reactivating…</> : <><IconPower /> Reactivate</>}
          </button>
        )}
      </div>
      {error && <Alert>{error}</Alert>}
    </>
  )
}

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

// ─── Role modal (create / edit) ───────────────────────────────────────────────

function RoleModal({ slug, existing, privilegeGroups, onClose, onSaved }) {
  const [name, setName]           = useState(existing?.name || '')
  const [desc, setDesc]           = useState(existing?.description || '')
  const [color, setColor]         = useState(existing?.color || '#3B82F6')
  const [selected, setSelected]   = useState(new Set(existing?.privileges || []))
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)

  function togglePrivilege(key) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  function toggleGroup(keys) {
    const allOn = keys.every(k => selected.has(k))
    setSelected(prev => {
      const next = new Set(prev)
      keys.forEach(k => allOn ? next.delete(k) : next.add(k))
      return next
    })
  }

  async function submit(e) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    setError(null)
    const payload = {
      name: name.trim(),
      description: desc.trim() || null,
      color: color || null,
      privileges: [...selected],
    }
    try {
      if (existing) {
        await roleApi.update(slug, existing.id, payload)
      } else {
        await roleApi.create(slug, payload)
      }
      onSaved()
    } catch (err) {
      if (err?.status === 409) setError('A role with that name already exists.')
      else setError(err?.data?.detail || 'Failed to save role.')
      setLoading(false)
    }
  }

  return (
    <div className="cc-overlay" onClick={e => e.target === e.currentTarget && !loading && onClose()}>
      <div className="cc-modal cc-modal--wide" role="dialog" aria-modal="true">
        <div className="cc-modal-head">
          <div>
            <div className="cc-modal-title">{existing ? 'Edit role' : 'Create custom role'}</div>
            <div className="cc-modal-sub">Choose a name and select which privileges members with this role will have.</div>
          </div>
          <button className="cc-modal-x" onClick={onClose} disabled={loading} aria-label="Close"><IconX /></button>
        </div>
        <form onSubmit={submit}>
          <div className="cc-modal-body">
            {error && <Alert>{error}</Alert>}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, alignItems: 'end' }}>
              <div className="cc-mfield">
                <label htmlFor="role-name">Role name <span style={{ color: '#E53E3E' }}>*</span></label>
                <input
                  id="role-name" type="text" value={name}
                  onChange={e => setName(e.target.value)}
                  maxLength={100} autoFocus autoComplete="off"
                  placeholder="e.g. Security Analyst"
                />
              </div>
              <div className="cc-mfield" style={{ minWidth: 56 }}>
                <label htmlFor="role-color">Color</label>
                <input
                  id="role-color" type="color" value={color}
                  onChange={e => setColor(e.target.value)}
                  style={{ height: 42, width: 56, padding: 4, borderRadius: 9, border: '1.5px solid var(--border)', cursor: 'pointer', background: 'var(--bg)' }}
                />
              </div>
            </div>

            <div className="cc-mfield">
              <label htmlFor="role-desc">Description</label>
              <input
                id="role-desc" type="text" value={desc}
                onChange={e => setDesc(e.target.value)}
                maxLength={200} placeholder="What is this role for?"
              />
            </div>

            <div style={{ marginTop: 8 }}>
              <div style={{ font: '500 12px/1 var(--font-body)', color: 'var(--fg-2)', marginBottom: 10, letterSpacing: '.01em' }}>
                Privileges ({selected.size} selected)
              </div>
              <div className="cc-priv-groups">
                {privilegeGroups.map(({ group, privileges }) => {
                  const keys = privileges.map(p => p.key)
                  const allOn = keys.every(k => selected.has(k))
                  const someOn = keys.some(k => selected.has(k))
                  return (
                    <div key={group} className="cc-priv-group">
                      <div className="cc-priv-group-head">
                        <label className="cc-priv-check">
                          <input
                            type="checkbox"
                            checked={allOn}
                            ref={el => { if (el) el.indeterminate = !allOn && someOn }}
                            onChange={() => toggleGroup(keys)}
                          />
                          <span className="cc-priv-group-name">{group}</span>
                        </label>
                      </div>
                      <div className="cc-priv-list">
                        {privileges.map(p => (
                          <label key={p.key} className="cc-priv-check cc-priv-item">
                            <input
                              type="checkbox"
                              checked={selected.has(p.key)}
                              onChange={() => togglePrivilege(p.key)}
                            />
                            <span>{p.label}</span>
                            <span className="cc-priv-key">{p.key}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
          <div className="cc-modal-foot">
            <button type="button" className="cc-btn cc-btn-md cc-btn-ghost" onClick={onClose} disabled={loading}>Cancel</button>
            <button type="submit" className="cc-btn cc-btn-md cc-btn-primary" disabled={loading || !name.trim()}>
              {loading ? <><span className="cc-spin" /> Saving…</> : (existing ? 'Save changes' : 'Create role')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Roles tab ────────────────────────────────────────────────────────────────

function RolesTab({ org, has }) {
  const [roles, setRoles]                 = useState([])
  const [privilegeGroups, setPrivGroups]  = useState([])
  const [loading, setLoading]             = useState(true)
  const [error, setError]                 = useState(null)
  const [showCreate, setShowCreate]       = useState(false)
  const [editingRole, setEditingRole]     = useState(null)
  const [confirmDel, setConfirmDel]       = useState(null)
  const [deleting, setDeleting]           = useState(false)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [rolesRes, privRes] = await Promise.all([
        roleApi.list(org.organization_slug),
        roleApi.listPrivileges(),
      ])
      setRoles(Array.isArray(rolesRes) ? rolesRes : [])
      setPrivGroups(Array.isArray(privRes) ? privRes : [])
    } catch (err) {
      setError(err?.data?.detail || 'Failed to load roles.')
    } finally {
      setLoading(false)
    }
  }, [org.organization_slug])

  useEffect(() => { reload() }, [reload])

  async function doDelete() {
    if (!confirmDel) return
    setDeleting(true)
    try {
      await roleApi.remove(org.organization_slug, confirmDel.id)
      setRoles(prev => prev.filter(r => r.id !== confirmDel.id))
      setConfirmDel(null)
    } catch (err) {
      setError(err?.data?.detail || 'Failed to delete role.')
    } finally {
      setDeleting(false)
    }
  }

  const totalPrivileges = privilegeGroups.reduce((n, g) => n + g.privileges.length, 0)

  return (
    <>
      {error && <Alert>{error}</Alert>}

      <div className="cc-section">
        <div className="cc-section-head cc-section-head--row">
          <span>Custom roles ({roles.length})</span>
          {has('roles.manage') && (
            <button className="cc-btn cc-btn-sm cc-btn-primary" onClick={() => setShowCreate(true)}>
              <IconPlus /> New role
            </button>
          )}
        </div>

        {loading ? (
          <div className="cc-empty cc-empty--inline">
            <span className="cc-skel" style={{ width: 200, height: 14, display: 'inline-block' }} />
          </div>
        ) : roles.length === 0 ? (
          <div className="cc-empty cc-empty--inline">
            <div className="cc-empty-title">No custom roles yet</div>
            <div className="cc-empty-sub">Create roles to give members fine-grained access to specific features.</div>
          </div>
        ) : (
          <div className="cc-role-list">
            {roles.map(role => (
              <div key={role.id} className="cc-role-card">
                <div className="cc-role-card-head">
                  <span
                    className="cc-role-dot"
                    style={{ background: role.color || '#8899AA' }}
                  />
                  <span className="cc-role-card-name">{role.name}</span>
                  <span className="cc-role-card-count">
                    {role.privileges.length}/{totalPrivileges} privileges
                  </span>
                  {has('roles.manage') && (
                    <div className="cc-role-card-actions">
                      <button
                        className="cc-icon-btn"
                        onClick={() => setEditingRole(role)}
                        title="Edit role"
                      >
                        <IconEdit />
                      </button>
                      <button
                        className="cc-icon-danger"
                        onClick={() => setConfirmDel(role)}
                        title="Delete role"
                      >
                        <IconTrash />
                      </button>
                    </div>
                  )}
                </div>
                {role.description && (
                  <div className="cc-role-card-desc">{role.description}</div>
                )}
                {role.privileges.length > 0 && (
                  <div className="cc-role-card-privs">
                    {role.privileges.map(p => (
                      <span key={p} className="cc-priv-tag">{p}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="cc-section" style={{ marginTop: 16 }}>
        <div className="cc-section-head">Available privileges</div>
        <div style={{ font: '400 13px/1.55 var(--font-body)', color: 'var(--fg-2)', padding: '10px 18px 0' }}>
          {totalPrivileges} privileges across {privilegeGroups.length} categories.
          New feature privileges (e.g. Scans, Alerts) appear here automatically when added to the system.
        </div>
        <div className="cc-priv-readonly-groups">
          {privilegeGroups.map(({ group, privileges }) => (
            <div key={group} className="cc-priv-readonly-group">
              <div className="cc-priv-readonly-head">{group}</div>
              {privileges.map(p => (
                <div key={p.key} className="cc-priv-readonly-row">
                  <span className="cc-priv-readonly-label">{p.label}</span>
                  <span className="cc-priv-key">{p.key}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {has('roles.manage') && (showCreate || editingRole) && (
        <RoleModal
          slug={org.organization_slug}
          existing={editingRole}
          privilegeGroups={privilegeGroups}
          onClose={() => { setShowCreate(false); setEditingRole(null) }}
          onSaved={() => { setShowCreate(false); setEditingRole(null); reload() }}
        />
      )}

      {confirmDel && (
        <ConfirmModal
          title={`Delete role "${confirmDel.name}"?`}
          message="Members assigned this role will revert to their base role (Member). This cannot be undone."
          confirmLabel="Delete role"
          danger
          loading={deleting}
          onConfirm={doDelete}
          onClose={() => setConfirmDel(null)}
        />
      )}
    </>
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

function MembersTab({ org, currentRole, ownerId, currentUserId, has }) {
  const [members, setMembers]         = useState([])
  const [ownerProfile, setOwner]      = useState(null)
  const [invites, setInvites]         = useState([])
  const [customRoles, setCustomRoles] = useState([])
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)
  const [showInvite, setShowInv]      = useState(false)
  const [confirmRm, setConfirmRm]     = useState(null)
  const [confirmRevoke, setConfirmRevoke] = useState(null)
  const [busy, setBusy]               = useState(false)

  const canInvite      = has('members.invite')
  const canRemove      = has('members.remove')
  const canManageRoles = has('members.manage_roles')
  const canViewInvites = has('members.invite')

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [mRes, rolesRes] = await Promise.all([
        memberApi.list(org.organization_slug),
        roleApi.list(org.organization_slug).catch(() => []),
      ])
      const list = Array.isArray(mRes) ? mRes : []
      setMembers(list)
      setCustomRoles(Array.isArray(rolesRes) ? rolesRes : [])

      if (canViewInvites) {
        const iRes = await inviteApi.list(org.organization_slug)
        setInvites(Array.isArray(iRes) ? iRes : [])
      } else {
        setInvites([])
      }

      const ids = [ownerId, ...list.map(m => m.user_id)].filter(Boolean)
      if (ids.length) {
        try {
          const profiles = await userApi.lookup(ids)
          const byId = Object.fromEntries((profiles || []).map(p => [p.id, p]))
          setOwner(byId[ownerId] || null)
          setMembers(list.map(m => ({
            ...m,
            email:     byId[m.user_id]?.email     ?? null,
            full_name: byId[m.user_id]?.full_name ?? null,
          })))
        } catch { /* keep UUIDs as fallback */ }
      }
    } catch (err) {
      setError(err?.data?.detail || 'Failed to load members.')
    } finally {
      setLoading(false)
    }
  }, [org.organization_slug, canViewInvites, ownerId])

  useEffect(() => { reload() }, [reload])

  async function changeRole(userId, value) {
    // value is either a built-in role ("admin","member","viewer")
    // or "custom:uuid" for a custom role
    const isCustom = value.startsWith('custom:')
    const payload = isCustom
      ? { custom_role_id: value.slice(7) }
      : { role: value }
    try {
      await memberApi.updateRole(org.organization_slug, userId, payload)
      if (isCustom) {
        const crid = value.slice(7)
        setMembers(prev => prev.map(m => m.user_id === userId ? { ...m, role: 'member', custom_role_id: crid } : m))
      } else {
        setMembers(prev => prev.map(m => m.user_id === userId ? { ...m, role: value, custom_role_id: null } : m))
      }
    } catch (err) {
      setError(err?.data?.detail || 'Failed to update role.')
    }
  }

  function getMemberRoleValue(m) {
    return m.custom_role_id ? `custom:${m.custom_role_id}` : m.role
  }

  function getMemberRoleLabel(m) {
    if (m.custom_role_id) {
      const cr = customRoles.find(r => r.id === m.custom_role_id)
      return cr ? cr.name : 'Custom'
    }
    return ROLE_LABEL[m.role] || m.role
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
          {canInvite && (
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
            <MemberRow
              displayName={
                ownerId === currentUserId
                  ? 'You'
                  : (ownerProfile?.full_name || 'Organization owner')
              }
              email={ownerProfile?.email}
              avatarSeed={ownerProfile?.full_name || ownerProfile?.email || 'O'}
              roleSlot={<span className="cc-role-pill cc-role-owner">Owner</span>}
            />

            {members.map(m => {
              const isSelf         = m.user_id === currentUserId
              const youCanEditThis = canManageRoles && !isSelf
              const displayName    = isSelf ? 'You' : (m.full_name || m.email || 'Member')
              return (
                <MemberRow
                  key={m.user_id}
                  displayName={displayName}
                  email={m.email}
                  avatarSeed={m.full_name || m.email || displayName}
                  roleSlot={
                    youCanEditThis ? (
                      <select
                        className="cc-role-select"
                        value={getMemberRoleValue(m)}
                        onChange={e => changeRole(m.user_id, e.target.value)}
                      >
                        <optgroup label="Built-in">
                          <option value="admin">Admin</option>
                          <option value="member">Member</option>
                          <option value="viewer">Viewer</option>
                        </optgroup>
                        {customRoles.length > 0 && (
                          <optgroup label="Custom roles">
                            {customRoles.map(cr => (
                              <option key={cr.id} value={`custom:${cr.id}`}>{cr.name}</option>
                            ))}
                          </optgroup>
                        )}
                      </select>
                    ) : (
                      <span
                        className={`cc-role-pill ${m.custom_role_id ? '' : `cc-role-${m.role}`}`}
                        style={m.custom_role_id ? {
                          background: (customRoles.find(r => r.id === m.custom_role_id)?.color || '#8899AA') + '22',
                          color: customRoles.find(r => r.id === m.custom_role_id)?.color || '#8899AA',
                          borderColor: (customRoles.find(r => r.id === m.custom_role_id)?.color || '#8899AA') + '44',
                        } : undefined}
                      >
                        {getMemberRoleLabel(m)}
                      </span>
                    )
                  }
                  actionSlot={
                    (canRemove || isSelf) && (
                      <button
                        className="cc-icon-danger"
                        onClick={() => setConfirmRm(m)}
                        title={isSelf ? 'Leave organization' : 'Remove member'}
                      >
                        <IconTrash />
                      </button>
                    )
                  }
                />
              )
            })}
          </div>
        )}
      </div>

      {canViewInvites && (
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
  const [showTransfer, setShowTransfer]   = useState(false)
  const [transferDone, setTransferDone]   = useState(false)

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

      {org.is_active && (
        <div className="cc-section" style={{ marginTop: 16 }}>
          <div className="cc-section-head">Ownership</div>
          <div className="cc-form-grid">
            {transferDone && (
              <Alert type="ok">
                Transfer initiated. The recipient will receive an email with a confirmation link
                (valid for 48&nbsp;hours). Ownership only changes once they accept.
              </Alert>
            )}
            <p style={{ font: '400 13px/1.55 var(--font-body)', color: '#4A6080', margin: 0 }}>
              Hand over ownership of this workspace to another member. They'll receive an
              email and become the new owner once they accept; you'll be downgraded to admin
              so you don't lose access.
            </p>
          </div>
          <div className="cc-form-actions">
            <button
              type="button"
              className="cc-btn cc-btn-md cc-btn-ghost"
              onClick={() => setShowTransfer(true)}
            >
              Transfer ownership…
            </button>
          </div>
        </div>
      )}

      {org.is_active && (
        <div className="cc-section cc-section--danger" style={{ marginTop: 16 }}>
          <div className="cc-section-head">Danger zone</div>
          <div className="cc-form-grid">
            <p style={{ font: '400 13px/1.55 var(--font-body)', color: '#4A6080', margin: 0 }}>
              Deactivating this organization pauses access for all members and freezes its workspace.
              You can reactivate it any time from the inactive list.
            </p>
          </div>
          <div className="cc-form-actions">
            <button
              type="button"
              className="cc-btn cc-btn-md cc-btn-danger"
              onClick={() => setConfirmDel(true)}
            >
              Deactivate organization
            </button>
          </div>
        </div>
      )}

      {confirmDel && (
        <ConfirmModal
          title={`Deactivate "${org.organization_name}"?`}
          message="The organization will be marked inactive. Members lose access until you reactivate it from the inactive list."
          confirmLabel="Deactivate"
          danger
          loading={deleting}
          onConfirm={doDelete}
          onClose={() => setConfirmDel(false)}
        />
      )}

      {showTransfer && (
        <TransferOwnershipModal
          slug={org.organization_slug}
          orgName={org.organization_name}
          onClose={() => setShowTransfer(false)}
          onTransferred={() => { setShowTransfer(false); setTransferDone(true) }}
        />
      )}
    </>
  )
}

// ─── OrgDashboard root ────────────────────────────────────────────────────────

// Each tab declares its own visibility rule.
// `visible({ role, has, loaded })` — called after privileges are resolved.
// `loaded` is false until the my-privileges API responds; privilege-gated tabs
// wait for it so they don't flash then disappear.
const TABS = [
  { id: 'overview', label: 'Overview',  visible: ()                       => true },
  { id: 'members',  label: 'Members',   visible: ()                       => true },
  { id: 'roles',    label: 'Roles',     visible: ({ has, loaded })        => loaded && (has('roles.view') || has('roles.manage')) },
  { id: 'scans',    label: 'Scans',     visible: ({ has, loaded })        => loaded && (has('scans.view') || has('scans.run')) },
  { id: 'settings', label: 'Settings',  visible: ({ role })               => canManageOrg(role) },
]

export function OrgDashboard({ org: initialOrg, onBack, onOrgChanged, currentUserId }) {
  const [org, setOrg]           = useState(initialOrg)
  const [tab, setTab]           = useState('overview')
  const [freshErr, setFreshErr] = useState(null)
  const [privileges, setPrivileges] = useState(new Set())
  const [privsLoaded, setPrivsLoaded] = useState(false)

  // Stable checker — components can safely list `has` in dependency arrays
  const has = useCallback((p) => privileges.has(p), [privileges])

  useEffect(() => {
    let cancelled = false
    Promise.all([
      orgApi.get(initialOrg.organization_slug),
      roleApi.myPrivileges(initialOrg.organization_slug),
    ]).then(([detail, privData]) => {
      if (!cancelled) {
        setOrg(prev => ({ ...prev, ...detail }))
        setPrivileges(new Set(privData?.privileges || []))
        setPrivsLoaded(true)
      }
    }).catch(err => {
      if (!cancelled) {
        setFreshErr(err?.data?.detail || 'Failed to load organization details.')
        setPrivsLoaded(true) // unblock tabs even on error
      }
    })
    return () => { cancelled = true }
  }, [initialOrg.organization_slug])

  const role = org.role || 'viewer'
  const plan = org.plan || 'free'

  // If the current tab becomes invisible after privileges load, reset to overview
  useEffect(() => {
    if (!privsLoaded) return
    const current = TABS.find(t => t.id === tab)
    if (current && !current.visible({ role, has, loaded: privsLoaded })) {
      setTab('overview')
    }
  }, [privsLoaded, role, has, tab])

  function handleUpdated(updated) {
    setOrg(prev => ({ ...prev, ...updated }))
    onOrgChanged?.({ ...org, ...updated })
  }

  const visibleTabs = TABS.filter(t => t.visible({ role, has, loaded: privsLoaded }))

  return (
    <div>
      <button className="cc-back" onClick={onBack}>
        <IconBack />
        Organizations
      </button>

      <div className={`cc-org-head${org.is_active ? '' : ' cc-org-head--inactive'}`}>
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

      {!org.is_active && (
        <InactiveBanner
          org={org}
          role={role}
          onReactivated={() => {
            orgApi.get(org.organization_slug).then(updated => {
              setOrg(prev => ({ ...prev, ...updated }))
              onOrgChanged?.({ ...org, ...updated })
            }).catch(() => {
              const next = { ...org, is_active: true }
              setOrg(next)
              onOrgChanged?.(next)
            })
          }}
        />
      )}

      <div className="cc-tabs" role="tablist">
        {visibleTabs.map(t => (
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
      {tab === 'members' && (
        <MembersTab
          org={org}
          currentRole={role}
          ownerId={org.owner_id}
          currentUserId={currentUserId}
          has={has}
        />
      )}
      {tab === 'roles' && (has('roles.view') || has('roles.manage')) && (
        <RolesTab org={org} has={has} />
      )}
      {tab === 'scans' && (has('scans.view') || has('scans.run')) && (
        <ScansTab org={org} has={has} />
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
