const API_BASE = import.meta.env.VITE_API_BASE || ''

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
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
