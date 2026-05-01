import { Button } from './Button'

const CHECK = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>

export function SuccessCard({ title, sub, btnLabel, onBtn }) {
  return (
    <div className="card" style={{ textAlign: 'center' }}>
      <div className="success-check">{CHECK}</div>
      <div className="card-title">{title}</div>
      <div className="card-sub" style={{ marginBottom: 28 }} dangerouslySetInnerHTML={{ __html: sub }} />
      <Button onClick={onBtn}>{btnLabel}</Button>
    </div>
  )
}