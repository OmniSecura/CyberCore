import { useState } from 'react'
import { Input } from '../components/ui/Input'
import { PasswordInput } from '../components/ui/PasswordInput'
import { Button } from '../components/ui/Button'
import { Alert } from '../components/ui/Alert'
import { useApi } from '../hooks/useApi'

const SHIELD = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>

export function LoginPage({ t, lang, navigate }) {
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
      navigate('dashboard') // swap for your post-login route
    } catch (err) {
      if (err.status === 403) setGlobal({ type: 'info',  msg: t('err_unverified') })
      else if (err.status === 401 && String(err.data?.detail).includes('locked')) setGlobal({ type: 'error', msg: t('err_locked') })
      else setGlobal({ type: 'error', msg: t('err_creds') })
    }
  }

  return (
    <div className="card">
      <div className="card-icon">{SHIELD}</div>
      <div className="card-title">{t('login_title')}</div>
      <div className="card-sub">{t('login_sub')}</div>

      {global && <Alert type={global.type}>{global.msg}</Alert>}

      <form className="form" onSubmit={submit} noValidate>
        <Input
          id="email" label={t('email_label')} type="email"
          placeholder={t('email_ph')} value={email}
          onChange={e => setEmail(e.target.value)} error={errors.email}
        />
        <PasswordInput
          id="password" label={t('pw_label')} lang={lang}
          placeholder={t('pw_ph')} value={pw}
          onChange={e => setPw(e.target.value)} error={errors.pw}
        />

        <div className="row">
          <span />
          <button type="button" className="link" onClick={() => navigate('reset-request')}>
            {t('forgot')}
          </button>
        </div>

        <Button type="submit" loading={loading}>{t('login_btn')}</Button>

        <div className="text-center small">
          {t('no_account')}{' '}
          <button type="button" className="link" onClick={() => navigate('register')}>
            {t('sign_up')}
          </button>
        </div>
      </form>
    </div>
  )
}
