import type { AutoGenerateConfirmCopy } from './scheduleImport'

type Props = {
  copy: AutoGenerateConfirmCopy
  onConfirm: () => void
  onCancel: () => void
}

export default function AutoGenerateConfirmDialog({ copy, onConfirm, onCancel }: Props) {
  return (
    <div className="confirm-overlay" role="presentation" onClick={onCancel}>
      <section
        className="confirm-dialog"
        role="dialog"
        aria-labelledby="auto-generate-confirm-title"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="confirm-dialog-header">
          <h2 id="auto-generate-confirm-title">{copy.title}</h2>
        </header>
        <p className="confirm-dialog-lead">{copy.lead}</p>
        <p className="settings-help">{copy.detail}</p>
        <footer className="settings-panel-footer">
          <button className="ghost-action" type="button" onClick={onCancel}>
            Cancel
          </button>
          <button className="primary-action" type="button" onClick={onConfirm}>
            Generate
          </button>
        </footer>
      </section>
    </div>
  )
}
