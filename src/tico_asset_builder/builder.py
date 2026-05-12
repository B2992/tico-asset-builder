from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .images import convert_cover
from .matcher import match_covers
from .models import CoverMatch, Game, MissingCover, SkippedFile
from .reports import write_reports
from .scanner import scan_cover_candidates, scan_games


@dataclass(frozen=True)
class BuildResult:
    games: list[Game]
    matches: list[CoverMatch]
    missing: list[MissingCover]
    skipped: list[SkippedFile]


def build_assets(input_path: Path, output_root: Path, style: str, threshold: int, dry_run: bool = False) -> BuildResult:
    games, skipped = scan_games(input_path)
    candidates = scan_cover_candidates(input_path)
    matches, missing = match_covers(games, candidates, output_root, threshold)

    if not dry_run:
        for match in matches:
            convert_cover(match.cover_path, match.output_path, style)

    write_reports(output_root, games, matches, missing, skipped)
    return BuildResult(games=games, matches=matches, missing=missing, skipped=skipped)

