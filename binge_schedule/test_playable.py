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


def test_nikki_load_movies_accepts_year_original_airdate_header():
    df = pd.DataFrame(
        [
            ["Title", "TRT", "Year/Original Airdate", "Playable"],
            ["Alpha Movie", 90, 1999, "Yes"],
            ["Beta Movie", 120, 2001, "Yes"],
        ]
    )
    episodes = nikki.load_movies(
        df,
        prefix="MOV",
        columns=NikkiColumnHeaders.movies_tab(),
    )
    assert len(episodes) == 2
    assert episodes[0].title == "Alpha Movie (1999)"
    assert episodes[1].title == "Beta Movie (2001)"


def test_runtime_minutes_from_cell_parses_excel_trt_mm_ss():
    from datetime import time

    from binge_schedule.content_import import _runtime_minutes_from_cell

    assert _runtime_minutes_from_cell("21:20") == 21
    assert _runtime_minutes_from_cell(time(21, 20, 0)) == 21
    assert _runtime_minutes_from_cell(time(0, 21, 20)) == 21
    assert _runtime_minutes_from_cell("0:52:35") == 52
    assert _runtime_minutes_from_cell(time(0, 52, 35)) == 52


def test_import_wizard_movies_mapping_does_not_duplicate_title_as_series():
    from binge_schedule.content_import_wizard import analyze_sheet

    df_raw = pd.DataFrame(
        [
            ["Title", "TRT", "Year/Original Airdate", "Genre", "Playable", "Synopsis"],
            ["Alpha Movie", 90, 1999, "Drama", "Yes", "Summary"],
        ]
    )
    analysis = analyze_sheet("MOVIES", df_raw)
    mapping = analysis["suggested_mapping"]
    assert mapping["title"] == "Title"
    assert mapping.get("series_title", "") == ""
    assert analysis["suggested_row_kind"] == "movie"


def test_imported_series_without_trt_uses_configured_binge_row_minutes():
    from binge_schedule.content_catalog import canonical_rows_from_imported_rows

    rows = canonical_rows_from_imported_rows(
        [
            {
                "content_type": "series",
                "display_name": "Hunter",
                "series_title": "Hunter",
                "episode_number": "01_01",
                "episode_title": "Pilot",
                "source_sheet": "Hunter",
            }
        ],
        station_id="test",
    )
    assert len(rows) == 1
    assert rows[0]["binge_row_minutes"] == 60
    assert rows[0]["runtime_minutes"] == 60


def test_imported_series_with_trt_snaps_binge_row_minutes():
    from binge_schedule.content_catalog import _snap_binge_row_minutes, canonical_rows_from_imported_rows

    assert _snap_binge_row_minutes(24) == 30
    assert _snap_binge_row_minutes(28.5) == 30
    assert _snap_binge_row_minutes(29) == 30
    assert _snap_binge_row_minutes(30) == 60
    assert _snap_binge_row_minutes(38) == 60
    assert _snap_binge_row_minutes(52) == 60
    assert _snap_binge_row_minutes(59) == 60
    assert _snap_binge_row_minutes(60) == 120
    assert _snap_binge_row_minutes(90) == 120

    rows = canonical_rows_from_imported_rows(
        [
            {
                "content_type": "series",
                "display_name": "Laugh-In",
                "series_title": "Laugh-In",
                "episode_number": "01_01",
                "episode_title": "Episode 1",
                "runtime_minutes": 52,
                "source_sheet": "Laugh In ",
            },
            {
                "content_type": "series",
                "display_name": "Laugh-In",
                "series_title": "Laugh-In",
                "episode_number": "01_02",
                "episode_title": "Episode 2",
                "runtime_minutes": 57,
                "source_sheet": "Laugh In ",
            },
        ],
        station_id="test",
    )
    assert rows[0]["runtime_minutes"] == 52
    assert rows[0]["binge_row_minutes"] == 60
    assert rows[1]["binge_row_minutes"] == 60


def test_parse_slot_minutes_cell_accepts_grid_values_only():
    import pandas as pd

    from binge_schedule.content_import import parse_slot_minutes_cell

    assert parse_slot_minutes_cell(30) == 30
    assert parse_slot_minutes_cell("60") == 60
    assert parse_slot_minutes_cell(120) == 120
    assert parse_slot_minutes_cell(90) is None
    assert parse_slot_minutes_cell("") is None
    assert parse_slot_minutes_cell("30:00") == 30
    assert parse_slot_minutes_cell("30:00:00") == 30
    assert parse_slot_minutes_cell("1:00:00") == 60
    assert parse_slot_minutes_cell("2:00:00") == 120
    assert parse_slot_minutes_cell("0:30:00") == 30
    assert parse_slot_minutes_cell(pd.Timedelta(minutes=60)) == 60


