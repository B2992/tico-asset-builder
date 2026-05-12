# Security Policy

Tico Asset Builder is a local utility. It does not upload ROMs, artwork, reports, or folder contents.

## Reporting Issues

If you find a safety or security issue, open a GitHub issue with a minimal description and safe reproduction steps.

Do not attach:

- ROM files
- BIOS files
- copyrighted artwork
- private folder listings
- generated outputs containing personal paths, unless you have cleaned them first

Safe bug reports can include:

- OS and Python version
- command used
- sanitized CSV report snippets
- fake filenames that reproduce the issue
- screenshots of the GUI with private paths hidden

## Safety Expectations

The tool should never modify source libraries in place. If you see behavior that renames, deletes, moves, or overwrites source files, report it as a safety bug.
