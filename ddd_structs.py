from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from ddd_binary import ByteReader


@dataclass(frozen=True)
class NameValue:
    code_page: int
    text: str


@dataclass(frozen=True)
class AddressValue:
    code_page: int
    text: str


@dataclass(frozen=True)
class ExtendedSerialNumber:
    serial_number: int
    month_year_bcd: str
    equipment_type: int
    manufacturer_code: int


@dataclass(frozen=True)
class VuSoftwareIdentification:
    version: str
    installation_time_raw: int
    installation_time_iso: str | None


@dataclass(frozen=True)
class VuIdentification:
    manufacturer_name: NameValue
    manufacturer_address: AddressValue
    part_number: str
    serial_number: ExtendedSerialNumber
    software_identification: VuSoftwareIdentification
    manufacturing_date_raw: int
    manufacturing_date_iso: str | None
    approval_number: str
    source_trep: int
    source_offset: int
    prefix_bytes: int
    heuristic: bool = True


@dataclass(frozen=True)
class VehicleRegistrationNumber:
    code_page: int
    registration_number: str


@dataclass(frozen=True)
class FullCardNumber:
    card_type: int
    issuing_nation: int
    card_number: str
    card_generation: int


@dataclass(frozen=True)
class VuDownloadActivityData:
    downloading_time_raw: int
    downloading_time_iso: str | None
    card_number: FullCardNumber
    company_name: NameValue


@dataclass(frozen=True)
class VuCompanyLock:
    lock_in_time_raw: int
    lock_in_time_iso: str | None
    lock_out_time_raw: int | None
    lock_out_time_iso: str | None
    company_name: NameValue
    company_address: AddressValue
    company_card_number: FullCardNumber


@dataclass(frozen=True)
class VuControlActivity:
    control_type: int
    control_time_raw: int
    control_time_iso: str | None
    control_card_number: FullCardNumber
    download_period_begin_raw: int
    download_period_begin_iso: str | None
    download_period_end_raw: int
    download_period_end_iso: str | None


@dataclass(frozen=True)
class VuOverview:
    vin: str | None
    registration_number: VehicleRegistrationNumber | None
    current_time_raw: int | None
    current_time_iso: str | None
    download_period_begin_raw: int | None
    download_period_begin_iso: str | None
    download_period_end_raw: int | None
    download_period_end_iso: str | None
    card_slots_status: int | None
    last_download: VuDownloadActivityData | None
    company_locks: tuple[VuCompanyLock, ...]
    control_activities: tuple[VuControlActivity, ...]


@dataclass(frozen=True)
class CardApplicationIdentification:
    card_type: int
    card_structure_version: int
    events_per_type: int
    faults_per_type: int
    activity_structure_length: int
    vehicle_records: int
    place_records: int
    card_generation: int | None


@dataclass(frozen=True)
class DrivingLicenceInformation:
    issuing_nation: int
    issuing_authority: NameValue
    licence_number: str


@dataclass(frozen=True)
class CardIdentification:
    card_number: FullCardNumber
    issuing_authority: NameValue
    issue_date_raw: int
    issue_date_iso: str | None
    validity_begin_raw: int
    validity_begin_iso: str | None
    expiry_date_raw: int
    expiry_date_iso: str | None
    holder_surname: NameValue
    holder_first_names: NameValue
    birth_date_bcd: str
    birth_date_iso: str | None


@dataclass(frozen=True)
class CardEventRecord:
    event_type: int
    begin_time_raw: int | None
    begin_time_iso: str | None
    end_time_raw: int | None
    end_time_iso: str | None
    registration_nation: int
    registration_number: VehicleRegistrationNumber


@dataclass(frozen=True)
class CardSpecificCondition:
    time_raw: int | None
    time_iso: str | None
    condition_type: int


@dataclass(frozen=True)
class CardVehicleRecord:
    first_use_raw: int | None
    first_use_iso: str | None
    last_use_raw: int | None
    last_use_iso: str | None
    odometer_begin: int | None
    odometer_end: int | None
    registration_nation: int
    registration_number: VehicleRegistrationNumber
    vin: str


