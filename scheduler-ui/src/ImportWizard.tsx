import { useCallback, useEffect, useMemo, useState } from 'react'
import { formatFetchError } from './api'
import ImportFormatGuide from './ImportFormatGuide'
import { checkImportWizardApi, importWizardApiError } from './scheduleApiBase'
import { analyzeImportSheet, commitImport, fetchImportSampleRows, parseImportFile, previewImport } from './contentImportApi'
import type {
  CanonicalField,
  CommitImportResponse,
  PreviewImportResponse,
  PreviewRow,
  RowKind,
  SheetAnalysis,
  SheetConfig,
} from './contentImportTypes'
import {
  catalogEpisodeCountByShow,
  normalizeShowKey,
  sheetToConfig,
  type CatalogRow,
} from './contentImportTypes'

type ImportWizardProps = {
  catalogRows: CatalogRow[]
  uploadActive: boolean
  onClose: () => void
  onImported: (result: CommitImportResponse) => void
}

function configsFromSheets(sheets: SheetAnalysis[]): SheetConfig[] {
  return sheets.map(sheetToConfig)
}

function formatShowSummary(summary: {
  show_name: string
  in_catalog: boolean
  catalog_episode_count: number
  new_episodes: number
  updates: number
  is_new_show: boolean
}): string {
  if (summary.is_new_show) return 'New show'
  if (!summary.in_catalog) return 'Not in catalog yet'
  const parts: string[] = [`Already in catalog · ${summary.catalog_episode_count.toLocaleString()} episodes`]
  if (summary.new_episodes) parts.push(`${summary.new_episodes} new`)
  if (summary.updates) parts.push(`${summary.updates} updates`)
  return parts.join(' · ')
}

function formatPreviewSlot(row: PreviewRow): string {
  const slot = row.grid_slot_minutes ?? row.slot_minutes
  if (slot == null) return '—'
  return String(slot)
}

