import tkinter as tk
from tkinter import filedialog, messagebox, ttk
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
    format_slot,
    format_time_real,
    is_card_number_missing,
)


class DddReaderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("dddPy - DDD File Reader")
        self.minsize(720, 640)

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

        self._build_ui()
        self.bind_all("<Control-c>", self._copy_selection)
        self.bind_all("<Control-C>", self._copy_selection)

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        summary_tab = ttk.Frame(notebook)
        vehicle_unit_tab = ttk.Frame(notebook)
        driver_card_tab = ttk.Frame(notebook)
        notebook.add(summary_tab, text="Summary")
        notebook.add(vehicle_unit_tab, text="Vehicle Unit")
        notebook.add(driver_card_tab, text="Driver Card")

        vu_notebook = ttk.Notebook(vehicle_unit_tab)
        vu_notebook.grid(row=0, column=0, sticky="nsew")
        vehicle_unit_tab.columnconfigure(0, weight=1)
        vehicle_unit_tab.rowconfigure(0, weight=1)

        ident_tab = ttk.Frame(vu_notebook)
        report_tab = ttk.Frame(vu_notebook)
        events_tab = ttk.Frame(vu_notebook)
        activities_tab = ttk.Frame(vu_notebook)
        vu_notebook.add(ident_tab, text="Identification")
        vu_notebook.add(report_tab, text="Report")
        vu_notebook.add(events_tab, text="Events/Faults")
        vu_notebook.add(activities_tab, text="Activities")

        summary = ttk.Frame(summary_tab, padding=12)
        summary.grid(row=0, column=0, sticky="nsew")
        summary_tab.columnconfigure(0, weight=1)
        summary_tab.rowconfigure(0, weight=1)
        summary.columnconfigure(0, weight=1)
        summary.rowconfigure(6, weight=1)
        summary.rowconfigure(8, weight=1)

        header_frame = ttk.Frame(summary)
        header_frame.grid(row=0, column=0, columnspan=3, sticky="ew")
        header_frame.columnconfigure(0, weight=1)

        self.validity_label = ttk.Label(header_frame, textvariable=self.validity_text)
        self.validity_label.grid(row=0, column=0, sticky="w")

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
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

        path_entry = ttk.Entry(summary, textvariable=self.file_path, state="readonly")
        path_entry.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(8, 0))

        ttk.Button(summary, text="Browse...", command=self._browse).grid(
            row=2, column=1, sticky="ew", pady=(8, 0)
        )
        ttk.Button(summary, text="Open", command=self._open_file).grid(
            row=2, column=2, sticky="ew", pady=(8, 0)
        )

        ttk.Label(summary, textvariable=self.status_text, foreground="gray").grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )

        ttk.Label(summary, textvariable=self.file_type_text).grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(6, 0)
        )

        ttk.Label(summary, text="Parsed header fields:").grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(12, 0)
        )

        details_frame = ttk.Frame(summary)
        details_frame.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=(6, 0))
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

        ttk.Label(summary, text="File parts:").grid(
            row=7, column=0, columnspan=3, sticky="w", pady=(12, 0)
        )

        parts_frame = ttk.Frame(summary)
        parts_frame.grid(row=8, column=0, columnspan=3, sticky="nsew", pady=(6, 0))
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

        driver_card = ttk.Notebook(driver_card_tab)
        driver_card.grid(row=0, column=0, sticky="nsew")
        driver_card_tab.columnconfigure(0, weight=1)
        driver_card_tab.rowconfigure(0, weight=1)

        card_ident_tab = ttk.Frame(driver_card)
        card_events_tab = ttk.Frame(driver_card)
        card_vehicles_tab = ttk.Frame(driver_card)
        card_conditions_tab = ttk.Frame(driver_card)
        card_units_tab = ttk.Frame(driver_card)
        driver_card.add(card_ident_tab, text="Identification")
        driver_card.add(card_events_tab, text="Events")
        driver_card.add(card_vehicles_tab, text="Vehicles")
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
        generation_label = self._generation_label(summary.header.detected_generation)
        if generation_label:
            status = f"Detected: {type_label} ({generation_label}) | {Path(path).name}"
        else:
            status = f"Detected: {type_label} | {Path(path).name}"
        self.status_text.set(status)
        validity_text, validity_style = self._format_validity(summary.header, summary.parts)
        self.validity_text.set(validity_text)
        self.validity_label.configure(style=validity_style)
        print(f"Selected file: {path}")

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

        for lock in locks:
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

        for control in controls:
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
        for event in events:
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
        for fault in faults:
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
        for vehicle in vehicles:
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

    def _update_card_conditions_view(self, conditions) -> None:
        self._clear_tree(self.card_conditions_tree)
        if not conditions:
            self.card_conditions_tree.insert(
                "", "end", values=("Not detected", "")
            )
            return
        for condition in conditions:
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
        for unit in units:
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

        for fault in faults:
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

        for event in events:
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

        for event in events:
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

        for day in days:
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

        for day in days:
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

        sorted_days = sorted(days, key=lambda item: item.date_raw)
        labels = []
        self._activity_day_map = {}
        for day in sorted_days:
            label = self._day_label(day.date_raw)
            labels.append(label)
            self._activity_day_map[label] = day

        self.activity_day_combo["values"] = tuple(labels)
        latest_label = labels[-1]
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

    def _clear_tree(self, tree: ttk.Treeview) -> None:
        for item in tree.get_children():
            tree.delete(item)

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
