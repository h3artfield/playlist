import { useEffect, useState } from 'react'
import type { AppSettings, AppTheme, DesktopWindowMode } from './settings'
import {
  applySettingsToDocument,
  DEFAULT_SETTINGS,
  fetchAppSettings,
  pickSettingsDirectory,
  saveAppSettings,
} from './settings'

type SettingsPanelProps = {
  open: boolean
  initial: AppSettings
  onClose: () => void
  onSaved: (settings: AppSettings) => void
}

export default function SettingsPanel({ open, initial, onClose, onSaved }: SettingsPanelProps) {
  const [draft, setDraft] = useState<AppSettings>(initial)
  const [status, setStatus] = useState('')
  const [saving, setSaving] = useState(false)
  const [picking, setPicking] = useState<'primary' | 'backup' | ''>('')

  useEffect(() => {
    if (open) {
      setDraft(initial)
      setStatus('')
    }
  }, [open, initial])

  if (!open) return null

  async function browse(kind: 'primary' | 'backup') {
    setPicking(kind)
    setStatus('')
    try {
      const path = await pickSettingsDirectory(kind)
      if (!path) return
      setDraft((prev) =>
        kind === 'primary' ? { ...prev, primary_save_directory: path } : { ...prev, backup_save_directory: path },
      )
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not open folder picker.'
      setStatus(
        message.includes('Not Found') || message.includes('Method Not Allowed')
          ? 'Restart the dev API (scripts/start-dev-api.ps1) or reopen the desktop app, then try again.'
          : message,
      )
    } finally {
      setPicking('')
    }
  }

  async function handleSave() {
    setSaving(true)
    setStatus('')
    try {
      const saved = await saveAppSettings(draft)
      onSaved(saved)
      onClose()
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not save settings.'
      setStatus(
        message.includes('Not Found') || message.includes('Method Not Allowed')
          ? 'Restart the dev API (scripts/start-dev-api.ps1) or reopen the desktop app, then try again.'
          : message,
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="settings-overlay" role="presentation" onClick={onClose}>
      <section
        className="settings-panel"
        role="dialog"
        aria-labelledby="settings-title"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="settings-panel-header">
          <div>
            <p className="eyebrow">Preferences</p>
            <h2 id="settings-title">Settings</h2>
          </div>
          <button className="settings-close" type="button" aria-label="Close settings" onClick={onClose}>
            ×
          </button>
        </header>

        <div className="settings-section">
          <h3>Appearance</h3>
          <div className="settings-theme-toggle">
            {(['dark', 'light'] as AppTheme[]).map((theme) => (
              <button
                key={theme}
                type="button"
                className={draft.theme === theme ? 'active' : ''}
                onClick={() => {
                  const next = { ...draft, theme }
                  setDraft(next)
                  applySettingsToDocument(next)
                }}
              >
                {theme === 'dark' ? 'Dark' : 'Light'}
              </button>
            ))}
          </div>
          <div className="settings-color-row">
            <label>
              <span>Primary color</span>
              <input
                type="color"
                value={draft.accent_primary}
                onChange={(event) => {
                  const next = { ...draft, accent_primary: event.target.value }
                  setDraft(next)
                  applySettingsToDocument(next)
                }}
              />
            </label>
            <label>
              <span>Secondary color</span>
              <input
                type="color"
                value={draft.accent_secondary}
                onChange={(event) => {
                  const next = { ...draft, accent_secondary: event.target.value }
                  setDraft(next)
                  applySettingsToDocument(next)
                }}
              />
            </label>
          </div>
          <button
            type="button"
            className="ghost-action"
            onClick={() => setDraft((prev) => ({
              ...prev,
              accent_primary: DEFAULT_SETTINGS.accent_primary,
              accent_secondary: DEFAULT_SETTINGS.accent_secondary,
            }))}
          >
            Reset colors
          </button>
        </div>

        {draft.desktop_runtime ? (
          <div className="settings-section">
            <h3>Desktop window</h3>
            <p className="settings-help">
              Windowed mode shows a normal window you can resize by dragging the edges or corners. Full screen
              fills your display. Changes apply right away.
            </p>
            <div className="settings-theme-toggle">
              {(['windowed', 'fullscreen'] as DesktopWindowMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  className={(draft.desktop_window_mode || 'windowed') === mode ? 'active' : ''}
                  onClick={() => setDraft((prev) => ({ ...prev, desktop_window_mode: mode }))}
                >
                  {mode === 'windowed' ? 'Windowed' : 'Full screen'}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <div className="settings-section">
          <h3>Save locations</h3>
          <p className="settings-help">
            Primary is where new schedules are saved (by default, next to the desktop app). Backup keeps a
            full copy of each save in a second folder if the primary drive fails.
          </p>
          <label className="settings-path-field">
            <span>Primary schedule save directory</span>
            <div className="settings-path-row">
              <input
                type="text"
                value={draft.primary_save_directory}
                placeholder="Choose a folder…"
                onChange={(event) =>
                  setDraft((prev) => ({ ...prev, primary_save_directory: event.target.value }))
                }
              />
              <button
                type="button"
                className="ghost-action"
                disabled={picking === 'primary'}
                onClick={() => void browse('primary')}
              >
                {picking === 'primary' ? '…' : 'Browse'}
              </button>
            </div>
          </label>
          <label className="settings-check">
            <input
              type="checkbox"
              checked={draft.backup_enabled}
              onChange={(event) => setDraft((prev) => ({ ...prev, backup_enabled: event.target.checked }))}
            />
            <span>Enable automatic backup copies</span>
          </label>
          <label className="settings-path-field">
            <span>Backup schedule save directory</span>
            <div className="settings-path-row">
              <input
                type="text"
                value={draft.backup_save_directory}
                placeholder="Optional second folder…"
                disabled={!draft.backup_enabled}
                onChange={(event) =>
                  setDraft((prev) => ({ ...prev, backup_save_directory: event.target.value }))
                }
              />
              <button
                type="button"
                className="ghost-action"
                disabled={!draft.backup_enabled || picking === 'backup'}
                onClick={() => void browse('backup')}
              >
                {picking === 'backup' ? '…' : 'Browse'}
              </button>
            </div>
          </label>
        </div>

        {status ? <p className="panel-status-error">{status}</p> : null}

        <footer className="settings-panel-footer">
          <button type="button" className="ghost-action" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="primary-action" disabled={saving} onClick={() => void handleSave()}>
            {saving ? 'Saving…' : 'Save settings'}
          </button>
        </footer>
      </section>
    </div>
  )
}
