"""Match detected ROMs to local artwork with conservative fuzzy matching."""

from __future__ import annotations

import re
from pathlib import Path

from rapidfuzz import fuzz, process

from .models import CoverCandidate, CoverMatch, Game, MissingCover
from .names import normalized_name, strip_compound_suffix

NUMBER_TOKEN = re.compile(r"\b\d+\b")


def match_covers(
    games: list[Game],
    candidates_by_console: dict[str, list[CoverCandidate]],
    output_root: Path,
    threshold: int,
) -> tuple[list[CoverMatch], list[MissingCover]]:
    """Match covers by exact, normalized, then high-confidence fuzzy name."""
    matches: list[CoverMatch] = []
    missing: list[MissingCover] = []

    for game in games:
        candidates = candidates_by_console.get(game.console, [])
        output_path = output_root / "tico" / "assets" / "covers" / game.console / f"{game.stem}.jpg"
        game_name = normalized_name(game.stem)
        exact = next((candidate for candidate in candidates if _candidate_stem(candidate) == game.stem), None)

        if exact:
            matches.append(CoverMatch(game, exact.path, 100.0, "exact", output_path))
            continue

        normalized = next((candidate for candidate in candidates if candidate.normalized_stem == game_name), None)

        if normalized:
            matches.append(CoverMatch(game, normalized.path, 100.0, "normalized", output_path))
            continue

        choices = {candidate.normalized_stem: candidate for candidate in candidates}
        result = process.extractOne(game_name, choices.keys(), scorer=fuzz.WRatio)
        if result and result[1] >= threshold:
            matched_name, score, _ = result
            # Prevent a common bad match: nearby numbered games borrowing each
            # other's covers, such as Game 01 matching Game 02.
            if _number_tokens(game_name) != _number_tokens(matched_name):
                missing.append(MissingCover(game, "no local cover match"))
                continue
            matches.append(CoverMatch(game, choices[matched_name].path, float(score), "fuzzy", output_path))
            continue

        missing.append(MissingCover(game, "no local cover match"))

    return matches, missing


def _candidate_stem(candidate: CoverCandidate) -> str:
    return strip_compound_suffix(candidate.path.name)


def _number_tokens(value: str) -> tuple[str, ...]:
    return tuple(NUMBER_TOKEN.findall(value))
