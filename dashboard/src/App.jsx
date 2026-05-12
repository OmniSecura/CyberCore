import { useState, useEffect } from 'react'
import { AuthLayout } from './components/layout/AuthLayout'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { VerifyEmailPage } from './pages/VerifyEmailPage'
import { ResetRequestPage } from './pages/ResetRequestPage'
import { ResetConfirmPage } from './pages/ResetConfirmPage'
import { DashboardPage } from './pages/DashboardPage'
import { InvitePage } from './pages/InvitePage'
import { useLang } from './hooks/useLang'
import { useAuth } from './hooks/useAuth'

const INVITE_TOKEN_KEY = 'cc.invite.pending_token'

function readInitialRoute() {
  const params = new URLSearchParams(window.location.search)
  const path   = window.location.pathname
  const token  = params.get('token')
  if (token && path.includes('verify')) return { view: 'verify',        token }
  if (token && path.includes('reset'))  return { view: 'reset-confirm', token }
  if (token && path.includes('invite')) {
    // Strip the token off the URL so it doesn't linger if the user reloads later.
    try { window.history.replaceState({}, '', '/') } catch { /* noop */ }
    return { view: 'invite', token }
  }
  return { view: 'login', token: null }
}

const initialRoute = readInitialRoute()

export function App() {
  const { lang, setLang, t, tf } = useLang()
  const { user, status, login, logout } = useAuth()
  const [view, setView]                 = useState(initialRoute.view === 'invite' ? 'login' : initialRoute.view)
  const [pendingInvite, setPendingInvite] = useState(
    initialRoute.view === 'invite' ? initialRoute.token : null
  )

  // If the user authenticates with a stashed invite token (post-login from the
  // unauthenticated invite landing), pull it back out and resume the flow.
  useEffect(() => {
    if (status !== 'authenticated' || pendingInvite) return
    const stashed = sessionStorage.getItem(INVITE_TOKEN_KEY)
    if (stashed) {
      sessionStorage.removeItem(INVITE_TOKEN_KEY)
      setPendingInvite(stashed)
    }
  }, [status, pendingInvite])

  // Blank screen while checking existing session
  if (status === 'loading') {
    return <div style={{ minHeight: '100vh', background: '#fff' }} />
  }

  // ── Invite flow (full-screen, takes precedence over dashboard/login) ──
  if (pendingInvite) {
    return (
      <InvitePage
        token={pendingInvite}
        user={user}
        status={status}
        onProceedToLogin={() => {
          // Stash the token so we can resume after the user authenticates.
          sessionStorage.setItem(INVITE_TOKEN_KEY, pendingInvite)
          setPendingInvite(null)
        }}
        onComplete={() => setPendingInvite(null)}
      />
    )
  }

  // Authenticated — always show dashboard, never let back to auth pages
  if (status === 'authenticated') {
    return <DashboardPage user={user} onLogout={logout} />
  }

  // Unauthenticated — auth flow
  function navigate(v) { setView(v) }

  const sharedProps = { t, tf, lang, navigate }

  const PAGE = {
    login:          <LoginPage        {...sharedProps} onLogin={login} />,
    register:       <RegisterPage     {...sharedProps} />,
    verify:         <VerifyEmailPage  {...sharedProps} token={initialRoute.token} />,
    'reset-request':<ResetRequestPage {...sharedProps} />,
    'reset-confirm':<ResetConfirmPage {...sharedProps} token={initialRoute.token} />,
  }

  return (
    <AuthLayout lang={lang} setLang={setLang}>
      {PAGE[view] || PAGE.login}
    </AuthLayout>
  )
}
