# Tico Asset Builder

Tico Asset Builder is a local-first utility that helps you create a Tico-compatible folder from an existing ROM library and existing local artwork.

Recommended output:

```text
my-library-tico-output/
  tico/
    roms/{console}/Game.ext
    assets/covers/{console}/Game.jpg
  reports/
```

The tool can run from the command line or from a simple Tkinter desktop GUI.

## Safety Promise

Tico Asset Builder treats your original ROM library as read-only.

- It does not rename, delete, move, or overwrite files in the source library.
- It writes prepared ROMs, resized cover assets, and reports only to output folders you choose.
- It refuses some dangerous output locations, such as writing directly into `source/roms`.
- Dry runs inspect what would happen without extracting ROMs or creating prepared output folders.

## No ROMs Or Copyrighted Artwork

This repository should not contain ROMs, BIOS files, copyrighted cover art, copied ROM libraries, generated reports, or generated output folders.

Tests use fake placeholder ROM files and generated Pillow images only.

## What It Does

- Prepares zipped ROM libraries into extracted ROM-only folders.
- Finds existing local artwork on your machine.
- Converts matched artwork to `512x512` JPG covers.
- Creates Tico-compatible `tico/roms/` and `tico/assets/covers/` folders.
- Writes CSV reports so you can review what happened.
- Provides a beginner-friendly GUI for the same local workflows.

## What It Does Not Do

- No scraping.
- No online artwork lookup.
- No ROM downloads.
- No BIOS handling.
- No source-library modification.
- No copied source artwork inside `tico/roms/{console}/images/`.

## Installation For Normal Users

From this project folder:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
```

If you are offline and dependencies are already installed in `.venv`, this local fallback can help:

```bash
python -m pip install --no-build-isolation --no-deps .
```

## Recommended Simple Workflow

Build one clean Tico-compatible folder:

```bash
source .venv/bin/activate
tico-build-tico-folder my-library --output my-library-tico-output --style fit
```

Result:

```text
my-library-tico-output/
  tico/
    roms/
      gb/
        Tetris.gb
    assets/
      covers/
        gb/
          Tetris.jpg
    reports/
      prepared-roms.csv
      skipped-archives.csv
  reports/
    detected-games.csv
    matched-covers.csv
    missing-covers.csv
    skipped-files.csv
```

This is the easiest path for normal users. It prepares ROMs into `tico/roms/`, builds resized covers into `tico/assets/covers/`, and leaves the original library untouched.

## Advanced Separate Workflows

### ROM-only prep

```bash
tico-prepare-roms my-library --output my-library-tico-prepared
```

Creates:

```text
my-library-tico-prepared/
  roms/{console}/Game.ext
  reports/
```

Prepared ROM output contains ROMs only. It does not copy `images/`, `imgs/`, `covers/`, `boxart/`, or other source artwork folders.

### Cover-assets-only build

```bash
tico-asset-builder my-prepared-roms --artwork-source my-original-library --output my-cover-assets --style fit
```

Creates:

```text
my-cover-assets/
  tico/assets/covers/{console}/Game.jpg
  reports/
```

Use `--artwork-source` when ROMs are in one folder and artwork is still in the original library. If artwork is already near the ROM input folder, `--artwork-source` is optional.

## GUI Usage

Launch the GUI from normal Terminal on macOS:

```bash
source .venv/bin/activate
tico-asset-builder-gui
```

GUI tabs:

- **Prepare ROMs**: create ROM-only prepared folders.
- **Build Cover Assets**: create resized Tico cover assets, optionally using an artwork source folder.
- **Combined Tico Folder**: create one clean final Tico folder with ROMs and covers.
- **Reports**: view CSV reports and save a summary.
- **Log / Status**: watch progress, review messages, and request cancellation.

The GUI has smart default output folders, safety checks, progress feedback, a cancel button, and a report viewer. Launching Tkinter apps from inside Codex may crash on macOS; use normal Terminal for the GUI.

When you click **Analyze Library**, the GUI detects supported console folders from `SOURCE/roms/{console}/` or `SOURCE/{console}/` and builds the console checkbox list from the same backend console configuration used by the CLI. Detected systems are shown by default with counts for zipped ROMs, extracted ROMs, and local images. Unsupported folders are shown in the analysis summary but are not processed unless the backend supports them. Folder names should use supported system slugs such as `gb`, `gba`, `snes`, `psp`, `dc`, `saturn`, `wii`, `sega-cd`, `master-system`, `game-gear`, or `gc`.

## Input Folder Examples

Tico-style source:

```text
my-library/
  roms/
    gb/
      Tetris.zip
      images/
        Tetris.png
```

Already-extracted source:

```text
my-library/
  roms/
    gb/
      Tetris.gb
      images/
        Tetris.png
```

Plain console-folder source:

```text
my-library/
  gb/
    Tetris.gb
    images/
      Tetris.png
