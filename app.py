import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.font as tkfont
from pathlib import Path
from datetime import datetime, timezone

from ddd_parser import DddHeader, parse_summary
from export_html import build_html
from ui_tabs import build_driver_card_tab, build_summary_tab, build_vehicle_unit_tab
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

        build_summary_tab(self, self.summary_tab)
        build_vehicle_unit_tab(self, self.vehicle_unit_tab)
        build_driver_card_tab(self, self.driver_card_tab)

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

        html_text = build_html(
            self.current_summary,
            source_path,
            self._type_label,
            self._generation_label,
            self._format_validity,
            self._status_label,
            self._sort_by_time_desc,
        )
        try:
            Path(target).write_text(html_text, encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Export error", str(exc))
            return

        self.status_text.set(f"Exported HTML: {Path(target).name}")

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
