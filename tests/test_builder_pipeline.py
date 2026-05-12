from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image

from tico_asset_builder.builder import build_assets


def test_builder_pipeline_creates_cover_and_reports(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "output"
    gb_roms = library / "roms" / "gb"
    snes_roms = library / "roms" / "snes"
    gb_images = library / "images" / "gb"
    gb_roms.mkdir(parents=True)
    snes_roms.mkdir(parents=True)
    gb_images.mkdir(parents=True)

    (gb_roms / "Tetris (World).gb").write_bytes(b"")
    (gb_roms / "Pokemon Red Version (USA).gb").write_bytes(b"")
    (snes_roms / "Super Mario World (USA).sfc").write_bytes(b"")
    Image.new("RGB", (320, 240), (30, 60, 120)).save(gb_images / "Tetris (World).png")

    build_assets(input_path=library, output_root=output, style="fit", threshold=88)

    cover_path = output / "tico" / "assets" / "covers" / "gb" / "Tetris (World).jpg"
    assert cover_path.exists()
    with Image.open(cover_path) as cover:
        cover.verify()
    with Image.open(cover_path) as cover:
        assert cover.format == "JPEG"
        assert cover.size == (512, 512)

    matched_rows = _read_csv(output / "reports" / "matched-covers.csv")
    missing_rows = _read_csv(output / "reports" / "missing-covers.csv")

    assert any(row["rom_stem"] == "Tetris (World)" for row in matched_rows)
    assert {row["rom_stem"] for row in missing_rows} == {
        "Pokemon Red Version (USA)",
        "Super Mario World (USA)",
    }


def test_build_assets_calls_progress_callback(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "output"
    _write_game_with_cover(library, "gb", "Tetris (World)", ".gb")
    progress: list[tuple[int, int, str]] = []

    build_assets(
        input_path=library,
        output_root=output,
        style="fit",
        threshold=88,
        progress_callback=lambda current, total, message: progress.append((current, total, message)),
    )

    assert progress == [(1, 1, "Building covers: 1 / 1")]


def test_build_assets_uses_optional_artwork_source(tmp_path: Path) -> None:
    prepared = tmp_path / "prepared"
    artwork = tmp_path / "original"
    output = tmp_path / "output"
    rom_dir = prepared / "roms" / "gb"
    image_dir = artwork / "roms" / "gb" / "images"
    rom_dir.mkdir(parents=True)
    image_dir.mkdir(parents=True)
    (rom_dir / "Tetris.gb").write_bytes(b"rom")
    Image.new("RGB", (320, 240), (30, 60, 120)).save(image_dir / "Tetris.png")

    result = build_assets(
        input_path=prepared,
        output_root=output,
        style="fit",
        threshold=88,
        artwork_sources=[artwork],
    )

    assert len(result.matches) == 1
    cover_path = output / "tico" / "assets" / "covers" / "gb" / "Tetris.jpg"
    with Image.open(cover_path) as cover:
        assert cover.format == "JPEG"
        assert cover.size == (512, 512)
    matched_rows = _read_csv(output / "reports" / "matched-covers.csv")
    assert matched_rows[0]["cover_path"] == str(image_dir / "Tetris.png")


def test_build_assets_cancel_stops_before_all_covers(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "output"
    _write_game_with_cover(library, "gb", "A", ".gb")
    _write_game_with_cover(library, "gb", "B", ".gb")
    should_cancel = False

    def progress_callback(current: int, total: int, message: str) -> None:
        nonlocal should_cancel
        should_cancel = True

    result = build_assets(
        input_path=library,
        output_root=output,
        style="fit",
        threshold=88,
        progress_callback=progress_callback,
        cancel_check=lambda: should_cancel,
    )

    assert result.cancelled
    assert len(result.matches) == 1
    assert (output / "tico" / "assets" / "covers" / "gb" / "A.jpg").exists()
    assert not (output / "tico" / "assets" / "covers" / "gb" / "B.jpg").exists()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_game_with_cover(library: Path, console: str, stem: str, extension: str) -> None:
    rom_dir = library / "roms" / console
    image_dir = library / "images" / console
    rom_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)
    (rom_dir / f"{stem}{extension}").write_bytes(b"rom")
    Image.new("RGB", (320, 240), (30, 60, 120)).save(image_dir / f"{stem}.png")