def test_imported_series_uses_slot_column_over_trt_inference():
    from binge_schedule.content_catalog import canonical_rows_from_imported_rows

    rows = canonical_rows_from_imported_rows(
        [
            {
                "content_type": "series",
                "display_name": "Hunter",
                "series_title": "Hunter",
                "episode_number": "01_01",
                "episode_title": "Pilot",
                "runtime_minutes": 52,
                "slot_minutes": 60,
                "source_sheet": "Hunter",
            }
        ],
        station_id="test",
    )
    assert rows[0]["runtime_minutes"] == 52
    assert rows[0]["binge_row_minutes"] == 60


def test_imported_paid_programming_slot_30_with_28_30_trt():
    from binge_schedule.content_catalog import canonical_rows_from_imported_rows

    rows = canonical_rows_from_imported_rows(
        [
            {
                "content_type": "paid_programming",
                "display_name": "Perry Stone",
                "series_title": "Perry Stone",
                "episode_title": "This Week",
                "runtime_minutes": 29,
                "slot_minutes": 30,
                "source_sheet": "Perry Stone",
            }
        ],
        station_id="test",
    )
    assert rows[0]["runtime_minutes"] == 29
    assert rows[0]["binge_row_minutes"] == 30


def test_imported_movies_ignore_slot_column():
    from binge_schedule.content_catalog import canonical_rows_from_imported_rows

    rows = canonical_rows_from_imported_rows(
        [
            {
                "content_type": "movie",
                "display_name": "Alpha Movie",
                "episode_title": "Alpha Movie",
                "runtime_minutes": 90,
                "slot_minutes": 60,
                "source_sheet": "MOVIES",
            }
        ],
        station_id="test",
    )
    assert rows[0]["runtime_minutes"] == 90
    assert rows[0]["binge_row_minutes"] == 90


def test_load_desktop_config_without_nikki_workbook():
    from pathlib import Path

    from binge_schedule.config_io import load_build_config

    cfg = load_build_config(Path("config/desktop.yaml"))
    assert cfg.nikki_workbook == ""
    assert cfg.shows == {}


def test_seed_cursors_from_template_continues_after_last_episode():
    from binge_schedule.api import _seed_cursors_from_template

    episodes_by_show = {
        "The Saint": [
            {"id": "saint-1", "code": "01_01", "title": "Pilot"},
            {"id": "saint-2", "code": "01_02", "title": "Part Two"},
            {"id": "saint-3", "code": "01_03", "title": "Part Three"},
        ]
    }
    template_blocks = [
        {"show": "The Saint", "episodeId": "saint-2", "episodeCode": "01_02", "contentType": "Series / show"},
    ]
    cursors = _seed_cursors_from_template(template_blocks, episodes_by_show)
    assert cursors["The Saint"] == 2


def test_rename_and_delete_show_catalog(tmp_path, monkeypatch):
    from pathlib import Path

    from binge_schedule.config_io import load_build_config
    from binge_schedule.content_import import (
        delete_show_catalog,
        load_imported_catalog_rows,
        rename_show_catalog,
        save_imported_catalog_rows,
    )
    from binge_schedule.runtime_paths import imported_catalog_path

    cfg = load_build_config(Path("config/desktop.yaml"))
    catalog_path = imported_catalog_path(cfg.config_path)
    monkeypatch.setattr(
        "binge_schedule.content_import.imported_catalog_path",
        lambda *_args, **_kwargs: tmp_path / "imported_content_catalog.json",
    )
    monkeypatch.setattr(
        "binge_schedule.runtime_paths.imported_catalog_path",
        lambda *_args, **_kwargs: tmp_path / "imported_content_catalog.json",
    )
    monkeypatch.setattr("binge_schedule.content_import.catalog_publish_paths", lambda: [])

    save_imported_catalog_rows(
        cfg,
        [
            {
                "content_type": "series",
                "display_name": "Old Show",
                "series_title": "Old Show",
                "episode_number": "01",
                "episode_title": "Pilot",
                "runtime_minutes": 30,
                "playable": True,
                "source_sheet": "manual",
                "source_file": "test",
            },
            {
                "content_type": "movie",
                "display_name": "Old Movie",
                "episode_title": "Old Movie",
                "runtime_minutes": 90,
                "playable": True,
                "source_sheet": "manual",
                "source_file": "test",
            },
        ],
    )

    renamed = rename_show_catalog(cfg, "Old Show", "New Show")
    assert renamed["renamed_row_count"] == 1
    rows = load_imported_catalog_rows(cfg)
    assert {row["display_name"] for row in rows} == {"New Show", "Old Movie"}

    deleted = delete_show_catalog(cfg, "Old Movie")
    assert deleted["deleted_row_count"] == 1
    rows = load_imported_catalog_rows(cfg)
    assert len(rows) == 1
    assert rows[0]["display_name"] == "New Show"