export default function ImportWizard({ catalogRows, uploadActive, onClose, onImported }: ImportWizardProps) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [filename, setFilename] = useState('')
  const [fields, setFields] = useState<CanonicalField[]>([])
  const [sheets, setSheets] = useState<SheetAnalysis[]>([])
  const [configs, setConfigs] = useState<SheetConfig[]>([])
  const [activeSheet, setActiveSheet] = useState('')
  const [preview, setPreview] = useState<PreviewImportResponse | null>(null)
  const [mapSampleRows, setMapSampleRows] = useState<PreviewRow[]>([])
  const [step, setStep] = useState<'pick' | 'map' | 'review'>('pick')
  const [apiReady, setApiReady] = useState<boolean | null>(null)

  const includedConfigs = useMemo(() => configs.filter((c) => c.include), [configs])
  const titleMappingReady = useMemo(
    () => includedConfigs.some((config) => Boolean(config.mapping.title?.trim())),
    [includedConfigs],
  )
  const importBlockers = useMemo(() => {
    if (!includedConfigs.length) return 'Select at least one sheet to include.'
    if (!titleMappingReady) return 'Map the episode or movie title column for at least one included sheet.'
    if (preview && !preview.can_import) {
      const errorIssues = preview.issues.filter((issue) => issue.level === 'error')
      if (errorIssues.length) {
        const first = errorIssues[0]
        return `${first.sheet}${first.row ? ` row ${first.row}` : ''}: ${first.message}`
      }
      if (!preview.ready_count) return 'No rows are ready to import. Check header row and column mapping.'
    }
    return ''
  }, [includedConfigs.length, preview, titleMappingReady])
  const activeConfig = useMemo(
    () => configs.find((c) => c.sheet_name === activeSheet) ?? configs[0],
    [activeSheet, configs],
  )
  const activeAnalysis = useMemo(
    () => sheets.find((s) => s.name === activeSheet) ?? sheets[0],
    [activeSheet, sheets],
  )

  const updateConfig = useCallback((sheetName: string, patch: Partial<SheetConfig>) => {
    setConfigs((prev) => prev.map((c) => (c.sheet_name === sheetName ? { ...c, ...patch } : c)))
    setPreview(null)
  }, [])

  const updateMapping = useCallback(
    (sheetName: string, key: string, column: string) => {
      setConfigs((prev) =>
        prev.map((c) => {
          if (c.sheet_name !== sheetName) return c
          return { ...c, mapping: { ...c.mapping, [key]: column } }
        }),
      )
      setPreview(null)
    },
    [],
  )

  async function recheckApi() {
    setApiReady(null)
    const ready = await checkImportWizardApi()
    setApiReady(ready)
    if (ready) setError('')
    return ready
  }

  useEffect(() => {
    if (!uploadActive) return
    void recheckApi()
  }, [uploadActive])

  async function handleFile(file: File) {
    setBusy(true)
    setError('')
    setPreview(null)
    setFilename(file.name)
    setStep('map')
    try {
      const parsed = await parseImportFile(file)
      setSessionId(parsed.session_id)
      setFilename(parsed.filename)
      setFields(parsed.fields)
      setSheets(parsed.sheets)
      const nextConfigs = configsFromSheets(parsed.sheets)
      setConfigs(nextConfigs)
      const firstIncluded = parsed.sheets.find((s) => s.include) ?? parsed.sheets[0]
      setActiveSheet(firstIncluded?.name ?? '')
      void refreshPreviewQuiet(parsed.session_id, nextConfigs)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not read file.'
      setError(message)
      void recheckApi()
      if (!sessionId) setStep('pick')
    } finally {
      setBusy(false)
    }
  }

  async function refreshPreviewQuiet(sid: string, sheetConfigs: SheetConfig[]) {
    if (!sheetConfigs.some((c) => c.include)) return
    try {
      const result = await previewImport(sid, sheetConfigs)
      setPreview(result)
    } catch {
      /* catalog preview is optional on first load */
    }
  }

  async function refreshPreview() {
    if (!sessionId || !includedConfigs.length) return
    setBusy(true)
    setError('')
    try {
      const result = await previewImport(sessionId, configs)
      setPreview(result)
      setStep('review')
    } catch (err) {
      setError(formatFetchError(err))
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (!sessionId || !activeConfig) return
    let cancelled = false
    const timer = window.setTimeout(() => {
      void analyzeImportSheet(sessionId, activeConfig.sheet_name, activeConfig.header_row)
        .then((analysis) => {
          if (cancelled) return
          setSheets((prev) => prev.map((s) => (s.name === analysis.name ? { ...s, ...analysis } : s)))
          setConfigs((prev) =>
            prev.map((c) => {
              if (c.sheet_name !== analysis.name) return c
              const mapping = { ...c.mapping }
              for (const [key, column] of Object.entries(analysis.suggested_mapping)) {
                if (!mapping[key] && column) mapping[key] = column
              }
              return {
                ...c,
                mapping,
                layout: analysis.layout,
                data_start_row: analysis.data_start_row,
                inferred_column_names: analysis.inferred_column_names,
              }
            }),
          )
        })
        .catch(() => undefined)
    }, 350)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [sessionId, activeConfig?.sheet_name, activeConfig?.header_row])

  const activeConfigSnapshot = useMemo(() => JSON.stringify(activeConfig ?? null), [activeConfig])

  useEffect(() => {
    if (!sessionId || !activeConfig || step !== 'map') return
    if (!activeConfig.mapping.title) {
      setMapSampleRows([])
      return
    }
    let cancelled = false
    const timer = window.setTimeout(() => {
      void fetchImportSampleRows(sessionId, activeConfig)
        .then((rows) => {
          if (!cancelled) setMapSampleRows(rows)
        })
        .catch(() => {
          if (!cancelled) setMapSampleRows([])
        })
    }, 350)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [sessionId, step, activeConfigSnapshot])

  const configsSnapshot = useMemo(() => JSON.stringify(configs), [configs])

  useEffect(() => {
    if (!sessionId || step === 'pick' || !titleMappingReady || !includedConfigs.length) return
    let cancelled = false
    const timer = window.setTimeout(() => {
      void previewImport(sessionId, configs)
        .then((result) => {
          if (cancelled) return
          setPreview(result)
          if (result.can_import) setStep((current) => (current === 'map' ? 'review' : current))
        })
        .catch((err) => {
          if (!cancelled) setError(formatFetchError(err))
        })
    }, 700)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [sessionId, step, configsSnapshot, titleMappingReady, includedConfigs.length])

  async function handleCommit() {
    if (!sessionId) return
    setBusy(true)
    setError('')
    try {
      if (!preview) {
        const result = await previewImport(sessionId, configs)
        setPreview(result)
        if (!result.can_import) {
          const errorIssues = result.issues.filter((issue) => issue.level === 'error')
          const detail = errorIssues[0]
            ? `${errorIssues[0].sheet}${errorIssues[0].row ? ` row ${errorIssues[0].row}` : ''}: ${errorIssues[0].message}`
            : 'Fix mapping errors before importing.'
          setError(detail)
          setStep('review')
          return
        }
      } else if (!preview.can_import) {
        setError(importBlockers || 'Fix mapping errors before importing.')
        return
      }
      const result = await commitImport(sessionId, configs)
      onImported(result)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed.')
    } finally {
      setBusy(false)
    }
  }

  function applyMappingToAll() {
    if (!activeConfig) return
    const { header_row, row_kind, default_series_title, mapping } = activeConfig
    setConfigs((prev) =>
      prev.map((c) =>
        c.include
          ? {
              ...c,
              header_row,
              row_kind,
              mapping: { ...mapping },
              default_series_title: c.row_kind === 'series' || row_kind === 'series' ? c.default_series_title || default_series_title : c.default_series_title,
            }
          : c,
      ),
    )
    setPreview(null)
  }

  const columnOptions = useMemo(() => {
    const cols = activeAnalysis?.source_columns ?? []
    return ['', ...cols]
  }, [activeAnalysis])

  const catalogCounts = useMemo(() => catalogEpisodeCountByShow(catalogRows), [catalogRows])

  const normalizedPreviewRows = mapSampleRows.length ? mapSampleRows : activeAnalysis?.sample_rows ?? []

  const sheetCatalogHint = useMemo(() => {
    if (!activeConfig) return null
    for (const candidate of [activeConfig.default_series_title, activeConfig.sheet_name]) {
      const key = normalizeShowKey(candidate)
      if (!key) continue
      const count = catalogCounts.get(key)
      if (count) {
        return { name: candidate.trim() || activeConfig.sheet_name, count }
      }
    }
    return null
  }, [activeConfig, catalogCounts])

  const apiErrorMessage = importWizardApiError()

  if (step === 'pick') {
    return (
      <div className="import-wizard">
        {apiReady === null ? <p className="muted import-api-checking">Checking API connection...</p> : null}
        {apiReady === false ? (
          <div className="import-api-error">
            <p className="panel-status-error">{apiErrorMessage}</p>
            <button className="ghost-action" type="button" disabled={busy} onClick={() => void recheckApi()}>
              Retry connection
            </button>
          </div>
        ) : null}
        <ImportFormatGuide />
        <p className="add-content-file-label">CSV or Excel file</p>
        <div className="add-content-file-row">
          <input
            className="add-content-file-input"
            type="file"
            accept=".csv,.xlsx,.xls"
            disabled={busy}
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void handleFile(file)
              event.target.value = ''
            }}
          />
          <label className="add-content-file-button">
            {busy ? 'Reading file...' : 'Choose file'}
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              disabled={busy}
              hidden
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) void handleFile(file)
                event.target.value = ''
              }}
            />
          </label>
          <span className="add-content-file-hint muted">.csv, .xlsx, or .xls</span>
        </div>
        {error && error !== apiErrorMessage ? <p className="panel-status-error">{error}</p> : null}
      </div>
    )
  }

  return (
    <div className="import-wizard">
      <div className="import-wizard-head">
        <div>
          <strong>{filename}</strong>
          <p className="muted">
            {sheets.length === 1 ? '1 sheet' : `${sheets.length} sheets`} · map columns then preview before import
          </p>
        </div>
        <button className="ghost-action" type="button" onClick={onClose} disabled={busy}>
          Cancel
        </button>
      </div>

      <section className="import-sheet-list">
        <h3>Sheets in file</h3>
        {busy && !sheets.length ? <p className="muted">Reading workbook and detecting columns...</p> : null}
        <div className="import-sheet-table">
          {sheets.map((sheet) => {
            const config = configs.find((c) => c.sheet_name === sheet.name)
            const included = config?.include ?? false
            const mappedCount = sheet.mapping_summary?.length ?? 0
            return (
              <div className={`import-sheet-row${activeSheet === sheet.name ? ' active' : ''}`} key={sheet.name}>
                <label className="import-sheet-include">
                  <input
                    type="checkbox"
                    checked={included}
                    onChange={(event) => updateConfig(sheet.name, { include: event.target.checked })}
                  />
                </label>
                <button className="import-sheet-name" type="button" onClick={() => setActiveSheet(sheet.name)}>
                  <span>{sheet.name}</span>
                  <small>
                    {sheet.data_row_count.toLocaleString()} rows ·{' '}
                    {sheet.header_row === 0 || sheet.layout === 'inferred'
                      ? 'columns inferred from data'
                      : `header row ${sheet.header_row}`}{' '}
                    · {mappedCount} fields mapped
                    {sheet.skip_reason ? ` · ${sheet.skip_reason}` : ''}
                  </small>
                </button>
                <span className={`import-sheet-status${included ? '' : ' muted'}`}>{included ? 'Include' : 'Skip'}</span>
              </div>
            )
          })}
        </div>
      </section>

      {activeConfig && activeAnalysis ? (
        <section className="import-map-panel">
          <div className="import-map-toolbar">
            <div>
              <h3>{sheets.length > 1 ? `Map: ${activeConfig.sheet_name}` : 'Map columns'}</h3>
              {sheetCatalogHint ? (
                <p className="import-catalog-hint">
                  <span className="catalog-detected">Show detected</span> — {sheetCatalogHint.name} already has{' '}
                  {sheetCatalogHint.count.toLocaleString()} episodes in catalog. New rows will add episodes or update matches.
                </p>
              ) : activeConfig.default_series_title || activeConfig.sheet_name ? (
                <p className="import-catalog-hint muted">No matching show in catalog yet — import will add as new content.</p>
              ) : null}
            </div>
            {sheets.length > 1 ? (
              <button className="ghost-action" type="button" onClick={applyMappingToAll} disabled={busy}>
                Apply mapping to all included sheets
              </button>
            ) : null}
          </div>

          <div className="import-map-options">
            <label className="schedule-field add-field-narrow">
              <span>Header row (0 = infer)</span>
              <input
                type="number"
                min={0}
                max={20}
                value={activeConfig.header_row}
                onChange={(event) =>
                  updateConfig(activeConfig.sheet_name, { header_row: Math.max(0, Number(event.target.value) || 0) })
                }
              />
            </label>
            <label className="schedule-field add-field-type">
              <span>Rows are</span>
              <select
                value={activeConfig.row_kind}
                onChange={(event) => updateConfig(activeConfig.sheet_name, { row_kind: event.target.value as RowKind })}
              >
                <option value="auto">Auto-detect</option>
                <option value="series">Series</option>
                <option value="movie">Movies / specials</option>
              </select>
            </label>
            {activeConfig.row_kind !== 'movie' ? (
              <label className="schedule-field add-field-grow">
                <span>Default series title</span>
                <input
                  value={activeConfig.default_series_title}
                  onChange={(event) => updateConfig(activeConfig.sheet_name, { default_series_title: event.target.value })}
                  placeholder={activeConfig.sheet_name}
                />
              </label>
            ) : null}
          </div>

          {activeAnalysis?.mapping_summary?.length ? (
            <div className="import-normalize-panel">
              <h4>Auto-detected mapping</h4>
              <div className="import-normalize-mapping">
                {activeAnalysis.mapping_summary.map((item) => (
                  <div className="import-normalize-map-row" key={item.field}>
                    <span>{item.field}</span>
                    <span>→</span>
                    <strong>{item.column}</strong>
                  </div>
                ))}
              </div>
              {normalizedPreviewRows.length ? (
                <>
                  <h4>Normalized preview (first rows)</h4>
                  <div className="import-preview-table-wrap">
                    <table className="import-preview-table">
                      <thead>
                        <tr>
                          <th>Show</th>
                          <th>Ep #</th>
                          <th>Title</th>
                          <th>TRT</th>
                          <th>Slot</th>
                        </tr>
                      </thead>
                      <tbody>
                        {normalizedPreviewRows.map((row, index) => (
                          <tr key={`${row.display_name}-${index}`}>
                            <td>{row.display_name}</td>
                            <td>{row.episode_number || '—'}</td>
                            <td>{row.episode_title || '—'}</td>
                            <td>{row.runtime_minutes ?? '—'}</td>
                            <td>{formatPreviewSlot(row)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <p className="muted">Map episode or movie title to see normalized rows.</p>
              )}
            </div>
          ) : null}

          <div className="import-map-grid">
            {fields.map((field) => {
              const match = activeAnalysis.mapping_match[field.key] ?? 'unmapped'
              const value = activeConfig.mapping[field.key] ?? ''
              return (
                <label className="schedule-field import-map-field" key={field.key}>
                  <span>
                    {field.label}
                    {field.required ? ' *' : ''}
                    {value ? <em className={`match-${match}`}>{match}</em> : null}
                  </span>
                  <select value={value} onChange={(event) => updateMapping(activeConfig.sheet_name, field.key, event.target.value)}>
                    {columnOptions.map((col) => (
                      <option key={col || 'none'} value={col}>
                        {col || '(ignore)'}
                      </option>
                    ))}
                  </select>
                </label>
              )
            })}
          </div>
        </section>
      ) : null}

      {step === 'review' && preview ? (
        <section className="import-preview-panel">
          <div className="import-preview-stats">
            <span className="stat-pill">{preview.ready_count.toLocaleString()} ready</span>
            {preview.match_stats?.new_shows ? (
              <span className="stat-pill">{preview.match_stats.new_shows} new shows</span>
            ) : null}
            {preview.match_stats?.new_episodes ? (
              <span className="stat-pill">{preview.match_stats.new_episodes.toLocaleString()} new episodes</span>
            ) : null}
            {preview.match_stats?.updates ? (
              <span className="stat-pill warn">{preview.match_stats.updates.toLocaleString()} updates</span>
            ) : null}
            {preview.match_stats?.new_movies ? (
              <span className="stat-pill">{preview.match_stats.new_movies} new movies</span>
            ) : null}
            {preview.warning_count ? <span className="stat-pill warn">{preview.warning_count} warnings</span> : null}
            {preview.skipped_count ? <span className="stat-pill warn">{preview.skipped_count} skipped</span> : null}
            {preview.error_count ? <span className="stat-pill error">{preview.error_count} errors</span> : null}
          </div>
          {preview.show_summaries?.length ? (
            <ul className="import-show-summary-list">
              {preview.show_summaries.slice(0, 12).map((summary) => (
                <li key={summary.show_name}>
                  <strong>{summary.show_name}</strong>
                  <span>{formatShowSummary(summary)}</span>
                </li>
              ))}
            </ul>
          ) : null}
          {preview.issues.length ? (
            <ul className="import-issue-list">
              {preview.issues.slice(0, 12).map((issue, index) => (
                <li key={`${issue.sheet}-${issue.row}-${index}`}>
                  <strong>{issue.sheet}</strong>
                  {issue.row ? ` row ${issue.row}` : ''}: {issue.message}
                </li>
              ))}
            </ul>
          ) : null}
          <div className="import-preview-table-wrap">
            <table className="import-preview-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Show</th>
                  <th>Ep #</th>
                  <th>Title</th>
                  <th>TRT</th>
                  <th>Slot</th>
                  <th>Status</th>
                  <th>Genre</th>
                  <th>Sheet</th>
                </tr>
              </thead>
              <tbody>
                {preview.preview_rows.map((row, index) => (
                  <tr key={`${row.display_name}-${index}`}>
                    <td>{row.content_type}</td>
                    <td>{row.display_name}</td>
                    <td>{row.episode_number || '—'}</td>
                    <td>{row.episode_title || '—'}</td>
                    <td>{row.runtime_minutes ?? '—'}</td>
                    <td>{formatPreviewSlot(row)}</td>
                    <td>
                      {row.catalog_match_label ? (
                        <span className={`catalog-match catalog-match--${row.catalog_match ?? 'unknown'}`}>
                          {row.catalog_match_label}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>{row.genre || '—'}</td>
                    <td>{row.source_sheet || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {preview.ready_count > preview.preview_rows.length ? (
            <p className="muted">Showing first {preview.preview_rows.length} of {preview.ready_count.toLocaleString()} rows.</p>
          ) : null}
        </section>
      ) : null}

      {error ? (
        <div className="import-api-error">
          <p className="panel-status-error">{error}</p>
          <button className="ghost-action" type="button" disabled={busy} onClick={() => setError('')}>
            Dismiss
          </button>
        </div>
      ) : null}

      <div className="import-wizard-actions">
        {step === 'review' ? (
          <button className="ghost-action" type="button" disabled={busy} onClick={() => setStep('map')}>
            Back to mapping
          </button>
        ) : null}
        <button
          className="ghost-action"
          type="button"
          disabled={busy || !includedConfigs.length || !titleMappingReady}
          onClick={() => void refreshPreview()}
        >
          {busy ? 'Working...' : 'Preview import'}
        </button>
        <button
          className="primary-action card-action"
          type="button"
          disabled={busy || !includedConfigs.length || !titleMappingReady}
          onClick={() => void handleCommit()}
        >
          {busy ? 'Importing...' : `Import ${(preview?.ready_count ?? '…').toLocaleString()} rows`}
        </button>
      </div>
      {importBlockers && !busy ? <p className="muted import-blocker-hint">{importBlockers}</p> : null}
    </div>
  )
}
