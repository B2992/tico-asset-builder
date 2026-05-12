"""Tkinter GUI wrapper around the same local-first CLI workflows."""

from __future__ import annotations

import csv
import threading
import tkinter as tk
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .builder import build_assets
from .combined import build_tico_folder, validate_combined_output_path
from .config import CONSOLES, IMAGE_EXTENSIONS, IMAGE_FOLDER_NAMES
from .prep import PrepResult, prepare_roms
from .system_aliases import ConsoleFolderMatch, resolve_console_folder_name

GUI_CONSOLES = tuple(CONSOLES)
COVER_STYLES = ("fit", "crop", "stretch")
REPORT_DEFINITIONS = {
    "prepared_roms": ("Prepared ROMs", "prepared-roms.csv", "No prepared ROMs found."),
    "skipped_archives": ("Skipped Archives", "skipped-archives.csv", "No skipped archive items found."),
    "detected_games": ("Detected Games", "detected-games.csv", "No detected games found."),
    "matched_covers": ("Matched Covers", "matched-covers.csv", "No matched covers found."),
    "missing_covers": ("Missing Covers", "missing-covers.csv", "No missing covers found."),
    "skipped_files": ("Skipped Files", "skipped-files.csv", "No skipped files found."),
}


@dataclass(frozen=True)
class CsvReport:
    path: Path
    headers: list[str]
    rows: list[dict[str, str]]
    exists: bool


@dataclass(frozen=True)
class ConsoleAnalysis:
    console: str
    source_folder_name: str
    zipped_roms: int
    extracted_roms: int
    local_images: int


@dataclass(frozen=True)
class LibraryAnalysis:
    source: Path
    consoles: dict[str, ConsoleAnalysis]
    unsupported_folders: list[str]

    @property
    def detected_consoles(self) -> list[str]:
        return [console for console, item in self.consoles.items() if item.zipped_roms or item.extracted_roms or item.local_images]

    @property
    def total_zipped_roms(self) -> int:
        return sum(item.zipped_roms for item in self.consoles.values())

    @property
    def total_extracted_roms(self) -> int:
        return sum(item.extracted_roms for item in self.consoles.values())

    @property
    def total_local_images(self) -> int:
        return sum(item.local_images for item in self.consoles.values())


class TicoAssetBuilderGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Tico Asset Builder")
        self.source_library = tk.StringVar()
        self.prepared_output = tk.StringVar()
        self.prepared_input = tk.StringVar()
        self.asset_output = tk.StringVar()
        self.artwork_source = tk.StringVar()
        self.final_output = tk.StringVar()
        self.dry_run = tk.BooleanVar()
        self.cover_style = tk.StringVar(value="fit")
        self.combined_style = tk.StringVar(value="fit")
        self.status_text = tk.StringVar(value="Status: Ready")
        self.detected_text = tk.StringVar(value="Detected consoles: none yet")
        self.prepared_count_text = tk.StringVar(value="Prepared ROMs: 0")
        self.cover_count_text = tk.StringVar(value="Matched covers: 0")
        self.missing_count_text = tk.StringVar(value="Missing covers: 0")
        self.progress_text = tk.StringVar(value="Progress: idle")
        self.progress_value = tk.DoubleVar(value=0)
        self.report_summary_text = tk.StringVar(value="Reports: not loaded yet")
        self.console_vars = {console: tk.BooleanVar() for console in GUI_CONSOLES}
        self._visible_console_keys: list[str] = []
        self._last_prepared_output_suggestion = ""
        self._last_asset_output_suggestion = ""
        self._last_artwork_source_suggestion = ""
        self._last_combined_output_suggestion = ""
        self._console_selection_changed_by_user = False
        self._last_analysis: LibraryAnalysis | None = None
        self._cancel_requested = threading.Event()
        self._task_running = False
        self._task_buttons: list[ttk.Button] = []
        self._cancel_button: ttk.Button | None = None
        self._report_trees: dict[str, ttk.Treeview] = {}
        self._report_messages: dict[str, tk.StringVar] = {}

        self._build_layout()

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=10)
        container.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        self.main_notebook = ttk.Notebook(container)
        self.main_notebook.grid(row=0, column=0, sticky="nsew")

        prepare_tab = ttk.Frame(self.main_notebook, padding=10)
        build_tab = ttk.Frame(self.main_notebook, padding=10)
        combined_tab = ttk.Frame(self.main_notebook, padding=10)
        reports_tab = ttk.Frame(self.main_notebook, padding=10)
        log_tab = ttk.Frame(self.main_notebook, padding=10)
        self.main_notebook.add(prepare_tab, text="Prepare ROMs")
        self.main_notebook.add(build_tab, text="Build Cover Assets")
        self.main_notebook.add(combined_tab, text="Combined Tico Folder")
        self.main_notebook.add(reports_tab, text="Reports")
        self.main_notebook.add(log_tab, text="Log / Status")

        for tab in (prepare_tab, build_tab, combined_tab, reports_tab, log_tab):
            tab.columnconfigure(0, weight=1)
        prepare_tab.rowconfigure(1, weight=1)
        reports_tab.rowconfigure(0, weight=1)
        log_tab.rowconfigure(1, weight=1)

        source_frame = ttk.LabelFrame(prepare_tab, text="Source Library")
        source_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        source_frame.columnconfigure(1, weight=1)
        self._folder_row(
            source_frame,
            0,
            "Source library folder (read-only / untouched)",
            self.source_library,
            "Choose Source",
            self._choose_source_library,
        )
        ttk.Label(
            source_frame,
            text="Choose the ROM library to inspect. The original source folder is read-only and left untouched.",
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 6))
        self.analyze_button = ttk.Button(source_frame, text="Analyze Library", command=self.analyze_source_library)
        self.analyze_button.grid(row=2, column=0, sticky="w", padx=8, pady=(0, 8))

        prepare_frame = ttk.LabelFrame(prepare_tab, text="Prepare ROMs")
        prepare_frame.grid(row=1, column=0, sticky="nsew")
        prepare_frame.columnconfigure(1, weight=1)
        prepare_frame.rowconfigure(6, weight=1)
        self._folder_row(
            prepare_frame,
            0,
            "Prepared output folder (separate extracted copy for Tico)",
            self.prepared_output,
            "Choose Output",
        )
        ttk.Label(
            prepare_frame,
            text="This creates extracted ROM files only. Cover art is not copied into the prepared ROM folder.",
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 4))
        ttk.Label(
            prepare_frame,
            text="Dry Run checks what would happen without extracting ROMs or creating folders.",
        ).grid(
            row=2, column=0, columnspan=3, sticky="w", padx=8, pady=4
        )
        ttk.Checkbutton(prepare_frame, text="Dry run", variable=self.dry_run).grid(
            row=3, column=0, columnspan=3, sticky="w", padx=8, pady=4
        )

        console_frame = ttk.LabelFrame(prepare_frame, text="Console Filters")
        console_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=8, pady=4)
        console_frame.columnconfigure(0, weight=1)
        ttk.Label(
            console_frame,
            text="Analyze a source library to show detected supported systems.",
        ).grid(row=0, column=0, sticky="w", padx=6, pady=(4, 2))
        self.console_options_frame = ttk.Frame(console_frame)
        self.console_options_frame.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
        self._render_console_checkboxes([])

        selection_frame = ttk.Frame(prepare_frame)
        selection_frame.grid(row=5, column=0, columnspan=3, sticky="w", padx=8, pady=2)
        ttk.Button(selection_frame, text="Select All", command=self.select_all_consoles).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(selection_frame, text="Clear All", command=self.clear_all_consoles).grid(row=0, column=1, padx=6)
        ttk.Button(selection_frame, text="Select Detected Only", command=self.select_detected_consoles).grid(
            row=0, column=2, padx=6
        )
        ttk.Button(selection_frame, text="Show All Supported", command=self.show_all_supported_consoles).grid(
            row=0, column=3, padx=6
        )

        analysis_frame = ttk.LabelFrame(prepare_frame, text="Detected Console Summary")
        analysis_frame.grid(row=6, column=0, columnspan=3, sticky="ew", padx=8, pady=6)
        analysis_frame.columnconfigure(0, weight=1)
        self.analysis_summary = tk.Text(analysis_frame, height=5, wrap="word")
        self.analysis_summary.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.analysis_summary.insert("end", "Choose a source library, then click Analyze Library.")
        self.analysis_summary.configure(state="disabled")

        action_frame = ttk.Frame(prepare_frame)
        action_frame.grid(row=7, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 8))
        self.dry_run_button = ttk.Button(action_frame, text="Dry Run", command=self.dry_run_roms)
        self.dry_run_button.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.prepare_button = ttk.Button(action_frame, text="Prepare ROMs", command=self.prepare_roms)
        self.prepare_button.grid(row=0, column=1, sticky="w", padx=8)
        ttk.Button(
            action_frame,
            text="Open Prepared Folder",
            command=lambda: self._open_folder(Path(self.prepared_output.get()), "prepared folder"),
        ).grid(row=0, column=2, sticky="w", padx=8)
        ttk.Button(
            action_frame,
            text="Open Reports Folder",
            command=lambda: self._open_folder(Path(self.prepared_output.get()) / "reports", "prep reports folder"),
        ).grid(row=0, column=3, sticky="w", padx=8)

        build_frame = ttk.LabelFrame(build_tab, text="Build Cover Assets")
        build_frame.grid(row=0, column=0, sticky="ew")
        build_frame.columnconfigure(1, weight=1)
        self._folder_row(
            build_frame,
            0,
            "Prepared ROM folder",
            self.prepared_input,
            "Choose Folder",
            self._choose_prepared_input,
        )
        self._folder_row(
            build_frame,
            1,
            "Asset output folder (separate Tico cover assets folder)",
            self.asset_output,
            "Choose Output",
        )
        self._folder_row(
            build_frame,
            2,
            "Optional artwork source folder",
            self.artwork_source,
            "Choose Artwork",
        )
        ttk.Label(
            build_frame,
            text="This writes resized Tico covers only. Use artwork source when images are still in the original library.",
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 4))

        style_frame = ttk.Frame(build_frame)
        style_frame.grid(row=4, column=0, columnspan=3, sticky="w", padx=8, pady=4)
        ttk.Label(style_frame, text="Cover style:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        for index, style in enumerate(COVER_STYLES, start=1):
            ttk.Radiobutton(style_frame, text=style, variable=self.cover_style, value=style).grid(
                row=0, column=index, sticky="w", padx=3
            )

        build_actions = ttk.Frame(build_frame)
        build_actions.grid(row=5, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 8))
        self.build_button = ttk.Button(build_actions, text="Build Tico Assets", command=self.build_assets)
        self.build_button.grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Button(
            build_actions,
            text="Open Asset Folder",
            command=lambda: self._open_folder(Path(self.asset_output.get()), "asset folder"),
        ).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Button(
            build_actions,
            text="Open Reports Folder",
            command=lambda: self._open_folder(Path(self.asset_output.get()) / "reports", "asset reports folder"),
        ).grid(row=0, column=2, sticky="w", padx=8)

        combined_frame = ttk.LabelFrame(combined_tab, text="Build Combined Tico Folder")
        combined_frame.grid(row=0, column=0, sticky="ew")
        combined_frame.columnconfigure(1, weight=1)
        self._folder_row(
            combined_frame,
            0,
            "Source library folder (read-only / untouched)",
            self.source_library,
            "Choose Source",
            self._choose_source_library,
        )
        self._folder_row(
            combined_frame,
            1,
            "Final Tico output folder",
            self.final_output,
            "Choose Output",
        )
        ttk.Label(
            combined_frame,
            text="Creates one clean folder with tico/roms and resized covers in tico/assets/covers.",
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 4))
        ttk.Label(
            combined_frame,
            text="The original source library is left untouched. Source artwork folders are not copied into tico/roms.",
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 4))

        combined_style_frame = ttk.Frame(combined_frame)
        combined_style_frame.grid(row=4, column=0, columnspan=3, sticky="w", padx=8, pady=4)
        ttk.Label(combined_style_frame, text="Cover style:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        for index, style in enumerate(COVER_STYLES, start=1):
            ttk.Radiobutton(combined_style_frame, text=style, variable=self.combined_style, value=style).grid(
                row=0, column=index, sticky="w", padx=3
            )

        ttk.Label(
            combined_frame,
            text="Console filters use the checkboxes on the Prepare ROMs tab. Use Analyze Library and Select Detected Only there first if desired.",
        ).grid(row=5, column=0, columnspan=3, sticky="w", padx=8, pady=4)

        combined_actions = ttk.Frame(combined_frame)
        combined_actions.grid(row=6, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 8))
        self.combined_button = ttk.Button(
            combined_actions,
            text="Build Combined Tico Folder",
            command=self.build_combined_tico_folder,
        )
        self.combined_button.grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Button(
            combined_actions,
            text="Open Final Folder",
            command=lambda: self._open_folder(Path(self.final_output.get()), "final Tico output folder"),
        ).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Button(
            combined_actions,
            text="Open Reports Folder",
            command=lambda: self._open_folder(Path(self.final_output.get()) / "reports", "asset reports folder"),
        ).grid(row=0, column=2, sticky="w", padx=8)

        status_frame = ttk.LabelFrame(log_tab, text="Status Summary")
        status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        status_frame.columnconfigure(0, weight=1)
        ttk.Label(status_frame, textvariable=self.status_text).grid(row=0, column=0, sticky="w", padx=8, pady=2)
        ttk.Label(status_frame, textvariable=self.detected_text).grid(row=1, column=0, sticky="w", padx=8, pady=2)
        ttk.Label(status_frame, textvariable=self.prepared_count_text).grid(row=2, column=0, sticky="w", padx=8, pady=2)
        ttk.Label(status_frame, textvariable=self.cover_count_text).grid(row=3, column=0, sticky="w", padx=8, pady=2)
        ttk.Label(status_frame, textvariable=self.missing_count_text).grid(row=4, column=0, sticky="w", padx=8, pady=(2, 6))
        ttk.Label(status_frame, textvariable=self.progress_text).grid(row=5, column=0, sticky="w", padx=8, pady=2)
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_value, maximum=100)
        self.progress_bar.grid(row=6, column=0, sticky="ew", padx=8, pady=(2, 6))
        self._cancel_button = ttk.Button(status_frame, text="Cancel", command=self.request_cancel, state="disabled")
        self._cancel_button.grid(row=6, column=1, sticky="e", padx=8, pady=(2, 6))
        status_frame.columnconfigure(0, weight=1)

        self._task_buttons = [
            self.analyze_button,
            self.dry_run_button,
            self.prepare_button,
            self.build_button,
            self.combined_button,
        ]

        reports_frame = ttk.LabelFrame(reports_tab, text="Report Viewer")
        reports_frame.grid(row=0, column=0, sticky="nsew")
        reports_frame.columnconfigure(0, weight=1)
        reports_frame.rowconfigure(1, weight=1)

        report_actions = ttk.Frame(reports_frame)
        report_actions.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
        ttk.Button(report_actions, text="Refresh Reports", command=self.refresh_reports).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(report_actions, text="Open Prep Reports Folder", command=self.open_prep_reports_folder).grid(
            row=0, column=1, padx=6
        )
        ttk.Button(report_actions, text="Open Asset Reports Folder", command=self.open_asset_reports_folder).grid(
            row=0, column=2, padx=6
        )
        ttk.Button(report_actions, text="Save Summary", command=self.save_summary).grid(row=0, column=3, padx=6)
        ttk.Label(report_actions, textvariable=self.report_summary_text).grid(row=0, column=4, sticky="w", padx=12)

        self.report_notebook = ttk.Notebook(reports_frame)
        self.report_notebook.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        for key, (title, _filename, _empty_message) in REPORT_DEFINITIONS.items():
            tab = ttk.Frame(self.report_notebook)
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(1, weight=1)
            message_var = tk.StringVar(value="Report not loaded yet.")
            ttk.Label(tab, textvariable=message_var).grid(row=0, column=0, sticky="w", padx=6, pady=4)
            tree = ttk.Treeview(tab, show="headings", height=6)
            tree.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
            scrollbar = ttk.Scrollbar(tab, orient="vertical", command=tree.yview)
            scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 6))
            tree.configure(yscrollcommand=scrollbar.set)
            self.report_notebook.add(tab, text=title)
            self._report_trees[key] = tree
            self._report_messages[key] = message_var

        log_frame = ttk.LabelFrame(log_tab, text="Results / Log")
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log = ScrolledText(log_frame, height=12, wrap="word")
        self.log.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._log("Ready. The source library is treated as read-only and left untouched.")

    def _folder_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        button_text: str,
        command=None,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        button_command = command or (lambda: self._choose_folder(variable))
        ttk.Button(parent, text=button_text, command=button_command).grid(
            row=row, column=2, sticky="e", padx=8, pady=4
        )

    def _choose_folder(self, variable: tk.StringVar) -> None:
        folder = filedialog.askdirectory()
        if folder:
            variable.set(folder)

    def _choose_source_library(self) -> None:
        folder = filedialog.askdirectory()
        if folder:
            self.source_library.set(folder)
            suggestion = suggest_prepared_output_folder(Path(folder))
            if _should_apply_suggestion(self.prepared_output.get(), self._last_prepared_output_suggestion):
                self.prepared_output.set(str(suggestion))
                self._last_prepared_output_suggestion = str(suggestion)
            if _should_apply_suggestion(self.artwork_source.get(), self._last_artwork_source_suggestion):
                self.artwork_source.set(folder)
                self._last_artwork_source_suggestion = folder
            combined_suggestion = suggest_combined_output_folder(Path(folder))
            if _should_apply_suggestion(self.final_output.get(), self._last_combined_output_suggestion):
                self.final_output.set(str(combined_suggestion))
                self._last_combined_output_suggestion = str(combined_suggestion)
            self.analyze_source_library()

    def _choose_prepared_input(self) -> None:
        folder = filedialog.askdirectory()
        if folder:
            self.prepared_input.set(folder)
            suggestion = suggest_asset_output_folder(Path(folder))
            if _should_apply_suggestion(self.asset_output.get(), self._last_asset_output_suggestion):
                self.asset_output.set(str(suggestion))
                self._last_asset_output_suggestion = str(suggestion)

    def _mark_console_selection_changed(self) -> None:
        self._console_selection_changed_by_user = True

    def _render_console_checkboxes(
        self,
        console_keys: list[str],
        analysis: LibraryAnalysis | None = None,
    ) -> None:
        self._visible_console_keys = list(console_keys)
        for child in self.console_options_frame.winfo_children():
            child.destroy()

        if not console_keys:
            ttk.Label(self.console_options_frame, text="No supported systems detected yet.").grid(
                row=0, column=0, sticky="w"
            )
            return

        for index, console in enumerate(console_keys):
            row = index // 2
            column = index % 2
            ttk.Checkbutton(
                self.console_options_frame,
                text=console_checkbox_label(console, analysis),
                variable=self.console_vars[console],
                command=self._mark_console_selection_changed,
            ).grid(row=row, column=column, sticky="w", padx=(0, 16), pady=2)

    def _set_console_options(
        self,
        console_keys: list[str],
        analysis: LibraryAnalysis | None,
    ) -> None:
        self.root.after(0, lambda: self._render_console_checkboxes(console_keys, analysis))

    def analyze_source_library(self) -> None:
        source = self.source_library.get().strip()
        if not source:
            self._warn("Choose a source library folder before analyzing.")
            return

        self._log_separator("Analyze Library")
        self._set_status("Analyzing")
        self._set_indeterminate_progress("Analyzing library...")
        self._run_in_background("Analyze Library", lambda: self._analyze_source_task(Path(source)))

    def _analyze_source_task(self, source: Path) -> None:
        analysis = analyze_library(source)
        self._last_analysis = analysis
        self._set_analysis_summary(format_library_analysis(analysis))
        self._log(f"Analyzed source folder: {analysis.source}")
        detected = analysis.detected_consoles
        self._log(f"Detected consoles: {', '.join(detected) if detected else 'none'}")
        self.root.after(0, lambda: self.detected_text.set(f"Detected consoles: {', '.join(detected) if detected else 'none'}"))
        self._log(f"Total zipped ROMs: {analysis.total_zipped_roms}")
        self._log(f"Total extracted ROMs: {analysis.total_extracted_roms}")
        self._log(f"Total local images: {analysis.total_local_images}")
        if analysis.unsupported_folders:
            self._log(f"Unsupported folders found: {', '.join(analysis.unsupported_folders)}")
        self._set_console_options(console_keys_for_analysis(analysis), analysis)
        if not self._console_selection_changed_by_user:
            self._set_console_selection(detected)
        self._set_status("Ready")
        self._set_progress(1, 1, "Analysis complete.")

    def _set_analysis_summary(self, text: str) -> None:
        def update() -> None:
            self.analysis_summary.configure(state="normal")
            self.analysis_summary.delete("1.0", "end")
            self.analysis_summary.insert("end", text)
            self.analysis_summary.configure(state="disabled")

        self.root.after(0, update)

    def select_all_consoles(self) -> None:
        self._console_selection_changed_by_user = True
        self._set_console_selection(self._visible_console_keys or GUI_CONSOLES)

    def clear_all_consoles(self) -> None:
        self._console_selection_changed_by_user = True
        self._set_console_selection([])

    def select_detected_consoles(self) -> None:
        self._console_selection_changed_by_user = True
        if not self._last_analysis:
            self._warn("Analyze a source library before selecting detected consoles.")
            return
        self._set_console_options(console_keys_for_analysis(self._last_analysis), self._last_analysis)
        self._set_console_selection(select_detected_console_keys(self._last_analysis))

    def show_all_supported_consoles(self) -> None:
        self._set_console_options(console_keys_for_analysis(self._last_analysis, show_all_supported=True), self._last_analysis)

    def _set_console_selection(self, selected: list[str] | tuple[str, ...]) -> None:
        selected_set = set(selected)
        self.root.after(0, lambda: [variable.set(console in selected_set) for console, variable in self.console_vars.items()])

    def dry_run_roms(self) -> None:
        self._start_prepare_roms(force_dry_run=True)

    def prepare_roms(self) -> None:
        self._start_prepare_roms(force_dry_run=None)

    def _start_prepare_roms(self, force_dry_run: bool | None) -> None:
        source = self.source_library.get().strip()
        output = self.prepared_output.get().strip()
        if not source or not output:
            self._warn("Choose a source library folder and a prepared output folder first.")
            return
        safety_issue = validate_prepare_output_path(Path(source), Path(output))
        if safety_issue:
            self._warn(safety_issue)
            return

        consoles = [console for console, variable in self.console_vars.items() if variable.get()]
        dry_run = self.dry_run.get() if force_dry_run is None else force_dry_run
        label = "Dry Run" if dry_run else "Preparing ROMs"
        self._log_separator("Prepare ROMs" if not dry_run else "Dry Run")
        self._set_status("Preparing" if not dry_run else "Analyzing")
        self._set_progress(0, 1, "Starting ROM prep...")
        self._run_in_background(
            label,
            lambda: self._prepare_roms_task(Path(source), Path(output), consoles, dry_run),
        )

    def _prepare_roms_task(self, source: Path, output: Path, consoles: list[str], dry_run: bool) -> None:
        self._log("Starting ROM prep.")
        self._log(f"Source library, read-only: {source}")
        self._log(f"Prepared output folder: {output}")
        if consoles:
            self._log(f"Console filter: {', '.join(consoles)}")
        if dry_run:
            self._log("Dry run enabled: no ROMs or artwork will be written.")

        result = prepare_roms(
            source,
            output,
            dry_run=dry_run,
            consoles=consoles,
            progress_callback=self._set_progress,
            cancel_check=self._cancel_requested.is_set,
        )
        for line in format_prepare_summary(result, dry_run):
            self._log(line)
        if result.cancelled:
            self._log("Cancelled. Partial output may exist. Original ROM library was left untouched.")
        self.root.after(0, lambda: self.prepared_count_text.set(f"Prepared ROMs: {len(result.prepared)}"))
        if not dry_run:
            self.root.after(0, self.refresh_reports)
            self._log(f"Prep reports loaded from: {output / 'reports'}")
        self._set_status("Cancelled" if result.cancelled else "Done")

    def build_assets(self) -> None:
        prepared = self.prepared_input.get().strip()
        output = self.asset_output.get().strip()
        if not prepared or not output:
            self._warn("Choose a prepared ROM folder and an asset output folder first.")
            return
        safety_issue = validate_asset_output_path(Path(prepared), Path(output))
        if safety_issue:
            self._warn(safety_issue)
            return
        artwork_source = self.artwork_source.get().strip()
        if artwork_source and not Path(artwork_source).is_dir():
            self._warn("Choose an artwork source folder that exists, or leave it blank.")
            return

        self._log_separator("Build Cover Assets")
        self._set_status("Building")
        self._set_progress(0, 1, "Starting cover build...")
        self._run_in_background(
            "Building Tico assets",
            lambda: self._build_assets_task(Path(prepared), Path(output), self.cover_style.get()),
        )

    def _build_assets_task(self, prepared: Path, output: Path, style: str) -> None:
        self._log("Starting Tico asset build.")
        self._log(f"Prepared ROM folder: {prepared}")
        self._log(f"Asset output folder: {output}")
        artwork_source = self.artwork_source.get().strip()
        artwork_sources = [Path(artwork_source)] if artwork_source else []
        if artwork_sources:
            self._log(f"Artwork source folder: {artwork_sources[0]}")
        self._log(f"Cover style: {style}")
        result = build_assets(
            input_path=prepared,
            output_root=output,
            style=style,
            threshold=88,
            artwork_sources=artwork_sources,
            progress_callback=self._set_progress,
            cancel_check=self._cancel_requested.is_set,
        )
        self._log(f"Detected games: {len(result.games)}")
        self._log(f"Matched covers: {len(result.matches)}")
        self._log(f"Missing covers: {len(result.missing)}")
        self._log(f"Skipped files: {len(result.skipped)}")
        self._log(f"Reports: {output / 'reports'}")
        self._log(f"Covers: {output / 'tico' / 'assets' / 'covers'}")
        if result.cancelled:
            self._log("Cancelled. Partial output may exist. Original ROM library was left untouched.")
        else:
            self._log("Tico asset build complete.")
        self.root.after(0, lambda: self.cover_count_text.set(f"Matched covers: {len(result.matches)}"))
        self.root.after(0, lambda: self.missing_count_text.set(f"Missing covers: {len(result.missing)}"))
        self.root.after(0, self.refresh_reports)
        self._log(f"Asset reports loaded from: {output / 'reports'}")
        self._set_status("Cancelled" if result.cancelled else "Done")

    def build_combined_tico_folder(self) -> None:
        source = self.source_library.get().strip()
        output = self.final_output.get().strip()
        if not source or not output:
            self._warn("Choose a source library folder and a final Tico output folder first.")
            return
        safety_issue = validate_combined_output_path(Path(source), Path(output))
        if safety_issue:
            self._warn(safety_issue)
            return

        consoles = [console for console, variable in self.console_vars.items() if variable.get()]
        self._log_separator("Build Combined Tico Folder")
        self._set_status("Building")
        self._set_progress(0, 1, "Starting combined Tico folder build...")
        self._run_in_background(
            "Building combined Tico folder",
            lambda: self._build_combined_tico_folder_task(
                Path(source),
                Path(output),
                self.combined_style.get(),
                consoles,
            ),
        )

    def _build_combined_tico_folder_task(self, source: Path, output: Path, style: str, consoles: list[str]) -> None:
        self._log("Starting combined Tico folder build.")
        self._log(f"Source library, read-only: {source}")
        self._log(f"Final Tico output folder: {output}")
        self._log(f"Cover style: {style}")
        if consoles:
            self._log(f"Console filter: {', '.join(consoles)}")
        result = build_tico_folder(
            source_library=source,
            final_output=output,
            style=style,
            consoles=consoles,
            progress_callback=self._set_progress,
            cancel_check=self._cancel_requested.is_set,
        )
        assets = result.assets
        self._log(f"Prepared ROMs: {len(result.prep.prepared)}")
        self._log(f"Skipped archive items: {len(result.prep.skipped)}")
        if assets:
            self._log(f"Detected games: {len(assets.games)}")
            self._log(f"Matched covers: {len(assets.matches)}")
            self._log(f"Missing covers: {len(assets.missing)}")
            self._log(f"Skipped files: {len(assets.skipped)}")
            self.root.after(0, lambda: self.cover_count_text.set(f"Matched covers: {len(assets.matches)}"))
            self.root.after(0, lambda: self.missing_count_text.set(f"Missing covers: {len(assets.missing)}"))
        self.root.after(0, lambda: self.prepared_count_text.set(f"Prepared ROMs: {len(result.prep.prepared)}"))
        self.root.after(0, lambda: self.prepared_output.set(str(output / "tico")))
        self.root.after(0, lambda: self.prepared_input.set(str(output / "tico")))
        self.root.after(0, lambda: self.asset_output.set(str(output)))
        self.root.after(0, lambda: self.artwork_source.set(str(source)))
        self.root.after(0, self.refresh_reports)
        self._log(f"Prepared ROM folder: {output / 'tico' / 'roms'}")
        self._log(f"Cover assets folder: {output / 'tico' / 'assets' / 'covers'}")
        self._log(f"Prep reports loaded from: {output / 'tico' / 'reports'}")
        self._log(f"Asset reports loaded from: {output / 'reports'}")
        if result.cancelled:
            self._log("Cancelled. Partial output may exist. Original ROM library was left untouched.")
        else:
            self._log("Combined Tico folder build complete. Original ROM library was left untouched.")
        self._set_status("Cancelled" if result.cancelled else "Done")

    def _run_in_background(self, label: str, task) -> None:
        """Run long tasks off the Tk main thread and marshal UI updates back."""
        if self._task_running:
            self._log("A task is already running. Please wait or click Cancel.")
            return
        self._task_running = True
        self._cancel_requested.clear()
        self._set_controls_running(True)
        self._log(f"{label}...")

        def runner() -> None:
            try:
                task()
                self._log(f"SUCCESS: {label} succeeded.")
            except Exception as error:  # pragma: no cover - exercised by manual GUI use
                self._set_status("Error")
                self._log(f"ERROR: {error}")
                self.root.after(0, lambda: messagebox.showerror("Tico Asset Builder", str(error)))
            finally:
                self._task_running = False
                self.root.after(0, lambda: self._set_controls_running(False))

        threading.Thread(target=runner, daemon=True).start()

    def request_cancel(self) -> None:
        """Request cooperative cancellation before the next archive or cover."""
        if not self._task_running:
            return
        self._cancel_requested.set()
        self._set_status("Cancel requested")
        self._log("Cancel requested. The app will stop after the current file finishes.")

    def _warn(self, message: str) -> None:
        self._set_status("Error")
        self._log(f"Warning: {message}")
        messagebox.showwarning("Tico Asset Builder", message)

    def _open_folder(self, folder: Path, label: str) -> None:
        if not str(folder).strip() or str(folder) == ".":
            self._log(f"Choose a {label} first.")
            return
        if not folder.exists() or not folder.is_dir():
            self._log(f"Cannot open {label}: {folder} does not exist yet.")
            return
        subprocess.run(["open", str(folder)], check=False)
        self._log(f"Opened {label}: {folder}")

    def open_prep_reports_folder(self) -> None:
        self._open_folder(Path(self.prepared_output.get()) / "reports", "prep reports folder")

    def open_asset_reports_folder(self) -> None:
        self._open_folder(Path(self.asset_output.get()) / "reports", "asset reports folder")

    def refresh_reports(self) -> None:
        prep_reports_dir = Path(self.prepared_output.get()) / "reports" if self.prepared_output.get().strip() else None
        asset_reports_dir = Path(self.asset_output.get()) / "reports" if self.asset_output.get().strip() else None
        reports = {
            "prepared_roms": load_csv_report(prep_reports_dir / "prepared-roms.csv") if prep_reports_dir else missing_report("prepared-roms.csv"),
            "skipped_archives": load_csv_report(prep_reports_dir / "skipped-archives.csv") if prep_reports_dir else missing_report("skipped-archives.csv"),
            "detected_games": load_csv_report(asset_reports_dir / "detected-games.csv") if asset_reports_dir else missing_report("detected-games.csv"),
            "matched_covers": load_csv_report(asset_reports_dir / "matched-covers.csv") if asset_reports_dir else missing_report("matched-covers.csv"),
            "missing_covers": load_csv_report(asset_reports_dir / "missing-covers.csv") if asset_reports_dir else missing_report("missing-covers.csv"),
            "skipped_files": load_csv_report(asset_reports_dir / "skipped-files.csv") if asset_reports_dir else missing_report("skipped-files.csv"),
        }
        for key, report in reports.items():
            self._populate_report_table(key, report)
        summary = summarize_reports(prep_reports_dir, asset_reports_dir)
        self._set_report_summary(summary)
        self._log("Reports refreshed.")

    def _populate_report_table(self, key: str, report: CsvReport) -> None:
        tree = self._report_trees[key]
        message = self._report_messages[key]
        empty_message = REPORT_DEFINITIONS[key][2]
        tree.delete(*tree.get_children())

        headers = report.headers or ["message"]
        tree.configure(columns=headers)
        for header in headers:
            tree.heading(header, text=header)
            tree.column(header, width=160, anchor="w")

        if not report.exists:
            message.set(f"Report not available: {report.path}")
            tree.insert("", "end", values=("Report not available yet.",))
            return
        if not report.rows:
            message.set(empty_message)
            tree.insert("", "end", values=(empty_message,))
            return

        message.set(f"{len(report.rows)} row(s) loaded from {report.path}")
        for row in report.rows:
            tree.insert("", "end", values=[row.get(header, "") for header in headers])

    def _set_report_summary(self, summary: dict[str, int]) -> None:
        self.report_summary_text.set(
            " | ".join(
                [
                    f"Prepared ROMs: {summary['prepared_roms']}",
                    f"Skipped Archives: {summary['skipped_archives']}",
                    f"Detected Games: {summary['detected_games']}",
                    f"Matched Covers: {summary['matched_covers']}",
                    f"Missing Covers: {summary['missing_covers']}",
                    f"Skipped Files: {summary['skipped_files']}",
                ]
            )
        )

    def save_summary(self) -> None:
        prep_reports_dir = Path(self.prepared_output.get()) / "reports" if self.prepared_output.get().strip() else None
        asset_reports_dir = Path(self.asset_output.get()) / "reports" if self.asset_output.get().strip() else None
        target_root = Path(self.asset_output.get() or self.prepared_output.get() or ".")
        if not target_root.exists():
            self._log(f"Cannot save summary: {target_root} does not exist yet.")
            return
        summary = summarize_reports(prep_reports_dir, asset_reports_dir)
        path = target_root / "summary.txt"
        path.write_text(format_summary_text(summary), encoding="utf-8")
        self._log(f"Saved summary: {path}")

    def _log_separator(self, label: str) -> None:
        self._log(f"--- {label} ---")

    def _set_status(self, status: str) -> None:
        self.root.after(0, lambda: self.status_text.set(f"Status: {status}"))

    def _set_progress(self, current: int, total: int, message: str) -> None:
        def update() -> None:
            if total:
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
                self.progress_value.set((current / total) * 100)
            self.progress_text.set(f"Progress: {message}")

        self.root.after(0, update)

    def _set_indeterminate_progress(self, message: str) -> None:
        def update() -> None:
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start(12)
            self.progress_text.set(f"Progress: {message}")

        self.root.after(0, update)

    def _set_controls_running(self, running: bool) -> None:
        state = "disabled" if running else "normal"
        for button in self._task_buttons:
            button.configure(state=state)
        if self._cancel_button:
            self._cancel_button.configure(state="normal" if running else "disabled")
        if not running:
            self.progress_bar.stop()

    def _log(self, message: str) -> None:
        def append() -> None:
            self.log.insert("end", f"{message}\n")
            self.log.see("end")

        if threading.current_thread() is threading.main_thread():
            append()
        else:
            self.root.after(0, append)


