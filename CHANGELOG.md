# Changelog

## 0.1.0

Initial local-first release preparation.

### Added

- ROM prep command: `tico-prepare-roms`
- Cover asset builder command: `tico-asset-builder`
- Combined output command: `tico-build-tico-folder`
- Tkinter GUI command: `tico-asset-builder-gui`
- Local image matching across common artwork folder names
- Optional `--artwork-source` for separate ROM and artwork folders
- CSV reports for prepared ROMs, skipped archives, detected games, matched covers, missing covers, and skipped files
- GUI report viewer, summary counts, progress feedback, cancellation, safety checks, and smart output folder suggestions
- Stress tests using fake ROM placeholders and generated artwork

### Safety

- Source ROM libraries are treated as read-only.
- Prepared ROM output contains ROMs only.
- Cover asset output contains resized `512x512` JPG covers only.
- Combined output avoids copying source artwork into `tico/roms/`.
- Fuzzy matching rejects numbered-game matches when numeric tokens differ.
