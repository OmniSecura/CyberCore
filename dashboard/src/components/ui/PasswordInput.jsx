import { useState } from 'react'
import { Input } from './Input'

const EYE    = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
const EYE_OFF= <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>

function strength(pw) {
  if (!pw) return 0
  let s = 0
  if (pw.length >= 12) s++
  if (/[A-Z]/.test(pw)) s++
  if (/\d/.test(pw)) s++
  if (/[^A-Za-z0-9]/.test(pw)) s++
  return s
}

const STRENGTH_CLASS = ['', 'weak', 'medium', 'strong', 'strong']
const STRENGTH_LABEL = { en: ['', 'Weak', 'Fair', 'Good', 'Strong'], pl: ['', 'Słabe', 'Średnie', 'Dobre', 'Silne'] }

export function PasswordInput({ showStrength, lang = 'en', ...props }) {
  const [visible, setVisible] = useState(false)
  const s = showStrength ? strength(props.value || '') : 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <Input type={visible ? 'text' : 'password'} {...props}>
        <button
          type="button"
          className="eye-btn"
          tabIndex={-1}
          onClick={() => setVisible(v => !v)}
        >
          {visible ? EYE_OFF : EYE}
        </button>
      </Input>

      {showStrength && (
        <>
          <div className="pw-strength">
            {[1,2,3,4].map(i => (
              <div key={i} className={`pw-bar${i <= s ? ` ${STRENGTH_CLASS[s]}` : ''}`} />
            ))}
          </div>
          {props.value && (
            <div className="pw-label">{STRENGTH_LABEL[lang]?.[s] || STRENGTH_LABEL.en[s]}</div>
          )}
        </>
      )}
    </div>
  )
}
