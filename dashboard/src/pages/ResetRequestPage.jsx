import { useState } from 'react'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { Alert } from '../components/ui/Alert'
import { SuccessCard } from '../components/ui/SuccessCard'
import { useApi } from '../hooks/useApi'

const KEY_ICON = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21 2-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>

export function ResetRequestPage({ t, tf, navigate }) {
  const [email, setEmail]   = useState('')
  const [errors, setErrors] = useState({})
  const [success, setSuccess] = useState(false)
  const { call, loading }   = useApi()

  async function submit(e) {
    e.preventDefault()
    if (!email) { setErrors({ email: t('err_email') }); return }
    setErrors({})
    try {
      await call('POST', '/email/reset-password/request', { email })
      setSuccess(true)
    } catch {
      setSuccess(true) // always show success to avoid email enumeration
    }
  }

  if (success) {
    return <SuccessCard title={t('reset_sent_title')} sub={tf('reset_sent', email)} btnLabel={t('back_login')} onBtn={() => navigate('login')} />
  }

  return (
    <div className="card">
      <div className="card-icon">{KEY_ICON}</div>
      <div className="card-title">{t('reset_title')}</div>
      <div className="card-sub">{t('reset_sub')}</div>
      <form className="form" onSubmit={submit} noValidate>
        <Input id="email" label={t('email_label')} type="email" placeholder={t('email_ph')} value={email} onChange={e => setEmail(e.target.value)} error={errors.email} />
        <Button type="submit" loading={loading}>{t('send_link')}</Button>
        <div className="text-center small">
          <button type="button" className="link" onClick={() => navigate('login')}>{t('back_login')}</button>
        </div>
      </form>
    </div>
  )
}
