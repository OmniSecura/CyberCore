import { SidePanel } from './SidePanel'

export function AuthLayout({ lang, setLang, children }) {
  return (
    <div className="root">
      <SidePanel lang={lang} setLang={setLang} />
      <div className="main">
        {children}
      </div>
    </div>
  )
}
