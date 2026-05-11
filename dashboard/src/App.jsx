import { useState } from 'react'
import { AuthLayout } from './components/layout/AuthLayout'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { VerifyEmailPage } from './pages/VerifyEmailPage'
import { ResetRequestPage } from './pages/ResetRequestPage'
import { ResetConfirmPage } from './pages/ResetConfirmPage'
import { DashboardPage } from './pages/DashboardPage'
import { useLang } from './hooks/useLang'
import { useAuth } from './hooks/useAuth'

function getInitialView() {
  const params = new URLSearchParams(window.location.search)
  const path   = window.location.pathname
  if (params.get('token') && path.includes('verify'))  return { view: 'verify',         token: params.get('token') }
  if (params.get('token') && path.includes('reset'))   return { view: 'reset-confirm',  token: params.get('token') }
  return { view: 'login', token: null }
}

const { view: initialView, token: urlToken } = getInitialView()

export function App() {
  const { lang, setLang, t, tf } = useLang()
  const { user, status, login, logout } = useAuth()
  const [view, setView] = useState(initialView)

  // Blank screen while checking existing session
  if (status === 'loading') {
    return <div style={{ minHeight: '100vh', background: '#fff' }} />
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
    verify:         <VerifyEmailPage  {...sharedProps} token={urlToken} />,
    'reset-request':<ResetRequestPage {...sharedProps} />,
    'reset-confirm':<ResetConfirmPage {...sharedProps} token={urlToken} />,
  }

  return (
    <AuthLayout lang={lang} setLang={setLang}>
      {PAGE[view] || PAGE.login}
    </AuthLayout>
  )
}