def format_prepare_summary(result: PrepResult, dry_run: bool) -> list[str]:
    lines: list[str] = []
    if dry_run:
        lines.extend(
            [
                "Dry run complete.",
                "No ROMs were extracted.",
                "No artwork was copied.",
                "No output folder was created.",
                f"ROMs that would be extracted: {len(result.prepared)}",
            ]
        )
    else:
        lines.extend(
            [
                "Prepared ROM copy complete.",
                f"Extracted ROMs: {len(result.prepared)}",
            ]
        )

    for console, count in sorted(Counter(item.console for item in result.prepared).items()):
        action = "would be extracted" if dry_run else "extracted"
        lines.append(f"{console}: {count} {action}")
    lines.append(f"Skipped archive items: {len(result.skipped)}")
    lines.append("Original ROM library was left untouched.")
    return lines


def suggest_prepared_output_folder(source_library: Path) -> Path:
    return source_library.with_name(f"{source_library.name}-tico-prepared")


def suggest_asset_output_folder(prepared_library: Path) -> Path:
    suffix = "-tico-prepared"
    if prepared_library.name.endswith(suffix):
        name = f"{prepared_library.name[: -len(suffix)]}-tico-assets"
    else:
        name = f"{prepared_library.name}-tico-assets"
    return prepared_library.with_name(name)


