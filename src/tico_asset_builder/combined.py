"""Combined workflow for one clean Tico-compatible output folder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .builder import BuildResult, build_assets
from .prep import PrepResult, prepare_roms


@dataclass(frozen=True)
class CombinedBuildResult:
    prep: PrepResult
    assets: BuildResult | None

    @property
    def cancelled(self) -> bool:
        return self.prep.cancelled or bool(self.assets and self.assets.cancelled)


def build_tico_folder(
    source_library: Path,
    final_output: Path,
    style: str,
    threshold: int = 88,
    consoles: list[str] | None = None,
    overwrite: bool = False,
    progress_callback=None,
    cancel_check=None,
) -> CombinedBuildResult:
    """Prepare ROMs and build covers into one final Tico folder.

    The original source library is used as the artwork source while ROMs are
    prepared into ``final_output/tico``. That keeps ``tico/roms`` clean: ROMs
    only, no copied source artwork folders.
    """
    issue = validate_combined_output_path(source_library, final_output)
    if issue:
        raise ValueError(issue)
    if final_output.exists() and any(final_output.iterdir()) and not overwrite:
        raise ValueError("Final output folder already exists and is not empty. Choose an empty folder or use --overwrite.")

    prepared_root = final_output / "tico"
    prep_result = prepare_roms(
        input_folder=source_library,
        output_folder=prepared_root,
        overwrite=overwrite,
        consoles=consoles,
        include_extracted=True,
        progress_callback=progress_callback,
        cancel_check=cancel_check,
    )
    if prep_result.cancelled or (cancel_check and cancel_check()):
        return CombinedBuildResult(prep=prep_result, assets=None)

    asset_result = build_assets(
        input_path=prepared_root,
        output_root=final_output,
        style=style,
        threshold=threshold,
        artwork_sources=[source_library],
        progress_callback=progress_callback,
        cancel_check=cancel_check,
    )
    return CombinedBuildResult(prep=prep_result, assets=asset_result)


def validate_combined_output_path(source_library: Path, final_output: Path) -> str | None:
    """Return a beginner-friendly safety error for risky output locations."""
    source = source_library.expanduser().resolve()
    output = final_output.expanduser().resolve()
    if output == source:
        return "Choose a final Tico output folder that is separate from the source library."

    source_roms = source / "roms"
    try:
        output.relative_to(source_roms)
    except ValueError:
        pass
    else:
        return "Choose a final Tico output folder outside the source library's roms folder."
    return None
