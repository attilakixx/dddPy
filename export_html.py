from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ddd_structs import (
    format_activity,
    format_card_slot,
    format_card_status,
    format_card_type,
    format_driving_status,
    format_driver_event_type,
    format_event_card_slot,
    format_event_fault_type,
    format_gnss_accuracy,
    format_gnss_coordinate,
    format_holder_name,
    format_minutes,
    format_nation_numeric,
    format_odometer,
    format_overspeed_event_type,
    format_place_entry_type,
    format_speed,
    format_specific_condition_type,
    format_slot,
    format_time_real,
    format_card_generation,
    is_card_number_missing,
)


def build_html(
    summary,
    source_path: Path,
    type_label: Callable[[str], str],
    generation_label: Callable[[str], str],
    format_validity: Callable[[object, object], tuple[str, str]],
    status_label: Callable[[str], str],
    sort_by_time_desc: Callable[[list, Callable[[object], int | None]], list],
) -> str:
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
    type_label_text = type_label(header.detected_type)
    generation_label_text = generation_label(header.detected_generation)
    validity_text, validity_style = format_validity(header, summary.parts)
    validity_class = "valid" if validity_style == "Valid.TLabel" else "invalid"

    sections = []
    sections.append(
        f"""
        <section class="card">
          <h2>Summary</h2>
          <div class="meta">
            <div><strong>File</strong>: {esc(source_path.name)}</div>
            <div><strong>Type</strong>: {esc(type_label_text)}</div>
            <div><strong>Generation</strong>: {esc(generation_label_text)}</div>
            <div class="validity {validity_class}">{esc(validity_text)}</div>
          </div>
        </section>
        """
    )

    header_entries = [("Detected type", type_label_text)]
    if generation_label_text:
        header_entries.append(("Detected generation", generation_label_text))
    header_entries.append(("File size (bytes)", header.file_size))
    if header.service_id is not None:
        header_entries.append(("Service ID (SID)", f"0x{header.service_id:02X}"))
    if header.trep is not None:
        header_entries.append(("TREP#2", f"0x{header.trep:02X}"))
    if header.trep_generation:
        header_entries.append(("TREP generation", generation_label(header.trep_generation)))
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
        part_rows.append((part.name, status_label(part.status), part.note or ""))
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
            sorted_locks = sort_by_time_desc(
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
            sorted_controls = sort_by_time_desc(
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
        sorted_events = sort_by_time_desc(summary.events, lambda item: item.begin_time_raw)
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
        sorted_faults = sort_by_time_desc(summary.faults, lambda item: item.begin_time_raw)
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
        sorted_overspeed = sort_by_time_desc(
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
        sorted_days = sort_by_time_desc(days, lambda item: item.date_raw)
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
        sorted_events = sort_by_time_desc(card.events, lambda item: item.begin_time_raw)
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
        sorted_faults = sort_by_time_desc(card.faults, lambda item: item.begin_time_raw)
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
        sorted_vehicles = sort_by_time_desc(
            card.vehicles_used,
            lambda item: item.last_use_raw if item.last_use_raw is not None else item.first_use_raw,
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
        sorted_places = sort_by_time_desc(
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
        sorted_conditions = sort_by_time_desc(
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
        sorted_units = sort_by_time_desc(card.vehicle_units, lambda item: item.timestamp_raw)
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
