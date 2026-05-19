import { useEffect, useMemo, useRef, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import type {
  DateSelectArg,
  EventClickArg,
  EventContentArg,
  EventInput,
} from '@fullcalendar/core'
import { fetchCatalog, fetchJson } from './api'
import './SchedulerApp.css'

type Episode = {
  id: string
  show: string
  title: string
  code: string
  durationMinutes: number
  genre: string
  contentType: 'Series / show' | 'Movie / special' | 'Paid programming'
}

type ScheduledBlock = {
  id: string
  episodeId: string
  title: string
  start: string
  end: string
  show: string
  genre: string
  contentType: Episode['contentType']
  runtimeMinutes: number
  episodeCode: string
  episodeTitle: string
}

type TimeRange = {
  start: Date
  end: Date
}

type CanonicalContentRow = {
  content_type?: string
  series_key?: string
  display_name?: string
  episode_key?: string
  episode_code?: string
  episode_number?: string
  episode_title?: string
  runtime_minutes?: number | null
  binge_row_minutes?: number | null
  genre?: string
  semantic_group?: string
  availability_status?: string
}

type SuggestedRule = {
  rule_type: string
  show: string
  confidence: number
  summary: string
  payload: Record<string, unknown>
}

const SHOW_COLORS = [
  '#4f7cff',
  '#18a999',
  '#b15cff',
  '#f59e0b',
  '#ef476f',
  '#38bdf8',
  '#84cc16',
  '#f97316',
]

const CATALOG_SHOWS = [
  { show: 'The Adventures of Jim Bowie', prefix: 'AJB', durationMinutes: 30, genre: 'western' },
  { show: 'The Texan', prefix: 'TEX', durationMinutes: 30, genre: 'western' },
  { show: 'Hunter', prefix: 'HUN', durationMinutes: 60, genre: 'action_drama' },
  { show: 'Renegade', prefix: 'REN', durationMinutes: 60, genre: 'action_drama' },
  { show: 'The Carol Burnett Show', prefix: 'CBS', durationMinutes: 60, genre: 'comedy_variety' },
  { show: 'Mystery Science Theater 3000', prefix: 'MST', durationMinutes: 120, genre: 'cult_movie' },
  { show: 'The Real McCoys', prefix: 'MCC', durationMinutes: 30, genre: 'western' },
  { show: '21 Jump Street', prefix: 'JMP', durationMinutes: 60, genre: 'action_drama' },
  { show: 'The Saint', prefix: 'SNT', durationMinutes: 60, genre: 'action_adventure' },
  { show: "Rowan & Martin's Laugh-In", prefix: 'RML', durationMinutes: 60, genre: 'comedy_variety' },
  { show: 'The Lucy Show', prefix: 'LUC', durationMinutes: 30, genre: 'comedy_variety' },
  { show: 'The Tim Conway Comedy Hour', prefix: 'TCC', durationMinutes: 60, genre: 'comedy_variety' },
]

const LITERAL_PROGRAMS = [
  { show: 'Paid Programming', genre: 'paid', contentType: 'Paid programming' as const },
  { show: 'Perry Stone', genre: 'ministry', contentType: 'Paid programming' as const },
  { show: 'Sacred Name', genre: 'ministry', contentType: 'Paid programming' as const },
  { show: 'Les Feldick Ministries', genre: 'ministry', contentType: 'Paid programming' as const },
  { show: 'The Healthy Christian with Rich Stocks', genre: 'ministry', contentType: 'Paid programming' as const },
  { show: 'Michael Youssef', genre: 'ministry', contentType: 'Paid programming' as const },
  { show: 'Micheal Youssef', genre: 'ministry', contentType: 'Paid programming' as const },
  { show: 'The Awakening Hour', genre: 'ministry', contentType: 'Paid programming' as const },
  { show: 'Time for Hope', genre: 'ministry', contentType: 'Paid programming' as const },
  { show: 'Rejoyce in Jesus', genre: 'ministry', contentType: 'Paid programming' as const },
  { show: 'Post Card Travel TV', genre: 'travel_lifestyle', contentType: 'Series / show' as const },
  { show: 'The Jet Set', genre: 'travel_lifestyle', contentType: 'Series / show' as const },
]

const MOVIE_PROGRAMS = [
  { show: '12 Days Of Christmas Eve', title: '12 Days Of Christmas Eve (2004)', durationMinutes: 120, genre: 'holiday' },
  { show: 'Santa Fe Trail', title: 'Santa Fe Trail (1940)', durationMinutes: 120, genre: 'western' },
  { show: 'Bells of Rosarita', title: 'Bells of Rosarita (1945)', durationMinutes: 90, genre: 'western' },
]

const SAMPLE_EPISODES: Episode[] = [
  ...CATALOG_SHOWS.flatMap((meta) =>
    Array.from({ length: 30 }, (_, i) => ({
      id: `${meta.prefix.toLowerCase()}-${i + 1}`,
      show: meta.show,
      title: meta.show === '21 Jump Street' ? `21 Jump Street: Pt ${i + 1}` : `Episode ${i + 1}`,
      code: `${meta.prefix}${String(i + 1).padStart(3, '0')}`,
      durationMinutes: meta.durationMinutes,
      genre: meta.genre,
      contentType: 'Series / show' as const,
    })),
  ),
  ...LITERAL_PROGRAMS.map((meta) => ({
    id: `literal-${meta.show.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
    show: meta.show,
    title: meta.show,
    code: meta.contentType === 'Paid programming' ? 'PAID' : 'LIT',
    durationMinutes: 30,
    genre: meta.genre,
    contentType: meta.contentType,
  })),
  ...MOVIE_PROGRAMS.map((meta) => ({
    id: `movie-${meta.show.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
    show: meta.show,
    title: meta.title,
    code: 'MOVIE',
    durationMinutes: meta.durationMinutes,
    genre: meta.genre,
    contentType: 'Movie / special' as const,
  })),
]

function contentTypeLabel(value = ''): Episode['contentType'] {
  const normalized = value.toLowerCase().replace(/\s+/g, '_')
  if (['movie', 'movies', 'special', 'specials', 'film', 'feature'].includes(normalized)) return 'Movie / special'
  if (['paid', 'paid_programming', 'infomercial', 'ministry'].includes(normalized)) return 'Paid programming'
  return 'Series / show'
}

function episodeFromCatalogRow(row: CanonicalContentRow, index: number): Episode | null {
  if (row.availability_status && !['available', 'metadata_only'].includes(row.availability_status)) return null
  const show = (row.display_name || '').trim()
  if (!show) return null
  const duration = Number(row.runtime_minutes || row.binge_row_minutes || 30)
  const code = (row.episode_code || row.episode_number || '').trim()
  const title = (row.episode_title || show).trim()
  return {
    id: row.episode_key || `${row.series_key || show}-${index}`,
    show,
    title,
    code: code || (row.content_type === 'paid_programming' ? 'PAID' : 'EP'),
    durationMinutes: Number.isFinite(duration) && duration > 0 ? duration : 30,
    genre: row.genre || row.semantic_group || 'unlabeled',
    contentType: contentTypeLabel(row.content_type),
  }
}

const dayIndexByName: Record<string, number> = {
  Sunday: 0,
  Monday: 1,
  Tuesday: 2,
  Wednesday: 3,
  Thursday: 4,
  Friday: 5,
  Saturday: 6,
}

function isoLocal(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:00`
}

function addMinutes(d: Date, minutes: number): Date {
  return new Date(d.getTime() + minutes * 60_000)
}

function minutesBetween(start: Date, end: Date): number {
  return Math.max(0, Math.round((end.getTime() - start.getTime()) / 60_000))
}

function startOfLocalDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}

function minutesOfDay(d: Date): number {
  return d.getHours() * 60 + d.getMinutes()
}

function sameLocalDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

function rangeOverlaps(block: ScheduledBlock, range: TimeRange): boolean {
  const blockStart = new Date(block.start)
  const blockEnd = new Date(block.end)
  return blockStart < range.end && blockEnd > range.start
}

function normalizeSelection(start: Date, end: Date): TimeRange[] {
  if (end <= start) return []
  const endMarker = addMinutes(end, -1)
  if (sameLocalDay(start, endMarker)) return [{ start, end }]

  const startMinute = minutesOfDay(start)
  const endMinute = minutesOfDay(end) || 24 * 60
  if (endMinute <= startMinute) return [{ start, end }]

  const ranges: TimeRange[] = []
  let day = startOfLocalDay(start)
  const lastDay = startOfLocalDay(endMarker)
  while (day <= lastDay) {
    ranges.push({
      start: addMinutes(day, startMinute),
      end: addMinutes(day, endMinute),
    })
    day = addMinutes(day, 24 * 60)
  }
  return ranges
}

function colorForShow(show: string): string {
  let total = 0
  for (const ch of show) total += ch.charCodeAt(0)
  return SHOW_COLORS[total % SHOW_COLORS.length]
}

function eventFromBlock(block: ScheduledBlock): EventInput {
  return {
    id: block.id,
    title: `${block.show} — ${block.title}`,
    start: block.start,
    end: block.end,
    backgroundColor: colorForShow(block.show),
    borderColor: colorForShow(block.show),
    extendedProps: block,
  }
}

function renderEventContent(arg: EventContentArg) {
  const block = arg.event.extendedProps as Partial<ScheduledBlock>
  if (!block.show) return null
  const minutes = minutesBetween(arg.event.start || new Date(), arg.event.end || new Date())
  const title = block.title || arg.event.title || ''
  const [code = '', ...titleParts] = title.split(' ')
  const details = [
    block.show ? `Show: ${block.show}` : '',
    block.episodeCode ? `Episode: ${block.episodeCode}${block.episodeTitle ? ` - ${block.episodeTitle}` : ''}` : block.episodeTitle ? `Title: ${block.episodeTitle}` : '',
    block.genre ? `Genre: ${block.genre}` : '',
    block.contentType ? `Type: ${block.contentType}` : '',
    block.runtimeMinutes ? `Runtime: ${block.runtimeMinutes} minutes` : '',
    `Scheduled slot: ${minutes} minutes`,
  ]
    .filter(Boolean)
    .join('\n')
  return (
    <div className={`event-card ${minutes <= 30 ? 'compact' : ''}`} title={details}>
      <div className="event-time">{arg.timeText}</div>
      <div className="event-show">{block.show || arg.event.title}</div>
      <div className="event-code">{code}</div>
      <div className="event-title">{titleParts.join(' ')}</div>
    </div>
  )
}

function unique<T>(items: T[]): T[] {
  return Array.from(new Set(items))
}

function movieRuntimeCapacity(slotMinutes: number): number {
  return Math.floor(slotMinutes * 0.75)
}

function isMovieEpisode(ep: Episode): boolean {
  return ep.contentType === 'Movie / special' || ep.genre.toLowerCase() === 'movie' || ep.code.toUpperCase() === 'MOVIE'
}

function episodeFitsSlot(ep: Episode, slotMinutes: number | null): boolean {
  if (!slotMinutes) return true
  if (isMovieEpisode(ep)) return ep.durationMinutes <= movieRuntimeCapacity(slotMinutes)
  return ep.durationMinutes <= slotMinutes
}

export default function SchedulerApp({
  stationId,
  onBack,
  onBaseSaved,
}: {
  stationId?: string
  onBack?: () => void
  onBaseSaved?: (label: string) => void
}) {
  const [blocks, setBlocks] = useState<ScheduledBlock[]>([])
  const [selectedRanges, setSelectedRanges] = useState<TimeRange[]>([])
  const [liveSelectionRanges, setLiveSelectionRanges] = useState<TimeRange[]>([])
  const [selectedBlockIds, setSelectedBlockIds] = useState<string[]>([])
  const [showQuery, setShowQuery] = useState('')
  const [startingEpisodeId, setStartingEpisodeId] = useState('')
  const [contentMode, setContentMode] = useState<'series' | 'movies'>('series')
  const [startDate, setStartDate] = useState('2026-05-18')
  const [firstDayOfWeek, setFirstDayOfWeek] = useState('Monday')
  const [catalogEpisodes, setCatalogEpisodes] = useState<Episode[]>([])
  const [, setCatalogStatus] = useState('Loading normalized content...')
  const [contentMenuOpen, setContentMenuOpen] = useState(false)
  const [generateStatus, setGenerateStatus] = useState('Ready to analyze schedule draft.')
  const [generateNotice, setGenerateNotice] = useState('')
  const [generateNoticeKind, setGenerateNoticeKind] = useState<'info' | 'success' | 'error'>('info')
  const [suggestedRules, setSuggestedRules] = useState<SuggestedRule[]>([])
  const [missingSlotCount, setMissingSlotCount] = useState<number | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const contentInputRef = useRef<HTMLInputElement | null>(null)

  const availableEpisodes = catalogEpisodes.length ? catalogEpisodes : SAMPLE_EPISODES
  const selectedRangeDurations = selectedRanges.map((range) => minutesBetween(range.start, range.end))
  const selectedSlotMinutes = selectedRangeDurations.length ? Math.min(...selectedRangeDurations) : null
  const selectableEpisodes = useMemo(
    () =>
      availableEpisodes.filter((ep) => {
        const isMovie = isMovieEpisode(ep)
        if (contentMode === 'movies' && !isMovie) return false
        if (contentMode === 'series' && isMovie) return false
        return episodeFitsSlot(ep, selectedSlotMinutes)
      }),
    [availableEpisodes, contentMode, selectedSlotMinutes],
  )
  const shows = useMemo(() => unique(selectableEpisodes.map((ep) => ep.show)).sort(), [selectableEpisodes])
  const matchingShow = shows.find((show) => show.toLowerCase() === showQuery.trim().toLowerCase()) || ''
  const filteredShows = useMemo(() => {
    const q = showQuery.trim().toLowerCase()
    if (!q || matchingShow) return shows
    return shows.filter((show) => show.toLowerCase().includes(q))
  }, [matchingShow, showQuery, shows])
  const episodesForShow = useMemo(
    () => selectableEpisodes.filter((ep) => ep.show === matchingShow),
    [selectableEpisodes, matchingShow],
  )

  const selectedMinutes = selectedRangeDurations.reduce((total, minutes) => total + minutes, 0)
  const selectedSlots = Math.floor(selectedMinutes / 30)
  const selectedRange = selectedRanges[0] || null
  const selectedLastRange = selectedRanges[selectedRanges.length - 1] || null
  const previewRanges = liveSelectionRanges.length ? liveSelectionRanges : selectedRanges
  const selectedSlotEvents = previewRanges.map((range, index): EventInput => ({
    id: `selected-slot-${index}`,
    start: isoLocal(range.start),
    end: isoLocal(range.end),
    display: 'background',
    classNames: ['selected-time-slot-event'],
  }))
  const events = [...blocks.map(eventFromBlock), ...selectedSlotEvents]
  const selectedBlockIdSet = useMemo(() => new Set(selectedBlockIds), [selectedBlockIds])
  const calendarStart = useMemo(() => {
    const base = new Date(`${startDate}T00:00:00`)
    const targetDay = dayIndexByName[firstDayOfWeek] ?? 1
    const diff = (base.getDay() - targetDay + 7) % 7
    return addMinutes(base, -diff * 24 * 60)
  }, [firstDayOfWeek, startDate])
  const firstDayIndex = dayIndexByName[firstDayOfWeek] ?? 1

  const totals = useMemo(() => {
    const totalMinutes = 7 * 24 * 60
    const filledMinutes = blocks.reduce(
      (acc, block) => acc + minutesBetween(new Date(block.start), new Date(block.end)),
      0,
    )
    const byType = new Map<string, number>()
    const byGenre = new Map<string, number>()
    for (const block of blocks) {
      const mins = minutesBetween(new Date(block.start), new Date(block.end))
      byType.set(block.contentType, (byType.get(block.contentType) || 0) + mins)
      byGenre.set(block.genre || 'unlabeled', (byGenre.get(block.genre || 'unlabeled') || 0) + mins)
    }
    return { totalMinutes, filledMinutes, byType, byGenre }
  }, [blocks])

  useEffect(() => {
    let cancelled = false
    fetchCatalog<{ rows?: CanonicalContentRow[] }>()
      .then((payload: { rows?: CanonicalContentRow[] }) => {
        if (cancelled) return
        const rows = Array.isArray(payload.rows) ? payload.rows : []
        const episodes = rows
          .map((row, index) => episodeFromCatalogRow(row, index))
          .filter((ep): ep is Episode => Boolean(ep))
        setCatalogEpisodes(episodes)
        setCatalogStatus(episodes.length ? `${episodes.length.toLocaleString()} normalized rows loaded` : 'Using fallback demo content')
      })
      .catch(() => {
        if (!cancelled) setCatalogStatus('Using fallback demo content')
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const active = document.activeElement
      const tag = active?.tagName.toLowerCase()
      if (tag === 'input' || tag === 'select' || tag === 'textarea') return
      if (event.key === 'Delete' || event.key === 'Backspace') {
        event.preventDefault()
        deleteSelected()
        return
      }
      if (selectedRanges.length && event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
        event.preventDefault()
        setShowQuery(event.key)
        setStartingEpisodeId('')
        setContentMenuOpen(true)
        requestAnimationFrame(() => contentInputRef.current?.focus())
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  })

  function fillSelectedRange() {
    if (!selectedRanges.length || !matchingShow || !startingEpisodeId) return
    const episodePool = episodesForShow
    const startIndex = episodePool.findIndex((ep) => ep.id === startingEpisodeId)
    if (startIndex < 0) return

    const nextBlocks: ScheduledBlock[] = []
    let epIndex = startIndex

    for (const range of selectedRanges) {
      let cursor = new Date(range.start)
      while (cursor < range.end && epIndex < episodePool.length) {
        const ep = episodePool[epIndex]
        const remainingMinutes = minutesBetween(cursor, range.end)
        if (!episodeFitsSlot(ep, remainingMinutes)) break
        const isMovie = isMovieEpisode(ep)
        const end = isMovie ? new Date(range.end) : addMinutes(cursor, ep.durationMinutes)
        if (end > range.end) break
        nextBlocks.push({
          id: `${ep.id}-${cursor.getTime()}`,
          episodeId: ep.id,
          title: `${ep.code} ${ep.title}`,
          start: isoLocal(cursor),
          end: isoLocal(end),
          show: ep.show,
          genre: ep.genre,
          contentType: ep.contentType,
          runtimeMinutes: ep.durationMinutes,
          episodeCode: ep.code,
          episodeTitle: ep.title,
        })
        cursor = end
        epIndex += 1
        if (isMovie) break
      }
    }

    setBlocks((prev) => [
      ...prev.filter((block) => {
        return !selectedRanges.some((range) => rangeOverlaps(block, range))
      }),
      ...nextBlocks,
    ])
    setSelectedRanges([])
    setSelectedBlockIds([])
    setShowQuery('')
    setStartingEpisodeId('')
    setContentMenuOpen(false)
  }

  function deleteSelected() {
    if (selectedBlockIds.length) {
      const ids = new Set(selectedBlockIds)
      setBlocks((prev) => prev.filter((block) => !ids.has(block.id)))
      setSelectedBlockIds([])
      return
    }
    if (selectedRanges.length) {
      setBlocks((prev) => prev.filter((block) => !selectedRanges.some((range) => rangeOverlaps(block, range))))
      setSelectedRanges([])
    }
  }

  function handleSelect(arg: DateSelectArg) {
    setSelectedRanges(normalizeSelection(arg.start, arg.end))
    setLiveSelectionRanges([])
    arg.view.calendar.unselect()
    setSelectedBlockIds([])
    setShowQuery('')
    setStartingEpisodeId('')
    setContentMenuOpen(false)
  }

  function changeContentMode(mode: 'series' | 'movies') {
    setContentMode(mode)
    setShowQuery('')
    setStartingEpisodeId('')
    setContentMenuOpen(false)
  }

  function handleSelectAllow(arg: { start: Date; end: Date }) {
    setLiveSelectionRanges(normalizeSelection(arg.start, arg.end))
    return true
  }

  function handleEventClick(arg: EventClickArg) {
    setSelectedBlockIds((prev) =>
      prev.includes(arg.event.id) ? prev.filter((id) => id !== arg.event.id) : [...prev, arg.event.id],
    )
    setSelectedRanges([])
  }

  function eventClassNames(arg: { event: { id: string } }) {
    return selectedBlockIdSet.has(arg.event.id) ? ['selected-schedule-event'] : []
  }

  async function generateScheduleDraft() {
    if (!blocks.length) {
      setGenerateStatus('Add at least one block before generating.')
      setGenerateNotice('Add at least one scheduled block before generating.')
      setGenerateNoticeKind('error')
      setSuggestedRules([])
      setMissingSlotCount(null)
      return
    }
    setIsGenerating(true)
    setGenerateStatus('Sending draft to local Python API...')
    setGenerateNotice('Analyzing schedule draft...')
    setGenerateNoticeKind('info')
    try {
      const payloadBlocks = blocks.map((block) => ({
        ...block,
        content_type: block.contentType,
        episode_id: block.episodeId,
      }))
      const [rulesPayload, gridPayload] = await Promise.all([
        fetchJson<{ rule_count: number; rules: SuggestedRule[] }>('/api/schedule/analyze-rules', {
          method: 'POST',
          body: JSON.stringify({ blocks: payloadBlocks }),
        }),
        fetchJson<{ missing_slot_count: number }>('/api/schedule/blocks-to-grid', {
          method: 'POST',
          body: JSON.stringify({
            week_monday: calendarStart.toISOString().slice(0, 10),
            blocks: payloadBlocks,
            require_complete: false,
          }),
        }),
      ])
      setSuggestedRules(rulesPayload.rules || [])
      setMissingSlotCount(gridPayload.missing_slot_count)
      const missingText = `${gridPayload.missing_slot_count.toLocaleString()} empty half-hour slot${
        gridPayload.missing_slot_count === 1 ? '' : 's'
      }`
      const ruleText = `${rulesPayload.rule_count} rule suggestion${rulesPayload.rule_count === 1 ? '' : 's'}`
      setGenerateStatus(
        `Draft analyzed: ${rulesPayload.rule_count} rule suggestion${rulesPayload.rule_count === 1 ? '' : 's'} found.`,
      )
      if (gridPayload.missing_slot_count === 0) {
        const savePayload = await fetchJson<{ label: string; path: string }>('/api/base-schedules/save', {
          method: 'POST',
          body: JSON.stringify({
            station_id: stationId || '',
            week_monday: calendarStart.toISOString().slice(0, 10),
            blocks: payloadBlocks,
            suggested_rules: rulesPayload.rules || [],
          }),
        })
        onBaseSaved?.(savePayload.label)
        setGenerateNotice(`Schedule analyzed and saved as ${savePayload.label}. ${ruleText} found.`)
        setGenerateNoticeKind('success')
      } else {
        setGenerateNotice(`Schedule analyzed but not saved yet. ${missingText}. ${ruleText} found.`)
        setGenerateNoticeKind('info')
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Generate failed.'
      setGenerateStatus(error instanceof Error ? `Generate failed: ${error.message}` : 'Generate failed.')
      setGenerateNotice(`Generate failed: ${message}`)
      setGenerateNoticeKind('error')
      setSuggestedRules([])
      setMissingSlotCount(null)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <main className="scheduler-shell">
      <header className="topbar">
        <div>
          {stationId ? <p className="station-context">Station ID: {stationId}</p> : null}
          <p className="subhead">Drag across the calendar to highlight time, type a show, then fill the time slots in episode order.</p>
        </div>
        <div className="topbar-actions">
          {onBack ? (
            <button className="ghost-action" type="button" onClick={onBack}>
              Back
            </button>
          ) : null}
          <button className="primary-action" type="button" disabled={isGenerating} onClick={generateScheduleDraft}>
            {isGenerating ? 'Analyzing...' : 'Generate Schedule'}
          </button>
        </div>
      </header>

      {generateNotice ? <div className={`generate-notice ${generateNoticeKind}`}>{generateNotice}</div> : null}

      <section className="setup-card">
        <label>
          First day of week
          <select value={firstDayOfWeek} onChange={(event) => setFirstDayOfWeek(event.target.value)}>
            <option>Monday</option>
            <option>Tuesday</option>
            <option>Wednesday</option>
            <option>Thursday</option>
            <option>Friday</option>
            <option>Saturday</option>
            <option>Sunday</option>
          </select>
        </label>
        <label>
          Start date
          <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
        </label>
        <label>
          Schedule length
          <select defaultValue="1 week">
            <option>1 week</option>
            <option>2 weeks</option>
            <option>4 weeks</option>
          </select>
        </label>
      </section>

      <section className="workspace">
        <div className="calendar-card">
          <FullCalendar
            plugins={[timeGridPlugin, interactionPlugin]}
            initialView="timeGridWeek"
            initialDate={calendarStart}
            key={`${startDate}-${firstDayOfWeek}`}
            firstDay={firstDayIndex}
            headerToolbar={false}
            allDaySlot={false}
            slotDuration="00:30:00"
            slotLabelInterval="01:00"
            snapDuration="00:30:00"
            selectable
            selectMirror={false}
            unselectAuto={false}
            editable
            events={events}
            eventContent={renderEventContent}
            eventClassNames={eventClassNames}
            selectAllow={handleSelectAllow}
            select={handleSelect}
            eventClick={handleEventClick}
            height="auto"
            nowIndicator={false}
            dayHeaderContent={(arg) => (
              <div className="day-header">
                <strong>{arg.date.toLocaleDateString([], { weekday: 'short' })}</strong>
                <span>
                  {arg.date.toLocaleDateString([], {
                    month: 'numeric',
                    day: 'numeric',
                  })}
                </span>
              </div>
            )}
            slotMinTime="00:00:00"
            slotMaxTime="24:00:00"
          />
        </div>

        <aside className="side-panel">
          <div className="panel-section">
            <p className="panel-title">Selected time slot</p>
            {selectedRange ? (
              <div className="selected-range">
                <strong>{selectedSlots} half-hours</strong>
                <span>
                  {selectedRange.start.toLocaleString([], {
                    weekday: 'short',
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                  {' → '}
                  {(selectedLastRange || selectedRange).end.toLocaleString([], {
                    weekday: 'short',
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </span>
                {selectedRanges.length > 1 ? <span>{selectedRanges.length} matching day/time selections</span> : null}
              </div>
            ) : selectedBlockIds.length ? (
              <div className="selected-range">
                <strong>{selectedBlockIds.length} program block{selectedBlockIds.length === 1 ? '' : 's'} selected</strong>
                <span>Press Delete or click Delete Selected to remove.</span>
              </div>
            ) : (
              <p className="muted">Drag across time cells to select a time slot.</p>
            )}
          </div>

          <div className="panel-section">
            <div className="content-mode-toggle" aria-label="Content type">
              <button className={contentMode === 'series' ? 'active' : ''} type="button" onClick={() => changeContentMode('series')}>
                Series
              </button>
              <button className={contentMode === 'movies' ? 'active' : ''} type="button" onClick={() => changeContentMode('movies')}>
                Movies
              </button>
            </div>
            <label>
              Select content
              <div className="content-combo">
                <input
                  ref={contentInputRef}
                  value={showQuery}
                  onChange={(event) => {
                    const nextValue = event.target.value
                    const exactMatch = shows.some((show) => show.toLowerCase() === nextValue.trim().toLowerCase())
                    setShowQuery(nextValue)
                    setStartingEpisodeId('')
                    setContentMenuOpen(!exactMatch)
                  }}
                  onFocus={() => {
                    if (!matchingShow) setContentMenuOpen(true)
                  }}
                  placeholder={`Search or choose from ${shows.length.toLocaleString()} items`}
                />
                <button
                  className="content-combo-arrow"
                  type="button"
                  aria-label="Show all content"
                  onClick={() => setContentMenuOpen((open) => !open)}
                >
                  ▾
                </button>
                {contentMenuOpen ? (
                  <div className="content-menu">
                    {filteredShows.map((show) => (
                      <button
                        className={`content-menu-item${show === matchingShow ? ' selected' : ''}`}
                        key={show}
                        type="button"
                        onMouseDown={(event) => {
                          event.preventDefault()
                          setShowQuery(show)
                          setStartingEpisodeId('')
                          setContentMenuOpen(false)
                        }}
                      >
                        {show}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
              <span className="picker-note">
                Showing {filteredShows.length.toLocaleString()} of {shows.length.toLocaleString()} content items
                {selectedSlotMinutes ? ` that fit ${selectedSlotMinutes} minutes` : ''}
              </span>
            </label>

            <label>
              Starting episode
              <select
                value={startingEpisodeId}
                onChange={(event) => setStartingEpisodeId(event.target.value)}
                disabled={!matchingShow}
              >
                <option value="">Select episode</option>
                {episodesForShow.map((ep) => (
                  <option key={ep.id} value={ep.id}>
                    {ep.code} — {ep.title}
                  </option>
                ))}
              </select>
            </label>

            <button
              className="primary-action wide"
              type="button"
              disabled={!selectedRanges.length || !matchingShow || !startingEpisodeId}
              onClick={fillSelectedRange}
            >
              Commit
            </button>
            <button className="ghost-action wide" type="button" disabled={!selectedRanges.length && !selectedBlockIds.length} onClick={deleteSelected}>
              Delete Selected
            </button>
          </div>

          <div className="panel-section">
            <p className="panel-title">Report</p>
            <div className="metric-row">
              <span>Filled</span>
              <strong>{Math.round((totals.filledMinutes / totals.totalMinutes) * 100)}%</strong>
            </div>
            {[...totals.byType.entries()].map(([type, minutes]) => (
              <div className="metric-row" key={type}>
                <span>{type}</span>
                <strong>{(minutes / 60).toFixed(1)}h</strong>
              </div>
            ))}
            {[...totals.byGenre.entries()].map(([genre, minutes]) => (
              <div className="metric-row quiet" key={genre}>
                <span>{genre}</span>
                <strong>{(minutes / 60).toFixed(1)}h</strong>
              </div>
            ))}
          </div>

          <div className="panel-section">
            <p className="panel-title">Backend analysis</p>
            <p className="muted">{generateStatus}</p>
            {missingSlotCount !== null ? (
              <div className="metric-row quiet">
                <span>Empty half-hours</span>
                <strong>{missingSlotCount.toLocaleString()}</strong>
              </div>
            ) : null}
            {suggestedRules.slice(0, 5).map((rule) => (
              <div className="rule-card" key={`${rule.rule_type}-${rule.show}-${rule.summary}`}>
                <strong>{rule.show}</strong>
                <span>{rule.summary}</span>
                <small>
                  {rule.rule_type} · {Math.round(rule.confidence * 100)}% confidence
                </small>
              </div>
            ))}
          </div>
        </aside>
      </section>
    </main>
  )
}