@dataclass(frozen=True)
class CardVehicleUnitRecord:
    timestamp_raw: int | None
    timestamp_iso: str | None
    manufacturer_code: int
    device_id: int
    software_version: str


@dataclass(frozen=True)
class DriverCardSummary:
    application_identification: CardApplicationIdentification | None
    driving_licence: DrivingLicenceInformation | None
    card_identification: CardIdentification | None
    events: tuple[CardEventRecord, ...]
    faults: tuple[CardEventRecord, ...]
    vehicles_used: tuple[CardVehicleRecord, ...]
    specific_conditions: tuple[CardSpecificCondition, ...]
    vehicle_units: tuple[CardVehicleUnitRecord, ...]


@dataclass(frozen=True)
class EventRecord:
    event_type: int
    record_purpose: int
    begin_time_raw: int | None
    begin_time_iso: str | None
    end_time_raw: int | None
    end_time_iso: str | None
    driver_card_begin: FullCardNumber
    driver_card_end: FullCardNumber
    codriver_card_begin: FullCardNumber
    codriver_card_end: FullCardNumber
    similar_events: int | None


@dataclass(frozen=True)
class FaultRecord:
    fault_type: int
    record_purpose: int
    begin_time_raw: int | None
    begin_time_iso: str | None
    end_time_raw: int | None
    end_time_iso: str | None
    driver_card_begin: FullCardNumber
    driver_card_end: FullCardNumber
    codriver_card_begin: FullCardNumber
    codriver_card_end: FullCardNumber


@dataclass(frozen=True)
class VuOverSpeedingControlData:
    last_overspeed_control_time_raw: int | None
    last_overspeed_control_time_iso: str | None
    first_overspeed_since_raw: int | None
    first_overspeed_since_iso: str | None
    number_of_overspeed_since: int


@dataclass(frozen=True)
class OverspeedingEventRecord:
    event_type: int
    record_purpose: int
    begin_time_raw: int | None
    begin_time_iso: str | None
    end_time_raw: int | None
    end_time_iso: str | None
    max_speed: int
    average_speed: int
    card_number: FullCardNumber
    similar_events: int


@dataclass(frozen=True)
class ActivityChangeInfo:
    slot: int
    driving_status: int
    card_status: int
    activity: int
    minutes: int


@dataclass(frozen=True)
class ActivitySegment:
    date_raw: int
    date_iso: str | None
    slot: int
    start_minute: int
    end_minute: int
    activity: int
    card_status: int
    driving_status: int


@dataclass(frozen=True)
class ActivityDay:
    date_raw: int
    date_iso: str | None
    odometer_midnight: int | None
    changes: tuple[ActivityChangeInfo, ...]
    segments: tuple[ActivitySegment, ...]
    card_iw_records: tuple[VuCardIWRecord, ...]


@dataclass(frozen=True)
class VuCardIWRecord:
    holder_surname: NameValue
    holder_first_names: NameValue
    card_number: FullCardNumber
    card_expiry_raw: int
    card_expiry_iso: str | None
    card_insertion_time_raw: int
    card_insertion_time_iso: str | None
    card_withdrawal_time_raw: int | None
    card_withdrawal_time_iso: str | None
    slot_number: int
    odometer_insertion: int | None
    odometer_withdrawal: int | None
    previous_vehicle_nation: int | None
    previous_vehicle_reg: VehicleRegistrationNumber | None
    previous_withdrawal_time_raw: int | None
    previous_withdrawal_time_iso: str | None


def parse_name(reader: ByteReader) -> NameValue:
    code_page = reader.read_u8()
    text = reader.read_fixed_str(35)
    return NameValue(code_page=code_page, text=text)


def parse_address(reader: ByteReader) -> AddressValue:
    code_page = reader.read_u8()
    text = reader.read_fixed_str(35)
    return AddressValue(code_page=code_page, text=text)


def parse_extended_serial_number(reader: ByteReader) -> ExtendedSerialNumber:
    serial_number = reader.read_u32_be()
    month_year_bcd = reader.read_bcd(2)
    equipment_type = reader.read_u8()
    manufacturer_code = reader.read_u8()
    return ExtendedSerialNumber(
        serial_number=serial_number,
        month_year_bcd=month_year_bcd,
        equipment_type=equipment_type,
        manufacturer_code=manufacturer_code,
    )


