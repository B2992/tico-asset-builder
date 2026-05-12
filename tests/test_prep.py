from __future__ import annotations

import csv
from pathlib import Path
from zipfile import ZipFile

import pytest

from tico_asset_builder.prep import prepare_roms


def test_extracts_valid_gb_zip(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "prepared"
    archive = library / "roms" / "gb" / "Tetris.zip"
    _write_zip(archive, {"Tetris.gb": b"gb-rom"})

    result = prepare_roms(library, output)

    assert (output / "roms" / "gb" / "Tetris.gb").read_bytes() == b"gb-rom"
    assert len(result.prepared) == 1


def test_extracts_valid_gba_zip(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "prepared"
    _write_zip(library / "roms" / "gba" / "Advance Wars.zip", {"Advance Wars.gba": b"gba-rom"})

    prepare_roms(library, output)

    assert (output / "roms" / "gba" / "Advance Wars.gba").read_bytes() == b"gba-rom"


def test_extracts_valid_snes_zip(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "prepared"
    _write_zip(library / "roms" / "snes" / "ActRaiser.zip", {"ActRaiser.sfc": b"snes-rom"})

    prepare_roms(library, output)

    assert (output / "roms" / "snes" / "ActRaiser.sfc").read_bytes() == b"snes-rom"


def test_ignores_junk_inside_zip(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "prepared"
    _write_zip(
        library / "roms" / "gb" / "Tetris.zip",
        {
            "Tetris.gb": b"gb-rom",
            ".DS_Store": b"metadata",
            "__MACOSX/Tetris.gb": b"metadata",
            "readme.txt": b"notes",
            "images/Tetris.png": b"image",
            "Tetris.png": b"image",
        },
    )

    result = prepare_roms(library, output)

    assert (output / "roms" / "gb" / "Tetris.gb").exists()
    assert sorted(path.name for path in (output / "roms" / "gb").iterdir()) == ["Tetris.gb"]
    assert len(result.skipped) == 5


def test_does_not_copy_images_folder(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "prepared"
    _write_zip(library / "roms" / "gb" / "Tetris.zip", {"Tetris.gb": b"gb-rom"})
    images_dir = library / "roms" / "gb" / "images"
    images_dir.mkdir(parents=True)
    (images_dir / "Tetris.png").write_bytes(b"image")

    prepare_roms(library, output)

    assert (output / "roms" / "gb" / "Tetris.gb").exists()
    assert not (output / "roms" / "gb" / "images").exists()


def test_refuses_non_empty_output_without_overwrite(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "prepared"
    _write_zip(library / "roms" / "gb" / "Tetris.zip", {"Tetris.gb": b"gb-rom"})
    output.mkdir()
    (output / "existing.txt").write_text("already here")

    with pytest.raises(ValueError, match="Output folder already exists"):
        prepare_roms(library, output)


def test_input_folder_is_not_modified_and_original_zip_remains(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "prepared"
    archive = library / "roms" / "gb" / "Tetris.zip"
    _write_zip(archive, {"Tetris.gb": b"gb-rom"})
    before = _snapshot(library)

    prepare_roms(library, output)

    assert _snapshot(library) == before
    assert archive.exists()


def test_writes_prep_reports(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "prepared"
    archive = library / "roms" / "gb" / "Tetris.zip"
    _write_zip(archive, {"Tetris.gb": b"gb-rom", "notes.txt": b"junk"})

    prepare_roms(library, output)

    prepared_rows = _read_csv(output / "reports" / "prepared-roms.csv")
    skipped_rows = _read_csv(output / "reports" / "skipped-archives.csv")
    assert prepared_rows[0]["console"] == "gb"
    assert prepared_rows[0]["source_archive_path"] == str(archive)
    assert prepared_rows[0]["output_rom_path"] == str(output / "roms" / "gb" / "Tetris.gb")
    assert skipped_rows[0]["reason"] == "unsupported file inside archive"


def test_dry_run_does_not_create_extracted_roms_or_output_folder(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "prepared"
    _write_zip(library / "roms" / "gb" / "Tetris.zip", {"Tetris.gb": b"gb-rom"})

    result = prepare_roms(library, output, dry_run=True)

    assert len(result.prepared) == 1
    assert result.prepared[0].output_rom == output / "roms" / "gb" / "Tetris.gb"
    assert not output.exists()


def test_console_filter_only_processes_selected_console(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "prepared"
    _write_zip(library / "roms" / "gb" / "Tetris.zip", {"Tetris.gb": b"gb-rom"})
    _write_zip(library / "roms" / "gba" / "Advance Wars.zip", {"Advance Wars.gba": b"gba-rom"})

    result = prepare_roms(library, output, consoles=["gb"])

    assert [item.console for item in result.prepared] == ["gb"]
    assert (output / "roms" / "gb" / "Tetris.gb").exists()
    assert not (output / "roms" / "gba").exists()


def test_repeated_console_filter_processes_selected_consoles(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "prepared"
    _write_zip(library / "roms" / "gb" / "Tetris.zip", {"Tetris.gb": b"gb-rom"})
    _write_zip(library / "roms" / "gba" / "Advance Wars.zip", {"Advance Wars.gba": b"gba-rom"})
    _write_zip(library / "roms" / "snes" / "ActRaiser.zip", {"ActRaiser.sfc": b"snes-rom"})

    result = prepare_roms(library, output, consoles=["gb", "gba"])

    assert [item.console for item in result.prepared] == ["gb", "gba"]
    assert (output / "roms" / "gb" / "Tetris.gb").exists()
    assert (output / "roms" / "gba" / "Advance Wars.gba").exists()
    assert not (output / "roms" / "snes").exists()


def test_dry_run_leaves_original_zip_untouched(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "prepared"
    archive = library / "roms" / "gb" / "Tetris.zip"
    _write_zip(archive, {"Tetris.gb": b"gb-rom"})
    before = _snapshot(library)

    prepare_roms(library, output, dry_run=True)

    assert _snapshot(library) == before
    assert archive.exists()


def test_prepare_roms_calls_progress_callback(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "prepared"
    _write_zip(library / "roms" / "gb" / "Tetris.zip", {"Tetris.gb": b"gb-rom"})
    progress: list[tuple[int, int, str]] = []

    prepare_roms(library, output, progress_callback=lambda current, total, message: progress.append((current, total, message)))

    assert progress == [(1, 1, "Preparing ROMs: 1 / 1")]


def test_prepare_roms_cancel_stops_before_all_archives(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "prepared"
    _write_zip(library / "roms" / "gb" / "A.zip", {"A.gb": b"a"})
    _write_zip(library / "roms" / "gb" / "B.zip", {"B.gb": b"b"})
    should_cancel = False

    def progress_callback(current: int, total: int, message: str) -> None:
        nonlocal should_cancel
        should_cancel = True

    result = prepare_roms(
        library,
        output,
        progress_callback=progress_callback,
        cancel_check=lambda: should_cancel,
    )

    assert result.cancelled
    assert len(result.prepared) == 1
    assert (output / "roms" / "gb" / "A.gb").exists()
    assert not (output / "roms" / "gb" / "B.gb").exists()


def _write_zip(path: Path, members: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def _snapshot(path: Path) -> dict[str, bytes]:
    return {str(item.relative_to(path)): item.read_bytes() for item in sorted(path.rglob("*")) if item.is_file()}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