```

Common local artwork folder names include `images`, `imgs`, `covers`, `cover`, `boxart`, `box_art`, `box-art`, `media`, `thumbnails`, `thumbs`, `downloaded_images`, `artwork`, and `art`.

## Supported Folder Aliases

Canonical Tico/system slugs remain the output folder names, but input folders can use common aliases. For example:

- `SFC`, `Super Nintendo`, `Super Famicom` -> `snes`
- `Mega Drive`, `Sega Genesis` -> `genesis`
- `PS1`, `PlayStation` -> `psx`
- `GameCube`, `Game Cube`, `GCN` -> `gc`
- `Game Boy`, `GameBoy`, `DMG` -> `gb`
- `Game Boy Color` -> `gbc`
- `Game Boy Advance` -> `gba`
- `Dreamcast` -> `dc`
- `Sega CD`, `Mega CD` -> `sega-cd`
- `Master System` -> `master-system`
- `Game Gear` -> `game-gear`
- `PlayStation Portable` -> `psp`
- `Nintendo Wii` -> `wii`

The app normalizes spaces, underscores, dots, hyphens, brackets, and generic words such as `roms`, `games`, `no-intro`, and `redump` before matching folder names. Exact aliases are preferred. Conservative fuzzy matching is used only for longer, high-confidence, unambiguous names; short names such as `gb`, `gg`, `dc`, `md`, `fc`, `gc`, and `sms` are never guessed fuzzily.

Output always uses canonical folders. For example, `roms/SFC/ActRaiser.zip` outputs to `tico/roms/snes/ActRaiser.sfc` and `tico/assets/covers/snes/ActRaiser.jpg`.

Unsupported folders are reported but not processed. More aliases can be requested through issues or pull requests.

## Cover Styles

All final covers are saved as `512x512` JPG files.

- `fit`: preserves the full image and adds black padding if needed.
- `crop`: fills the square by trimming edges.
- `stretch`: resizes directly to a square, which may distort the image.

Default:

```bash
--style fit
```

## Reports

Prep reports are written to `OUTPUT/tico/reports/` for combined output, or `PREPARED_OUTPUT/reports/` for ROM-only prep.

- `prepared-roms.csv`: zip archives or extracted source ROMs that were prepared into the output.
- `skipped-archives.csv`: archive contents skipped during ROM prep, including junk files or invalid zips.

Asset reports are written to `OUTPUT/reports/`.

- `detected-games.csv`: ROMs found by the asset builder.
- `matched-covers.csv`: ROMs that matched local artwork, including source artwork path and output cover path.
- `missing-covers.csv`: ROMs that need artwork fixes.
- `skipped-files.csv`: unsupported files ignored by the scanner.
- `summary.txt`: optional GUI-generated summary of report counts.

## Troubleshooting

### 0 games detected

Check that your ROMs are under `roms/{console}/` or `{console}/`, and that the console folder name is supported.

### My ROMs are .zip files

Use the combined workflow or ROM prep command. The asset builder does not treat `.zip` files as playable games.

```bash
tico-build-tico-folder my-library --output my-library-tico-output --style fit
```

### Images in prepared ROM folders are not resized

Prepared ROM folders intentionally contain ROMs only. Source artwork is not copied there.

### Where are the final resized covers?

Look in:

```text
OUTPUT/tico/assets/covers/{console}/
```

### Missing covers report is not empty

Open `missing-covers.csv`. Add or rename local artwork in your source library, then run the builder again. The project intentionally uses local artwork only.

### GUI does not show newest changes

Refresh the install:

```bash
source .venv/bin/activate
python -m pip install --no-build-isolation --no-deps .
```

### macOS/Tkinter GUI crashed when launched from Codex

Launch from normal Terminal instead:

```bash
source .venv/bin/activate
tico-asset-builder-gui
```

### The GUI window is too tall or cramped

The GUI uses tabs to fit smaller screens. If it still feels cramped, resize the window and use the **Build Cover Assets**, **Reports**, and **Log / Status** tabs separately.

### Output folder already exists

Some commands refuse to write into a non-empty output folder unless `--overwrite` is provided. Choose an empty output folder when possible.

### Why no images folder appears inside tico/roms/

That is expected. `tico/roms/` contains ROM files only. Final resized covers are in `tico/assets/covers/`.

## Installation For Developers

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e . pytest
```

Run tests:

```bash
python -m pytest
python -m pytest tests/test_stress_workflows.py
```

The stress tests use fake ROM placeholder files and generated artwork only.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor guidelines.

## Known Limitations

- `.zip` prep is supported; `.7z` and `.rar` extraction are not supported yet.
- Artwork matching is local-only.
- No scraping or online lookup.
- GUI uses Tkinter.
- Output is designed around current Tico folder assumptions.
- Disc and multi-disc systems may need more real-world testing.

## Contributing

Issues and pull requests are welcome. Please do not upload ROMs, BIOS files, copyrighted artwork, generated output folders, or private folder listings.

Before opening a pull request:

```bash
source .venv/bin/activate
python -m pytest
```

## License

MIT License. See [LICENSE](LICENSE).

## Disclaimer

Tico Asset Builder does not provide ROMs, BIOS files, copyrighted artwork, scraping, or download features. You are responsible for using the tool only with files you have the right to use.