def parse_vu_software_identification(reader: ByteReader) -> VuSoftwareIdentification:
    version = reader.read_fixed_str(4)
    installation_time_raw = reader.read_time_real_raw()
    return VuSoftwareIdentification(
        version=version,
        installation_time_raw=installation_time_raw,
        installation_time_iso=_time_real_to_iso(installation_time_raw),
    )


def parse_vu_identification(reader: ByteReader) -> tuple[
    NameValue,
    AddressValue,
    str,
    ExtendedSerialNumber,
    VuSoftwareIdentification,
    int,
    str | None,
    str,
]:
    manufacturer_name = parse_name(reader)
    manufacturer_address = parse_address(reader)
    part_number = reader.read_fixed_str(16)
    serial_number = parse_extended_serial_number(reader)
    software_identification = parse_vu_software_identification(reader)
    manufacturing_date_raw = reader.read_time_real_raw()
    manufacturing_date_iso = _time_real_to_iso(manufacturing_date_raw)
    approval_number = reader.read_fixed_str(8)
    return (
        manufacturer_name,
        manufacturer_address,
        part_number,
        serial_number,
        software_identification,
        manufacturing_date_raw,
        manufacturing_date_iso,
        approval_number,
    )


def parse_vehicle_registration_number(reader: ByteReader) -> VehicleRegistrationNumber:
    code_page = reader.read_u8()
    registration_number = reader.read_fixed_str(13)
    return VehicleRegistrationNumber(
        code_page=code_page,
        registration_number=registration_number,
    )


def parse_full_card_number_gen2(reader: ByteReader) -> FullCardNumber:
    card_type = reader.read_u8()
    issuing_nation = reader.read_u8()
    card_number = reader.read_fixed_str(16)
    card_generation = reader.read_u8()
    return FullCardNumber(
        card_type=card_type,
        issuing_nation=issuing_nation,
        card_number=card_number,
        card_generation=card_generation,
    )


def parse_vu_download_activity_data(reader: ByteReader) -> VuDownloadActivityData:
    downloading_time_raw = reader.read_u32_be()
    card_number = parse_full_card_number_gen2(reader)
    company_name = parse_name(reader)
    return VuDownloadActivityData(
        downloading_time_raw=downloading_time_raw,
        downloading_time_iso=_time_real_to_iso(downloading_time_raw),
        card_number=card_number,
        company_name=company_name,
    )


def parse_vu_company_lock(reader: ByteReader) -> VuCompanyLock:
    lock_in_raw = reader.read_u32_be()
    lock_out_raw = reader.read_u32_be()
    company_name = parse_name(reader)
    company_address = parse_address(reader)
    company_card_number = parse_full_card_number_gen2(reader)
    lock_out_iso = None
    if not _is_time_real_max(lock_out_raw):
        lock_out_iso = _time_real_to_iso(lock_out_raw)
    return VuCompanyLock(
        lock_in_time_raw=lock_in_raw,
        lock_in_time_iso=_time_real_to_iso(lock_in_raw),
        lock_out_time_raw=None if _is_time_real_max(lock_out_raw) else lock_out_raw,
        lock_out_time_iso=lock_out_iso,
        company_name=company_name,
        company_address=company_address,
        company_card_number=company_card_number,
    )


def parse_vu_control_activity(reader: ByteReader) -> VuControlActivity:
    control_type = reader.read_u8()
    control_time_raw = reader.read_u32_be()
    control_card_number = parse_full_card_number_gen2(reader)
    download_begin_raw = reader.read_u32_be()
    download_end_raw = reader.read_u32_be()
    return VuControlActivity(
        control_type=control_type,
        control_time_raw=control_time_raw,
        control_time_iso=_time_real_to_iso(control_time_raw),
        control_card_number=control_card_number,
        download_period_begin_raw=download_begin_raw,
        download_period_begin_iso=_time_real_to_iso(download_begin_raw),
        download_period_end_raw=download_end_raw,
        download_period_end_iso=_time_real_to_iso(download_end_raw),
    )


