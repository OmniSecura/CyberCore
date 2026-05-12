import { useState } from 'react'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { SuccessCard } from '../components/ui/SuccessCard'
import { useApi } from '../hooks/useApi'

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
      setSuccess(true)
    }
  }

  if (success) {
    return (
      <SuccessCard
        title={t('reset_sent_title')}
        sub={tf('reset_sent', email)}
        btnLabel={t('back_login')}
        onBtn={() => navigate('login')}
      />
    )
  }

  return (
    <div className="auth-card">
      <div className="head">
        <div className="eyebrow">{t('eyebrow_reset')}</div>
        <h1>{t('reset_title')}</h1>
        <div className="sub">{t('reset_sub')}</div>
      </div>
      <form className="form" onSubmit={submit} noValidate>
        <Input
          id="email" label={t('email_label')} type="email"
          placeholder={t('email_ph')} value={email}
          onChange={e => setEmail(e.target.value)} error={errors.email}
        />
        <Button type="submit" loading={loading}>{t('send_link')}</Button>
        <div className="text-center small" style={{ marginTop: 6 }}>
          <button type="button" className="link" onClick={() => navigate('login')}>{t('back_login')}</button>
        </div>
      </form>
    </div>
  )
}
