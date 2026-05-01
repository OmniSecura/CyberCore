import { useState, useCallback } from 'react'
import en from '../i18n/en'
import pl from '../i18n/pl'

const LANGS = { en, pl }
const STORAGE_KEY = 'cc_lang'

export function useLang() {
  const [lang, setLangState] = useState(
    () => localStorage.getItem(STORAGE_KEY) || 'en'
  )

  const setLang = useCallback((l) => {
    localStorage.setItem(STORAGE_KEY, l)
    setLangState(l)
  }, [])

  const strings = LANGS[lang] || en

  // t('key') — simple string lookup
  const t = useCallback((key) => strings[key] ?? key, [strings])

  // tf('key', ...args) — supports function values like reg_ok(email)
  const tf = useCallback((key, ...args) => {
    const v = strings[key]
    return typeof v === 'function' ? v(...args) : (v ?? key)
  }, [strings])

  return { lang, setLang, t, tf }
}
