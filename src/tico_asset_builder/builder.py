"""Build resized Tico cover assets from ROMs and local artwork.

The builder detects games from the main input folder, optionally searches extra
artwork source folders, and writes only cover assets plus reports to the output
root. It does not prepare ROMs or alter source folders.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .images import convert_cover
from .matcher import match_covers
from .models import CoverCandidate, CoverMatch, Game, MissingCover, SkippedFile
from .reports import write_reports
from .scanner import scan_cover_candidates, scan_games


@dataclass(frozen=True)
class BuildResult:
    games: list[Game]
    matches: list[CoverMatch]
    missing: list[MissingCover]
    skipped: list[SkippedFile]
    cancelled: bool = False


def build_assets(
    input_path: Path,
    output_root: Path,
    style: str,
    threshold: int,
    dry_run: bool = False,
    artwork_sources: list[Path] | None = None,
    progress_callback=None,
    cancel_check=None,
) -> BuildResult:
    """Scan games, match local artwork, convert covers, and write reports."""
    games, skipped = scan_games(input_path)
    candidates = scan_cover_candidates(input_path)
    for artwork_source in artwork_sources or []:
        _merge_candidates(candidates, scan_cover_candidates(artwork_source))
    matches, missing = match_covers(games, candidates, output_root, threshold)
    cancelled = False

    if not dry_run:
        total = len(matches)
        for index, match in enumerate(matches, start=1):
            if cancel_check and cancel_check():
                cancelled = True
                break
            convert_cover(match.cover_path, match.output_path, style)
            if progress_callback:
                progress_callback(index, total, f"Building covers: {index} / {total}")
        if cancelled:
            matches = matches[: max(index - 1, 0)]

    write_reports(output_root, games, matches, missing, skipped)
    return BuildResult(games=games, matches=matches, missing=missing, skipped=skipped, cancelled=cancelled)


def _merge_candidates(
    target: dict[str, list[CoverCandidate]],
    source: dict[str, list[CoverCandidate]],
) -> None:
    """Merge optional artwork-source candidates without duplicating paths."""
    for console, candidates in source.items():
        seen = {candidate.path for candidate in target.setdefault(console, [])}
        for candidate in candidates:
            if candidate.path not in seen:
                target[console].append(candidate)
                seen.add(candidate.path)
