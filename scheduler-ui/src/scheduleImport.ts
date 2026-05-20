type ScheduledBlock = {
  id: string
  start: string
  end: string
  [key: string]: unknown
}

export function draftStorageKey(stationId?: string): string {
  return `schedule-builder-draft:${(stationId || 'default').trim() || 'default'}`
}

export function clearScheduleDraft(stationId?: string): void {
  try {
    window.localStorage.removeItem(draftStorageKey(stationId))
  } catch {
    // ignore
  }
}

export function normalizeWeekCount(raw: number): number {
  const value = Number(raw)
  if (!Number.isFinite(value)) return 1
  return Math.max(1, Math.min(4, Math.round(value)))
}

function isoLocal(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:00`
}

export function mondayOnOrBefore(isoDate: string): string {
  const d = new Date(isoDate.includes('T') ? isoDate : `${isoDate.slice(0, 10)}T12:00:00`)
  const mondayOffset = (d.getDay() + 6) % 7
  const monday = new Date(d)
  monday.setDate(d.getDate() - mondayOffset)
  monday.setHours(0, 0, 0, 0)
  return isoLocal(monday).slice(0, 10)
}

export function addDaysToIsoDate(isoDate: string, days: number): string {
  const d = new Date(`${isoDate.slice(0, 10)}T12:00:00`)
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

export function formatWeekCountLabel(weekCount: number): string {
  const count = normalizeWeekCount(weekCount)
  return `${count} week${count === 1 ? '' : 's'}`
}

export function formatScheduleWeekRange(weekMondayIso: string | undefined, weekCount: number): string {
  if (!weekMondayIso) return ''
  const weeks = normalizeWeekCount(weekCount)
  const start = new Date(`${weekMondayIso.slice(0, 10)}T12:00:00`)
  const end = new Date(start)
  end.setDate(end.getDate() + weeks * 7 - 1)
  const fmt = (d: Date) => `${d.getMonth() + 1}/${d.getDate()}/${d.getFullYear()}`
  return `${fmt(start)} – ${fmt(end)}`
}

export function savedScheduleWeekCount(base: {
  template_week_count?: number
  week_count?: number
}): number {
  return normalizeWeekCount(base.template_week_count || base.week_count || 1)
}

export function confirmAutoGenerate(savedWeeks: number, generateWeeks: number): boolean {
  const saved = normalizeWeekCount(savedWeeks)
  const generate = normalizeWeekCount(generateWeeks)
  const savedLabel = formatWeekCountLabel(saved)
  const generateLabel = formatWeekCountLabel(generate)
  const continuation =
    'Series episodes continue from where you left off (wrapping at the end of each show). Movies and paid programming stay in the same time slots.'

  if (generate === saved) {
    return window.confirm(
      `The saved schedule is ${savedLabel}.\n\nGenerate the next ${generateLabel} using the same pattern?\n\n${continuation}`,
    )
  }

  return window.confirm(
    `The saved schedule is ${savedLabel}. Are you sure you want to generate ${generateLabel}?\n\n${continuation}`,
  )
}

export function shiftBlocksToMonday(blocks: ScheduledBlock[], targetMondayIso: string): ScheduledBlock[] {
  if (!blocks.length) return blocks
  const earliest = blocks.reduce((min, block) => {
    const value = new Date(block.start).getTime()
    return value < min ? value : min
  }, new Date(blocks[0].start).getTime())
  const currentMonday = mondayOnOrBefore(new Date(earliest).toISOString())
  const targetMonday = mondayOnOrBefore(targetMondayIso)
  if (currentMonday === targetMonday) return blocks

  const shiftMs = new Date(`${targetMonday}T00:00:00`).getTime() - new Date(`${currentMonday}T00:00:00`).getTime()
  return blocks.map((block) => {
    const start = new Date(block.start)
    const end = new Date(block.end)
    const newStart = new Date(start.getTime() + shiftMs)
    const newEnd = new Date(end.getTime() + shiftMs)
    const stem = block.id.includes('-') ? block.id.slice(0, block.id.lastIndexOf('-')) : block.id
    return {
      ...block,
      id: `${stem}-${newStart.getTime()}`,
      start: isoLocal(newStart),
      end: isoLocal(newEnd),
    }
  })
}

type AutoGenerateLike = {
  station_id: string
  week_monday: string
  week_count: number
  blocks: ScheduledBlock[]
}

type NormalizeRequest = {
  requestedWeeks: number
  baseWeekMonday?: string
  baseTemplateWeeks?: number
  templateBlockCount?: number
}

export function normalizeAutoGenerateResult<T extends AutoGenerateLike>(
  result: T,
  request: NormalizeRequest,
): T {
  const requestedWeeks = normalizeWeekCount(request.requestedWeeks)
  let blocks = result.blocks
  let weekMonday = result.week_monday
  let weekCount = normalizeWeekCount(result.week_count)

  if (request.baseWeekMonday) {
    const templateWeeks = normalizeWeekCount(request.baseTemplateWeeks || 1)
    const expectedMonday = addDaysToIsoDate(request.baseWeekMonday, templateWeeks * 7)
    const blockMonday = blocks.length ? mondayOnOrBefore(blocks[0].start) : weekMonday
    if (blockMonday === request.baseWeekMonday || weekMonday === request.baseWeekMonday) {
      weekMonday = expectedMonday
      blocks = shiftBlocksToMonday(blocks, expectedMonday)
    } else if (weekMonday) {
      blocks = shiftBlocksToMonday(blocks, weekMonday)
    }
  } else if (weekMonday) {
    blocks = shiftBlocksToMonday(blocks, weekMonday)
  }

  const templateBlocksPerWeek = Math.max(
    1,
    Math.round((request.templateBlockCount || blocks.length) / Math.max(1, request.baseTemplateWeeks || 1)),
  )
  const expectedBlockCount = templateBlocksPerWeek * requestedWeeks

  if (weekCount < requestedWeeks && blocks.length >= expectedBlockCount * 0.9) {
    weekCount = requestedWeeks
  }

  if (requestedWeeks > 1 && blocks.length < expectedBlockCount * 0.75) {
    throw new Error(
      'Only one week came back from the API. Close the Schedule Builder desktop app if it is running, restart the dev API, then try Auto Generate again.',
    )
  }

  return {
    ...result,
    blocks,
    week_monday: weekMonday,
    week_count: weekCount,
  }
}
