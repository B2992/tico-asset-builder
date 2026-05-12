"""Optional CustomTkinter GUI for a more modern desktop experience."""

from __future__ import annotations

import threading
import sys
from pathlib import Path
from tkinter import filedialog, messagebox

from .builder import build_assets
from .combined import build_tico_folder, validate_combined_output_path
from .gui import (
    COVER_STYLES,
    REPORT_DEFINITIONS,
    analyze_library,
    console_checkbox_label,
    console_keys_for_analysis,
    format_library_analysis,
    format_prepare_summary,
    format_summary_text,
    load_csv_report,
    select_detected_console_keys,
    suggest_asset_output_folder,
    suggest_combined_output_folder,
    suggest_prepared_output_folder,
    summarize_reports,
    validate_asset_output_path,
    validate_prepare_output_path,
    _should_apply_suggestion,
)
from .prep import prepare_roms

try:  # CustomTkinter is optional so the stable Tkinter GUI can keep working.
    import customtkinter as ctk
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    ctk = None


MODERN_GUI_COMMAND = "tico-asset-builder-modern-gui"
_ModernBase = ctk.CTk if ctk is not None else object
MODERN_GUI_HELP = f"""Tico Asset Builder modern desktop GUI.

Usage:
  {MODERN_GUI_COMMAND}

Launches the optional CustomTkinter interface.
Install with:
  python -m pip install -e ".[modern-gui]"
"""

# Tico-inspired original companion palette. Do not copy Tico assets; use cyan
# only as the primary active/action accent, with small status-dot colors.
APP_BG = "#171A1F"
PAGE_BG = "#1E222A"
SIDEBAR_BG = "#141821"
CARD_BG = "#242936"
ALT_CARD_BG = "#2B3140"
FIELD_BG = "#303645"
BORDER_COLOR = "#3B4354"
PRIMARY_TEXT = "#F3F5F8"
SECONDARY_TEXT = "#C2C8D2"
MUTED_TEXT = "#8F98A8"
BUTTON_BG = "#303645"
BUTTON_HOVER = "#3A4254"
QUIET_BUTTON_BG = "#242936"
QUIET_BUTTON_HOVER = "#2B3140"
ACCENT = "#19C7E8"
ACCENT_HOVER = "#34D8F3"
ACCENT_SOFT = "#8EEBFF"
ACCENT_DARK = "#123744"
DOT_CORAL = "#FF9A7A"
DOT_YELLOW = "#FFE66B"
DOT_GREEN = "#3EF071"
SUCCESS = "#3EF071"
WARNING = "#FFE66B"
ERROR = "#FF6F7D"
DANGER = "#6F2930"

CARD_RADIUS = 18
CONTROL_RADIUS = 10
PAGE_PAD = 24
CARD_PAD_X = 20
CARD_PAD_Y = 16
SECTION_GAP = 16
FIELD_HEIGHT = 38
BUTTON_HEIGHT = 38

BUTTON_ROLE_STYLES = {
    "primary": {"fg_color": ACCENT, "hover_color": ACCENT_HOVER, "text_color": PRIMARY_TEXT},
    "secondary": {"fg_color": BUTTON_BG, "hover_color": BUTTON_HOVER, "text_color": PRIMARY_TEXT},
    "quiet": {"fg_color": QUIET_BUTTON_BG, "hover_color": QUIET_BUTTON_HOVER, "text_color": SECONDARY_TEXT},
    "danger": {"fg_color": DANGER, "hover_color": ERROR, "text_color": PRIMARY_TEXT},
}

RAW_TK_BACKGROUND_OPTIONS = {
    "bg": PAGE_BG,
    "background": PAGE_BG,
    "highlightbackground": PAGE_BG,
    "highlightcolor": PAGE_BG,
}

MODERN_GUI_PAGES = (
    "Build Complete Tico Folder",
    "Extract ROMs Only",
    "Build Covers Only",
    "Reports",
    "Log / Status",
)
NAVIGATION_USES_STACKED_PAGES = True


def customtkinter_available() -> bool:
    return ctk is not None


def button_grid_position(index: int, max_columns: int) -> tuple[int, int]:
    """Return a wrapped row/column position for responsive button groups."""
    return index // max_columns, index % max_columns


def is_redundant_navigation(requested_page: str, current_page: str | None) -> bool:
    """Return True when a sidebar click targets the page already on screen."""
    return requested_page == current_page