def test_movie_title_start_offset_formats_report_row():
    from binge_schedule.export_xlsx import blocks_to_binge_dataframe

    blocks = [
        {
            "start": "2026-05-18T16:00:00",
            "end": "2026-05-18T18:00:00",
            "show": "Blue Steel",
            "episodeCode": "MOVIE",
            "episodeTitle": "Blue Steel - (1934)",
            "contentType": "Movie / special",
            "titleStartOffsetMinutes": 5,
        }
    ]
    df = blocks_to_binge_dataframe(blocks)
    assert df.iloc[0]["START TIME"] == "16:05"
    assert str(df.iloc[0]["EPISODE NAME "]).startswith("STARTS AT 4:05 PM")
    assert "Blue Steel - (1934)" in str(df.iloc[0]["EPISODE NAME "])


def test_movie_without_title_start_offset_keeps_block_time():
    from binge_schedule.export_xlsx import blocks_to_binge_dataframe

    blocks = [
        {
            "start": "2026-05-18T16:00:00",
            "end": "2026-05-18T18:00:00",
            "show": "Blue Steel",
            "episodeCode": "MOVIE",
            "episodeTitle": "Blue Steel - (1934)",
            "contentType": "Movie / special",
        }
    ]
    df = blocks_to_binge_dataframe(blocks)
    assert df.iloc[0]["START TIME"] == "16:00"
    assert str(df.iloc[0]["EPISODE NAME "]) == "Blue Steel - (1934)"


def test_desktop_app_version_prefers_version_file(tmp_path, monkeypatch):
    from binge_schedule.runtime_paths import desktop_app_version

    version_file = tmp_path / "VERSION.txt"
    version_file.write_text("9.9.9\n", encoding="utf-8")
    monkeypatch.setenv("DESKTOP_APP_VERSION", "")
    monkeypatch.setattr(
        "binge_schedule.runtime_paths.resource_search_roots",
        lambda: [tmp_path],
    )
    assert desktop_app_version() == "9.9.9"


def test_react_dist_path_prefers_bundled_ui_when_frozen(tmp_path, monkeypatch):
    from binge_schedule.runtime_paths import react_dist_path

    install = tmp_path / "install"
    internal = install / "_internal" / "scheduler-ui" / "dist"
    internal.mkdir(parents=True)
    (internal / "index.html").write_text(
        '<meta name="schedule-builder-version" content="9.9.9" />',
        encoding="utf-8",
    )

    dev_root = tmp_path / "dev"
    dev_dist = dev_root / "scheduler-ui" / "dist"
    dev_dist.mkdir(parents=True)
    (dev_dist / "index.html").write_text("old ui", encoding="utf-8")

    exe = install / "ScheduleBuilder.exe"
    exe.write_text("", encoding="utf-8")

    monkeypatch.setattr("binge_schedule.runtime_paths.is_frozen", lambda: True)
    monkeypatch.setattr("binge_schedule.runtime_paths.executable_dir", lambda: install)
    monkeypatch.chdir(dev_root)
    monkeypatch.delenv("SCHEDULE_BUILDER_REACT_DIST", raising=False)

    assert react_dist_path() == internal


def test_react_dist_bundle_version_reads_index_meta(tmp_path):
    from binge_schedule.runtime_paths import react_dist_bundle_version

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        '<html><head><meta name="schedule-builder-version" content="1.2.3" /></head></html>',
        encoding="utf-8",
    )
    assert react_dist_bundle_version(dist) == "1.2.3"
