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
) -> None:
    """Generate BINGE.xlsx and BINGE GRIDS.xlsx from Nikki data and weekly grids."""
    cfg = load_build_config(config)
    binge, grids, warnings = export_both(cfg, out_dir)
    typer.echo(f"Wrote {binge}")
    typer.echo(f"Wrote {grids}")
    for w in warnings:
        typer.echo(f"Warning: {w}", err=True)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
