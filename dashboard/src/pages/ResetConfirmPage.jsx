import { useState } from 'react'
import { Input } from '../components/ui/Input'
import { PasswordInput } from '../components/ui/PasswordInput'
import { Button } from '../components/ui/Button'
import { Alert } from '../components/ui/Alert'
import { SuccessCard } from '../components/ui/SuccessCard'
import { useApi } from '../hooks/useApi'

const LOCK_ICON = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>

export function ResetConfirmPage({ t, lang, navigate, token: initialToken }) {
  const [token, setToken]   = useState(initialToken || '')
  const [pw, setPw]         = useState('')
  const [pw2, setPw2]       = useState('')
  const [errors, setErrors] = useState({})
  const [globalErr, setGlobalErr] = useState(null)
  const [success, setSuccess] = useState(false)
  const { call, loading }   = useApi()

  async function submit(e) {
    e.preventDefault()
    const errs = {}
    if (!token && !initialToken) errs.token = t('err_token')
    if (!pw)          errs.pw  = t('err_pw')
    if (pw.length < 12) errs.pw = t('err_pw_min')
    if (pw !== pw2)   errs.pw2 = t('err_pw_match')
    if (Object.keys(errs).length) { setErrors(errs); return }
    setErrors({})
    setGlobalErr(null)

    try {
      await call('POST', '/email/reset-password/confirm', { token: initialToken || token, new_password: pw })
      setSuccess(true)
    } catch (err) {
      if (err.status === 400) setGlobalErr(t('err_reset_invalid'))
      else if (err.status === 422 && err.data?.detail?.password) {
        const m = Array.isArray(err.data.detail.password) ? err.data.detail.password.join(' ') : err.data.detail.password
        setErrors(prev => ({ ...prev, pw: m }))
      }
      else setGlobalErr(t('err_generic'))
    }
  }

  if (success) {
    return <SuccessCard title={t('pw_changed_title')} sub={t('pw_changed_sub')} btnLabel={t('go_login')} onBtn={() => navigate('login')} />
  }

  return (
    <div className="card">
      <div className="card-icon">{LOCK_ICON}</div>
      <div className="card-title">{t('new_pw_title')}</div>
      <div className="card-sub">{t('new_pw_sub')}</div>
      {globalErr && <Alert type="error">{globalErr}</Alert>}
      <form className="form" onSubmit={submit} noValidate>
        {!initialToken && (
          <Input id="token" label={t('reset_token_label')} type="text" placeholder={t('token_ph')} value={token} onChange={e => setToken(e.target.value)} error={errors.token} />
        )}
        <PasswordInput id="password" label={t('new_pw_label')} lang={lang} placeholder={t('pw_min_ph')} value={pw} onChange={e => setPw(e.target.value)} error={errors.pw} showStrength />
        <PasswordInput id="password2" label={t('confirm_new_pw')} lang={lang} placeholder={t('pw_ph')} value={pw2} onChange={e => setPw2(e.target.value)} error={errors.pw2} />
        <Button type="submit" loading={loading}>{t('set_pw_btn')}</Button>
      </form>
    </div>
  )
}