def themed_raw_background_options(color: str = PAGE_BG) -> dict[str, str | int]:
    """Return Tk background options used to mask default gray redraw surfaces."""
    return {
        "bg": color,
        "background": color,
        "highlightbackground": color,
        "highlightcolor": color,
        "borderwidth": 0,
        "highlightthickness": 0,
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if any(arg in {"-h", "--help"} for arg in args):
        print(MODERN_GUI_HELP)
        return 0

    if ctk is None:
        print(
            "CustomTkinter is not installed. Install project dependencies, then run "
            f"{MODERN_GUI_COMMAND} again."
        )
        return 1

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = ModernTicoApp()
    app.mainloop()
    return 0


class ModernTicoApp(_ModernBase):  # pragma: no cover - GUI exercised manually
    def __init__(self) -> None:
        super().__init__()
        self.title("Tico Asset Builder")
        self.geometry("1050x700")
        self.minsize(850, 600)
        self.configure(fg_color=APP_BG)
        self._theme_raw_widget_background(self, APP_BG)
        root = getattr(self, "_root", None)
        if root is not None:
            self._theme_raw_widget_background(root, APP_BG)

        self.source_library = ctk.StringVar()
        self.prepared_output = ctk.StringVar()
        self.prepared_input = ctk.StringVar()
        self.asset_output = ctk.StringVar()
        self.artwork_source = ctk.StringVar()
        self.final_output = ctk.StringVar()
        self.cover_style = ctk.StringVar(value="fit")
        self.combined_style = ctk.StringVar(value="fit")
        self.dry_run = ctk.BooleanVar(value=False)

        self._last_prepared_output_suggestion = ""
        self._last_asset_output_suggestion = ""
        self._last_artwork_source_suggestion = ""
        self._last_combined_output_suggestion = ""
        self._last_analysis = None
        self._console_vars: dict[str, object] = {}
        self._console_checks: list[object] = []
        self._console_selection_changed_by_user = False
        self._cancel_requested = threading.Event()
        self._task_running = False
        self.nav_buttons: dict[str, object] = {}
        self._summary_labels: dict[str, object] = {}
        self.current_page: str | None = None

        self._build_shell()

    def _build_shell(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=SIDEBAR_BG)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(10, weight=1)
        ctk.CTkLabel(
            sidebar,
            text="Tico Asset\nBuilder",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=PRIMARY_TEXT,
            justify="left",
        ).grid(
            row=0, column=0, padx=22, pady=(26, 8), sticky="w"
        )
        ctk.CTkLabel(
            sidebar,
            text="Build Tico-ready libraries.",
            text_color=SECONDARY_TEXT,
            wraplength=190,
            justify="left",
        ).grid(row=1, column=0, padx=22, pady=(0, 24), sticky="w")

        self.content = ctk.CTkFrame(self, fg_color=PAGE_BG, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self._theme_raw_widget_background(self.content, PAGE_BG)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        self.page_host = ctk.CTkFrame(self.content, fg_color=PAGE_BG, corner_radius=0)
        self.page_host.grid(row=0, column=0, sticky="nsew")
        self.page_host.grid_columnconfigure(0, weight=1)
        self.page_host.grid_rowconfigure(0, weight=1)
        self._theme_raw_widget_background(self.page_host, PAGE_BG)

        self.pages: dict[str, object] = {}
        ctk.CTkLabel(sidebar, text="WORKFLOWS", text_color=MUTED_TEXT, font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=2, column=0, padx=22, pady=(2, 6), sticky="w"
        )
        nav = [
            (MODERN_GUI_PAGES[0], self._build_complete_page),
            (MODERN_GUI_PAGES[1], self._build_extract_page),
            (MODERN_GUI_PAGES[2], self._build_covers_page),
        ]
        for index, (name, builder) in enumerate(nav, start=3):
            self._add_nav_button(sidebar, index, name)
            page = builder()
            self.pages[name] = getattr(page, "_tico_page_shell", page)

        ctk.CTkLabel(sidebar, text="TOOLS", text_color=MUTED_TEXT, font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=6, column=0, padx=22, pady=(20, 6), sticky="w"
        )
        tool_nav = [
            (MODERN_GUI_PAGES[3], self._build_reports_page),
            (MODERN_GUI_PAGES[4], self._build_log_page),
        ]
        for index, (name, builder) in enumerate(tool_nav, start=7):
            self._add_nav_button(sidebar, index, name)
            page = builder()
            self.pages[name] = getattr(page, "_tico_page_shell", page)

        self._show_page(MODERN_GUI_PAGES[0])

    def _add_nav_button(self, parent, row: int, name: str) -> None:
        button = ctk.CTkButton(
            parent,
            text=name,
            anchor="w",
            height=BUTTON_HEIGHT,
            corner_radius=CONTROL_RADIUS,
            fg_color=QUIET_BUTTON_BG,
            hover_color=QUIET_BUTTON_HOVER,
            text_color=SECONDARY_TEXT,
            command=lambda page=name: self._show_page(page),
        )
        button.grid(row=row, column=0, padx=16, pady=5, sticky="ew")
        self.nav_buttons[name] = button

    def _page(self) -> object:
        shell = ctk.CTkFrame(self.page_host, fg_color=PAGE_BG, corner_radius=0)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(0, weight=1)
        self._theme_raw_widget_background(shell, PAGE_BG)
        page = ctk.CTkScrollableFrame(
            shell,
            fg_color=PAGE_BG,
            scrollbar_button_color=BUTTON_BG,
            scrollbar_button_hover_color=BUTTON_HOVER,
        )
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)
        page._tico_page_shell = shell
        self._theme_scrollable_page(page)
        return page

    def _theme_raw_widget_background(self, widget, color: str = PAGE_BG) -> None:
        options = themed_raw_background_options(color)
        for option, value in options.items():
            try:
                widget.configure(**{option: value})
            except Exception:
                pass

    def _theme_scrollable_page(self, page) -> None:
        # CTkScrollableFrame uses an internal Tk canvas; if left at the Tk
        # default background, macOS can flash gray/brown while pages repaint.
        self._theme_raw_widget_background(page, PAGE_BG)
        for attr in ("_parent_canvas", "_canvas"):
            canvas = getattr(page, attr, None)
            if canvas is not None:
                self._theme_raw_widget_background(canvas, PAGE_BG)

    def _page_header(self, page, title: str, description: str, eyebrow: str = "") -> None:
        if eyebrow:
            ctk.CTkLabel(page, text=eyebrow.upper(), text_color=ACCENT, font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=0, column=0, padx=PAGE_PAD, pady=(PAGE_PAD, 4), sticky="w"
            )
        ctk.CTkLabel(page, text=title, text_color=PRIMARY_TEXT, font=ctk.CTkFont(size=28, weight="bold")).grid(
            row=1, column=0, padx=PAGE_PAD, pady=(0, 4), sticky="w"
        )
        ctk.CTkLabel(page, text=description, text_color=SECONDARY_TEXT, wraplength=780, justify="left").grid(
            row=2, column=0, padx=PAGE_PAD, pady=(0, SECTION_GAP), sticky="w"
        )

    def _card(self, parent, title: str, subtitle: str = "", tone: str = "default"):
        color = ALT_CARD_BG if tone == "alternate" else CARD_BG
        card = ctk.CTkFrame(parent, fg_color=color, corner_radius=CARD_RADIUS, border_color=BORDER_COLOR, border_width=1)
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text=title, text_color=PRIMARY_TEXT, font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=3, padx=CARD_PAD_X, pady=(CARD_PAD_Y, 2), sticky="w"
        )
        if subtitle:
            ctk.CTkLabel(card, text=subtitle, text_color=MUTED_TEXT, wraplength=760).grid(
                row=1, column=0, columnspan=3, padx=CARD_PAD_X, pady=(0, 12), sticky="w"
            )
        return card

    def _folder_row(self, parent, row: int, label: str, variable, button: str, command=None) -> None:
        ctk.CTkLabel(parent, text=label, text_color=SECONDARY_TEXT).grid(
            row=row, column=0, padx=CARD_PAD_X, pady=8, sticky="w"
        )
        ctk.CTkEntry(
            parent,
            textvariable=variable,
            height=FIELD_HEIGHT,
            fg_color=FIELD_BG,
            border_color=BORDER_COLOR,
            corner_radius=CONTROL_RADIUS,
        ).grid(
            row=row, column=1, padx=8, pady=8, sticky="ew"
        )
        self._button(parent, button, command or (lambda: self._choose_folder(variable)), role="quiet", width=120).grid(
            row=row, column=2, padx=CARD_PAD_X, pady=8, sticky="e"
        )

    def _output_preview(self, parent, row: int, title: str, lines: list[str]) -> None:
        preview = ctk.CTkFrame(parent, fg_color=FIELD_BG, corner_radius=CONTROL_RADIUS, border_color=BORDER_COLOR, border_width=1)
        preview.grid(row=row, column=0, columnspan=3, padx=CARD_PAD_X, pady=(4, CARD_PAD_Y), sticky="ew")
        ctk.CTkLabel(preview, text=title, text_color=MUTED_TEXT, font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, padx=14, pady=(12, 0), sticky="w"
        )
        ctk.CTkLabel(
            preview,
            text="\n".join(lines),
            text_color=SECONDARY_TEXT,
            font=ctk.CTkFont(family="Menlo", size=13),
            justify="left",
        ).grid(row=1, column=0, padx=14, pady=(4, 12), sticky="w")

    def _button(self, parent, text: str, command, role: str = "secondary", width: int | None = None):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            height=BUTTON_HEIGHT,
            corner_radius=CONTROL_RADIUS,
            width=width or 170,
            **BUTTON_ROLE_STYLES[role],
        )

    def _button_row(self, parent, buttons: list[tuple[str, object, str, int]], max_columns: int = 3) -> object:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        for index, (text, command, role, width) in enumerate(buttons):
            grid_row, grid_column = button_grid_position(index, max_columns)
            self._button(row, text, command, role=role, width=width).grid(
                row=grid_row,
                column=grid_column,
                padx=(0, 8),
                pady=4,
                sticky="w",
            )
        return row

    def _textbox(self, parent, height: int):
        return ctk.CTkTextbox(
            parent,
            height=height,
            fg_color=FIELD_BG,
            border_color=BORDER_COLOR,
            border_width=1,
            corner_radius=CONTROL_RADIUS,
            text_color=SECONDARY_TEXT,
        )

    def _build_complete_page(self):
        page = self._page()
        self._page_header(
            page,
            "Build Complete Tico Folder",
            "Recommended. Creates a clean Tico-ready folder with ROMs and cover assets.",
            "Start here",
        )
        source_card = self._card(
            page,
            "Source Library",
            "Choose your existing ROM/artwork library. It stays untouched.",
            tone="alternate",
        )
        source_card.grid(row=3, column=0, padx=PAGE_PAD, pady=(0, SECTION_GAP), sticky="ew")
        self._folder_row(source_card, 2, "Source library folder", self.source_library, "Choose", self._choose_source_library)

        output_card = self._card(page, "Final Tico Output", "This is the folder you copy/use with Tico.", tone="alternate")
        output_card.grid(row=4, column=0, padx=PAGE_PAD, pady=(0, SECTION_GAP), sticky="ew")
        self._folder_row(output_card, 2, "Final Tico folder to copy/use", self.final_output, "Choose")
        self._output_preview(output_card, 3, "Output preview", ["final-output/", "  tico/", "    roms/", "    assets/covers/"])

        style_card = self._card(page, "Cover Style", "Fit is safest. Crop fills the square. Stretch may distort.")
        style_card.grid(row=5, column=0, padx=PAGE_PAD, pady=(0, SECTION_GAP), sticky="ew")
        self._style_row(style_card, 2, self.combined_style)
        self._button_row(
            style_card,
            [
                ("Analyze Library", self.analyze_source_library, "secondary", 165),
                ("Build Complete Tico Folder", self.build_combined_tico_folder, "primary", 230),
            ],
            max_columns=2,
        ).grid(row=3, column=0, columnspan=3, padx=CARD_PAD_X, pady=(12, CARD_PAD_Y), sticky="w")
        result_card = self._card(page, "Status", "Short messages from analysis and build runs.")
        result_card.grid(row=6, column=0, padx=PAGE_PAD, pady=(0, PAGE_PAD), sticky="ew")
        self.analysis_box = self._textbox(result_card, height=130)
        self.analysis_box.grid(row=2, column=0, columnspan=3, padx=CARD_PAD_X, pady=(4, CARD_PAD_Y), sticky="ew")
        self._set_textbox(self.analysis_box, "Choose a source library, then click Analyze Library.")
        return page

    def _build_extract_page(self):
        page = self._page()
        self._page_header(
            page,
            "Advanced: Extract ROMs Only",
            "Advanced. Creates extracted ROMs only. No cover assets are created.",
            "Advanced workflow",
        )
        source_card = self._card(page, "Source", "Original libraries are read-only. Extraction writes only to the output folder.")
        source_card.grid(row=3, column=0, padx=PAGE_PAD, pady=(0, SECTION_GAP), sticky="ew")
        self._folder_row(source_card, 2, "Source library folder", self.source_library, "Choose", self._choose_source_library)

        settings_card = self._card(page, "Output and Preview", "Prepared output contains ROM files only.")
        settings_card.grid(row=4, column=0, padx=PAGE_PAD, pady=(0, SECTION_GAP), sticky="ew")
        self._folder_row(settings_card, 2, "Prepared ROMs-only output folder", self.prepared_output, "Choose")
        ctk.CTkCheckBox(
            settings_card,
            text="Dry run: preview only, no output folder",
            variable=self.dry_run,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            border_color=BORDER_COLOR,
        ).grid(
            row=3, column=0, columnspan=3, padx=CARD_PAD_X, pady=(8, CARD_PAD_Y), sticky="w"
        )

        systems_card = self._card(page, "Systems to Process", "Analyze the source library to show detected systems.")
        systems_card.grid(row=5, column=0, padx=PAGE_PAD, pady=(0, PAGE_PAD), sticky="ew")
        self.console_frame = ctk.CTkFrame(systems_card, fg_color=FIELD_BG, corner_radius=CONTROL_RADIUS, border_color=BORDER_COLOR, border_width=1)
        self.console_frame.grid(row=2, column=0, columnspan=3, padx=CARD_PAD_X, pady=8, sticky="ew")
        self._render_console_checks([])
        self._button_row(
            systems_card,
            [
                ("Select All", self.select_all_consoles, "quiet", 110),
                ("Clear All", self.clear_all_consoles, "quiet", 110),
                ("Select Detected Only", self.select_detected_consoles, "secondary", 170),
                ("Show All Supported", self.show_all_supported_consoles, "quiet", 160),
            ],
            max_columns=3,
        ).grid(row=3, column=0, columnspan=3, padx=CARD_PAD_X, pady=(8, 4), sticky="w")
        self._button_row(
            systems_card,
            [("Extract ROMs Only", self.prepare_roms, "primary", 180)],
            max_columns=1,
        ).grid(row=4, column=0, columnspan=3, padx=CARD_PAD_X, pady=(2, CARD_PAD_Y), sticky="w")
        return page

    def _build_covers_page(self):
        page = self._page()
        self._page_header(
            page,
            "Advanced: Build Covers Only",
            "Advanced. Creates resized cover assets only. No ROMs are extracted or copied.",
            "Advanced workflow",
        )
        paths_card = self._card(
            page,
            "Folders",
            "Use an optional original artwork/source folder when cover images live outside the prepared ROM folder.",
        )
        paths_card.grid(row=3, column=0, padx=PAGE_PAD, pady=(0, SECTION_GAP), sticky="ew")
        self._folder_row(paths_card, 2, "Prepared ROM folder", self.prepared_input, "Choose", self._choose_prepared_input)
        self._folder_row(paths_card, 3, "Covers-only output folder", self.asset_output, "Choose")
        self._folder_row(paths_card, 4, "Original artwork/source folder, optional", self.artwork_source, "Choose")
        options_card = self._card(page, "Cover Options", "Final covers are always written as 512x512 JPG files.")
        options_card.grid(row=4, column=0, padx=PAGE_PAD, pady=(0, PAGE_PAD), sticky="ew")
        self._style_row(options_card, 2, self.cover_style)
        self._button(options_card, "Build Covers Only", self.build_assets, role="primary", width=180).grid(
            row=3, column=0, padx=CARD_PAD_X, pady=(12, CARD_PAD_Y), sticky="w"
        )
        return page

    def _build_reports_page(self):
        page = self._page()
        self._page_header(
            page,
            "Reports",
            "Review what was prepared, matched, missed, or skipped. Start with Missing Covers.",
            "Review",
        )
        summary_card = self._card(page, "Summary", "If Missing Covers is 0, your cover matching is complete.", tone="alternate")
        summary_card.grid(row=3, column=0, padx=PAGE_PAD, pady=(0, SECTION_GAP), sticky="ew")
        summary_keys = [
            ("Missing Covers", "missing_covers", DOT_YELLOW),
            ("Extracted ROMs", "prepared_roms", DOT_GREEN),
            ("Covers Found", "matched_covers", ACCENT),
            ("Ignored Files", "skipped_files", DOT_CORAL),
            ("Detected ROMs", "detected_games", MUTED_TEXT),
            ("Skipped Archives", "skipped_archives", DOT_YELLOW),
        ]
        for index, (label, key, dot_color) in enumerate(summary_keys):
            chip = ctk.CTkFrame(summary_card, fg_color=FIELD_BG, corner_radius=CONTROL_RADIUS, border_color=BORDER_COLOR, border_width=1)
            chip.grid(row=2 + index // 3, column=index % 3, padx=8, pady=8, sticky="ew")
            ctk.CTkLabel(chip, text="●", text_color=dot_color, font=ctk.CTkFont(size=13, weight="bold")).grid(
                row=0, column=0, padx=(12, 4), pady=(10, 0), sticky="w"
            )
            ctk.CTkLabel(chip, text=label, text_color=MUTED_TEXT, font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=0, column=1, padx=(0, 12), pady=(10, 0), sticky="w"
            )
            value = ctk.CTkLabel(chip, text="0", text_color=PRIMARY_TEXT, font=ctk.CTkFont(size=20, weight="bold"))
            value.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="w")
            self._summary_labels[key] = value

        self._button_row(
            summary_card,
            [
                ("Refresh Reports", self.refresh_reports, "secondary", 160),
                ("Save Summary", self.save_summary, "quiet", 150),
            ],
            max_columns=2,
        ).grid(row=4, column=0, columnspan=3, padx=CARD_PAD_X, pady=(8, CARD_PAD_Y), sticky="w")

        card = self._card(page, "Report Viewer", "CSV reports are still saved in the output folders.")
        card.grid(row=4, column=0, padx=PAGE_PAD, pady=(0, PAGE_PAD), sticky="nsew")
        self.report_box = self._textbox(card, height=360)
        self.report_box.grid(row=2, column=0, columnspan=3, padx=CARD_PAD_X, pady=(4, CARD_PAD_Y), sticky="nsew")
        return page

    def _build_log_page(self):
        page = self._page()
        self._page_header(page, "Log / Status", "Progress, warnings, and cancellation for the current run.", "Tools")
        card = self._card(page, "Run Status", "Longer tasks run in the background so the interface stays responsive.")
        card.grid(row=3, column=0, padx=PAGE_PAD, pady=(0, PAGE_PAD), sticky="nsew")
        self.progress = ctk.CTkProgressBar(card)
        self.progress.set(0)
        self.progress.grid(row=2, column=0, columnspan=2, padx=CARD_PAD_X, pady=8, sticky="ew")
        self._button(card, "Cancel", self.request_cancel, role="danger", width=120).grid(
            row=2, column=2, padx=CARD_PAD_X, pady=8, sticky="e"
        )
        self.log_box = self._textbox(card, height=420)
        self.log_box.grid(row=3, column=0, columnspan=3, padx=CARD_PAD_X, pady=(8, CARD_PAD_Y), sticky="nsew")
        self._log("Ready. Safety: your source library is read-only.")
        return page

    def _style_row(self, parent, row: int, variable) -> None:
        ctk.CTkLabel(parent, text="Cover style", text_color=SECONDARY_TEXT).grid(
            row=row, column=0, padx=CARD_PAD_X, pady=8, sticky="w"
        )
        ctk.CTkSegmentedButton(
            parent,
            values=list(COVER_STYLES),
            variable=variable,
            height=FIELD_HEIGHT,
            corner_radius=CONTROL_RADIUS,
            fg_color=FIELD_BG,
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
            unselected_color=BUTTON_BG,
            unselected_hover_color=BUTTON_HOVER,
        ).grid(
            row=row, column=1, padx=8, pady=8, sticky="w"
        )

    def _show_page(self, name: str) -> None:
        # Re-clicking the active page is intentionally a no-op. Avoiding that
        # extra grid/style work prevents a visible repaint flash on revisit.
        if is_redundant_navigation(name, self.current_page):
            return

        # Pages are stacked and kept mounted for the lifetime of the window.
        # Navigation only raises an existing shell; it never unmaps or rebuilds
        # page widgets, which avoids exposing a default Tk redraw surface.
        selected_page = self.pages[name]
        selected_page.tkraise()
        for page_name, button in self.nav_buttons.items():
            button.configure(
                fg_color=ACCENT_DARK if page_name == name else QUIET_BUTTON_BG,
                hover_color=BUTTON_HOVER if page_name == name else QUIET_BUTTON_HOVER,
                text_color=PRIMARY_TEXT if page_name == name else SECONDARY_TEXT,
            )
        self.current_page = name

    def _choose_folder(self, variable) -> None:
        folder = filedialog.askdirectory()
        if folder:
            variable.set(folder)

    def _choose_source_library(self) -> None:
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.source_library.set(folder)
        self.artwork_source.set(folder)
        self._suggest_outputs(Path(folder))

    def _choose_prepared_input(self) -> None:
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.prepared_input.set(folder)
        suggestion = suggest_asset_output_folder(Path(folder))
        if _should_apply_suggestion(self.asset_output.get(), self._last_asset_output_suggestion):
            self.asset_output.set(str(suggestion))
            self._last_asset_output_suggestion = str(suggestion)

    def _suggest_outputs(self, folder: Path) -> None:
        prepared = suggest_prepared_output_folder(folder)
        final = suggest_combined_output_folder(folder)
        if _should_apply_suggestion(self.prepared_output.get(), self._last_prepared_output_suggestion):
            self.prepared_output.set(str(prepared))
            self._last_prepared_output_suggestion = str(prepared)
        if _should_apply_suggestion(self.final_output.get(), self._last_combined_output_suggestion):
            self.final_output.set(str(final))
            self._last_combined_output_suggestion = str(final)

    def analyze_source_library(self) -> None:
        source = self.source_library.get().strip()
        if not source:
            self._warn("Choose a source library folder first.")
            return
        analysis = analyze_library(Path(source))
        self._last_analysis = analysis
        self._set_textbox(self.analysis_box, format_library_analysis(analysis))
        self._render_console_checks(console_keys_for_analysis(analysis), analysis)
        if not self._console_selection_changed_by_user:
            self._set_console_selection(select_detected_console_keys(analysis))
        self._log("Analyzed source library.")

    def _render_console_checks(self, console_keys: list[str], analysis=None) -> None:
        for child in self.console_frame.winfo_children():
            child.destroy()
        self._console_checks = []
        if not console_keys:
            ctk.CTkLabel(
                self.console_frame,
                text="Analyze a source library to show detected systems.",
                text_color=MUTED_TEXT,
            ).grid(
                row=0, column=0, padx=12, pady=10, sticky="w"
            )
            return
        for index, console in enumerate(console_keys):
            variable = self._console_vars.setdefault(console, ctk.BooleanVar(value=False))
            chip = ctk.CTkFrame(
                self.console_frame,
                fg_color=CARD_BG,
                corner_radius=CONTROL_RADIUS,
                border_color=BORDER_COLOR,
                border_width=1,
            )
            chip.grid(row=index // 2, column=index % 2, padx=8, pady=8, sticky="ew")
            self.console_frame.grid_columnconfigure(index % 2, weight=1)
            check = ctk.CTkCheckBox(
                chip,
                text=console_checkbox_label(console, analysis),
                variable=variable,
                fg_color=ACCENT,
                hover_color=ACCENT_HOVER,
                border_color=BORDER_COLOR,
                text_color=SECONDARY_TEXT,
                command=self._mark_console_selection_changed,
            )
            check.grid(row=0, column=0, padx=12, pady=10, sticky="w")
            self._console_checks.append(check)

    def _mark_console_selection_changed(self) -> None:
        self._console_selection_changed_by_user = True

    def _selected_consoles(self) -> list[str]:
        return [console for console, variable in self._console_vars.items() if variable.get()]

    def _set_console_selection(self, selected: list[str]) -> None:
        selected_set = set(selected)
        for console, variable in self._console_vars.items():
            variable.set(console in selected_set)

    def select_all_consoles(self) -> None:
        self._console_selection_changed_by_user = True
        self._set_console_selection(list(self._console_vars))

    def clear_all_consoles(self) -> None:
        self._console_selection_changed_by_user = True
        self._set_console_selection([])

    def select_detected_consoles(self) -> None:
        self._console_selection_changed_by_user = True
        if not self._last_analysis:
            self._warn("Analyze a source library before selecting detected systems.")
            return
        self._render_console_checks(console_keys_for_analysis(self._last_analysis), self._last_analysis)
        self._set_console_selection(select_detected_console_keys(self._last_analysis))

    def show_all_supported_consoles(self) -> None:
        self._render_console_checks(console_keys_for_analysis(self._last_analysis, show_all_supported=True), self._last_analysis)

    def prepare_roms(self) -> None:
        source = self.source_library.get().strip()
        output = self.prepared_output.get().strip()
        if not source or not output:
            self._warn("Choose a source library and prepared ROMs-only output folder first.")
            return
        issue = validate_prepare_output_path(Path(source), Path(output))
        if issue:
            self._warn(issue)
            return
        self._run_task(lambda: self._prepare_task(Path(source), Path(output)))

    def _prepare_task(self, source: Path, output: Path) -> None:
        result = prepare_roms(source, output, dry_run=self.dry_run.get(), consoles=self._selected_consoles())
        for line in format_prepare_summary(result, self.dry_run.get()):
            self._log(line)

    def build_assets(self) -> None:
        prepared = self.prepared_input.get().strip()
        output = self.asset_output.get().strip()
        if not prepared or not output:
            self._warn("Choose a prepared ROM folder and covers-only output folder first.")
            return
        issue = validate_asset_output_path(Path(prepared), Path(output))
        if issue:
            self._warn(issue)
            return
        artwork = self.artwork_source.get().strip()
        sources = [Path(artwork)] if artwork else []
        self._run_task(lambda: build_assets(Path(prepared), Path(output), self.cover_style.get(), 88, artwork_sources=sources))

    def build_combined_tico_folder(self) -> None:
        source = self.source_library.get().strip()
        output = self.final_output.get().strip()
        if not source or not output:
            self._warn("Choose a source library and final Tico folder first.")
            return
        issue = validate_combined_output_path(Path(source), Path(output))
        if issue:
            self._warn(issue)
            return
        self._run_task(
            lambda: build_tico_folder(
                Path(source),
                Path(output),
                self.combined_style.get(),
                consoles=self._selected_consoles(),
            )
        )

    def refresh_reports(self) -> None:
        prep_dir = Path(self.prepared_output.get()) / "reports" if self.prepared_output.get().strip() else None
        asset_dir = Path(self.asset_output.get()) / "reports" if self.asset_output.get().strip() else None
        if self.final_output.get().strip():
            prep_dir = Path(self.final_output.get()) / "tico" / "reports"
            asset_dir = Path(self.final_output.get()) / "reports"
        summary = summarize_reports(prep_dir, asset_dir)
        for key, value in summary.items():
            if key in self._summary_labels:
                self._summary_labels[key].configure(text=str(value))
        lines = [format_summary_text(summary)]
        for key, (_title, filename, _empty) in REPORT_DEFINITIONS.items():
            root = prep_dir if key in {"prepared_roms", "skipped_archives"} else asset_dir
            report = load_csv_report(root / filename) if root else None
            lines.append(f"{filename}: {len(report.rows) if report else 0} row(s)")
        self._set_textbox(self.report_box, "\n".join(lines))

    def save_summary(self) -> None:
        target = Path(self.final_output.get() or self.asset_output.get() or self.prepared_output.get() or ".")
        if not target.exists():
            self._warn("Run a workflow before saving a summary.")
            return
        prep_dir = target / "tico" / "reports" if (target / "tico" / "reports").exists() else target / "reports"
        asset_dir = target / "reports"
        (target / "summary.txt").write_text(format_summary_text(summarize_reports(prep_dir, asset_dir)), encoding="utf-8")
        self._log(f"Saved summary: {target / 'summary.txt'}")

    def request_cancel(self) -> None:
        self._cancel_requested.set()
        self._log("Cancel requested. The app will stop after the current file when possible.")

    def _run_task(self, task) -> None:
        if self._task_running:
            self._warn("A task is already running.")
            return
        self._task_running = True
        self._cancel_requested.clear()
        self.progress.set(0.1)

        def runner() -> None:
            try:
                task()
                self.after(0, lambda: self.progress.set(1))
                self._log("Done.")
            except Exception as error:
                self._warn(str(error))
            finally:
                self._task_running = False

        threading.Thread(target=runner, daemon=True).start()

    def _warn(self, message: str) -> None:
        self._log(f"Warning: {message}")
        messagebox.showwarning("Tico Asset Builder", message)

    def _log(self, message: str) -> None:
        def append() -> None:
            self.log_box.insert("end", f"{message}\n")
            self.log_box.see("end")

        if hasattr(self, "log_box"):
            self.after(0, append)

    def _set_textbox(self, textbox, text: str) -> None:
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        textbox.insert("end", text)
        textbox.configure(state="disabled")
