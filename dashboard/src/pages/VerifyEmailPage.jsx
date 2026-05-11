import { useEffect, useState } from 'react'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { Alert } from '../components/ui/Alert'
import { SuccessCard } from '../components/ui/SuccessCard'
import { useApi } from '../hooks/useApi'

export function VerifyEmailPage({ t, navigate, token: initialToken }) {
  const [token, setToken]   = useState(initialToken || '')
  const [errors, setErrors] = useState({})
  const [success, setSuccess] = useState(false)
  const [globalErr, setGlobalErr] = useState(null)
  const { call, loading }   = useApi()

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
    return (
      <SuccessCard
        title={t('verified_title')}
        sub={t('verified_sub')}
        btnLabel={t('go_login')}
        onBtn={() => navigate('login')}
      />
    )
  }

  if (initialToken) {
    return (
      <div className="auth-card" style={{ textAlign: 'center' }}>
        <div className="head">
          <div className="eyebrow">{t('eyebrow_verify')}</div>
          <h1>{t('verify_title')}</h1>
          <div className="sub">{globalErr ? '' : t('verify_loading')}</div>
        </div>
        {globalErr && <Alert type="error">{globalErr}</Alert>}
      </div>
    )
  }

  return (
    <div className="auth-card">
      <div className="head">
        <div className="eyebrow">{t('eyebrow_verify')}</div>
        <h1>{t('verify_title')}</h1>
        <div className="sub">{t('verify_manual_sub')}</div>
      </div>
      {globalErr && <Alert type="error">{globalErr}</Alert>}
      <form className="form" onSubmit={e => { e.preventDefault(); doVerify() }} noValidate>
        <Input
          id="token" label={t('token_label')} type="text"
          placeholder={t('token_ph')} value={token}
          onChange={e => setToken(e.target.value)} error={errors.token}
        />
        <Button type="submit" loading={loading}>{t('verify_btn')}</Button>
        <div className="text-center small" style={{ marginTop: 6 }}>
          <button type="button" className="link" onClick={() => navigate('login')}>{t('back_login')}</button>
        </div>
      </form>
    </div>
  )
}
