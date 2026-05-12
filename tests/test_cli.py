from __future__ import annotations

from pathlib import Path

from PIL import Image

from tico_asset_builder.cli import main


def test_cli_warns_when_compressed_archives_are_skipped(tmp_path: Path, capsys) -> None:
    library = tmp_path / "library"
    output = tmp_path / "output"
    roms = library / "roms" / "gb"
    roms.mkdir(parents=True)
    (roms / "Tetris (World).zip").write_bytes(b"archive")

    exit_code = main([str(library), "--output", str(output), "--style", "fit"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Warning: skipped 1 compressed ROM archive(s)." in captured.out
    assert "Tico does not support compressed ROM archives" in captured.out
    assert "extract those ROMs before building covers" in captured.out
    assert "skipped-files.csv" in captured.out


def test_cli_builds_with_artwork_source(tmp_path: Path, capsys) -> None:
    prepared = tmp_path / "prepared"
    original = tmp_path / "original"
    output = tmp_path / "output"
    rom_dir = prepared / "roms" / "gb"
    image_dir = original / "roms" / "gb" / "images"
    rom_dir.mkdir(parents=True)
    image_dir.mkdir(parents=True)
    (rom_dir / "Tetris.gb").write_bytes(b"rom")
    Image.new("RGB", (320, 240), (30, 60, 120)).save(image_dir / "Tetris.png")

    exit_code = main(
        [
            str(prepared),
            "--artwork-source",
            str(original),
            "--output",
            str(output),
            "--style",
            "fit",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Matched covers: 1" in captured.out
    assert "Artwork sources:" in captured.out
    with Image.open(output / "tico" / "assets" / "covers" / "gb" / "Tetris.jpg") as cover:
        assert cover.format == "JPEG"
        assert cover.size == (512, 512)
