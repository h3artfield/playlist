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
  runtimeMinutes: number
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

type GridPayload = {
  week_monday: string
  missing_slot_count: number
  missing_slots?: Array<{ slot: number; day_index: number }>
  grid: Array<Array<string | null>>
}

type ScheduleNote = {
  kind: 'warning' | 'info'
  show: string
  message: string
}

type GenerateResult = {
  generatedAt: string
  stationId: string
  weekCount: number
  weekStarts: string[]
  payloadBlocks: Array<ScheduledBlock & { content_type: string; episode_id: string }>
  grids: GridPayload[]
  rules: SuggestedRule[]
  notes: ScheduleNote[]
  missingSlotTotal: number
}

type CatalogOrder = {
  order: Map<string, number>
  count: number
}

type GridPreviewCell = {
  text: string
  rowSpan: number
  hidden: boolean
  filled: boolean
}

type ScheduleDraft = {
  version: 1
  stationId: string
  blocks: ScheduledBlock[]
  startDate: string
  firstDayOfWeek: string
  startTimeHour: number
  scheduleLengthWeeks: number
  savedAt: string
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
  '#ec4899',
  '#14b8a6',
  '#a855f7',
  '#eab308',
  '#06b6d4',
  '#22c55e',
  '#fb7185',
  '#8b5cf6',
]

const FIXED_SHOW_COLORS: Record<string, string> = {
  'paid programming': '#64748b',
}

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
  { show: 'Post Card Travel TV', genre: 'travel_lifestyle', contentType: 'Paid programming' as const },
  { show: 'The Jet Set', genre: 'travel_lifestyle', contentType: 'Series / show' as const },
]

