"""CSV report writers for reviewing local prep and cover-building results."""

from __future__ import annotations

import csv
from pathlib import Path

from .models import CoverMatch, Game, MissingCover, SkippedFile


def write_reports(
    output_root: Path,
    games: list[Game],
    matches: list[CoverMatch],
    missing: list[MissingCover],
    skipped: list[SkippedFile],
) -> None:
    """Write asset-builder reports into ``output_root/reports``."""
    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(
        reports_dir / "detected-games.csv",
        ["console", "rom_stem", "rom_path"],
        ((game.console, game.stem, str(game.path)) for game in games),
    )
    _write_csv(
        reports_dir / "matched-covers.csv",
        ["console", "rom_stem", "rom_path", "cover_path", "score", "method", "output_path"],
        (
            (
                match.game.console,
                match.game.stem,
                str(match.game.path),
                str(match.cover_path),
                f"{match.score:.1f}",
                match.method,
                str(match.output_path),
            )
            for match in matches
        ),
    )
    _write_csv(
        reports_dir / "missing-covers.csv",
        ["console", "rom_stem", "rom_path", "reason"],
        ((item.game.console, item.game.stem, str(item.game.path), item.reason) for item in missing),
    )
    _write_csv(
        reports_dir / "skipped-files.csv",
        ["console", "path", "reason"],
        ((item.console or "", str(item.path), item.reason) for item in skipped),
    )


def _write_csv(path: Path, headers: list[str], rows: object) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
