# Tico Asset Builder

Tico Asset Builder is a command-line utility that scans a Tico folder or a ROM library folder and creates a Tico-compatible cover asset folder.

It only uses local files. Online scraping and GUI features are intentionally out of scope for the MVP.

## Requirements

- Python 3.11+
- Pillow
- RapidFuzz

## Install for local development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Example Commands

Scan a Tico folder that contains `roms/{console}/`:

```bash
tico-asset-builder /path/to/tico-folder --output /path/to/output
```

Scan a ROM library folder where console folders are directly inside the input folder:

```bash
tico-asset-builder /path/to/rom-library --output /path/to/output
```

Use a different cover style:

```bash
tico-asset-builder /path/to/library --style crop
tico-asset-builder /path/to/library --style stretch
```

Adjust fuzzy matching strictness:

```bash
tico-asset-builder /path/to/library --match-threshold 82
```

Preview what would be created without writing images:

```bash
tico-asset-builder /path/to/library --dry-run
```

## Output

Covers are exported to:

```text
output/tico/assets/covers/{console}/{rom_stem}.jpg
```

Reports are written to:

```text
output/reports/detected-games.csv
output/reports/matched-covers.csv
output/reports/missing-covers.csv
output/reports/skipped-files.csv
```

## Supported Consoles

The MVP detects:

`gb`, `gbc`, `gba`, `nes`, `snes`, `genesis`, `master-system`, `game-gear`, `sega-cd`, `saturn`, `dc`, `psx`, `psp`, `gc`, `wii`

Input can be either:

- A Tico folder containing `roms/{console}/`
- A ROM library folder containing console folders directly

## Local Image Discovery

The scanner looks for images in likely folders such as:

`imgs`, `images`, `thumbnails`, `media`, `covers`, `boxart`

Images are matched to ROM filenames using exact normalized names first, then RapidFuzz fuzzy matching.

## Notes

- Compressed archives such as `.zip` and `.7z` are skipped.
- For disc systems, `.bin` track files are not treated as separate games when nearby `.cue`, `.chd`, `.iso`, or `.m3u` files indicate the disc game already exists.
- Default cover style is `fit`, which preserves aspect ratio and pads to 512x512.