const PAID_PROGRAMMING_SHOWS = new Set([
  'paid programming',
  'perry stone',
  'sacred name',
  'les feldick ministries',
  'the healthy christian with rich stocks',
  'michael youssef',
  'micheal youssef',
  'the awakening hour',
  'time for hope',
  'rejoyce in jesus',
  'post card travel tv',
  'postcard tv',
  'postcard travel tv',
])

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
      runtimeMinutes: meta.durationMinutes,
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
    runtimeMinutes: 30,
    genre: meta.genre,
    contentType: meta.contentType,
  })),
  ...MOVIE_PROGRAMS.map((meta) => ({
    id: `movie-${meta.show.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
    show: meta.show,
    title: meta.title,
    code: 'MOVIE',
    durationMinutes: meta.durationMinutes,
    runtimeMinutes: meta.durationMinutes,
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
  const scheduledDuration = Number(row.binge_row_minutes || row.runtime_minutes || 30)
  const runtime = Number(row.runtime_minutes || scheduledDuration)
  const code = (row.episode_code || row.episode_number || '').trim()
  const title = (row.episode_title || show).trim()
  return {
    id: row.episode_key || `${row.series_key || show}-${index}`,
    show,
    title,
    code: code || (row.content_type === 'paid_programming' ? 'PAID' : 'EP'),
    durationMinutes: Number.isFinite(scheduledDuration) && scheduledDuration > 0 ? scheduledDuration : 30,
    runtimeMinutes: Number.isFinite(runtime) && runtime > 0 ? runtime : 30,
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

const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

const START_TIME_OPTIONS = Array.from({ length: 24 }, (_, hour) => {
  const displayHour = hour % 12 || 12
  const suffix = hour < 12 ? 'AM' : 'PM'
  return {
    value: String(hour),
    label: `${displayHour} ${suffix}`,
  }
})

function draftStorageKey(stationId?: string): string {
  return `schedule-builder-draft:${(stationId || 'default').trim() || 'default'}`
}

function isScheduledBlock(value: unknown): value is ScheduledBlock {
  const block = value as Partial<ScheduledBlock>
  return Boolean(
    block &&
      typeof block.id === 'string' &&
      typeof block.start === 'string' &&
      typeof block.end === 'string' &&
      typeof block.show === 'string' &&
      typeof block.contentType === 'string',
  )
}

function loadScheduleDraft(stationId?: string): ScheduleDraft | null {
  try {
    const raw = window.localStorage.getItem(draftStorageKey(stationId))
    if (!raw) return null
    const draft = JSON.parse(raw) as Partial<ScheduleDraft>
    if (!Array.isArray(draft.blocks)) return null
    const startTimeHour = Number(draft.startTimeHour ?? 0)
    const weekCount = Number(draft.scheduleLengthWeeks ?? 1)
    return {
      version: 1,
      stationId: String(draft.stationId || stationId || ''),
      blocks: draft.blocks.filter(isScheduledBlock),
      startDate: typeof draft.startDate === 'string' ? draft.startDate : '2026-05-18',
      firstDayOfWeek: DAY_NAMES.includes(String(draft.firstDayOfWeek)) ? String(draft.firstDayOfWeek) : 'Monday',
      startTimeHour: Number.isInteger(startTimeHour) && startTimeHour >= 0 && startTimeHour <= 23 ? startTimeHour : 0,
      scheduleLengthWeeks: [1, 2, 4].includes(weekCount) ? weekCount : 1,
      savedAt: typeof draft.savedAt === 'string' ? draft.savedAt : '',
    }
  } catch {
    return null
  }
}

function saveScheduleDraft(stationId: string | undefined, draft: Omit<ScheduleDraft, 'version' | 'stationId' | 'savedAt'>): void {
  try {
    const payload: ScheduleDraft = {
      version: 1,
      stationId: stationId || '',
      ...draft,
      savedAt: new Date().toISOString(),
    }
    window.localStorage.setItem(draftStorageKey(stationId), JSON.stringify(payload))
  } catch {
    // Local autosave should never block schedule building.
  }
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

function formatRuntimeMinutes(minutes: number): string {
  if (!Number.isFinite(minutes) || minutes <= 0) return ''
  const totalSeconds = Math.round(minutes * 60)
  const mins = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return seconds ? `${mins}:${String(seconds).padStart(2, '0')}` : `${mins} minutes`
}

function formatClock(value: Date): string {
  return value.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

function formatShortDate(value: Date): string {
  return value.toLocaleDateString([], { weekday: 'short', month: 'numeric', day: 'numeric' })
}

function slotLabel(slot: number): string {
  const minutes = slot * 30
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  const date = new Date(2026, 0, 1, hours, mins)
  return formatClock(date)
}

function localDateKey(value: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`
}

function parseLocalDate(value: string): Date {
  return new Date(`${value}T00:00:00`)
}

function blockStartSlot(block: Pick<ScheduledBlock, 'start'>): number {
  const start = new Date(block.start)
  return Math.max(0, Math.min(47, Math.floor(minutesOfDay(start) / 30)))
}

function blockEndSlot(block: Pick<ScheduledBlock, 'start' | 'end'>): number {
  const start = new Date(block.start)
  const end = new Date(block.end)
  if (localDateKey(end) > localDateKey(start)) return 48
  return Math.max(0, Math.min(48, Math.ceil(minutesOfDay(end) / 30)))
}

function episodeLabelFromBlock(block: ScheduledBlock): string {
  return [block.episodeCode, block.episodeTitle].filter(Boolean).join(' - ')
}

function gridPreviewShowName(value: string | null): string {
  const text = String(value || '').trim()
  if (!text) return ''
  const first = text.split('\n')[0].trim()
  if (first.includes(' - (')) return first.split(' - (', 1)[0].trim()
  return first
}

function buildGridPreviewCells(resultGrid: GridPayload, blocks: GenerateResult['payloadBlocks']): GridPreviewCell[][] {
  const weekStart = parseLocalDate(resultGrid.week_monday)
  const cells = resultGrid.grid.map((row) =>
    row.map((cell) => ({
      text: gridPreviewShowName(cell),
      rowSpan: 1,
      hidden: false,
      filled: Boolean(cell),
    })),
  )

  for (const block of blocks) {
    const start = new Date(block.start)
    const dayIndex = Math.floor((startOfLocalDay(start).getTime() - weekStart.getTime()) / (24 * 60 * 60 * 1000))
    if (dayIndex < 0 || dayIndex > 6) continue
    const startSlot = blockStartSlot(block)
    const endSlot = blockEndSlot(block)
    const rowSpan = Math.max(1, endSlot - startSlot)
    if (startSlot < 0 || startSlot > 47 || !cells[startSlot]?.[dayIndex]) continue
    cells[startSlot][dayIndex] = {
      text: gridPreviewShowName(block.show),
      rowSpan,
      hidden: false,
      filled: true,
    }
    for (let slot = startSlot + 1; slot < Math.min(endSlot, 48); slot += 1) {
      cells[slot][dayIndex] = {
        text: '',
        rowSpan: 1,
        hidden: true,
        filled: false,
      }
    }
  }

  return cells
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

function sameTimeRanges(a: TimeRange[], b: TimeRange[]): boolean {
  return (
    a.length === b.length &&
    a.every((range, index) => range.start.getTime() === b[index].start.getTime() && range.end.getTime() === b[index].end.getTime())
  )
}

function durationTime(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:00`
}

function colorForShow(show: string): string {
  const normalized = show.trim().toLowerCase()
  if (FIXED_SHOW_COLORS[normalized]) return FIXED_SHOW_COLORS[normalized]
  let total = 2166136261
  for (const ch of normalized) {
    total ^= ch.charCodeAt(0)
    total = Math.imul(total, 16777619)
  }
  return SHOW_COLORS[Math.abs(total) % SHOW_COLORS.length]
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
  const [, ...titleParts] = title.split(' ')
  const episodeLabel = [block.episodeCode, block.episodeTitle || titleParts.join(' ')].filter(Boolean).join(' - ')
  const showName = block.show || arg.event.title
  const usefulEpisodeLabel =
    episodeLabel && episodeLabel.toLowerCase() !== showName.toLowerCase() && !episodeLabel.toLowerCase().endsWith(` - ${showName.toLowerCase()}`)
  const runtimeText = block.runtimeMinutes ? formatRuntimeMinutes(block.runtimeMinutes) : ''
  const availsText = block.runtimeMinutes ? formatRuntimeMinutes(Math.max(0, minutes - block.runtimeMinutes)) : ''
  const details = [
    block.show ? `Show: ${block.show}` : '',
    block.episodeCode ? `Episode: ${block.episodeCode}${block.episodeTitle ? ` - ${block.episodeTitle}` : ''}` : block.episodeTitle ? `Title: ${block.episodeTitle}` : '',
    block.genre ? `Genre: ${block.genre}` : '',
    block.contentType ? `Type: ${block.contentType}` : '',
    `Scheduled slot: ${minutes} minutes`,
    runtimeText ? `Runtime: ${runtimeText}` : '',
    availsText ? `Avails: ${availsText}` : '',
  ]
    .filter(Boolean)
    .join('\n')
  return (
    <div className={`event-card ${minutes <= 30 ? 'compact' : ''}`} title={details}>
      <div className="event-time">{arg.timeText}</div>
      <div className="event-show">{showName}</div>
      {usefulEpisodeLabel ? <div className="event-title">{episodeLabel}</div> : null}
    </div>
  )
}

function unique<T>(items: T[]): T[] {
  return Array.from(new Set(items))
}

function payloadFromBlocks(blocks: ScheduledBlock[]): GenerateResult['payloadBlocks'] {
  return blocks.map((block) => ({
    ...block,
    content_type: block.contentType,
    episode_id: block.episodeId,
  }))
}

function analyzerCatalogRows(episodes: Episode[]): Array<Record<string, string>> {
  return episodes.map((ep) => ({
    display_name: ep.show,
    episode_key: ep.id,
    episode_code: ep.code,
    episode_title: ep.title,
  }))
}

function stationReportLabel(stationId: string): string {
  return stationId.trim() || 'Station'
}

async function downloadScheduleWorkbook(kind: 'binge' | 'grids', result: GenerateResult, weekMonday: Date): Promise<void> {
  const response = await fetch(`/api/schedule/download/${kind}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      station_id: result.stationId,
      week_monday: weekMonday.toISOString().slice(0, 10),
      week_count: result.weekCount,
      blocks: result.payloadBlocks,
    }),
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(detail || `Download failed: HTTP ${response.status}`)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const label = stationReportLabel(result.stationId)
  link.href = url
  link.download = kind === 'binge' ? `${label}.xlsx` : `${label} GRIDS.xlsx`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

async function downloadSchedulePackage(result: GenerateResult, weekMonday: Date, notes: ScheduleNote[]): Promise<void> {
  const response = await fetch('/api/schedule/download-package', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      station_id: result.stationId,
      week_monday: weekMonday.toISOString().slice(0, 10),
      week_count: result.weekCount,
      blocks: result.payloadBlocks,
      notes,
    }),
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(detail || `Download failed: HTTP ${response.status}`)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const label = stationReportLabel(result.stationId)
  link.href = url
  link.download = `${label} Reports.zip`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function csvEscape(value: string | number): string {
  const text = String(value)
  return `"${text.replace(/"/g, '""')}"`
}

function downloadScheduleNotes(notes: ScheduleNote[], stationId: string): void {
  const rows = [
    ['Station ID', 'Type', 'Show', 'Message'],
    ...notes.map((note) => [stationId, note.kind, note.show, note.message]),
  ]
  const csv = rows.map((row) => row.map(csvEscape).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'Warnings and Notes.csv'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function buildCatalogOrder(episodes: Episode[]): Map<string, CatalogOrder> {
  const byShow = new Map<string, CatalogOrder>()
  for (const ep of episodes) {
    if (!byShow.has(ep.show)) byShow.set(ep.show, { order: new Map(), count: 0 })
    const entry = byShow.get(ep.show)
    if (!entry) continue
    const position = entry.count
    entry.count += 1
    for (const token of [ep.id, ep.code, ep.title]) {
      const clean = String(token || '').trim().toLowerCase()
      if (clean && !entry.order.has(clean)) entry.order.set(clean, position)
    }
  }
  return byShow
}

function blockCatalogPosition(block: ScheduledBlock, order: Map<string, number>): number | null {
  for (const token of [block.episodeId, block.episodeCode, block.episodeTitle]) {
    const key = String(token || '').trim().toLowerCase()
    if (key && order.has(key)) return order.get(key) ?? null
  }
  return null
}

function twoPartNumber(block: ScheduledBlock): 1 | 2 | null {
  const text = `${block.episodeCode} ${block.episodeTitle} ${block.title}`.toLowerCase()
  if (/\b(?:part|pt\.?)\s*(?:1|one|i)\b/.test(text) || /\b(?:1|one|i)\s*(?:of|\/)\s*(?:2|two|ii)\b/.test(text)) return 1
  if (/\b(?:part|pt\.?)\s*(?:2|two|ii)\b/.test(text) || /\b(?:2|two|ii)\s*(?:of|\/)\s*(?:2|two|ii)\b/.test(text)) return 2
  return null
}

function twoPartBaseTitle(block: ScheduledBlock): string {
  const title = block.episodeTitle || block.title || block.show
  return title
    .replace(/\b(?:part|pt\.?)\s*(?:1|2|one|two|i|ii)\b/gi, '')
    .replace(/\b(?:1|2|one|two|i|ii)\s*(?:of|\/)\s*(?:2|two|ii)\b/gi, '')
    .replace(/[-:()[\]]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

function buildScheduleNotes(blocks: ScheduledBlock[], episodes: Episode[]): ScheduleNote[] {
  const catalogOrder = buildCatalogOrder(episodes)
  const blocksByShow = new Map<string, ScheduledBlock[]>()
  for (const block of blocks) {
    if (!blocksByShow.has(block.show)) blocksByShow.set(block.show, [])
    blocksByShow.get(block.show)?.push(block)
  }

  const notes: ScheduleNote[] = []
  for (const [show, showBlocks] of blocksByShow) {
    const orderedBlocks = [...showBlocks].sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime())
    if (orderedBlocks.every(isPaidProgrammingBlock)) continue
    const twoPartGroups = new Map<string, ScheduledBlock[]>()
    for (const block of orderedBlocks) {
      const slotMinutes = minutesBetween(new Date(block.start), new Date(block.end))
      if (
        block.contentType === 'Movie / special' &&
        block.runtimeMinutes <= slotMinutes &&
        block.runtimeMinutes > movieRuntimeCapacity(slotMinutes)
      ) {
        notes.push({
          kind: 'info',
          show,
          message: `${show} fits the ${slotMinutes}-minute slot by runtime, but not with the normal movie commercial allowance. Add a title-start timing note in the report.`,
        })
      }

      const partNumber = twoPartNumber(block)
      if (partNumber) {
        const key = twoPartBaseTitle(block) || `${show}-${block.episodeCode}`.toLowerCase()
        if (!twoPartGroups.has(key)) twoPartGroups.set(key, [])
        twoPartGroups.get(key)?.push(block)
      }
    }

    for (const groupBlocks of twoPartGroups.values()) {
      const partNumbers = new Set(groupBlocks.map((block) => twoPartNumber(block)))
      const labels = groupBlocks.map(episodeLabelFromBlock).filter(Boolean).join(', ')
      if (partNumbers.has(1) && partNumbers.has(2)) {
        notes.push({
          kind: 'info',
          show,
          message: `${show} has a two-part episode scheduled: ${labels}.`,
        })
      } else {
        notes.push({
          kind: 'warning',
          show,
          message: `${show} has part of a two-part episode scheduled (${labels}). Confirm the matching part is also placed.`,
        })
      }
    }

    if (orderedBlocks.every((block) => block.contentType === 'Movie / special')) continue

    const catalog = catalogOrder.get(show)
    if (!catalog) continue
    const positions = orderedBlocks
      .map((block) => ({ block, position: blockCatalogPosition(block, catalog.order) }))
      .filter((item): item is { block: ScheduledBlock; position: number } => item.position !== null)
    if (!positions.length) continue

    const lastPosition = Math.max(...positions.map((item) => item.position))
    const remaining = catalog.count - lastPosition - 1
    if (remaining >= 0 && remaining <= 10) {
      notes.push({
        kind: 'warning',
        show,
        message: `${show} is within ${remaining} episode${remaining === 1 ? '' : 's'} of the end of available content.`,
      })
    }

    for (const [prev, next] of positions.map((item) => item.position).entries()) {
      if (prev === 0) continue
      const prior = positions[prev - 1]
      const current = positions[prev]
      const gap = next - prior.position
      if (gap > 1) {
        notes.push({
          kind: 'info',
          show,
          message: `${show} skips ${gap - 1} catalog episode${gap - 1 === 1 ? '' : 's'} between ${episodeLabelFromBlock(prior.block)} and ${episodeLabelFromBlock(current.block)}.`,
        })
      }
    }
  }
  return notes
}

function movieRuntimeCapacity(slotMinutes: number): number {
  return Math.floor(slotMinutes * 0.75)
}

function isMovieEpisode(ep: Episode): boolean {
  return ep.contentType === 'Movie / special' || ep.genre.toLowerCase() === 'movie' || ep.code.toUpperCase() === 'MOVIE'
}

function isRepeatableLiteralEpisode(ep: Episode): boolean {
  return ep.contentType === 'Paid programming' || PAID_PROGRAMMING_SHOWS.has(ep.show.trim().toLowerCase()) || ep.code.toUpperCase() === 'PAID' || ep.code.toUpperCase() === 'LIT'
}

function isPaidProgrammingBlock(block: Pick<ScheduledBlock, 'show' | 'contentType'>): boolean {
  return block.contentType === 'Paid programming' || PAID_PROGRAMMING_SHOWS.has(block.show.trim().toLowerCase())
}

function movieNeedsTimingNote(ep: Episode, slotMinutes: number | null): boolean {
  return Boolean(slotMinutes && isMovieEpisode(ep) && ep.runtimeMinutes <= slotMinutes && ep.runtimeMinutes > movieRuntimeCapacity(slotMinutes))
}

function episodeFitsSlot(ep: Episode, slotMinutes: number | null): boolean {
  if (!slotMinutes) return true
  if (isMovieEpisode(ep)) return ep.durationMinutes <= movieRuntimeCapacity(slotMinutes) || ep.runtimeMinutes <= slotMinutes
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
  const initialDraftRef = useRef<ScheduleDraft | null | undefined>(undefined)
  if (initialDraftRef.current === undefined) initialDraftRef.current = loadScheduleDraft(stationId)
  const initialDraft = initialDraftRef.current

  const [blocks, setBlocks] = useState<ScheduledBlock[]>(() => initialDraft?.blocks || [])
  const [selectedRanges, setSelectedRanges] = useState<TimeRange[]>([])
  const [liveSelectionRanges, setLiveSelectionRanges] = useState<TimeRange[]>([])
  const [selectedBlockIds, setSelectedBlockIds] = useState<string[]>([])
  const [showQuery, setShowQuery] = useState('')
  const [startingEpisodeId, setStartingEpisodeId] = useState('')
  const [contentMode, setContentMode] = useState<'series' | 'movies'>('series')
  const [startDate, setStartDate] = useState(() => initialDraft?.startDate || '2026-05-18')
  const [firstDayOfWeek, setFirstDayOfWeek] = useState(() => initialDraft?.firstDayOfWeek || 'Monday')
  const [startTimeHour, setStartTimeHour] = useState(() => initialDraft?.startTimeHour ?? 0)
  const [scheduleLengthWeeks, setScheduleLengthWeeks] = useState(() => initialDraft?.scheduleLengthWeeks || 1)
  const [visibleWeekIndex, setVisibleWeekIndex] = useState(0)
  const [catalogEpisodes, setCatalogEpisodes] = useState<Episode[]>([])
  const [, setCatalogStatus] = useState('Loading normalized content...')
  const [contentMenuOpen, setContentMenuOpen] = useState(false)
  const [generateStatus, setGenerateStatus] = useState('Ready to analyze schedule draft.')
  const [generateNotice, setGenerateNotice] = useState('')
  const [generateNoticeKind, setGenerateNoticeKind] = useState<'info' | 'success' | 'error'>('info')
  const [suggestedRules, setSuggestedRules] = useState<SuggestedRule[]>([])
  const [missingSlotCount, setMissingSlotCount] = useState<number | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generateResult, setGenerateResult] = useState<GenerateResult | null>(null)
  const [viewMode, setViewMode] = useState<'builder' | 'results'>('builder')
  const [resultWeekIndex, setResultWeekIndex] = useState(0)
  const [isSavingBase, setIsSavingBase] = useState(false)
  const [downloadStatus, setDownloadStatus] = useState('')
  const contentInputRef = useRef<HTMLInputElement | null>(null)

  const availableEpisodes = catalogEpisodes.length ? catalogEpisodes : SAMPLE_EPISODES
  const selectedRangeDurations = useMemo(() => selectedRanges.map((range) => minutesBetween(range.start, range.end)), [selectedRanges])
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
  const inferredStartingEpisode = useMemo(() => {
    if (!matchingShow || !selectedRanges.length || !episodesForShow.length) return null
    const selectionStart = selectedRanges.reduce(
      (earliest, range) => (range.start < earliest ? range.start : earliest),
      selectedRanges[0].start,
    )
    const priorBlocks = blocks
      .filter((block) => block.show === matchingShow && new Date(block.start) < selectionStart)
      .sort((a, b) => new Date(b.start).getTime() - new Date(a.start).getTime())

    for (const block of priorBlocks) {
      const previousIndex = episodesForShow.findIndex((ep) => {
        return ep.id === block.episodeId || ep.code === block.episodeCode || ep.title === block.episodeTitle
      })
      if (previousIndex >= 0 && previousIndex + 1 < episodesForShow.length) {
        return episodesForShow[previousIndex + 1]
      }
    }
    return null
  }, [blocks, episodesForShow, matchingShow, selectedRanges])
  const previewRanges = liveSelectionRanges.length ? liveSelectionRanges : selectedRanges
  const baseCalendarStart = useMemo(() => {
    const base = new Date(`${startDate}T00:00:00`)
    const targetDay = dayIndexByName[firstDayOfWeek] ?? 1
    const diff = (base.getDay() - targetDay + 7) % 7
    return addMinutes(base, -diff * 24 * 60)
  }, [firstDayOfWeek, startDate])
  const calendarStart = useMemo(() => addMinutes(baseCalendarStart, visibleWeekIndex * 7 * 24 * 60), [baseCalendarStart, visibleWeekIndex])
  const dayStartMinutes = startTimeHour * 60
  const calendarEnd = useMemo(() => addMinutes(calendarStart, 7 * 24 * 60 + dayStartMinutes), [calendarStart, dayStartMinutes])
  const scheduleWeekStarts = useMemo(
    () => Array.from({ length: scheduleLengthWeeks }, (_, index) => addMinutes(baseCalendarStart, index * 7 * 24 * 60)),
    [baseCalendarStart, scheduleLengthWeeks],
  )
  const visibleBlocks = useMemo(
    () =>
      blocks.filter((block) => {
        const blockStart = new Date(block.start)
        const blockEnd = new Date(block.end)
        return blockStart < calendarEnd && blockEnd > calendarStart
      }),
    [blocks, calendarEnd, calendarStart],
  )
  const events = useMemo(() => {
    const selectedSlotEvents = previewRanges.map((range, index): EventInput => ({
      id: `selected-slot-${index}`,
      start: isoLocal(range.start),
      end: isoLocal(range.end),
      display: 'background',
      classNames: ['selected-time-slot-event'],
    }))
    return [...visibleBlocks.map(eventFromBlock), ...selectedSlotEvents]
  }, [previewRanges, visibleBlocks])
  const selectedBlockIdSet = useMemo(() => new Set(selectedBlockIds), [selectedBlockIds])
  const firstDayIndex = dayIndexByName[firstDayOfWeek] ?? 1
  const calendarSlotMinTime = durationTime(dayStartMinutes)
  const calendarSlotMaxTime = durationTime(dayStartMinutes + 24 * 60)
  const calendarScrollTime = calendarSlotMinTime

  const totals = useMemo(() => {
    const totalMinutes = scheduleLengthWeeks * 7 * 24 * 60
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
  }, [blocks, scheduleLengthWeeks])

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
    setVisibleWeekIndex((index) => Math.min(index, scheduleLengthWeeks - 1))
  }, [scheduleLengthWeeks])

  useEffect(() => {
    saveScheduleDraft(stationId, {
      blocks,
      startDate,
      firstDayOfWeek,
      startTimeHour,
      scheduleLengthWeeks,
    })
  }, [blocks, firstDayOfWeek, scheduleLengthWeeks, startDate, startTimeHour, stationId])

  useEffect(() => {
    setVisibleWeekIndex(0)
    setSelectedRanges([])
    setLiveSelectionRanges([])
    setSelectedBlockIds([])
  }, [baseCalendarStart])

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
    const startEpisodeId = startingEpisodeId || inferredStartingEpisode?.id || ''
    if (!selectedRanges.length || !matchingShow || !startEpisodeId) return
    const episodePool = episodesForShow
    const startIndex = episodePool.findIndex((ep) => ep.id === startEpisodeId)
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
        const isRepeatableLiteral = isRepeatableLiteralEpisode(ep)
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
          runtimeMinutes: ep.runtimeMinutes,
          episodeCode: ep.code,
          episodeTitle: ep.title,
        })
        cursor = end
        if (!isRepeatableLiteral) epIndex += 1
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

  function changeStartDate(nextDate: string) {
    setStartDate(nextDate)
    const parsed = new Date(`${nextDate}T00:00:00`)
    if (!Number.isNaN(parsed.getTime())) {
      setFirstDayOfWeek(DAY_NAMES[parsed.getDay()])
    }
  }

  function handleSelectAllow(arg: { start: Date; end: Date }) {
    const normalized = normalizeSelection(arg.start, arg.end)
    const preview = normalized.length > 1 ? normalized : []
    setLiveSelectionRanges((prev) => (sameTimeRanges(prev, preview) ? prev : preview))
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
      const payloadBlocks = payloadFromBlocks(blocks)
      const [rulesPayload, gridPayload] = await Promise.all([
        fetchJson<{ rule_count: number; rules: SuggestedRule[] }>('/api/schedule/analyze-rules', {
          method: 'POST',
          body: JSON.stringify({ blocks: payloadBlocks, catalog_rows: analyzerCatalogRows(availableEpisodes) }),
        }),
        Promise.all(
          scheduleWeekStarts.map((weekStart) =>
            fetchJson<GridPayload>('/api/schedule/blocks-to-grid', {
              method: 'POST',
              body: JSON.stringify({
                week_monday: weekStart.toISOString().slice(0, 10),
                blocks: payloadBlocks,
                require_complete: false,
              }),
            }),
          ),
        ),
      ])
      const missingSlotTotal = gridPayload.reduce((total, payload) => total + payload.missing_slot_count, 0)
      const rules = rulesPayload.rules || []
      const notes = buildScheduleNotes(blocks, availableEpisodes)
      setSuggestedRules(rules)
      setMissingSlotCount(missingSlotTotal)
      const missingText = `${missingSlotTotal.toLocaleString()} empty half-hour slot${
        missingSlotTotal === 1 ? '' : 's'
      }`
      const ruleText = `${rulesPayload.rule_count} rule suggestion${rulesPayload.rule_count === 1 ? '' : 's'}`
      setGenerateStatus(
        `Draft analyzed: ${rulesPayload.rule_count} rule suggestion${rulesPayload.rule_count === 1 ? '' : 's'} found.`,
      )
      setGenerateResult({
        generatedAt: new Date().toISOString(),
        stationId: stationId || '',
        weekCount: scheduleLengthWeeks,
        weekStarts: scheduleWeekStarts.map((weekStart) => weekStart.toISOString().slice(0, 10)),
        payloadBlocks,
        grids: gridPayload,
        rules,
        notes,
        missingSlotTotal,
      })
      setResultWeekIndex(0)
      setViewMode('results')
      setGenerateNotice(`Schedule analyzed. ${missingText}. ${ruleText} found.`)
      setGenerateNoticeKind(missingSlotTotal === 0 ? 'success' : 'info')
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

  async function saveGeneratedBaseSchedule() {
    if (!generateResult || generateResult.missingSlotTotal > 0) return
    const notes = buildScheduleNotes(generateResult.payloadBlocks, availableEpisodes)
    setIsSavingBase(true)
    setGenerateNotice('Saving reviewed schedule as base schedule...')
    setGenerateNoticeKind('info')
    try {
      const savePayload = await fetchJson<{ label: string; path: string }>('/api/base-schedules/save', {
        method: 'POST',
        body: JSON.stringify({
          station_id: generateResult.stationId,
          week_monday: baseCalendarStart.toISOString().slice(0, 10),
          week_count: generateResult.weekCount,
          blocks: generateResult.payloadBlocks,
          suggested_rules: generateResult.rules,
          notes,
        }),
      })
      onBaseSaved?.(savePayload.label)
      setGenerateNotice(`Schedule saved as ${savePayload.label}.`)
      setGenerateNoticeKind('success')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Save failed.'
      setGenerateNotice(`Save failed: ${message}`)
      setGenerateNoticeKind('error')
    } finally {
      setIsSavingBase(false)
    }
  }

  async function downloadGeneratedReport(kind: 'binge' | 'grids') {
    if (!generateResult) return
    const label = stationReportLabel(generateResult.stationId)
    setDownloadStatus(`Preparing ${kind === 'binge' ? label : `${label} GRIDS`} download...`)
    try {
      await downloadScheduleWorkbook(kind, generateResult, baseCalendarStart)
      setDownloadStatus('')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Download failed.'
      setDownloadStatus(message)
    }
  }

  async function downloadGeneratedPackage(notes: ScheduleNote[]) {
    if (!generateResult) return
    setDownloadStatus('Preparing report download...')
    try {
      await downloadSchedulePackage(generateResult, baseCalendarStart, notes)
      setDownloadStatus('')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Download failed.'
      setDownloadStatus(message)
    }
  }

  if (viewMode === 'results' && generateResult) {
    const resultGrid = generateResult.grids[Math.min(resultWeekIndex, generateResult.grids.length - 1)]
    const gridPreviewCells = resultGrid ? buildGridPreviewCells(resultGrid, generateResult.payloadBlocks) : []
    const displayedNotes = buildScheduleNotes(generateResult.payloadBlocks, availableEpisodes)
    const reportLabel = stationReportLabel(generateResult.stationId)
    const resultBlocks = [...generateResult.payloadBlocks].sort(
      (a, b) => new Date(a.start).getTime() - new Date(b.start).getTime(),
    )
    const filledPercent = Math.round((totals.filledMinutes / totals.totalMinutes) * 100)
    const canSave = generateResult.missingSlotTotal === 0

    return (
      <main className="scheduler-shell">
        <header className="topbar">
          <div>
            {stationId ? <p className="station-context">Station ID: {stationId}</p> : null}
            <p className="subhead">Review the generated schedule report, grid preview, warnings, and suggested rules before saving.</p>
          </div>
          <div className="topbar-actions">
            <button className="ghost-action" type="button" onClick={() => setViewMode('builder')}>
              Back to Schedule
            </button>
            <button className="ghost-action" type="button" onClick={() => downloadGeneratedPackage(displayedNotes)}>
              Download Reports.zip
            </button>
            <button className="primary-action" type="button" disabled={!canSave || isSavingBase} onClick={saveGeneratedBaseSchedule}>
              {isSavingBase ? 'Saving...' : 'Save as Base Schedule'}
            </button>
          </div>
        </header>

        {generateNotice ? <div className={`generate-notice ${generateNoticeKind}`}>{generateNotice}</div> : null}
        {downloadStatus ? <p className="download-status">{downloadStatus}</p> : null}

        <section className="results-summary">
          <div className="result-metric">
            <span>Filled</span>
            <strong>{filledPercent}%</strong>
          </div>
          <div className="result-metric">
            <span>Empty half-hours</span>
            <strong>{generateResult.missingSlotTotal.toLocaleString()}</strong>
          </div>
          <div className="result-metric">
            <span>Notes</span>
            <strong>{displayedNotes.length.toLocaleString()}</strong>
          </div>
        </section>

        <section className="results-grid">
          <article className="result-card wide-result">
            <div className="result-card-header">
              <div>
                <h2>{reportLabel} Preview</h2>
                <span>{resultBlocks.length.toLocaleString()} scheduled blocks</span>
              </div>
              <button className="ghost-action small-action" type="button" onClick={() => downloadGeneratedReport('binge')}>
                Download {reportLabel}.xlsx
              </button>
            </div>
            <div className="report-table-wrap">
              <table className="report-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Start</th>
                    <th>End</th>
                    <th>Show</th>
                    <th>Episode</th>
                    <th>Slot</th>
                    <th>Runtime</th>
                    <th>Avails</th>
                  </tr>
                </thead>
                <tbody>
                  {resultBlocks.map((block) => {
                    const start = new Date(block.start)
                    const end = new Date(block.end)
                    const slotMinutes = minutesBetween(start, end)
                    return (
                      <tr key={block.id}>
                        <td>{formatShortDate(start)}</td>
                        <td>{formatClock(start)}</td>
                        <td>{formatClock(end)}</td>
                        <td>{block.show}</td>
                        <td>{episodeLabelFromBlock(block)}</td>
                        <td>{slotMinutes} min</td>
                        <td>{formatRuntimeMinutes(block.runtimeMinutes)}</td>
                        <td>{formatRuntimeMinutes(Math.max(0, slotMinutes - block.runtimeMinutes))}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </article>

          <article className="result-card">
            <div className="result-card-header">
              <div>
                <h2>{reportLabel} GRIDS Preview</h2>
                <span>{resultGrid ? `Week ${resultWeekIndex + 1} of ${generateResult.grids.length}` : 'No grid'}</span>
              </div>
              <button className="ghost-action small-action" type="button" onClick={() => downloadGeneratedReport('grids')}>
                Download {reportLabel} GRIDS.xlsx
              </button>
            </div>
            {generateResult.grids.length > 1 ? (
              <div className="week-nav compact-week-nav">
                <button
                  type="button"
                  onClick={() => setResultWeekIndex((index) => Math.max(0, index - 1))}
                  disabled={resultWeekIndex === 0}
                >
                  ←
                </button>
                <span>{resultGrid?.week_monday}</span>
                <button
                  type="button"
                  onClick={() => setResultWeekIndex((index) => Math.min(generateResult.grids.length - 1, index + 1))}
                  disabled={resultWeekIndex >= generateResult.grids.length - 1}
                >
                  →
                </button>
              </div>
            ) : null}
            {resultGrid ? (
              <div className="grid-preview-wrap">
                <table className="grid-preview">
                  <thead>
                    <tr>
                      <th>Time</th>
                      {DAY_NAMES.slice(1).concat(DAY_NAMES[0]).map((day) => (
                        <th key={day}>{day.slice(0, 3)}</th>
                      ))}
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gridPreviewCells.map((row, slot) => (
                      <tr key={`${resultGrid.week_monday}-${slot}`}>
                        <th>{slotLabel(slot)}</th>
                        {row.map((cell, dayIndex) =>
                          cell.hidden ? null : (
                            <td key={`${slot}-${dayIndex}`} rowSpan={cell.rowSpan} className={cell.filled ? 'filled-cell merged-cell' : ''}>
                              {cell.text}
                            </td>
                          ),
                        )}
                        <th>{slotLabel(slot)}</th>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </article>

          <article className="result-card">
            <div className="result-card-header">
              <div>
                <h2>Warnings and Notes</h2>
                <span>{displayedNotes.length || 'None'}</span>
              </div>
              <button className="ghost-action small-action" type="button" onClick={() => downloadScheduleNotes(displayedNotes, generateResult.stationId)}>
                Download Notes.csv
              </button>
            </div>
            <div className="result-list">
              {displayedNotes.length ? (
                displayedNotes.map((note, index) => (
                  <div className={`result-note ${note.kind}`} key={`${note.show}-${index}`}>
                    <strong>{note.show}</strong>
                    <span>{note.message}</span>
                  </div>
                ))
              ) : (
                <p className="muted">No end-of-series or skipped-episode notes found.</p>
              )}
            </div>
          </article>

        </section>
      </main>
    )
  }

  return (
    <main className="scheduler-shell">
      <header className="topbar">
        <div>
          {stationId ? <p className="station-context">Station ID: {stationId}</p> : null}
          <p className="subhead">Drag across the calendar to highlight time, type a show, then fill the time slots in episode order.</p>
          <p className="autosave-note">Draft autosaves in this browser while you build.</p>
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
          Start date
          <input type="date" value={startDate} onChange={(event) => changeStartDate(event.target.value)} />
        </label>
        <label>
          First day of week
          <select value={firstDayOfWeek} onChange={(event) => setFirstDayOfWeek(event.target.value)}>
            {DAY_NAMES.map((day) => (
              <option key={day}>{day}</option>
            ))}
          </select>
        </label>
        <label>
          Start time
          <select value={startTimeHour} onChange={(event) => setStartTimeHour(Number(event.target.value))}>
            {START_TIME_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Schedule length
          <select value={scheduleLengthWeeks} onChange={(event) => setScheduleLengthWeeks(Number(event.target.value))}>
            <option value={1}>1 week</option>
            <option value={2}>2 weeks</option>
            <option value={4}>4 weeks</option>
          </select>
        </label>
      </section>

      <section className="workspace">
        <div className={`calendar-card${liveSelectionRanges.length > 1 ? ' is-normalized-drag' : ''}`}>
          {scheduleLengthWeeks > 1 ? (
            <div className="week-nav">
              <button
                type="button"
                onClick={() => setVisibleWeekIndex((index) => Math.max(0, index - 1))}
                disabled={visibleWeekIndex === 0}
              >
                ←
              </button>
              <span>
                Week {visibleWeekIndex + 1} of {scheduleLengthWeeks}
              </span>
              <button
                type="button"
                onClick={() => setVisibleWeekIndex((index) => Math.min(scheduleLengthWeeks - 1, index + 1))}
                disabled={visibleWeekIndex >= scheduleLengthWeeks - 1}
              >
                →
              </button>
            </div>
          ) : null}
          <FullCalendar
            plugins={[timeGridPlugin, interactionPlugin]}
            initialView="timeGridWeek"
            initialDate={calendarStart}
            key={`${startDate}-${firstDayOfWeek}-${visibleWeekIndex}-${startTimeHour}`}
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
            height="72vh"
            expandRows={false}
            nowIndicator={false}
            scrollTime={calendarScrollTime}
            scrollTimeReset={false}
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
            slotMinTime={calendarSlotMinTime}
            slotMaxTime={calendarSlotMaxTime}
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
                <option value="">
                  {inferredStartingEpisode ? `Auto: ${inferredStartingEpisode.code} - ${inferredStartingEpisode.title}` : 'Select episode'}
                </option>
                {episodesForShow.map((ep) => (
                  <option key={ep.id} value={ep.id}>
                    {ep.code} — {ep.title}
                    {movieNeedsTimingNote(ep, selectedSlotMinutes) ? ' (needs timing note)' : ''}
                  </option>
                ))}
              </select>
              {inferredStartingEpisode && !startingEpisodeId ? (
                <span className="picker-note">
                  Will continue with {inferredStartingEpisode.code} — {inferredStartingEpisode.title}
                </span>
              ) : null}
              {episodesForShow.some((ep) => movieNeedsTimingNote(ep, selectedSlotMinutes)) ? (
                <span className="picker-note">Some movies fit by runtime but need a title-start timing note.</span>
              ) : null}
            </label>

            <button
              className="primary-action wide"
              type="button"
              disabled={!selectedRanges.length || !matchingShow || (!startingEpisodeId && !inferredStartingEpisode)}
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
