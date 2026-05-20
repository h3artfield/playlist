import { resolveScheduleApiBase, scheduleApiUrl } from './scheduleApiBase'

export { checkScheduleApi, resolveScheduleApiBase, scheduleApiUrl } from './scheduleApiBase'

export function formatFetchError(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error)
  if (message === 'Failed to fetch' || message.includes('NetworkError') || message.includes('fetch')) {
    return 'Cannot reach the schedule API. Start it with: .\\scripts\\start-dev-api.ps1 (port 8765), then refresh this page.'
  }
  return message
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  await resolveScheduleApiBase()
  const response = await fetch(scheduleApiUrl(path), {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    try {
      const parsed = JSON.parse(detail) as { detail?: string }
      if (typeof parsed.detail === 'string' && parsed.detail.trim()) {
        throw new Error(parsed.detail)
      }
    } catch (inner) {
      if (inner instanceof Error && inner.message !== detail) throw inner
    }
    throw new Error(detail || `HTTP ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function fetchCatalog<T>(): Promise<T> {
  try {
    return await fetchJson<T>('/api/content-catalog')
  } catch {
    const response = await fetch('/content-catalog.json')
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return response.json() as Promise<T>
  }
}

export async function uploadContentCatalog<T>(file: File): Promise<T> {
  await resolveScheduleApiBase()
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(scheduleApiUrl('/api/content/import/upload'), {
    method: 'POST',
    body: form,
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(detail || `HTTP ${response.status}`)
  }
  return response.json() as Promise<T>
}
