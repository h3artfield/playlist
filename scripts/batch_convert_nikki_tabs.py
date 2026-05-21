#!/usr/bin/env python3
"""Convert Nikki workbook tabs to individual import-ready Excel files."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from binge_schedule import nikki
from binge_schedule.content_import import parse_playable_cell
from binge_schedule.models import NikkiColumnHeaders

WORKBOOK = Path(r"c:\Users\h3art\Downloads\2024 Nikki Spreadsheets.xlsx")
OUT_DIR = Path(r"c:\Users\h3art\Downloads")

SERIES_COLUMNS = [
    "Episode",
    "Season/Episode",
    "TRT",
    "Year/Original Airdate",
    "Genre",
    "Playable",
    "Stars",
    "Synopsis",
    "Notes",
]

MOVIE_COLUMNS = [
    "Title",
    "TRT",
    "B&W/Color",
    "Year/Original Airdate",
    "Genre",
    "Playable",
    "Stars",
    "Synopsis",
    "Notes",
]

# Tabs already converted — skip unless --force
SKIP_TABS = {
    "Bonanza - Bonanza",
    "Stingray",
    "Carol Burnett - NOTE - EPISODE ",
    "CPO Sharkey",
    "Dragnet - Dragnet",
    "The Gene Autry Show",
    "Greatest American Hero",
    "Life With Elizabeth",
}

GENRE_BY_SHEET: dict[str, str] = {
    "21 jump street": "action_drama",
    "ace crawford": "comedy_variety",
    "annie oakley": "western",
    "beverly hillbillies": "comedy_variety",
    "bonanza": "western",
    "californians": "western",
    "commish": "action_drama",
    "candid camera": "comedy_variety",
    "cpo sharkey": "comedy_variety",
    "date with the angels": "comedy_variety",
    "dragnet": "action_drama",
    "gene autry": "western",
    "greatest american hero": "action_drama",
    "wyatt earp": "western",
    "hawkeye": "action_adventure",
    "hunter": "action_drama",
    "laugh-in": "comedy_variety",
    "laugh in": "comedy_variety",
    "sherlock holmes": "action_adventure",
    "jack benny": "comedy_variety",
    "farscape": "action_adventure",
    "life with elizabeth": "comedy_variety",
    "lucy show": "comedy_variety",
    "mst3k": "cult_movie",
    "my little margie": "comedy_variety",
    "petticoat junction": "comedy_variety",
    "ozzie and harriet": "comedy_variety",
    "real mccoy": "western",
    "saint": "action_adventure",
    "secret agent": "action_adventure",
    "danger man": "action_adventure",
    "roy rogers": "western",
    "red skelton": "comedy_variety",
    "renegade": "action_drama",
    "republic of doyle": "action_drama",
    "route 66": "action_drama",
    "prisoner": "action_adventure",
    "silk stalkings": "action_drama",
    "space": "action_adventure",
    "texan": "western",
    "lone ranger": "western",
    "alf": "action_drama",
    "tim conway": "comedy_variety",
    "wiseguy": "action_drama",
    "jim bowie": "western",
    "bowie": "western",
    "stingray": "action_drama",
}

ROW_FILTER_BY_SHEET: dict[str, str] = {
    "carol burnett": nikki.ROW_FILTER_GREEN_EPISODE_CELL,
    "the saint": nikki.ROW_FILTER_EXCLUDE_RED_EPISODE_TEXT,
    "texan": nikki.ROW_FILTER_EXCLUDE_RED_EPISODE_TEXT,
    "republic of doyle": nikki.ROW_FILTER_EXCLUDE_RED_EPISODE_TEXT,
    "wiseguy": nikki.ROW_FILTER_EXCLUDE_RED_EPISODE_TEXT,
}

NEW_SHOWS_GENRE = "travel_lifestyle"

OUTPUT_NAME_OVERRIDES: dict[str, str] = {
    "21 Jump Street": "21_Jump_Street",
    "Ace Crawford - Ace Crawford…Pri": "Ace_Crawford",
    "Annie Oakley": "Annie_Oakley",
    "Beverly Hillbillies - The Bever": "Beverly_Hillbillies",
    "Bonanza - Bonanza": "Bonanza",
    "Californians": "Californians",
    "The Commish": "The_Commish",
    "Carol Burnett - NOTE - EPISODE ": "Carol_Burnett",
    "CPO Sharkey": "CPO_Sharkey",
    "Date With The Angels": "Date_With_The_Angels",
    "Dragnet - Dragnet": "Dragnet",
    "The Gene Autry Show": "Gene_Autry_Show",
    "Greatest American Hero": "Greatest_American_Hero",
    "The Life & Legend of Wyatt Earp": "Wyatt_Earp",
    "Hawkeye (color)": "Hawkeye",
    "Laugh-In - NOTE - CC Files are ": "Laugh_In",
    "SHERLOCK HOLMES": "Sherlock_Holmes",
    "Jack Benny Program": "Jack_Benny_Program",
    "FARSCAPE": "Farscape",
    "CANDID CAMERA": "Candid_Camera",
    "Life With Elizabeth": "Life_with_Elizabeth",
    "Lucy Show": "Lucy_Show",
    "MST3K - NOTE - Each episode fol": "MST3K",
    "My Little Margie": "My_Little_Margie",
    "Petticoat Junction": "Petticoat_Junction",
    "ozzie and harriet": "Ozzie_and_Harriet",
    "Real McCoys - NOTE - Each Seaso": "Real_McCoys",
    "The Saint - NOTE - Episode titl": "The_Saint",
    "Secret Agent _ Danger Man": "Secret_Agent_Danger_Man",
    "Roy Rogers": "Roy_Rogers",
    "Red Skelton - Color Episode": "Red_Skelton",
    "Republic Of Doyle - NOTE - Epis": "Republic_of_Doyle",
    "The Prisoner": "The_Prisoner",
    "silk stalkings": "Silk_Stalkings",
    "Space_ 1999": "Space_1999",
    "The Texan - Note - missing epis": "The_Texan",
    "The Lone Ranger": "The_Lone_Ranger",
    "ALF 2025": "ALF",
    "Tim Conway Comedy Hour - Note -": "Tim_Conway_Comedy_Hour",
    "Tim Conway Show": "Tim_Conway_Show",
    "Wiseguy - NOTE - Episode titles": "Wiseguy",
    "2025 JIM BOWIE": "Jim_Bowie",
    "movies": "Movies",
}


@dataclass
class ConvertResult:
    sheet: str
    output: Path | None = None
    rows: int = 0
    playable_yes: int = 0
    status: str = "ok"
    note: str = ""


def _clean(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _fix_text(text: str) -> str:
    return _clean(text).replace("\ufffd", "'").replace("\u2019", "'").replace("\u2018", "'")


def _format_airdate(value) -> str:
    if not _clean(value):
        return ""
    if isinstance(value, (int, float)) and not pd.isna(value):
        year = int(value)
        if 1900 <= year <= 2100:
            return str(year)
    text = _clean(value)
    if re.fullmatch(r"\d{4}", text):
        return text
    try:
        return pd.to_datetime(value).date().isoformat()
    except Exception:
        return text


def _season_ep_key(se: str) -> tuple[int, int]:
    text = _clean(se)
    if "_" in text:
        left, right = text.split("_", 1)
        try:
            return int(left), int(re.sub(r"\D.*", "", right) or "0")
        except ValueError:
            pass
    m = re.search(r"s(\d+)\s*e(\d+)", text, re.I)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 999, 999


def _genre_for_sheet(sheet: str) -> str:
    slug = sheet.casefold()
    for key, genre in GENRE_BY_SHEET.items():
        if key in slug:
            return genre
    return "action_drama"


def _row_filter_for_sheet(sheet: str) -> str | None:
    slug = sheet.casefold()
    for key, filt in ROW_FILTER_BY_SHEET.items():
        if key in slug:
            return filt
    return None


def _output_stem(sheet: str) -> str:
    if sheet in OUTPUT_NAME_OVERRIDES:
        return OUTPUT_NAME_OVERRIDES[sheet]
    stem = re.sub(r"[^\w]+", "_", sheet.strip()).strip("_")
    return stem or "Show"


def _output_path(sheet: str) -> Path:
    return OUT_DIR / f"{_output_stem(sheet)}_import_ready.xlsx"


def _augment_column_map(row: pd.Series, col_idx: dict[str, int]) -> dict[str, int]:
    hm = nikki._row_header_index_map(row)
    out = dict(col_idx)
    if "year" not in out:
        for alias in ("year/original airdate", "original airdate", "year"):
            if alias in hm:
                out["year"] = hm[alias]
                break
    if "trt" not in out:
        for alias in ("trt", "runtime", "duration", "run time"):
            if alias in hm:
                out["trt"] = hm[alias]
                break
    if "season_episode" not in out and "season/episode" in hm:
        out["season_episode"] = hm["season/episode"]
    if "notes" not in out and "notes" in hm:
        out["notes"] = hm["notes"]
    return out


def _find_header_row(df: pd.DataFrame, *, require_season_episode: bool = True) -> tuple[int | None, dict[str, int]]:
    headers = NikkiColumnHeaders.standard_series()
    if not require_season_episode:
        headers = NikkiColumnHeaders(
            episode="Episode",
            season_episode=None,
            year="Year/Original Airdate",
            stars="Stars",
            synopsis="Synopsis",
        )
    hr, col_idx = nikki._find_header_row_and_columns(df, headers)
    if hr is not None:
        return hr, _augment_column_map(df.iloc[hr], col_idx)

    if require_season_episode:
        return _find_header_row(df, require_season_episode=False)

    for i in range(min(35, len(df))):
        hm = nikki._row_header_index_map(df.iloc[i])
        if "episode" in hm or "title" in hm:
            idx: dict[str, int] = {}
            idx["episode"] = hm.get("episode", hm.get("title", 0))
            for alias in ("year/original airdate", "original airdate", "year"):
                if alias in hm:
                    idx["year"] = hm[alias]
                    break
            for alias in ("stars", "synopsis", "notes", "trt", "runtime", "season/episode"):
                if alias in hm:
                    key = "season_episode" if alias == "season/episode" else alias.split("/")[0]
                    idx[key] = hm[alias]
            return i, idx
    return None, {}


def _derive_season_episode(episode: str, existing: str = "") -> str:
    if existing:
        return existing.strip()
    patterns = [
        r"S(\d+)_E(\d+)",
        r"S(\d+)\s*E(\d+)",
        r"(\d+)_(\d+)",
    ]
    for pat in patterns:
        m = re.search(pat, episode, re.I)
        if m:
            return f"{int(m.group(1)):02d}_{int(m.group(2)):02d}"
    return ""


def _playable_for_row(
    row_index: int,
    *,
    row_filter: str | None,
    green_rows: set[int] | None,
    red_rows: set[int] | None,
    playable_col: int | None,
    df: pd.DataFrame,
) -> bool:
    if playable_col is not None:
        val = df.iloc[row_index, playable_col] if playable_col < len(df.columns) else None
        return parse_playable_cell(val)
    if row_filter == nikki.ROW_FILTER_GREEN_EPISODE_CELL:
        return green_rows is not None and row_index in green_rows
    if row_filter == nikki.ROW_FILTER_EXCLUDE_RED_EPISODE_TEXT:
        return red_rows is None or row_index not in red_rows
    return True


def _extract_standard_rows(
    df: pd.DataFrame,
    sheet: str,
    *,
    workbook_path: str,
    require_season_episode: bool = True,
    assign_sequential_se: bool = False,
) -> list[dict[str, str]]:
    hr, col_idx = _find_header_row(df, require_season_episode=require_season_episode)
    if hr is None or "episode" not in col_idx:
        return []

    ep_col = col_idx["episode"]
    se_col = col_idx.get("season_episode")
    year_col = col_idx.get("year")
    stars_col = col_idx.get("stars")
    syn_col = col_idx.get("synopsis")
    notes_col = col_idx.get("notes")
    trt_col = col_idx.get("trt") or col_idx.get("runtime")
    playable_col = col_idx.get("playable")

    row_filter = _row_filter_for_sheet(sheet)
    green_rows: set[int] | None = None
    red_rows: set[int] | None = None
    if row_filter == nikki.ROW_FILTER_GREEN_EPISODE_CELL:
        green_rows = nikki._green_episode_row_indices(
            workbook_path, sheet, header_row=hr, ep_col=ep_col, n_df_rows=len(df)
        )
    elif row_filter == nikki.ROW_FILTER_EXCLUDE_RED_EPISODE_TEXT:
        red_rows = nikki._red_episode_text_row_indices(
            workbook_path, sheet, header_row=hr, ep_col=ep_col, n_df_rows=len(df)
        )

    genre = _genre_for_sheet(sheet)
    rows: list[dict[str, str]] = []
    seq = 0
    for i in range(hr + 1, len(df)):
        if nikki._skip_instruction_row(df, i, hr, col_idx):
            continue
        episode_raw = df.iloc[i, ep_col]
        if pd.isna(episode_raw):
            continue
        episode = _fix_text(str(episode_raw))
        if not episode or nikki._norm_header(episode) == nikki._norm_header("Episode"):
            continue

        season_ep = ""
        if se_col is not None and se_col < len(df.columns):
            season_ep = _clean(df.iloc[i, se_col])
        season_ep = _derive_season_episode(episode, season_ep)
        if not season_ep and assign_sequential_se:
            seq += 1
            season_ep = f"01_{seq:02d}"
        elif not season_ep:
            seq += 1
            season_ep = f"01_{seq:02d}"

        rows.append(
            {
                "Episode": episode,
                "Season/Episode": season_ep,
                "TRT": _clean(df.iloc[i, trt_col]) if trt_col is not None and trt_col < len(df.columns) else "",
                "Year/Original Airdate": _format_airdate(df.iloc[i, year_col]) if year_col is not None and year_col < len(df.columns) else "",
                "Genre": genre,
                "Playable": "Yes" if _playable_for_row(i, row_filter=row_filter, green_rows=green_rows, red_rows=red_rows, playable_col=playable_col, df=df) else "No",
                "Stars": _fix_text(df.iloc[i, stars_col]) if stars_col is not None and stars_col < len(df.columns) else "",
                "Synopsis": _clean(df.iloc[i, syn_col]) if syn_col is not None and syn_col < len(df.columns) else "",
                "Notes": _clean(df.iloc[i, notes_col]) if notes_col is not None and notes_col < len(df.columns) else "",
            }
        )
    return rows


def _convert_stingray(df: pd.DataFrame) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i in range(len(df)):
        title = _clean(df.iloc[i, 0])
        if not title or title.lower() in {"episode", "table 1"}:
            continue
        trt = _clean(df.iloc[i, 1]) if len(df.columns) > 1 else ""
        season_ep = _clean(df.iloc[i, 2]) if len(df.columns) > 2 else ""
        synopsis = _clean(df.iloc[i, 3]) if len(df.columns) > 3 else ""
        if not season_ep:
            season_ep = _derive_season_episode(title) or f"01_{len(rows)+1:02d}"
        rows.append(
            {
                "Episode": title,
                "Season/Episode": season_ep,
                "TRT": trt,
                "Year/Original Airdate": "",
                "Genre": "action_drama",
                "Playable": "Yes",
                "Stars": "",
                "Synopsis": synopsis,
                "Notes": "",
            }
        )
    return rows


def _convert_cpo_sharkey(df: pd.DataFrame) -> list[dict[str, str]]:
    return _extract_standard_rows(
        df,
        "CPO Sharkey",
        workbook_path=str(WORKBOOK),
        require_season_episode=False,
        assign_sequential_se=False,
    )


def _convert_farscape(df: pd.DataFrame) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i in range(len(df)):
        episode = _clean(df.iloc[i, 0])
        synopsis = _clean(df.iloc[i, 1]) if len(df.columns) > 1 else ""
        if not episode or not episode.lower().startswith("farscape:"):
            continue
        if "season" in episode.lower() and " e" not in episode.lower():
            continue
        title = episode.split(" - ", 1)[-1].strip() if " - " in episode else episode
        season_ep = _derive_season_episode(episode) or f"01_{len(rows)+1:02d}"
        rows.append(
            {
                "Episode": title if title != episode else episode,
                "Season/Episode": season_ep,
                "TRT": "",
                "Year/Original Airdate": "",
                "Genre": "action_adventure",
                "Playable": "Yes",
                "Stars": "",
                "Synopsis": synopsis,
                "Notes": "",
            }
        )
    return rows


def _convert_candid_camera(df: pd.DataFrame) -> list[dict[str, str]]:
    hr, col_idx = _find_header_row(df, require_season_episode=False)
    if hr is None:
        return []
    ep_col = col_idx["episode"]
    syn_col = col_idx.get("synopsis", 1)
    rows: list[dict[str, str]] = []
    seq = 0
    for i in range(hr + 1, len(df)):
        code = _clean(df.iloc[i, ep_col])
        if not code or not re.search(r"\d", code):
            continue
        seq += 1
        rows.append(
            {
                "Episode": code,
                "Season/Episode": f"01_{seq:02d}",
                "TRT": "",
                "Year/Original Airdate": "",
                "Genre": "comedy_variety",
                "Playable": "Yes",
                "Stars": "",
                "Synopsis": _clean(df.iloc[i, syn_col]) if syn_col < len(df.columns) else "",
                "Notes": "",
            }
        )
    return rows


def _convert_jim_bowie(df: pd.DataFrame) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i in range(len(df)):
        cell = _clean(df.iloc[i, 0])
        if not cell:
            continue
        cell = re.sub(r"^:\s*", "", cell)
        m = re.match(r"S(\d+)\s*E(\d+)\s*-\s*(.+)", cell, re.I)
        if not m:
            continue
        season, ep, title = int(m.group(1)), int(m.group(2)), _fix_text(m.group(3))
        rows.append(
            {
                "Episode": title,
                "Season/Episode": f"{season:02d}_{ep:02d}",
                "TRT": "",
                "Year/Original Airdate": "",
                "Genre": "western",
                "Playable": "Yes",
                "Stars": "",
                "Synopsis": "",
                "Notes": "",
            }
        )
    return rows


def _convert_movies(df: pd.DataFrame) -> list[dict[str, str]]:
    hr, col_idx = nikki._find_header_row_and_columns(df, NikkiColumnHeaders.movies_tab())
    if hr is None:
        return []
    title_col = col_idx["episode"]
    year_col = col_idx.get("year")
    rows: list[dict[str, str]] = []
    hm = nikki._row_header_index_map(df.iloc[hr])
    trt_col = hm.get("trt")
    bw_col = hm.get("b&w/color") or hm.get("b&w / color")
    genre_col = hm.get("genre")
    stars_col = hm.get("stars")
    syn_col = hm.get("synopsis")
    notes_col = hm.get("notes")

    for i in range(hr + 1, len(df)):
        title = _fix_text(df.iloc[i, title_col])
        if not title:
            continue
        raw_genre = _clean(df.iloc[i, genre_col]) if genre_col is not None else ""
        genre = raw_genre.split(",")[0].strip().lower().replace(" ", "_") if raw_genre else "drama"
        rows.append(
            {
                "Title": title,
                "TRT": _clean(df.iloc[i, trt_col]) if trt_col is not None else "",
                "B&W/Color": _clean(df.iloc[i, bw_col]) if bw_col is not None else "",
                "Year/Original Airdate": _format_airdate(df.iloc[i, year_col]) if year_col is not None else "",
                "Genre": genre,
                "Playable": "Yes",
                "Stars": _fix_text(df.iloc[i, stars_col]) if stars_col is not None else "",
                "Synopsis": _clean(df.iloc[i, syn_col]) if syn_col is not None else "",
                "Notes": _clean(df.iloc[i, notes_col]) if notes_col is not None else "",
            }
        )
    return rows


def _convert_new_shows(df: pd.DataFrame) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for i in range(1, len(df)):
        artist = _clean(df.iloc[i, 0]) if len(df.columns) > 0 else ""
        internal = _clean(df.iloc[i, 1]) if len(df.columns) > 1 else ""
        sort_title = _clean(df.iloc[i, 2]) if len(df.columns) > 2 else ""
        desc = _clean(df.iloc[i, 3]) if len(df.columns) > 3 else ""
        short_desc = _clean(df.iloc[i, 4]) if len(df.columns) > 4 else ""
        if not artist:
            continue
        if not internal or internal == artist:
            continue
        if sort_title == artist:
            continue
        episode_title = sort_title or internal
        season_ep = _derive_season_episode(internal) or _derive_season_episode(sort_title)
        if not season_ep:
            season_ep = f"01_{len(grouped.get(artist, []))+1:02d}"
        row = {
            "Episode": episode_title,
            "Season/Episode": season_ep,
            "TRT": "",
            "Year/Original Airdate": "",
            "Genre": NEW_SHOWS_GENRE,
            "Playable": "Yes",
            "Stars": "",
            "Synopsis": desc or short_desc,
            "Notes": "",
        }
        grouped.setdefault(artist, []).append(row)
    for artist in grouped:
        grouped[artist].sort(key=lambda r: _season_ep_key(r["Season/Episode"]))
    return grouped


def _write_series(sheet: str, rows: list[dict[str, str]], output: Path) -> ConvertResult:
    if not rows:
        return ConvertResult(sheet=sheet, status="empty", note="no rows extracted")
    df = pd.DataFrame(rows)
    df = df.sort_values(by="Season/Episode", key=lambda s: s.map(lambda v: _season_ep_key(str(v))))
    sheet_name = sheet[:31]
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df[SERIES_COLUMNS].to_excel(writer, sheet_name=sheet_name, index=False)
    yes = int((df["Playable"] == "Yes").sum())
    return ConvertResult(sheet=sheet, output=output, rows=len(df), playable_yes=yes)


def _write_movies(rows: list[dict[str, str]], output: Path) -> ConvertResult:
    df = pd.DataFrame(rows)
    df = df.sort_values(by="Title")
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df[MOVIE_COLUMNS].to_excel(writer, sheet_name="movies", index=False)
    return ConvertResult(sheet="movies", output=output, rows=len(df), playable_yes=len(df))


def convert_tab(sheet: str, *, force: bool = False) -> list[ConvertResult]:
    if sheet in SKIP_TABS and not force:
        return [ConvertResult(sheet=sheet, status="skipped", note="already converted")]

    output = _output_path(sheet)
    df = pd.read_excel(WORKBOOK, sheet_name=sheet, header=None)

    if sheet == "NEW SHOWS":
        results: list[ConvertResult] = []
        grouped = _convert_new_shows(df)
        for artist, rows in sorted(grouped.items()):
            stem = re.sub(r"[^\w]+", "_", artist.strip()).strip("_")
            out = OUT_DIR / f"{stem}_import_ready.xlsx"
            results.append(_write_series(artist, rows, out))
        return results

    if sheet == "movies":
        rows = _convert_movies(df)
        return [_write_movies(rows, output)]

    if sheet == "FARSCAPE":
        rows = _convert_farscape(df)
        return [_write_series(sheet, rows, output)]

    if sheet == "CANDID CAMERA":
        rows = _convert_candid_camera(df)
        return [_write_series(sheet, rows, output)]

    if sheet == "2025 JIM BOWIE":
        rows = _convert_jim_bowie(df)
        return [_write_series(sheet, rows, output)]

    if sheet == "Stingray":
        rows = _convert_stingray(df)
        return [_write_series(sheet, rows, output)]

    if sheet == "CPO Sharkey":
        rows = _convert_cpo_sharkey(df)
        return [_write_series(sheet, rows, output)]

    if sheet == "Hawkeye (color)":
        rows = _extract_standard_rows(
            df, sheet, workbook_path=str(WORKBOOK), require_season_episode=False, assign_sequential_se=True
        )
        return [_write_series(sheet, rows, output)]

    rows = _extract_standard_rows(df, sheet, workbook_path=str(WORKBOOK))
    return [_write_series(sheet, rows, output)]


def main() -> int:
    force = "--force" in sys.argv
    if not WORKBOOK.is_file():
        print(f"Workbook not found: {WORKBOOK}", file=sys.stderr)
        return 1

    import openpyxl

    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)
    sheets = list(wb.sheetnames)
    wb.close()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_results: list[ConvertResult] = []

    for sheet in sheets:
        try:
            results = convert_tab(sheet, force=force)
            all_results.extend(results)
        except Exception as exc:
            all_results.append(ConvertResult(sheet=sheet, status="error", note=str(exc)[:200]))

    ok = [r for r in all_results if r.status == "ok"]
    skipped = [r for r in all_results if r.status == "skipped"]
    empty = [r for r in all_results if r.status == "empty"]
    errors = [r for r in all_results if r.status == "error"]

    print(f"Workbook: {WORKBOOK}")
    print(f"Output dir: {OUT_DIR}")
    print(f"Converted: {len(ok)} files | Skipped: {len(skipped)} | Empty: {len(empty)} | Errors: {len(errors)}")
    print()
    for r in sorted(ok, key=lambda x: x.sheet):
        print(f"  OK  {r.rows:4d} rows ({r.playable_yes:4d} Yes)  {r.output.name if r.output else ''}")
    for r in skipped:
        print(f"  SKIP  {r.sheet}")
    for r in empty:
        print(f"  EMPTY {r.sheet} — {r.note}")
    for r in errors:
        print(f"  ERR   {r.sheet} — {r.note}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
