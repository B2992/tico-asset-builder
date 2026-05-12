"""Command-line entry point for the recommended combined workflow."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from .combined import build_tico_folder
from .config import CONSOLES
from .images import VALID_STYLES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tico-build-tico-folder",
        description=(
            "Build one final Tico-compatible folder containing prepared ROMs and resized local cover assets. "
            "The source library is never modified."
        ),
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Source ROM library to read. The original folder is treated as read-only.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Final output folder to create. It will contain tico/roms and tico/assets/covers.",
    )
    parser.add_argument(
        "--style",
        choices=VALID_STYLES,
        default="fit",
        help="How to resize covers to 512x512: fit adds padding, crop trims edges, stretch fills the square. Defaults to fit.",
    )
    parser.add_argument(
        "--console",
        action="append",
        choices=CONSOLES,
        help="Only prepare one console folder. Repeat this option to prepare more than one console.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing into a non-empty final output folder and replacing extracted ROM files there.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_folder = args.input.expanduser().resolve()
    output_folder = args.output.expanduser().resolve()

    if not input_folder.exists() or not input_folder.is_dir():
        parser.error(f"Input folder does not exist: {input_folder}")

    try:
        result = build_tico_folder(
            source_library=input_folder,
            final_output=output_folder,
            style=args.style,
            consoles=args.console,
            overwrite=args.overwrite,
        )
    except ValueError as error:
        parser.error(str(error))

    assets = result.assets
    print("Combined Tico folder complete.")
    print(f"Prepared ROMs: {len(result.prep.prepared)}")
    for console, count in sorted(Counter(item.console for item in result.prep.prepared).items()):
        print(f"{console}: {count} prepared")
    print(f"Skipped archive items: {len(result.prep.skipped)}")
    if assets:
        print(f"Detected games: {len(assets.games)}")
        print(f"Matched covers: {len(assets.matches)}")
        print(f"Missing covers: {len(assets.missing)}")
        print(f"Skipped files: {len(assets.skipped)}")
    print(f"Prepared ROM folder: {output_folder / 'tico' / 'roms'}")
    print(f"Cover assets folder: {output_folder / 'tico' / 'assets' / 'covers'}")
    print(f"Prep reports: {output_folder / 'tico' / 'reports'}")
    print(f"Asset reports: {output_folder / 'reports'}")
    print("Original ROM library was left untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
