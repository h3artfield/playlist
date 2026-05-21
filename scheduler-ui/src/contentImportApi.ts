import { formatFetchError } from './api'
import {
  checkImportWizardApi,
  importWizardApiError,
  scheduleApiFetch,
} from './scheduleApiBase'
import type {
  CommitImportResponse,
  ParseImportResponse,
  PreviewImportResponse,
  PreviewRow,
  SheetConfig,
} from './contentImportTypes'

function parseErrorMessage(error: unknown, responseDetail: string): string {
  if (responseDetail) {
    try {
      const json = JSON.parse(responseDetail) as { detail?: string }
      if (json.detail) return json.detail
    } catch {
      /* plain text */
    }
    return responseDetail
  }
  return formatFetchError(error)
}

export async function parseImportFile(file: File): Promise<ParseImportResponse> {
  const ready = await checkImportWizardApi()
  if (!ready) {
    throw new Error(importWizardApiError())
  }

  const form = new FormData()
  form.append('file', file)
  try {
    const response = await scheduleApiFetch('/api/content/import/parse', {
      method: 'POST',
      body: form,
    })
    if (!response.ok) {
      const detail = await response.text().catch(() => '')
      if (response.status === 405) {
        throw new Error(importWizardApiError())
      }
      throw new Error(parseErrorMessage(new Error(`HTTP ${response.status}`), detail))
    }
    return response.json() as Promise<ParseImportResponse>
  } catch (error) {
    if (error instanceof Error) throw error
    throw new Error(formatFetchError(error))
  }
}

export async function analyzeImportSheet(
  sessionId: string,
  sheetName: string,
  headerRow: number,
): Promise<import('./contentImportTypes').SheetAnalysis> {
  const response = await scheduleApiFetch('/api/content/import/sheet', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, sheet_name: sheetName, header_row: headerRow }),
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(parseErrorMessage(new Error(`HTTP ${response.status}`), detail))
  }
  return response.json() as Promise<import('./contentImportTypes').SheetAnalysis>
}

export async function fetchImportSampleRows(sessionId: string, sheet: SheetConfig): Promise<PreviewRow[]> {
  const response = await scheduleApiFetch('/api/content/import/sample-rows', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, sheet }),
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(parseErrorMessage(new Error(`HTTP ${response.status}`), detail))
  }
  const payload = (await response.json()) as { sample_rows?: PreviewRow[] }
  return payload.sample_rows ?? []
}

export async function previewImport(sessionId: string, sheets: SheetConfig[]): Promise<PreviewImportResponse> {
  const response = await scheduleApiFetch('/api/content/import/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, sheets }),
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(parseErrorMessage(new Error(`HTTP ${response.status}`), detail))
  }
  return response.json() as Promise<PreviewImportResponse>
}

export async function commitImport(sessionId: string, sheets: SheetConfig[]): Promise<CommitImportResponse> {
  const response = await scheduleApiFetch('/api/content/import/commit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, sheets }),
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(parseErrorMessage(new Error(`HTTP ${response.status}`), detail))
  }
  return response.json() as Promise<CommitImportResponse>
}