def suggest_combined_output_folder(source_library: Path) -> Path:
    return source_library.with_name(f"{source_library.name}-tico-output")


def _should_apply_suggestion(current_value: str, previous_suggestion: str) -> bool:
    """Only replace empty fields or fields still holding our prior suggestion."""
    return not current_value.strip() or current_value == previous_suggestion


def validate_prepare_output_path(source_library: Path, prepared_output: Path) -> str | None:
    source = _resolved(source_library)
    output = _resolved(prepared_output)
    if output == source:
        return "Choose a prepared output folder that is separate from the source library."

    source_roms = source / "roms"
    if _is_relative_to(output, source_roms):
        return "Choose a prepared output folder outside the source library's roms folder."
    return None


def validate_asset_output_path(prepared_library: Path, asset_output: Path) -> str | None:
    prepared = _resolved(prepared_library)
    output = _resolved(asset_output)
    if output == prepared:
        return "Choose an asset output folder that is separate from the prepared ROM folder."

    prepared_roms = prepared / "roms"
    if _is_relative_to(output, prepared_roms):
        return "Choose an asset output folder outside the prepared ROM folder's roms folder."
    return None


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve()


def _is_relative_to(path: Path, possible_parent: Path) -> bool:
    try:
        path.relative_to(possible_parent)
    except ValueError:
        return False
    return True


