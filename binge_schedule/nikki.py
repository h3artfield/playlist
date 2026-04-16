from __future__ import annotations

import re
from typing import Optional

import pandas as pd

from binge_schedule.models import Episode


def _clean(s: str) -> str:
    return " ".join(str(s).replace("\xa0", " ").split()).strip()


def _parse_jim_bowie_line(cell: str) -> Optional[tuple[int, str]]:
    s = _clean(cell)
    s = re.sub(r"^:\s*", "", s)
    m = re.match(r"S(\d+)\s*E(\d+)\s*-\s*(.+)", s, re.I)
    if not m:
        m = re.match(r"(\d+)\s*E(\d+)\s*-\s*(.+)", s, re.I)
    if not m:
        return None
    season, ep, title = int(m.group(1)), int(m.group(2)), _clean(m.group(3))
    code_num = season * 100 + ep
    return code_num, title


def load_jim_bowie(df: pd.DataFrame) -> list[Episode]:
    out: list[Episode] = []
    for i in range(len(df)):
        cell = df.iloc[i, 0]
        if pd.isna(cell):
            continue
        parsed = _parse_jim_bowie_line(str(cell))
        if not parsed:
            continue
        num, title = parsed
        code = f"AJB{num}"
        out.append(Episode(raw=str(cell), title=title, code=code, episode_num=num))
    return out


def _header_row_index(df: pd.DataFrame) -> Optional[int]:
    for i in range(min(15, len(df))):
        row = df.iloc[i]
        for j in range(min(6, len(row))):
            v = row.iloc[j]
            if pd.isna(v):
                continue
            if "episode" in str(v).lower():
                return i
    return None


def _title_from_episode_cell(cell: str) -> str:
    s = _clean(cell)
    if " - " in s:
        return s.split(" - ", 1)[-1].strip()
    return s


def _code_from_hunter(cell: str) -> Optional[tuple[str, int]]:
    m = re.search(r"HUN_(\d+)", cell, re.I)
    if m:
        n = int(m.group(1))
        return f"HUN{n}", n
    return None


def _code_from_texan(cell: str) -> Optional[tuple[str, int]]:
    m = re.search(r"S(\d+)_EP(\d+)", cell, re.I)
    if m:
        s, e = int(m.group(1)), int(m.group(2))
        n = s * 100 + e
        return f"TEX{n}", n
    return None


def _code_from_renegade(cell: str) -> Optional[tuple[str, int]]:
    m = re.search(r"S(\d+)E(\d+)", cell, re.I)
    if m:
        s, e = int(m.group(1)), int(m.group(2))
        n = s * 100 + e
        return f"REN{n}", n
    return None


def _code_from_leading_digits(cell: str, prefix: str) -> Optional[tuple[str, int]]:
    m = re.match(r"(\d+)\s*-\s*", cell)
    if m:
        n = int(m.group(1))
        return f"{prefix}{n}", n
    return None


def _code_from_carol(cell: str, season_ep: str) -> tuple[str, int]:
    m = re.match(r"(\d+)\s*-\s*", cell)
    if m:
        n = int(m.group(1))
        return f"CBS{n}", n
    parts = str(season_ep).split("_")
    if len(parts) == 2:
        try:
            a, b = int(parts[0]), int(parts[1])
            n = a * 100 + b
            return f"CBS{n}", n
        except ValueError:
            pass
    h = abs(hash(cell)) % 900000 + 100000
    return f"CBS{h}", h


def _code_from_mst3k(cell: str, season_ep: str) -> tuple[str, int]:
    parts = str(season_ep).split("_")
    if len(parts) == 2:
        try:
            a, b = int(parts[0]), int(parts[1])
            n = a * 100 + b
            return f"MST{n}", n
        except ValueError:
            pass
    h = abs(hash(cell)) % 900 + 100
    return f"MST{h}", h


def _code_from_jmp(cell: str) -> Optional[tuple[str, int]]:
    m = re.search(r"JMP_(\d+)", cell, re.I)
    if m:
        n = int(m.group(1))
        return f"JMP{n}", n
    return None


