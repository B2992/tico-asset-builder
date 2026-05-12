"""Command-line entry point for ROM-only preparation."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from .config import CONSOLES
from .prep import prepare_roms


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tico-prepare-roms",
        description=(
            "Create a separate prepared ROM folder from zipped local ROM folders. "
            "The input folder is never modified."
        ),
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Source ROM library to read. Use a Tico-style folder with roms/{console}/Game.zip.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Separate folder to create for extracted ROMs and prep reports. Cover art is not copied.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing into a non-empty output folder and replacing extracted ROM files there.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect what would be prepared without extracting ROMs or creating the output folder.",
    )
    parser.add_argument(
        "--console",
        action="append",
        choices=CONSOLES,
        help="Only prepare one console folder. Repeat this option to prepare more than one console.",
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
        result = prepare_roms(
            input_folder=input_folder,
            output_folder=output_folder,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            consoles=args.console,
        )
    except ValueError as error:
        parser.error(str(error))

    if args.dry_run:
        print("Dry run complete. No ROMs were extracted and no output folder was created.")
        print(f"ROMs that would be extracted: {len(result.prepared)}")
    else:
        print("Prepared ROM copy complete. Cover art was not copied.")
        print(f"Extracted ROMs: {len(result.prepared)}")
    for console, count in sorted(Counter(item.console for item in result.prepared).items()):
        action = "would be extracted" if args.dry_run else "extracted"
        print(f"{console}: {count} {action}")
    print(f"Skipped archive items: {len(result.skipped)}")
    if args.dry_run:
        print(f"Output folder checked: {output_folder}")
    else:
        print(f"Prepared folder: {output_folder / 'roms'}")
        print(f"Reports: {output_folder / 'reports'}")
    print("Original ROM library was left untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
