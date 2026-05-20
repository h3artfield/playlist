import { useEffect, useMemo, useState } from 'react'
import SchedulerApp from './SchedulerApp'
import { fetchCatalog, fetchJson } from './api'
import { checkScheduleApi } from './scheduleApiBase'
import ContentSheetEditor, { catalogRowsToEditable } from './ContentSheetEditor'
import ImportWizard from './ImportWizard'
import type { CommitImportResponse } from './contentImportTypes'
import {
  clearScheduleDraft,
  confirmAutoGenerate,
  formatScheduleWeekRange,
  formatWeekCountLabel,
  normalizeAutoGenerateResult,
  savedScheduleWeekCount,
} from './scheduleImport'
import './App.css'

type PageId = 'create' | 'blank' | 'archive' | 'schedules'

type CatalogRow = {
  content_type?: string
  display_name?: string
  episode_code?: string
  episode_key?: string
  episode_number?: string
  episode_title?: string
  genre?: string
  semantic_group?: string
  availability_status?: string
  original_airdate?: string
  runtime_minutes?: number | null
  synopsis_long?: string
  source_sheet?: string
  source_file?: string
}

type ContentCategory = 'series' | 'movie' | 'paid_programming'

type BaseScheduleSummary = {
  path: string
  label: string
  station_id?: string
  week_count: number
  template_week_count?: number
  week_monday?: string
  created_at?: string
  draft_block_count?: number
  show_count: number
  ready_to_generate: boolean
}

type BaseSchedulesResponse = {
  count: number
  ready_count: number
  schedules: BaseScheduleSummary[]
  active: BaseScheduleSummary | null
}

type GeneratedBlock = {
  id: string
  episodeId: string
  title: string
  start: string
  end: string
  show: string
  genre: string
  contentType: 'Series / show' | 'Movie / special' | 'Paid programming'
  runtimeMinutes: number
  episodeCode: string
  episodeTitle: string
}

type AutoGenerateResult = {
  station_id: string
  week_monday: string
  week_count: number
  blocks: GeneratedBlock[]
}

const NAV_ITEMS: Array<{ id: PageId; label: string }> = [
  { id: 'create', label: 'Create Schedule' },
  { id: 'archive', label: 'Available Content' },
  { id: 'schedules', label: 'Schedule' },
]

function scheduleTimestamp(schedule: BaseScheduleSummary): number {
  if (schedule.created_at) {
    const parsed = Date.parse(schedule.created_at)
    if (!Number.isNaN(parsed)) return parsed
  }
  const match = schedule.path.match(/(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})/)
  if (match) {
    const parsed = Date.parse(`${match[1]}T${match[2].replace(/-/g, ':')}:00`)
    if (!Number.isNaN(parsed)) return parsed
  }
  return 0
}

function sortSchedulesNewestFirst(schedules: BaseScheduleSummary[]): BaseScheduleSummary[] {
  return [...schedules].sort((a, b) => scheduleTimestamp(b) - scheduleTimestamp(a))
}

function newestReadySchedule(schedules: BaseScheduleSummary[]): BaseScheduleSummary | null {
  const ready = sortSchedulesNewestFirst(schedules.filter((item) => item.ready_to_generate))
  return ready[0] || null
}

function pickSchedule(schedules: BaseScheduleSummary[], preferPath?: string): BaseScheduleSummary | null {
  const ready = schedules.filter((item) => item.ready_to_generate)
  if (!ready.length) return null
  if (preferPath) {
    const match = ready.find((item) => item.path === preferPath)
    if (match) return match
  }
  return newestReadySchedule(schedules)
}

function scheduleSavedLabel(schedule: BaseScheduleSummary): string {
  if (schedule.created_at) {
    const parsed = new Date(schedule.created_at)
    if (!Number.isNaN(parsed.getTime())) {
      return parsed.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
    }
  }
  const match = schedule.path.match(/(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})/)
  if (!match) return schedule.path
  const [datePart, timePart] = match[1].split('_')
  return `${datePart.replace(/-/g, '/')} ${timePart.replace(/-/g, ':')}`
}

