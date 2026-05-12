from __future__ import annotations

from pathlib import Path

from PIL import Image

from tico_asset_builder.builder import build_assets
from tico_asset_builder.matcher import match_covers
from tico_asset_builder.models import CoverCandidate, Game
from tico_asset_builder.names import normalized_stem


def test_local_matching_handles_common_clean_name_differences(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "output"
    roms = library / "roms"
    images = library / "images"

    _touch_rom(roms / "gb" / "Tetris (World).gb")
    _touch_rom(roms / "gb" / "Pokemon Red Version (USA).gb")
    _touch_rom(roms / "gb" / "The Legend of Zelda - Link's Awakening (USA, Europe).gb")
    _touch_rom(roms / "snes" / "Super Mario World (USA).sfc")
    _write_png(images / "gb" / "Tetris.png")
    _write_png(images / "gb" / "Pokemon Red Version.png")
    _write_png(images / "gb" / "Legend of Zelda Links Awakening.png")
    _write_png(images / "snes" / "Super Mario World-cover.jpg")

    result = build_assets(input_path=library, output_root=output, style="fit", threshold=88)

    assert not result.missing
    assert _cover_exists(output, "gb", "Tetris (World)")
    assert _cover_exists(output, "gb", "Pokemon Red Version (USA)")
    assert _cover_exists(output, "gb", "The Legend of Zelda - Link's Awakening (USA, Europe)")
    assert _cover_exists(output, "snes", "Super Mario World (USA)")


def test_local_matching_finds_downloaded_images_folder_next_to_console(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "output"
    _touch_rom(library / "roms" / "gb" / "Tetris (World).gb")
    _write_png(library / "roms" / "gb" / "downloaded_images" / "Tetris.png")

    build_assets(input_path=library, output_root=output, style="fit", threshold=88)

    assert _cover_exists(output, "gb", "Tetris (World)")


def test_local_matching_finds_artwork_folder_by_console(tmp_path: Path) -> None:
    library = tmp_path / "library"
    output = tmp_path / "output"
    _touch_rom(library / "gb" / "Tetris (World).gb")
    _write_png(library / "artwork" / "gb" / "Tetris.png")

    build_assets(input_path=library, output_root=output, style="fit", threshold=88)

    assert _cover_exists(output, "gb", "Tetris (World)")


def test_exact_stem_match_wins_before_normalized_match(tmp_path: Path) -> None:
    game = Game(console="gb", path=tmp_path / "Tetris (World).gb", stem="Tetris (World)")
    exact_candidate = _candidate(tmp_path / "Tetris (World).png")
    normalized_candidate = _candidate(tmp_path / "Tetris.png")

    matches, missing = match_covers(
        [game],
        {"gb": [normalized_candidate, exact_candidate]},
        tmp_path / "output",
        threshold=88,
    )

    assert not missing
    assert matches[0].cover_path == exact_candidate.path
    assert matches[0].method == "exact"


def _touch_rom(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


def _write_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (320, 240), (30, 60, 120)).save(path)


def _cover_exists(output: Path, console: str, stem: str) -> bool:
    return (output / "tico" / "assets" / "covers" / console / f"{stem}.jpg").exists()


def _candidate(path: Path) -> CoverCandidate:
    return CoverCandidate(path=path, normalized_stem=normalized_stem(path))