def parse_event_record(data: bytes) -> EventRecord:
    reader = ByteReader(data)
    event_type = reader.read_u8()
    record_purpose = reader.read_u8()
    begin_raw, begin_iso = _normalize_time_real(reader.read_u32_be())
    end_raw, end_iso = _normalize_time_real(reader.read_u32_be())
    driver_begin = parse_full_card_number_gen2(reader)
    driver_end = parse_full_card_number_gen2(reader)
    codriver_begin = parse_full_card_number_gen2(reader)
    codriver_end = parse_full_card_number_gen2(reader)
    similar_events = reader.read_u8() if reader.remaining() >= 1 else None
    if reader.remaining() > 0:
        reader.skip(reader.remaining())
    return EventRecord(
        event_type=event_type,
        record_purpose=record_purpose,
        begin_time_raw=begin_raw,
        begin_time_iso=begin_iso,
        end_time_raw=end_raw,
        end_time_iso=end_iso,
        driver_card_begin=driver_begin,
        driver_card_end=driver_end,
        codriver_card_begin=codriver_begin,
        codriver_card_end=codriver_end,
        similar_events=similar_events,
    )


def parse_fault_record(data: bytes) -> FaultRecord:
    reader = ByteReader(data)
    fault_type = reader.read_u8()
    record_purpose = reader.read_u8()
    begin_raw, begin_iso = _normalize_time_real(reader.read_u32_be())
    end_raw, end_iso = _normalize_time_real(reader.read_u32_be())
    driver_begin = parse_full_card_number_gen2(reader)
    driver_end = parse_full_card_number_gen2(reader)
    codriver_begin = parse_full_card_number_gen2(reader)
    codriver_end = parse_full_card_number_gen2(reader)
    if reader.remaining() > 0:
        reader.skip(reader.remaining())
    return FaultRecord(
        fault_type=fault_type,
        record_purpose=record_purpose,
        begin_time_raw=begin_raw,
        begin_time_iso=begin_iso,
        end_time_raw=end_raw,
        end_time_iso=end_iso,
        driver_card_begin=driver_begin,
        driver_card_end=driver_end,
        codriver_card_begin=codriver_begin,
        codriver_card_end=codriver_end,
    )


def parse_overspeed_control_data(data: bytes) -> VuOverSpeedingControlData:
    reader = ByteReader(data)
    last_control_raw, last_control_iso = _normalize_time_real(reader.read_u32_be())
    first_since_raw, first_since_iso = _normalize_time_real(reader.read_u32_be())
    count = reader.read_u8() if reader.remaining() >= 1 else 0
    if reader.remaining() > 0:
        reader.skip(reader.remaining())
    return VuOverSpeedingControlData(
        last_overspeed_control_time_raw=last_control_raw,
        last_overspeed_control_time_iso=last_control_iso,
        first_overspeed_since_raw=first_since_raw,
        first_overspeed_since_iso=first_since_iso,
        number_of_overspeed_since=count,
    )


def parse_overspeed_event_record(data: bytes) -> OverspeedingEventRecord:
    reader = ByteReader(data)
    event_type = reader.read_u8()
    record_purpose = reader.read_u8()
    begin_raw, begin_iso = _normalize_time_real(reader.read_u32_be())
    end_raw, end_iso = _normalize_time_real(reader.read_u32_be())
    max_speed = reader.read_u8()
    average_speed = reader.read_u8()
    card_number = parse_full_card_number_gen2(reader)
    similar_events = reader.read_u8() if reader.remaining() >= 1 else 0
    if reader.remaining() > 0:
        reader.skip(reader.remaining())
    return OverspeedingEventRecord(
        event_type=event_type,
        record_purpose=record_purpose,
        begin_time_raw=begin_raw,
        begin_time_iso=begin_iso,
        end_time_raw=end_raw,
        end_time_iso=end_iso,
        max_speed=max_speed,
        average_speed=average_speed,
        card_number=card_number,
        similar_events=similar_events,
    )