export default function App() {
  const [page, setPage] = useState<PageId>('create')
  const [draftStationId, setDraftStationId] = useState('')
  const [generatedSchedule, setGeneratedSchedule] = useState<AutoGenerateResult | null>(null)
  const [builderSessionKey, setBuilderSessionKey] = useState(0)
  const [savedSchedules, setSavedSchedules] = useState<BaseScheduleSummary[]>([])
  const [selectedSchedule, setSelectedSchedule] = useState<BaseScheduleSummary | null>(null)
  const [schedulesStatus, setSchedulesStatus] = useState('Loading saved schedules...')

  useEffect(() => {
    function requestDesktopShutdown() {
      const url = '/api/desktop/shutdown'
      if (navigator.sendBeacon) {
        navigator.sendBeacon(url, new Blob([], { type: 'text/plain' }))
        return
      }
      void fetch(url, { method: 'POST', keepalive: true }).catch(() => undefined)
    }

    window.addEventListener('pagehide', requestDesktopShutdown)
    return () => window.removeEventListener('pagehide', requestDesktopShutdown)
  }, [])

  const refreshSchedules = async (preferPath?: string) => {
    try {
      const payload = await fetchJson<BaseSchedulesResponse>('/api/base-schedules')
      const sorted = sortSchedulesNewestFirst(payload.schedules || [])
      const ready = sorted.filter((item) => item.ready_to_generate)
      setSavedSchedules(ready)
      const picked = pickSchedule(payload.schedules || [], preferPath)
      setSelectedSchedule(picked)
      setSchedulesStatus(
        ready.length
          ? `${ready.length} saved schedule${ready.length === 1 ? '' : 's'} ready for auto-generate. Newest is selected by default.`
          : 'No saved schedules yet. Build one, then use Save Schedule on the results page.',
      )
    } catch {
      setSavedSchedules([])
      setSelectedSchedule(null)
      setSchedulesStatus('Start the local API to load saved schedules.')
    }
  }

  useEffect(() => {
    void refreshSchedules()
  }, [])

  function selectSchedule(schedule: BaseScheduleSummary) {
    setSelectedSchedule(schedule)
  }

  return (
    <div className="app-shell">
      <header className="main-header">
        <div>
          <span className="brand-kicker">Playlist</span>
          <h1>Schedule Builder</h1>
        </div>
      </header>

      <nav className="top-nav" aria-label="Application sections">
        <div className="segmented-nav">
          {NAV_ITEMS.map((item) => (
            <button
              className={page === item.id || (page === 'blank' && item.id === 'create') ? 'active' : ''}
              key={item.id}
              type="button"
              onClick={() => setPage(item.id)}
            >
              {item.id === 'schedules' && selectedSchedule
                ? `${item.label}: ${selectedSchedule.station_id || selectedSchedule.label.replace(/^Station\s+/i, '')}`
                : item.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="app-content">
        {page === 'create' ? (
          <CreateSchedulePage
            activeBase={selectedSchedule}
            onBlankSchedule={(stationId) => {
              setDraftStationId(stationId)
              setGeneratedSchedule(null)
              setBuilderSessionKey((key) => key + 1)
              setPage('blank')
            }}
            onAutoGenerate={(result) => {
              setDraftStationId(result.station_id)
              setGeneratedSchedule(result)
              setBuilderSessionKey((key) => key + 1)
              setPage('blank')
            }}
            onOpenSchedulePicker={() => setPage('schedules')}
          />
        ) : null}
        {page === 'blank' ? (
          <SchedulerApp
            key={`builder-${builderSessionKey}`}
            stationId={draftStationId}
            initialBlocks={generatedSchedule?.blocks}
            initialStartDate={generatedSchedule?.week_monday}
            initialScheduleLengthWeeks={generatedSchedule?.week_count}
            importKey={generatedSchedule ? builderSessionKey : undefined}
            onBack={() => {
              setGeneratedSchedule(null)
              setPage('create')
            }}
            onBaseSaved={(path) => void refreshSchedules(path)}
          />
        ) : null}
        {page === 'archive' ? <ArchivePage /> : null}
        {page === 'schedules' ? (
          <SchedulesPage
            schedules={savedSchedules}
            selectedPath={selectedSchedule?.path || ''}
            status={schedulesStatus}
            onSelect={(schedule) => {
              selectSchedule(schedule)
              setPage('create')
            }}
            onRefresh={() => void refreshSchedules()}
          />
        ) : null}
      </main>
    </div>
  )
}

function CreateSchedulePage({
  activeBase,
  onBlankSchedule,
  onAutoGenerate,
  onOpenSchedulePicker,
}: {
  activeBase: BaseScheduleSummary | null
  onBlankSchedule: (stationId: string) => void
  onAutoGenerate: (result: AutoGenerateResult) => void
  onOpenSchedulePicker: () => void
}) {
  const [stationId, setStationId] = useState('')
  const [stationIdError, setStationIdError] = useState('')
  const [autoStatus, setAutoStatus] = useState('')
  const [isAutoGenerating, setIsAutoGenerating] = useState(false)
  const [autoGenerateWeeks, setAutoGenerateWeeks] = useState(1)

  const savedWeeks = activeBase ? savedScheduleWeekCount(activeBase) : 1

  async function autoGenerateSchedule() {
    if (!activeBase) return
    if (!confirmAutoGenerate(savedWeeks, autoGenerateWeeks)) return

    setIsAutoGenerating(true)
    setAutoStatus('Loading saved schedule and continuing episodes...')
    try {
      const health = await fetchJson<{ features?: { auto_generate_weeks?: boolean } }>('/api/health')
      if (!health.features?.auto_generate_weeks) {
        throw new Error(
          'The API on port 8765 is out of date. Close Schedule Builder if it is open, then from the playlist folder run: .\\scripts\\start-dev-api.ps1 â€” or: python -m binge_schedule.cli serve',
        )
      }
      const raw = await fetchJson<AutoGenerateResult>('/api/schedule/auto-generate', {
        method: 'POST',
        body: JSON.stringify({ base_path: activeBase.path, week_count: autoGenerateWeeks }),
      })
      const result = normalizeAutoGenerateResult(raw, {
        requestedWeeks: autoGenerateWeeks,
        baseWeekMonday: activeBase.week_monday,
        baseTemplateWeeks: activeBase.template_week_count || activeBase.week_count || 1,
        templateBlockCount: activeBase.draft_block_count,
      })
      clearScheduleDraft(result.station_id)
      setAutoStatus('')
      onAutoGenerate(result)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Auto generate failed.'
      setAutoStatus(message)
    } finally {
      setIsAutoGenerating(false)
    }
  }

  return (
    <main className="app-page">
      <section className="create-panel">
        <div>
          <h2>Create a schedule</h2>
        </div>
        <div className="create-actions">
          <label className="schedule-field station-id-field">
            <span>Station ID</span>
            <input
              type="text"
              value={stationId}
              aria-invalid={Boolean(stationIdError)}
              required
              onChange={(event) => {
                setStationId(event.target.value)
                if (stationIdError) setStationIdError('')
              }}
            />
            {stationIdError ? <small>{stationIdError}</small> : null}
          </label>
          <button
            className="primary-action card-action"
            type="button"
            onClick={() => {
              const cleaned = stationId.trim()
              if (!cleaned) {
                setStationIdError('Required')
                return
              }
              onBlankSchedule(cleaned)
            }}
          >
            New Schedule
          </button>
        </div>
      </section>

      {activeBase ? (
        <section className="create-panel">
          <div>
            <h2>Auto generate schedule</h2>
            {autoStatus ? <p className="panel-status-error">{autoStatus}</p> : null}
          </div>
          <div className="create-actions">
            <label className="schedule-field week-count-field">
              <span>Weeks</span>
              <select
                value={autoGenerateWeeks}
                disabled={isAutoGenerating}
                onChange={(event) => setAutoGenerateWeeks(Number(event.target.value))}
              >
                {[1, 2, 3, 4].map((weeks) => (
                  <option key={weeks} value={weeks}>
                    {weeks} week{weeks === 1 ? '' : 's'}
                  </option>
                ))}
              </select>
            </label>
            <button className="primary-action card-action" type="button" disabled={isAutoGenerating} onClick={autoGenerateSchedule}>
              {isAutoGenerating ? 'Generating...' : 'Auto Generate'}
            </button>
          </div>
        </section>
      ) : (
        <section className="create-panel disabled-panel" aria-disabled="true">
          <div>
            <h2>Auto generate schedule</h2>
            <p className="muted">Select a saved schedule on the Schedule tab first.</p>
          </div>
          <div className="create-actions create-actions--solo">
            <button className="primary-action card-action" type="button" onClick={onOpenSchedulePicker}>
              Choose schedule
            </button>
          </div>
        </section>
      )}
    </main>
  )
}

function ArchivePage() {
  const [rows, setRows] = useState<CatalogRow[]>([])
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<ContentCategory>('series')
  const [expandedName, setExpandedName] = useState('')
  const [addContentOpen, setAddContentOpen] = useState(false)
  const [addMode, setAddMode] = useState<'manual' | 'upload'>('manual')
  const [importStatus, setImportStatus] = useState('')
  const [isImporting, setIsImporting] = useState(false)
  const [contentType, setContentType] = useState<ContentCategory>('series')
  const [showName, setShowName] = useState('')
  const [episodeNumber, setEpisodeNumber] = useState('')
  const [episodeTitle, setEpisodeTitle] = useState('')
  const [runtimeMinutes, setRuntimeMinutes] = useState('')
  const [genre, setGenre] = useState('')
  async function reloadCatalog() {
    const payload = await fetchCatalog<{ rows?: CatalogRow[] }>()
    const nextRows = Array.isArray(payload.rows) ? payload.rows : []
    setRows(nextRows)
    return nextRows
  }

  useEffect(() => {
    void checkScheduleApi()
    void reloadCatalog()
  }, [])

  async function submitManualImport() {
    setIsImporting(true)
    setImportStatus('')
    try {
      const result = await fetchJson<{ imported_count?: number; catalog_row_count?: number }>('/api/content/import', {
        method: 'POST',
        body: JSON.stringify({
          content_type: contentType,
          show_name: showName.trim(),
          episode_number: episodeNumber.trim(),
          episode_title: episodeTitle.trim(),
          runtime_minutes: runtimeMinutes.trim() ? Number(runtimeMinutes) : null,
          genre: genre.trim(),
        }),
      })
      await reloadCatalog()
      setShowName('')
      setEpisodeNumber('')
      setEpisodeTitle('')
      setRuntimeMinutes('')
      setGenre('')
      setImportStatus(
        `Added ${result.imported_count ?? 1} row(s). Catalog now has ${(result.catalog_row_count ?? 0).toLocaleString()} rows.`,
      )
    } catch (error) {
      setImportStatus(error instanceof Error ? error.message : 'Could not add content.')
    } finally {
      setIsImporting(false)
    }
  }

  function handleImportComplete(result: CommitImportResponse) {
    void reloadCatalog().then(() => {
      const stats = result.match_stats
      const detail = stats
        ? ` (${[stats.new_shows ? `${stats.new_shows} new shows` : '', stats.new_episodes ? `${stats.new_episodes} new episodes` : '', stats.updates ? `${stats.updates} updates` : '']
            .filter(Boolean)
            .join(', ')})`
        : ''
      setImportStatus(
        `Imported ${(result.imported_count ?? result.imported_row_count ?? 0).toLocaleString()} row(s)${detail}. Catalog now has ${(result.catalog_row_count ?? 0).toLocaleString()} rows.`,
      )
    })
  }

  const summary = useMemo(() => {
    const names = new Set(rows.map((row) => row.display_name).filter(Boolean))
    const byType = new Map<string, number>()
    for (const row of rows) {
      const type = contentCategory(row)
      byType.set(type, (byType.get(type) || 0) + 1)
    }
    return { names: names.size, byType }
  }, [rows])

  const groupedResults = useMemo(() => {
    const q = query.trim().toLowerCase()
    const filtered = (q
      ? rows.filter((row) =>
          [row.display_name, row.episode_title, row.genre, row.semantic_group, row.source_sheet]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(q)),
        )
      : rows
    ).filter((row) => contentCategory(row) === category)
    const groups = new Map<string, CatalogRow[]>()
    for (const row of filtered) {
      const name = row.display_name || 'Untitled'
      if (!groups.has(name)) groups.set(name, [])
      groups.get(name)?.push(row)
    }
    return [...groups.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(0, 120)
  }, [category, query, rows])

  const categoryCounts = useMemo(() => {
    const namesByCategory = new Map<ContentCategory, Set<string>>([
      ['series', new Set()],
      ['movie', new Set()],
      ['paid_programming', new Set()],
    ])
    for (const row of rows) {
      const name = row.display_name
      if (name) namesByCategory.get(contentCategory(row))?.add(name)
    }
    return {
      series: namesByCategory.get('series')?.size || 0,
      movie: namesByCategory.get('movie')?.size || 0,
      paid_programming: namesByCategory.get('paid_programming')?.size || 0,
    }
  }, [rows])

  return (
    <main className="app-page content-page">
      <section className={`create-panel add-content-panel${addContentOpen ? ' is-open' : ''}`}>
        <button className="add-content-toggle" type="button" onClick={() => setAddContentOpen((open) => !open)}>
          <div>
            <h2>Add content</h2>
          </div>
          <span className="add-content-toggle-label">{addContentOpen ? 'Hide' : 'Show'}</span>
        </button>
        {addContentOpen ? (
          <div className="add-content-body">
            <div className="content-tabs add-content-tabs">
              <button className={addMode === 'manual' ? 'active' : ''} type="button" onClick={() => setAddMode('manual')}>
                Manual entry
              </button>
              <button className={addMode === 'upload' ? 'active' : ''} type="button" onClick={() => setAddMode('upload')}>
                Upload file
              </button>
            </div>
            {addMode === 'manual' ? (
              <div className="add-content-form">
                <div className="add-content-row">
                  <label className="schedule-field add-field-type">
                    <span>Type</span>
                    <select value={contentType} onChange={(event) => setContentType(event.target.value as ContentCategory)}>
                      <option value="series">Series</option>
                      <option value="movie">Movie / special</option>
                      <option value="paid_programming">Paid programming</option>
                    </select>
                  </label>
                  <label className="schedule-field add-field-grow">
                    <span>{contentType === 'series' ? 'Series name' : 'Title'}</span>
                    <input value={showName} onChange={(event) => setShowName(event.target.value)} />
                  </label>
                  {contentType === 'series' ? (
                    <label className="schedule-field add-field-narrow">
                      <span>Episode #</span>
                      <input value={episodeNumber} onChange={(event) => setEpisodeNumber(event.target.value)} />
                    </label>
                  ) : null}
                </div>
                {contentType === 'series' ? (
                  <div className="add-content-row">
                    <label className="schedule-field add-field-full">
                      <span>Episode title</span>
                      <input value={episodeTitle} onChange={(event) => setEpisodeTitle(event.target.value)} />
                    </label>
                  </div>
                ) : null}
                <div className="add-content-row add-content-row-footer">
                  <label className="schedule-field add-field-narrow">
                    <span>Runtime (min)</span>
                    <input
                      type="number"
                      placeholder="30"
                      value={runtimeMinutes}
                      onChange={(event) => setRuntimeMinutes(event.target.value)}
                    />
                  </label>
                  <label className="schedule-field add-field-medium">
                    <span>Genre</span>
                    <input value={genre} onChange={(event) => setGenre(event.target.value)} placeholder="Optional" />
                  </label>
                  <button
                    className="primary-action card-action add-content-submit"
                    type="button"
                    disabled={isImporting || !showName.trim()}
                    onClick={() => void submitManualImport()}
                  >
                    {isImporting ? 'Adding...' : 'Add content'}
                  </button>
                </div>
              </div>
            ) : (
              <ImportWizard
                catalogRows={rows}
                uploadActive={addContentOpen && addMode === 'upload'}
                onClose={() => setImportStatus('')}
                onImported={(result) => {
                  setIsImporting(false)
                  handleImportComplete(result)
                }}
              />
            )}
            {importStatus ? <p className="panel-status-error import-status-ok">{importStatus}</p> : null}
          </div>
        ) : null}
      </section>

      <section className="available-content-section">
        <header className="available-content-header">
          <div>
            <h2>Available Content</h2>
          </div>
          <div className="stat-pill">{summary.names.toLocaleString()} content names</div>
        </header>

        <div className="available-content-toolbar">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search shows, movies, episodes, genres"
          />
          <div className="content-tabs">
            <button className={category === 'series' ? 'active' : ''} type="button" onClick={() => setCategory('series')}>
              Series <span>{categoryCounts.series.toLocaleString()}</span>
            </button>
            <button className={category === 'movie' ? 'active' : ''} type="button" onClick={() => setCategory('movie')}>
              Movies <span>{categoryCounts.movie.toLocaleString()}</span>
            </button>
            <button
              className={category === 'paid_programming' ? 'active' : ''}
              type="button"
              onClick={() => setCategory('paid_programming')}
            >
              Paid Programming <span>{categoryCounts.paid_programming.toLocaleString()}</span>
            </button>
          </div>
        </div>

        <div className="available-content-list">
          {groupedResults.map(([name, group]) => {
            const isOpen = expandedName === name
            const first = group[0]
            return (
              <article className="archive-row grouped" key={name}>
                <button
                  className="archive-row-header"
                  type="button"
                  onClick={() => setExpandedName(isOpen ? '' : name)}
                >
                  <span>
                    <strong>{name}</strong>
                    <small>
                      {contentCategoryLabel(category)} · {first.genre || first.semantic_group || 'unlabeled'} ·{' '}
                      {group.length.toLocaleString()} {category === 'series' ? 'episodes' : 'items'}
                    </small>
                  </span>
                  <b>{isOpen ? 'Hide sheet' : 'Edit sheet'}</b>
                </button>
                {isOpen ? (
                  <ContentSheetEditor
                    showName={name}
                    contentType={first.content_type || category}
                    sourceSheet={first.source_sheet}
                    rows={catalogRowsToEditable(name, group)}
                    onSaved={() => void reloadCatalog()}
                  />
                ) : null}
              </article>
            )
          })}
          {!groupedResults.length ? (
            <article className="archive-row archive-row-empty">
              <strong>No content found</strong>
              <span>Try another category or search term.</span>
            </article>
          ) : null}
        </div>
      </section>
    </main>
  )
}

function contentCategory(row: CatalogRow): ContentCategory {
  const raw = String(row.content_type || '').toLowerCase()
  if (raw === 'movie' || raw === 'movies' || raw === 'movie / special') return 'movie'
  if (raw === 'paid_programming' || raw === 'paid programming') return 'paid_programming'
  if (raw === 'literal') {
    const group = String(row.genre || row.semantic_group || '').toLowerCase()
    return group === 'ministry' || group === 'paid' ? 'paid_programming' : 'series'
  }
  return 'series'
}

function contentCategoryLabel(category: ContentCategory): string {
  if (category === 'movie') return 'Movie'
  if (category === 'paid_programming') return 'Paid Programming'
  return 'Series'
}

function SchedulesPage({
  schedules,
  selectedPath,
  status,
  onSelect,
  onRefresh,
}: {
  schedules: BaseScheduleSummary[]
  selectedPath: string
  status: string
  onSelect: (schedule: BaseScheduleSummary) => void
  onRefresh: () => void
}) {
  return (
    <main className="app-page schedules-page">
      <section className="page-header schedule-page-header">
        <div>
          <p className="eyebrow">Schedule</p>
          <h1>Saved schedules</h1>
          <p>{status}</p>
        </div>
        <button className="ghost-action" type="button" onClick={onRefresh}>
          Refresh
        </button>
      </section>

      {schedules.length ? (
        <section className="schedule-picker-list" aria-label="Saved schedules">
          {schedules.map((schedule) => {
            const weeks = savedScheduleWeekCount(schedule)
            const range = formatScheduleWeekRange(schedule.week_monday, weeks)
            const isSelected = schedule.path === selectedPath
            return (
              <button
                key={schedule.path}
                type="button"
                className={`schedule-picker-card${isSelected ? ' is-selected' : ''}`}
                onClick={() => onSelect(schedule)}
              >
                <div className="schedule-picker-card-head">
                  <strong>{schedule.label}</strong>
                  {isSelected ? <span className="schedule-picker-badge">Active</span> : null}
                </div>
                <span>
                  {formatWeekCountLabel(weeks)}
                  {range ? ` · ${range}` : ''}
                </span>
                <small>Saved {scheduleSavedLabel(schedule)}</small>
              </button>
            )
          })}
        </section>
      ) : (
        <section className="create-panel create-panel--simple">
          <p className="muted">Save a schedule from the builder results page to use it here for auto-generate.</p>
        </section>
      )}
    </main>
  )
}
