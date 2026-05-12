from __future__ import annotations

import tomllib
import csv
from pathlib import Path


def test_gui_module_imports() -> None:
    import tico_asset_builder.gui as gui
    from tico_asset_builder.config import CONSOLES

    assert gui.GUI_CONSOLES == tuple(CONSOLES)
    assert "psp" in gui.GUI_CONSOLES
    assert "dc" in gui.GUI_CONSOLES
    assert "wii" in gui.GUI_CONSOLES
    assert gui.COVER_STYLES == ("fit", "crop", "stretch")


def test_gui_entry_point_is_declared() -> None:
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    assert data["project"]["scripts"]["tico-asset-builder-gui"] == "tico_asset_builder.gui:main"
    assert data["project"]["scripts"]["tico-build-tico-folder"] == "tico_asset_builder.combined_cli:main"


def test_gui_dry_run_summary_is_explicit() -> None:
    from tico_asset_builder.gui import format_prepare_summary
    from tico_asset_builder.prep import PrepResult

    lines = format_prepare_summary(PrepResult(prepared=[], skipped=[]), dry_run=True)

    assert "Dry run complete." in lines
    assert "No ROMs were extracted." in lines
    assert "No artwork was copied." in lines
    assert "No output folder was created." in lines
    assert "Original ROM library was left untouched." in lines


def test_gui_suggests_prepared_output_folder() -> None:
    from tico_asset_builder.gui import suggest_prepared_output_folder

    assert suggest_prepared_output_folder(Path("/tmp/real_test_library")) == Path(
        "/tmp/real_test_library-tico-prepared"
    )


def test_gui_suggests_asset_output_folder_from_prepared_suffix() -> None:
    from tico_asset_builder.gui import suggest_asset_output_folder

    assert suggest_asset_output_folder(Path("/tmp/real_test_library-tico-prepared")) == Path(
        "/tmp/real_test_library-tico-assets"
    )


def test_gui_suggests_asset_output_folder_without_prepared_suffix() -> None:
    from tico_asset_builder.gui import suggest_asset_output_folder

    assert suggest_asset_output_folder(Path("/tmp/prepared-gb")) == Path("/tmp/prepared-gb-tico-assets")


def test_gui_suggests_combined_output_folder() -> None:
    from tico_asset_builder.gui import suggest_combined_output_folder

    assert suggest_combined_output_folder(Path("/tmp/real_test_library")) == Path("/tmp/real_test_library-tico-output")


def test_gui_preserves_custom_output_choice() -> None:
    from tico_asset_builder.gui import _should_apply_suggestion

    assert _should_apply_suggestion("", "/tmp/old-auto")
    assert _should_apply_suggestion("/tmp/old-auto", "/tmp/old-auto")
    assert not _should_apply_suggestion("/tmp/custom-output", "/tmp/old-auto")


def test_gui_rejects_prepare_output_same_as_source() -> None:
    from tico_asset_builder.gui import validate_prepare_output_path

    message = validate_prepare_output_path(Path("/tmp/source"), Path("/tmp/source"))

    assert message == "Choose a prepared output folder that is separate from the source library."


def test_gui_rejects_prepare_output_inside_source_roms() -> None:
    from tico_asset_builder.gui import validate_prepare_output_path

    message = validate_prepare_output_path(Path("/tmp/source"), Path("/tmp/source/roms/prepared"))

    assert message == "Choose a prepared output folder outside the source library's roms folder."


def test_gui_rejects_asset_output_same_as_prepared_folder() -> None:
    from tico_asset_builder.gui import validate_asset_output_path

    message = validate_asset_output_path(Path("/tmp/prepared"), Path("/tmp/prepared"))

    assert message == "Choose an asset output folder that is separate from the prepared ROM folder."


