from __future__ import annotations

import csv
from pathlib import Path
from zipfile import ZipFile

import pytest
from PIL import Image

from tico_asset_builder.combined import build_tico_folder, validate_combined_output_path


def test_combined_workflow_creates_roms_covers_and_reports(tmp_path: Path) -> None:
    source = tmp_path / "library"
    output = tmp_path / "library-tico-output"
    archive = source / "roms" / "gb" / "Tetris.zip"
    _write_zip(archive, {"Tetris.gb": b"gb-rom"})
    image_dir = source / "roms" / "gb" / "images"
    image_dir.mkdir(parents=True)
    Image.new("RGB", (320, 240), (30, 60, 120)).save(image_dir / "Tetris.png")
    before = _snapshot(source)

    result = build_tico_folder(source, output, style="fit")

    assert len(result.prep.prepared) == 1
    assert result.assets is not None
    assert (output / "tico" / "roms" / "gb" / "Tetris.gb").read_bytes() == b"gb-rom"
    assert not (output / "tico" / "roms" / "gb" / "images").exists()
    cover_path = output / "tico" / "assets" / "covers" / "gb" / "Tetris.jpg"
    assert cover_path.exists()
    with Image.open(cover_path) as cover:
        cover.verify()
    with Image.open(cover_path) as cover:
        assert cover.format == "JPEG"
        assert cover.size == (512, 512)
    assert _snapshot(source) == before
    assert archive.exists()
    assert _read_csv(output / "tico" / "reports" / "prepared-roms.csv")
    assert _read_csv(output / "reports" / "detected-games.csv")
    assert _read_csv(output / "reports" / "matched-covers.csv")


def test_combined_workflow_rejects_non_empty_output_without_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "library"
    output = tmp_path / "library-tico-output"
    _write_zip(source / "roms" / "gb" / "Tetris.zip", {"Tetris.gb": b"gb-rom"})
    output.mkdir()
    (output / "keep.txt").write_text("existing", encoding="utf-8")

    with pytest.raises(ValueError, match="Final output folder already exists"):
        build_tico_folder(source, output, style="fit")


def test_combined_workflow_copies_already_extracted_roms(tmp_path: Path) -> None:
    source = tmp_path / "library"
    output = tmp_path / "library-tico-output"
    rom_dir = source / "roms" / "gb"
    image_dir = rom_dir / "images"
    image_dir.mkdir(parents=True)
    (rom_dir / "Tetris.gb").write_bytes(b"gb-rom")
    Image.new("RGB", (320, 240), (30, 60, 120)).save(image_dir / "Tetris.png")

    result = build_tico_folder(source, output, style="fit")

    assert len(result.prep.prepared) == 1
    assert (output / "tico" / "roms" / "gb" / "Tetris.gb").read_bytes() == b"gb-rom"
    assert not (output / "tico" / "roms" / "gb" / "images").exists()
    with Image.open(output / "tico" / "assets" / "covers" / "gb" / "Tetris.jpg") as cover:
        assert cover.format == "JPEG"
        assert cover.size == (512, 512)


def test_combined_output_safety_checks() -> None:
    assert (
        validate_combined_output_path(Path("/tmp/source"), Path("/tmp/source"))
        == "Choose a final Tico output folder that is separate from the source library."
    )
    assert (
        validate_combined_output_path(Path("/tmp/source"), Path("/tmp/source/roms/output"))
        == "Choose a final Tico output folder outside the source library's roms folder."
    )
    assert validate_combined_output_path(Path("/tmp/source"), Path("/tmp/source-tico-output")) is None


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
