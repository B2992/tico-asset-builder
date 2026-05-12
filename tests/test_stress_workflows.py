from __future__ import annotations

import csv
from pathlib import Path
from zipfile import ZipFile

import pytest
from PIL import Image

from tico_asset_builder.builder import build_assets
from tico_asset_builder.combined import build_tico_folder
from tico_asset_builder.gui import (
    _should_apply_suggestion,
    count_report_rows,
    load_csv_report,
    select_detected_console_keys,
    summarize_reports,
    validate_asset_output_path,
    validate_prepare_output_path,
)
from tico_asset_builder.images import convert_cover
from tico_asset_builder.prep import prepare_roms


STRESS_CONSOLES = {
    "gb": ".gb",
    "gbc": ".gbc",
    "gba": ".gba",
    "nes": ".nes",
    "snes": ".sfc",
    "genesis": ".md",
}


def test_combined_workflow_stress_multiple_consoles(tmp_path: Path) -> None:
    source = tmp_path / "fake-library"
    output = tmp_path / "fake-library-tico-output"
    expected_per_console = 25
    missing_per_console = 5

    for console, extension in STRESS_CONSOLES.items():
        for index in range(expected_per_console):
            stem = f"{console.upper()} Fake Game {index:02d} (USA)"
            _write_zip(source / "roms" / console / f"{stem}.zip", {f"{stem}{extension}": _rom_bytes(console, index)})
            if index >= missing_per_console:
                _write_image(source / "roms" / console / "images" / f"{console.upper()} Fake Game {index:02d}.png")

    before = _snapshot(source)

    result = build_tico_folder(source, output, style="fit")

    assert _snapshot(source) == before
    assert len(result.prep.prepared) == len(STRESS_CONSOLES) * expected_per_console
    assert result.assets is not None
    assert len(result.assets.matches) == len(STRESS_CONSOLES) * (expected_per_console - missing_per_console)
    assert len(result.assets.missing) == len(STRESS_CONSOLES) * missing_per_console

    for console, extension in STRESS_CONSOLES.items():
        roms = sorted((output / "tico" / "roms" / console).glob(f"*{extension}"))
        covers = sorted((output / "tico" / "assets" / "covers" / console).glob("*.jpg"))
        assert len(roms) == expected_per_console
        assert len(covers) == expected_per_console - missing_per_console
        assert not (output / "tico" / "roms" / console / "images").exists()
        assert sorted((source / "roms" / console).glob("*.zip"))
        with Image.open(covers[0]) as cover:
            assert cover.format == "JPEG"
            assert cover.size == (512, 512)

    assert (output / "tico" / "reports" / "prepared-roms.csv").exists()
    assert (output / "tico" / "reports" / "skipped-archives.csv").exists()
    assert count_report_rows(output / "reports" / "missing-covers.csv") == len(STRESS_CONSOLES) * missing_per_console


