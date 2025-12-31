from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk


def build_summary_tab(app, parent: ttk.Frame) -> None:
    summary = ttk.Frame(parent, padding=16)
    summary.grid(row=0, column=0, sticky="nsew")
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(0, weight=1)
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
    app.validity_label = ttk.Label(
        header_left, textvariable=app.validity_text, style="Neutral.TLabel"
    )
    app.validity_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
    ttk.Label(header_left, textvariable=app.file_type_text, style="Subtle.TLabel").grid(
        row=2, column=0, sticky="w", pady=(2, 0)
    )

    app.logo_image = None
    logo_path = Path(__file__).with_name("logo.png")
    if logo_path.exists():
        try:
            logo_image = tk.PhotoImage(file=str(logo_path))
            scale = max(1, logo_image.width() // 260, logo_image.height() // 90)
            if scale > 1:
                logo_image = logo_image.subsample(scale, scale)
            app.logo_image = logo_image
            ttk.Label(header_frame, image=app.logo_image).grid(
                row=0, column=1, sticky="e"
            )
        except tk.TclError:
            app.logo_image = None

    ttk.Label(
        summary,
        text="Select a tachograph .ddd file to open:",
        style="Section.TLabel",
    ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(10, 0))

    path_entry = ttk.Entry(summary, textvariable=app.file_path, state="readonly")
    path_entry.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(8, 0))

    ttk.Button(summary, text="Browse...", command=app._browse).grid(
        row=2, column=1, sticky="ew", pady=(8, 0)
    )
    ttk.Button(summary, text="Open", style="Accent.TButton", command=app._open_file).grid(
        row=2, column=2, sticky="ew", pady=(8, 0)
    )
    ttk.Button(summary, text="Export HTML", command=app._export_html).grid(
        row=2, column=3, sticky="ew", pady=(8, 0)
    )

    ttk.Label(summary, textvariable=app.status_text, style="Subtle.TLabel").grid(
        row=3, column=0, columnspan=4, sticky="w", pady=(8, 0)
    )

    ttk.Label(summary, text="Parsed header fields:", style="Section.TLabel").grid(
        row=4, column=0, columnspan=4, sticky="w", pady=(12, 0)
    )

    details_frame = ttk.Frame(summary)
    details_frame.grid(row=5, column=0, columnspan=4, sticky="nsew", pady=(6, 0))
    details_frame.columnconfigure(0, weight=1)
    details_frame.rowconfigure(0, weight=1)

    app.header_tree = ttk.Treeview(
        details_frame, columns=("value",), show="tree headings", height=7
    )
    app.header_tree.heading("#0", text="Field")
    app.header_tree.heading("value", text="Value")
    app.header_tree.column("#0", width=200, anchor="w")
    app.header_tree.column("value", anchor="w")

    scrollbar = ttk.Scrollbar(
        details_frame, orient="vertical", command=app.header_tree.yview
    )
    app.header_tree.configure(yscrollcommand=scrollbar.set)

    app.header_tree.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    ttk.Label(summary, text="File parts:", style="Section.TLabel").grid(
        row=6, column=0, columnspan=4, sticky="w", pady=(12, 0)
    )

    parts_frame = ttk.Frame(summary)
    parts_frame.grid(row=7, column=0, columnspan=4, sticky="nsew", pady=(6, 0))
    parts_frame.columnconfigure(0, weight=1)
    parts_frame.rowconfigure(0, weight=1)

    app.parts_tree = ttk.Treeview(
        parts_frame, columns=("part", "status", "note"), show="headings", height=6
    )
    app.parts_tree.heading("part", text="Part")
    app.parts_tree.heading("status", text="Status")
    app.parts_tree.heading("note", text="Note")
    app.parts_tree.column("part", width=200, anchor="w")
    app.parts_tree.column("status", width=120, anchor="w")
    app.parts_tree.column("note", anchor="w")

    parts_scrollbar = ttk.Scrollbar(
        parts_frame, orient="vertical", command=app.parts_tree.yview
    )
    app.parts_tree.configure(yscrollcommand=parts_scrollbar.set)

    app.parts_tree.grid(row=0, column=0, sticky="nsew")
    parts_scrollbar.grid(row=0, column=1, sticky="ns")

    style = ttk.Style()
    style.configure("Valid.TLabel", foreground="#1B5E20")
    style.configure("Invalid.TLabel", foreground="#B71C1C")
    style.configure("Neutral.TLabel", foreground="#333333")
    app.parts_tree.tag_configure("valid", foreground="#1B5E20")
    app.parts_tree.tag_configure("invalid", foreground="#B71C1C")
    app.parts_tree.tag_configure("missing", foreground="#6B6B6B")
    app.parts_tree.tag_configure("not_applicable", foreground="#6B6B6B")


