import { useState } from 'react'
import { Input } from '../components/ui/Input'
import { PasswordInput } from '../components/ui/PasswordInput'
import { Button } from '../components/ui/Button'
import { Alert } from '../components/ui/Alert'
import { useApi } from '../hooks/useApi'

const GOOGLE_ICON = <svg viewBox="0 0 24 24" fill="none"><path fill="#4285F4" d="M23.49 12.27c0-.79-.07-1.54-.2-2.27H12v4.51h6.45c-.28 1.45-1.12 2.68-2.38 3.5v2.91h3.85c2.26-2.08 3.57-5.14 3.57-8.65z"/><path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.85-2.99c-1.08.72-2.45 1.16-4.08 1.16-3.13 0-5.78-2.11-6.73-4.96H1.29v3.09C3.26 21.3 7.31 24 12 24z"/><path fill="#FBBC05" d="M5.27 14.29c-.25-.72-.38-1.49-.38-2.29s.14-1.57.38-2.29V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.98-3.09z"/><path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.98 3.09C6.22 6.86 8.87 4.75 12 4.75z"/></svg>
const GITHUB_ICON = <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 .3a12 12 0 0 0-3.79 23.4c.6.1.82-.26.82-.58v-2c-3.34.72-4.04-1.6-4.04-1.6-.55-1.39-1.34-1.76-1.34-1.76-1.09-.74.08-.72.08-.72 1.2.08 1.84 1.24 1.84 1.24 1.07 1.84 2.81 1.3 3.49.99.1-.78.42-1.3.76-1.6-2.66-.3-5.47-1.33-5.47-5.93 0-1.31.47-2.38 1.24-3.22-.13-.3-.54-1.52.11-3.18 0 0 1-.32 3.3 1.23a11.5 11.5 0 0 1 6 0c2.29-1.55 3.3-1.23 3.3-1.23.65 1.66.24 2.88.12 3.18.77.84 1.23 1.91 1.23 3.22 0 4.61-2.81 5.62-5.48 5.92.43.37.81 1.1.81 2.22v3.29c0 .32.22.69.83.58A12 12 0 0 0 12 .3"/></svg>

export function LoginPage({ t, lang, navigate, onLogin }) {
  const [email, setEmail]   = useState('')
  const [pw, setPw]         = useState('')
  const [errors, setErrors] = useState({})
  const [global, setGlobal] = useState(null)
  const { call, loading }   = useApi()

  async function submit(e) {
    e.preventDefault()
    const errs = {}
    if (!email) errs.email = t('err_email')
    if (!pw)    errs.pw    = t('err_pw')
    if (Object.keys(errs).length) { setErrors(errs); return }
    setErrors({})
    setGlobal(null)

    try {
      await call('POST', '/users/login', { email, password: pw })
      await onLogin()
    } catch (err) {
      if (err.status === 403) setGlobal({ type: 'info',  msg: t('err_unverified') })
      else if (err.status === 401 && String(err.data?.detail).includes('locked')) setGlobal({ type: 'error', msg: t('err_locked') })
      else setGlobal({ type: 'error', msg: t('err_creds') })
    }
  }

  return (
    <div className="auth-card">
      <div className="head">
        <div className="eyebrow">{t('eyebrow_signin')}</div>
        <h1>{t('login_title')}</h1>
        <div className="sub">{t('login_sub')}</div>
      </div>

      {global && <Alert type={global.type}>{global.msg}</Alert>}

      <form className="form" onSubmit={submit} noValidate>
        <Input
          id="email" label={t('email_label')} type="email"
          placeholder={t('email_ph')} value={email}
          onChange={e => setEmail(e.target.value)} error={errors.email}
          autoComplete="username"
        />
        <PasswordInput
          id="password" label={t('pw_label')} lang={lang}
          placeholder={t('pw_ph')} value={pw}
          onChange={e => setPw(e.target.value)} error={errors.pw}
          autoComplete="current-password"
        />

        <div className="row">
          <span />
          <button type="button" className="link" onClick={() => navigate('reset-request')}>
            {t('forgot')}
          </button>
        </div>

        <Button type="submit" loading={loading}>{t('login_btn')}</Button>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 4 }}>
          <div className="divider">{t('or')}</div>
          <div className="oauth-row">
            <button className="oauth-btn" type="button" onClick={() => {}}>
              {GOOGLE_ICON}<span>Google</span>
            </button>
            <button className="oauth-btn" type="button" onClick={() => {}}>
              {GITHUB_ICON}<span>GitHub</span>
            </button>
          </div>
        </div>

        <div className="text-center small" style={{ marginTop: 6 }}>
          {t('no_account')}{' '}
          <button type="button" className="link" onClick={() => navigate('register')}>
            {t('sign_up')}
          </button>
        </div>
      </form>
    </div>
  )
}
