// VerifyEmailPage.jsx
import { useEffect, useState } from 'react'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { Alert } from '../components/ui/Alert'
import { SuccessCard } from '../components/ui/SuccessCard'
import { useApi } from '../hooks/useApi'

const MAIL_ICON = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>

export function VerifyEmailPage({ t, navigate, token: initialToken }) {
  const [token, setToken]   = useState(initialToken || '')
  const [errors, setErrors] = useState({})
  const [success, setSuccess] = useState(false)
  const [globalErr, setGlobalErr] = useState(null)
  const { call, loading }   = useApi()

  // Auto-verify if token came from URL
  useEffect(() => {
    if (initialToken) doVerify(initialToken)
  }, [])

  async function doVerify(t_) {
    const tok = t_ || token
    if (!tok) { setErrors({ token: t('err_token') }); return }
    setErrors({})
    setGlobalErr(null)
    try {
      await call('POST', '/email/verify', { token: tok })
      setSuccess(true)
    } catch {
      setGlobalErr(t('verify_fail'))
    }
  }

  if (success) {
    return <SuccessCard title={t('verified_title')} sub={t('verified_sub')} btnLabel={t('go_login')} onBtn={() => navigate('login')} />
  }

  if (initialToken) {
    return (
      <div className="card" style={{ textAlign: 'center' }}>
        <div className="card-icon" style={{ margin: '0 auto 22px' }}>{MAIL_ICON}</div>
        <div className="card-title">{t('verify_title')}</div>
        <div className="card-sub">{globalErr ? '' : t('verify_loading')}</div>
        {globalErr && <Alert type="error">{globalErr}</Alert>}
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-icon">{MAIL_ICON}</div>
      <div className="card-title">{t('verify_title')}</div>
      <div className="card-sub">{t('verify_manual_sub')}</div>
      {globalErr && <Alert type="error">{globalErr}</Alert>}
      <form className="form" onSubmit={e => { e.preventDefault(); doVerify() }} noValidate>
        <Input id="token" label={t('token_label')} type="text" placeholder={t('token_ph')} value={token} onChange={e => setToken(e.target.value)} error={errors.token} />
        <Button type="submit" loading={loading}>{t('verify_btn')}</Button>
        <div className="text-center small">
          <button type="button" className="link" onClick={() => navigate('login')}>{t('back_login')}</button>
        </div>
      </form>
    </div>
  )
}