def analyze_library(source: Path) -> LibraryAnalysis:
    source = source.expanduser()
    rom_root = source / "roms" if (source / "roms").is_dir() else source
    consoles: dict[str, ConsoleAnalysis] = {}
    unsupported_folders: list[str] = []

    folder_matches: list[tuple[ConsoleFolderMatch, Path]] = []
    if rom_root.is_dir():
        for child in sorted(rom_root.iterdir()):
            if not child.is_dir() or child.name.startswith(".") or child.name.lower() in IMAGE_FOLDER_NAMES:
                continue
            match = resolve_console_folder_name(child.name)
            if match:
                if match.console not in consoles:
                    folder_matches.append((match, child))
            else:
                unsupported_folders.append(child.name)

    for match, console_dir in folder_matches:
        config = CONSOLES[match.console]
        if not console_dir.is_dir():
            continue
        zipped_roms = sum(1 for path in console_dir.glob("*.zip") if path.is_file() and not path.name.startswith("."))
        extracted_roms = sum(
            1
            for path in console_dir.iterdir()
            if path.is_file() and not path.name.startswith(".") and _effective_suffix(path) in config.extensions
        )
        local_images = _count_local_images(console_dir)
        consoles[match.console] = ConsoleAnalysis(match.console, match.folder_name, zipped_roms, extracted_roms, local_images)

    return LibraryAnalysis(source=source, consoles=consoles, unsupported_folders=unsupported_folders)