def parse_vu_card_iw_record(data: bytes) -> VuCardIWRecord:
    reader = ByteReader(data)
    holder_surname = parse_name(reader)
    holder_first_names = parse_name(reader)
    card_number = parse_full_card_number_gen2(reader)
    card_expiry_raw = reader.read_u32_be()
    card_insertion_raw = reader.read_u32_be()
    odometer_insertion = reader.read_u24_be()
    slot_number = reader.read_u8()
    card_withdrawal_raw = reader.read_u32_be()
    odometer_withdrawal = reader.read_u24_be()
    previous_nation = reader.read_u8()
    previous_reg = parse_vehicle_registration_number(reader)
    previous_withdrawal_raw = reader.read_u32_be()

    card_withdrawal_iso = None
    if not _is_time_real_max(card_withdrawal_raw):
        card_withdrawal_iso = _time_real_to_iso(card_withdrawal_raw)

    return VuCardIWRecord(
        holder_surname=holder_surname,
        holder_first_names=holder_first_names,
        card_number=card_number,
        card_expiry_raw=card_expiry_raw,
        card_expiry_iso=_time_real_to_iso(card_expiry_raw),
        card_insertion_time_raw=card_insertion_raw,
        card_insertion_time_iso=_time_real_to_iso(card_insertion_raw),
        card_withdrawal_time_raw=None
        if _is_time_real_max(card_withdrawal_raw)
        else card_withdrawal_raw,
        card_withdrawal_time_iso=card_withdrawal_iso,
        slot_number=slot_number,
        odometer_insertion=odometer_insertion,
        odometer_withdrawal=odometer_withdrawal,
        previous_vehicle_nation=previous_nation,
        previous_vehicle_reg=previous_reg,
        previous_withdrawal_time_raw=previous_withdrawal_raw,
        previous_withdrawal_time_iso=_time_real_to_iso(previous_withdrawal_raw),
    )


def parse_activity_change_infos(raw: bytes) -> tuple[ActivityChangeInfo, ...]:
    changes = []
    for index in range(0, len(raw), 2):
        if index + 2 > len(raw):
            break
        word = int.from_bytes(raw[index:index + 2], "big")
        changes.append(_decode_activity_change_info(word))
    return tuple(changes)


def build_activity_segments(
    date_raw: int, changes: tuple[ActivityChangeInfo, ...]
) -> tuple[ActivitySegment, ...]:
    segments: list[ActivitySegment] = []
    for slot in (0, 1):
        slot_changes = sorted(
            (change for change in changes if change.slot == slot),
            key=lambda item: item.minutes,
        )
        for idx, change in enumerate(slot_changes):
            start = change.minutes
            end = slot_changes[idx + 1].minutes if idx + 1 < len(slot_changes) else 1440
            if start == end:
                continue
            segments.append(
                ActivitySegment(
                    date_raw=date_raw,
                    date_iso=time_real_to_iso(date_raw),
                    slot=slot,
                    start_minute=start,
                    end_minute=end,
                    activity=change.activity,
                    card_status=change.card_status,
                    driving_status=change.driving_status,
                )
            )
    return tuple(segments)


def format_time_real(value: int | None) -> str:
    if value is None:
        return ""
    dt = datetime.fromtimestamp(value, tz=timezone.utc)
    return f"{dt.year}. {dt.month:02d}. {dt.day:02d}. {dt.hour}:{dt.minute:02d}:{dt.second:02d}"


def time_real_to_iso(value: int | None) -> str | None:
    if value is None:
        return None
    return _time_real_to_iso(value)


def format_card_type(card_type: int) -> str:
    labels = {
        0: "Reserved",
        1: "Driver Card",
        2: "Workshop Card",
        3: "Control Card",
        4: "Company Card",
        5: "Manufacturing Card",
        6: "Vehicle Unit",
        7: "Motion Sensor",
    }
    return labels.get(card_type, f"Unknown ({card_type})")


def format_nation_numeric(nation: int) -> str:
    return _NATION_NUMERIC_TO_ALPHA.get(nation, f"0x{nation:02X}")


def format_card_generation(value: int | None) -> str:
    if value is None or value == 0:
        return ""
    if value == 1:
        return "First Generation"
    if value == 2:
        return "Second Generation"
    return str(value)


def format_specific_condition_type(condition_type: int) -> str:
    labels = {
        1: "Out Of Scope End",
        2: "Out Of Scope Begin",
        3: "Ferry/Train Crossing Begin",
        4: "Ferry/Train Crossing End",
    }
    return labels.get(condition_type, f"Unknown ({condition_type})")


