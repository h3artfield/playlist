from __future__ import annotations

import pandas as pd

from binge_schedule.content_catalog import canonical_rows_from_imported_rows
from binge_schedule.content_import import (
    imported_row_is_playable,
    parse_playable_cell,
    rows_from_dataframe,
)
from binge_schedule.models import NikkiColumnHeaders
from binge_schedule import nikki


def test_parse_playable_cell_yes_no_and_blank():
    assert parse_playable_cell("Yes") is True
    assert parse_playable_cell("y") is True
    assert parse_playable_cell(1) is True
    assert parse_playable_cell("No") is False
    assert parse_playable_cell("") is False
    assert parse_playable_cell(None) is False
    assert parse_playable_cell("maybe") is False


def test_imported_row_is_playable_legacy_defaults_true():
    assert imported_row_is_playable({"episode_title": "Pilot"}) is True
    assert imported_row_is_playable({"playable": False}) is False
    assert imported_row_is_playable({"playable": "Yes"}) is True


def test_rows_from_dataframe_keeps_non_playable_rows_in_catalog():
    df = pd.DataFrame(
        [
            {
                "Episode": "Ep 1",
                "Season/Episode": "01_01",
                "Playable": "No",
            },
            {
                "Episode": "Ep 6",
                "Season/Episode": "01_06",
                "Playable": "Yes",
            },
        ]
    )
    rows = rows_from_dataframe(df, sheet_name="Demo Show", source_name="demo.xlsx")
    assert len(rows) == 2
    assert rows[0]["playable"] is False
    assert rows[1]["playable"] is True


def test_canonical_rows_mark_non_playable_availability():
    imported = [
        {
            "content_type": "series",
            "display_name": "Demo Show",
            "series_title": "Demo Show",
            "episode_number": "01_01",
            "episode_title": "Ep 1",
            "playable": False,
        },
        {
            "content_type": "series",
            "display_name": "Demo Show",
            "series_title": "Demo Show",
            "episode_number": "01_06",
            "episode_title": "Ep 6",
            "playable": True,
        },
    ]
    rows = canonical_rows_from_imported_rows(imported, station_id="test")
    assert rows[0]["availability_status"] == "not_playable"
    assert rows[1]["availability_status"] == "available"


def test_nikki_load_standard_sheet_filters_playable_column():
    df = pd.DataFrame(
        [
            ["Episode", "Season/Episode", "Playable"],
            ["Ep 1", "01_01", "No"],
            ["Ep 2", "01_02", ""],
            ["Ep 6", "01_06", "Yes"],
        ]
    )
    episodes = nikki.load_standard_sheet(
        df,
        style="generic",
        prefix="DEM",
        columns=NikkiColumnHeaders.standard_series(),
    )
    assert [ep.title for ep in episodes] == ["Ep 6"]
    assert episodes[0].episode_num == 1