def _code_from_se_underscore(cell: str, prefix: str) -> Optional[tuple[str, int]]:
    m = re.search(r"S(\d+)_E(\d+)", cell, re.I)
    if m:
        s, e = int(m.group(1)), int(m.group(2))
        n = s * 100 + e
        return f"{prefix}{n}", n
    return None


def load_standard_sheet(
    df: pd.DataFrame,
    *,
    style: str = "generic",
    prefix: str = "",
) -> list[Episode]:
    """Load rows after an 'Episode' header row."""
    hr = _header_row_index(df)
    if hr is None:
        return []
    start = hr + 1
    out: list[Episode] = []
    for i in range(start, len(df)):
        cell = df.iloc[i, 0]
        if pd.isna(cell):
            continue
        raw = str(cell)
        s = _clean(raw)
        if not s or s.lower() == "episode":
            continue
        season_ep = ""
        if len(df.columns) > 1:
            v1 = df.iloc[i, 1]
            if pd.notna(v1) and str(v1).strip():
                season_ep = str(v1).strip()
        title = _title_from_episode_cell(s)

        code: Optional[str] = None
        epn: Optional[int] = None

        if style == "hunter":
            t = _code_from_hunter(s)
            if t:
                code, epn = t
        elif style == "texan":
            t = _code_from_texan(s)
            if t:
                code, epn = t
        elif style == "renegade":
            t = _code_from_renegade(s)
            if t:
                code, epn = t
        elif style == "real_mccoys":
            t = _code_from_leading_digits(s, prefix or "MCC")
            if t:
                code, epn = t
        elif style == "leading_episode":
            t = _code_from_leading_digits(s, prefix or "EP")
            if t:
                code, epn = t
        elif style == "carol_burnett":
            code, epn = _code_from_carol(s, season_ep)
        elif style == "mst3k":
            code, epn = _code_from_mst3k(s, season_ep)
        elif style == "jmp":
            t = _code_from_jmp(s)
            if t:
                code, epn = t
            else:
                code, epn = f"JMP{i}", i
        elif style in ("saint", "laugh_in"):
            pfx = prefix or ("SNT" if style == "saint" else "RML")
            t = _code_from_se_underscore(s, pfx)
            if t:
                code, epn = t
            else:
                code, epn = f"{pfx}{i}", i
        else:
            seq = len(out) + 1
            if prefix:
                code, epn = f"{prefix}{seq}", seq
            else:
                code, epn = f"EP{seq}", seq

        if code is None:
            seq = len(out) + 1
            code, epn = f"EP{seq}", seq

        out.append(Episode(raw=raw, title=title, code=code, episode_num=epn, season_ep=season_ep or None))
    return out


STYLE_BY_PREFIX = {
    "AJB": "jim_bowie",
    "TEX": "texan",
    "HUN": "hunter",
    "REN": "renegade",
    "MCC": "real_mccoys",
    "CBS": "carol_burnett",
    "MST": "mst3k",
}


def load_sheet(path: str, sheet_name: str, *, style: str, prefix: str = "") -> list[Episode]:
    df = pd.read_excel(path, sheet_name=sheet_name, header=None)
    if style == "jim_bowie":
        return load_jim_bowie(df)
    return load_standard_sheet(df, style=style, prefix=prefix)


def default_style_for_sheet(sheet_name: str) -> str:
    u = sheet_name.upper()
    if "JIM BOWIE" in u or "BOWIE" in u:
        return "jim_bowie"
    if "TEXAN" in u:
        return "texan"
    if sheet_name == "Hunter" or u == "HUNTER":
        return "hunter"
    if "RENEGADE" in u:
        return "renegade"
    if "REAL MCCOY" in u:
        return "real_mccoys"
    if "CAROL BURNETT" in u:
        return "carol_burnett"
    if "MST3K" in u or "MYSTERY SCIENCE" in u:
        return "mst3k"
    if "21 JUMP" in u:
        return "jmp"
    if "SAINT" in u and "SHERLOCK" not in u:
        return "saint"
    if "LAUGH-IN" in u or "LAUGH IN" in u:
        return "laugh_in"
    if "TIM CONWAY COMEDY" in u:
        return "leading_episode"
    return "generic"
