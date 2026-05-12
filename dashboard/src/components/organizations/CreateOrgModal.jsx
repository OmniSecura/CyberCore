import { useState } from 'react'
import { orgApi } from '../../api/endpoints'

function toSlug(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
}

export function CreateOrgModal({ onClose, onCreate }) {
  const [name, setName]       = useState('')
  const [desc, setDesc]       = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  const slug = toSlug(name)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    setError(null)
    try {
      await orgApi.create({
        organization_name:        name.trim(),
        organization_slug:        slug,
        organization_description: desc.trim() || undefined,
      })
      onCreate()
    } catch (err) {
      setError(err?.data?.detail || 'Failed to create organization.')
      setLoading(false)
    }
  }

  return (
    <div className="cc-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="cc-modal" role="dialog" aria-modal="true">
        {/* Head */}
        <div className="cc-modal-head">
          <div>
            <div className="cc-modal-title">New organization</div>
            <div className="cc-modal-sub">Set up a workspace for your team or project.</div>
          </div>
          <button className="cc-modal-x" onClick={onClose} aria-label="Close">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M3 3l10 10M13 3L3 13"/>
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit}>
          <div className="cc-modal-body">
            {error && (
              <div className="cc-alert cc-alert--err">
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="8" cy="8" r="6"/><path d="M8 5v3M8 11v.5"/>
                </svg>
                {error}
              </div>
            )}

            <div className="cc-mfield">
              <label htmlFor="org-name">
                Name <span style={{ color: '#E53E3E' }}>*</span>
              </label>
              <input
                id="org-name"
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Acme Corp"
                autoFocus
                autoComplete="off"
                maxLength={80}
              />
              {slug && (
                <div className="cc-slug-hint">
                  <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10 6l2-2a2.83 2.83 0 0 0-4-4L4 4a2.83 2.83 0 0 0 0 4l1 1"/>
                    <path d="M6 10l-2 2a2.83 2.83 0 0 0 4 4l4-4a2.83 2.83 0 0 0 0-4l-1-1"/>
                  </svg>
                  Slug: <code>{slug}</code>
                </div>
              )}
            </div>

            <div className="cc-mfield">
              <label htmlFor="org-desc">
                Description{' '}
                <span style={{ color: '#8899AA', fontWeight: 400 }}>optional</span>
              </label>
              <textarea
                id="org-desc"
                value={desc}
                onChange={e => setDesc(e.target.value)}
                placeholder="What does this organization do?"
                rows={3}
                maxLength={400}
              />
            </div>
          </div>

          {/* Footer */}
          <div className="cc-modal-foot">
            <button
              type="button"
              className="cc-btn cc-btn-md cc-btn-ghost"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="cc-btn cc-btn-md cc-btn-primary"
              disabled={loading || !name.trim()}
            >
              {loading ? (
                <><span className="cc-spin" /> Creating…</>
              ) : (
                <>
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
                    <path d="M8 2v12M2 8h12"/>
                  </svg>
                  Create organization
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