def format_library_analysis(analysis: LibraryAnalysis) -> str:
    lines = ["Detected library contents:"]
    detected = analysis.detected_consoles
    if not detected:
        lines.append("No supported console folders were found.")
    for console in detected:
        item = analysis.consoles[console]
        prefix = f"{item.source_folder_name} -> {console}" if item.source_folder_name != console else console
        lines.append(
            f"{prefix}: {item.zipped_roms} zipped ROMs, "
            f"{item.extracted_roms} extracted ROMs, {item.local_images} local images"
        )
    if analysis.unsupported_folders:
        lines.append(f"Unsupported folders: {', '.join(analysis.unsupported_folders)}")
    return "\n".join(lines)


def console_keys_for_analysis(analysis: LibraryAnalysis | None, show_all_supported: bool = False) -> list[str]:
    """Return checkbox keys from backend-supported consoles, detected first."""
    if not analysis:
        return list(GUI_CONSOLES) if show_all_supported else []
    detected = [console for console in GUI_CONSOLES if console in analysis.detected_consoles]
    if not show_all_supported:
        return detected
    undetected = [console for console in GUI_CONSOLES if console not in detected]
    return detected + undetected


def console_checkbox_label(console: str, analysis: LibraryAnalysis | None) -> str:
    if not analysis or console not in analysis.consoles:
        return console
    item = analysis.consoles[console]
    source = f" from {item.source_folder_name}" if item.source_folder_name != console else ""
    return f"{console}{source} - {item.zipped_roms} zipped, {item.extracted_roms} extracted, {item.local_images} images"


