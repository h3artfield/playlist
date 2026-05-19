import { useEffect, useMemo, useState } from 'react'
import SchedulerApp from './SchedulerApp'
import { fetchCatalog, fetchJson } from './api'
import './App.css'

type PageId = 'create' | 'blank' | 'archive' | 'edit'

type CatalogRow = {
  content_type?: string
  display_name?: string
  episode_code?: string
  episode_number?: string
  episode_title?: string
  genre?: string
  semantic_group?: string
  availability_status?: string
  source_sheet?: string
}

type ContentCategory = 'series' | 'movie' | 'paid_programming'

type BaseScheduleSummary = {
  path: string
  label: string
  week_count: number
  show_count: number
  ready_to_generate: boolean
}

const NAV_ITEMS: Array<{ id: PageId; label: string }> = [
  { id: 'create', label: 'Create Schedule' },
  { id: 'archive', label: 'Available Content' },
  { id: 'edit', label: 'Edit schedules' },
]

export default function App() {
  const [page, setPage] = useState<PageId>('create')
  const [baseLabel, setBaseLabel] = useState('Checking...')
  const [draftStationId, setDraftStationId] = useState('')

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

  useEffect(() => {
    let cancelled = false
    fetchJson<{ active: BaseScheduleSummary | null; schedules?: BaseScheduleSummary[] }>('/api/base-schedules')
      .then((payload) => {
        if (cancelled) return
        if (payload.active) {
          setBaseLabel(payload.active.label)
          return
        }
        if (payload.schedules?.length) {
          setBaseLabel('No schedule yet')
          return
        }
        setBaseLabel('No schedule yet')
      })
      .catch(() => {
        if (!cancelled) setBaseLabel('No schedule yet')
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="app-shell">
      <header className="main-header">
        <div>
          <span className="brand-kicker">Playlist</span>
          <h1>Schedule Builder</h1>
        </div>
        <div className="base-schedule-control">
          <span>Schedule</span>
          <button type="button">{baseLabel}</button>
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
              {item.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="app-content">
        {page === 'create' ? (
          <CreateSchedulePage
            onBlankSchedule={(stationId) => {
              setDraftStationId(stationId)
              setPage('blank')
            }}
          />
        ) : null}
        {page === 'blank' ? <SchedulerApp stationId={draftStationId} onBack={() => setPage('create')} /> : null}
        {page === 'archive' ? <ArchivePage /> : null}
        {page === 'edit' ? <EditSchedulePage /> : null}
      </main>
    </div>
  )
}

function CreateSchedulePage({ onBlankSchedule }: { onBlankSchedule: (stationId: string) => void }) {
  const [apiStatus, setApiStatus] = useState('Checking local API...')
  const [baseStatus, setBaseStatus] = useState('Checking for a saved base schedule...')
  const [activeBase, setActiveBase] = useState<BaseScheduleSummary | null>(null)
  const [stationId, setStationId] = useState('')
  const [stationIdError, setStationIdError] = useState('')

  useEffect(() => {
    let cancelled = false
    Promise.all([
      fetchJson<{ status: string }>('/api/health'),
      fetchJson<{ active: BaseScheduleSummary | null; count: number; ready_count: number }>('/api/base-schedules'),
    ])
      .then(([health, bases]) => {
        if (cancelled) return
        setApiStatus(`Local API is ${health.status}`)
        setActiveBase(bases.active)
        if (bases.active) {
          setBaseStatus(`${bases.active.label} found with ${bases.active.week_count} week${bases.active.week_count === 1 ? '' : 's'}`)
        } else if (bases.count) {
          setBaseStatus('Builder base schedule found, but it has no weeks yet.')
        } else {
          setBaseStatus('No builder-created base schedule found yet.')
        }
      })
      .catch(() => {
        if (!cancelled) {
          setApiStatus('Local API is not running yet')
          setBaseStatus('Start the local API to check for saved base schedules.')
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="app-page">
      <section className="create-panel">
        <div>
          <h2>Create a schedule</h2>
        </div>
        <div className="create-actions">
          <label className="station-id-field">
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
        <section className="build-panel">
          <div>
            <h3>Auto generate schedule</h3>
            <p>{baseStatus}</p>
            <p>{apiStatus}</p>
          </div>
          <button className="primary-action card-action" type="button">
            Auto Generate
          </button>
        </section>
      ) : (
        <section className="build-panel disabled-panel" aria-disabled="true">
          <h2>Auto generate schedule</h2>
          <button className="primary-action card-action" type="button" disabled>
            Create Schedule
          </button>
        </section>
      )}
    </main>
  )
}

function ArchivePage() {
  const [rows, setRows] = useState<CatalogRow[]>([])
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('Loading content catalog...')
  const [category, setCategory] = useState<ContentCategory>('series')
  const [expandedName, setExpandedName] = useState('')

  useEffect(() => {
    let cancelled = false
    fetchCatalog<{ rows?: CatalogRow[] }>()
      .then((payload: { rows?: CatalogRow[] }) => {
        if (cancelled) return
        const nextRows = Array.isArray(payload.rows) ? payload.rows : []
        setRows(nextRows)
        setStatus(`${nextRows.length.toLocaleString()} content rows loaded`)
      })
      .catch(() => {
        if (!cancelled) setStatus('Catalog not available yet')
      })
    return () => {
      cancelled = true
    }
  }, [])

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
    <main className="app-page">
      <section className="page-header">
        <div>
          <p className="eyebrow">Available Content</p>
          <h1>Available Content</h1>
          <p>{status}</p>
        </div>
        <div className="stat-pill">{summary.names.toLocaleString()} content names</div>
      </section>

      <section className="tool-panel">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search shows, movies, episodes, genres" />
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
      </section>

      <section className="archive-list">
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
                    {contentCategoryLabel(category)} · {first.genre || first.semantic_group || 'unlabeled'} · {group.length.toLocaleString()}{' '}
                    {category === 'series' ? 'episodes' : 'items'}
                  </small>
                </span>
                <b>{isOpen ? 'Hide' : 'Open'}</b>
              </button>
              {isOpen ? (
                <div className="episode-list">
                  {group.slice(0, 250).map((row, index) => (
                    <div className="episode-row" key={`${name}-${row.episode_title}-${index}`}>
                      <span>{row.episode_code || row.episode_number || index + 1}</span>
                      <strong>{row.episode_title || row.display_name || 'Untitled'}</strong>
                      <small>{row.availability_status || 'available'}</small>
                    </div>
                  ))}
                </div>
              ) : null}
            </article>
          )
        })}
        {!groupedResults.length ? (
          <article className="archive-row">
            <strong>No content found</strong>
            <span>Try another category or search term.</span>
          </article>
        ) : null}
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

function EditSchedulePage() {
  return (
    <main className="app-page">
      <section className="page-header">
        <div>
          <p className="eyebrow">Edit Schedule</p>
          <h1>Existing Schedule Editor</h1>
          <p>This page will load existing BINGE/GRIDS files through the Python block adapter and open them in the visual calendar.</p>
        </div>
      </section>
      <section className="workflow-grid">
        <div className="workflow-card static">
          <span>Import existing files</span>
          <small>Upload BINGE.xlsx and BINGE GRIDS.xlsx, then convert them to editable React blocks.</small>
        </div>
        <div className="workflow-card static">
          <span>Edit blocks visually</span>
          <small>Use the same click, delete, replace, and rule analysis tools as the blank builder.</small>
        </div>
        <div className="workflow-card static">
          <span>Regenerate outputs</span>
          <small>Save back to GRIDS and run the Python export engine.</small>
        </div>
      </section>
    </main>
  )
}
