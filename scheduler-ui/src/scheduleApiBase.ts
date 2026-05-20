const ENV_BASE = import.meta.env.VITE_API_BASE || ''
const DEV_FALLBACK = 'http://127.0.0.1:8765'

let resolvedBase = ENV_BASE
let apiAvailable = false
let importWizardAvailable = false

export type ScheduleApiHealth = {
  status?: string
  features?: {
    auto_generate_weeks?: boolean
    auto_generate_date_shift?: boolean
    content_import_wizard?: boolean
  }
}

/** Vite dev server (any port) or preview — always use same-origin /api (proxy). */
function preferSameOriginApi(): boolean {
  if (import.meta.env.DEV) return true
  if (typeof window === 'undefined') return false
  const port = window.location.port
  return port === '5173' || port === '5174' || port === '4173' || port === '8765'
}

export function getScheduleApiBase(): string {
  return resolvedBase
}

export function isScheduleApiAvailable(): boolean {
  return apiAvailable
}

export function isImportWizardAvailable(): boolean {
  return importWizardAvailable
}

function healthUrl(base: string): string {
  const path = '/api/health'
  if (!base) return path
  return `${base.replace(/\/$/, '')}${path}`
}

function apiCandidates(): string[] {
  if (ENV_BASE) return [ENV_BASE]
  if (typeof window !== 'undefined') {
    const origin = window.location.origin
    if (preferSameOriginApi()) return [origin]
    return [origin, DEV_FALLBACK]
  }
  return ['', DEV_FALLBACK]
}

async function probeHealth(base: string): Promise<ScheduleApiHealth | null> {
  try {
    const response = await fetch(healthUrl(base), {
      method: 'GET',
      cache: 'no-store',
    })
    if (!response.ok) return null
    return (await response.json()) as ScheduleApiHealth
  } catch {
    return null
  }
}

export async function resolveScheduleApiBase(): Promise<string> {
  apiAvailable = false
  importWizardAvailable = false

  for (const base of apiCandidates()) {
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const health = await probeHealth(base)
      if (health?.status === 'ok') {
        const sameOrigin = typeof window !== 'undefined' && base === window.location.origin
        resolvedBase = sameOrigin || base === '' ? '' : base
        apiAvailable = true
        importWizardAvailable = health.features?.content_import_wizard === true
        return resolvedBase
      }
      if (attempt < 2) {
        await new Promise((resolve) => setTimeout(resolve, 200))
      }
    }
  }

  resolvedBase = ENV_BASE || ''
  return resolvedBase
}

export async function checkScheduleApi(): Promise<boolean> {
  await resolveScheduleApiBase()
  return apiAvailable
}

export async function checkImportWizardApi(): Promise<boolean> {
  await resolveScheduleApiBase()
  return apiAvailable && importWizardAvailable
}

export function importWizardApiError(): string {
  const onDesktopPort =
    typeof window !== 'undefined' &&
    (window.location.port === '8765' || window.location.hostname === '127.0.0.1')
  if (!apiAvailable) {
    if (onDesktopPort) {
      return 'Cannot reach the schedule API. Close Schedule Builder completely, reopen it from the Start menu, then refresh this page.'
    }
    return 'Cannot reach the schedule API. Start it with: .\\scripts\\start-dev-api.ps1 (port 8765), then refresh this page.'
  }
  if (onDesktopPort) {
    return 'File import is not available in this build. Reinstall the latest Schedule Builder desktop app, then try again.'
  }
  return 'The API on port 8765 is running old code (file import not loaded). Close Schedule Builder if it is open, run .\\scripts\\start-dev-api.ps1 from the project folder, then refresh.'
}

/** Same-origin /api in dev (Vite proxy). Avoids CORS failures on POST after health via :8765. */
export function scheduleApiUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`
  const base = getScheduleApiBase()
  if (!base) return normalized
  return `${base.replace(/\/$/, '')}${normalized}`
}

export async function scheduleApiFetch(path: string, init?: RequestInit): Promise<Response> {
  if (!apiAvailable) {
    await resolveScheduleApiBase()
  }
  return fetch(scheduleApiUrl(path), init)
}
