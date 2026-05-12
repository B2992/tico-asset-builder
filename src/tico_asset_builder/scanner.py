"""Local scanners for ROM files, skipped files, and artwork candidates."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .config import ARCHIVE_EXTENSIONS, CONSOLES, DISC_PRIMARY_EXTENSIONS, IMAGE_EXTENSIONS, IMAGE_FOLDER_NAMES
from .models import ConsoleConfig, CoverCandidate, Game, SkippedFile
from .names import normalized_stem, strip_compound_suffix
from .system_aliases import resolve_console_folder_name


def detect_rom_root(input_path: Path) -> Path:
    roms = input_path / "roms"
    if roms.is_dir():
        return roms
    return input_path


def find_console_dirs(input_path: Path) -> dict[str, Path]:
    rom_root = detect_rom_root(input_path)
    dirs: dict[str, Path] = {}
    for child in sorted(rom_root.iterdir()) if rom_root.is_dir() else []:
        if not child.is_dir() or child.name.startswith(".") or child.name.lower() in IMAGE_FOLDER_NAMES:
            continue
        match = resolve_console_folder_name(child.name)
        if match and match.console not in dirs:
            dirs[match.console] = child
    return dirs


def scan_games(input_path: Path) -> tuple[list[Game], list[SkippedFile]]:
    """Detect supported ROM files while reporting unsupported local files."""
    games: list[Game] = []
    skipped: list[SkippedFile] = []

    for console, console_dir in find_console_dirs(input_path).items():
        config = CONSOLES[console]
        primary_disc_stems = _primary_disc_stems(console_dir) if config.disc_system else set()

        for file_path in sorted(_iter_files(console_dir)):
            if _is_inside_image_folder(file_path):
                continue

            ext = _effective_suffix(file_path)
            if ext in ARCHIVE_EXTENSIONS:
                skipped.append(SkippedFile(file_path, console, "compressed archive"))
                continue

            if ext not in config.extensions:
                skipped.append(SkippedFile(file_path, console, "unsupported extension"))
                continue

            if _is_secondary_disc_track(file_path, config, primary_disc_stems):
                skipped.append(SkippedFile(file_path, console, "secondary disc track"))
                continue

            games.append(Game(console=console, path=file_path, stem=strip_compound_suffix(file_path.name)))

    return games, skipped


def scan_cover_candidates(input_path: Path) -> dict[str, list[CoverCandidate]]:
    """Find local artwork near console folders and common image roots."""
    rom_root = detect_rom_root(input_path)
    candidates: dict[str, list[CoverCandidate]] = {console: [] for console in CONSOLES}

    for console, console_dir in find_console_dirs(input_path).items():
        search_roots = [console_dir]
        search_roots.extend(_likely_image_dirs_near(console_dir))
        search_roots.extend(_console_image_dirs(rom_root, input_path, console))

        seen: set[Path] = set()
        for root in search_roots:
            for image_path in sorted(_iter_files(root)):
                if image_path in seen:
                    continue
                seen.add(image_path)
                if image_path.suffix.lower() in IMAGE_EXTENSIONS:
                    candidates[console].append(CoverCandidate(image_path, normalized_stem(image_path)))

    return candidates


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (path for path in root.rglob("*") if path.is_file())


def _likely_image_dirs_near(console_dir: Path) -> list[Path]:
    roots: list[Path] = []
    for folder in IMAGE_FOLDER_NAMES:
        candidate = console_dir / folder
        if candidate.is_dir():
            roots.append(candidate)
    return roots


def _console_image_dirs(rom_root: Path, input_path: Path, console: str) -> list[Path]:
    roots: list[Path] = []
    possible_parents = [rom_root, input_path]
    if rom_root.name == "roms":
        possible_parents.append(rom_root.parent)

    for parent in possible_parents:
        for image_folder in IMAGE_FOLDER_NAMES:
            candidate = parent / image_folder / console
            if candidate.is_dir() and candidate not in roots:
                roots.append(candidate)
    return roots


def _is_inside_image_folder(path: Path) -> bool:
    return any(part.lower() in IMAGE_FOLDER_NAMES for part in path.parts)


def _effective_suffix(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".nkit.iso"):
        return ".nkit.iso"
    return path.suffix.lower()


def _primary_disc_stems(console_dir: Path) -> set[str]:
    return {
        normalized_stem(path)
        for path in _iter_files(console_dir)
        if _effective_suffix(path) in DISC_PRIMARY_EXTENSIONS
    }


def _is_secondary_disc_track(path: Path, config: ConsoleConfig, primary_disc_stems: set[str]) -> bool:
    if not config.disc_system or path.suffix.lower() != ".bin":
        return False
    bin_stem = normalized_stem(path)
    return any(
        bin_stem == primary_stem
        or bin_stem.startswith(f"{primary_stem} ")
        or primary_stem.startswith(f"{bin_stem} ")
        for primary_stem in primary_disc_stems
    )
