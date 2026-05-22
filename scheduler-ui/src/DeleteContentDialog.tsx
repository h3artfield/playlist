import { useState } from 'react'

type Props = {
  label: string
  detail: string
  busy?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export default function DeleteContentDialog({ label, detail, busy = false, onConfirm, onCancel }: Props) {
  const [confirmText, setConfirmText] = useState('')
  const canConfirm = confirmText.trim().toUpperCase() === 'DELETE' && !busy

  function submitDelete() {
    if (!canConfirm) return
    onConfirm()
  }

  return (
    <div className="confirm-overlay" role="presentation" onClick={onCancel}>
      <section
        className="confirm-dialog"
        role="dialog"
        aria-labelledby="delete-content-title"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <form
          onSubmit={(event) => {
            event.preventDefault()
            submitDelete()
          }}
        >
          <header className="confirm-dialog-header">
            <h2 id="delete-content-title">Delete from catalog?</h2>
          </header>
          <p className="confirm-dialog-lead">
            This permanently removes <strong>{label}</strong> from Available Content. {detail}
          </p>
          <label className="delete-confirm-field">
            <span>Type DELETE to confirm</span>
            <input
              type="text"
              value={confirmText}
              autoComplete="off"
              autoFocus
              spellCheck={false}
              disabled={busy}
              onChange={(event) => setConfirmText(event.target.value)}
            />
          </label>
          <footer className="settings-panel-footer">
            <button className="ghost-action" type="button" disabled={busy} onClick={onCancel}>
              Cancel
            </button>
            <button className="danger-action" type="submit" disabled={!canConfirm}>
              {busy ? 'Deleting…' : 'Delete content'}
            </button>
          </footer>
        </form>
      </section>
    </div>
  )
}
