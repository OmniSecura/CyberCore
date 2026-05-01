import { useState } from 'react'
import { Input } from '../components/ui/Input'
import { PasswordInput } from '../components/ui/PasswordInput'
import { Button } from '../components/ui/Button'
import { Alert } from '../components/ui/Alert'
import { SuccessCard } from '../components/ui/SuccessCard'
import { useApi } from '../hooks/useApi'

const USER_ICON = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 1 0-16 0"/></svg>

export function RegisterPage({ t, tf, lang, navigate }) {
  const [name, setName]     = useState('')
  const [email, setEmail]   = useState('')
  const [pw, setPw]         = useState('')
  const [pw2, setPw2]       = useState('')
  const [errors, setErrors] = useState({})
  const [global, setGlobal] = useState(null)
  const [success, setSuccess] = useState(false)
  const { call, loading }   = useApi()

  async function submit(e) {
    e.preventDefault()
    const errs = {}
    if (!name)          errs.name = t('err_name')
    if (!email)         errs.email = t('err_email')
    if (!pw)            errs.pw   = t('err_pw')
    if (pw && pw.length < 12) errs.pw = t('err_pw_min')
    if (pw !== pw2)     errs.pw2  = t('err_pw_match')
    if (Object.keys(errs).length) { setErrors(errs); return }
    setErrors({})
    setGlobal(null)

    try {
      await call('POST', '/users/register', { email, full_name: name, password: pw })
      setSuccess(true)
    } catch (err) {
      if (err.status === 409) setErrors(prev => ({ ...prev, email: t('err_taken') }))
      else if (err.data?.detail?.password) {
        const m = Array.isArray(err.data.detail.password)
          ? err.data.detail.password.join(' ')
          : err.data.detail.password
        setErrors(prev => ({ ...prev, pw: m }))
      }
      else setGlobal({ type: 'error', msg: t('err_reg') })
    }
  }

  if (success) {
    return (
      <SuccessCard
        title={t('inbox_title')}
        sub={tf('reg_ok', email)}
        btnLabel={t('back_login')}
        onBtn={() => navigate('login')}
      />
    )
  }

  return (
    <div className="card">
      <div className="card-icon">{USER_ICON}</div>
      <div className="card-title">{t('reg_title')}</div>
      <div className="card-sub">{t('reg_sub')}</div>

      {global && <Alert type={global.type}>{global.msg}</Alert>}

      <form className="form" onSubmit={submit} noValidate>
        <Input
          id="full_name" label={t('name_label')} type="text"
          placeholder={t('name_ph')} value={name}
          onChange={e => setName(e.target.value)} error={errors.name}
        />
        <Input
          id="email" label={t('email_label')} type="email"
          placeholder={t('email_ph')} value={email}
          onChange={e => setEmail(e.target.value)} error={errors.email}
        />
        <PasswordInput
          id="password" label={t('pw_label')} lang={lang}
          placeholder={t('pw_min_ph')} value={pw}
          onChange={e => setPw(e.target.value)} error={errors.pw}
          showStrength
        />
        <PasswordInput
          id="password2" label={t('confirm_pw')} lang={lang}
          placeholder={t('pw_ph')} value={pw2}
          onChange={e => setPw2(e.target.value)} error={errors.pw2}
        />

        <Button type="submit" loading={loading}>{t('reg_btn')}</Button>

        <div className="text-center small">
          {t('have_account')}{' '}
          <button type="button" className="link" onClick={() => navigate('login')}>
            {t('sign_in')}
          </button>
        </div>
      </form>
    </div>
  )
}
