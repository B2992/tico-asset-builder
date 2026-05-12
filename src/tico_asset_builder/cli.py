from __future__ import annotations

import argparse
from pathlib import Path

from .builder import build_assets
from .config import CONSOLES
from .images import VALID_STYLES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tico-asset-builder",
        description="Create Tico-compatible cover assets from a local Tico or ROM library folder.",
    )
    parser.add_argument("input", type=Path, help="Tico folder or ROM library folder to scan.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Output folder. Defaults to ./output.",
    )
    parser.add_argument(
        "--style",
        choices=VALID_STYLES,
        default="fit",
        help="Cover conversion style. Defaults to fit with padding.",
    )
    parser.add_argument(
        "--match-threshold",
        type=int,
        default=88,
        help="Minimum RapidFuzz score for fuzzy cover matches. Defaults to 88.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write reports without converting image files.",
    )
    parser.add_argument(
        "--list-consoles",
        action="store_true",
        help="Print supported console folder names and exit.",
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

    if not 0 <= args.match_threshold <= 100:
        parser.error("--match-threshold must be between 0 and 100")

    result = build_assets(
        input_path=input_path,
        output_root=output_root,
        style=args.style,
        threshold=args.match_threshold,
        dry_run=args.dry_run,
    )

    print(f"Detected games: {len(result.games)}")
    print(f"Matched covers: {len(result.matches)}")
    print(f"Missing covers: {len(result.missing)}")
    print(f"Skipped files: {len(result.skipped)}")
    print(f"Reports: {output_root / 'reports'}")
    if not args.dry_run:
        print(f"Covers: {output_root / 'tico' / 'assets' / 'covers'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

