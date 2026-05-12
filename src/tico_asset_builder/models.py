from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConsoleConfig:
    key: str
    extensions: frozenset[str]
    disc_system: bool = False


@dataclass(frozen=True)
class Game:
    console: str
    path: Path
    stem: str


@dataclass(frozen=True)
class CoverCandidate:
    path: Path
    normalized_stem: str


@dataclass(frozen=True)
class CoverMatch:
    game: Game
    cover_path: Path
    score: float
    method: str
    output_path: Path


@dataclass(frozen=True)
class MissingCover:
    game: Game
    reason: str


@dataclass(frozen=True)
class SkippedFile:
    path: Path
    console: str | None
    reason: str