def format_driver_event_type(event_type: int) -> str:
    labels = {
        6: "Last Card Session Not Correctly Closed",
        8: "Power Supply Interruption",
        33: "SensorAuthenticationFailure",
    }
    if event_type in labels:
        return labels[event_type]
    return f"Type {event_type}"


def format_event_fault_type(event_type: int) -> str:
    return _EVENT_FAULT_TYPES.get(event_type, f"Unknown (0x{event_type:02X})")


def format_overspeed_event_type(event_type: int, record_purpose: int) -> str:
    if event_type == 0x07:
        return f"Overspeeding {record_purpose}"
    return format_event_fault_type(event_type)


def format_event_card_slot(card: FullCardNumber) -> str:
    if is_card_number_missing(card):
        return "Not Inserted"
    parts = [
        format_card_type(card.card_type),
        format_nation_numeric(card.issuing_nation),
        card.card_number,
    ]
    return " ".join(part for part in parts if part)


def is_card_number_missing(card: FullCardNumber) -> bool:
    if card.card_type == 0xFF and card.issuing_nation == 0xFF:
        return True
    if not card.card_number:
        return True
    return all(ch == "ÿ" for ch in card.card_number)


def format_speed(value: int | None) -> str:
    return "" if value is None else str(value)


def format_control_type(control_type: int) -> str:
    parts = []
    if (control_type >> 7) & 1:
        parts.append("Card Downloading")
    if (control_type >> 6) & 1:
        parts.append("VU Downloading")
    if (control_type >> 5) & 1:
        parts.append("Printing")
    if (control_type >> 4) & 1:
        parts.append("Display")
    return " ".join(parts) if parts else "None"


def format_activity(activity: int, card_status: int) -> str:
    if card_status == 1:
        return "Unknown"
    labels = {
        0: "Rest",
        1: "Availability",
        2: "Work",
        3: "Driving",
    }
    return labels.get(activity, f"Unknown ({activity})")


def format_slot(slot: int) -> str:
    return "Driver" if slot == 0 else "Codriver"


def format_card_slot(slot: int) -> str:
    return "Driver" if slot == 0 else "Codriver"


def format_odometer(value: int | None) -> str:
    return "" if value is None else str(value)


def format_minutes(minutes: int) -> str:
    if minutes < 0:
        return ""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}:{mins:02d}"


def format_holder_name(surname: NameValue, first_names: NameValue) -> str:
    surname_text = surname.text.strip()
    first_text = first_names.text.strip()
    if surname_text and first_text:
        return f"{surname_text} {first_text}"
    return surname_text or first_text


def format_card_status(status: int) -> str:
    return "Not inserted" if status == 1 else "Inserted"


def format_driving_status(status: int) -> str:
    return "Crew" if status == 1 else "Single"


def _time_real_to_iso(value: int) -> str | None:
    if value <= 0:
        return None
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _is_time_real_max(value: int) -> bool:
    return value >= 0xFFFFFFFF


def _decode_activity_change_info(value: int) -> ActivityChangeInfo:
    slot = (value >> 15) & 0x1
    driving_status = (value >> 14) & 0x1
    card_status = (value >> 13) & 0x1
    activity = (value >> 11) & 0x3
    minutes = value & 0x7FF
    return ActivityChangeInfo(
        slot=slot,
        driving_status=driving_status,
        card_status=card_status,
        activity=activity,
        minutes=minutes,
    )


def _normalize_time_real(value: int) -> tuple[int | None, str | None]:
    if value <= 0 or _is_time_real_max(value):
        return None, None
    return value, _time_real_to_iso(value)


_EVENT_FAULT_TYPES = {
    0x04: "Driving Without Appropriate Card",
    0x05: "Card Insertion While Driving",
    0x07: "Overspeeding",
    0x08: "Power Supply Interruption",
    0x09: "Motion Data Error",
    0x21: "SensorAuthenticationFailure",
}


_NATION_NUMERIC_TO_ALPHA = {
    0x00: "",
    0x0A: "CH",
    0x0D: "DK",
    0x18: "H",
    0x28: "PL",
    0x29: "RO",
    0x35: "SRB",
}
