import { fetchJson } from './api'

export type AppTheme = 'dark' | 'light'
export type DesktopWindowMode = 'fullscreen' | 'windowed'

export type AppSettings = {
  theme: AppTheme
  accent_primary: string
  accent_secondary: string
  primary_save_directory: string
  backup_save_directory: string
  backup_enabled: boolean
  desktop_window_mode?: DesktopWindowMode
  desktop_runtime?: boolean
  settings_file?: string
  desktop_window_applied?: boolean
}

const STORAGE_KEY = 'schedule-builder-settings'

export const DEFAULT_SETTINGS: AppSettings = {
  theme: 'dark',
  accent_primary: '#2563eb',
  accent_secondary: '#7c3aed',
  primary_save_directory: '',
  backup_save_directory: '',
  backup_enabled: true,
  desktop_window_mode: 'windowed',
}

type HealthPayload = {
  primary_save_directory?: string
  features?: { app_settings?: boolean }
}

function mergeSettings(partial: Partial<AppSettings>, primaryFallback = ''): AppSettings {
  const mode = partial.desktop_window_mode === 'fullscreen' ? 'fullscreen' : 'windowed'
  return {
    ...DEFAULT_SETTINGS,
    ...partial,
    desktop_window_mode: mode,
    primary_save_directory:
      partial.primary_save_directory?.trim() || primaryFallback || DEFAULT_SETTINGS.primary_save_directory,
  }
}

async function primaryPathFromHealth(): Promise<string> {
  try {
    const health = await fetchJson<HealthPayload>('/api/health')
    return health.primary_save_directory?.trim() || ''
  } catch {
    return ''
  }
}

export function loadCachedSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...DEFAULT_SETTINGS }
    const parsed = JSON.parse(raw) as Partial<AppSettings>
    return mergeSettings(parsed)
  } catch {
    return { ...DEFAULT_SETTINGS }
  }
}

export function cacheSettings(settings: AppSettings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
}

export function applySettingsToDocument(settings: AppSettings): void {
  const root = document.documentElement
  const theme = settings.theme === 'light' ? 'light' : 'dark'
  root.dataset.theme = theme
  root.style.colorScheme = theme
  root.style.setProperty('--sb-accent-start', settings.accent_primary)
  root.style.setProperty('--sb-accent-end', settings.accent_secondary)
  root.style.setProperty(
    '--sb-accent-gradient',
    `linear-gradient(135deg, ${settings.accent_primary}, ${settings.accent_secondary})`,
  )
}

export async function fetchAppSettings(): Promise<AppSettings> {
  const healthPrimary = await primaryPathFromHealth()
  try {
    const remote = await fetchJson<AppSettings>('/api/settings')
    const merged = mergeSettings(remote, healthPrimary)
    cacheSettings(merged)
    applySettingsToDocument(merged)
    return merged
  } catch {
    const cached = loadCachedSettings()
    const merged = mergeSettings(cached, healthPrimary)
    cacheSettings(merged)
    applySettingsToDocument(merged)
    return merged
  }
}

export async function saveAppSettings(settings: AppSettings): Promise<AppSettings> {
  const saved = await fetchJson<AppSettings>('/api/settings', {
    method: 'POST',
    body: JSON.stringify(settings),
  })
  const merged = mergeSettings(saved)
  cacheSettings(merged)
  applySettingsToDocument(merged)
  return merged
}

export async function pickSettingsDirectory(kind: 'primary' | 'backup'): Promise<string> {
  const payload = await fetchJson<{ path: string }>('/api/settings/pick-directory', {
    method: 'POST',
    body: JSON.stringify({ kind }),
  })
  return payload.path || ''
}
