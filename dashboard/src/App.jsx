import { useState, useEffect } from 'react'
import { AuthLayout } from './components/layout/AuthLayout'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { VerifyEmailPage } from './pages/VerifyEmailPage'
import { ResetRequestPage } from './pages/ResetRequestPage'
import { ResetConfirmPage } from './pages/ResetConfirmPage'
import { DashboardPage } from './pages/DashboardPage'
import { InvitePage } from './pages/InvitePage'
import { TransferAcceptPage } from './pages/TransferAcceptPage'
import { useLang } from './hooks/useLang'
import { useAuth } from './hooks/useAuth'

const PENDING_FLOW_KEY = 'cc.pending_flow'    // sessionStorage: { kind, token }

function readInitialRoute() {
  const params = new URLSearchParams(window.location.search)
  const path   = window.location.pathname
  const token  = params.get('token')

  if (token && path.includes('verify')) return { view: 'verify',        token }
  if (token && path.includes('reset'))  return { view: 'reset-confirm', token }

  if (token && path.includes('transfer-ownership')) {
    try { window.history.replaceState({}, '', '/') } catch { /* noop */ }
    return { view: 'token-flow', flow: { kind: 'transfer', token } }
  }
  if (token && path.includes('invite')) {
    try { window.history.replaceState({}, '', '/') } catch { /* noop */ }
    return { view: 'token-flow', flow: { kind: 'invite', token } }
  }
  return { view: 'login', token: null }
}

const initialRoute = readInitialRoute()

export function App() {
  const { lang, setLang, t, tf } = useLang()
  const { user, status, login, logout } = useAuth()
  const [view, setView]                 = useState(initialRoute.view === 'token-flow' ? 'login' : initialRoute.view)
  const [pendingFlow, setPendingFlow]   = useState(
    initialRoute.view === 'token-flow' ? initialRoute.flow : null
  )

  // After login, restore any flow stashed during the unauthenticated landing.
  useEffect(() => {
    if (status !== 'authenticated' || pendingFlow) return
    try {
      const raw = sessionStorage.getItem(PENDING_FLOW_KEY)
      if (!raw) return
      const parsed = JSON.parse(raw)
      if (parsed && parsed.kind && parsed.token) {
        sessionStorage.removeItem(PENDING_FLOW_KEY)
        setPendingFlow(parsed)
      }
    } catch { /* ignore corrupt storage */ }
  }, [status, pendingFlow])

  if (status === 'loading') {
    return <div style={{ minHeight: '100vh', background: '#fff' }} />
  }

  // ── Token-driven flows (invite / transfer-ownership) ──
  if (pendingFlow) {
    const shared = {
      token:  pendingFlow.token,
      user,
      status,
      onProceedToLogin: () => {
        sessionStorage.setItem(PENDING_FLOW_KEY, JSON.stringify(pendingFlow))
        setPendingFlow(null)
      },
      onComplete: () => setPendingFlow(null),
    }
    if (pendingFlow.kind === 'invite')   return <InvitePage          {...shared} />
    if (pendingFlow.kind === 'transfer') return <TransferAcceptPage  {...shared} />
  }

  if (status === 'authenticated') {
    return <DashboardPage user={user} onLogout={logout} />
  }

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
