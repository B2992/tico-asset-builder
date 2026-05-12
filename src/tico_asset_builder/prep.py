"""Prepare ROM-only output folders without touching source libraries.

The prep step intentionally extracts or copies ROM files only. Source artwork
stays in the original library so prepared ROM folders do not look like final
cover output folders.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from shutil import copy2
from zipfile import BadZipFile, ZipFile

from .config import CONSOLES, IMAGE_EXTENSIONS
from .system_aliases import resolve_console_folder_name

@dataclass(frozen=True)
class PreparedRom:
    console: str
    source_archive: Path
    output_rom: Path


@dataclass(frozen=True)
class SkippedArchiveItem:
    console: str
    source_archive: Path
    member: str
    reason: str


@dataclass(frozen=True)
class PrepResult:
    prepared: list[PreparedRom]
    skipped: list[SkippedArchiveItem]
    cancelled: bool = False


def prepare_roms(
    input_folder: Path,
    output_folder: Path,
    overwrite: bool = False,
    dry_run: bool = False,
    consoles: list[str] | None = None,
    include_extracted: bool = False,
    progress_callback=None,
    cancel_check=None,
) -> PrepResult:
    """Create a ROM-only prepared copy from a source library.

    All writes are constrained to ``output_folder``. The input folder is scanned
    as read-only, and dry runs avoid creating the output folder entirely.
    """
    if not dry_run and output_folder.exists() and any(output_folder.iterdir()) and not overwrite:
        raise ValueError("Output folder already exists and is not empty. Use --overwrite to allow writing there.")

    prepared: list[PreparedRom] = []
    skipped: list[SkippedArchiveItem] = []
    cancelled = False
    rom_root = _detect_rom_root(input_folder)
    selected_consoles = set(consoles or [])
    archives_by_console = _zip_archives_by_console(rom_root, selected_consoles)
    total_archives = sum(len(paths) for paths in archives_by_console.values())
    processed_archives = 0

    for console, archive_paths in archives_by_console.items():
        console_dir = rom_root / console
        output_console_dir = output_folder / "roms" / console
        if not dry_run:
            output_console_dir.mkdir(parents=True, exist_ok=True)

        for archive_path in archive_paths:
            if cancel_check and cancel_check():
                cancelled = True
                break
            try:
                with ZipFile(archive_path) as archive:
                    prepared.extend(
                        _extract_rom_members(
                            archive=archive,
                            archive_path=archive_path,
                            console=console,
                            output_console_dir=output_console_dir,
                            overwrite=overwrite,
                            dry_run=dry_run,
                            skipped=skipped,
                            cancel_check=cancel_check,
                        )
                    )
            except BadZipFile:
                skipped.append(SkippedArchiveItem(console, archive_path, "", "invalid zip archive"))
            processed_archives += 1
            if progress_callback:
                progress_callback(processed_archives, total_archives, f"Preparing ROMs: {processed_archives} / {total_archives}")
            if cancel_check and cancel_check():
                cancelled = True
                break
        if cancelled:
            break

    if include_extracted and not cancelled:
        for console, console_dir in _console_dirs(rom_root).items():
            if selected_consoles and console not in selected_consoles:
                continue
            output_console_dir = output_folder / "roms" / console
            if not dry_run:
                output_console_dir.mkdir(parents=True, exist_ok=True)
            for rom_path in _extracted_rom_paths(console, console_dir):
                if cancel_check and cancel_check():
                    cancelled = True
                    break
                output_rom = output_console_dir / rom_path.name
                if not dry_run and output_rom.exists() and not overwrite:
                    skipped.append(SkippedArchiveItem(console, rom_path, rom_path.name, "output ROM already exists"))
                    continue
                if not dry_run:
                    copy2(rom_path, output_rom)
                prepared.append(PreparedRom(console, rom_path, output_rom))
            if cancelled:
                break

    if not dry_run:
        _write_prep_reports(output_folder, prepared, skipped)
    return PrepResult(prepared=prepared, skipped=skipped, cancelled=cancelled)


def _detect_rom_root(input_folder: Path) -> Path:
    roms = input_folder / "roms"
    if roms.is_dir():
        return roms
    return input_folder


def _console_dirs(rom_root: Path) -> dict[str, Path]:
    dirs: dict[str, Path] = {}
    for child in sorted(rom_root.iterdir()) if rom_root.is_dir() else []:
        if not child.is_dir() or child.name.startswith("."):
            continue
        match = resolve_console_folder_name(child.name)
        if match and match.console not in dirs:
            dirs[match.console] = child
    return dirs


def _zip_archives_by_console(rom_root: Path, selected_consoles: set[str]) -> dict[str, list[Path]]:
    archives: dict[str, list[Path]] = {}
    for console, console_dir in _console_dirs(rom_root).items():
        if selected_consoles and console not in selected_consoles:
            continue
        archives[console] = sorted(path for path in console_dir.glob("*.zip") if path.is_file())
    return archives


def _extracted_rom_paths(console: str, console_dir: Path) -> list[Path]:
    allowed_extensions = CONSOLES[console].extensions
    return sorted(
        path
        for path in console_dir.iterdir()
        if path.is_file() and not path.name.startswith(".") and _effective_suffix(path) in allowed_extensions
    )


def _extract_rom_members(
    archive: ZipFile,
    archive_path: Path,
    console: str,
    output_console_dir: Path,
    overwrite: bool,
    dry_run: bool,
    skipped: list[SkippedArchiveItem],
    cancel_check=None,
) -> list[PreparedRom]:
    """Extract only ROM-like zip members and report every skipped item."""
    prepared: list[PreparedRom] = []
    allowed_extensions = CONSOLES[console].extensions

    for member in archive.infolist():
        if cancel_check and cancel_check():
            break
        if member.is_dir():
            continue

        member_path = Path(member.filename)
        filename = member_path.name
        reason = _skip_reason(member_path, allowed_extensions)
        if reason:
            skipped.append(SkippedArchiveItem(console, archive_path, member.filename, reason))
            continue

        output_rom = output_console_dir / filename
        if not dry_run and output_rom.exists() and not overwrite:
            skipped.append(SkippedArchiveItem(console, archive_path, member.filename, "output ROM already exists"))
            continue

        if not dry_run:
            with archive.open(member) as source, output_rom.open("wb") as destination:
                destination.write(source.read())
        prepared.append(PreparedRom(console, archive_path, output_rom))

    return prepared


def _skip_reason(member_path: Path, allowed_extensions: frozenset[str]) -> str | None:
    filename = member_path.name
    lowered_parts = {part.lower() for part in member_path.parts}
    if "__macosx" in lowered_parts:
        return "macOS metadata"
    if "images" in lowered_parts:
        return "image folder inside archive"
    if filename.startswith(".") or filename == ".DS_Store":
        return "hidden or metadata file"
    if member_path.suffix.lower() in IMAGE_EXTENSIONS:
        return "image file inside archive"
    if _effective_suffix(member_path) not in allowed_extensions:
        return "unsupported file inside archive"
    return None


def _effective_suffix(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".nkit.iso"):
        return ".nkit.iso"
    return path.suffix.lower()


def _write_prep_reports(output_folder: Path, prepared: list[PreparedRom], skipped: list[SkippedArchiveItem]) -> None:
    reports_dir = output_folder / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    with (reports_dir / "prepared-roms.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["console", "source_archive_path", "output_rom_path"])
        writer.writerows((item.console, str(item.source_archive), str(item.output_rom)) for item in prepared)

    with (reports_dir / "skipped-archives.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["console", "source_archive_path", "archive_member", "reason"])
        writer.writerows((item.console, str(item.source_archive), item.member, item.reason) for item in skipped)
