# Contributing

Thanks for helping improve Tico Asset Builder. This project is local-first and safety-first: it reads source libraries and writes only to chosen output folders.

## Local Setup

Use Python 3.12 when possible.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e . pytest
```

If you are working offline and build isolation cannot fetch build tools, use:

```bash
python -m pip install --no-build-isolation --no-deps .
```

## Running Tests

```bash
source .venv/bin/activate
python -m pytest
python -m pytest tests/test_stress_workflows.py
```

The stress tests use fake ROM placeholder files and generated artwork only.

## Coding Style

- Keep changes small and focused.
- Prefer existing project patterns over new abstractions.
- Add tests for behavior changes.
- Use clear names and short comments for non-obvious safety decisions.
- Do not add scraping, downloads, telemetry, or online features without explicit project agreement.

## Safety Rules

- Never modify source ROM libraries in place.
- Write prepared ROMs, cover assets, and reports only to user-selected output folders.
- Do not commit ROMs, BIOS files, copyrighted cover art, local test libraries, generated reports, or output folders.
- Use fake placeholder ROM files and generated images in tests.

## Pull Requests

Before opening a PR:

- Run `python -m pytest`.
- Confirm no ROMs, BIOS files, copyrighted artwork, or generated outputs are included.
- Update README or tests when behavior changes.
- Explain how source-library safety is preserved.