def test_messy_filename_matching_accepts_expected_and_rejects_bad_matches(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "output"
    rom_dir = library / "roms" / "gb"
    image_dir = library / "roms" / "gb" / "images"
    rom_dir.mkdir(parents=True)
    image_dir.mkdir(parents=True)

    expected_matches = {
        "Game Name (USA)": "Game Name.png",
        "Game Name (USA, Europe)": "Game Name.png",
        "Game Name [Rev 1]": "Game Name.png",
        "The Adventures of Test, The (USA)": "Adventures of Test The.png",
        "Test Game - Subtitle (Europe)": "Test Game Subtitle.png",
        "Test_Game_Cover": "Test Game-cover.png",
        "test game boxart": "test game boxart.png",
        "The Legend of Zelda - Link's Awakening (USA, Europe)": "Legend of Zelda Links Awakening.png",
    }
    for stem in expected_matches:
        (rom_dir / f"{stem}.gb").write_bytes(b"fake-rom")
    for filename in set(expected_matches.values()):
        _write_image(image_dir / filename)
    (rom_dir / "Completely Different Game.gb").write_bytes(b"fake-rom")
    _write_image(image_dir / "Wrong Franchise Cover.png")

    result = build_assets(library, output, style="fit", threshold=88)

    matched_stems = {match.game.stem for match in result.matches}
    assert set(expected_matches) <= matched_stems
    assert "Completely Different Game" not in matched_stems
    assert any(item.game.stem == "Completely Different Game" for item in result.missing)


def test_zip_edge_cases_are_reported_without_crashing(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "prepared"
    console_dir = source / "roms" / "gb"
    _write_zip(
        console_dir / "Valid With Junk.zip",
        {
            "Valid With Junk.gb": b"rom",
            ".DS_Store": b"metadata",
            "__MACOSX/Valid With Junk.gb": b"metadata",
            "readme.txt": b"notes",
            "images/cover.png": b"image",
            "cover.png": b"image",
        },
    )
    _write_zip(console_dir / "Two Games.zip", {"One.gb": b"one", "Two.gb": b"two"})
    _write_zip(console_dir / "No Valid Rom.zip", {"notes.txt": b"notes"})
    _write_corrupt_zip(console_dir / "Corrupt.zip")

    result = prepare_roms(source, output)

    assert sorted(path.name for path in (output / "roms" / "gb").glob("*.gb")) == [
        "One.gb",
        "Two.gb",
        "Valid With Junk.gb",
    ]
    assert len(result.prepared) == 3
    skipped_rows = _read_csv(output / "reports" / "skipped-archives.csv")
    reasons = [row["reason"] for row in skipped_rows]
    assert "invalid zip archive" in reasons
    assert "unsupported file inside archive" in reasons
    assert "macOS metadata" in reasons
    assert "image folder inside archive" in reasons
    assert "image file inside archive" in reasons


def test_safety_boundaries_and_dry_run_leave_source_untouched(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "prepared"
    _write_zip(source / "roms" / "gb" / "Tetris.zip", {"Tetris.gb": b"rom"})
    before = _snapshot(source)

    assert validate_prepare_output_path(source, source) is not None
    assert validate_prepare_output_path(source, source / "roms" / "prepared") is not None
    assert validate_asset_output_path(output, output) is not None

    output.mkdir()
    (output / "existing.txt").write_text("existing", encoding="utf-8")
    with pytest.raises(ValueError, match="Output folder already exists"):
        prepare_roms(source, output)
    assert _snapshot(source) == before

    dry_run_output = tmp_path / "dry-run-output"
    result = prepare_roms(source, dry_run_output, dry_run=True)

    assert len(result.prepared) == 1
    assert not dry_run_output.exists()
    assert _snapshot(source) == before


def test_separate_and_combined_workflows_keep_outputs_clean(tmp_path: Path) -> None:
    source = tmp_path / "source"
    prepared = tmp_path / "prepared"
    assets = tmp_path / "assets"
    combined = tmp_path / "combined"
    _write_zip(source / "roms" / "gb" / "Tetris.zip", {"Tetris.gb": b"rom"})
    _write_image(source / "roms" / "gb" / "images" / "Tetris.png")

    prepare_roms(source, prepared)

    assert (prepared / "roms" / "gb" / "Tetris.gb").exists()
    assert not (prepared / "roms" / "gb" / "images").exists()

    build_assets(prepared, assets, style="fit", threshold=88, artwork_sources=[source])

    assert (assets / "tico" / "assets" / "covers" / "gb" / "Tetris.jpg").exists()
    assert not (assets / "tico" / "roms").exists()

    build_tico_folder(source, combined, style="fit")

    assert (combined / "tico" / "roms" / "gb" / "Tetris.gb").exists()
    assert (combined / "tico" / "assets" / "covers" / "gb" / "Tetris.jpg").exists()
    assert not (combined / "tico" / "roms" / "gb" / "images").exists()


def test_image_styles_always_output_512_square_jpegs(tmp_path: Path) -> None:
    source = tmp_path / "wide.png"
    _write_image(source, size=(800, 240))

    for style in ("fit", "crop", "stretch"):
        destination = tmp_path / f"{style}.jpg"
        convert_cover(source, destination, style)
        with Image.open(destination) as cover:
            assert cover.format == "JPEG"
            assert cover.size == (512, 512)
            assert cover.size != (800, 240)


def test_report_and_gui_helpers_handle_stress_reports(tmp_path: Path) -> None:
    prep_reports = tmp_path / "prep" / "reports"
    asset_reports = tmp_path / "assets" / "reports"
    prep_reports.mkdir(parents=True)
    asset_reports.mkdir(parents=True)
    _write_csv(prep_reports / "prepared-roms.csv", ["console"], [["gb"], ["gba"]])
    _write_csv(prep_reports / "skipped-archives.csv", ["console"], [])
    _write_csv(asset_reports / "detected-games.csv", ["console"], [["gb"], ["gba"], ["snes"]])
    _write_csv(asset_reports / "matched-covers.csv", ["console"], [["gb"], ["gba"]])
    _write_csv(asset_reports / "missing-covers.csv", ["console"], [["snes"]])
    _write_csv(asset_reports / "skipped-files.csv", ["console"], [])

    assert load_csv_report(prep_reports / "prepared-roms.csv").rows == [{"console": "gb"}, {"console": "gba"}]
    assert load_csv_report(prep_reports / "skipped-archives.csv").rows == []
    assert not load_csv_report(tmp_path / "missing.csv").exists
    assert count_report_rows(asset_reports / "detected-games.csv") == 3
    assert summarize_reports(prep_reports, asset_reports)["missing_covers"] == 1
    assert _should_apply_suggestion("", "/tmp/old")
    assert not _should_apply_suggestion("/tmp/custom", "/tmp/old")


def test_detected_console_selection_helper_uses_gui_supported_subset(tmp_path: Path) -> None:
    from tico_asset_builder.gui import analyze_library

    source = tmp_path / "source"
    _write_zip(source / "roms" / "gb" / "Tetris.zip", {"Tetris.gb": b"rom"})
    _write_zip(source / "roms" / "wii" / "Disc.zip", {"Disc.iso": b"rom"})

    analysis = analyze_library(source)

    assert "gb" in analysis.detected_consoles
    assert "wii" in analysis.detected_consoles
    assert select_detected_console_keys(analysis) == ["gb", "wii"]


def _write_zip(path: Path, members: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def _write_corrupt_zip(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"this is not a zip file")


def _write_image(path: Path, size: tuple[int, int] = (320, 240)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (40, 90, 150)).save(path)


def _write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _snapshot(path: Path) -> dict[str, bytes]:
    return {str(item.relative_to(path)): item.read_bytes() for item in sorted(path.rglob("*")) if item.is_file()}


def _rom_bytes(console: str, index: int) -> bytes:
    return f"fake-rom-{console}-{index}".encode("ascii")