def build_vehicle_unit_tab(app, parent: ttk.Frame) -> None:
    vu_notebook = ttk.Notebook(parent)
    vu_notebook.grid(row=0, column=0, sticky="nsew")
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(0, weight=1)

    ident_tab = ttk.Frame(vu_notebook)
    report_tab = ttk.Frame(vu_notebook)
    events_tab = ttk.Frame(vu_notebook)
    activities_tab = ttk.Frame(vu_notebook)
    vu_notebook.add(ident_tab, text="Identification")
    vu_notebook.add(report_tab, text="Report")
    vu_notebook.add(events_tab, text="Events/Faults")
    vu_notebook.add(activities_tab, text="Activities")

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

    app.ident_tree = ttk.Treeview(
        ident_frame, columns=("value",), show="tree headings", height=7
    )
    app.ident_tree.heading("#0", text="Field")
    app.ident_tree.heading("value", text="Value")
    app.ident_tree.column("#0", width=220, anchor="w")
    app.ident_tree.column("value", anchor="w")

    ident_scrollbar = ttk.Scrollbar(
        ident_frame, orient="vertical", command=app.ident_tree.yview
    )
    app.ident_tree.configure(yscrollcommand=ident_scrollbar.set)

    app.ident_tree.grid(row=0, column=0, sticky="nsew")
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

    app.overview_tree = ttk.Treeview(
        overview_frame, columns=("value",), show="tree headings", height=10
    )
    app.overview_tree.heading("#0", text="Field")
    app.overview_tree.heading("value", text="Value")
    app.overview_tree.column("#0", width=260, anchor="w")
    app.overview_tree.column("value", anchor="w")

    overview_scrollbar = ttk.Scrollbar(
        overview_frame, orient="vertical", command=app.overview_tree.yview
    )
    app.overview_tree.configure(yscrollcommand=overview_scrollbar.set)

    app.overview_tree.grid(row=0, column=0, sticky="nsew")
    overview_scrollbar.grid(row=0, column=1, sticky="ns")

    ttk.Label(report, text="Company locks:").grid(
        row=2, column=0, sticky="w", pady=(0, 6)
    )

    locks_frame = ttk.Frame(report)
    locks_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
    locks_frame.columnconfigure(0, weight=1)
    locks_frame.rowconfigure(0, weight=1)

    app.company_locks_tree = ttk.Treeview(
        locks_frame,
        columns=("start", "end", "name", "address", "card"),
        show="headings",
        height=6,
    )
    app.company_locks_tree.heading("start", text="Start")
    app.company_locks_tree.heading("end", text="End")
    app.company_locks_tree.heading("name", text="Company Name")
    app.company_locks_tree.heading("address", text="Company Address")
    app.company_locks_tree.heading("card", text="Card Number")
    app.company_locks_tree.column("start", width=160, anchor="w")
    app.company_locks_tree.column("end", width=160, anchor="w")
    app.company_locks_tree.column("name", width=180, anchor="w")
    app.company_locks_tree.column("address", width=220, anchor="w")
    app.company_locks_tree.column("card", width=160, anchor="w")

    locks_scrollbar = ttk.Scrollbar(
        locks_frame, orient="vertical", command=app.company_locks_tree.yview
    )
    app.company_locks_tree.configure(yscrollcommand=locks_scrollbar.set)

    app.company_locks_tree.grid(row=0, column=0, sticky="nsew")
    locks_scrollbar.grid(row=0, column=1, sticky="ns")

    ttk.Label(report, text="Control activities:").grid(
        row=4, column=0, sticky="w", pady=(0, 6)
    )

    controls_frame = ttk.Frame(report)
    controls_frame.grid(row=5, column=0, sticky="nsew")
    controls_frame.columnconfigure(0, weight=1)
    controls_frame.rowconfigure(0, weight=1)

    app.control_tree = ttk.Treeview(
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
    app.control_tree.heading("type", text="Type")
    app.control_tree.heading("time", text="Time")
    app.control_tree.heading("card_type", text="Card Type")
    app.control_tree.heading("nation", text="Card Issuing Member State")
    app.control_tree.heading("card_number", text="Card Number")
    app.control_tree.heading("generation", text="Card Generation")
    app.control_tree.heading("begin", text="Begin Period")
    app.control_tree.heading("end", text="End Period")

    app.control_tree.column("type", width=200, anchor="w")
    app.control_tree.column("time", width=160, anchor="w")
    app.control_tree.column("card_type", width=140, anchor="w")
    app.control_tree.column("nation", width=120, anchor="w")
    app.control_tree.column("card_number", width=160, anchor="w")
    app.control_tree.column("generation", width=110, anchor="w")
    app.control_tree.column("begin", width=160, anchor="w")
    app.control_tree.column("end", width=160, anchor="w")

    controls_scrollbar = ttk.Scrollbar(
        controls_frame, orient="vertical", command=app.control_tree.yview
    )
    app.control_tree.configure(yscrollcommand=controls_scrollbar.set)

    app.control_tree.grid(row=0, column=0, sticky="nsew")
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
    ttk.Label(overspeed_info, textvariable=app.overspeed_last_control_var).grid(
        row=0, column=1, sticky="w"
    )
    ttk.Label(overspeed_info, text="First Overspeed Since:").grid(
        row=1, column=0, sticky="w", padx=(0, 8)
    )
    ttk.Label(overspeed_info, textvariable=app.overspeed_first_since_var).grid(
        row=1, column=1, sticky="w"
    )
    ttk.Label(overspeed_info, text="Number Of Overspeed Since:").grid(
        row=2, column=0, sticky="w", padx=(0, 8)
    )
    ttk.Label(overspeed_info, textvariable=app.overspeed_count_var).grid(
        row=2, column=1, sticky="w"
    )

    ttk.Label(events, text="Fault data:").grid(
        row=2, column=0, sticky="w", pady=(0, 6)
    )

    faults_frame = ttk.Frame(events)
    faults_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
    faults_frame.columnconfigure(0, weight=1)
    faults_frame.rowconfigure(0, weight=1)

    app.faults_tree = ttk.Treeview(
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
    app.faults_tree.heading("type", text="Fault Type")
    app.faults_tree.heading("purpose", text="Purpose")
    app.faults_tree.heading("begin", text="Begin")
    app.faults_tree.heading("end", text="End")
    app.faults_tree.heading("driver_begin", text="Driver Slot Begin")
    app.faults_tree.heading("driver_end", text="Driver Slot End")
    app.faults_tree.heading("codriver_begin", text="Codriver Slot Begin")
    app.faults_tree.heading("codriver_end", text="Codriver Slot End")

    app.faults_tree.column("type", width=220, anchor="w")
    app.faults_tree.column("purpose", width=80, anchor="w")
    app.faults_tree.column("begin", width=160, anchor="w")
    app.faults_tree.column("end", width=160, anchor="w")
    app.faults_tree.column("driver_begin", width=220, anchor="w")
    app.faults_tree.column("driver_end", width=220, anchor="w")
    app.faults_tree.column("codriver_begin", width=220, anchor="w")
    app.faults_tree.column("codriver_end", width=220, anchor="w")

    faults_scrollbar = ttk.Scrollbar(
        faults_frame, orient="vertical", command=app.faults_tree.yview
    )
    app.faults_tree.configure(yscrollcommand=faults_scrollbar.set)

    app.faults_tree.grid(row=0, column=0, sticky="nsew")
    faults_scrollbar.grid(row=0, column=1, sticky="ns")

    ttk.Label(events, text="Event data:").grid(
        row=4, column=0, sticky="w", pady=(0, 6)
    )

    events_frame = ttk.Frame(events)
    events_frame.grid(row=5, column=0, sticky="nsew", pady=(0, 12))
    events_frame.columnconfigure(0, weight=1)
    events_frame.rowconfigure(0, weight=1)

    app.events_tree = ttk.Treeview(
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
    app.events_tree.heading("type", text="Event Type")
    app.events_tree.heading("purpose", text="Purpose")
    app.events_tree.heading("begin", text="Begin")
    app.events_tree.heading("end", text="End")
    app.events_tree.heading("similar", text="Similar Events")
    app.events_tree.heading("driver_begin", text="Driver Slot Begin")
    app.events_tree.heading("driver_end", text="Driver Slot End")
    app.events_tree.heading("codriver_begin", text="Codriver Slot Begin")
    app.events_tree.heading("codriver_end", text="Codriver Slot End")

    app.events_tree.column("type", width=220, anchor="w")
    app.events_tree.column("purpose", width=80, anchor="w")
    app.events_tree.column("begin", width=160, anchor="w")
    app.events_tree.column("end", width=160, anchor="w")
    app.events_tree.column("similar", width=120, anchor="w")
    app.events_tree.column("driver_begin", width=220, anchor="w")
    app.events_tree.column("driver_end", width=220, anchor="w")
    app.events_tree.column("codriver_begin", width=220, anchor="w")
    app.events_tree.column("codriver_end", width=220, anchor="w")

    events_scrollbar = ttk.Scrollbar(
        events_frame, orient="vertical", command=app.events_tree.yview
    )
    app.events_tree.configure(yscrollcommand=events_scrollbar.set)

    app.events_tree.grid(row=0, column=0, sticky="nsew")
    events_scrollbar.grid(row=0, column=1, sticky="ns")

    ttk.Label(events, text="Overspeeding event data:").grid(
        row=6, column=0, sticky="w", pady=(0, 6)
    )

    overspeed_frame = ttk.Frame(events)
    overspeed_frame.grid(row=7, column=0, sticky="nsew")
    overspeed_frame.columnconfigure(0, weight=1)
    overspeed_frame.rowconfigure(0, weight=1)

    app.overspeed_tree = ttk.Treeview(
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
    app.overspeed_tree.heading("type", text="Event Type")
    app.overspeed_tree.heading("begin", text="Begin")
    app.overspeed_tree.heading("end", text="End")
    app.overspeed_tree.heading("max_speed", text="Max Speed")
    app.overspeed_tree.heading("avg_speed", text="Avg Speed")
    app.overspeed_tree.heading("similar", text="Similar Events")
    app.overspeed_tree.heading("card_type", text="Card Type")
    app.overspeed_tree.heading("card_number", text="Card Number")
    app.overspeed_tree.heading("nation", text="Card Issuing State")

    app.overspeed_tree.column("type", width=160, anchor="w")
    app.overspeed_tree.column("begin", width=160, anchor="w")
    app.overspeed_tree.column("end", width=160, anchor="w")
    app.overspeed_tree.column("max_speed", width=90, anchor="w")
    app.overspeed_tree.column("avg_speed", width=90, anchor="w")
    app.overspeed_tree.column("similar", width=120, anchor="w")
    app.overspeed_tree.column("card_type", width=140, anchor="w")
    app.overspeed_tree.column("card_number", width=160, anchor="w")
    app.overspeed_tree.column("nation", width=140, anchor="w")

    overspeed_scrollbar = ttk.Scrollbar(
        overspeed_frame, orient="vertical", command=app.overspeed_tree.yview
    )
    app.overspeed_tree.configure(yscrollcommand=overspeed_scrollbar.set)

    app.overspeed_tree.grid(row=0, column=0, sticky="nsew")
    overspeed_scrollbar.grid(row=0, column=1, sticky="ns")

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

    app.activity_header_tree = ttk.Treeview(
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
    app.activity_header_tree.heading("date", text="Date")
    app.activity_header_tree.heading("slot", text="Slot")
    app.activity_header_tree.heading("name", text="Name")
    app.activity_header_tree.heading("card_number", text="Card Number")
    app.activity_header_tree.heading("expiry", text="Card Expiry")
    app.activity_header_tree.heading("insertion", text="Insertion Time")
    app.activity_header_tree.heading("withdrawal", text="Withdrawal Time")
    app.activity_header_tree.heading("odo_in", text="Odometer In")
    app.activity_header_tree.heading("odo_out", text="Odometer Out")
    app.activity_header_tree.heading("prev_vehicle", text="Previous Vehicle")
    app.activity_header_tree.heading("prev_withdrawal", text="Prev Withdrawal")

    app.activity_header_tree.column("date", width=140, anchor="w")
    app.activity_header_tree.column("slot", width=80, anchor="w")
    app.activity_header_tree.column("name", width=180, anchor="w")
    app.activity_header_tree.column("card_number", width=160, anchor="w")
    app.activity_header_tree.column("expiry", width=130, anchor="w")
    app.activity_header_tree.column("insertion", width=140, anchor="w")
    app.activity_header_tree.column("withdrawal", width=140, anchor="w")
    app.activity_header_tree.column("odo_in", width=100, anchor="w")
    app.activity_header_tree.column("odo_out", width=100, anchor="w")
    app.activity_header_tree.column("prev_vehicle", width=180, anchor="w")
    app.activity_header_tree.column("prev_withdrawal", width=140, anchor="w")

    activity_header_scrollbar = ttk.Scrollbar(
        activity_header_frame,
        orient="vertical",
        command=app.activity_header_tree.yview,
    )
    app.activity_header_tree.configure(
        yscrollcommand=activity_header_scrollbar.set
    )

    app.activity_header_tree.grid(row=0, column=0, sticky="nsew")
    activity_header_scrollbar.grid(row=0, column=1, sticky="ns")

    chart_header = ttk.Frame(activities)
    chart_header.grid(row=2, column=0, sticky="ew", pady=(0, 6))
    chart_header.columnconfigure(1, weight=1)

    ttk.Label(chart_header, text="Activities (chart):").grid(
        row=0, column=0, sticky="w"
    )
    ttk.Label(chart_header, text="Day:").grid(row=0, column=2, sticky="e")

    app.activity_day_combo = ttk.Combobox(
        chart_header,
        textvariable=app.activity_day_var,
        state="readonly",
        width=20,
    )
    app.activity_day_combo.grid(row=0, column=3, sticky="e", padx=(8, 0))
    app.activity_day_combo.bind("<<ComboboxSelected>>", app._on_day_selected)

    legend = ttk.Frame(activities)
    legend.grid(row=3, column=0, sticky="w", pady=(0, 6))

    app._add_legend_item(legend, "Rest", "#CFE8D5", 0)
    app._add_legend_item(legend, "Availability", "#D7E5FA", 1)
    app._add_legend_item(legend, "Work", "#F7E0A3", 2)
    app._add_legend_item(legend, "Driving", "#F2B8A2", 3)
    app._add_legend_item(legend, "Unknown", "#E0E0E0", 4)

    chart_frame = ttk.Frame(activities)
    chart_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 12))
    chart_frame.columnconfigure(0, weight=1)
    chart_frame.rowconfigure(0, weight=1)

    app.activity_canvas = tk.Canvas(chart_frame, height=140, bg="white")
    app.activity_canvas.grid(row=0, column=0, sticky="nsew")
    app.activity_canvas.bind("<Configure>", app._on_canvas_resize)

    ttk.Label(activities, text="Activities (timeline):").grid(
        row=5, column=0, sticky="w", pady=(0, 6)
    )

    activities_frame = ttk.Frame(activities)
    activities_frame.grid(row=6, column=0, sticky="nsew")
    activities_frame.columnconfigure(0, weight=1)
    activities_frame.rowconfigure(0, weight=1)

    app.activities_tree = ttk.Treeview(
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
    app.activities_tree.heading("date", text="Date")
    app.activities_tree.heading("slot", text="Slot")
    app.activities_tree.heading("start", text="Start")
    app.activities_tree.heading("end", text="End")
    app.activities_tree.heading("activity", text="Activity")
    app.activities_tree.heading("card_status", text="Card Status")
    app.activities_tree.heading("driving_status", text="Driving Status")
    app.activities_tree.heading("odometer", text="Odometer @ Midnight")

    app.activities_tree.column("date", width=140, anchor="w")
    app.activities_tree.column("slot", width=80, anchor="w")
    app.activities_tree.column("start", width=70, anchor="w")
    app.activities_tree.column("end", width=70, anchor="w")
    app.activities_tree.column("activity", width=120, anchor="w")
    app.activities_tree.column("card_status", width=120, anchor="w")
    app.activities_tree.column("driving_status", width=120, anchor="w")
    app.activities_tree.column("odometer", width=140, anchor="w")

    activities_scrollbar = ttk.Scrollbar(
        activities_frame, orient="vertical", command=app.activities_tree.yview
    )
    app.activities_tree.configure(yscrollcommand=activities_scrollbar.set)

    app.activities_tree.grid(row=0, column=0, sticky="nsew")
    activities_scrollbar.grid(row=0, column=1, sticky="ns")


def build_driver_card_tab(app, parent: ttk.Frame) -> None:
    driver_card = ttk.Notebook(parent)
    driver_card.grid(row=0, column=0, sticky="nsew")
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(0, weight=1)

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

    app.card_app_tree = ttk.Treeview(
        card_app_frame, columns=("value",), show="tree headings", height=6
    )
    app.card_app_tree.heading("#0", text="Field")
    app.card_app_tree.heading("value", text="Value")
    app.card_app_tree.column("#0", width=260, anchor="w")
    app.card_app_tree.column("value", anchor="w")

    card_app_scrollbar = ttk.Scrollbar(
        card_app_frame, orient="vertical", command=app.card_app_tree.yview
    )
    app.card_app_tree.configure(yscrollcommand=card_app_scrollbar.set)

    app.card_app_tree.grid(row=0, column=0, sticky="nsew")
    card_app_scrollbar.grid(row=0, column=1, sticky="ns")

    ttk.Label(card_ident_tab, text="Driving licence information:").grid(
        row=2, column=0, sticky="w", pady=(0, 6)
    )

    card_licence_frame = ttk.Frame(card_ident_tab)
    card_licence_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
    card_licence_frame.columnconfigure(0, weight=1)
    card_licence_frame.rowconfigure(0, weight=1)

    app.card_licence_tree = ttk.Treeview(
        card_licence_frame, columns=("value",), show="tree headings", height=4
    )
    app.card_licence_tree.heading("#0", text="Field")
    app.card_licence_tree.heading("value", text="Value")
    app.card_licence_tree.column("#0", width=260, anchor="w")
    app.card_licence_tree.column("value", anchor="w")

    card_licence_scrollbar = ttk.Scrollbar(
        card_licence_frame, orient="vertical", command=app.card_licence_tree.yview
    )
    app.card_licence_tree.configure(yscrollcommand=card_licence_scrollbar.set)

    app.card_licence_tree.grid(row=0, column=0, sticky="nsew")
    card_licence_scrollbar.grid(row=0, column=1, sticky="ns")

    ttk.Label(card_ident_tab, text="Card identification:").grid(
        row=4, column=0, sticky="w", pady=(0, 6)
    )

    card_ident_frame = ttk.Frame(card_ident_tab)
    card_ident_frame.grid(row=5, column=0, sticky="nsew")
    card_ident_frame.columnconfigure(0, weight=1)
    card_ident_frame.rowconfigure(0, weight=1)

    app.card_ident_tree = ttk.Treeview(
        card_ident_frame, columns=("value",), show="tree headings", height=8
    )
    app.card_ident_tree.heading("#0", text="Field")
    app.card_ident_tree.heading("value", text="Value")
    app.card_ident_tree.column("#0", width=260, anchor="w")
    app.card_ident_tree.column("value", anchor="w")

    card_ident_scrollbar = ttk.Scrollbar(
        card_ident_frame, orient="vertical", command=app.card_ident_tree.yview
    )
    app.card_ident_tree.configure(yscrollcommand=card_ident_scrollbar.set)

    app.card_ident_tree.grid(row=0, column=0, sticky="nsew")
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

    app.card_events_tree = ttk.Treeview(
        card_events_frame,
        columns=("type", "begin", "end", "nation", "registration"),
        show="headings",
        height=10,
    )
    app.card_events_tree.heading("type", text="Type")
    app.card_events_tree.heading("begin", text="Begin")
    app.card_events_tree.heading("end", text="End")
    app.card_events_tree.heading("nation", text="Registration Nation")
    app.card_events_tree.heading("registration", text="Registration Number")

    app.card_events_tree.column("type", width=240, anchor="w")
    app.card_events_tree.column("begin", width=160, anchor="w")
    app.card_events_tree.column("end", width=160, anchor="w")
    app.card_events_tree.column("nation", width=140, anchor="w")
    app.card_events_tree.column("registration", width=160, anchor="w")

    card_events_scrollbar = ttk.Scrollbar(
        card_events_frame, orient="vertical", command=app.card_events_tree.yview
    )
    app.card_events_tree.configure(yscrollcommand=card_events_scrollbar.set)

    app.card_events_tree.grid(row=0, column=0, sticky="nsew")
    card_events_scrollbar.grid(row=0, column=1, sticky="ns")

    ttk.Label(card_events_tab, text="Fault data:").grid(
        row=2, column=0, sticky="w", pady=(0, 6)
    )

    card_faults_frame = ttk.Frame(card_events_tab)
    card_faults_frame.grid(row=3, column=0, sticky="nsew")
    card_faults_frame.columnconfigure(0, weight=1)
    card_faults_frame.rowconfigure(0, weight=1)

    app.card_faults_tree = ttk.Treeview(
        card_faults_frame,
        columns=("type", "begin", "end", "nation", "registration"),
        show="headings",
        height=6,
    )
    app.card_faults_tree.heading("type", text="Type")
    app.card_faults_tree.heading("begin", text="Begin")
    app.card_faults_tree.heading("end", text="End")
    app.card_faults_tree.heading("nation", text="Registration Nation")
    app.card_faults_tree.heading("registration", text="Registration Number")

    app.card_faults_tree.column("type", width=240, anchor="w")
    app.card_faults_tree.column("begin", width=160, anchor="w")
    app.card_faults_tree.column("end", width=160, anchor="w")
    app.card_faults_tree.column("nation", width=140, anchor="w")
    app.card_faults_tree.column("registration", width=160, anchor="w")

    card_faults_scrollbar = ttk.Scrollbar(
        card_faults_frame, orient="vertical", command=app.card_faults_tree.yview
    )
    app.card_faults_tree.configure(yscrollcommand=card_faults_scrollbar.set)

    app.card_faults_tree.grid(row=0, column=0, sticky="nsew")
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

    app.card_vehicles_tree = ttk.Treeview(
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
    app.card_vehicles_tree.heading("first_use", text="First Use")
    app.card_vehicles_tree.heading("last_use", text="Last Use")
    app.card_vehicles_tree.heading("odo_begin", text="Odometer Begin")
    app.card_vehicles_tree.heading("odo_end", text="Odometer End")
    app.card_vehicles_tree.heading("nation", text="Registration Nation")
    app.card_vehicles_tree.heading("registration", text="Registration Number")
    app.card_vehicles_tree.heading("vin", text="VIN")

    app.card_vehicles_tree.column("first_use", width=160, anchor="w")
    app.card_vehicles_tree.column("last_use", width=160, anchor="w")
    app.card_vehicles_tree.column("odo_begin", width=120, anchor="w")
    app.card_vehicles_tree.column("odo_end", width=120, anchor="w")
    app.card_vehicles_tree.column("nation", width=140, anchor="w")
    app.card_vehicles_tree.column("registration", width=160, anchor="w")
    app.card_vehicles_tree.column("vin", width=180, anchor="w")

    card_vehicles_scrollbar = ttk.Scrollbar(
        card_vehicles_frame, orient="vertical", command=app.card_vehicles_tree.yview
    )
    app.card_vehicles_tree.configure(yscrollcommand=card_vehicles_scrollbar.set)

    app.card_vehicles_tree.grid(row=0, column=0, sticky="nsew")
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

    app.card_places_tree = ttk.Treeview(
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
    app.card_places_tree.heading("time", text="Time")
    app.card_places_tree.heading("country", text="Country")
    app.card_places_tree.heading("region", text="Region")
    app.card_places_tree.heading("odometer", text="Odometer")
    app.card_places_tree.heading("entry", text="Entry Type")
    app.card_places_tree.heading("gps_time", text="GPS Time")
    app.card_places_tree.heading("accuracy", text="Accuracy")
    app.card_places_tree.heading("latitude", text="Latitude")
    app.card_places_tree.heading("longitude", text="Longitude")

    app.card_places_tree.column("time", width=160, anchor="w")
    app.card_places_tree.column("country", width=100, anchor="w")
    app.card_places_tree.column("region", width=80, anchor="w")
    app.card_places_tree.column("odometer", width=120, anchor="w")
    app.card_places_tree.column("entry", width=220, anchor="w")
    app.card_places_tree.column("gps_time", width=160, anchor="w")
    app.card_places_tree.column("accuracy", width=90, anchor="w")
    app.card_places_tree.column("latitude", width=120, anchor="w")
    app.card_places_tree.column("longitude", width=120, anchor="w")

    card_places_scrollbar = ttk.Scrollbar(
        card_places_frame, orient="vertical", command=app.card_places_tree.yview
    )
    app.card_places_tree.configure(yscrollcommand=card_places_scrollbar.set)

    app.card_places_tree.grid(row=0, column=0, sticky="nsew")
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

    app.card_conditions_tree = ttk.Treeview(
        card_conditions_frame,
        columns=("time", "type"),
        show="headings",
        height=8,
    )
    app.card_conditions_tree.heading("time", text="Time")
    app.card_conditions_tree.heading("type", text="Type")
    app.card_conditions_tree.column("time", width=200, anchor="w")
    app.card_conditions_tree.column("type", width=220, anchor="w")

    card_conditions_scrollbar = ttk.Scrollbar(
        card_conditions_frame, orient="vertical", command=app.card_conditions_tree.yview
    )
    app.card_conditions_tree.configure(yscrollcommand=card_conditions_scrollbar.set)

    app.card_conditions_tree.grid(row=0, column=0, sticky="nsew")
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

    app.card_units_tree = ttk.Treeview(
        card_units_frame,
        columns=("time", "manufacturer", "device", "software"),
        show="headings",
        height=6,
    )
    app.card_units_tree.heading("time", text="Timestamp")
    app.card_units_tree.heading("manufacturer", text="Manufacturer Code")
    app.card_units_tree.heading("device", text="Device ID")
    app.card_units_tree.heading("software", text="Software Version")

    app.card_units_tree.column("time", width=180, anchor="w")
    app.card_units_tree.column("manufacturer", width=160, anchor="w")
    app.card_units_tree.column("device", width=120, anchor="w")
    app.card_units_tree.column("software", width=140, anchor="w")

    card_units_scrollbar = ttk.Scrollbar(
        card_units_frame, orient="vertical", command=app.card_units_tree.yview
    )
    app.card_units_tree.configure(yscrollcommand=card_units_scrollbar.set)

    app.card_units_tree.grid(row=0, column=0, sticky="nsew")
    card_units_scrollbar.grid(row=0, column=1, sticky="ns")
