from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from core.config import (
    CUSTOM_PRESET,
    DEFAULT_SEPARATOR,
    DEFAULT_NUMBER_PADDING,
    DEFAULT_PREFIX,
    DEFAULT_START_NUMBER,
    DEFAULT_SUFFIX,
    SEPARATOR_OPTIONS,
    PRESETS,
    VIDEO_EXTENSION_ORDER,
)
from core.filtering import preview_item_matches_query
from core.models import RenameItem
from core.naming import build_rename_items
from core.renamer import apply_rename_plan
from core.scanner import discover_video_files
from core.storage import (
    load_app_settings,
    load_custom_presets,
    save_app_settings,
    save_custom_presets,
)
from core.undo_log import create_undo_log_file, load_rollback_items
from core.validator import validate_naming_inputs, validate_preview_items


WINDOWS_APP_TITLE = "Export Batch Renamer"
WINDOWS_MUTEX_NAME = "Local\\ExportBatchRenamerSingleInstance"


def _runtime_base_path() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


def _persistent_app_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class RenameToolApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.runtime_root = _runtime_base_path()
        self.app_root = _persistent_app_path()
        self.custom_presets = load_custom_presets(self.app_root, set(PRESETS.keys()))

        self.title(WINDOWS_APP_TITLE)
        self.geometry("1040x680")
        self.minsize(880, 560)
        self._set_window_icon()

        self.folder_var = tk.StringVar(value="")
        self.preset_var = tk.StringVar(value="Organic")
        self.prefix_var = tk.StringVar(value=DEFAULT_PREFIX)
        self.suffix_var = tk.StringVar(value=DEFAULT_SUFFIX)
        self.separator_var = tk.StringVar(value=DEFAULT_SEPARATOR)
        self.start_var = tk.StringVar(value=str(DEFAULT_START_NUMBER))
        self.padding_var = tk.StringVar(value=str(DEFAULT_NUMBER_PADDING))
        self.filter_var = tk.StringVar(value="")
        self.create_undo_log_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Choose a folder and click Preview.")

        self.extension_vars: dict[str, tk.BooleanVar] = {
            extension: tk.BooleanVar(value=True) for extension in VIDEO_EXTENSION_ORDER
        }

        self.preview_items: list[RenameItem] = []
        self.preview_errors: list[str] = []
        self.preview_is_fresh = False
        self.last_undo_log_path: Path | None = None

        self.row_item_map: dict[str, RenameItem] = {}
        self.row_include_map: dict[str, bool] = {}
        self.row_index_map: dict[str, int] = {}
        self.include_state_by_source: dict[str, bool] = {}

        self._configure_theme()
        self._build_ui()
        self._apply_input_cursor_style()
        self._bind_events()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._restore_saved_settings()

    def _set_window_icon(self) -> None:
        icon_path = self.runtime_root / "assets" / "app.ico"
        if not icon_path.exists():
            return

        try:
            self.iconbitmap(default=str(icon_path))
        except tk.TclError:
            # Ignore unsupported icon formats or platform-specific failures.
            return

    def _configure_theme(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        app_bg = "#1E1E1E"
        sidebar_bg = "#232323"
        panel_bg = "#2B2B2B"
        panel_alt = "#262626"
        border = "#3A3A3A"
        text_primary = "#F2F5F8"
        text_secondary = "#CBD3DC"
        accent_blue = "#4A9CFF"
        accent_blue_hover = "#66AEFF"
        accent_purple = "#9A8DFF"
        accent_teal = "#5CC8BD"

        self.configure(background=app_bg)
        self.option_add("*insertBackground", text_primary)
        self.option_add("*insertWidth", 2)
        self.option_add("*selectBackground", accent_blue)
        self.option_add("*selectForeground", "#FFFFFF")
        style.configure(".", font=("Segoe UI", 11), background=app_bg, foreground=text_primary)
        style.configure("App.TFrame", background=app_bg)
        style.configure("Sidebar.TFrame", background=sidebar_bg)
        style.configure("SidebarSection.TFrame", background=panel_alt, borderwidth=1, relief="solid")
        style.configure("Toolbar.TFrame", background=panel_bg, borderwidth=1, relief="solid")
        style.configure("Workspace.TFrame", background=panel_bg, borderwidth=1, relief="solid")
        style.configure("Status.TFrame", background=panel_bg, borderwidth=1, relief="solid")
        style.configure("TSeparator", background=border)

        style.configure("SidebarTitle.TLabel", background=sidebar_bg, foreground="#F8FAFC", font=("Segoe UI", 16, "bold"))
        style.configure("SidebarSubtitle.TLabel", background=sidebar_bg, foreground=text_secondary, font=("Segoe UI", 10))
        style.configure("SidebarSectionTitle.TLabel", background=sidebar_bg, foreground="#D6DEE8", font=("Segoe UI", 10, "bold"))
        style.configure("SidebarMeta.TLabel", background=sidebar_bg, foreground="#D6DEE8", font=("Segoe UI", 10))

        style.configure("PanelTitle.TLabel", background=panel_bg, foreground="#E8EEF5", font=("Segoe UI", 11, "bold"))
        style.configure("PanelHelp.TLabel", background=panel_bg, foreground=text_secondary, font=("Segoe UI", 10))
        style.configure("Summary.TLabel", background=panel_bg, foreground=accent_purple, font=("Segoe UI", 10))
        style.configure("Status.TLabel", background=panel_bg, foreground="#DEE6EF", padding=(12, 10), font=("Segoe UI", 11))

        style.configure(
            "Action.TButton",
            padding=(12, 7),
            background="#343434",
            foreground=text_primary,
            borderwidth=1,
            focusthickness=0,
            focuscolor=panel_bg,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Action.TButton",
            background=[("disabled", "#2B2B2B"), ("active", "#3D3D3D"), ("!disabled", "#343434")],
            foreground=[("disabled", "#737373"), ("!disabled", text_primary)],
        )

        style.configure(
            "Primary.TButton",
            padding=(14, 8),
            background=accent_blue,
            foreground="#FFFFFF",
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("disabled", "#476584"), ("active", accent_blue_hover), ("!disabled", accent_blue)],
            foreground=[("disabled", "#E1EBF6"), ("!disabled", "#FFFFFF")],
        )

        style.configure(
            "Nav.TButton",
            padding=(10, 6),
            background=sidebar_bg,
            foreground="#C9D2DC",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI", 10),
        )
        style.map(
            "Nav.TButton",
            background=[("active", "#2B2B2B"), ("!disabled", sidebar_bg)],
            foreground=[("active", "#EEF2F7"), ("!disabled", "#B9C2CC")],
        )

        style.configure(
            "NavActive.TButton",
            padding=(10, 6),
            background=accent_blue,
            foreground="#FFFFFF",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "NavActive.TButton",
            background=[("active", accent_blue_hover), ("!disabled", accent_blue)],
            foreground=[("!disabled", "#FFFFFF")],
        )

        style.configure(
            "TEntry",
            fieldbackground=panel_alt,
            foreground=text_primary,
            borderwidth=1,
            insertcolor=text_primary,
            insertwidth=2,
        )
        style.configure(
            "TCombobox",
            fieldbackground=panel_alt,
            background=panel_bg,
            foreground=text_primary,
            insertcolor=text_primary,
            insertwidth=2,
            arrowsize=14,
        )
        style.map(
            "TEntry",
            fieldbackground=[("disabled", "#202020"), ("!disabled", panel_alt)],
            foreground=[("disabled", "#8B939C"), ("!disabled", text_primary)],
            bordercolor=[("focus", accent_blue), ("!focus", border)],
            lightcolor=[("focus", accent_blue), ("!focus", border)],
            darkcolor=[("focus", accent_blue), ("!focus", border)],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", panel_alt)],
            selectforeground=[("readonly", text_primary)],
            selectbackground=[("readonly", panel_alt)],
            foreground=[("readonly", text_primary)],
            bordercolor=[("focus", accent_blue), ("!focus", border)],
            lightcolor=[("focus", accent_blue), ("!focus", border)],
            darkcolor=[("focus", accent_blue), ("!focus", border)],
        )

        style.configure("TCheckbutton", background=panel_alt, foreground=text_primary)
        style.map(
            "TCheckbutton",
            foreground=[("disabled", "#6D6D6D"), ("!disabled", text_primary)],
            background=[("active", panel_alt), ("!disabled", panel_alt)],
        )

        style.configure("Treeview", rowheight=34, borderwidth=0, relief="flat", background="#252525", fieldbackground="#252525", foreground=text_primary, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"), background="#323232", foreground="#E9EFF6", relief="flat")
        style.map(
            "Treeview",
            background=[("selected", accent_blue)],
            foreground=[("selected", "#F8FBFF")],
        )
        style.map("Treeview.Heading", background=[("active", "#3A3A3A")])

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        root = ttk.Frame(self, style="App.TFrame")
        root.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=0, minsize=236)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(root, style="Sidebar.TFrame", padding=(14, 14, 14, 14))
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(5, weight=1)

        ttk.Label(sidebar, text="Export Batch Renamer", style="SidebarTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            sidebar,
            text="Creative batch delivery workspace",
            style="SidebarSubtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 10))
        ttk.Separator(sidebar, orient="horizontal").grid(row=2, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(sidebar, text="Tools", style="SidebarSectionTitle.TLabel").grid(
            row=3, column=0, sticky="w"
        )

        nav_frame = ttk.Frame(sidebar, style="Sidebar.TFrame")
        nav_frame.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        nav_frame.columnconfigure(0, weight=1)
        ttk.Button(nav_frame, text="Rename Workspace", style="NavActive.TButton").grid(
            row=0, column=0, sticky="ew", pady=(0, 6)
        )
        ttk.Button(nav_frame, text="Preset Library", style="Nav.TButton").grid(
            row=1, column=0, sticky="ew", pady=(0, 6)
        )
        ttk.Button(nav_frame, text="Undo Logs", style="Nav.TButton").grid(row=2, column=0, sticky="ew")

        extension_panel = ttk.Frame(sidebar, style="SidebarSection.TFrame", padding=(10, 10))
        extension_panel.grid(row=6, column=0, sticky="ew", pady=(14, 0))
        ttk.Label(extension_panel, text="Include Types", style="SidebarSectionTitle.TLabel").pack(
            side="top", anchor="w"
        )
        extension_options_grid = ttk.Frame(extension_panel, style="SidebarSection.TFrame")
        extension_options_grid.pack(fill="x", pady=(6, 0))
        for column in range(3):
            extension_options_grid.columnconfigure(column, weight=1)

        for index, extension in enumerate(VIDEO_EXTENSION_ORDER):
            grid_row = index // 3
            grid_col = index % 3
            ttk.Checkbutton(
                extension_options_grid,
                text=extension,
                variable=self.extension_vars[extension],
                command=self._handle_extension_toggle,
            ).grid(row=grid_row, column=grid_col, sticky="w", padx=(0, 8), pady=(2, 2))

        ttk.Checkbutton(
            extension_panel,
            text="Write undo log",
            variable=self.create_undo_log_var,
        ).pack(side="top", anchor="w", pady=(8, 0))

        self.rollback_button = ttk.Button(
            extension_panel,
            text="Rollback Last Rename",
            command=self.rollback_last_rename,
            state="disabled",
            style="Action.TButton",
        )
        self.rollback_button.pack(side="top", anchor="w", pady=(8, 0))

        self.summary_label = ttk.Label(
            sidebar,
            text="",
            style="SidebarMeta.TLabel",
            justify="left",
            wraplength=200,
        )
        self.summary_label.grid(row=7, column=0, sticky="sw", pady=(12, 0))

        content = ttk.Frame(root, style="App.TFrame", padding=(12, 12, 12, 12))
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(content, style="Toolbar.TFrame", padding=(12, 10))
        toolbar.grid(row=0, column=0, sticky="ew")
        for column in range(8):
            toolbar.columnconfigure(column, weight=1)

        ttk.Label(toolbar, text="Export Folder", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(toolbar, textvariable=self.folder_var).grid(
            row=0, column=1, columnspan=4, sticky="ew", padx=(8, 8)
        )
        ttk.Button(toolbar, text="Browse", command=self._choose_folder, style="Action.TButton").grid(
            row=0, column=5, sticky="ew", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Preview", command=self.generate_preview, style="Action.TButton").grid(
            row=0, column=6, sticky="ew", padx=(0, 8)
        )

        self.apply_button = ttk.Button(
            toolbar,
            text="Rename All",
            command=self.rename_all,
            state="disabled",
            style="Primary.TButton",
        )
        self.apply_button.grid(row=0, column=7, sticky="ew")

        ttk.Label(toolbar, text="Preset", style="PanelTitle.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.preset_combo = ttk.Combobox(
            toolbar,
            values=self._preset_names(),
            textvariable=self.preset_var,
            state="readonly",
        )
        self.preset_combo.grid(row=1, column=1, sticky="ew", padx=(8, 8), pady=(10, 0))
        ttk.Button(toolbar, text="Save Preset", command=self.save_current_preset, style="Action.TButton").grid(
            row=1, column=2, sticky="ew", padx=(0, 8), pady=(10, 0)
        )
        ttk.Button(toolbar, text="Delete Preset", command=self.delete_selected_preset, style="Action.TButton").grid(
            row=1, column=3, sticky="ew", padx=(0, 8), pady=(10, 0)
        )
        ttk.Label(toolbar, text="Prefix", style="PanelTitle.TLabel").grid(row=1, column=4, sticky="w", pady=(10, 0))
        ttk.Entry(toolbar, textvariable=self.prefix_var).grid(row=1, column=5, sticky="ew", padx=(8, 8), pady=(10, 0))
        ttk.Label(toolbar, text="Suffix", style="PanelTitle.TLabel").grid(row=1, column=6, sticky="w", pady=(10, 0))
        ttk.Entry(toolbar, textvariable=self.suffix_var).grid(row=1, column=7, sticky="ew", pady=(10, 0))

        ttk.Label(toolbar, text="Start", style="PanelTitle.TLabel").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(toolbar, textvariable=self.start_var).grid(row=2, column=1, sticky="ew", padx=(8, 8), pady=(10, 0))
        ttk.Label(toolbar, text="Padding", style="PanelTitle.TLabel").grid(row=2, column=2, sticky="w", pady=(10, 0))
        ttk.Entry(toolbar, textvariable=self.padding_var).grid(row=2, column=3, sticky="ew", padx=(8, 8), pady=(10, 0))
        ttk.Label(toolbar, text="Separator", style="PanelTitle.TLabel").grid(row=2, column=4, sticky="w", pady=(10, 0))
        self.separator_combo = ttk.Combobox(
            toolbar,
            values=SEPARATOR_OPTIONS,
            textvariable=self.separator_var,
            state="readonly",
            width=4,
        )
        self.separator_combo.grid(row=2, column=5, sticky="ew", padx=(8, 8), pady=(10, 0))
        ttk.Label(toolbar, text="Selection controls are below.", style="PanelHelp.TLabel").grid(
            row=2, column=6, columnspan=2, sticky="w", pady=(12, 0)
        )

        selection_bar = ttk.Frame(content, style="Toolbar.TFrame", padding=(12, 10))
        selection_bar.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        selection_bar.columnconfigure(0, weight=1)
        selection_bar.columnconfigure(1, weight=1)

        selection_actions = ttk.Frame(selection_bar, style="Toolbar.TFrame")
        selection_actions.grid(row=0, column=0, sticky="w")

        self.select_all_button = ttk.Button(
            selection_actions,
            text="Select All",
            command=self.select_all_files,
            state="disabled",
            style="Action.TButton",
        )
        self.select_all_button.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.select_none_button = ttk.Button(
            selection_actions,
            text="Select None",
            command=self.select_no_files,
            state="disabled",
            style="Action.TButton",
        )
        self.select_none_button.grid(row=0, column=1, padx=(0, 8), sticky="w")

        self.invert_selection_button = ttk.Button(
            selection_actions,
            text="Invert Selection",
            command=self.invert_visible_selection,
            state="disabled",
            style="Action.TButton",
        )
        self.invert_selection_button.grid(row=0, column=2, padx=(0, 8), sticky="w")

        self.use_highlighted_only_button = ttk.Button(
            selection_actions,
            text="Use Highlighted Only",
            command=self.use_highlighted_only_files,
            state="disabled",
            style="Action.TButton",
        )
        self.use_highlighted_only_button.grid(row=0, column=3, padx=(0, 8), sticky="w")

        self.include_highlighted_button = ttk.Button(
            selection_actions,
            text="Include Highlighted",
            command=self.include_highlighted_files,
            state="disabled",
            style="Action.TButton",
        )
        self.include_highlighted_button.grid(row=0, column=4, padx=(0, 8), sticky="w")

        self.exclude_highlighted_button = ttk.Button(
            selection_actions,
            text="Exclude Highlighted",
            command=self.exclude_highlighted_files,
            state="disabled",
            style="Action.TButton",
        )
        self.exclude_highlighted_button.grid(row=0, column=5, sticky="w")

        filter_panel = ttk.Frame(selection_bar, style="Toolbar.TFrame")
        filter_panel.grid(row=0, column=1, sticky="e")
        ttk.Label(filter_panel, text="Filter", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="e")
        self.filter_entry = ttk.Entry(filter_panel, textvariable=self.filter_var, width=28)
        self.filter_entry.grid(row=0, column=1, padx=(8, 6), sticky="e")
        ttk.Button(filter_panel, text="Clear", command=self.clear_filter, style="Action.TButton").grid(
            row=0, column=2, sticky="e"
        )
        self.filter_count_label = ttk.Label(filter_panel, text="", style="Summary.TLabel")
        self.filter_count_label.grid(row=1, column=0, columnspan=3, sticky="e", pady=(6, 0))

        workspace = ttk.Frame(content, style="Workspace.TFrame", padding=(10, 10))
        workspace.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        workspace.columnconfigure(0, weight=1)
        workspace.rowconfigure(1, weight=1)

        ttk.Label(workspace, text="Workspace", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            workspace,
            text="Click Include to toggle files or apply bulk actions above.",
            style="PanelHelp.TLabel",
        ).grid(row=0, column=1, sticky="e")

        table_frame = ttk.Frame(workspace, style="Workspace.TFrame")
        table_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.preview_table = ttk.Treeview(
            table_frame,
            columns=("include", "original", "new", "action"),
            show="headings",
            selectmode="extended",
        )
        self.preview_table.heading("include", text="Include")
        self.preview_table.heading("original", text="Original Name")
        self.preview_table.heading("new", text="New Name")
        self.preview_table.heading("action", text="Action")
        self.preview_table.column("include", width=86, minwidth=76, anchor="center", stretch=False)
        self.preview_table.column("original", width=330, minwidth=180, anchor="w", stretch=True)
        self.preview_table.column("new", width=330, minwidth=180, anchor="w", stretch=True)
        self.preview_table.column("action", width=110, minwidth=94, anchor="center", stretch=False)

        self.preview_table.tag_configure("even", background="#252525")
        self.preview_table.tag_configure("odd", background="#2E2E2E")
        self.preview_table.tag_configure("excluded", foreground="#B1BDC9")
        self.preview_table.tag_configure("noop", foreground="#93A1AF")

        y_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.preview_table.yview)
        x_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.preview_table.xview)
        self.preview_table.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)

        self.preview_table.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")

        status_frame = ttk.Frame(content, style="Status.TFrame")
        status_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)
        ttk.Label(status_frame, textvariable=self.status_var, anchor="w", style="Status.TLabel").grid(
            row=0, column=0, sticky="ew"
        )

        self._refresh_extension_summary()
        self._refresh_filter_summary(0, 0)

    def _apply_input_cursor_style(self) -> None:
        caret_color = "#F2F5F8"

        def visit(widget: tk.Misc) -> None:
            for child in widget.winfo_children():
                if isinstance(child, (tk.Entry, ttk.Entry, ttk.Combobox)):
                    try:
                        child.configure(
                            insertbackground=caret_color,
                            insertwidth=2,
                            selectbackground="#4A9CFF",
                            selectforeground=caret_color,
                        )
                    except tk.TclError:
                        pass
                visit(child)

        visit(self)

    def _bind_events(self) -> None:
        self.preset_var.trace_add("write", self._handle_preset_change)
        self.filter_var.trace_add("write", self._handle_filter_change)
        self.preview_table.bind("<Button-1>", self._handle_preview_table_click)

        for variable in (
            self.folder_var,
            self.prefix_var,
            self.suffix_var,
            self.separator_var,
            self.start_var,
            self.padding_var,
        ):
            variable.trace_add("write", self._mark_preview_stale)

    def _all_presets(self) -> dict[str, dict[str, str]]:
        all_presets = dict(PRESETS)
        all_presets.update(self.custom_presets)
        return all_presets

    def _preset_names(self) -> list[str]:
        custom_names = sorted(self.custom_presets.keys(), key=lambda value: value.lower())
        return [*PRESETS.keys(), *custom_names, CUSTOM_PRESET]

    def _refresh_preset_options(self) -> None:
        self.preset_combo.configure(values=self._preset_names())

    def save_current_preset(self) -> None:
        preset_name = simpledialog.askstring(
            "Save preset",
            "Preset name:",
            parent=self,
        )
        if preset_name is None:
            return

        clean_name = preset_name.strip()
        if not clean_name:
            messagebox.showerror("Save preset", "Preset name is required.")
            return
        if clean_name == CUSTOM_PRESET:
            messagebox.showerror("Save preset", f"{CUSTOM_PRESET} is reserved.")
            return
        if clean_name in PRESETS:
            messagebox.showerror("Save preset", "Built-in preset names cannot be overwritten.")
            return

        prefix = self.prefix_var.get()
        suffix = self.suffix_var.get()
        input_errors = validate_naming_inputs(prefix=prefix, suffix=suffix, start_number=0, number_padding=0)
        if input_errors:
            self._show_blocking_errors("Save preset", input_errors)
            return

        if clean_name in self.custom_presets:
            overwrite = messagebox.askyesno(
                "Overwrite preset",
                f"Preset '{clean_name}' already exists. Overwrite it?",
                icon="question",
            )
            if not overwrite:
                return

        self.custom_presets[clean_name] = {
            "prefix": prefix,
            "suffix": suffix,
        }

        try:
            save_custom_presets(self.app_root, self.custom_presets)
        except OSError as exc:
            self._show_blocking_errors("Save preset", [f"Could not save preset: {exc}"])
            return

        self._refresh_preset_options()
        self.preset_var.set(clean_name)
        self.status_var.set(f"Preset saved: {clean_name}")

    def delete_selected_preset(self) -> None:
        preset_name = self.preset_var.get().strip()
        if preset_name in PRESETS:
            messagebox.showinfo("Delete preset", "Built-in presets cannot be deleted.")
            return
        if preset_name == CUSTOM_PRESET:
            messagebox.showinfo("Delete preset", "Select a saved preset first.")
            return
        if preset_name not in self.custom_presets:
            messagebox.showinfo("Delete preset", "Selected preset was not found.")
            return

        confirm = messagebox.askyesno(
            "Delete preset",
            f"Delete preset '{preset_name}'?",
            icon="warning",
        )
        if not confirm:
            return

        del self.custom_presets[preset_name]
        try:
            save_custom_presets(self.app_root, self.custom_presets)
        except OSError as exc:
            self._show_blocking_errors("Delete preset", [f"Could not save preset changes: {exc}"])
            return

        self._refresh_preset_options()
        self.preset_var.set(CUSTOM_PRESET)
        self.status_var.set(f"Preset deleted: {preset_name}")

    def _build_settings_payload(self) -> dict[str, object]:
        selected_preset = self.preset_var.get().strip() or CUSTOM_PRESET
        all_presets = self._all_presets()

        if selected_preset in all_presets:
            preset = all_presets[selected_preset]
            if (
                selected_preset != CUSTOM_PRESET
                and (self.prefix_var.get() != preset["prefix"] or self.suffix_var.get() != preset["suffix"])
            ):
                selected_preset = CUSTOM_PRESET
        else:
            selected_preset = CUSTOM_PRESET

        return {
            "folder": self.folder_var.get().strip(),
            "selected_preset": selected_preset,
            "prefix": self.prefix_var.get(),
            "suffix": self.suffix_var.get(),
            "separator": self.separator_var.get() if self.separator_var.get() in SEPARATOR_OPTIONS else DEFAULT_SEPARATOR,
            "start_number": self.start_var.get().strip(),
            "padding": self.padding_var.get().strip(),
            "selected_extensions": [
                extension for extension in VIDEO_EXTENSION_ORDER if self.extension_vars[extension].get()
            ],
            "create_undo_log": bool(self.create_undo_log_var.get()),
            "filter_query": self.filter_var.get(),
            "window_geometry": self.geometry(),
        }

    def _save_current_settings(self) -> None:
        try:
            save_app_settings(self.app_root, self._build_settings_payload())
        except OSError:
            # Ignore save failures to avoid blocking app close.
            return

    def _restore_saved_settings(self) -> None:
        settings = load_app_settings(self.app_root)
        if not settings:
            return

        geometry = settings.get("window_geometry")
        if isinstance(geometry, str) and "x" in geometry:
            try:
                self.geometry(geometry)
            except tk.TclError:
                pass

        folder = settings.get("folder")
        if isinstance(folder, str):
            self.folder_var.set(folder)

        start_number = settings.get("start_number")
        if isinstance(start_number, str) and start_number.strip():
            self.start_var.set(start_number)

        padding = settings.get("padding")
        if isinstance(padding, str) and padding.strip():
            self.padding_var.set(padding)

        separator = settings.get("separator")
        if isinstance(separator, str) and separator in SEPARATOR_OPTIONS:
            self.separator_var.set(separator)

        selected_extensions = settings.get("selected_extensions")
        if isinstance(selected_extensions, list):
            selected_set = {
                extension
                for extension in selected_extensions
                if isinstance(extension, str) and extension in self.extension_vars
            }
            if selected_set:
                for extension, variable in self.extension_vars.items():
                    variable.set(extension in selected_set)

        create_undo_log = settings.get("create_undo_log")
        if isinstance(create_undo_log, bool):
            self.create_undo_log_var.set(create_undo_log)

        selected_preset = settings.get("selected_preset")
        all_presets = self._all_presets()
        if isinstance(selected_preset, str) and selected_preset in all_presets:
            self.preset_var.set(selected_preset)
        else:
            self.preset_var.set(CUSTOM_PRESET)

        if self.preset_var.get() == CUSTOM_PRESET:
            prefix = settings.get("prefix")
            suffix = settings.get("suffix")
            if isinstance(prefix, str):
                self.prefix_var.set(prefix)
            if isinstance(suffix, str):
                self.suffix_var.set(suffix)

        filter_query = settings.get("filter_query")
        if isinstance(filter_query, str):
            self.filter_var.set(filter_query)

        self._refresh_extension_summary()

    def _on_close(self) -> None:
        self._save_current_settings()
        self.destroy()

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(title="Choose folder with exported videos")
        if selected:
            self.folder_var.set(selected)

    def _handle_preset_change(self, *_: object) -> None:
        preset_name = self.preset_var.get()
        preset = self._all_presets().get(preset_name)
        if preset:
            self.prefix_var.set(preset["prefix"])
            self.suffix_var.set(preset["suffix"])

    def _handle_extension_toggle(self) -> None:
        self._refresh_extension_summary()
        self._mark_preview_stale()

    def _handle_filter_change(self, *_: object) -> None:
        if not self.preview_items:
            self._refresh_filter_summary(0, 0)
            return

        self._render_preview_table()
        if self.preview_is_fresh and not self.preview_errors:
            self._update_ready_status()

    def clear_filter(self) -> None:
        if self.filter_var.get():
            self.filter_var.set("")

    def _refresh_extension_summary(self) -> None:
        selected_extensions = [
            extension
            for extension in VIDEO_EXTENSION_ORDER
            if self.extension_vars[extension].get()
        ]
        if selected_extensions:
            summary = "Selected types: " + ", ".join(selected_extensions)
        else:
            summary = "Selected types: none"

        self.summary_label.configure(text=summary)

    def _refresh_filter_summary(self, visible_count: int, total_count: int) -> None:
        query = self.filter_var.get().strip()
        if total_count == 0:
            self.filter_count_label.configure(text="Showing 0 files")
            return

        if query:
            self.filter_count_label.configure(text=f"Showing {visible_count} of {total_count} files")
        else:
            self.filter_count_label.configure(text=f"Showing {total_count} files")

    def _mark_preview_stale(self, *_: object) -> None:
        self.preview_is_fresh = False
        self.apply_button.state(["disabled"])
        self._set_select_buttons_enabled(False)
        self.status_var.set("Inputs changed. Click Preview to refresh.")

    def _set_rollback_available(self, is_available: bool) -> None:
        if is_available:
            self.rollback_button.state(["!disabled"])
        else:
            self.rollback_button.state(["disabled"])

    def _parse_int(self, value: str, field_name: str) -> int:
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an integer.") from exc

    def _get_folder(self) -> Path:
        folder_text = self.folder_var.get().strip()
        if not folder_text:
            raise ValueError("Please choose a folder first.")

        folder = Path(folder_text)
        if not folder.exists() or not folder.is_dir():
            raise ValueError("Selected folder does not exist.")

        return folder

    def _show_blocking_errors(self, title: str, errors: list[str]) -> None:
        error_body = "\n".join(errors)
        messagebox.showerror(title, error_body)

    def _set_select_buttons_enabled(self, is_enabled: bool) -> None:
        if is_enabled:
            self.select_all_button.state(["!disabled"])
            self.select_none_button.state(["!disabled"])
            self.invert_selection_button.state(["!disabled"])
            self.include_highlighted_button.state(["!disabled"])
            self.exclude_highlighted_button.state(["!disabled"])
            self.use_highlighted_only_button.state(["!disabled"])
        else:
            self.select_all_button.state(["disabled"])
            self.select_none_button.state(["disabled"])
            self.invert_selection_button.state(["disabled"])
            self.include_highlighted_button.state(["disabled"])
            self.exclude_highlighted_button.state(["disabled"])
            self.use_highlighted_only_button.state(["disabled"])

    def _get_selected_extensions(self) -> set[str]:
        selected_extensions = {
            extension
            for extension, variable in self.extension_vars.items()
            if variable.get()
        }
        if not selected_extensions:
            raise ValueError("Select at least one extension type.")
        return selected_extensions

    def _item_key(self, item: RenameItem) -> str:
        return str(item.source_path)

    def _sync_include_state_with_preview_items(self) -> None:
        active_keys: set[str] = set()
        for item in self.preview_items:
            key = self._item_key(item)
            active_keys.add(key)
            if key not in self.include_state_by_source:
                self.include_state_by_source[key] = not item.is_noop
            if item.is_noop:
                self.include_state_by_source[key] = False

        stale_keys = [key for key in self.include_state_by_source if key not in active_keys]
        for key in stale_keys:
            del self.include_state_by_source[key]

    def _visible_preview_items(self) -> list[RenameItem]:
        query = self.filter_var.get()
        return [
            item for item in self.preview_items if preview_item_matches_query(item, query)
        ]

    def _clear_preview_table(self) -> None:
        for item_id in self.preview_table.get_children():
            self.preview_table.delete(item_id)
        self.row_item_map = {}
        self.row_include_map = {}
        self.row_index_map = {}

    def _refresh_row_visual_state(self, row_id: str) -> None:
        item = self.row_item_map.get(row_id)
        if not item:
            return

        row_index = self.row_index_map.get(row_id, 0)
        tags: list[str] = ["even" if row_index % 2 == 0 else "odd"]

        if item.is_noop:
            tags.append("noop")
        elif not self.row_include_map.get(row_id, False):
            tags.append("excluded")

        self.preview_table.item(row_id, tags=tuple(tags))

    def _set_row_included(self, row_id: str, is_included: bool) -> None:
        item = self.row_item_map.get(row_id)
        if not item:
            return

        include_value = bool(is_included and not item.is_noop)
        key = self._item_key(item)

        self.include_state_by_source[key] = include_value
        self.row_include_map[row_id] = include_value
        self.preview_table.set(row_id, "include", "Yes" if include_value else "No")
        self._refresh_row_visual_state(row_id)

    def _render_preview_table(self) -> None:
        self._clear_preview_table()
        visible_items = self._visible_preview_items()

        for index, item in enumerate(visible_items):
            key = self._item_key(item)
            include_value = self.include_state_by_source.get(key, False)
            action = "No change" if item.is_noop else "Rename"
            row_id = self.preview_table.insert(
                "",
                "end",
                values=("Yes" if include_value else "No", item.source_name, item.target_name, action),
            )
            self.row_item_map[row_id] = item
            self.row_include_map[row_id] = include_value
            self.row_index_map[row_id] = index
            self._refresh_row_visual_state(row_id)

        self._refresh_filter_summary(len(visible_items), len(self.preview_items))

    def _populate_preview_table(self, items: list[RenameItem]) -> None:
        self.preview_items = items
        self._sync_include_state_with_preview_items()
        self._render_preview_table()

    def _get_selected_preview_items(self) -> list[RenameItem]:
        selected_items: list[RenameItem] = []
        for item in self.preview_items:
            if item.is_noop:
                continue

            key = self._item_key(item)
            if self.include_state_by_source.get(key, False):
                selected_items.append(item)

        return selected_items

    def _update_ready_status(self) -> None:
        rename_count = sum(1 for item in self.preview_items if not item.is_noop)
        no_change_count = len(self.preview_items) - rename_count
        selected_count = len(self._get_selected_preview_items())
        deselected_count = max(rename_count - selected_count, 0)
        visible_count = len(self.row_item_map)

        if rename_count == 0:
            self.apply_button.state(["disabled"])
            self._set_select_buttons_enabled(False)
            self.status_var.set(
                f"Preview ready. {no_change_count} file(s) already match this pattern."
            )
            return

        self._set_select_buttons_enabled(True)
        if selected_count == 0:
            self.apply_button.state(["disabled"])
            self.status_var.set(
                f"Preview ready. {rename_count} renamable, {no_change_count} unchanged. "
                "Select at least one file."
            )
            return

        filtered_note = ""
        if self.filter_var.get().strip():
            filtered_note = f" Showing {visible_count} filtered rows."

        self.apply_button.state(["!disabled"])
        self.status_var.set(
            f"Preview ready. {selected_count} selected, {deselected_count} deselected, "
            f"{no_change_count} unchanged.{filtered_note}"
        )

    def select_all_files(self) -> None:
        for item in self.preview_items:
            if item.is_noop:
                continue
            self.include_state_by_source[self._item_key(item)] = True

        self._render_preview_table()
        if self.preview_is_fresh and not self.preview_errors:
            self._update_ready_status()

    def select_no_files(self) -> None:
        for item in self.preview_items:
            if item.is_noop:
                continue
            self.include_state_by_source[self._item_key(item)] = False

        self._render_preview_table()
        if self.preview_is_fresh and not self.preview_errors:
            self._update_ready_status()

    def invert_visible_selection(self) -> None:
        row_ids = self.preview_table.get_children()
        if not row_ids:
            messagebox.showinfo("No files", "No files are visible in the current filter.")
            return

        for row_id in row_ids:
            item = self.row_item_map.get(row_id)
            if not item or item.is_noop:
                continue
            current_state = self.row_include_map.get(row_id, False)
            self._set_row_included(row_id, not current_state)

        if self.preview_is_fresh and not self.preview_errors:
            self._update_ready_status()

    def include_highlighted_files(self) -> None:
        highlighted_rows = self.preview_table.selection()
        if not highlighted_rows:
            messagebox.showinfo(
                "No highlighted files",
                "Highlight one or more files in the preview first.",
            )
            return

        for row_id in highlighted_rows:
            self._set_row_included(row_id, True)

        if self.preview_is_fresh and not self.preview_errors:
            self._update_ready_status()

    def use_highlighted_only_files(self) -> None:
        highlighted_rows = self.preview_table.selection()
        if not highlighted_rows:
            messagebox.showinfo(
                "No highlighted files",
                "Highlight one or more files in the preview first.",
            )
            return

        highlighted_keys: set[str] = set()
        for row_id in highlighted_rows:
            item = self.row_item_map.get(row_id)
            if item and not item.is_noop:
                highlighted_keys.add(self._item_key(item))

        for item in self.preview_items:
            if item.is_noop:
                continue
            item_key = self._item_key(item)
            self.include_state_by_source[item_key] = item_key in highlighted_keys

        self._render_preview_table()
        if self.preview_is_fresh and not self.preview_errors:
            self._update_ready_status()

    def exclude_highlighted_files(self) -> None:
        highlighted_rows = self.preview_table.selection()
        if not highlighted_rows:
            messagebox.showinfo(
                "No highlighted files",
                "Highlight one or more files in the preview first.",
            )
            return

        for row_id in highlighted_rows:
            self._set_row_included(row_id, False)

        if self.preview_is_fresh and not self.preview_errors:
            self._update_ready_status()

    def _handle_preview_table_click(self, event: tk.Event) -> str | None:
        region = self.preview_table.identify("region", event.x, event.y)
        if region != "cell":
            return None

        row_id = self.preview_table.identify_row(event.y)
        column_id = self.preview_table.identify_column(event.x)
        if not row_id or column_id != "#1":
            return None

        item = self.row_item_map.get(row_id)
        if not item or item.is_noop:
            return "break"

        current_state = self.row_include_map.get(row_id, False)
        self._set_row_included(row_id, not current_state)

        if self.preview_is_fresh and not self.preview_errors:
            self._update_ready_status()

        return "break"

    def generate_preview(self) -> None:
        try:
            folder = self._get_folder()
            start_number = self._parse_int(self.start_var.get().strip(), "Starting number")
            padding = self._parse_int(self.padding_var.get().strip(), "Padding")
            selected_extensions = self._get_selected_extensions()
        except ValueError as exc:
            self._show_blocking_errors("Preview error", [str(exc)])
            return

        prefix = self.prefix_var.get()
        suffix = self.suffix_var.get()
        separator = self.separator_var.get() if self.separator_var.get() in SEPARATOR_OPTIONS else DEFAULT_SEPARATOR
        source_files = discover_video_files(folder, selected_extensions)

        if not source_files:
            self.preview_items = []
            self.preview_errors = []
            self.preview_is_fresh = False
            self.include_state_by_source = {}
            self._clear_preview_table()
            self._set_select_buttons_enabled(False)
            self._refresh_filter_summary(0, 0)
            self.status_var.set("No supported video files found in this folder.")
            self.apply_button.state(["disabled"])
            return

        errors = validate_naming_inputs(
            prefix=prefix,
            suffix=suffix,
            start_number=start_number,
            number_padding=padding,
        )

        preview_items = build_rename_items(
            source_files=source_files,
            prefix=prefix,
            suffix=suffix,
            start_number=start_number,
            number_padding=padding,
            separator=separator,
        )
        errors.extend(validate_preview_items(preview_items))

        self.preview_errors = errors
        self._populate_preview_table(preview_items)

        if errors:
            self.preview_is_fresh = False
            self.apply_button.state(["disabled"])
            self._set_select_buttons_enabled(False)
            self.status_var.set(f"Preview blocked by {len(errors)} issue(s).")
            self._show_blocking_errors("Cannot rename yet", errors)
            return

        self.preview_is_fresh = True
        self._update_ready_status()

    def rename_all(self) -> None:
        if not self.preview_items:
            messagebox.showinfo("Nothing to rename", "Generate a preview first.")
            return

        if not self.preview_is_fresh:
            messagebox.showinfo(
                "Preview outdated",
                "Inputs changed. Click Preview before renaming.",
            )
            return

        if self.preview_errors:
            self._show_blocking_errors("Cannot rename yet", self.preview_errors)
            return

        selected_items = self._get_selected_preview_items()
        if not selected_items:
            messagebox.showinfo("Nothing selected", "Select at least one file to rename.")
            return

        selection_errors = validate_preview_items(selected_items)
        if selection_errors:
            self._show_blocking_errors("Cannot rename selected files", selection_errors)
            return

        confirm = messagebox.askyesno(
            "Apply rename",
            f"Rename {len(selected_items)} selected file(s)?",
            icon="question",
        )
        if not confirm:
            return

        result = apply_rename_plan(selected_items)
        if result.errors:
            self.status_var.set("Rename failed. See error dialog for details.")
            self._show_blocking_errors("Rename failed", result.errors)
            return

        undo_log_name = ""
        if self.create_undo_log_var.get() and result.renamed_count > 0:
            try:
                folder = self._get_folder()
                self.last_undo_log_path = create_undo_log_file(selected_items, folder)
                self._set_rollback_available(True)
                undo_log_name = self.last_undo_log_path.name
            except Exception as exc:
                self.last_undo_log_path = None
                self._set_rollback_available(False)
                self._show_blocking_errors("Undo log warning", [f"Rename succeeded but undo log failed: {exc}"])
        else:
            self.last_undo_log_path = None
            self._set_rollback_available(False)

        message = f"Renamed {result.renamed_count} file(s)."
        if result.skipped_count:
            message += f" {result.skipped_count} file(s) already matched and were skipped."
        if undo_log_name:
            message += f" Undo log saved as {undo_log_name}."

        self.status_var.set(message)
        messagebox.showinfo("Rename complete", message)
        self.generate_preview()

    def rollback_last_rename(self) -> None:
        if not self.last_undo_log_path:
            messagebox.showinfo(
                "No rollback available",
                "No undo log is available for rollback in this session.",
            )
            return

        if not self.last_undo_log_path.exists():
            self._set_rollback_available(False)
            messagebox.showerror(
                "Undo log missing",
                f"Undo log file was not found:\n{self.last_undo_log_path}",
            )
            return

        confirm = messagebox.askyesno(
            "Rollback rename",
            "Rollback the last rename operation now?",
            icon="question",
        )
        if not confirm:
            return

        try:
            rollback_items = load_rollback_items(self.last_undo_log_path)
        except Exception as exc:
            self._show_blocking_errors("Undo log error", [f"Could not load undo log: {exc}"])
            return

        if not rollback_items:
            messagebox.showinfo("Nothing to rollback", "Undo log has no rename entries.")
            return

        missing_sources = [item.source_name for item in rollback_items if not item.source_path.exists()]
        if missing_sources:
            self._show_blocking_errors(
                "Rollback blocked",
                ["Missing files required for rollback:"] + missing_sources,
            )
            return

        validation_errors = validate_preview_items(rollback_items)
        if validation_errors:
            self._show_blocking_errors("Rollback blocked", validation_errors)
            return

        result = apply_rename_plan(rollback_items)
        if result.errors:
            self._show_blocking_errors("Rollback failed", result.errors)
            return

        self._set_rollback_available(False)
        restored_count = result.renamed_count
        self.status_var.set(f"Rollback complete. Restored {restored_count} file(s).")
        messagebox.showinfo("Rollback complete", f"Restored {restored_count} file(s).")
        self.generate_preview()


