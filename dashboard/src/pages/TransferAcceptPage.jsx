import { useEffect, useState } from 'react'
import { orgApi } from '../api/endpoints'

/**
 * Module-level dedupe — see InvitePage.jsx for rationale (StrictMode double-fire).
 */
const inflight = new Map()
function acceptOnce(token) {
  let p = inflight.get(token)
  if (!p) {
    p = orgApi.acceptOwnershipTransfer(token)
    inflight.set(token, p)
  }
  return p
}

export function TransferAcceptPage({ token, user, status, onProceedToLogin, onComplete }) {
  const [phase, setPhase]   = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError]   = useState(null)

  useEffect(() => {
    if (status !== 'authenticated' || !token) return
    if (phase !== 'idle') return

    setPhase('accepting')
    acceptOnce(token)
      .then(data => { setResult(data); setPhase('success') })
      .catch(err => {
        const detail = err?.data?.detail
        if (err?.status === 404)      setError(detail || 'This transfer is invalid or has already been used.')
        else if (err?.status === 410) setError(detail || 'This transfer request has expired.')
        else if (err?.status === 403) setError(detail || 'This transfer was sent to a different account.')
        else                          setError(detail || 'Failed to accept the ownership transfer.')
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
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <path d="M15 13l3-3-3-3M18 10H8"/>
            </svg>
          </div>
          <h1 className="cc-landing-title">Ownership transfer</h1>
          <p className="cc-landing-sub">
            Sign in to accept ownership of the organization.
          </p>
          <button
            className="cc-btn cc-btn-md cc-btn-primary"
            onClick={onProceedToLogin}
            style={{ marginTop: 4 }}
          >
            Continue to sign in
          </button>
          <p className="cc-landing-foot">
            After signing in, the transfer will be accepted automatically.
          </p>
        </div>
      </div>
    )
  }

  if (phase === 'accepting' || phase === 'idle') {
    return (
      <div className="cc-landing">
        <div className="cc-landing-card">
          <div className="cc-landing-spinner"><span className="cc-spin cc-spin--lg" /></div>
          <h1 className="cc-landing-title">Accepting ownership…</h1>
          <p className="cc-landing-sub">Finalizing the ownership transfer.</p>
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
          <h1 className="cc-landing-title">You're the new owner</h1>
          <p className="cc-landing-sub">
            You now own <strong>{result?.organization_name}</strong>. The previous owner has been
            kept as an admin.
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
        <h1 className="cc-landing-title">Couldn't accept the transfer</h1>
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
