export type RowKind = 'auto' | 'series' | 'movie'
export type MatchQuality = 'exact' | 'likely' | 'manual' | 'unmapped' | 'inferred'

export type CanonicalField = {
  key: string
  label: string
  required: boolean
}

export type MappingSummaryItem = {
  field: string
  column: string
}

export type SheetLayout = 'header' | 'inferred'

export type SheetAnalysis = {
  name: string
  row_count: number
  data_row_count: number
  column_count: number
  header_row: number
  header_score: number
  layout?: SheetLayout
  data_start_row?: number
  inferred_column_names?: string[]
  source_columns: string[]
  suggested_mapping: Record<string, string>
  mapping_match: Record<string, MatchQuality>
  suggested_row_kind: RowKind
  default_series_title: string
  include: boolean
  skip_reason: string
  sample_rows?: PreviewRow[]
  mapping_summary?: MappingSummaryItem[]
}

export type SheetConfig = {
  sheet_name: string
  include: boolean
  header_row: number
  row_kind: RowKind
  default_series_title: string
  mapping: Record<string, string>
  layout?: SheetLayout
  data_start_row?: number
  inferred_column_names?: string[]
}

export type ParseImportResponse = {
  session_id: string
  filename: string
  fields: CanonicalField[]
  sheets: SheetAnalysis[]
}

export type CatalogMatchKind = 'update' | 'new_episode' | 'new_show' | 'new_movie'

export type PreviewRow = {
  content_type: string
  display_name: string
  series_title?: string
  episode_number?: string
  episode_title?: string
  runtime_minutes?: number | null
  genre?: string
  source_sheet?: string
  catalog_match?: CatalogMatchKind
  catalog_match_label?: string
}

export type ShowMatchSummary = {
  show_name: string
  in_catalog: boolean
  catalog_episode_count: number
  new_episodes: number
  updates: number
  is_new_show: boolean
}

export type ImportMatchStats = {
  new_shows: number
  new_episodes: number
  updates: number
  new_movies: number
}

export type PreviewIssue = {
  sheet: string
  row: number | null
  level: string
  message: string
}

export type PreviewImportResponse = {
  ready_count: number
  warning_count: number
  skipped_count: number
  error_count: number
  total_count: number
  preview_rows: PreviewRow[]
  issues: PreviewIssue[]
  per_sheet: { sheet_name: string; row_count: number; issues: number }[]
  can_import: boolean
  match_stats?: ImportMatchStats
  show_summaries?: ShowMatchSummary[]
}

export type CommitImportResponse = {
  imported_count?: number
  catalog_row_count?: number
  imported_row_count?: number
  warning_count?: number
  skipped_count?: number
  match_stats?: ImportMatchStats
}

export type CatalogRow = {
  display_name?: string
  episode_title?: string
  content_type?: string
}

export function normalizeShowKey(name: string): string {
  return name.trim().toLowerCase().replace(/\s+/g, ' ')
}

export function catalogEpisodeCountByShow(rows: CatalogRow[]): Map<string, number> {
  const counts = new Map<string, number>()
  for (const row of rows) {
    const name = row.display_name?.trim()
    if (!name) continue
    const key = normalizeShowKey(name)
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }
  return counts
}

export function sheetToConfig(sheet: SheetAnalysis): SheetConfig {
  return {
    sheet_name: sheet.name,
    include: sheet.include,
    header_row: sheet.header_row,
    row_kind: sheet.suggested_row_kind,
    default_series_title: sheet.default_series_title,
    mapping: { ...sheet.suggested_mapping },
    layout: sheet.layout,
    data_start_row: sheet.data_start_row,
    inferred_column_names: sheet.inferred_column_names,
  }
}
