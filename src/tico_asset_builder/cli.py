"""Command-line entry point for cover-asset-only builds."""

from __future__ import annotations

import argparse
from pathlib import Path

from .builder import build_assets
from .config import CONSOLES
from .images import VALID_STYLES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tico-asset-builder",
        description=(
            "Build a Tico-compatible tico/assets/covers folder from a local ROM library and local cover images. "
            "No scraping or online image lookup is performed."
        ),
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Folder to scan. Use a Tico folder with roms/{console}/ or a ROM library with console folders directly inside.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Folder where tico/assets/covers and CSV reports will be created. Defaults to ./output.",
    )
    parser.add_argument(
        "--artwork-source",
        type=Path,
        action="append",
        help=(
            "Optional source folder to search for local artwork in addition to the input folder. "
            "Use this when ROMs are in a prepared folder but artwork is still in the original library."
        ),
    )
    parser.add_argument(
        "--style",
        choices=VALID_STYLES,
        default="fit",
        help="How to resize covers to 512x512: fit adds padding, crop trims edges, stretch fills the square. Defaults to fit.",
    )
    parser.add_argument(
        "--match-threshold",
        type=int,
        default=88,
        help="Minimum fuzzy match score for matching image names to ROM names, from 0 to 100. Defaults to 88.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Create reports only, without writing converted cover image files.",
    )
    parser.add_argument(
        "--list-consoles",
        action="store_true",
        help="Show the supported console folder names and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_consoles:
        for console in CONSOLES:
            print(console)
        return 0

    input_path = args.input.expanduser().resolve()
    output_root = args.output.expanduser().resolve()

    if not input_path.exists() or not input_path.is_dir():
        parser.error(f"Input folder does not exist: {input_path}")
    artwork_sources = [path.expanduser().resolve() for path in args.artwork_source or []]
    for artwork_source in artwork_sources:
        if not artwork_source.exists() or not artwork_source.is_dir():
            parser.error(f"Artwork source folder does not exist: {artwork_source}")

    if not 0 <= args.match_threshold <= 100:
        parser.error("--match-threshold must be between 0 and 100")

    result = build_assets(
        input_path=input_path,
        output_root=output_root,
        style=args.style,
        threshold=args.match_threshold,
        dry_run=args.dry_run,
        artwork_sources=artwork_sources,
    )

    print(f"Detected games: {len(result.games)}")
    print(f"Matched covers: {len(result.matches)}")
    print(f"Missing covers: {len(result.missing)}")
    print(f"Skipped files: {len(result.skipped)}")
    compressed_archive_count = sum(1 for item in result.skipped if item.reason == "compressed archive")
    if compressed_archive_count:
        print(
            "Warning: skipped "
            f"{compressed_archive_count} compressed ROM archive(s). "
            "Tico does not support compressed ROM archives, so extract those ROMs before building covers. "
            "Skipped archive files are listed in skipped-files.csv."
        )
    print(f"Reports: {output_root / 'reports'}")
    if artwork_sources:
        print("Artwork sources:")
        for artwork_source in artwork_sources:
            print(f"- {artwork_source}")
    if not args.dry_run:
        print(f"Covers: {output_root / 'tico' / 'assets' / 'covers'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
