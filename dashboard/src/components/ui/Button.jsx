export function Button({ variant = 'primary', loading, children, ...props }) {
  return (
    <button className={`btn-${variant}`} disabled={loading || props.disabled} {...props}>
      {loading ? <span className="spinner" /> : children}
    </button>
  )
}
