import { useState, useEffect } from 'react'
import { memberApi, orgApi, userApi } from '../../api/endpoints'

const ROLE_LABEL = { admin: 'Admin', member: 'Member', viewer: 'Viewer' }

function initials(s = '') {
  return s.split(/[\s@._-]/).filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join('') || '?'
}

export function TransferOwnershipModal({ slug, orgName, onClose, onTransferred }) {
  const [members, setMembers]       = useState([])    // [{ user_id, role, email?, full_name? }]
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [confirmStep, setConfirmStep] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitErr, setSubmitErr]   = useState(null)

  useEffect(() => {
    let cancelled = false

    async function loadMembersWithProfiles() {
      try {
        const members = await memberApi.list(slug)
        if (cancelled) return
        const list = Array.isArray(members) ? members : []
        // Render rows immediately with UUID placeholder; enrich asynchronously
        setMembers(list.map(m => ({ ...m })))
        setLoading(false)

        if (list.length === 0) return

        const ids = list.map(m => m.user_id)
        const profiles = await userApi.lookup(ids)
        if (cancelled) return
        const byId = Object.fromEntries((profiles || []).map(p => [p.id, p]))
        setMembers(list.map(m => ({
          ...m,
          email:     byId[m.user_id]?.email     ?? null,
          full_name: byId[m.user_id]?.full_name ?? null,
        })))
      } catch (err) {
        if (!cancelled) {
          setError(err?.data?.detail || 'Failed to load members.')
          setLoading(false)
        }
      }
    }
    loadMembersWithProfiles()

    return () => { cancelled = true }
  }, [slug])

  async function submit() {
    setSubmitting(true)
    setSubmitErr(null)
    try {
      await orgApi.transferOwnership(slug, selectedId)
      onTransferred()
    } catch (err) {
      setSubmitErr(err?.data?.detail || 'Failed to start the transfer.')
      setSubmitting(false)
    }
  }

  function close() {
    if (submitting) return
    onClose()
  }

  const selected = members.find(m => m.user_id === selectedId)

  function MemberLine({ m }) {
    const primary = m.full_name || m.email || m.user_id
    const secondary = m.full_name && m.email
      ? m.email
      : m.email
        ? `${ROLE_LABEL[m.role] || m.role}`
        : m.user_id
    return (
      <>
        <div className="cc-mrow-avatar">{initials(m.full_name || m.email || m.user_id)}</div>
        <div className="cc-mrow-main">
          <div className="cc-mrow-title">
            {primary}
            <span className={`cc-role-pill cc-role-${m.role}`} style={{ marginLeft: 8, verticalAlign: 'middle' }}>
              {ROLE_LABEL[m.role] || m.role}
            </span>
          </div>
          <div className="cc-mrow-sub">{secondary}</div>
        </div>
      </>
    )
  }

  return (
    <div className="cc-overlay" onClick={e => e.target === e.currentTarget && close()}>
      <div className="cc-modal" role="dialog" aria-modal="true">
        <div className="cc-modal-head">
          <div>
            <div className="cc-modal-title">
              {confirmStep ? 'Confirm transfer' : 'Transfer ownership'}
            </div>
            <div className="cc-modal-sub">
              {confirmStep
                ? `Once they accept, you become an admin and lose owner-only powers.`
                : `Pick a member to receive ownership of ${orgName}.`}
            </div>
          </div>
          <button className="cc-modal-x" onClick={close} disabled={submitting} aria-label="Close">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M3 3l10 10M13 3L3 13"/>
            </svg>
          </button>
        </div>

        <div className="cc-modal-body">
          {error && (
            <div className="cc-alert cc-alert--err">
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="8" cy="8" r="6"/><path d="M8 5v3M8 11v.5"/>
              </svg>
              {error}
            </div>
          )}
          {submitErr && (
            <div className="cc-alert cc-alert--err">
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="8" cy="8" r="6"/><path d="M8 5v3M8 11v.5"/>
              </svg>
              {submitErr}
            </div>
          )}

          {!confirmStep ? (
            loading ? (
              <div style={{ padding: '24px 0', textAlign: 'center' }}>
                <span className="cc-skel" style={{ width: 180, height: 14, display: 'inline-block' }} />
              </div>
            ) : members.length === 0 ? (
              <div className="cc-empty cc-empty--inline">
                <div className="cc-empty-title">No members to transfer to</div>
                <div className="cc-empty-sub">Invite someone first, then you can hand off ownership.</div>
              </div>
            ) : (
              <div className="cc-member-pick">
                {members.map(m => (
                  <label key={m.user_id} className={`cc-pick-row${selectedId === m.user_id ? ' cc-pick-row--on' : ''}`}>
                    <input
                      type="radio"
                      name="transfer-target"
                      value={m.user_id}
                      checked={selectedId === m.user_id}
                      onChange={() => setSelectedId(m.user_id)}
                    />
                    <MemberLine m={m} />
                  </label>
                ))}
              </div>
            )
          ) : (
            <div className="cc-transfer-confirm">
              <p style={{ font: '400 13.5px/1.55 var(--font-body)', color: '#4A6080', margin: '0 0 14px' }}>
                Ownership of <strong style={{ color: '#0A1628' }}>{orgName}</strong> will be transferred to:
              </p>
              <div className="cc-pick-row cc-pick-row--readonly">
                <MemberLine m={selected} />
              </div>
              <p style={{ font: '400 12.5px/1.55 var(--font-body)', color: '#8899AA', margin: '14px 0 0' }}>
                They'll receive an email at <strong>{selected?.email || 'their address'}</strong> with a
                confirmation link. The transfer only completes once they accept.
              </p>
            </div>
          )}
        </div>

        <div className="cc-modal-foot">
          {confirmStep ? (
            <>
              <button className="cc-btn cc-btn-md cc-btn-ghost" onClick={() => setConfirmStep(false)} disabled={submitting}>
                Back
              </button>
              <button className="cc-btn cc-btn-md cc-btn-primary" onClick={submit} disabled={submitting}>
                {submitting ? <><span className="cc-spin" /> Sending…</> : 'Send transfer request'}
              </button>
            </>
          ) : (
            <>
              <button className="cc-btn cc-btn-md cc-btn-ghost" onClick={close}>Cancel</button>
              <button
                className="cc-btn cc-btn-md cc-btn-primary"
                onClick={() => setConfirmStep(true)}
                disabled={!selectedId || loading}
              >
                Continue
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
