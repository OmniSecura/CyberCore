import { useEffect, useState } from 'react'
import { inviteApi } from '../api/endpoints'

const ROLE_LABEL = { admin: 'Admin', member: 'Member', viewer: 'Viewer' }

/**
 * Module-level guard so StrictMode double-mount in dev cannot fire the
 * accept call twice (which races a row lock on the invite in MySQL).
 * Survives unmount/remount because it lives at module scope.
 *
 * Maps token → Promise so the second invocation reuses the first's result
 * instead of either firing again or silently doing nothing.
 */
const inflight = new Map()

function acceptOnce(token) {
  let p = inflight.get(token)
  if (!p) {
    p = inviteApi.accept(token)
    inflight.set(token, p)
  }
  return p
}

export function InvitePage({ token, user, status, onProceedToLogin, onComplete }) {
  // status: 'authenticated' | 'unauthenticated' | 'loading'
  const [phase, setPhase]   = useState('idle')   // idle | accepting | success | error
  const [result, setResult] = useState(null)
  const [error, setError]   = useState(null)

  useEffect(() => {
    if (status !== 'authenticated' || !token) return
    if (phase !== 'idle') return

    setPhase('accepting')
    acceptOnce(token)
      .then(data => {
        setResult(data)
        setPhase('success')
      })
      .catch(err => {
        const detail = err?.data?.detail
        if (err?.status === 404)      setError(detail || 'This invite is invalid or has already been used.')
        else if (err?.status === 410) setError(detail || 'This invite has expired.')
        else if (err?.status === 403) setError(detail || 'This invite was sent to a different email address.')
        else if (err?.status === 400) setError(detail || 'You are already a member of this organization.')
        else                          setError(detail || 'Failed to accept the invitation.')
        setPhase('error')
      })
  }, [status, token, phase])

  // ── Unauthenticated landing ──
  if (status === 'unauthenticated') {
    return (
      <div className="cc-landing">
        <div className="cc-landing-card">
          <div className="cc-landing-icon cc-landing-icon--brand">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                 strokeLinecap="round" strokeLinejoin="round">
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M22 11l-3 3-2-2"/>
            </svg>
          </div>
          <h1 className="cc-landing-title">You've been invited</h1>
          <p className="cc-landing-sub">
            Sign in (or create an account) to accept the invitation and join the organization.
          </p>
          <button
            className="cc-btn cc-btn-md cc-btn-primary"
            onClick={onProceedToLogin}
            style={{ marginTop: 4 }}
          >
            Continue to sign in
          </button>
          <p className="cc-landing-foot">
            After signing in, your invitation will be accepted automatically.
          </p>
        </div>
      </div>
    )
  }

  // ── Authenticated — auto-accepting / result ──
  if (phase === 'accepting' || phase === 'idle') {
    return (
      <div className="cc-landing">
        <div className="cc-landing-card">
          <div className="cc-landing-spinner"><span className="cc-spin cc-spin--lg" /></div>
          <h1 className="cc-landing-title">Accepting invitation…</h1>
          <p className="cc-landing-sub">Hold on a moment while we add you to the organization.</p>
        </div>
      </div>
    )
  }

  if (phase === 'success') {
    return (
      <div className="cc-landing">
        <div className="cc-landing-card">
          <div className="cc-landing-icon cc-landing-icon--ok">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"
                 strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12l5 5 9-11"/>
            </svg>
          </div>
          <h1 className="cc-landing-title">Welcome aboard!</h1>
          <p className="cc-landing-sub">
            You've joined <strong>{result?.organization_name}</strong> as{' '}
            <strong>{ROLE_LABEL[result?.role] || result?.role}</strong>.
          </p>
          <button
            className="cc-btn cc-btn-md cc-btn-primary"
            onClick={onComplete}
            style={{ marginTop: 4 }}
          >
            Go to dashboard
          </button>
        </div>
      </div>
    )
  }

  // phase === 'error'
  return (
    <div className="cc-landing">
      <div className="cc-landing-card">
        <div className="cc-landing-icon cc-landing-icon--err">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
               strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="9"/><path d="M12 8v4M12 16v.5"/>
          </svg>
        </div>
        <h1 className="cc-landing-title">Couldn't accept the invitation</h1>
        <p className="cc-landing-sub">{error}</p>
        <button
          className="cc-btn cc-btn-md cc-btn-ghost"
          onClick={onComplete}
          style={{ marginTop: 4 }}
        >
          Go to dashboard
        </button>
      </div>
    </div>
  )
}
