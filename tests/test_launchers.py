from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
LAUNCHERS = (
    "launch_tico_asset_builder.command",
    "launch_tico_asset_builder.bat",
    "launch_tico_asset_builder.sh",
)


def test_launcher_files_exist() -> None:
    for launcher in LAUNCHERS:
        assert (ROOT / launcher).is_file()


def test_launchers_prefer_modern_gui_and_fallback_to_stable_gui() -> None:
    for launcher in LAUNCHERS:
        text = (ROOT / launcher).read_text(encoding="utf-8")
        assert "tico-asset-builder-modern-gui" in text
        assert "tico-asset-builder-gui" in text
        assert "modern-gui" in text


def test_readme_mentions_double_click_launchers() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Double-click launchers" in readme
    for launcher in LAUNCHERS:
        assert launcher in readme
