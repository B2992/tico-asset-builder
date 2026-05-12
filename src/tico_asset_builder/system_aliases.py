"""Resolve common input folder names to canonical Tico console slugs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from .config import CONSOLES

GENERIC_WORDS = frozenset({"roms", "rom", "games", "library", "no", "intro", "redump"})
SHORT_ALIAS_NAMES = frozenset({"gb", "gg", "dc", "md", "fc", "gc", "sms"})
FUZZY_THRESHOLD = 94
AMBIGUITY_GAP = 4

CONSOLE_ALIASES: dict[str, tuple[str, ...]] = {
    "gb": ("gb", "gameboy", "game boy", "nintendo game boy", "dmg"),
    "gbc": ("gbc", "gameboy color", "game boy color", "nintendo game boy color"),
    "gba": ("gba", "gameboy advance", "game boy advance", "nintendo game boy advance"),
    "nes": ("nes", "nintendo entertainment system", "famicom", "fc"),
    "snes": ("snes", "super nintendo", "super nintendo entertainment system", "super famicom", "sfc"),
    "genesis": ("genesis", "sega genesis", "mega drive", "megadrive", "md", "sega md"),
    "master-system": ("master-system", "master system", "sega master system", "sms"),
    "game-gear": ("game-gear", "game gear", "sega game gear", "gg"),
    "sega-cd": ("sega-cd", "sega cd", "mega cd", "megacd"),
    "saturn": ("saturn", "sega saturn"),
    "dc": ("dc", "dreamcast", "sega dreamcast"),
    "psx": ("psx", "ps1", "playstation", "playstation 1", "sony playstation"),
    "psp": ("psp", "playstation portable", "sony psp"),
    "gc": ("gc", "gcn", "gamecube", "game cube", "nintendo gamecube"),
    "wii": ("wii", "nintendo wii"),
}


@dataclass(frozen=True)
class ConsoleFolderMatch:
    console: str
    folder_name: str
    method: str


def normalize_console_folder_name(name: str) -> str:
    """Normalize real-world folder names before alias matching."""
    value = name.lower().strip()
    value = re.sub(r"[\[\](){}]", " ", value)
    value = re.sub(r"[_./\\-]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    words = [word for word in value.split() if word not in GENERIC_WORDS]
    return " ".join(words)


def resolve_console_folder_name(name: str) -> ConsoleFolderMatch | None:
    """Resolve one folder name to a canonical console slug, if safe."""
    normalized = normalize_console_folder_name(name)
    if not normalized:
        return None

    exact = _exact_aliases()
    if normalized in exact:
        return ConsoleFolderMatch(exact[normalized], name, "alias")
    if normalized in CONSOLES:
        return ConsoleFolderMatch(normalized, name, "canonical")
    if normalized in SHORT_ALIAS_NAMES or len(normalized) <= 3:
        return None

    choices = list(exact)
    matches = process.extract(normalized, choices, scorer=fuzz.WRatio, limit=2)
    if not matches:
        return None
    best_name, best_score, _ = matches[0]
    if best_score < FUZZY_THRESHOLD:
        return None
    if len(matches) > 1 and best_score - matches[1][1] < AMBIGUITY_GAP:
        return None
    return ConsoleFolderMatch(exact[best_name], name, "fuzzy")


def _exact_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for console, names in CONSOLE_ALIASES.items():
        for name in names:
            aliases[normalize_console_folder_name(name)] = console
    return aliases