def test_gui_allows_safe_sibling_outputs() -> None:
    from tico_asset_builder.gui import validate_asset_output_path, validate_prepare_output_path

    assert validate_prepare_output_path(Path("/tmp/source"), Path("/tmp/source-tico-prepared")) is None
    assert validate_asset_output_path(Path("/tmp/source-tico-prepared"), Path("/tmp/source-tico-assets")) is None


def test_analyze_library_counts_zipped_extracted_and_images(tmp_path: Path) -> None:
    from tico_asset_builder.gui import analyze_library

    gb = tmp_path / "library" / "roms" / "gb"
    gb_images = gb / "images"
    gb_images.mkdir(parents=True)
    (gb / "Tetris.zip").write_bytes(b"zip")
    (gb / "Tetris.gb").write_bytes(b"rom")
    (gb / ".DS_Store").write_bytes(b"metadata")
    (gb_images / "Tetris.png").write_bytes(b"image")
    (gb_images / ".DS_Store").write_bytes(b"metadata")

    analysis = analyze_library(tmp_path / "library")

    assert analysis.consoles["gb"].zipped_roms == 1
    assert analysis.consoles["gb"].extracted_roms == 1
    assert analysis.consoles["gb"].local_images == 1
    assert analysis.consoles["gb"].source_folder_name == "gb"


def test_analyze_library_counts_multiple_consoles_and_unsupported_folders(tmp_path: Path) -> None:
    from tico_asset_builder.gui import analyze_library

    roms = tmp_path / "library" / "roms"
    (roms / "gba").mkdir(parents=True)
    (roms / "snes" / "images").mkdir(parents=True)
    (roms / "not-a-console").mkdir(parents=True)
    (roms / "gba" / "Advance Wars.zip").write_bytes(b"zip")
    (roms / "snes" / "ActRaiser.sfc").write_bytes(b"rom")
    (roms / "snes" / "images" / "ActRaiser.jpg").write_bytes(b"image")

    analysis = analyze_library(tmp_path / "library")

    assert analysis.consoles["gba"].zipped_roms == 1
    assert analysis.consoles["snes"].extracted_roms == 1
    assert analysis.consoles["snes"].local_images == 1
    assert analysis.unsupported_folders == ["not-a-console"]


def test_select_detected_console_keys_uses_gui_supported_subset(tmp_path: Path) -> None:
    from tico_asset_builder.gui import analyze_library, select_detected_console_keys

    roms = tmp_path / "library" / "roms"
    (roms / "gb").mkdir(parents=True)
    (roms / "wii").mkdir(parents=True)
    (roms / "gb" / "Tetris.zip").write_bytes(b"zip")
    (roms / "wii" / "Game.iso").write_bytes(b"rom")

    analysis = analyze_library(tmp_path / "library")

    assert analysis.detected_consoles == ["gb", "wii"]
    assert select_detected_console_keys(analysis) == ["gb", "wii"]


def test_console_keys_for_analysis_detected_only_and_all_supported(tmp_path: Path) -> None:
    from tico_asset_builder.gui import analyze_library, console_keys_for_analysis

    roms = tmp_path / "library" / "roms"
    (roms / "gb").mkdir(parents=True)
    (roms / "gba").mkdir(parents=True)
    (roms / "not-supported").mkdir(parents=True)
    (roms / "gb" / "Tetris.zip").write_bytes(b"zip")
    (roms / "gba" / "Advance Wars.gba").write_bytes(b"rom")

    analysis = analyze_library(tmp_path / "library")

    assert console_keys_for_analysis(analysis) == ["gb", "gba"]
    all_keys = console_keys_for_analysis(analysis, show_all_supported=True)
    assert all_keys[:2] == ["gb", "gba"]
    assert "psp" in all_keys
    assert "not-supported" not in all_keys
    assert analysis.unsupported_folders == ["not-supported"]