def select_detected_console_keys(analysis: LibraryAnalysis) -> list[str]:
    return [console for console in GUI_CONSOLES if console in analysis.detected_consoles]


def _count_local_images(console_dir: Path) -> int:
    count = 0
    for folder in IMAGE_FOLDER_NAMES:
        image_dir = console_dir / folder
        if image_dir.is_dir():
            count += sum(
                1
                for path in image_dir.rglob("*")
                if path.is_file() and not path.name.startswith(".") and path.suffix.lower() in IMAGE_EXTENSIONS
            )
    return count


def _effective_suffix(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".nkit.iso"):
        return ".nkit.iso"
    return path.suffix.lower()


def load_csv_report(path: Path) -> CsvReport:
    if not path.exists():
        return CsvReport(path=path, headers=[], rows=[], exists=False)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return CsvReport(path=path, headers=headers, rows=rows, exists=True)


def missing_report(filename: str) -> CsvReport:
    return CsvReport(path=Path(filename), headers=[], rows=[], exists=False)


def count_report_rows(path: Path) -> int:
    return len(load_csv_report(path).rows)


def summarize_reports(prep_reports_dir: Path | None, asset_reports_dir: Path | None) -> dict[str, int]:
    return {
        "prepared_roms": count_report_rows(prep_reports_dir / "prepared-roms.csv") if prep_reports_dir else 0,
        "skipped_archives": count_report_rows(prep_reports_dir / "skipped-archives.csv") if prep_reports_dir else 0,
        "detected_games": count_report_rows(asset_reports_dir / "detected-games.csv") if asset_reports_dir else 0,
        "matched_covers": count_report_rows(asset_reports_dir / "matched-covers.csv") if asset_reports_dir else 0,
        "missing_covers": count_report_rows(asset_reports_dir / "missing-covers.csv") if asset_reports_dir else 0,
        "skipped_files": count_report_rows(asset_reports_dir / "skipped-files.csv") if asset_reports_dir else 0,
    }


def format_summary_text(summary: dict[str, int]) -> str:
    return "\n".join(
        [
            "Tico Asset Builder Summary",
            f"Prepared ROMs: {summary['prepared_roms']}",
            f"Skipped Archives: {summary['skipped_archives']}",
            f"Detected Games: {summary['detected_games']}",
            f"Matched Covers: {summary['matched_covers']}",
            f"Missing Covers: {summary['missing_covers']}",
            f"Skipped Files: {summary['skipped_files']}",
            "Original ROM Library Modified: No",
            "",
        ]
    )


def main() -> int:
    root = tk.Tk()
    root.geometry("950x700")
    root.minsize(800, 600)
    TicoAssetBuilderGui(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
