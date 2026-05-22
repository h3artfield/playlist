import { useEffect, useState } from 'react'

type Props = {
  currentName: string
  busy?: boolean
  onConfirm: (newName: string) => void
  onCancel: () => void
}

export default function RenameShowDialog({ currentName, busy = false, onConfirm, onCancel }: Props) {
  const [newName, setNewName] = useState(currentName)

  useEffect(() => {
    setNewName(currentName)
  }, [currentName])

  const trimmed = newName.trim()
  const canConfirm = Boolean(trimmed) && trimmed !== currentName.trim() && !busy

  return (
    <div className="confirm-overlay" role="presentation" onClick={onCancel}>
      <section
        className="confirm-dialog"
        role="dialog"
        aria-labelledby="rename-show-title"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (!canConfirm) return
            onConfirm(trimmed)
          }}
        >
          <header className="confirm-dialog-header">
            <h2 id="rename-show-title">Rename content</h2>
          </header>
          <p className="confirm-dialog-lead">
            Update the catalog title for <strong>{currentName}</strong>. Saved schedules keep the old name on existing
            blocks until you edit them.
          </p>
          <label className="delete-confirm-field">
            <span>New title</span>
            <input
              type="text"
              value={newName}
              autoComplete="off"
              autoFocus
              spellCheck={false}
              disabled={busy}
              onChange={(event) => setNewName(event.target.value)}
            />
          </label>
          <footer className="settings-panel-footer">
            <button className="ghost-action" type="button" disabled={busy} onClick={onCancel}>
              Cancel
            </button>
            <button className="primary-action" type="submit" disabled={!canConfirm}>
              {busy ? 'Saving…' : 'Rename'}
            </button>
          </footer>
        </form>
      </section>
    </div>
  )
}
