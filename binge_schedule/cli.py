from __future__ import annotations

from pathlib import Path

import typer

from binge_schedule.config_io import load_build_config
from binge_schedule.export_xlsx import export_both

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def build(
    config: Path = typer.Option(
        Path("config/april_2026.yaml"),
        "--config",
        "-c",
        exists=True,
        dir_okay=False,
        readable=True,
        help="YAML build config (see config/april_2026.yaml)",
    ),
    out_dir: Path = typer.Option(
        Path("out"),
        "--out-dir",
        "-o",
        help="Directory for BINGE.xlsx and BINGE GRIDS.xlsx",
    ),
    week: list[str] = typer.Option(
        (),
        "--week",
        help="Monday YYYY-MM-DD; limit export to these weeks (repeatable). Default: all weeks in config.",
    ),
) -> None:
    """Generate BINGE.xlsx and BINGE GRIDS.xlsx from the content workbook and weekly grids."""
    cfg = load_build_config(config)
    weeks_filter = None
    if week:
        want = {w.strip() for w in week if w and w.strip()}
        weeks_filter = [w for w in cfg.weeks if w.monday in want]
        missing = want - {w.monday for w in weeks_filter}
        if missing:
            typer.echo(f"Unknown week monday(s) not in config: {sorted(missing)}", err=True)
            raise typer.Exit(code=1)
    binge, grids, warnings, seeded = export_both(cfg, out_dir, weeks=weeks_filter)
    typer.echo(f"Wrote {binge}")
    typer.echo(f"Wrote {grids}")
    for s in seeded:
        if s.startswith("Copied") or any(
            x in s.lower()
            for x in ("could not", "cannot load", "missing", "skipping", "no program", "no ``weeks")
        ):
            typer.echo(s)
    for w in warnings:
        typer.echo(f"Warning: {w}", err=True)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