def _acquire_single_instance_mutex() -> int | None:
    if not hasattr(ctypes, "windll"):
        return None

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.GetLastError.argtypes = []
    kernel32.GetLastError.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    mutex_handle = kernel32.CreateMutexW(None, False, WINDOWS_MUTEX_NAME)
    if not mutex_handle:
        return None

    error_already_exists = 183
    if kernel32.GetLastError() == error_already_exists:
        kernel32.CloseHandle(mutex_handle)
        return 0

    return int(mutex_handle)


def _release_single_instance_mutex(mutex_handle: int | None) -> None:
    if not mutex_handle:
        return

    if not hasattr(ctypes, "windll"):
        return

    kernel32 = ctypes.windll.kernel32
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle(mutex_handle)


def _focus_existing_window() -> None:
    if not hasattr(ctypes, "windll"):
        return

    user32 = ctypes.windll.user32
    user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.restype = wintypes.BOOL

    found_hwnd: list[int | None] = [None]

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_windows_callback(hwnd: int, _: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True

        title_length = user32.GetWindowTextLengthW(hwnd)
        if title_length <= 0:
            return True

        title_buffer = ctypes.create_unicode_buffer(title_length + 1)
        user32.GetWindowTextW(hwnd, title_buffer, len(title_buffer))
        if title_buffer.value == WINDOWS_APP_TITLE:
            found_hwnd[0] = hwnd
            return False

        return True

    user32.EnumWindows(enum_windows_callback, 0)
    target = found_hwnd[0]
    if not target:
        return

    sw_restore = 9
    user32.ShowWindow(target, sw_restore)
    user32.BringWindowToTop(target)
    user32.SetForegroundWindow(target)


def main() -> None:
    mutex_handle = _acquire_single_instance_mutex()

    # None means mutex setup failed, so continue without blocking startup.
    if mutex_handle == 0:
        _focus_existing_window()
        return

    try:
        app = RenameToolApp()
        app.mainloop()
    finally:
        _release_single_instance_mutex(mutex_handle)


if __name__ == "__main__":
    main()
