import { useEffect, useMemo, useState } from 'react'
import { fetchJson } from './api'

export type EditableEpisodeRow = {
  row_id: string
  content_type: string
  episode_number: string
  episode_title: string
  episode_code: string
  runtime_minutes: string
  original_airdate: string
  genre: string
  synopsis_long: string
  source_sheet: string
  source_file: string
}

type ContentSheetEditorProps = {
  showName: string
  contentType: string
  sourceSheet?: string
  rows: EditableEpisodeRow[]
  onSaved: () => void
}

function newRowId() {
  return `new-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function catalogRowsToEditable(
  showName: string,
  rows: Array<{
    content_type?: string
    episode_number?: string
    episode_title?: string
    episode_code?: string
    runtime_minutes?: number | null
    original_airdate?: string
    genre?: string
    semantic_group?: string
    synopsis_long?: string
    source_sheet?: string
    source_file?: string
    episode_key?: string
  }>,
): EditableEpisodeRow[] {
  return rows.map((row, index) => ({
    row_id: row.episode_key || `${showName}-${index}`,
    content_type: row.content_type || 'series',
    episode_number: row.episode_number || '',
    episode_title: row.episode_title || '',
    episode_code: row.episode_code || '',
    runtime_minutes: row.runtime_minutes != null ? String(row.runtime_minutes) : '',
    original_airdate: row.original_airdate || '',
    genre: row.genre || row.semantic_group || '',
    synopsis_long: row.synopsis_long || '',
    source_sheet: row.source_sheet || '',
    source_file: row.source_file || '',
  }))
}

function editableToImportRows(showName: string, rows: EditableEpisodeRow[]) {
  return rows.map((row) => ({
    content_type: row.content_type || 'series',
    display_name: showName,
    series_title: showName,
    episode_number: row.episode_number.trim(),
    episode_title: row.episode_title.trim(),
    episode_code: row.episode_code.trim(),
    runtime_minutes: row.runtime_minutes.trim() ? Number(row.runtime_minutes) : null,
    original_airdate: row.original_airdate.trim(),
    genre: row.genre.trim(),
    synopsis_long: row.synopsis_long.trim(),
    source_sheet: row.source_sheet,
    source_file: row.source_file || 'schedule_builder',
  }))
}

export default function ContentSheetEditor({
  showName,
  contentType,
  sourceSheet,
  rows,
  onSaved,
}: ContentSheetEditorProps) {
  const [draft, setDraft] = useState<EditableEpisodeRow[]>(rows)
  const [status, setStatus] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setDraft(rows)
    setStatus('')
  }, [showName, rows])

  const dirty = useMemo(() => JSON.stringify(draft) !== JSON.stringify(rows), [draft, rows])

  function updateRow(rowId: string, patch: Partial<EditableEpisodeRow>) {
    setDraft((prev) => prev.map((row) => (row.row_id === rowId ? { ...row, ...patch } : row)))
  }

  function addRow() {
    setDraft((prev) => [
      ...prev,
      {
        row_id: newRowId(),
        content_type: contentType,
        episode_number: '',
        episode_title: '',
        episode_code: '',
        runtime_minutes: '',
        original_airdate: '',
        genre: prev[0]?.genre || '',
        synopsis_long: '',
        source_sheet: sourceSheet || prev[0]?.source_sheet || '',
        source_file: prev[0]?.source_file || 'schedule_builder',
      },
    ])
  }

  function removeRow(rowId: string) {
    setDraft((prev) => (prev.length <= 1 ? prev : prev.filter((row) => row.row_id !== rowId)))
  }

  async function save() {
    setSaving(true)
    setStatus('')
    try {
      const payload = editableToImportRows(showName, draft)
      const result = await fetchJson<{ saved_row_count?: number; catalog_row_count?: number }>(
        '/api/content/show-rows',
        {
          method: 'PUT',
          body: JSON.stringify({ display_name: showName, rows: payload }),
        },
      )
      setStatus(`Saved ${(result.saved_row_count ?? draft.length).toLocaleString()} row(s).`)
      onSaved()
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Could not save changes.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="content-sheet-editor">
      <div className="content-sheet-editor-head">
        <div>
          <strong>Sheet editor</strong>
          {sourceSheet ? <p className="muted">Source tab: {sourceSheet}</p> : null}
        </div>
        <div className="content-sheet-editor-actions">
          <button className="ghost-action" type="button" onClick={addRow} disabled={saving}>
            Add row
          </button>
          <button className="primary-action" type="button" onClick={() => void save()} disabled={saving || !dirty}>
            {saving ? 'Saving...' : 'Save sheet'}
          </button>
        </div>
      </div>

      <div className="content-sheet-table-wrap">
        <table className="content-sheet-table">
          <thead>
            <tr>
              <th>Ep #</th>
              <th>Episode title</th>
              <th>Code</th>
              <th>Runtime (min)</th>
              <th>Airdate</th>
              <th>Genre</th>
              <th>Synopsis</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {draft.map((row) => (
              <tr key={row.row_id}>
                <td>
                  <input
                    value={row.episode_number}
                    onChange={(e) => updateRow(row.row_id, { episode_number: e.target.value })}
                  />
                </td>
                <td>
                  <input
                    value={row.episode_title}
                    onChange={(e) => updateRow(row.row_id, { episode_title: e.target.value })}
                  />
                </td>
                <td>
                  <input value={row.episode_code} onChange={(e) => updateRow(row.row_id, { episode_code: e.target.value })} />
                </td>
                <td>
                  <input
                    type="number"
                    min={1}
                    value={row.runtime_minutes}
                    onChange={(e) => updateRow(row.row_id, { runtime_minutes: e.target.value })}
                  />
                </td>
                <td>
                  <input
                    value={row.original_airdate}
                    onChange={(e) => updateRow(row.row_id, { original_airdate: e.target.value })}
                  />
                </td>
                <td>
                  <input value={row.genre} onChange={(e) => updateRow(row.row_id, { genre: e.target.value })} />
                </td>
                <td>
                  <textarea
                    rows={2}
                    value={row.synopsis_long}
                    onChange={(e) => updateRow(row.row_id, { synopsis_long: e.target.value })}
                  />
                </td>
                <td>
                  <button className="ghost-action content-sheet-delete" type="button" onClick={() => removeRow(row.row_id)}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {status ? <p className={status.startsWith('Saved') ? 'panel-status-ok' : 'panel-status-error'}>{status}</p> : null}
    </div>
  )
}