def test_console_checkbox_label_includes_counts(tmp_path: Path) -> None:
    from tico_asset_builder.gui import analyze_library, console_checkbox_label

    gb = tmp_path / "library" / "roms" / "gb"
    images = gb / "images"
    images.mkdir(parents=True)
    (gb / "Tetris.zip").write_bytes(b"zip")
    (gb / "Pokemon.gb").write_bytes(b"rom")
    (images / "Tetris.png").write_bytes(b"image")

    analysis = analyze_library(tmp_path / "library")

    assert console_checkbox_label("gb", analysis) == "gb - 1 zipped, 1 extracted, 1 images"


def test_analyze_library_reports_aliases_with_canonical_console(tmp_path: Path) -> None:
    from tico_asset_builder.gui import analyze_library, console_checkbox_label, format_library_analysis

    sfc = tmp_path / "library" / "roms" / "SFC"
    sfc_images = sfc / "images"
    sfc_images.mkdir(parents=True)
    (sfc / "ActRaiser.zip").write_bytes(b"zip")
    (sfc_images / "ActRaiser.png").write_bytes(b"image")

    analysis = analyze_library(tmp_path / "library")

    assert list(analysis.consoles) == ["snes"]
    assert analysis.consoles["snes"].source_folder_name == "SFC"
    assert "SFC -> snes" in format_library_analysis(analysis)
    assert console_checkbox_label("snes", analysis).startswith("snes from SFC")


def test_load_csv_report_with_rows(tmp_path: Path) -> None:
    from tico_asset_builder.gui import load_csv_report

    path = tmp_path / "report.csv"
    _write_csv(path, ["console", "name"], [["gb", "Tetris"]])

    report = load_csv_report(path)

    assert report.exists
    assert report.headers == ["console", "name"]
    assert report.rows == [{"console": "gb", "name": "Tetris"}]


def test_load_csv_report_empty_with_headers(tmp_path: Path) -> None:
    from tico_asset_builder.gui import load_csv_report

    path = tmp_path / "missing-covers.csv"
    _write_csv(path, ["console", "rom_stem"], [])

    report = load_csv_report(path)

    assert report.exists
    assert report.headers == ["console", "rom_stem"]
    assert report.rows == []


def test_load_csv_report_missing_file() -> None:
    from tico_asset_builder.gui import load_csv_report

    report = load_csv_report(Path("/tmp/does-not-exist-report.csv"))

    assert not report.exists
    assert report.headers == []
    assert report.rows == []


def test_summarize_reports_counts_rows(tmp_path: Path) -> None:
    from tico_asset_builder.gui import summarize_reports

    prep = tmp_path / "prepared" / "reports"
    assets = tmp_path / "assets" / "reports"
    prep.mkdir(parents=True)
    assets.mkdir(parents=True)
    _write_csv(prep / "prepared-roms.csv", ["console"], [["gb"], ["gba"]])
    _write_csv(prep / "skipped-archives.csv", ["console"], [["gb"]])
    _write_csv(assets / "detected-games.csv", ["console"], [["gb"], ["gba"], ["snes"]])
    _write_csv(assets / "matched-covers.csv", ["console"], [["gb"], ["gba"]])
    _write_csv(assets / "missing-covers.csv", ["console"], [["snes"]])
    _write_csv(assets / "skipped-files.csv", ["console"], [])

    summary = summarize_reports(prep, assets)

    assert summary == {
        "prepared_roms": 2,
        "skipped_archives": 1,
        "detected_games": 3,
        "matched_covers": 2,
        "missing_covers": 1,
        "skipped_files": 0,
    }


def test_format_summary_text() -> None:
    from tico_asset_builder.gui import format_summary_text

    text = format_summary_text(
        {
            "prepared_roms": 1,
            "skipped_archives": 2,
            "detected_games": 3,
            "matched_covers": 4,
            "missing_covers": 5,
            "skipped_files": 6,
        }
    )

    assert "Tico Asset Builder Summary" in text
    assert "Missing Covers: 5" in text
    assert "Original ROM Library Modified: No" in text


def _write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
