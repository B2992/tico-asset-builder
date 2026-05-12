from __future__ import annotations

from pathlib import Path

from tico_asset_builder.scanner import scan_games


def test_scans_tico_rom_root(tmp_path: Path) -> None:
    rom_dir = tmp_path / "roms" / "gba"
    rom_dir.mkdir(parents=True)
    (rom_dir / "Metroid Fusion.gba").write_bytes(b"rom")
    (rom_dir / "ignore.zip").write_bytes(b"archive")

    games, skipped = scan_games(tmp_path)

    assert [game.stem for game in games] == ["Metroid Fusion"]
    assert skipped[0].reason == "compressed archive"


def test_disc_system_skips_bin_when_cue_exists(tmp_path: Path) -> None:
    psx_dir = tmp_path / "psx"
    psx_dir.mkdir()
    (psx_dir / "Ridge Racer.cue").write_text("FILE \"Ridge Racer.bin\" BINARY")
    (psx_dir / "Ridge Racer.bin").write_bytes(b"track")

    games, skipped = scan_games(tmp_path)

    assert [game.path.name for game in games] == ["Ridge Racer.cue"]
    assert [item.reason for item in skipped] == ["secondary disc track"]


def test_disc_system_keeps_unrelated_standalone_bin(tmp_path: Path) -> None:
    psx_dir = tmp_path / "psx"
    psx_dir.mkdir()
    (psx_dir / "Ridge Racer.cue").write_text("FILE \"Ridge Racer.bin\" BINARY")
    (psx_dir / "Ridge Racer Track 01.bin").write_bytes(b"track")
    (psx_dir / "Standalone Demo.bin").write_bytes(b"disc")

    games, skipped = scan_games(tmp_path)

    assert [game.path.name for game in games] == ["Ridge Racer.cue", "Standalone Demo.bin"]
    assert [item.path.name for item in skipped] == ["Ridge Racer Track 01.bin"]
