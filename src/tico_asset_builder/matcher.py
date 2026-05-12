from __future__ import annotations

from pathlib import Path

from rapidfuzz import fuzz, process

from .models import CoverCandidate, CoverMatch, Game, MissingCover
from .names import normalized_name


def match_covers(
    games: list[Game],
    candidates_by_console: dict[str, list[CoverCandidate]],
    output_root: Path,
    threshold: int,
) -> tuple[list[CoverMatch], list[MissingCover]]:
    matches: list[CoverMatch] = []
    missing: list[MissingCover] = []

    for game in games:
        candidates = candidates_by_console.get(game.console, [])
        output_path = output_root / "tico" / "assets" / "covers" / game.console / f"{game.stem}.jpg"
        game_name = normalized_name(game.stem)
        exact = next((candidate for candidate in candidates if candidate.normalized_stem == game_name), None)

        if exact:
            matches.append(CoverMatch(game, exact.path, 100.0, "exact", output_path))
            continue

        choices = {candidate.normalized_stem: candidate for candidate in candidates}
        result = process.extractOne(game_name, choices.keys(), scorer=fuzz.WRatio)
        if result and result[1] >= threshold:
            matched_name, score, _ = result
            matches.append(CoverMatch(game, choices[matched_name].path, float(score), "fuzzy", output_path))
            continue

        missing.append(MissingCover(game, "no local cover match"))

    return matches, missing

