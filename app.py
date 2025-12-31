import html
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.font as tkfont
from pathlib import Path
from datetime import datetime, timezone

from ddd_parser import DddHeader, parse_summary
from ddd_structs import (
    format_card_type,
    format_card_slot,
    format_card_status,
    format_control_type,
    format_driving_status,
    format_card_generation,
    format_driver_event_type,
    format_event_card_slot,
    format_event_fault_type,
    format_holder_name,
    format_nation_numeric,
    format_activity,
    format_minutes,
    format_odometer,
    format_overspeed_event_type,
    format_speed,
    format_specific_condition_type,
    format_place_entry_type,
    format_gnss_accuracy,
    format_gnss_coordinate,
    format_slot,
    format_time_real,
    is_card_number_missing,
)


class DddReaderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("dddPy - DDD File Reader")
        self.minsize(720, 640)

        self.colors = {}
        self.icon_image = None
        for icon_name in ("icon.png", "dddPyIcon.png"):
            icon_path = Path(__file__).with_name(icon_name)
            if icon_path.exists():
                try:
                    icon_image = tk.PhotoImage(file=str(icon_path))
                except tk.TclError:
                    continue
                self.icon_image = icon_image
                self.iconphoto(True, icon_image)
                break

        self.current_file_path = None
        self.current_summary = None
        self.file_path = tk.StringVar()
        self.status_text = tk.StringVar(value="No file selected.")
        self.validity_text = tk.StringVar(value="Validity: Not checked.")
        self.file_type_text = tk.StringVar(value="File type: Unknown")
        self.overspeed_last_control_var = tk.StringVar(value="")
        self.overspeed_first_since_var = tk.StringVar(value="")
        self.overspeed_count_var = tk.StringVar(value="")
        self.activity_day_var = tk.StringVar()
        self._activity_day_map = {}
        self._current_activity_day = None

        self._apply_theme()
        self._build_ui()
        self._enable_tree_multiselect()
        self.bind_all("<Control-c>", self._copy_selection)
        self.bind_all("<Control-C>", self._copy_selection)

    def _apply_theme(self) -> None:
        colors = {
            "bg": "#EEF1F5",
            "panel": "#FFFFFF",
            "border": "#D9DEE7",
            "accent": "#1F6FEB",
            "accent_dark": "#164EB6",
            "text": "#1F2937",
            "subtext": "#6B7280",
            "success": "#15803D",
            "danger": "#B91C1C",
        }
        self.colors = colors
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        base_family = self._pick_font_family()
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family=base_family, size=10)
        heading_font = tkfont.Font(family=base_family, size=10, weight="bold")
        title_font = tkfont.Font(family=base_family, size=16, weight="bold")

        self.configure(background=colors["bg"])
        style.configure("TFrame", background=colors["panel"])
        style.configure("Header.TFrame", background=colors["panel"])
        style.configure("TLabel", background=colors["panel"], foreground=colors["text"])
        style.configure("Subtle.TLabel", background=colors["panel"], foreground=colors["subtext"])
        style.configure("Title.TLabel", background=colors["panel"], foreground=colors["text"], font=title_font)
        style.configure("Section.TLabel", background=colors["panel"], foreground=colors["text"], font=heading_font)
        style.configure("Valid.TLabel", background=colors["panel"], foreground=colors["success"])
        style.configure("Invalid.TLabel", background=colors["panel"], foreground=colors["danger"])
        style.configure("Neutral.TLabel", background=colors["panel"], foreground=colors["text"])

        style.configure(
            "Accent.TButton",
            background=colors["accent"],
            foreground="#FFFFFF",
            padding=(12, 6),
            borderwidth=0,
        )
        style.map(
            "Accent.TButton",
            background=[("active", colors["accent_dark"])],
            foreground=[("disabled", "#D1D5DB")],
        )
        style.configure("TButton", padding=(10, 6))
        style.configure("TEntry", fieldbackground="#FFFFFF", bordercolor=colors["border"], padding=6)

        style.configure("TNotebook", background=colors["bg"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background="#E5E7EB",
            padding=(12, 6),
            font=heading_font,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", colors["panel"])],
            foreground=[("selected", colors["text"]), ("!selected", colors["subtext"])],
        )

        style.configure(
            "Treeview",
            background=colors["panel"],
            fieldbackground=colors["panel"],
            foreground=colors["text"],
            rowheight=24,
            bordercolor=colors["border"],
        )
        style.configure(
            "Treeview.Heading",
            background="#E9ECF2",
            foreground=colors["text"],
            font=heading_font,
        )
        style.map(
            "Treeview",
            background=[("selected", "#D6E4FF")],
            foreground=[("selected", colors["text"])],
        )

    def _pick_font_family(self) -> str:
        families = set(tkfont.families())
        for candidate in ("Segoe UI", "Helvetica Neue", "DejaVu Sans", "Liberation Sans"):
            if candidate in families:
                return candidate
        return tkfont.nametofont("TkDefaultFont").actual("family")

    def _build_ui(self) -> None:
        self.main_notebook = ttk.Notebook(self)
        self.main_notebook.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.summary_tab = ttk.Frame(self.main_notebook)
        self.vehicle_unit_tab = ttk.Frame(self.main_notebook)
        self.driver_card_tab = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.summary_tab, text="Summary")
        self.main_notebook.add(self.vehicle_unit_tab, text="Vehicle Unit")
        self.main_notebook.add(self.driver_card_tab, text="Driver Card")

        vu_notebook = ttk.Notebook(self.vehicle_unit_tab)
        vu_notebook.grid(row=0, column=0, sticky="nsew")
        self.vehicle_unit_tab.columnconfigure(0, weight=1)
        self.vehicle_unit_tab.rowconfigure(0, weight=1)

        ident_tab = ttk.Frame(vu_notebook)
        report_tab = ttk.Frame(vu_notebook)
        events_tab = ttk.Frame(vu_notebook)
        activities_tab = ttk.Frame(vu_notebook)
        vu_notebook.add(ident_tab, text="Identification")
        vu_notebook.add(report_tab, text="Report")
        vu_notebook.add(events_tab, text="Events/Faults")
        vu_notebook.add(activities_tab, text="Activities")

        summary = ttk.Frame(self.summary_tab, padding=16)
        summary.grid(row=0, column=0, sticky="nsew")
        self.summary_tab.columnconfigure(0, weight=1)
        self.summary_tab.rowconfigure(0, weight=1)
        summary.columnconfigure(0, weight=1)
        summary.rowconfigure(5, weight=1)
        summary.rowconfigure(7, weight=1)

        header_frame = ttk.Frame(summary, style="Header.TFrame")
        header_frame.grid(row=0, column=0, columnspan=4, sticky="ew")
        header_frame.columnconfigure(0, weight=1)

        header_left = ttk.Frame(header_frame, style="Header.TFrame")
        header_left.grid(row=0, column=0, sticky="w")
        header_left.columnconfigure(0, weight=1)

        ttk.Label(header_left, text="dddPy", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.validity_label = ttk.Label(
            header_left, textvariable=self.validity_text, style="Neutral.TLabel"
        )
        self.validity_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Label(header_left, textvariable=self.file_type_text, style="Subtle.TLabel").grid(
            row=2, column=0, sticky="w", pady=(2, 0)
        )

        self.logo_image = None
        logo_path = Path(__file__).with_name("logo.png")
        if logo_path.exists():
            try:
                logo_image = tk.PhotoImage(file=str(logo_path))
                scale = max(1, logo_image.width() // 260, logo_image.height() // 90)
                if scale > 1:
                    logo_image = logo_image.subsample(scale, scale)
                self.logo_image = logo_image
                ttk.Label(header_frame, image=self.logo_image).grid(
                    row=0, column=1, sticky="e"
                )
            except tk.TclError:
                self.logo_image = None

        ttk.Label(
            summary,
            text="Select a tachograph .ddd file to open:",
            style="Section.TLabel",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(10, 0))

        path_entry = ttk.Entry(summary, textvariable=self.file_path, state="readonly")
        path_entry.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(8, 0))

        ttk.Button(summary, text="Browse...", command=self._browse).grid(
            row=2, column=1, sticky="ew", pady=(8, 0)
        )
        ttk.Button(summary, text="Open", style="Accent.TButton", command=self._open_file).grid(
            row=2, column=2, sticky="ew", pady=(8, 0)
        )
        ttk.Button(summary, text="Export HTML", command=self._export_html).grid(
            row=2, column=3, sticky="ew", pady=(8, 0)
        )

        ttk.Label(summary, textvariable=self.status_text, style="Subtle.TLabel").grid(
            row=3, column=0, columnspan=4, sticky="w", pady=(8, 0)
        )

        ttk.Label(summary, text="Parsed header fields:", style="Section.TLabel").grid(
            row=4, column=0, columnspan=4, sticky="w", pady=(12, 0)
        )

        details_frame = ttk.Frame(summary)
        details_frame.grid(row=5, column=0, columnspan=4, sticky="nsew", pady=(6, 0))
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(0, weight=1)

        self.header_tree = ttk.Treeview(
            details_frame, columns=("value",), show="tree headings", height=7
        )
        self.header_tree.heading("#0", text="Field")
        self.header_tree.heading("value", text="Value")
        self.header_tree.column("#0", width=200, anchor="w")
        self.header_tree.column("value", anchor="w")

        scrollbar = ttk.Scrollbar(
            details_frame, orient="vertical", command=self.header_tree.yview
        )
        self.header_tree.configure(yscrollcommand=scrollbar.set)

        self.header_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Label(summary, text="File parts:", style="Section.TLabel").grid(
            row=6, column=0, columnspan=4, sticky="w", pady=(12, 0)
        )

        parts_frame = ttk.Frame(summary)
        parts_frame.grid(row=7, column=0, columnspan=4, sticky="nsew", pady=(6, 0))
        parts_frame.columnconfigure(0, weight=1)
        parts_frame.rowconfigure(0, weight=1)

        self.parts_tree = ttk.Treeview(
            parts_frame, columns=("part", "status", "note"), show="headings", height=6
        )
        self.parts_tree.heading("part", text="Part")
        self.parts_tree.heading("status", text="Status")
        self.parts_tree.heading("note", text="Note")
        self.parts_tree.column("part", width=200, anchor="w")
        self.parts_tree.column("status", width=120, anchor="w")
        self.parts_tree.column("note", anchor="w")

        parts_scrollbar = ttk.Scrollbar(
            parts_frame, orient="vertical", command=self.parts_tree.yview
        )
        self.parts_tree.configure(yscrollcommand=parts_scrollbar.set)

        self.parts_tree.grid(row=0, column=0, sticky="nsew")
        parts_scrollbar.grid(row=0, column=1, sticky="ns")

        style = ttk.Style()
        style.configure("Valid.TLabel", foreground="#1B5E20")
        style.configure("Invalid.TLabel", foreground="#B71C1C")
        style.configure("Neutral.TLabel", foreground="#333333")
        self.parts_tree.tag_configure("valid", foreground="#1B5E20")
        self.parts_tree.tag_configure("invalid", foreground="#B71C1C")
        self.parts_tree.tag_configure("missing", foreground="#6B6B6B")
        self.parts_tree.tag_configure("not_applicable", foreground="#6B6B6B")

        ident = ttk.Frame(ident_tab, padding=12)
        ident.grid(row=0, column=0, sticky="nsew")
        ident_tab.columnconfigure(0, weight=1)
        ident_tab.rowconfigure(0, weight=1)
        ident.columnconfigure(0, weight=1)
        ident.rowconfigure(1, weight=1)

        ttk.Label(ident, text="VU identification (heuristic):").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )

        ident_frame = ttk.Frame(ident)
        ident_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        ident_frame.columnconfigure(0, weight=1)
        ident_frame.rowconfigure(0, weight=1)

        self.ident_tree = ttk.Treeview(
            ident_frame, columns=("value",), show="tree headings", height=7
        )
        self.ident_tree.heading("#0", text="Field")
        self.ident_tree.heading("value", text="Value")
        self.ident_tree.column("#0", width=220, anchor="w")
        self.ident_tree.column("value", anchor="w")

        ident_scrollbar = ttk.Scrollbar(
            ident_frame, orient="vertical", command=self.ident_tree.yview
        )
        self.ident_tree.configure(yscrollcommand=ident_scrollbar.set)

        self.ident_tree.grid(row=0, column=0, sticky="nsew")
        ident_scrollbar.grid(row=0, column=1, sticky="ns")

        report = ttk.Frame(report_tab, padding=12)
        report.grid(row=0, column=0, sticky="nsew")
        report_tab.columnconfigure(0, weight=1)
        report_tab.rowconfigure(0, weight=1)
        report.columnconfigure(0, weight=1)
        report.rowconfigure(1, weight=1)
        report.rowconfigure(3, weight=1)
        report.rowconfigure(5, weight=1)

        ttk.Label(report, text="Overview:").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )

        overview_frame = ttk.Frame(report)
        overview_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        overview_frame.columnconfigure(0, weight=1)
        overview_frame.rowconfigure(0, weight=1)

        self.overview_tree = ttk.Treeview(
            overview_frame, columns=("value",), show="tree headings", height=10
        )
        self.overview_tree.heading("#0", text="Field")
        self.overview_tree.heading("value", text="Value")
        self.overview_tree.column("#0", width=260, anchor="w")
        self.overview_tree.column("value", anchor="w")

        overview_scrollbar = ttk.Scrollbar(
            overview_frame, orient="vertical", command=self.overview_tree.yview
        )
        self.overview_tree.configure(yscrollcommand=overview_scrollbar.set)

        self.overview_tree.grid(row=0, column=0, sticky="nsew")
        overview_scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Label(report, text="Company locks:").grid(
            row=2, column=0, sticky="w", pady=(0, 6)
        )

        locks_frame = ttk.Frame(report)
        locks_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
        locks_frame.columnconfigure(0, weight=1)
        locks_frame.rowconfigure(0, weight=1)

        self.company_locks_tree = ttk.Treeview(
            locks_frame,
            columns=("start", "end", "name", "address", "card"),
            show="headings",
            height=6,
        )
        self.company_locks_tree.heading("start", text="Start")
        self.company_locks_tree.heading("end", text="End")
        self.company_locks_tree.heading("name", text="Company Name")
        self.company_locks_tree.heading("address", text="Company Address")
        self.company_locks_tree.heading("card", text="Card Number")
        self.company_locks_tree.column("start", width=160, anchor="w")
        self.company_locks_tree.column("end", width=160, anchor="w")
        self.company_locks_tree.column("name", width=180, anchor="w")
        self.company_locks_tree.column("address", width=220, anchor="w")
        self.company_locks_tree.column("card", width=160, anchor="w")

        locks_scrollbar = ttk.Scrollbar(
            locks_frame, orient="vertical", command=self.company_locks_tree.yview
        )
        self.company_locks_tree.configure(yscrollcommand=locks_scrollbar.set)

        self.company_locks_tree.grid(row=0, column=0, sticky="nsew")
        locks_scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Label(report, text="Control activities:").grid(
            row=4, column=0, sticky="w", pady=(0, 6)
        )

        controls_frame = ttk.Frame(report)
        controls_frame.grid(row=5, column=0, sticky="nsew")
        controls_frame.columnconfigure(0, weight=1)
        controls_frame.rowconfigure(0, weight=1)

        self.control_tree = ttk.Treeview(
            controls_frame,
            columns=(
                "type",
                "time",
                "card_type",
                "nation",
                "card_number",
                "generation",
                "begin",
                "end",
            ),
            show="headings",
            height=7,
        )
        self.control_tree.heading("type", text="Type")
        self.control_tree.heading("time", text="Time")
        self.control_tree.heading("card_type", text="Card Type")
        self.control_tree.heading("nation", text="Card Issuing Member State")
        self.control_tree.heading("card_number", text="Card Number")
        self.control_tree.heading("generation", text="Card Generation")
        self.control_tree.heading("begin", text="Begin Period")
        self.control_tree.heading("end", text="End Period")

        self.control_tree.column("type", width=200, anchor="w")
        self.control_tree.column("time", width=160, anchor="w")
        self.control_tree.column("card_type", width=140, anchor="w")
        self.control_tree.column("nation", width=120, anchor="w")
        self.control_tree.column("card_number", width=160, anchor="w")
        self.control_tree.column("generation", width=110, anchor="w")
        self.control_tree.column("begin", width=160, anchor="w")
        self.control_tree.column("end", width=160, anchor="w")

        controls_scrollbar = ttk.Scrollbar(
            controls_frame, orient="vertical", command=self.control_tree.yview
        )
        self.control_tree.configure(yscrollcommand=controls_scrollbar.set)

        self.control_tree.grid(row=0, column=0, sticky="nsew")
        controls_scrollbar.grid(row=0, column=1, sticky="ns")

        events = ttk.Frame(events_tab, padding=12)
        events.grid(row=0, column=0, sticky="nsew")
        events_tab.columnconfigure(0, weight=1)
        events_tab.rowconfigure(0, weight=1)
        events.columnconfigure(0, weight=1)
        events.rowconfigure(3, weight=1)
        events.rowconfigure(5, weight=1)
        events.rowconfigure(7, weight=1)

        ttk.Label(events, text="Overspeed control:").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )

        overspeed_info = ttk.Frame(events)
        overspeed_info.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        overspeed_info.columnconfigure(1, weight=1)

        ttk.Label(overspeed_info, text="Last Overspeed Control Time:").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        ttk.Label(overspeed_info, textvariable=self.overspeed_last_control_var).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(overspeed_info, text="First Overspeed Since:").grid(
            row=1, column=0, sticky="w", padx=(0, 8)
        )
        ttk.Label(overspeed_info, textvariable=self.overspeed_first_since_var).grid(
            row=1, column=1, sticky="w"
        )
        ttk.Label(overspeed_info, text="Number Of Overspeed Since:").grid(
            row=2, column=0, sticky="w", padx=(0, 8)
        )
        ttk.Label(overspeed_info, textvariable=self.overspeed_count_var).grid(
            row=2, column=1, sticky="w"
        )

        ttk.Label(events, text="Fault data:").grid(
            row=2, column=0, sticky="w", pady=(0, 6)
        )

        faults_frame = ttk.Frame(events)
        faults_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
        faults_frame.columnconfigure(0, weight=1)
        faults_frame.rowconfigure(0, weight=1)

        self.faults_tree = ttk.Treeview(
            faults_frame,
            columns=(
                "type",
                "purpose",
                "begin",
                "end",
                "driver_begin",
                "driver_end",
                "codriver_begin",
                "codriver_end",
            ),
            show="headings",
            height=6,
        )
        self.faults_tree.heading("type", text="Fault Type")
        self.faults_tree.heading("purpose", text="Purpose")
        self.faults_tree.heading("begin", text="Begin")
        self.faults_tree.heading("end", text="End")
        self.faults_tree.heading("driver_begin", text="Driver Slot Begin")
        self.faults_tree.heading("driver_end", text="Driver Slot End")
        self.faults_tree.heading("codriver_begin", text="Codriver Slot Begin")
        self.faults_tree.heading("codriver_end", text="Codriver Slot End")

        self.faults_tree.column("type", width=220, anchor="w")
        self.faults_tree.column("purpose", width=80, anchor="w")
        self.faults_tree.column("begin", width=160, anchor="w")
        self.faults_tree.column("end", width=160, anchor="w")
        self.faults_tree.column("driver_begin", width=220, anchor="w")
        self.faults_tree.column("driver_end", width=220, anchor="w")
        self.faults_tree.column("codriver_begin", width=220, anchor="w")
        self.faults_tree.column("codriver_end", width=220, anchor="w")

        faults_scrollbar = ttk.Scrollbar(
            faults_frame, orient="vertical", command=self.faults_tree.yview
        )
        self.faults_tree.configure(yscrollcommand=faults_scrollbar.set)

        self.faults_tree.grid(row=0, column=0, sticky="nsew")
        faults_scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Label(events, text="Event data:").grid(
            row=4, column=0, sticky="w", pady=(0, 6)
        )

        events_frame = ttk.Frame(events)
        events_frame.grid(row=5, column=0, sticky="nsew", pady=(0, 12))
        events_frame.columnconfigure(0, weight=1)
        events_frame.rowconfigure(0, weight=1)

        self.events_tree = ttk.Treeview(
            events_frame,
            columns=(
                "type",
                "purpose",
                "begin",
                "end",
                "similar",
                "driver_begin",
                "driver_end",
                "codriver_begin",
                "codriver_end",
            ),
            show="headings",
            height=8,
        )
        self.events_tree.heading("type", text="Event Type")
        self.events_tree.heading("purpose", text="Purpose")
        self.events_tree.heading("begin", text="Begin")
        self.events_tree.heading("end", text="End")
        self.events_tree.heading("similar", text="Similar Events")
        self.events_tree.heading("driver_begin", text="Driver Slot Begin")
        self.events_tree.heading("driver_end", text="Driver Slot End")
        self.events_tree.heading("codriver_begin", text="Codriver Slot Begin")
        self.events_tree.heading("codriver_end", text="Codriver Slot End")

        self.events_tree.column("type", width=220, anchor="w")
        self.events_tree.column("purpose", width=80, anchor="w")
        self.events_tree.column("begin", width=160, anchor="w")
        self.events_tree.column("end", width=160, anchor="w")
        self.events_tree.column("similar", width=120, anchor="w")
        self.events_tree.column("driver_begin", width=220, anchor="w")
        self.events_tree.column("driver_end", width=220, anchor="w")
        self.events_tree.column("codriver_begin", width=220, anchor="w")
        self.events_tree.column("codriver_end", width=220, anchor="w")

        events_scrollbar = ttk.Scrollbar(
            events_frame, orient="vertical", command=self.events_tree.yview
        )
        self.events_tree.configure(yscrollcommand=events_scrollbar.set)

        self.events_tree.grid(row=0, column=0, sticky="nsew")
        events_scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Label(events, text="Overspeeding event data:").grid(
            row=6, column=0, sticky="w", pady=(0, 6)
        )

        overspeed_frame = ttk.Frame(events)
        overspeed_frame.grid(row=7, column=0, sticky="nsew")
        overspeed_frame.columnconfigure(0, weight=1)
        overspeed_frame.rowconfigure(0, weight=1)

        self.overspeed_tree = ttk.Treeview(
            overspeed_frame,
            columns=(
                "type",
                "begin",
                "end",
                "max_speed",
                "avg_speed",
                "similar",
                "card_type",
                "card_number",
                "nation",
            ),
            show="headings",
            height=8,
        )
        self.overspeed_tree.heading("type", text="Event Type")
        self.overspeed_tree.heading("begin", text="Begin")
        self.overspeed_tree.heading("end", text="End")
        self.overspeed_tree.heading("max_speed", text="Max Speed")
        self.overspeed_tree.heading("avg_speed", text="Avg Speed")
        self.overspeed_tree.heading("similar", text="Similar Events")
        self.overspeed_tree.heading("card_type", text="Card Type")
        self.overspeed_tree.heading("card_number", text="Card Number")
        self.overspeed_tree.heading("nation", text="Card Issuing State")

        self.overspeed_tree.column("type", width=160, anchor="w")
        self.overspeed_tree.column("begin", width=160, anchor="w")
        self.overspeed_tree.column("end", width=160, anchor="w")
        self.overspeed_tree.column("max_speed", width=90, anchor="w")
        self.overspeed_tree.column("avg_speed", width=90, anchor="w")
        self.overspeed_tree.column("similar", width=120, anchor="w")
        self.overspeed_tree.column("card_type", width=140, anchor="w")
        self.overspeed_tree.column("card_number", width=160, anchor="w")
        self.overspeed_tree.column("nation", width=140, anchor="w")

        overspeed_scrollbar = ttk.Scrollbar(
            overspeed_frame, orient="vertical", command=self.overspeed_tree.yview
        )
        self.overspeed_tree.configure(yscrollcommand=overspeed_scrollbar.set)

        self.overspeed_tree.grid(row=0, column=0, sticky="nsew")
        overspeed_scrollbar.grid(row=0, column=1, sticky="ns")

        driver_card = ttk.Notebook(self.driver_card_tab)
        driver_card.grid(row=0, column=0, sticky="nsew")
        self.driver_card_tab.columnconfigure(0, weight=1)
        self.driver_card_tab.rowconfigure(0, weight=1)

        card_ident_tab = ttk.Frame(driver_card)
        card_events_tab = ttk.Frame(driver_card)
        card_vehicles_tab = ttk.Frame(driver_card)
        card_places_tab = ttk.Frame(driver_card)
        card_conditions_tab = ttk.Frame(driver_card)
        card_units_tab = ttk.Frame(driver_card)
        driver_card.add(card_ident_tab, text="Identification")
        driver_card.add(card_events_tab, text="Events")
        driver_card.add(card_vehicles_tab, text="Vehicles")
        driver_card.add(card_places_tab, text="Places")
        driver_card.add(card_conditions_tab, text="Conditions")
        driver_card.add(card_units_tab, text="Vehicle Units")

        card_ident_tab.columnconfigure(0, weight=1)
        card_ident_tab.rowconfigure(1, weight=1)
        card_ident_tab.rowconfigure(3, weight=1)
        card_ident_tab.rowconfigure(5, weight=1)

        ttk.Label(card_ident_tab, text="Card application identification:").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )

        card_app_frame = ttk.Frame(card_ident_tab)
        card_app_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        card_app_frame.columnconfigure(0, weight=1)
        card_app_frame.rowconfigure(0, weight=1)

        self.card_app_tree = ttk.Treeview(
            card_app_frame, columns=("value",), show="tree headings", height=6
        )
        self.card_app_tree.heading("#0", text="Field")
        self.card_app_tree.heading("value", text="Value")
        self.card_app_tree.column("#0", width=260, anchor="w")
        self.card_app_tree.column("value", anchor="w")

        card_app_scrollbar = ttk.Scrollbar(
            card_app_frame, orient="vertical", command=self.card_app_tree.yview
        )
        self.card_app_tree.configure(yscrollcommand=card_app_scrollbar.set)

        self.card_app_tree.grid(row=0, column=0, sticky="nsew")
        card_app_scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Label(card_ident_tab, text="Driving licence information:").grid(
            row=2, column=0, sticky="w", pady=(0, 6)
        )

        card_licence_frame = ttk.Frame(card_ident_tab)
        card_licence_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
        card_licence_frame.columnconfigure(0, weight=1)
        card_licence_frame.rowconfigure(0, weight=1)

        self.card_licence_tree = ttk.Treeview(
            card_licence_frame, columns=("value",), show="tree headings", height=4
        )
        self.card_licence_tree.heading("#0", text="Field")
        self.card_licence_tree.heading("value", text="Value")
        self.card_licence_tree.column("#0", width=260, anchor="w")
        self.card_licence_tree.column("value", anchor="w")

        card_licence_scrollbar = ttk.Scrollbar(
            card_licence_frame, orient="vertical", command=self.card_licence_tree.yview
        )
        self.card_licence_tree.configure(yscrollcommand=card_licence_scrollbar.set)

        self.card_licence_tree.grid(row=0, column=0, sticky="nsew")
        card_licence_scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Label(card_ident_tab, text="Card identification:").grid(
            row=4, column=0, sticky="w", pady=(0, 6)
        )

        card_ident_frame = ttk.Frame(card_ident_tab)
        card_ident_frame.grid(row=5, column=0, sticky="nsew")
        card_ident_frame.columnconfigure(0, weight=1)
        card_ident_frame.rowconfigure(0, weight=1)

        self.card_ident_tree = ttk.Treeview(
            card_ident_frame, columns=("value",), show="tree headings", height=8
        )
        self.card_ident_tree.heading("#0", text="Field")
        self.card_ident_tree.heading("value", text="Value")
        self.card_ident_tree.column("#0", width=260, anchor="w")
        self.card_ident_tree.column("value", anchor="w")

        card_ident_scrollbar = ttk.Scrollbar(
            card_ident_frame, orient="vertical", command=self.card_ident_tree.yview
        )
        self.card_ident_tree.configure(yscrollcommand=card_ident_scrollbar.set)

        self.card_ident_tree.grid(row=0, column=0, sticky="nsew")
        card_ident_scrollbar.grid(row=0, column=1, sticky="ns")

        card_events_tab.columnconfigure(0, weight=1)
        card_events_tab.rowconfigure(1, weight=1)
        card_events_tab.rowconfigure(3, weight=1)

        ttk.Label(card_events_tab, text="Event data:").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )

        card_events_frame = ttk.Frame(card_events_tab)
        card_events_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        card_events_frame.columnconfigure(0, weight=1)
        card_events_frame.rowconfigure(0, weight=1)

        self.card_events_tree = ttk.Treeview(
            card_events_frame,
            columns=("type", "begin", "end", "nation", "registration"),
            show="headings",
            height=10,
        )
        self.card_events_tree.heading("type", text="Type")
        self.card_events_tree.heading("begin", text="Begin")
        self.card_events_tree.heading("end", text="End")
        self.card_events_tree.heading("nation", text="Registration Nation")
        self.card_events_tree.heading("registration", text="Registration Number")

        self.card_events_tree.column("type", width=240, anchor="w")
        self.card_events_tree.column("begin", width=160, anchor="w")
        self.card_events_tree.column("end", width=160, anchor="w")
        self.card_events_tree.column("nation", width=140, anchor="w")
        self.card_events_tree.column("registration", width=160, anchor="w")

        card_events_scrollbar = ttk.Scrollbar(
            card_events_frame, orient="vertical", command=self.card_events_tree.yview
        )
        self.card_events_tree.configure(yscrollcommand=card_events_scrollbar.set)

        self.card_events_tree.grid(row=0, column=0, sticky="nsew")
        card_events_scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Label(card_events_tab, text="Fault data:").grid(
            row=2, column=0, sticky="w", pady=(0, 6)
        )

        card_faults_frame = ttk.Frame(card_events_tab)
        card_faults_frame.grid(row=3, column=0, sticky="nsew")
        card_faults_frame.columnconfigure(0, weight=1)
        card_faults_frame.rowconfigure(0, weight=1)

        self.card_faults_tree = ttk.Treeview(
            card_faults_frame,
            columns=("type", "begin", "end", "nation", "registration"),
            show="headings",
            height=6,
        )
        self.card_faults_tree.heading("type", text="Type")
        self.card_faults_tree.heading("begin", text="Begin")
        self.card_faults_tree.heading("end", text="End")
        self.card_faults_tree.heading("nation", text="Registration Nation")
        self.card_faults_tree.heading("registration", text="Registration Number")

        self.card_faults_tree.column("type", width=240, anchor="w")
        self.card_faults_tree.column("begin", width=160, anchor="w")
        self.card_faults_tree.column("end", width=160, anchor="w")
        self.card_faults_tree.column("nation", width=140, anchor="w")
        self.card_faults_tree.column("registration", width=160, anchor="w")

        card_faults_scrollbar = ttk.Scrollbar(
            card_faults_frame, orient="vertical", command=self.card_faults_tree.yview
        )
        self.card_faults_tree.configure(yscrollcommand=card_faults_scrollbar.set)

        self.card_faults_tree.grid(row=0, column=0, sticky="nsew")
        card_faults_scrollbar.grid(row=0, column=1, sticky="ns")

        card_vehicles_tab.columnconfigure(0, weight=1)
        card_vehicles_tab.rowconfigure(1, weight=1)

        ttk.Label(card_vehicles_tab, text="Vehicles used:").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )

        card_vehicles_frame = ttk.Frame(card_vehicles_tab)
        card_vehicles_frame.grid(row=1, column=0, sticky="nsew")
        card_vehicles_frame.columnconfigure(0, weight=1)
        card_vehicles_frame.rowconfigure(0, weight=1)

        self.card_vehicles_tree = ttk.Treeview(
            card_vehicles_frame,
            columns=(
                "first_use",
                "last_use",
                "odo_begin",
                "odo_end",
                "nation",
                "registration",
                "vin",
            ),
            show="headings",
            height=10,
        )
        self.card_vehicles_tree.heading("first_use", text="First Use")
        self.card_vehicles_tree.heading("last_use", text="Last Use")
        self.card_vehicles_tree.heading("odo_begin", text="Odometer Begin")
        self.card_vehicles_tree.heading("odo_end", text="Odometer End")
        self.card_vehicles_tree.heading("nation", text="Registration Nation")
        self.card_vehicles_tree.heading("registration", text="Registration Number")
        self.card_vehicles_tree.heading("vin", text="VIN")

        self.card_vehicles_tree.column("first_use", width=160, anchor="w")
        self.card_vehicles_tree.column("last_use", width=160, anchor="w")
        self.card_vehicles_tree.column("odo_begin", width=120, anchor="w")
        self.card_vehicles_tree.column("odo_end", width=120, anchor="w")
        self.card_vehicles_tree.column("nation", width=140, anchor="w")
        self.card_vehicles_tree.column("registration", width=160, anchor="w")
        self.card_vehicles_tree.column("vin", width=180, anchor="w")

        card_vehicles_scrollbar = ttk.Scrollbar(
            card_vehicles_frame, orient="vertical", command=self.card_vehicles_tree.yview
        )
        self.card_vehicles_tree.configure(yscrollcommand=card_vehicles_scrollbar.set)

        self.card_vehicles_tree.grid(row=0, column=0, sticky="nsew")
        card_vehicles_scrollbar.grid(row=0, column=1, sticky="ns")

        card_places_tab.columnconfigure(0, weight=1)
        card_places_tab.rowconfigure(1, weight=1)

        ttk.Label(card_places_tab, text="Places:").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )

        card_places_frame = ttk.Frame(card_places_tab)
        card_places_frame.grid(row=1, column=0, sticky="nsew")
        card_places_frame.columnconfigure(0, weight=1)
        card_places_frame.rowconfigure(0, weight=1)

        self.card_places_tree = ttk.Treeview(
            card_places_frame,
            columns=(
                "time",
                "country",
                "region",
                "odometer",
                "entry",
                "gps_time",
                "accuracy",
                "latitude",
                "longitude",
            ),
            show="headings",
            height=10,
        )
        self.card_places_tree.heading("time", text="Time")
        self.card_places_tree.heading("country", text="Country")
        self.card_places_tree.heading("region", text="Region")
        self.card_places_tree.heading("odometer", text="Odometer")
        self.card_places_tree.heading("entry", text="Entry Type")
        self.card_places_tree.heading("gps_time", text="GPS Time")
        self.card_places_tree.heading("accuracy", text="Accuracy")
        self.card_places_tree.heading("latitude", text="Latitude")
        self.card_places_tree.heading("longitude", text="Longitude")

        self.card_places_tree.column("time", width=160, anchor="w")
        self.card_places_tree.column("country", width=100, anchor="w")
        self.card_places_tree.column("region", width=80, anchor="w")
        self.card_places_tree.column("odometer", width=120, anchor="w")
        self.card_places_tree.column("entry", width=220, anchor="w")
        self.card_places_tree.column("gps_time", width=160, anchor="w")
        self.card_places_tree.column("accuracy", width=90, anchor="w")
        self.card_places_tree.column("latitude", width=120, anchor="w")
        self.card_places_tree.column("longitude", width=120, anchor="w")

        card_places_scrollbar = ttk.Scrollbar(
            card_places_frame, orient="vertical", command=self.card_places_tree.yview
        )
        self.card_places_tree.configure(yscrollcommand=card_places_scrollbar.set)

        self.card_places_tree.grid(row=0, column=0, sticky="nsew")
        card_places_scrollbar.grid(row=0, column=1, sticky="ns")

        card_conditions_tab.columnconfigure(0, weight=1)
        card_conditions_tab.rowconfigure(1, weight=1)

        ttk.Label(card_conditions_tab, text="Specific conditions:").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )

        card_conditions_frame = ttk.Frame(card_conditions_tab)
        card_conditions_frame.grid(row=1, column=0, sticky="nsew")
        card_conditions_frame.columnconfigure(0, weight=1)
        card_conditions_frame.rowconfigure(0, weight=1)

        self.card_conditions_tree = ttk.Treeview(
            card_conditions_frame,
            columns=("time", "type"),
            show="headings",
            height=8,
        )
        self.card_conditions_tree.heading("time", text="Time")
        self.card_conditions_tree.heading("type", text="Type")
        self.card_conditions_tree.column("time", width=200, anchor="w")
        self.card_conditions_tree.column("type", width=220, anchor="w")

        card_conditions_scrollbar = ttk.Scrollbar(
            card_conditions_frame, orient="vertical", command=self.card_conditions_tree.yview
        )
        self.card_conditions_tree.configure(yscrollcommand=card_conditions_scrollbar.set)

        self.card_conditions_tree.grid(row=0, column=0, sticky="nsew")
        card_conditions_scrollbar.grid(row=0, column=1, sticky="ns")

        card_units_tab.columnconfigure(0, weight=1)
        card_units_tab.rowconfigure(1, weight=1)

        ttk.Label(card_units_tab, text="Vehicle units:").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )

        card_units_frame = ttk.Frame(card_units_tab)
        card_units_frame.grid(row=1, column=0, sticky="nsew")
        card_units_frame.columnconfigure(0, weight=1)
        card_units_frame.rowconfigure(0, weight=1)

        self.card_units_tree = ttk.Treeview(
            card_units_frame,
            columns=("time", "manufacturer", "device", "software"),
            show="headings",
            height=6,
        )
        self.card_units_tree.heading("time", text="Timestamp")
        self.card_units_tree.heading("manufacturer", text="Manufacturer Code")
        self.card_units_tree.heading("device", text="Device ID")
        self.card_units_tree.heading("software", text="Software Version")

        self.card_units_tree.column("time", width=180, anchor="w")
        self.card_units_tree.column("manufacturer", width=160, anchor="w")
        self.card_units_tree.column("device", width=120, anchor="w")
        self.card_units_tree.column("software", width=140, anchor="w")

        card_units_scrollbar = ttk.Scrollbar(
            card_units_frame, orient="vertical", command=self.card_units_tree.yview
        )
        self.card_units_tree.configure(yscrollcommand=card_units_scrollbar.set)

        self.card_units_tree.grid(row=0, column=0, sticky="nsew")
        card_units_scrollbar.grid(row=0, column=1, sticky="ns")

        activities = ttk.Frame(activities_tab, padding=12)
        activities.grid(row=0, column=0, sticky="nsew")
        activities_tab.columnconfigure(0, weight=1)
        activities_tab.rowconfigure(0, weight=1)
        activities.columnconfigure(0, weight=1)
        activities.rowconfigure(1, weight=1)
        activities.rowconfigure(3, weight=0)
        activities.rowconfigure(5, weight=1)
        activities.rowconfigure(7, weight=1)

        ttk.Label(activities, text="Activity header:").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )

        activity_header_frame = ttk.Frame(activities)
        activity_header_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        activity_header_frame.columnconfigure(0, weight=1)
        activity_header_frame.rowconfigure(0, weight=1)

        self.activity_header_tree = ttk.Treeview(
            activity_header_frame,
            columns=(
                "date",
                "slot",
                "name",
                "card_number",
                "expiry",
                "insertion",
                "withdrawal",
                "odo_in",
                "odo_out",
                "prev_vehicle",
                "prev_withdrawal",
            ),
            show="headings",
            height=6,
        )
        self.activity_header_tree.heading("date", text="Date")
        self.activity_header_tree.heading("slot", text="Slot")
        self.activity_header_tree.heading("name", text="Name")
        self.activity_header_tree.heading("card_number", text="Card Number")
        self.activity_header_tree.heading("expiry", text="Card Expiry")
        self.activity_header_tree.heading("insertion", text="Insertion Time")
        self.activity_header_tree.heading("withdrawal", text="Withdrawal Time")
        self.activity_header_tree.heading("odo_in", text="Odometer In")
        self.activity_header_tree.heading("odo_out", text="Odometer Out")
        self.activity_header_tree.heading("prev_vehicle", text="Previous Vehicle")
        self.activity_header_tree.heading("prev_withdrawal", text="Prev Withdrawal")

        self.activity_header_tree.column("date", width=140, anchor="w")
        self.activity_header_tree.column("slot", width=80, anchor="w")
        self.activity_header_tree.column("name", width=180, anchor="w")
        self.activity_header_tree.column("card_number", width=160, anchor="w")
        self.activity_header_tree.column("expiry", width=130, anchor="w")
        self.activity_header_tree.column("insertion", width=140, anchor="w")
        self.activity_header_tree.column("withdrawal", width=140, anchor="w")
        self.activity_header_tree.column("odo_in", width=100, anchor="w")
        self.activity_header_tree.column("odo_out", width=100, anchor="w")
        self.activity_header_tree.column("prev_vehicle", width=180, anchor="w")
        self.activity_header_tree.column("prev_withdrawal", width=140, anchor="w")

        activity_header_scrollbar = ttk.Scrollbar(
            activity_header_frame,
            orient="vertical",
            command=self.activity_header_tree.yview,
        )
        self.activity_header_tree.configure(
            yscrollcommand=activity_header_scrollbar.set
        )

        self.activity_header_tree.grid(row=0, column=0, sticky="nsew")
        activity_header_scrollbar.grid(row=0, column=1, sticky="ns")

        chart_header = ttk.Frame(activities)
        chart_header.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        chart_header.columnconfigure(1, weight=1)

        ttk.Label(chart_header, text="Activities (chart):").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(chart_header, text="Day:").grid(row=0, column=2, sticky="e")

        self.activity_day_combo = ttk.Combobox(
            chart_header,
            textvariable=self.activity_day_var,
            state="readonly",
            width=20,
        )
        self.activity_day_combo.grid(row=0, column=3, sticky="e", padx=(8, 0))
        self.activity_day_combo.bind("<<ComboboxSelected>>", self._on_day_selected)

        legend = ttk.Frame(activities)
        legend.grid(row=3, column=0, sticky="w", pady=(0, 6))

        self._add_legend_item(legend, "Rest", "#CFE8D5", 0)
        self._add_legend_item(legend, "Availability", "#D7E5FA", 1)
        self._add_legend_item(legend, "Work", "#F7E0A3", 2)
        self._add_legend_item(legend, "Driving", "#F2B8A2", 3)
        self._add_legend_item(legend, "Unknown", "#E0E0E0", 4)

        chart_frame = ttk.Frame(activities)
        chart_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 12))
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)

        self.activity_canvas = tk.Canvas(chart_frame, height=140, bg="white")
        self.activity_canvas.grid(row=0, column=0, sticky="nsew")
        self.activity_canvas.bind("<Configure>", self._on_canvas_resize)

        ttk.Label(activities, text="Activities (timeline):").grid(
            row=5, column=0, sticky="w", pady=(0, 6)
        )

        activities_frame = ttk.Frame(activities)
        activities_frame.grid(row=6, column=0, sticky="nsew")
        activities_frame.columnconfigure(0, weight=1)
        activities_frame.rowconfigure(0, weight=1)

        self.activities_tree = ttk.Treeview(
            activities_frame,
            columns=(
                "date",
                "slot",
                "start",
                "end",
                "activity",
                "card_status",
                "driving_status",
                "odometer",
            ),
            show="headings",
            height=10,
        )
        self.activities_tree.heading("date", text="Date")
        self.activities_tree.heading("slot", text="Slot")
        self.activities_tree.heading("start", text="Start")
        self.activities_tree.heading("end", text="End")
        self.activities_tree.heading("activity", text="Activity")
        self.activities_tree.heading("card_status", text="Card Status")
        self.activities_tree.heading("driving_status", text="Driving Status")
        self.activities_tree.heading("odometer", text="Odometer @ Midnight")

        self.activities_tree.column("date", width=140, anchor="w")
        self.activities_tree.column("slot", width=80, anchor="w")
        self.activities_tree.column("start", width=70, anchor="w")
        self.activities_tree.column("end", width=70, anchor="w")
        self.activities_tree.column("activity", width=120, anchor="w")
        self.activities_tree.column("card_status", width=120, anchor="w")
        self.activities_tree.column("driving_status", width=120, anchor="w")
        self.activities_tree.column("odometer", width=140, anchor="w")

        activities_scrollbar = ttk.Scrollbar(
            activities_frame, orient="vertical", command=self.activities_tree.yview
        )
        self.activities_tree.configure(yscrollcommand=activities_scrollbar.set)

        self.activities_tree.grid(row=0, column=0, sticky="nsew")
        activities_scrollbar.grid(row=0, column=1, sticky="ns")

    def _copy_selection(self, _event=None) -> None:
        widget = self.focus_get()
        if widget is None:
            return

        text = None
        if isinstance(widget, ttk.Treeview):
            selection = widget.selection()
            if not selection:
                return
            lines = []
            for item_id in selection:
                item = widget.item(item_id)
                values = item.get("values") or ()
                label = item.get("text") or ""
                parts = []
                if label:
                    parts.append(str(label))
                parts.extend(str(value) for value in values if value != "")
                if parts:
                    lines.append(" | ".join(parts))
            if lines:
                text = "\n".join(lines)
        elif isinstance(widget, tk.Entry):
            try:
                text = widget.selection_get()
            except tk.TclError:
                text = widget.get()
        elif isinstance(widget, tk.Text):
            try:
                text = widget.selection_get()
            except tk.TclError:
                text = widget.get("1.0", "end-1c")

        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update_idletasks()

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Open DDD file",
            filetypes=[("DDD files", "*.ddd *.DDD"), ("All files", "*.*")],
        )
        if path:
            self.file_path.set(path)
            self.status_text.set(f"Selected: {Path(path).name}")
            if not self.current_file_path:
                self._open_file()

    def _open_file(self) -> None:
        path = self.file_path.get().strip()
        if not path:
            messagebox.showwarning("No file selected", "Please choose a .ddd file first.")
            return

        try:
            summary = parse_summary(path)
        except (OSError, ValueError) as exc:
            if isinstance(exc, ValueError) and str(exc).lower().startswith("file is empty"):
                self.validity_text.set("Validity: Invalid — Header (empty)")
            else:
                self.validity_text.set(f"Validity: Invalid — File ({exc})")
            self.validity_label.configure(style="Invalid.TLabel")
            self.file_type_text.set("File type: Unknown")
            self.current_file_path = None
            self.current_summary = None
            self._clear_tree(self.header_tree)
            self._clear_tree(self.parts_tree)
            self._clear_tree(self.ident_tree)
            self._clear_tree(self.overview_tree)
            self._clear_tree(self.company_locks_tree)
            self._clear_tree(self.control_tree)
            self._clear_tree(self.faults_tree)
            self._clear_tree(self.events_tree)
            self._clear_tree(self.overspeed_tree)
            self._clear_tree(self.card_app_tree)
            self._clear_tree(self.card_licence_tree)
            self._clear_tree(self.card_ident_tree)
            self._clear_tree(self.card_events_tree)
            self._clear_tree(self.card_faults_tree)
            self._clear_tree(self.card_vehicles_tree)
            self._clear_tree(self.card_places_tree)
            self._clear_tree(self.card_conditions_tree)
            self._clear_tree(self.card_units_tree)
            self._clear_tree(self.activity_header_tree)
            self._clear_tree(self.activities_tree)
            self.activity_canvas.delete("all")
            self.activity_day_combo["values"] = ()
            self.activity_day_var.set("")
            self.overspeed_last_control_var.set("")
            self.overspeed_first_since_var.set("")
            self.overspeed_count_var.set("")
            self._set_tab_state(self.vehicle_unit_tab, "normal")
            self._set_tab_state(self.driver_card_tab, "normal")
            messagebox.showerror("Parse error", str(exc))
            return

        self._update_header_view(summary.header)
        self._update_parts_view(summary.parts)
        self._update_identification_view(summary.vu_identification)
        self._update_report_view(summary)
        self._update_events_tab(summary)
        self._update_driver_card_view(summary.driver_card)
        self._update_activities_tab(summary)
        type_label = self._type_label(summary.header.detected_type)
        self.file_type_text.set(f"File type: {type_label}")
        self.current_file_path = path
        self.current_summary = summary
        generation_label = self._generation_label(summary.header.detected_generation)
        if generation_label:
            status = f"Detected: {type_label} ({generation_label}) | {Path(path).name}"
        else:
            status = f"Detected: {type_label} | {Path(path).name}"
        self.status_text.set(status)
        validity_text, validity_style = self._format_validity(summary.header, summary.parts)
        self.validity_text.set(validity_text)
        self.validity_label.configure(style=validity_style)
        self._update_tab_visibility(summary)
        print(f"Selected file: {path}")

    def _export_html(self) -> None:
        if not self.current_summary or not self.current_file_path:
            messagebox.showwarning("No data to export", "Open a .ddd file first.")
            return

        source_path = Path(self.current_file_path)
        default_name = source_path.with_suffix(".html").name
        target = filedialog.asksaveasfilename(
            title="Export HTML",
            defaultextension=".html",
            initialdir=str(source_path.parent),
            initialfile=default_name,
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
        )
        if not target:
            return

        html_text = self._build_html(self.current_summary, source_path)
        try:
            Path(target).write_text(html_text, encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Export error", str(exc))
            return

        self.status_text.set(f"Exported HTML: {Path(target).name}")

    def _build_html(self, summary, source_path: Path) -> str:
        def esc(value) -> str:
            if value is None:
                return ""
            return html.escape(str(value))

        def table(headers, rows, row_classes=None) -> str:
            head = "".join(f"<th>{esc(h)}</th>" for h in headers)
            body_rows = []
            if row_classes is None:
                row_classes = ["" for _ in rows]
            for row, row_class in zip(rows, row_classes):
                cells = "".join(f"<td>{esc(cell)}</td>" for cell in row)
                class_attr = f' class="{row_class}"' if row_class else ""
                body_rows.append(f"<tr{class_attr}>{cells}</tr>")
            body = "".join(body_rows) if body_rows else ""
            return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

        def field_table(entries) -> str:
            rows = [(label, value) for label, value in entries]
            return table(("Field", "Value"), rows)

        header = summary.header
        type_label = self._type_label(header.detected_type)
        generation_label = self._generation_label(header.detected_generation)
        validity_text, validity_style = self._format_validity(header, summary.parts)
        validity_class = "valid" if validity_style == "Valid.TLabel" else "invalid"

        sections = []
        sections.append(
            f"""
            <section class="card">
              <h2>Summary</h2>
              <div class="meta">
                <div><strong>File</strong>: {esc(source_path.name)}</div>
                <div><strong>Type</strong>: {esc(type_label)}</div>
                <div><strong>Generation</strong>: {esc(generation_label)}</div>
                <div class="validity {validity_class}">{esc(validity_text)}</div>
              </div>
            </section>
            """
        )

        header_entries = [("Detected type", type_label)]
        if generation_label:
            header_entries.append(("Detected generation", generation_label))
        header_entries.append(("File size (bytes)", header.file_size))
        if header.service_id is not None:
            header_entries.append(("Service ID (SID)", f"0x{header.service_id:02X}"))
        if header.trep is not None:
            header_entries.append(("TREP#2", f"0x{header.trep:02X}"))
        if header.trep_generation:
            header_entries.append(("TREP generation", self._generation_label(header.trep_generation)))
        if header.trep_data_type:
            header_entries.append(("TREP data type", header.trep_data_type))
        if header.download_interface_version:
            header_entries.append(("Download interface version", header.download_interface_version))
        header_entries.extend(
            [
                ("Signature (first 6 bytes)", header.signature_hex),
                (f"First {header.header_length} bytes (hex)", header.header_hex),
            ]
        )
        sections.append(
            f"""
            <section class="card">
              <h2>Header</h2>
              {field_table(header_entries)}
            </section>
            """
        )

        part_rows = []
        part_classes = []
        for part in summary.parts:
            part_rows.append((part.name, self._status_label(part.status), part.note or ""))
            part_classes.append(part.status)
        sections.append(
            f"""
            <section class="card">
              <h2>File parts</h2>
              {table(("Part", "Status", "Note"), part_rows, part_classes)}
            </section>
            """
        )

        if header.detected_type == "vehicle_unit" or summary.overview or summary.vu_identification:
            ident = summary.vu_identification
            if ident is None:
                ident_section = field_table([("Status", "Not detected")])
            else:
                ident_entries = [
                    ("Manufacturer name", ident.manufacturer_name.text),
                    ("Manufacturer address", ident.manufacturer_address.text),
                    ("Part number", ident.part_number),
                    ("Approval number", ident.approval_number.strip()),
                    ("Serial number", ident.serial_number.serial_number),
                    ("Serial month/year", ident.serial_number.month_year_bcd),
                    ("Serial type", f"0x{ident.serial_number.equipment_type:02X}"),
                    ("Manufacturer code", ident.serial_number.manufacturer_code),
                    ("Software version", ident.software_identification.version),
                    (
                        "Software installation time",
                        format_time_real(ident.software_identification.installation_time_raw),
                    ),
                    ("Manufacturing date", format_time_real(ident.manufacturing_date_raw)),
                ]
                ident_section = field_table(ident_entries)

            overview = summary.overview
            if overview is None:
                overview_section = field_table([("Status", "Not detected")])
                locks_table = table(
                    ("Start", "End", "Company Name", "Company Address", "Card Number"),
                    [("Not detected", "", "", "", "")],
                )
                controls_table = table(
                    (
                        "Type",
                        "Time",
                        "Card Type",
                        "Card Issuing Member State",
                        "Card Number",
                        "Card Generation",
                        "Begin Period",
                        "End Period",
                    ),
                    [("Not detected", "", "", "", "", "", "", "")],
                )
            else:
                last_download = overview.last_download
                overview_entries = [
                    ("Vehicle Identification Number", overview.vin or ""),
                    (
                        "Registration",
                        overview.registration_number.registration_number
                        if overview.registration_number
                        else "",
                    ),
                    ("Current Timestamp", format_time_real(overview.current_time_raw)),
                    (
                        "Start Timestamp of stored Activities",
                        format_time_real(overview.download_period_begin_raw),
                    ),
                    (
                        "End Timestamp of stored Activities",
                        format_time_real(overview.download_period_end_raw),
                    ),
                    (
                        "Card Slot Status",
                        str(overview.card_slots_status)
                        if overview.card_slots_status is not None
                        else "",
                    ),
                    (
                        "Timestamp Previous Download",
                        format_time_real(last_download.downloading_time_raw)
                        if last_download
                        else "",
                    ),
                    (
                        "Card Type Previous Download",
                        format_card_type(last_download.card_number.card_type)
                        if last_download
                        else "",
                    ),
                    (
                        "Card Number Previous Download",
                        last_download.card_number.card_number if last_download else "",
                    ),
                    (
                        "Card Generation Previous Download",
                        str(last_download.card_number.card_generation) if last_download else "",
                    ),
                    (
                        "Company Name Previous Download",
                        last_download.company_name.text if last_download else "",
                    ),
                ]
                overview_section = field_table(overview_entries)

                lock_rows = []
                sorted_locks = self._sort_by_time_desc(
                    overview.company_locks, lambda item: item.lock_in_time_raw
                )
                for lock in sorted_locks:
                    lock_rows.append(
                        (
                            format_time_real(lock.lock_in_time_raw),
                            format_time_real(lock.lock_out_time_raw)
                            if lock.lock_out_time_raw is not None
                            else "",
                            lock.company_name.text,
                            lock.company_address.text,
                            lock.company_card_number.card_number,
                        )
                    )
                if not lock_rows:
                    lock_rows = [("Not detected", "", "", "", "")]
                locks_table = table(
                    ("Start", "End", "Company Name", "Company Address", "Card Number"),
                    lock_rows,
                )

                control_rows = []
                sorted_controls = self._sort_by_time_desc(
                    overview.control_activities, lambda item: item.control_time_raw
                )
                for control in sorted_controls:
                    card = control.control_card_number
                    control_rows.append(
                        (
                            format_control_type(control.control_type),
                            format_time_real(control.control_time_raw),
                            format_card_type(card.card_type),
                            format_nation_numeric(card.issuing_nation),
                            card.card_number,
                            str(card.card_generation),
                            format_time_real(control.download_period_begin_raw),
                            format_time_real(control.download_period_end_raw),
                        )
                    )
                if not control_rows:
                    control_rows = [("Not detected", "", "", "", "", "", "", "")]
                controls_table = table(
                    (
                        "Type",
                        "Time",
                        "Card Type",
                        "Card Issuing Member State",
                        "Card Number",
                        "Card Generation",
                        "Begin Period",
                        "End Period",
                    ),
                    control_rows,
                )

            sections.append(
                f"""
                <section class="card">
                  <h2>Vehicle Unit</h2>
                  <h3>Identification</h3>
                  {ident_section}
                  <h3>Overview</h3>
                  {overview_section}
                  <h3>Company locks</h3>
                  {locks_table}
                  <h3>Control activities</h3>
                  {controls_table}
                </section>
                """
            )

            events_rows = []
            sorted_events = self._sort_by_time_desc(
                summary.events, lambda item: item.begin_time_raw
            )
            for event in sorted_events:
                similar = "" if event.similar_events is None else str(event.similar_events)
                events_rows.append(
                    (
                        format_event_fault_type(event.event_type),
                        str(event.record_purpose),
                        format_time_real(event.begin_time_raw),
                        format_time_real(event.end_time_raw),
                        similar,
                        format_event_card_slot(event.driver_card_begin),
                        format_event_card_slot(event.driver_card_end),
                        format_event_card_slot(event.codriver_card_begin),
                        format_event_card_slot(event.codriver_card_end),
                    )
                )
            if not events_rows:
                events_rows = [("Not detected", "", "", "", "", "", "", "", "")]
            events_table = table(
                (
                    "Event Type",
                    "Purpose",
                    "Begin",
                    "End",
                    "Similar Events",
                    "Driver Card Begin",
                    "Driver Card End",
                    "Co-driver Card Begin",
                    "Co-driver Card End",
                ),
                events_rows,
            )

            faults_rows = []
            sorted_faults = self._sort_by_time_desc(
                summary.faults, lambda item: item.begin_time_raw
            )
            for fault in sorted_faults:
                faults_rows.append(
                    (
                        format_event_fault_type(fault.fault_type),
                        str(fault.record_purpose),
                        format_time_real(fault.begin_time_raw),
                        format_time_real(fault.end_time_raw),
                        format_event_card_slot(fault.driver_card_begin),
                        format_event_card_slot(fault.driver_card_end),
                        format_event_card_slot(fault.codriver_card_begin),
                        format_event_card_slot(fault.codriver_card_end),
                    )
                )
            if not faults_rows:
                faults_rows = [("Not detected", "", "", "", "", "", "", "")]
            faults_table = table(
                (
                    "Fault Type",
                    "Purpose",
                    "Begin",
                    "End",
                    "Driver Card Begin",
                    "Driver Card End",
                    "Co-driver Card Begin",
                    "Co-driver Card End",
                ),
                faults_rows,
            )

            control = summary.overspeed_control
            if control is None:
                overspeed_info = field_table([("Status", "Not detected")])
            else:
                overspeed_info = field_table(
                    [
                        (
                            "Last Overspeed Control Time",
                            format_time_real(control.last_overspeed_control_time_raw),
                        ),
                        ("First Overspeed Since", format_time_real(control.first_overspeed_since_raw)),
                        ("Number Of Overspeed Since", control.number_of_overspeed_since),
                    ]
                )
            overspeed_rows = []
            sorted_overspeed = self._sort_by_time_desc(
                summary.overspeed_events, lambda item: item.begin_time_raw
            )
            for event in sorted_overspeed:
                card = event.card_number
                if is_card_number_missing(card):
                    card_type = "Not Inserted"
                    card_number = ""
                    nation = ""
                else:
                    card_type = format_card_type(card.card_type)
                    card_number = card.card_number
                    nation = format_nation_numeric(card.issuing_nation)
                overspeed_rows.append(
                    (
                        format_overspeed_event_type(event.event_type, event.record_purpose),
                        format_time_real(event.begin_time_raw),
                        format_time_real(event.end_time_raw),
                        format_speed(event.max_speed),
                        format_speed(event.average_speed),
                        str(event.similar_events),
                        card_type,
                        card_number,
                        nation,
                    )
                )
            if not overspeed_rows:
                overspeed_rows = [("Not detected", "", "", "", "", "", "", "", "")]
            overspeed_table = table(
                (
                    "Event Type",
                    "Begin",
                    "End",
                    "Max Speed",
                    "Average Speed",
                    "Similar Events",
                    "Card Type",
                    "Card Number",
                    "Card Issuing State",
                ),
                overspeed_rows,
            )

            sections.append(
                f"""
                <section class="card">
                  <h2>VU events &amp; faults</h2>
                  <h3>Events</h3>
                  {events_table}
                  <h3>Faults</h3>
                  {faults_table}
                  <h3>Overspeed control</h3>
                  {overspeed_info}
                  <h3>Overspeed events</h3>
                  {overspeed_table}
                </section>
                """
            )

            days = summary.activity_days
            header_rows = []
            sorted_days = self._sort_by_time_desc(days, lambda item: item.date_raw)
            for day in sorted_days:
                date_label = format_time_real(day.date_raw)
                first_row = True
                for record in day.card_iw_records:
                    prev_vehicle = ""
                    if record.previous_vehicle_reg:
                        nation = format_nation_numeric(record.previous_vehicle_nation or 0)
                        reg = record.previous_vehicle_reg.registration_number
                        prev_vehicle = f"{nation} {reg}".strip()
                    header_rows.append(
                        (
                            date_label if first_row else "",
                            format_card_slot(record.slot_number),
                            format_holder_name(record.holder_surname, record.holder_first_names),
                            record.card_number.card_number,
                            format_time_real(record.card_expiry_raw),
                            format_time_real(record.card_insertion_time_raw),
                            format_time_real(record.card_withdrawal_time_raw),
                            format_odometer(record.odometer_insertion),
                            format_odometer(record.odometer_withdrawal),
                            prev_vehicle,
                            format_time_real(record.previous_withdrawal_time_raw),
                        )
                    )
                    first_row = False
            if not header_rows:
                header_rows = [("Not detected", "", "", "", "", "", "", "", "", "", "")]
            activity_header_table = table(
                (
                    "Date",
                    "Slot",
                    "Holder",
                    "Card Number",
                    "Card Expiry",
                    "Insertion",
                    "Withdrawal",
                    "Odometer In",
                    "Odometer Out",
                    "Previous Vehicle",
                    "Previous Withdrawal",
                ),
                header_rows,
            )

            activity_rows = []
            for day in sorted_days:
                date_label = format_time_real(day.date_raw)
                odometer = str(day.odometer_midnight) if day.odometer_midnight is not None else ""
                first_row = True
                for segment in day.segments:
                    activity_rows.append(
                        (
                            date_label if first_row else "",
                            format_slot(segment.slot),
                            format_minutes(segment.start_minute),
                            format_minutes(segment.end_minute),
                            format_activity(segment.activity, segment.card_status),
                            format_card_status(segment.card_status),
                            format_driving_status(segment.driving_status),
                            odometer if first_row else "",
                        )
                    )
                    first_row = False
            if not activity_rows:
                activity_rows = [("Not detected", "", "", "", "", "", "", "")]
            activities_table = table(
                (
                    "Date",
                    "Slot",
                    "Start",
                    "End",
                    "Activity",
                    "Card Status",
                    "Driving Status",
                    "Odometer",
                ),
                activity_rows,
            )

            sections.append(
                f"""
                <section class="card">
                  <h2>Activities</h2>
                  <h3>Activity header</h3>
                  {activity_header_table}
                  <h3>Activity segments</h3>
                  {activities_table}
                </section>
                """
            )

        card = summary.driver_card
        if card is not None:
            app_entries = []
            if card.application_identification is None:
                app_section = field_table([("Status", "Not detected")])
            else:
                app = card.application_identification
                app_entries = [
                    ("Card Type", format_card_type(app.card_type)),
                    ("Card Structure Version", app.card_structure_version),
                    ("Events Per Type", app.events_per_type),
                    ("Faults Per Type", app.faults_per_type),
                    ("Activity Structure Length", app.activity_structure_length),
                    ("Vehicle Records", app.vehicle_records),
                    ("Place Records", app.place_records),
                ]
                if card.card_identification is not None:
                    app_entries.append(
                        (
                            "Card Generation",
                            format_card_generation(card.card_identification.card_number.card_generation),
                        )
                    )
                app_section = field_table(app_entries)

            if card.driving_licence is None:
                licence_section = field_table([("Status", "Not detected")])
            else:
                licence = card.driving_licence
                licence_section = field_table(
                    [
                        ("Issuing Nation", format_nation_numeric(licence.issuing_nation)),
                        ("Issuing Authority", licence.issuing_authority.text),
                        ("Licence Number", licence.licence_number),
                    ]
                )

            if card.card_identification is None:
                ident_section = field_table([("Status", "Not detected")])
            else:
                ident = card.card_identification
                card_number = ident.card_number
                ident_section = field_table(
                    [
                        ("Card Number", card_number.card_number),
                        ("Card Type", format_card_type(card_number.card_type)),
                        ("Card Issuing Authority", ident.issuing_authority.text),
                        ("Issue Date", format_time_real(ident.issue_date_raw)),
                        ("Validity Begin", format_time_real(ident.validity_begin_raw)),
                        ("Expiry Date", format_time_real(ident.expiry_date_raw)),
                        ("First Name", ident.holder_first_names.text),
                        ("Last Name", ident.holder_surname.text),
                        ("Birth Date", ident.birth_date_iso or ident.birth_date_bcd),
                    ]
                )

            event_rows = []
            sorted_events = self._sort_by_time_desc(
                card.events, lambda item: item.begin_time_raw
            )
            for event in sorted_events:
                event_rows.append(
                    (
                        format_driver_event_type(event.event_type),
                        format_time_real(event.begin_time_raw),
                        format_time_real(event.end_time_raw),
                        format_nation_numeric(event.registration_nation),
                        event.registration_number.registration_number,
                    )
                )
            if not event_rows:
                event_rows = [("Not detected", "", "", "", "")]
            events_table = table(
                ("Type", "Begin", "End", "Registration Nation", "Registration"),
                event_rows,
            )

            fault_rows = []
            sorted_faults = self._sort_by_time_desc(
                card.faults, lambda item: item.begin_time_raw
            )
            for fault in sorted_faults:
                fault_rows.append(
                    (
                        format_driver_event_type(fault.event_type),
                        format_time_real(fault.begin_time_raw),
                        format_time_real(fault.end_time_raw),
                        format_nation_numeric(fault.registration_nation),
                        fault.registration_number.registration_number,
                    )
                )
            if not fault_rows:
                fault_rows = [("Not detected", "", "", "", "")]
            faults_table = table(
                ("Type", "Begin", "End", "Registration Nation", "Registration"),
                fault_rows,
            )

            vehicle_rows = []
            sorted_vehicles = self._sort_by_time_desc(
                card.vehicles_used,
                lambda item: (
                    item.last_use_raw if item.last_use_raw is not None else item.first_use_raw
                ),
            )
            for vehicle in sorted_vehicles:
                vehicle_rows.append(
                    (
                        format_time_real(vehicle.first_use_raw),
                        format_time_real(vehicle.last_use_raw),
                        format_odometer(vehicle.odometer_begin),
                        format_odometer(vehicle.odometer_end),
                        format_nation_numeric(vehicle.registration_nation),
                        vehicle.registration_number.registration_number,
                        vehicle.vin,
                    )
                )
            if not vehicle_rows:
                vehicle_rows = [("Not detected", "", "", "", "", "", "")]
            vehicles_table = table(
                (
                    "First Use",
                    "Last Use",
                    "Odometer Begin",
                    "Odometer End",
                    "Registration Nation",
                    "Registration",
                    "VIN",
                ),
                vehicle_rows,
            )

            place_rows = []
            sorted_places = self._sort_by_time_desc(
                card.places,
                lambda item: item.time_raw if item.time_raw is not None else item.gps_time_raw,
            )
            for place in sorted_places:
                place_rows.append(
                    (
                        format_time_real(place.time_raw),
                        format_nation_numeric(place.country),
                        str(place.region),
                        format_odometer(place.odometer),
                        format_place_entry_type(place.entry_type),
                        format_time_real(place.gps_time_raw),
                        format_gnss_accuracy(place.accuracy),
                        format_gnss_coordinate(place.latitude_raw),
                        format_gnss_coordinate(place.longitude_raw),
                    )
                )
            if not place_rows:
                place_rows = [("Not detected", "", "", "", "", "", "", "", "")]
            places_table = table(
                (
                    "Time",
                    "Country",
                    "Region",
                    "Odometer",
                    "Entry Type",
                    "GPS Time",
                    "Accuracy",
                    "Latitude",
                    "Longitude",
                ),
                place_rows,
            )

            condition_rows = []
            sorted_conditions = self._sort_by_time_desc(
                card.specific_conditions, lambda item: item.time_raw
            )
            for condition in sorted_conditions:
                condition_rows.append(
                    (
                        format_time_real(condition.time_raw),
                        format_specific_condition_type(condition.condition_type),
                    )
                )
            if not condition_rows:
                condition_rows = [("Not detected", "")]
            conditions_table = table(("Time", "Condition"), condition_rows)

            unit_rows = []
            sorted_units = self._sort_by_time_desc(
                card.vehicle_units, lambda item: item.timestamp_raw
            )
            for unit in sorted_units:
                unit_rows.append(
                    (
                        format_time_real(unit.timestamp_raw),
                        unit.manufacturer_code,
                        unit.device_id,
                        unit.software_version,
                    )
                )
            if not unit_rows:
                unit_rows = [("Not detected", "", "", "")]
            units_table = table(
                ("Timestamp", "Manufacturer Code", "Device ID", "Software Version"),
                unit_rows,
            )

            sections.append(
                f"""
                <section class="card">
                  <h2>Driver Card</h2>
                  <h3>Application identification</h3>
                  {app_section}
                  <h3>Driving licence</h3>
                  {licence_section}
                  <h3>Card identification</h3>
                  {ident_section}
                  <h3>Events</h3>
                  {events_table}
                  <h3>Faults</h3>
                  {faults_table}
                  <h3>Vehicles used</h3>
                  {vehicles_table}
                  <h3>Places</h3>
                  {places_table}
                  <h3>Specific conditions</h3>
                  {conditions_table}
                  <h3>Vehicle units</h3>
                  {units_table}
                </section>
                """
            )

        generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        body = "\n".join(section.strip() for section in sections)
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>dddPy export - {esc(source_path.name)}</title>
  <style>
    :root {{
      color-scheme: light;
    }}
    body {{
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      margin: 24px;
      background: #f4f6fb;
      color: #1f2937;
    }}
    h1 {{
      margin: 0 0 8px 0;
      font-size: 24px;
    }}
    h2 {{
      margin: 0 0 8px 0;
      font-size: 18px;
    }}
    h3 {{
      margin: 16px 0 8px 0;
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #374151;
    }}
    .card {{
      background: #ffffff;
      border-radius: 10px;
      padding: 16px;
      margin: 16px 0;
      box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 8px 16px;
      font-size: 14px;
    }}
    .validity {{
      font-weight: 600;
    }}
    .validity.valid {{
      color: #15803d;
    }}
    .validity.invalid {{
      color: #b91c1c;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      text-align: left;
      padding: 6px 8px;
      border-bottom: 1px solid #e5e7eb;
      vertical-align: top;
    }}
    th {{
      background: #eef2ff;
      font-weight: 600;
    }}
    tr.valid td {{
      color: #15803d;
      font-weight: 600;
    }}
    tr.invalid td {{
      color: #b91c1c;
      font-weight: 600;
    }}
    tr.missing td {{
      color: #6b7280;
    }}
    tr.not_applicable td {{
      color: #6b7280;
    }}
    footer {{
      margin-top: 24px;
      font-size: 12px;
      color: #6b7280;
    }}
  </style>
</head>
<body>
  <h1>dddPy export</h1>
  {body}
  <footer>Generated {esc(generated)}</footer>
</body>
</html>
"""

    def _update_header_view(self, header: DddHeader) -> None:
        self._clear_tree(self.header_tree)

        header_label = f"First {header.header_length} bytes (hex)"
        entries = [
            ("Detected type", self._type_label(header.detected_type)),
        ]
        generation_label = self._generation_label(header.detected_generation)
        if generation_label:
            entries.append(("Detected generation", generation_label))
        entries.append(("File size (bytes)", str(header.file_size)))
        if header.service_id is not None:
            entries.append(("Service ID (SID)", f"0x{header.service_id:02X}"))
        if header.trep is not None:
            entries.append(("TREP#2", f"0x{header.trep:02X}"))
        if header.trep_generation:
            entries.append(("TREP generation", self._generation_label(header.trep_generation)))
        if header.trep_data_type:
            entries.append(("TREP data type", header.trep_data_type))
        if header.download_interface_version:
            entries.append(
                ("Download interface version", header.download_interface_version)
            )
        entries.extend(
            [
                ("Signature (first 6 bytes)", header.signature_hex),
                (header_label, header.header_hex),
            ]
        )

        for field, value in entries:
            self.header_tree.insert("", "end", text=field, values=(value,))

    def _update_identification_view(self, identification) -> None:
        self._clear_tree(self.ident_tree)
        if identification is None:
            self.ident_tree.insert("", "end", text="Status", values=("Not detected",))
            return

        entries = [
            ("Manufacturer name", identification.manufacturer_name.text),
            ("Manufacturer address", identification.manufacturer_address.text),
            ("Part number", identification.part_number),
            ("Approval number", identification.approval_number.strip()),
            ("Serial number", str(identification.serial_number.serial_number)),
            ("Serial month/year", identification.serial_number.month_year_bcd),
            ("Serial type", f"0x{identification.serial_number.equipment_type:02X}"),
            ("Manufacturer code", str(identification.serial_number.manufacturer_code)),
            ("Software version", identification.software_identification.version),
            (
                "Software install time",
                identification.software_identification.installation_time_iso
                or str(identification.software_identification.installation_time_raw),
            ),
            (
                "Manufacturing date",
                identification.manufacturing_date_iso
                or str(identification.manufacturing_date_raw),
            ),
            (
                "Source (TREP, offset, prefix)",
                f"0x{identification.source_trep:02X}, {identification.source_offset}, {identification.prefix_bytes}",
            ),
        ]

        for field, value in entries:
            self.ident_tree.insert("", "end", text=field, values=(value,))

    def _update_report_view(self, summary) -> None:
        overview = summary.overview
        self._update_overview_view(overview)
        self._update_company_locks_view(overview.company_locks if overview else ())
        self._update_control_activities_view(overview.control_activities if overview else ())

    def _update_events_tab(self, summary) -> None:
        self._update_overspeed_control_view(summary.overspeed_control)
        self._update_faults_view(summary.faults)
        self._update_events_view(summary.events)
        self._update_overspeed_events_view(summary.overspeed_events)

    def _update_driver_card_view(self, driver_card) -> None:
        if driver_card is None:
            self._update_card_application_view(None, None)
            self._update_card_licence_view(None)
            self._update_card_ident_view(None)
            self._update_card_events_view(())
            self._update_card_faults_view(())
            self._update_card_vehicles_view(())
            self._update_card_places_view(())
            self._update_card_conditions_view(())
            self._update_card_units_view(())
            return

        self._update_card_application_view(
            driver_card.application_identification,
            driver_card.card_identification,
        )
        self._update_card_licence_view(driver_card.driving_licence)
        self._update_card_ident_view(driver_card.card_identification)
        self._update_card_events_view(driver_card.events)
        self._update_card_faults_view(driver_card.faults)
        self._update_card_vehicles_view(driver_card.vehicles_used)
        self._update_card_places_view(driver_card.places)
        self._update_card_conditions_view(driver_card.specific_conditions)
        self._update_card_units_view(driver_card.vehicle_units)

    def _update_activities_tab(self, summary) -> None:
        self._update_activity_header_view(summary.activity_days)
        self._update_activities_view(summary.activity_days)
        self._update_activity_chart(summary.activity_days)

    def _update_overview_view(self, overview) -> None:
        self._clear_tree(self.overview_tree)
        if overview is None:
            self.overview_tree.insert("", "end", text="Status", values=("Not detected",))
            return

        last_download = overview.last_download
        entries = [
            ("Vehicle Identification Number", overview.vin or ""),
            (
                "Registration",
                overview.registration_number.registration_number
                if overview.registration_number
                else "",
            ),
            ("Current Timestamp", format_time_real(overview.current_time_raw)),
            (
                "Start Timestamp of stored Activities",
                format_time_real(overview.download_period_begin_raw),
            ),
            (
                "End Timestamp of stored Activities",
                format_time_real(overview.download_period_end_raw),
            ),
            (
                "Card Slot Status",
                str(overview.card_slots_status)
                if overview.card_slots_status is not None
                else "",
            ),
            (
                "Timestamp Previous Download",
                format_time_real(last_download.downloading_time_raw)
                if last_download
                else "",
            ),
            (
                "Card Type Previous Download",
                format_card_type(last_download.card_number.card_type)
                if last_download
                else "",
            ),
            (
                "Card Number Previous Download",
                last_download.card_number.card_number if last_download else "",
            ),
            (
                "Card Generation Previous Download",
                str(last_download.card_number.card_generation) if last_download else "",
            ),
            (
                "Company Name Previous Download",
                last_download.company_name.text if last_download else "",
            ),
        ]

        for field, value in entries:
            self.overview_tree.insert("", "end", text=field, values=(value,))

    def _update_company_locks_view(self, locks) -> None:
        self._clear_tree(self.company_locks_tree)
        if not locks:
            self.company_locks_tree.insert(
                "", "end", values=("Not detected", "", "", "", "")
            )
            return

        sorted_locks = self._sort_by_time_desc(
            locks, lambda item: item.lock_in_time_raw
        )
        for lock in sorted_locks:
            self.company_locks_tree.insert(
                "",
                "end",
                values=(
                    format_time_real(lock.lock_in_time_raw),
                    format_time_real(lock.lock_out_time_raw)
                    if lock.lock_out_time_raw is not None
                    else "",
                    lock.company_name.text,
                    lock.company_address.text,
                    lock.company_card_number.card_number,
                ),
            )

    def _update_control_activities_view(self, controls) -> None:
        self._clear_tree(self.control_tree)
        if not controls:
            self.control_tree.insert(
                "",
                "end",
                values=("Not detected", "", "", "", "", "", "", ""),
            )
            return

        sorted_controls = self._sort_by_time_desc(
            controls, lambda item: item.control_time_raw
        )
        for control in sorted_controls:
            card = control.control_card_number
            self.control_tree.insert(
                "",
                "end",
                values=(
                    format_control_type(control.control_type),
                    format_time_real(control.control_time_raw),
                    format_card_type(card.card_type),
                    format_nation_numeric(card.issuing_nation),
                    card.card_number,
                    str(card.card_generation),
                    format_time_real(control.download_period_begin_raw),
                    format_time_real(control.download_period_end_raw),
                ),
            )

    def _update_card_application_view(self, app, card_ident) -> None:
        self._clear_tree(self.card_app_tree)
        if app is None:
            self.card_app_tree.insert("", "end", text="Status", values=("Not detected",))
            return
        entries = [
            ("Card Type", format_card_type(app.card_type)),
            ("Card Structure Version", str(app.card_structure_version)),
            ("Events Per Type", str(app.events_per_type)),
            ("Faults Per Type", str(app.faults_per_type)),
            ("Activity Structure Length", str(app.activity_structure_length)),
            ("Vehicle Records", str(app.vehicle_records)),
            ("Place Records", str(app.place_records)),
        ]
        if card_ident is not None:
            entries.append(
                (
                    "Card Generation",
                    format_card_generation(card_ident.card_number.card_generation),
                )
            )
        for field, value in entries:
            self.card_app_tree.insert("", "end", text=field, values=(value,))

    def _update_card_licence_view(self, licence) -> None:
        self._clear_tree(self.card_licence_tree)
        if licence is None:
            self.card_licence_tree.insert(
                "", "end", text="Status", values=("Not detected",)
            )
            return
        entries = [
            ("Issuing Nation", format_nation_numeric(licence.issuing_nation)),
            ("Issuing Authority", licence.issuing_authority.text),
            ("Licence Number", licence.licence_number),
        ]
        for field, value in entries:
            self.card_licence_tree.insert("", "end", text=field, values=(value,))

    def _update_card_ident_view(self, ident) -> None:
        self._clear_tree(self.card_ident_tree)
        if ident is None:
            self.card_ident_tree.insert(
                "", "end", text="Status", values=("Not detected",)
            )
            return
        card = ident.card_number
        entries = [
            ("Card Number", card.card_number),
            ("Card Type", format_card_type(card.card_type)),
            ("Card Issuing Authority", ident.issuing_authority.text),
            ("Issue Date", format_time_real(ident.issue_date_raw)),
            ("Validity Begin", format_time_real(ident.validity_begin_raw)),
            ("Expiry Date", format_time_real(ident.expiry_date_raw)),
            ("First Name", ident.holder_first_names.text),
            ("Last Name", ident.holder_surname.text),
            ("Birth Date", ident.birth_date_iso or ident.birth_date_bcd),
        ]
        for field, value in entries:
            self.card_ident_tree.insert("", "end", text=field, values=(value,))

    def _update_card_events_view(self, events) -> None:
        self._clear_tree(self.card_events_tree)
        if not events:
            self.card_events_tree.insert(
                "", "end", values=("Not detected", "", "", "", "")
            )
            return
        sorted_events = self._sort_by_time_desc(
            events, lambda item: item.begin_time_raw
        )
        for event in sorted_events:
            self.card_events_tree.insert(
                "",
                "end",
                values=(
                    format_driver_event_type(event.event_type),
                    format_time_real(event.begin_time_raw),
                    format_time_real(event.end_time_raw),
                    format_nation_numeric(event.registration_nation),
                    event.registration_number.registration_number,
                ),
            )

    def _update_card_faults_view(self, faults) -> None:
        self._clear_tree(self.card_faults_tree)
        if not faults:
            self.card_faults_tree.insert(
                "", "end", values=("Not detected", "", "", "", "")
            )
            return
        sorted_faults = self._sort_by_time_desc(
            faults, lambda item: item.begin_time_raw
        )
        for fault in sorted_faults:
            self.card_faults_tree.insert(
                "",
                "end",
                values=(
                    format_driver_event_type(fault.event_type),
                    format_time_real(fault.begin_time_raw),
                    format_time_real(fault.end_time_raw),
                    format_nation_numeric(fault.registration_nation),
                    fault.registration_number.registration_number,
                ),
            )

    def _update_card_vehicles_view(self, vehicles) -> None:
        self._clear_tree(self.card_vehicles_tree)
        if not vehicles:
            self.card_vehicles_tree.insert(
                "", "end", values=("Not detected", "", "", "", "", "", "")
            )
            return
        sorted_vehicles = self._sort_by_time_desc(
            vehicles,
            lambda item: (
                item.last_use_raw if item.last_use_raw is not None else item.first_use_raw
            ),
        )
        for vehicle in sorted_vehicles:
            self.card_vehicles_tree.insert(
                "",
                "end",
                values=(
                    format_time_real(vehicle.first_use_raw),
                    format_time_real(vehicle.last_use_raw),
                    format_odometer(vehicle.odometer_begin),
                    format_odometer(vehicle.odometer_end),
                    format_nation_numeric(vehicle.registration_nation),
                    vehicle.registration_number.registration_number,
                    vehicle.vin,
                ),
            )

    def _update_card_places_view(self, places) -> None:
        self._clear_tree(self.card_places_tree)
        if not places:
            self.card_places_tree.insert(
                "", "end", values=("Not detected", "", "", "", "", "", "", "", "")
            )
            return
        sorted_places = self._sort_by_time_desc(
            places,
            lambda item: item.time_raw if item.time_raw is not None else item.gps_time_raw,
        )
        for place in sorted_places:
            self.card_places_tree.insert(
                "",
                "end",
                values=(
                    format_time_real(place.time_raw),
                    format_nation_numeric(place.country),
                    str(place.region),
                    format_odometer(place.odometer),
                    format_place_entry_type(place.entry_type),
                    format_time_real(place.gps_time_raw),
                    format_gnss_accuracy(place.accuracy),
                    format_gnss_coordinate(place.latitude_raw),
                    format_gnss_coordinate(place.longitude_raw),
                ),
            )

    def _update_card_conditions_view(self, conditions) -> None:
        self._clear_tree(self.card_conditions_tree)
        if not conditions:
            self.card_conditions_tree.insert(
                "", "end", values=("Not detected", "")
            )
            return
        sorted_conditions = self._sort_by_time_desc(
            conditions, lambda item: item.time_raw
        )
        for condition in sorted_conditions:
            self.card_conditions_tree.insert(
                "",
                "end",
                values=(
                    format_time_real(condition.time_raw),
                    format_specific_condition_type(condition.condition_type),
                ),
            )

    def _update_card_units_view(self, units) -> None:
        self._clear_tree(self.card_units_tree)
        if not units:
            self.card_units_tree.insert(
                "", "end", values=("Not detected", "", "", "")
            )
            return
        sorted_units = self._sort_by_time_desc(
            units, lambda item: item.timestamp_raw
        )
        for unit in sorted_units:
            self.card_units_tree.insert(
                "",
                "end",
                values=(
                    format_time_real(unit.timestamp_raw),
                    str(unit.manufacturer_code),
                    str(unit.device_id),
                    unit.software_version,
                ),
            )

    def _update_overspeed_control_view(self, control) -> None:
        if control is None:
            self.overspeed_last_control_var.set("Not detected")
            self.overspeed_first_since_var.set("")
            self.overspeed_count_var.set("")
            return
        self.overspeed_last_control_var.set(
            format_time_real(control.last_overspeed_control_time_raw)
        )
        self.overspeed_first_since_var.set(
            format_time_real(control.first_overspeed_since_raw)
        )
        self.overspeed_count_var.set(str(control.number_of_overspeed_since))

    def _update_faults_view(self, faults) -> None:
        self._clear_tree(self.faults_tree)
        if not faults:
            self.faults_tree.insert(
                "",
                "end",
                values=("Not detected", "", "", "", "", "", "", ""),
            )
            return
        sorted_faults = self._sort_by_time_desc(
            faults, lambda item: item.begin_time_raw
        )
        for fault in sorted_faults:
            self.faults_tree.insert(
                "",
                "end",
                values=(
                    format_event_fault_type(fault.fault_type),
                    str(fault.record_purpose),
                    format_time_real(fault.begin_time_raw),
                    format_time_real(fault.end_time_raw),
                    format_event_card_slot(fault.driver_card_begin),
                    format_event_card_slot(fault.driver_card_end),
                    format_event_card_slot(fault.codriver_card_begin),
                    format_event_card_slot(fault.codriver_card_end),
                ),
            )

    def _update_events_view(self, events) -> None:
        self._clear_tree(self.events_tree)
        if not events:
            self.events_tree.insert(
                "",
                "end",
                values=("Not detected", "", "", "", "", "", "", "", ""),
            )
            return
        sorted_events = self._sort_by_time_desc(
            events, lambda item: item.begin_time_raw
        )
        for event in sorted_events:
            similar = "" if event.similar_events is None else str(event.similar_events)
            self.events_tree.insert(
                "",
                "end",
                values=(
                    format_event_fault_type(event.event_type),
                    str(event.record_purpose),
                    format_time_real(event.begin_time_raw),
                    format_time_real(event.end_time_raw),
                    similar,
                    format_event_card_slot(event.driver_card_begin),
                    format_event_card_slot(event.driver_card_end),
                    format_event_card_slot(event.codriver_card_begin),
                    format_event_card_slot(event.codriver_card_end),
                ),
            )

    def _update_overspeed_events_view(self, events) -> None:
        self._clear_tree(self.overspeed_tree)
        if not events:
            self.overspeed_tree.insert(
                "",
                "end",
                values=("Not detected", "", "", "", "", "", "", "", ""),
            )
            return
        sorted_events = self._sort_by_time_desc(
            events, lambda item: item.begin_time_raw
        )
        for event in sorted_events:
            card = event.card_number
            if is_card_number_missing(card):
                card_type = "Not Inserted"
                card_number = ""
                nation = ""
            else:
                card_type = format_card_type(card.card_type)
                card_number = card.card_number
                nation = format_nation_numeric(card.issuing_nation)

            self.overspeed_tree.insert(
                "",
                "end",
                values=(
                    format_overspeed_event_type(event.event_type, event.record_purpose),
                    format_time_real(event.begin_time_raw),
                    format_time_real(event.end_time_raw),
                    format_speed(event.max_speed),
                    format_speed(event.average_speed),
                    str(event.similar_events),
                    card_type,
                    card_number,
                    nation,
                ),
            )

    def _update_activity_header_view(self, days) -> None:
        self._clear_tree(self.activity_header_tree)
        if not days:
            self.activity_header_tree.insert(
                "",
                "end",
                values=("Not detected", "", "", "", "", "", "", "", "", "", ""),
            )
            return
        sorted_days = self._sort_by_time_desc(days, lambda item: item.date_raw)
        for day in sorted_days:
            date_label = format_time_real(day.date_raw)
            first_row = True
            for record in day.card_iw_records:
                prev_vehicle = ""
                if record.previous_vehicle_reg:
                    nation = format_nation_numeric(record.previous_vehicle_nation or 0)
                    reg = record.previous_vehicle_reg.registration_number
                    prev_vehicle = f"{nation} {reg}".strip()

                self.activity_header_tree.insert(
                    "",
                    "end",
                    values=(
                        date_label if first_row else "",
                        format_card_slot(record.slot_number),
                        format_holder_name(
                            record.holder_surname, record.holder_first_names
                        ),
                        record.card_number.card_number,
                        format_time_real(record.card_expiry_raw),
                        format_time_real(record.card_insertion_time_raw),
                        format_time_real(record.card_withdrawal_time_raw),
                        format_odometer(record.odometer_insertion),
                        format_odometer(record.odometer_withdrawal),
                        prev_vehicle,
                        format_time_real(record.previous_withdrawal_time_raw),
                    ),
                )
                first_row = False

    def _update_activities_view(self, days) -> None:
        self._clear_tree(self.activities_tree)
        if not days:
            self.activities_tree.insert(
                "",
                "end",
                values=("Not detected", "", "", "", "", "", "", ""),
            )
            return
        sorted_days = self._sort_by_time_desc(days, lambda item: item.date_raw)
        for day in sorted_days:
            date_label = format_time_real(day.date_raw)
            odometer = str(day.odometer_midnight) if day.odometer_midnight is not None else ""
            first_row = True
            for segment in day.segments:
                self.activities_tree.insert(
                    "",
                    "end",
                    values=(
                        date_label if first_row else "",
                        format_slot(segment.slot),
                        format_minutes(segment.start_minute),
                        format_minutes(segment.end_minute),
                        format_activity(segment.activity, segment.card_status),
                        format_card_status(segment.card_status),
                        format_driving_status(segment.driving_status),
                        odometer if first_row else "",
                    ),
                )
                first_row = False

    def _update_activity_chart(self, days) -> None:
        if not days:
            self._activity_day_map = {}
            self.activity_day_combo["values"] = ()
            self.activity_day_var.set("")
            self.activity_canvas.delete("all")
            self._current_activity_day = None
            return

        sorted_days = self._sort_by_time_desc(days, lambda item: item.date_raw)
        labels = []
        self._activity_day_map = {}
        for day in sorted_days:
            label = self._day_label(day.date_raw)
            labels.append(label)
            self._activity_day_map[label] = day

        self.activity_day_combo["values"] = tuple(labels)
        latest_label = labels[0]
        self.activity_day_var.set(latest_label)
        self._current_activity_day = self._activity_day_map[latest_label]
        self._draw_activity_chart(self._current_activity_day)

    def _on_day_selected(self, _event) -> None:
        label = self.activity_day_var.get()
        day = self._activity_day_map.get(label)
        if day is None:
            return
        self._current_activity_day = day
        self._draw_activity_chart(day)

    def _on_canvas_resize(self, _event) -> None:
        if self._current_activity_day is not None:
            self._draw_activity_chart(self._current_activity_day)

    def _draw_activity_chart(self, day) -> None:
        canvas = self.activity_canvas
        canvas.delete("all")

        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 50 or height < 50:
            return

        margin_left = 70
        margin_right = 20
        timeline_top = 30
        row_height = 18
        row_gap = 22

        usable_width = max(1, width - margin_left - margin_right)
        scale = usable_width / 1440.0

        axis_y = timeline_top - 12
        for hour in range(0, 25, 2):
            x = margin_left + hour * 60 * scale
            canvas.create_line(x, axis_y, x, axis_y + 6, fill="#666666")
            canvas.create_text(
                x,
                axis_y - 2,
                text=str(hour),
                fill="#444444",
                anchor="s",
                font=("TkDefaultFont", 8),
            )

        row_positions = {
            0: timeline_top,
            1: timeline_top + row_height + row_gap,
        }

        canvas.create_text(
            8,
            row_positions[0] + row_height / 2,
            text="Driver",
            anchor="w",
            fill="#222222",
        )
        canvas.create_text(
            8,
            row_positions[1] + row_height / 2,
            text="Codriver",
            anchor="w",
            fill="#222222",
        )

        for segment in day.segments:
            row_y = row_positions.get(segment.slot)
            if row_y is None:
                continue
            x1 = margin_left + segment.start_minute * scale
            x2 = margin_left + segment.end_minute * scale
            if x2 <= x1:
                continue
            color = self._activity_color(segment.activity, segment.card_status)
            canvas.create_rectangle(
                x1,
                row_y,
                x2,
                row_y + row_height,
                fill=color,
                outline="",
            )

        canvas.create_text(
            margin_left,
            timeline_top + row_height + row_gap + row_height + 10,
            text=self._day_label(day.date_raw),
            anchor="w",
            fill="#333333",
        )

    def _activity_color(self, activity: int, card_status: int) -> str:
        if card_status == 1:
            return "#E0E0E0"
        if activity == 0:
            return "#CFE8D5"
        if activity == 1:
            return "#D7E5FA"
        if activity == 2:
            return "#F7E0A3"
        if activity == 3:
            return "#F2B8A2"
        return "#E0E0E0"

    def _day_label(self, timestamp: int) -> str:
        date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return f"{date.year}. {date.month:02d}. {date.day:02d}"

    def _update_parts_view(self, parts) -> None:
        self._clear_tree(self.parts_tree)
        for part in parts:
            self.parts_tree.insert(
                "",
                "end",
                values=(part.name, self._status_label(part.status), part.note or ""),
                tags=(part.status,),
            )

    def _add_legend_item(self, parent, label: str, color: str, column: int) -> None:
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=column, padx=(0, 12))

        box = tk.Canvas(frame, width=12, height=12, highlightthickness=1)
        box.create_rectangle(0, 0, 12, 12, fill=color, outline="")
        box.grid(row=0, column=0, padx=(0, 4))

        ttk.Label(frame, text=label).grid(row=0, column=1, sticky="w")

    def _sort_by_time_desc(self, items, key):
        return sorted(
            items,
            key=lambda item: (
                key(item) is None,
                -(key(item) or 0),
            ),
        )

    def _enable_tree_multiselect(self) -> None:
        def walk(widget) -> None:
            for child in widget.winfo_children():
                if isinstance(child, ttk.Treeview):
                    child.configure(selectmode="extended")
                walk(child)

        walk(self)

    def _clear_tree(self, tree: ttk.Treeview) -> None:
        for item in tree.get_children():
            tree.delete(item)

    def _set_tab_state(self, tab: ttk.Frame, state: str) -> None:
        try:
            self.main_notebook.tab(tab, state=state)
        except tk.TclError:
            pass

    def _update_tab_visibility(self, summary) -> None:
        has_driver = summary.driver_card is not None
        has_vu = any(
            (
                summary.vu_identification is not None,
                summary.overview is not None,
                bool(summary.activity_days),
                bool(summary.events),
                bool(summary.faults),
                bool(summary.overspeed_control),
                bool(summary.overspeed_events),
            )
        )
        self._set_tab_state(self.vehicle_unit_tab, "normal" if has_vu else "hidden")
        self._set_tab_state(self.driver_card_tab, "normal" if has_driver else "hidden")

    def _type_label(self, detected_type: str) -> str:
        if detected_type == "vehicle_unit":
            return "VU (vehicle unit)"
        if detected_type == "driver_card":
            return "Driver card"
        return "Unknown"

    def _status_label(self, status: str) -> str:
        if status == "valid":
            return "Valid"
        if status == "invalid":
            return "Invalid"
        if status == "missing":
            return "Missing"
        if status == "not_applicable":
            return "N/A"
        return status.capitalize()

    def _format_validity(self, header: DddHeader, parts) -> tuple[str, str]:
        if not header.is_valid:
            reason = header.invalid_reason or "Unknown issue"
            return f"Validity: Invalid — {reason}", "Invalid.TLabel"
        invalid_parts = [part.name for part in parts if part.status == "invalid"]
        if invalid_parts:
            names = ", ".join(invalid_parts)
            return f"Validity: Invalid — {names}", "Invalid.TLabel"
        return "Validity: Valid", "Valid.TLabel"

    def _generation_label(self, generation: str) -> str:
        if generation == "gen1":
            return "Generation 1"
        if generation == "gen2_v1":
            return "Smart tachograph Gen2 v1"
        if generation == "gen2_v2":
            return "Smart tachograph Gen2 v2"
        if generation == "gen2_v1_or_v2":
            return "Smart tachograph Gen2 (v1 or v2)"
        return ""


def main() -> None:
    app = DddReaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
