const ERR_ICON = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>

export function Input({ id, label, error, children, ...inputProps }) {
  return (
    <div className="field">
      {label && <label htmlFor={id}>{label}</label>}
      <div className="input-wrap">
        <input id={id} className={error ? 'error' : ''} {...inputProps} />
        {children}
      </div>
      {error && (
        <div className="field-error">
          {ERR_ICON}
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}