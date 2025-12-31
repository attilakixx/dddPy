from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from ddd_binary import ByteReader
from ddd_structs import (
    ActivityDay,
    CardApplicationIdentification,
    CardEventRecord,
    CardIdentification,
    CardPlaceRecord,
    CardSpecificCondition,
    CardVehicleRecord,
    CardVehicleUnitRecord,
    DriverCardSummary,
    DrivingLicenceInformation,
    EventRecord,
    FaultRecord,
    FullCardNumber,
    VuIdentification,
    VuOverview,
    VuCardIWRecord,
    VuOverSpeedingControlData,
    OverspeedingEventRecord,
    build_activity_segments,
    parse_name,
    parse_event_record,
    parse_fault_record,
    parse_activity_change_infos,
    parse_vehicle_registration_number,
    parse_overspeed_control_data,
    parse_overspeed_event_record,
    parse_vu_card_iw_record,
    parse_vu_company_lock,
    parse_vu_control_activity,
    parse_vu_download_activity_data,
    parse_vu_identification,
    parse_full_card_number_gen2,
    time_real_to_iso,
)

HEADER_READ_LEN = 32
TRANSFER_DATA_POSITIVE_RESPONSE_SID = 0x76

# Known signatures from sample files; keep this small and explicit for now.
_DRIVER_CARD_SIGNATURES = (
    b"\x00\x02\x00\x00\x19\x00",
)
_VU_SIGNATURES = (
    b"\x76\x21\x04\x00\xcd\x00",
)

# TREP values per Annex 1C Appendix 7 (Gen1/Gen2 V1/V2).
_TREPS_GEN1 = {0x01, 0x02, 0x03, 0x04, 0x05}
_TREPS_GEN2_V1 = {0x21, 0x22, 0x23, 0x24, 0x25}
_TREPS_GEN2_V2 = {0x00, 0x24, 0x31, 0x32, 0x33, 0x35}

_TREP_DATA_TYPES = {
    0x00: "Download interface version",
    0x01: "Overview",
    0x02: "Activities",
    0x03: "Events and faults",
    0x04: "Detailed speed",
    0x05: "Technical data",
    0x21: "Overview",
    0x22: "Activities",
    0x23: "Events and faults",
    0x24: "Detailed speed",
    0x25: "Technical data",
    0x31: "Overview",
    0x32: "Activities",
    0x33: "Events and faults",
    0x35: "Technical data",
}

_TECH_TREPS = {0x05, 0x25, 0x35}

_PART_DEFS = (
    ("Overview", {0x01, 0x21, 0x31}, None),
    ("Activities", {0x02, 0x22, 0x32}, None),
    ("Events and faults", {0x03, 0x23, 0x33}, None),
    ("Detailed speed", {0x04, 0x24}, None),
    ("Technical data", {0x05, 0x25, 0x35}, None),
    ("Company locks", {0x05, 0x25, 0x35}, "Contained in Technical data"),
    ("Overspeeding", {0x03, 0x23, 0x33}, "Contained in Events and faults"),
    ("Faults", {0x03, 0x23, 0x33}, "Contained in Events and faults"),
)

_VALID_TREPS = set(_TREP_DATA_TYPES.keys())

_CARD_PART_DEFS = (
    ("File structure", None, False, None, ()),
    ("Application identification", 0x0501, True, ("min", 10), ("gen1", "gen2")),
    ("Card identification", 0x0520, True, ("min", 143), ("gen1", "gen2")),
    ("Driving licence info", 0x0521, True, ("min", 53), ("gen1", "gen2")),
    ("Events", 0x0502, True, ("min", 1), ("gen1", "gen2")),
    ("Faults", 0x0503, True, ("min", 1), ("gen1", "gen2")),
    ("Driver activity", 0x0504, True, ("range", 5548, 13780), ("gen1", "gen2")),
    ("Vehicles used", 0x0505, True, ("min", 1), ("gen1", "gen2")),
    ("Places", 0x0506, True, ("min", 1), ("gen1", "gen2")),
    ("Current usage", 0x0507, True, ("min", 1), ("gen1", "gen2")),
    ("Control activity", 0x0508, True, ("min", 1), ("gen1", "gen2")),
    ("Specific conditions", 0x0522, True, ("min", 1), ("gen1", "gen2")),
    ("GNSS places (Gen2)", 0x0523, True, ("min", 2002), ("gen2",)),
    ("Border crossings (Gen2)", 0x0524, True, ("min", 6050), ("gen2",)),
    ("Card download", 0x050E, True, ("min", 4), ("gen1", "gen2")),
    ("Card certificate", 0xC100, False, ("min", 194), ("gen1",)),
    ("CA certificate", 0xC108, False, ("min", 194), ("gen1",)),
    ("Card certificate (Gen2)", 0xC101, False, ("min", 194), ("gen2",)),
    ("CA certificate (Gen2)", 0xC109, False, ("min", 194), ("gen2",)),
    ("ICC identification", 0x0002, False, ("min", 1), ("gen1", "gen2")),
    ("IC identification", 0x0005, False, ("min", 1), ("gen1", "gen2")),
)

_CARD_SIGNATURE_LEN = 128
_CARD_CERT_LEN = 194

_CARD_APPENDIX_SCHEMES = {
    "gen1": {"data": 0, "sig": 1, "sig_len": 128},
    "gen2": {"data": 2, "sig": 3, "sig_len": 64},
}

_EU_RSA_N = bytes(
    [
        0xE9, 0x80, 0x76, 0x3A, 0x44, 0x4A, 0x95, 0x25,
        0x0A, 0x95, 0x87, 0x82, 0xD1, 0xD5, 0x4A, 0xCF,
        0xC3, 0x23, 0xD2, 0x5F, 0x39, 0x46, 0xB8, 0x16,
        0xE9, 0x2F, 0xCF, 0x9D, 0x32, 0xB4, 0x2A, 0x26,
        0x13, 0xD1, 0xA3, 0x63, 0xB4, 0xE4, 0x35, 0x32,
        0xA0, 0x26, 0x68, 0x63, 0x29, 0xC8, 0x96, 0x63,
        0xCC, 0xC0, 0x01, 0xF7, 0x27, 0x82, 0x06, 0xB6,
        0xAB, 0x65, 0xAD, 0x28, 0x71, 0x84, 0x8A, 0x68,
        0x0F, 0x6A, 0x57, 0xD8, 0xFD, 0xA1, 0xD7, 0x82,
        0xC9, 0xB5, 0x81, 0x29, 0x03, 0xEA, 0x5B, 0x66,
        0xE2, 0xA9, 0xBE, 0x1D, 0x85, 0xBD, 0xD0, 0xFD,
        0xAE, 0x76, 0xA4, 0x60, 0x88, 0xD7, 0x1A, 0x61,
        0x76, 0xB1, 0xF6, 0xA9, 0x84, 0x19, 0x10, 0x04,
        0x24, 0xDC, 0x56, 0xD0, 0x84, 0x6A, 0xA3, 0xC8,
        0x43, 0x90, 0xD3, 0x51, 0x7A, 0x0F, 0x11, 0x92,
        0xDE, 0xDF, 0xF7, 0x40, 0x92, 0x4C, 0xDB, 0xA7,
    ]
)
_EU_RSA_E = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01])

_GEN2_OVERVIEW_SEQUENCE = (
    (0x04,),
    (0x0F,),
    (0x0A,),
    (0x0B,),
    (0x03,),
    (0x13,),
    (0x02,),
    (0x14,),
    (0x10,),
    (0x11,),
    (0x08,),
)
_GEN2_ACTIVITIES_SEQUENCE = (
    (0x06,),
    (0x05,),
    (0x0D,),
    (0x01,),
    (0x1C,),
    (0x16,),
    (0x09,),
    (0x08,),
)
_GEN2_EVENTS_SEQUENCE = (
    (0x18,),
    (0x15,),
    (0x1A,),
    (0x1B,),
    (0x1E,),
    (0x08,),
)
_GEN2_SPEED_SEQUENCE = (
    (0x17,),
    (0x08,),
)
_GEN2_TECH_SEQUENCE = (
    (0x19,),
    (0x20,),
    (0x21,),
    (0x0C,),
    (0x0E,),
    (0x17,),
    (0x1F,),
    (0x08,),
)

_GEN2_TREP_SEQUENCES = {
    0x21: _GEN2_OVERVIEW_SEQUENCE,
    0x22: _GEN2_ACTIVITIES_SEQUENCE,
    0x23: _GEN2_EVENTS_SEQUENCE,
    0x24: _GEN2_SPEED_SEQUENCE,
    0x25: _GEN2_TECH_SEQUENCE,
    0x31: _GEN2_OVERVIEW_SEQUENCE,
    0x32: _GEN2_ACTIVITIES_SEQUENCE,
    0x33: _GEN2_EVENTS_SEQUENCE,
    0x35: _GEN2_TECH_SEQUENCE,
}

_GEN2_PART_LABELS = {
    "Overview": "Overview",
    "Activities": "Activities",
    "Events and faults": "Events and faults",
    "Detailed speed": "Detailed speed",
    "Technical data": "Technical data",
}

_PART_STATUS_PROXIES = {
    "Company locks": "Technical data",
    "Overspeeding": "Events and faults",
    "Faults": "Events and faults",
}


@dataclass(frozen=True)
class DddHeader:
    file_size: int
    detected_type: str
    detected_generation: str
    is_valid: bool
    invalid_reason: str | None
    signature_hex: str
    header_hex: str
    header_length: int
    service_id: int | None
    trep: int | None
    trep_generation: str | None
    trep_data_type: str | None
    download_interface_version: str | None


@dataclass(frozen=True)
class DddPart:
    name: str
    status: str
    note: str | None


@dataclass(frozen=True)
class DddSummary:
    header: DddHeader
    parts: tuple[DddPart, ...]
    vu_identification: VuIdentification | None
    overview: VuOverview | None
    activity_days: tuple[ActivityDay, ...]
    events: tuple[EventRecord, ...]
    faults: tuple[FaultRecord, ...]
    overspeed_control: VuOverSpeedingControlData | None
    overspeed_events: tuple[OverspeedingEventRecord, ...]
    driver_card: DriverCardSummary | None


def parse_header(path: str | Path) -> DddHeader:
    file_path = Path(path)
    with file_path.open("rb") as handle:
        header = handle.read(HEADER_READ_LEN)

    return _parse_header_bytes(header, file_path.stat().st_size)


def parse_summary(path: str | Path) -> DddSummary:
    file_path = Path(path)
    data = file_path.read_bytes()
    header = _parse_header_bytes(data[:HEADER_READ_LEN], len(data))
    parts = _validate_parts(data, header)
    driver_card = _parse_driver_card_summary(data, header)
    vu_identification = _parse_vu_identification(data, header)
    overview = _parse_overview(data, header)
    activity_days = _parse_activities(data, header)
    events, faults, overspeed_control, overspeed_events = _parse_events_faults(
        data, header
    )
    return DddSummary(
        header=header,
        parts=parts,
        vu_identification=vu_identification,
        overview=overview,
        activity_days=activity_days,
        events=events,
        faults=faults,
        overspeed_control=overspeed_control,
        overspeed_events=overspeed_events,
        driver_card=driver_card,
    )


def _parse_header_bytes(header: bytes, file_size: int) -> DddHeader:
    if not header:
        raise ValueError("File is empty.")

    reader = ByteReader(header)
    service_id = None
    trep = None
    if reader.remaining() >= 1 and reader.peek_bytes(1)[0] == TRANSFER_DATA_POSITIVE_RESPONSE_SID:
        service_id = reader.read_u8()
        if reader.remaining() >= 1:
            trep = reader.read_u8()
    trep_generation = None
    trep_data_type = None
    download_interface_version = None

    if service_id == TRANSFER_DATA_POSITIVE_RESPONSE_SID and trep is not None:
        trep_generation = _detect_trep_generation(trep)
        trep_data_type = _TREP_DATA_TYPES.get(trep)
        if trep == 0x00 and len(header) >= 4:
            download_interface_version = _parse_download_interface_version(header[2:4])

    detected_type, detected_generation = _detect_file_type(
        header, service_id, trep, trep_generation
    )
    is_valid, invalid_reason = _validate_header(
        header, service_id, trep, trep_generation, detected_type
    )

    signature = header[:6]
    return DddHeader(
        file_size=file_size,
        detected_type=detected_type,
        detected_generation=detected_generation,
        is_valid=is_valid,
        invalid_reason=invalid_reason,
        signature_hex=_hex_bytes(signature),
        header_hex=_hex_bytes(header),
        header_length=len(header),
        service_id=service_id,
        trep=trep,
        trep_generation=trep_generation,
        trep_data_type=trep_data_type,
        download_interface_version=download_interface_version,
    )


def _detect_file_type(
    header: bytes,
    service_id: int | None,
    trep: int | None,
    trep_generation: str | None,
) -> tuple[str, str]:
    if service_id == TRANSFER_DATA_POSITIVE_RESPONSE_SID and trep is not None:
        if trep_generation is not None:
            return "vehicle_unit", trep_generation
        return "vehicle_unit", "unknown"

    for signature in _DRIVER_CARD_SIGNATURES:
        if header.startswith(signature):
            return "driver_card", "unknown"
    for signature in _VU_SIGNATURES:
        if header.startswith(signature):
            return "vehicle_unit", "unknown"
    return "unknown", "unknown"


def _detect_trep_generation(trep: int) -> str | None:
    if trep in _TREPS_GEN1:
        return "gen1"
    if trep in _TREPS_GEN2_V1:
        if trep == 0x24:
            return "gen2_v1_or_v2"
        return "gen2_v1"
    if trep in _TREPS_GEN2_V2:
        if trep == 0x24:
            return "gen2_v1_or_v2"
        return "gen2_v2"
    return None


def _parse_download_interface_version(data: bytes) -> str:
    if len(data) < 2:
        return "unknown"
    gen = data[0]
    version = data[1]
    if gen == 0x01 and version == 0x01:
        return "gen2_v2 (0x01 0x01)"
    if gen == 0x01:
        return f"gen2 (0x01 {version:02X})"
    return f"0x{gen:02X} 0x{version:02X}"


def _validate_header(
    header: bytes,
    service_id: int | None,
    trep: int | None,
    trep_generation: str | None,
    detected_type: str,
) -> tuple[bool, str | None]:
    if not header:
        return False, "Header (empty)"

    if service_id == TRANSFER_DATA_POSITIVE_RESPONSE_SID:
        if trep is None:
            return False, "Header (missing TREP#2)"
        if trep_generation is None:
            return False, f"Header (unknown TREP#2 0x{trep:02X})"
        if trep == 0x00 and len(header) < 4:
            return False, "Header (download interface version missing)"
        return True, None

    if detected_type in {"driver_card", "vehicle_unit"}:
        return True, None

    return False, "Header (unknown signature)"


def _validate_parts(data: bytes, header: DddHeader) -> tuple[DddPart, ...]:
    if header.detected_type == "driver_card":
        return _validate_driver_card_parts(data)

    if header.detected_type != "vehicle_unit":
        note = (
            "Driver card file"
            if header.detected_type == "driver_card"
            else "Unknown file type"
        )
        return tuple(
            DddPart(name=name, status="not_applicable", note=note)
            for name, _treps, _note in _PART_DEFS
        )

    stats = {
        name: {"count": 0, "invalid": 0, "notes": []}
        for name, _treps, _note in _PART_DEFS
    }

    reader = ByteReader(data)
    while reader.remaining() > 0:
        if reader.remaining() < 2:
            _append_note(stats, "Overview", "Trailing bytes after last part")
            break
        sid = reader.read_u8()
        if sid != TRANSFER_DATA_POSITIVE_RESPONSE_SID:
            _append_note(
                stats,
                "Overview",
                f"Missing SID at offset {reader.tell() - 1}",
                invalid=True,
            )
            if not _resync_to_next_part(reader):
                break
            continue
        trep = reader.read_u8()
        part_label = _TREP_DATA_TYPES.get(trep)
        try:
            ok, note = _validate_vu_part(reader, trep)
        except ValueError as exc:
            ok, note = False, f"Invalid structure ({exc})"
        if ok and reader.remaining() > 0 and reader.peek_bytes(1)[0] != TRANSFER_DATA_POSITIVE_RESPONSE_SID:
            ok = False
            note = "Unexpected bytes after part"
        part_name = _GEN2_PART_LABELS.get(part_label, part_label)
        if part_name in stats:
            stats[part_name]["count"] += 1
            if ok:
                if note and note not in stats[part_name]["notes"]:
                    stats[part_name]["notes"].append(note)
            else:
                stats[part_name]["invalid"] += 1
                stats[part_name]["notes"].append(note or "Invalid structure")
        if not ok and not _resync_to_next_part(reader):
            break

    parts: list[DddPart] = []
    for name, _treps, base_note in _PART_DEFS:
        proxy_name = _PART_STATUS_PROXIES.get(name)
        stat_name = proxy_name or name
        stat = stats.get(stat_name)
        if stat is None:
            status = "missing"
            note = base_note
        else:
            status = _resolve_part_status(stat["count"], stat["invalid"])
            note = _build_part_note(stat, base_note)
        parts.append(DddPart(name=name, status=status, note=note))
    return tuple(parts)


def _scan_treps(data: bytes) -> set[int]:
    treps: set[int] = set()
    for index in range(len(data) - 1):
        if data[index] != TRANSFER_DATA_POSITIVE_RESPONSE_SID:
            continue
        trep = data[index + 1]
        if trep in _TREP_DATA_TYPES:
            treps.add(trep)
    return treps


def _resolve_part_status(count: int, invalid: int) -> str:
    if count == 0:
        return "missing"
    if invalid > 0:
        return "invalid"
    return "valid"


def _build_part_note(stat: dict, base_note: str | None) -> str | None:
    notes: list[str] = []
    count = stat.get("count", 0)
    invalid = stat.get("invalid", 0)
    if count > 0:
        if invalid > 0:
            notes.append(f"Segments valid: {count - invalid}/{count}")
        elif count > 1:
            notes.append(f"Segments: {count}")
    extra_notes = stat.get("notes") or []
    notes.extend(extra_notes)
    if base_note:
        notes.append(base_note)
    if not notes:
        return None
    return "; ".join(notes)


def _append_note(
    stats: dict[str, dict],
    part_name: str,
    note: str,
    invalid: bool = False,
) -> None:
    stat = stats.get(part_name)
    if stat is None:
        return
    if stat["count"] == 0:
        stat["count"] = 1
    if invalid:
        stat["invalid"] += 1
    stat["notes"].append(note)


def _resync_to_next_part(reader: ByteReader) -> bool:
    data = reader.data
    pos = reader.tell()
    while pos + 1 < len(data):
        if data[pos] == TRANSFER_DATA_POSITIVE_RESPONSE_SID and data[pos + 1] in _VALID_TREPS:
            reader.seek(pos)
            return True
        pos += 1
    return False


def _get_gen2_sequence(trep: int, generation: str | None) -> tuple[tuple[int, ...], ...] | None:
    sequence = _GEN2_TREP_SEQUENCES.get(trep)
    if sequence is None:
        return None
    if generation == "gen2_v2" and trep in {0x31}:
        sequence = list(sequence)
        sequence[3] = (0x0B, 0x12)
        return tuple(sequence)
    return sequence


def _read_gen2_record(reader: ByteReader) -> tuple[int, int, int, bool]:
    if reader.remaining() < 5:
        return 0, 0, 0, False
    record_type = reader.read_u8()
    record_size = reader.read_u16_be()
    record_count = reader.read_u16_be()
    total = record_size * record_count
    if reader.remaining() < total:
        return record_type, record_size, record_count, False
    reader.skip(total)
    return record_type, record_size, record_count, True


def _validate_vu_part(reader: ByteReader, trep: int) -> tuple[bool, str | None]:
    if trep == 0x00:
        if reader.remaining() < 2:
            return False, "Download interface version truncated"
        reader.skip(2)
        return True, "Download interface version (not validated)"

    generation = _detect_trep_generation(trep)
    if generation == "gen1":
        return _validate_gen1_part(reader, trep)
    if generation in {"gen2_v1", "gen2_v2", "gen2_v1_or_v2"}:
        return _validate_gen2_part(reader, trep, generation)
    return False, f"Unknown TREP 0x{trep:02X}"


def _validate_gen1_part(reader: ByteReader, trep: int) -> tuple[bool, str | None]:
    try:
        if trep == 0x01:
            if not _skip_exact(reader, 194) or not _skip_exact(reader, 194):
                return False, "Overview certificates truncated"
            if not _skip_exact(reader, 103):
                return False, "Overview header truncated"
            if reader.remaining() < 1:
                return False, "Overview locks count missing"
            locks = reader.read_u8()
            if not _skip_exact(reader, locks * 98):
                return False, "Overview locks truncated"
            if reader.remaining() < 1:
                return False, "Overview controls count missing"
            controls = reader.read_u8()
            if not _skip_exact(reader, controls * 31):
                return False, "Overview controls truncated"
            if not _skip_exact(reader, 128):
                return False, "Overview signature truncated"
            return True, "Structure OK (signature not verified)"
        if trep == 0x02:
            if not _skip_exact(reader, 7):
                return False, "Activities header truncated"
            if reader.remaining() < 2:
                return False, "Activities card IW count missing"
            card_iw = reader.read_u16_be()
            if not _skip_exact(reader, card_iw * 129):
                return False, "Activities card IW records truncated"
            if reader.remaining() < 2:
                return False, "Activities change count missing"
            changes = reader.read_u16_be()
            if not _skip_exact(reader, changes * 2):
                return False, "Activities change records truncated"
            if reader.remaining() < 1:
                return False, "Activities place count missing"
            places = reader.read_u8()
            if not _skip_exact(reader, places * 28):
                return False, "Activities place records truncated"
            if reader.remaining() < 2:
                return False, "Activities condition count missing"
            conditions = reader.read_u16_be()
            if not _skip_exact(reader, conditions * 5):
                return False, "Activities condition records truncated"
            if not _skip_exact(reader, 128):
                return False, "Activities signature truncated"
            return True, "Structure OK (signature not verified)"
        if trep == 0x03:
            if reader.remaining() < 1:
                return False, "Events faults count missing"
            faults = reader.read_u8()
            if not _skip_exact(reader, faults * 82):
                return False, "Fault records truncated"
            if reader.remaining() < 1:
                return False, "Events count missing"
            events = reader.read_u8()
            if not _skip_exact(reader, events * 83):
                return False, "Event records truncated"
            if not _skip_exact(reader, 9):
                return False, "Overspeed control truncated"
            if reader.remaining() < 1:
                return False, "Overspeed events count missing"
            overspeed = reader.read_u8()
            if not _skip_exact(reader, overspeed * 31):
                return False, "Overspeed events truncated"
            if reader.remaining() < 1:
                return False, "Time adjustment count missing"
            time_adj = reader.read_u8()
            if not _skip_exact(reader, time_adj * 98):
                return False, "Time adjustment records truncated"
            if not _skip_exact(reader, 128):
                return False, "Events signature truncated"
            return True, "Structure OK (signature not verified)"
        if trep == 0x04:
            if reader.remaining() < 2:
                return False, "Speed block count missing"
            blocks = reader.read_u16_be()
            if not _skip_exact(reader, blocks * 64):
                return False, "Speed blocks truncated"
            if not _skip_exact(reader, 128):
                return False, "Speed signature truncated"
            return True, "Structure OK (signature not verified)"
        if trep == 0x05:
            if not _skip_exact(reader, 88):
                return False, "Technical data header truncated"
            if not _skip_exact(reader, 8):
                return False, "Technical data block truncated"
            if not _skip_exact(reader, 12):
                return False, "Technical data reserved truncated"
            if not _skip_exact(reader, 24):
                return False, "Technical data block truncated"
            if not _skip_exact(reader, 4):
                return False, "Technical data reserved truncated"
            if reader.remaining() < 1:
                return False, "Calibration count missing"
            calibrations = reader.read_u8()
            if not _skip_exact(reader, calibrations * 167):
                return False, "Calibration records truncated"
            if not _skip_exact(reader, 128):
                return False, "Technical data signature truncated"
            return True, "Structure OK (signature not verified)"
        return False, f"Unsupported Gen1 TREP 0x{trep:02X}"
    except ValueError:
        return False, "Truncated Gen1 part"


def _validate_gen2_part(
    reader: ByteReader, trep: int, generation: str | None
) -> tuple[bool, str | None]:
    sequence = _get_gen2_sequence(trep, generation)
    if sequence is None:
        return False, f"Unsupported Gen2 TREP 0x{trep:02X}"

    allow_extras = generation == "gen2_v2" and trep in {0x32, 0x35}

    if allow_extras:
        for allowed in sequence[:-1]:
            record_type, _size, _count, ok = _read_gen2_record(reader)
            if not ok:
                return False, "Truncated record"
            if record_type not in allowed:
                return False, f"Unexpected record 0x{record_type:02X}"
        signature_seen = False
        while reader.remaining() >= 5:
            record_type, _size, _count, ok = _read_gen2_record(reader)
            if not ok:
                return False, "Truncated record"
            if record_type == 0x08:
                signature_seen = True
                break
        if not signature_seen:
            return False, "Missing signature record"
        return True, "Structure OK (signature not verified)"

    for allowed in sequence:
        record_type, _size, _count, ok = _read_gen2_record(reader)
        if not ok:
            return False, "Truncated record"
        if record_type not in allowed:
            return False, f"Unexpected record 0x{record_type:02X}"

    return True, "Structure OK (signature not verified)"


def _skip_exact(reader: ByteReader, count: int) -> bool:
    if count < 0:
        return False
    if reader.remaining() < count:
        return False
    reader.skip(count)
    return True


def _validate_driver_card_parts(data: bytes) -> tuple[DddPart, ...]:
    entries, trailing, truncated = _parse_card_ef_files(data)
    entries_by_id = {}
    unknown_ids: set[int] = set()

    known_ids = {part_id for _name, part_id, _sig, _rule, _schemes in _CARD_PART_DEFS if part_id}
    for entry in entries:
        entries_by_id.setdefault(entry["file_id"], []).append(entry)
        if entry["appendix"] in {0, 1} and entry["file_id"] not in known_ids:
            unknown_ids.add(entry["file_id"])

    structure_note_parts = []
    if truncated:
        structure_note_parts.append("Truncated file entry")
    if trailing:
        structure_note_parts.append("Trailing bytes after last file entry")
    if unknown_ids:
        unknown_list = ", ".join(f"0x{val:04X}" for val in sorted(unknown_ids))
        structure_note_parts.append(f"Unknown EF file IDs: {unknown_list}")
    structure_note = "; ".join(structure_note_parts) if structure_note_parts else None

    cert_ca_data = _get_card_file_data(entries_by_id, 0xC108, appendices=(0,))
    cert_card_data = _get_card_file_data(entries_by_id, 0xC100, appendices=(0,))
    cert_chain_ok = None
    cert_chain_note = None
    if cert_ca_data and cert_card_data:
        cert_chain_ok, cert_chain_note = _verify_driver_card_certificates(
            cert_ca_data, cert_card_data
        )

    parts: list[DddPart] = []
    for name, file_id, requires_sig, rule, schemes in _CARD_PART_DEFS:
        if file_id is None:
            status = "valid" if not truncated and not trailing else "invalid"
            parts.append(DddPart(name=name, status=status, note=structure_note))
            continue

        status, note = _validate_card_entries(entries_by_id.get(file_id, []), requires_sig, rule, schemes)
        notes: list[str] = []
        if note:
            notes.append(note)
        if file_id == 0xC108 and cert_chain_ok is False:
            status = "invalid"
            if cert_chain_note:
                notes.append(cert_chain_note)
        if file_id == 0xC100 and cert_chain_ok is False:
            status = "invalid"
            if cert_chain_note:
                notes.append(cert_chain_note)
        if file_id in {0xC101, 0xC109} and status == "valid":
            notes.append("ECC certificate not verified")

        parts.append(DddPart(name=name, status=status, note="; ".join(notes) if notes else None))
    return tuple(parts)


def _parse_card_ef_files(data: bytes) -> tuple[list[dict], bool, bool]:
    entries: list[dict] = []
    offset = 0
    truncated = False
    while offset + 5 <= len(data):
        file_id = int.from_bytes(data[offset:offset + 2], "big")
        appendix = data[offset + 2]
        length = int.from_bytes(data[offset + 3:offset + 5], "big")
        end = offset + 5 + length
        if end > len(data):
            truncated = True
            break
        entries.append(
            {
                "file_id": file_id,
                "appendix": appendix,
                "length": length,
                "offset": offset,
                "data": data[offset + 5:end],
            }
        )
        offset = end
    trailing = offset != len(data)
    return entries, trailing, truncated


def _validate_card_length(length: int, rule: tuple) -> bool:
    if not rule:
        return True
    if rule[0] == "min":
        return length >= rule[1]
    if rule[0] == "range":
        return rule[1] <= length <= rule[2]
    return True


def _validate_card_entries(
    entries: list[dict],
    requires_sig: bool,
    rule: tuple | None,
    schemes: tuple[str, ...],
) -> tuple[str, str | None]:
    if not entries:
        return "missing", None

    scheme_results: list[tuple[str, bool, list[str]]] = []
    for scheme in schemes:
        scheme_info = _CARD_APPENDIX_SCHEMES.get(scheme)
        if scheme_info is None:
            continue
        data_appendix = scheme_info["data"]
        sig_appendix = scheme_info["sig"]
        sig_len = scheme_info["sig_len"]
        data_entries = [entry for entry in entries if entry["appendix"] == data_appendix]
        sig_entries = [entry for entry in entries if entry["appendix"] == sig_appendix]
        if not data_entries and not sig_entries:
            continue
        notes: list[str] = []
        valid = True
        if len(data_entries) > 1:
            notes.append("Duplicate data entries")
        if len(sig_entries) > 1:
            notes.append("Duplicate signature entries")

        if not data_entries:
            valid = False
            notes.append("Missing data appendix")
        else:
            if rule is not None and not _validate_card_length(data_entries[0]["length"], rule):
                valid = False
                notes.append("Unexpected length")
        if requires_sig:
            if not sig_entries:
                valid = False
                notes.append("Missing signature appendix")
            elif sig_entries[0]["length"] != sig_len:
                valid = False
                notes.append("Invalid signature length")
        scheme_results.append((scheme, valid, notes))

    if not scheme_results:
        return "missing", None

    if any(valid for _scheme, valid, _notes in scheme_results):
        combined_notes = []
        for scheme, valid, notes in scheme_results:
            if notes:
                label = "Gen1" if scheme == "gen1" else "Gen2"
                combined_notes.append(f"{label}: {', '.join(notes)}")
        return "valid", "; ".join(combined_notes) if combined_notes else None

    combined_notes = []
    for scheme, _valid, notes in scheme_results:
        label = "Gen1" if scheme == "gen1" else "Gen2"
        if notes:
            combined_notes.append(f"{label}: {', '.join(notes)}")
    return "invalid", "; ".join(combined_notes) if combined_notes else None


def _get_card_file_data(
    entries_by_id: dict, file_id: int, appendices: tuple[int, ...]
) -> bytes | None:
    for appendix in appendices:
        for entry in entries_by_id.get(file_id, []):
            if entry["appendix"] == appendix:
                return entry["data"]
    return None


def _get_card_file_entry(
    entries_by_id: dict, file_id: int, appendices: tuple[int, ...]
) -> dict | None:
    for appendix in appendices:
        for entry in entries_by_id.get(file_id, []):
            if entry["appendix"] == appendix:
                return entry
    return None


def _verify_driver_card_certificates(
    ca_data: bytes, card_data: bytes
) -> tuple[bool, str | None]:
    if len(ca_data) < _CARD_CERT_LEN or len(card_data) < _CARD_CERT_LEN:
        return False, "Certificate data truncated"
    ca_ok, ca_content = _verify_driver_card_certificate(ca_data, _EU_RSA_N, _EU_RSA_E)
    if not ca_ok or ca_content is None:
        return False, "CA certificate invalid"
    member_key_n = ca_content[28:156]
    member_key_e = ca_content[156:164]
    if len(member_key_n) != 128 or len(member_key_e) != 8:
        return False, "Member state key invalid"
    card_ok, _card_content = _verify_driver_card_certificate(
        card_data, member_key_n, member_key_e
    )
    if not card_ok:
        return False, "Card certificate invalid"
    return True, None


def _verify_driver_card_certificate(
    data: bytes, key_n: bytes, key_e: bytes
) -> tuple[bool, bytes | None]:
    if len(data) < _CARD_CERT_LEN:
        return False, None
    signature = data[:128]
    cndash = data[128:186]
    decoded = _rsa_decode(signature, key_n, key_e)
    if len(decoded) != _CARD_SIGNATURE_LEN:
        return False, None
    if decoded[0] != 0x6A or decoded[-1] != 0xBC:
        return False, None
    crdash = decoded[1:107]
    hdash = decoded[107:127]
    content = crdash + cndash
    digest = hashlib.sha1(content).digest()
    if digest != hdash:
        return False, None
    return True, content


def _rsa_decode(signature: bytes, key_n: bytes, key_e: bytes) -> bytes:
    modulus = int.from_bytes(key_n, "big")
    exponent = int.from_bytes(key_e, "big")
    value = pow(int.from_bytes(signature, "big"), exponent, modulus)
    length = (modulus.bit_length() + 7) // 8
    return value.to_bytes(length, "big")


def _parse_vu_identification(
    data: bytes, header: DddHeader
) -> VuIdentification | None:
    if header.detected_type != "vehicle_unit":
        return None

    candidates = [
        (index, trep)
        for index, trep in _iter_trep_offsets(data)
        if trep in _TECH_TREPS
    ]
    for index, trep in candidates:
        base_offset = index + 2
        for prefix in range(0, 13):
            try:
                reader = ByteReader(data)
                reader.seek(base_offset + prefix)
                (
                    manufacturer_name,
                    manufacturer_address,
                    part_number,
                    serial_number,
                    software_identification,
                    manufacturing_date_raw,
                    manufacturing_date_iso,
                    approval_number,
                ) = parse_vu_identification(reader)
            except ValueError:
                continue

            if not _looks_like_identification(
                manufacturer_name.text,
                manufacturer_address.text,
                part_number,
                approval_number,
            ):
                continue

            return VuIdentification(
                manufacturer_name=manufacturer_name,
                manufacturer_address=manufacturer_address,
                part_number=part_number,
                serial_number=serial_number,
                software_identification=software_identification,
                manufacturing_date_raw=manufacturing_date_raw,
                manufacturing_date_iso=manufacturing_date_iso,
                approval_number=approval_number,
                source_trep=trep,
                source_offset=index,
                prefix_bytes=prefix,
            )

    return None


def _parse_overview(data: bytes, header: DddHeader) -> VuOverview | None:
    if header.detected_type != "vehicle_unit":
        return None

    offsets = list(_iter_trep_offsets(data))
    for idx, (_offset, trep) in enumerate(offsets):
        if trep in {0x21, 0x31, 0x01}:
            segment = _slice_segment(data, offsets, idx)
            if trep == 0x21:
                return _parse_overview_gen2(segment)
            # TODO: Add parsers for TREP 0x01 and 0x31.
    return None


def _parse_overview_gen2(segment: bytes) -> VuOverview:
    reader = ByteReader(segment)
    reader.read_u8()  # SID
    reader.read_u8()  # TREP

    vin = None
    registration = None
    current_time_raw = None
    download_begin_raw = None
    download_end_raw = None
    card_slots_status = None
    last_download = None
    company_locks: list = []
    control_activities: list = []

    while reader.remaining() >= 5:
        record_type = reader.read_u8()
        record_size = reader.read_u16_be()
        record_count = reader.read_u16_be()
        total = record_size * record_count
        if reader.remaining() < total:
            break
        record_data = reader.read_bytes(total)

        if record_count == 0:
            continue

        if record_type == 0x0A:
            vin = record_data[:record_size].decode("latin-1", errors="replace").strip()
        elif record_type == 0x0B:
            record_reader = ByteReader(record_data[:record_size])
            registration = parse_vehicle_registration_number(record_reader)
        elif record_type == 0x03:
            current_time_raw = int.from_bytes(record_data[:4], "big")
        elif record_type == 0x13:
            download_begin_raw = int.from_bytes(record_data[:4], "big")
            download_end_raw = int.from_bytes(record_data[4:8], "big")
        elif record_type == 0x02:
            card_slots_status = record_data[0]
        elif record_type == 0x14:
            record_reader = ByteReader(record_data[:record_size])
            last_download = parse_vu_download_activity_data(record_reader)
        elif record_type == 0x10:
            record_reader = ByteReader(record_data)
            for _ in range(record_count):
                company_locks.append(parse_vu_company_lock(record_reader))
        elif record_type == 0x11:
            record_reader = ByteReader(record_data)
            for _ in range(record_count):
                control_activities.append(parse_vu_control_activity(record_reader))

    return VuOverview(
        vin=vin,
        registration_number=registration,
        current_time_raw=current_time_raw,
        current_time_iso=time_real_to_iso(current_time_raw),
        download_period_begin_raw=download_begin_raw,
        download_period_begin_iso=time_real_to_iso(download_begin_raw),
        download_period_end_raw=download_end_raw,
        download_period_end_iso=time_real_to_iso(download_end_raw),
        card_slots_status=card_slots_status,
        last_download=last_download,
        company_locks=tuple(company_locks),
        control_activities=tuple(control_activities),
    )


def _parse_activities(
    data: bytes, header: DddHeader
) -> tuple[ActivityDay, ...]:
    if header.detected_type != "vehicle_unit":
        return ()

    days: list[ActivityDay] = []
    offsets = list(_iter_trep_offsets(data))
    for idx, (_offset, trep) in enumerate(offsets):
        if trep != 0x22:
            continue
        segment = _slice_segment(data, offsets, idx)
        day = _parse_activity_segment(segment)
        if day is not None:
            days.append(day)
    return tuple(days)


def _parse_events_faults(
    data: bytes, header: DddHeader
) -> tuple[
    tuple[EventRecord, ...],
    tuple[FaultRecord, ...],
    VuOverSpeedingControlData | None,
    tuple[OverspeedingEventRecord, ...],
]:
    if header.detected_type != "vehicle_unit":
        return (), (), None, ()

    events: list[EventRecord] = []
    faults: list[FaultRecord] = []
    overspeed_events: list[OverspeedingEventRecord] = []
    overspeed_control: VuOverSpeedingControlData | None = None

    offsets = list(_iter_trep_offsets(data))
    for idx, (_offset, trep) in enumerate(offsets):
        if trep not in {0x03, 0x23, 0x33}:
            continue
        segment = _slice_segment(data, offsets, idx)
        reader = ByteReader(segment)
        reader.read_u8()
        reader.read_u8()

        while reader.remaining() >= 5:
            record_type = reader.read_u8()
            record_size = reader.read_u16_be()
            record_count = reader.read_u16_be()
            total = record_size * record_count
            if reader.remaining() < total:
                break
            record_data = reader.read_bytes(total)

            if record_count == 0:
                continue

            if record_type == 0x15:
                offset = 0
                for _ in range(record_count):
                    chunk = record_data[offset:offset + record_size]
                    if len(chunk) < record_size:
                        break
                    try:
                        events.append(parse_event_record(chunk))
                    except ValueError:
                        pass
                    offset += record_size
            elif record_type == 0x18:
                offset = 0
                for _ in range(record_count):
                    chunk = record_data[offset:offset + record_size]
                    if len(chunk) < record_size:
                        break
                    try:
                        faults.append(parse_fault_record(chunk))
                    except ValueError:
                        pass
                    offset += record_size
            elif record_type == 0x1A:
                offset = 0
                for _ in range(record_count):
                    chunk = record_data[offset:offset + record_size]
                    if len(chunk) < record_size:
                        break
                    try:
                        overspeed_control = parse_overspeed_control_data(chunk)
                    except ValueError:
                        pass
                    offset += record_size
            elif record_type == 0x1B:
                offset = 0
                for _ in range(record_count):
                    chunk = record_data[offset:offset + record_size]
                    if len(chunk) < record_size:
                        break
                    try:
                        overspeed_events.append(parse_overspeed_event_record(chunk))
                    except ValueError:
                        pass
                    offset += record_size

    return (
        tuple(events),
        tuple(faults),
        overspeed_control,
        tuple(overspeed_events),
    )


def _parse_driver_card_summary(
    data: bytes, header: DddHeader
) -> DriverCardSummary | None:
    if header.detected_type != "driver_card":
        return None

    segments = _parse_driver_card_segments(data)
    seg_ident = segments.get(0x120D, b"")
    seg_misc = segments.get(0x4420, b"")
    entries, _trailing, _truncated = _parse_card_ef_files(data)
    entries_by_id: dict[int, list[dict]] = {}
    for entry in entries:
        entries_by_id.setdefault(entry["file_id"], []).append(entry)

    app_entry = _get_card_file_entry(entries_by_id, 0x0501, appendices=(2, 0))
    card_app = _parse_card_application_identification(data, app_entry)
    driving_licence = _parse_driving_licence_information(data)
    card_ident = _parse_card_identification(data, card_app)
    events = _parse_driver_card_events(
        seg_ident, card_app.events_per_type if card_app else None
    )
    faults = _parse_driver_card_faults(
        seg_ident, card_app.faults_per_type if card_app else None
    )
    vehicles_data = _get_card_file_data(entries_by_id, 0x0505, appendices=(2, 0))
    vehicles_used = _parse_driver_card_vehicles_used(
        vehicles_data, card_app.vehicle_records if card_app else None
    )
    places_entry = _get_card_file_entry(entries_by_id, 0x0506, appendices=(2, 0))
    places = _parse_driver_card_places(
        places_entry, card_app.place_records if card_app else None
    )
    specific_conditions = _parse_driver_card_specific_conditions(seg_misc)
    vehicle_units = _parse_driver_card_vehicle_units_from_gnss(
        _get_card_file_entry(entries_by_id, 0x0523, appendices=(2, 0))
    )
    if not vehicle_units:
        vehicle_units = _parse_driver_card_vehicle_units(seg_misc)

    return DriverCardSummary(
        application_identification=card_app,
        driving_licence=driving_licence,
        card_identification=card_ident,
        events=events,
        faults=faults,
        vehicles_used=vehicles_used,
        places=places,
        specific_conditions=specific_conditions,
        vehicle_units=vehicle_units,
    )


def _parse_driver_card_segments(data: bytes) -> dict[int, bytes]:
    segments: dict[int, bytes] = {}
    if len(data) < 10:
        return segments
    offset = 6
    while offset + 4 <= len(data):
        file_id = int.from_bytes(data[offset:offset + 2], "big")
        length = int.from_bytes(data[offset + 2:offset + 4], "big")
        if length <= 0:
            break
        end = offset + 4 + length
        if end > len(data):
            break
        if file_id not in segments:
            segments[file_id] = data[offset + 4:end]
        offset = end
    return segments


def _find_driver_card_tag_record(
    data: bytes,
    record_id: int,
    min_length: int,
    max_length: int | None = None,
) -> tuple[int, int] | None:
    if not data:
        return None
    needle = record_id.to_bytes(2, "big")
    start = 0
    while True:
        idx = data.find(needle, start)
        if idx == -1:
            return None
        if idx + 5 <= len(data):
            length = int.from_bytes(data[idx + 2:idx + 5], "big")
            if length >= min_length and (max_length is None or length <= max_length):
                end = idx + 5 + length
                if end <= len(data):
                    return idx + 5, length
        start = idx + 1


def _parse_card_application_identification(
    data: bytes,
    entry: dict | None = None,
) -> CardApplicationIdentification | None:
    if entry is None:
        record = _find_driver_card_tag_record(data, 0x0501, min_length=10, max_length=17)
        if record is None:
            return None
        start, length = record
        payload = data[start:start + length]
        appendix = None
    else:
        payload = entry.get("data") or b""
        length = entry.get("length", len(payload))
        appendix = entry.get("appendix")

    if len(payload) < 10:
        return None
    card_type = payload[0]
    if card_type not in {1, 2, 3, 4, 5, 6}:
        return None
    card_structure_version = int.from_bytes(payload[1:3], "big")
    events_per_type = payload[3]
    faults_per_type = payload[4]
    activity_length = int.from_bytes(payload[5:7], "big")
    vehicle_records = int.from_bytes(payload[7:9], "big")
    if length >= 11:
        place_records = int.from_bytes(payload[9:11], "big")
    else:
        place_records = payload[9]
    card_generation = None
    if appendix == 2:
        card_generation = 2
    elif appendix == 0:
        card_generation = 1
    return CardApplicationIdentification(
        card_type=card_type,
        card_structure_version=card_structure_version,
        events_per_type=events_per_type,
        faults_per_type=faults_per_type,
        activity_structure_length=activity_length,
        vehicle_records=vehicle_records,
        place_records=place_records,
        card_generation=card_generation,
    )


def _parse_driving_licence_information(
    data: bytes,
) -> DrivingLicenceInformation | None:
    record = _find_driver_card_tag_record(data, 0x0521, min_length=53, max_length=80)
    if record is None:
        return None
    start, length = record
    if length < 53:
        return None
    reader = ByteReader(data)
    reader.seek(start)
    authority = parse_name(reader)
    issuing_nation = reader.read_u8()
    licence_number = reader.read_fixed_str(16)
    if not authority.text or not licence_number:
        return None
    return DrivingLicenceInformation(
        issuing_nation=issuing_nation,
        issuing_authority=authority,
        licence_number=licence_number,
    )


def _parse_card_identification(
    data: bytes,
    card_app: CardApplicationIdentification | None,
) -> CardIdentification | None:
    record = _find_driver_card_tag_record(data, 0x0520, min_length=140, max_length=200)
    if record is None:
        return None
    start, length = record
    required_len = 1 + 16 + 36 + 12 + 36 + 36 + 4
    if length < required_len:
        return None
    reader = ByteReader(data)
    reader.seek(start)
    issuing_nation = reader.read_u8()
    card_number = reader.read_fixed_str(16)
    issuing_authority = parse_name(reader)
    issue_raw = reader.read_u32_be()
    validity_raw = reader.read_u32_be()
    expiry_raw = reader.read_u32_be()
    if not _looks_like_time_real(issue_raw):
        return None
    if not _looks_like_time_real(validity_raw):
        return None
    if not _looks_like_time_real(expiry_raw):
        return None
    if not (issue_raw <= validity_raw <= expiry_raw):
        return None

    holder_surname = parse_name(reader)
    holder_first_names = parse_name(reader)
    birth_date_raw = reader.read_bytes(4)
    birth_date_bcd = _decode_birth_date(birth_date_raw)
    birth_date_iso = _bcd_date_to_iso(birth_date_bcd)
    if birth_date_iso is None:
        return None

    card_type = card_app.card_type if card_app else 1
    card_generation = card_app.card_generation if card_app and card_app.card_generation else 0
    card_number_value = FullCardNumber(
        card_type=card_type,
        issuing_nation=issuing_nation,
        card_number=card_number,
        card_generation=card_generation,
    )

    if not _looks_like_card_number(card_number):
        return None

    return CardIdentification(
        card_number=card_number_value,
        issuing_authority=issuing_authority,
        issue_date_raw=issue_raw,
        issue_date_iso=time_real_to_iso(issue_raw),
        validity_begin_raw=validity_raw,
        validity_begin_iso=time_real_to_iso(validity_raw),
        expiry_date_raw=expiry_raw,
        expiry_date_iso=time_real_to_iso(expiry_raw),
        holder_surname=holder_surname,
        holder_first_names=holder_first_names,
        birth_date_bcd=birth_date_bcd,
        birth_date_iso=birth_date_iso,
    )


def _parse_driver_card_events(
    data: bytes, events_per_type: int | None
) -> tuple[CardEventRecord, ...]:
    records: list[CardEventRecord] = []
    if not data or not events_per_type:
        return ()
    record_len = 24
    block = _find_driver_card_record_block(data, record_len)
    if block is None:
        return ()
    start, count = block
    for idx in range(count):
        offset = start + idx * record_len
        chunk = data[offset:offset + record_len]
        event_type = chunk[0]
        if event_type == 0:
            continue
        begin_raw = int.from_bytes(chunk[1:5], "big")
        end_raw = int.from_bytes(chunk[5:9], "big")
        registration_nation = chunk[9]
        reg_reader = ByteReader(chunk[10:24])
        registration_number = parse_vehicle_registration_number(reg_reader)
        records.append(
            CardEventRecord(
                event_type=event_type,
                begin_time_raw=begin_raw if _looks_like_time_real(begin_raw) else None,
                begin_time_iso=time_real_to_iso(begin_raw),
                end_time_raw=end_raw if _looks_like_time_real(end_raw) else None,
                end_time_iso=time_real_to_iso(end_raw),
                registration_nation=registration_nation,
                registration_number=registration_number,
            )
        )
    return tuple(records)


def _parse_driver_card_faults(
    data: bytes, faults_per_type: int | None
) -> tuple[CardEventRecord, ...]:
    if not data or not faults_per_type:
        return ()
    record_len = 24
    block = _find_driver_card_record_block(data, record_len, min_run=faults_per_type)
    if block is None:
        return ()
    start, count = block
    records: list[CardEventRecord] = []
    for idx in range(count):
        offset = start + idx * record_len
        chunk = data[offset:offset + record_len]
        event_type = chunk[0]
        if event_type == 0:
            continue
        begin_raw = int.from_bytes(chunk[1:5], "big")
        end_raw = int.from_bytes(chunk[5:9], "big")
        registration_nation = chunk[9]
        reg_reader = ByteReader(chunk[10:24])
        registration_number = parse_vehicle_registration_number(reg_reader)
        records.append(
            CardEventRecord(
                event_type=event_type,
                begin_time_raw=begin_raw if _looks_like_time_real(begin_raw) else None,
                begin_time_iso=time_real_to_iso(begin_raw),
                end_time_raw=end_raw if _looks_like_time_real(end_raw) else None,
                end_time_iso=time_real_to_iso(end_raw),
                registration_nation=registration_nation,
                registration_number=registration_number,
            )
        )
    return tuple(records)


def _parse_driver_card_vehicles_used(
    data: bytes | None, vehicle_records: int | None
) -> tuple[CardVehicleRecord, ...]:
    if not data or len(data) < 33:
        return ()
    payload_len = len(data) - 2
    if payload_len <= 0:
        return ()

    record_len = None
    for candidate in (48, 31):
        if payload_len % candidate == 0:
            record_len = candidate
            break
    if record_len is None:
        if payload_len >= 48:
            record_len = 48
        elif payload_len >= 31:
            record_len = 31
        else:
            return ()

    has_vin = record_len == 48
    record_count = payload_len // record_len
    if vehicle_records:
        record_count = min(record_count, vehicle_records)

    records: list[CardVehicleRecord] = []
    for idx in range(record_count):
        offset = 2 + idx * record_len
        record = data[offset:offset + record_len]
        if len(record) < record_len:
            break
        odo_begin = int.from_bytes(record[0:3], "big")
        odo_end = int.from_bytes(record[3:6], "big")
        first_use = int.from_bytes(record[6:10], "big")
        last_use = int.from_bytes(record[10:14], "big")
        registration_nation = record[14]
        reg_reader = ByteReader(record[15:29])
        registration_number = parse_vehicle_registration_number(reg_reader)
        vin = ""
        if has_vin and len(record) >= 48:
            vin = record[31:48].decode("latin-1", errors="replace").strip()
        records.append(
            CardVehicleRecord(
                first_use_raw=first_use if _looks_like_time_real(first_use) else None,
                first_use_iso=time_real_to_iso(first_use),
                last_use_raw=last_use if _looks_like_time_real(last_use) else None,
                last_use_iso=time_real_to_iso(last_use),
                odometer_begin=odo_begin,
                odometer_end=odo_end,
                registration_nation=registration_nation,
                registration_number=registration_number,
                vin=vin,
            )
        )
    return tuple(records)


def _parse_driver_card_places(
    entry: dict | None, place_records: int | None
) -> tuple[CardPlaceRecord, ...]:
    if entry is None:
        return ()
    data = entry.get("data") or b""
    if not data:
        return ()

    appendix = entry.get("appendix")
    header_len = 2 if appendix == 2 else 1
    if len(data) <= header_len:
        return ()

    record_len = None
    if place_records and (len(data) - header_len) % place_records == 0:
        record_len = (len(data) - header_len) // place_records
    if record_len not in (10, 21):
        record_len = 21 if appendix == 2 else 10

    record_count = (len(data) - header_len) // record_len
    if place_records:
        record_count = min(record_count, place_records)

    records: list[CardPlaceRecord] = []
    for idx in range(record_count):
        offset = header_len + idx * record_len
        record = data[offset:offset + record_len]
        if len(record) < record_len:
            break
        if all(b == 0 for b in record):
            continue

        time_raw = int.from_bytes(record[0:4], "big")
        entry_type = record[4]
        country = record[5]
        region = record[6]
        odometer = int.from_bytes(record[7:10], "big")

        gps_time_raw = None
        accuracy = None
        latitude_raw = None
        longitude_raw = None
        if record_len >= 21:
            gps_time_raw = int.from_bytes(record[10:14], "big")
            accuracy = record[14]
            latitude_raw = _decode_signed_24(int.from_bytes(record[15:18], "big"))
            longitude_raw = _decode_signed_24(int.from_bytes(record[18:21], "big"))

        time_value = time_raw if _looks_like_time_real(time_raw) else None
        gps_time_value = None
        if gps_time_raw is not None and _looks_like_time_real(gps_time_raw):
            gps_time_value = gps_time_raw

        if (
            time_value is None
            and gps_time_value is None
            and country == 0
            and region == 0
            and odometer == 0
            and entry_type == 0
        ):
            continue

        records.append(
            CardPlaceRecord(
                time_raw=time_value,
                time_iso=time_real_to_iso(time_value) if time_value else None,
                entry_type=entry_type,
                country=country,
                region=region,
                odometer=odometer if odometer else None,
                gps_time_raw=gps_time_value,
                gps_time_iso=time_real_to_iso(gps_time_value) if gps_time_value else None,
                accuracy=accuracy,
                latitude_raw=latitude_raw,
                longitude_raw=longitude_raw,
            )
        )
    return tuple(records)


def _parse_driver_card_specific_conditions(
    data: bytes,
) -> tuple[CardSpecificCondition, ...]:
    if not data:
        return ()
    record_len = 5
    block = _find_driver_card_condition_block(data, record_len)
    if block is None:
        return ()
    start, count = block
    records: list[CardSpecificCondition] = []
    for idx in range(count):
        offset = start + idx * record_len
        condition_type = data[offset]
        time_raw = int.from_bytes(data[offset + 1:offset + 5], "big")
        records.append(
            CardSpecificCondition(
                time_raw=time_raw if _looks_like_time_real(time_raw) else None,
                time_iso=time_real_to_iso(time_raw),
                condition_type=condition_type,
            )
        )
    return tuple(records)


def _parse_driver_card_vehicle_units(
    data: bytes,
) -> tuple[CardVehicleUnitRecord, ...]:
    if not data:
        return ()
    records: list[CardVehicleUnitRecord] = []
    for idx in range(len(data) - 10):
        timestamp = int.from_bytes(data[idx:idx + 4], "big")
        if not _looks_like_time_real(timestamp):
            continue
        manufacturer_code = data[idx + 4]
        device_id = data[idx + 5]
        version_bytes = data[idx + 6:idx + 10]
        if not all(48 <= b <= 57 for b in version_bytes):
            continue
        software_version = version_bytes.decode("latin-1")
        records.append(
            CardVehicleUnitRecord(
                timestamp_raw=timestamp,
                timestamp_iso=time_real_to_iso(timestamp),
                manufacturer_code=manufacturer_code,
                device_id=device_id,
                software_version=software_version,
            )
        )
    return tuple(records)


def _parse_driver_card_vehicle_units_from_gnss(
    entry: dict | None,
) -> tuple[CardVehicleUnitRecord, ...]:
    if entry is None:
        return ()
    data = entry.get("data") or b""
    if len(data) < 12:
        return ()
    timestamp = int.from_bytes(data[2:6], "big")
    manufacturer_code = data[6]
    device_id = data[7]
    software_version = data[8:12].decode("latin-1", errors="replace").strip()
    if not _looks_like_time_real(timestamp):
        return ()
    return (
        CardVehicleUnitRecord(
            timestamp_raw=timestamp,
            timestamp_iso=time_real_to_iso(timestamp),
            manufacturer_code=manufacturer_code,
            device_id=device_id,
            software_version=software_version,
        ),
    )


def _find_driver_card_record_block(
    data: bytes, record_len: int, min_run: int | None = None
) -> tuple[int, int] | None:
    best: tuple[int, int] | None = None
    for alignment in range(record_len):
        run_start = None
        run_len = 0
        max_run = (0, None)
        for offset in range(alignment, len(data) - record_len + 1, record_len):
            chunk = data[offset:offset + record_len]
            if not _looks_like_driver_card_record(chunk):
                if run_len > max_run[0]:
                    max_run = (run_len, run_start)
                run_start = None
                run_len = 0
                continue
            if run_start is None:
                run_start = offset
                run_len = 1
            else:
                run_len += 1
        if run_len > max_run[0]:
            max_run = (run_len, run_start)
        if best is None or max_run[0] > best[1]:
            if max_run[1] is not None:
                best = (max_run[1], max_run[0])
    if best is None:
        return None
    if min_run is not None and best[1] < min_run:
        return None
    return best


def _find_driver_card_condition_block(
    data: bytes, record_len: int
) -> tuple[int, int] | None:
    best: tuple[int, int] | None = None
    for alignment in range(record_len):
        run_start = None
        run_len = 0
        max_run = (0, None)
        for offset in range(alignment, len(data) - record_len + 1, record_len):
            condition_type = data[offset]
            time_raw = int.from_bytes(data[offset + 1:offset + 5], "big")
            ok = condition_type in {1, 2, 3, 4} and _looks_like_time_real(time_raw)
            if not ok:
                if run_len > max_run[0]:
                    max_run = (run_len, run_start)
                run_start = None
                run_len = 0
                continue
            if run_start is None:
                run_start = offset
                run_len = 1
            else:
                run_len += 1
        if run_len > max_run[0]:
            max_run = (run_len, run_start)
        if best is None or max_run[0] > best[1]:
            if max_run[1] is not None:
                best = (max_run[1], max_run[0])
    return best


def _looks_like_driver_card_record(chunk: bytes) -> bool:
    if not chunk:
        return False
    event_type = chunk[0]
    if event_type not in {0, 6, 8, 12, 33} and event_type > 0x40:
        return False
    reg = chunk[11:24]
    if not all((b == 0 or b == 0x20 or 32 <= b < 127) for b in reg):
        return False
    return True


def _looks_like_name_bytes(raw: bytes, min_alnum: int = 4) -> bool:
    text = raw.decode("latin-1", errors="replace").strip()
    if len(text) < 4:
        return False
    printable = sum(1 for ch in text if ch.isprintable())
    if printable / len(text) < 0.9:
        return False
    if sum(1 for ch in text if ch.isalnum()) < min_alnum:
        return False
    return True


def _looks_like_licence_bytes(raw: bytes) -> bool:
    text = raw.decode("latin-1", errors="replace").strip()
    if len(text) < 6:
        return False
    if not all(ch.isalnum() for ch in text):
        return False
    return sum(1 for ch in text if ch.isalnum()) >= 6


def _looks_like_time_real(value: int) -> bool:
    return 946684800 <= value <= 1893456000


def _decode_signed_24(value: int) -> int:
    if value & 0x800000:
        return value - 0x1000000
    return value


def _looks_like_card_number(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) < 6:
        return False
    return sum(1 for ch in stripped if ch.isalnum()) >= 4


def _decode_birth_date(raw: bytes) -> str:
    if len(raw) != 4:
        return ""
    digits = []
    for byte in raw:
        digits.append(f"{(byte >> 4) & 0x0F}")
        digits.append(f"{byte & 0x0F}")
    return "".join(digits)


def _bcd_date_to_iso(value: str) -> str | None:
    if len(value) != 8 or not value.isdigit():
        return None
    year = value[:4]
    month = value[4:6]
    day = value[6:8]
    return f"{year}-{month}-{day}"


def _parse_activity_segment(segment: bytes) -> ActivityDay | None:
    reader = ByteReader(segment)
    reader.read_u8()
    reader.read_u8()

    date_raw: int | None = None
    odometer_midnight: int | None = None
    changes: tuple = ()
    card_iw_records: list[VuCardIWRecord] = []

    while reader.remaining() >= 5:
        record_type = reader.read_u8()
        record_size = reader.read_u16_be()
        record_count = reader.read_u16_be()
        total = record_size * record_count
        if reader.remaining() < total:
            break
        record_data = reader.read_bytes(total)

        if record_count == 0:
            continue

        if record_type == 0x06:
            date_raw = int.from_bytes(record_data[:4], "big")
        elif record_type == 0x05:
            if record_size >= 3:
                odometer_midnight = int.from_bytes(record_data[:3], "big")
        elif record_type == 0x01:
            changes = parse_activity_change_infos(record_data)
        elif record_type == 0x0D:
            offset = 0
            for _ in range(record_count):
                chunk = record_data[offset:offset + record_size]
                if len(chunk) < record_size:
                    break
                card_iw_records.append(parse_vu_card_iw_record(chunk))
                offset += record_size

    if date_raw is None or not changes:
        return None

    segments = build_activity_segments(date_raw, changes)
    return ActivityDay(
        date_raw=date_raw,
        date_iso=time_real_to_iso(date_raw),
        odometer_midnight=odometer_midnight,
        changes=changes,
        segments=segments,
        card_iw_records=tuple(card_iw_records),
    )


def _slice_segment(
    data: bytes, offsets: list[tuple[int, int]], index: int
) -> bytes:
    start = offsets[index][0]
    end = offsets[index + 1][0] if index + 1 < len(offsets) else len(data)
    return data[start:end]


def _iter_trep_offsets(data: bytes) -> tuple[tuple[int, int], ...]:
    offsets: list[tuple[int, int]] = []
    for index in range(len(data) - 1):
        if data[index] != TRANSFER_DATA_POSITIVE_RESPONSE_SID:
            continue
        trep = data[index + 1]
        if trep in _TREP_DATA_TYPES:
            offsets.append((index, trep))
    return tuple(offsets)


def _looks_like_identification(
    manufacturer_name: str,
    manufacturer_address: str,
    part_number: str,
    approval_number: str,
) -> bool:
    if not _looks_like_text(manufacturer_name, min_alnum=6):
        return False
    if not _looks_like_text(manufacturer_address, min_alnum=8):
        return False
    if not _looks_like_text(part_number, min_alnum=4):
        return False
    if not _looks_like_text(approval_number, min_alnum=2, min_length=2):
        return False
    return True


def _looks_like_text(
    text: str,
    min_alnum: int,
    min_length: int = 4,
    min_printable_ratio: float = 0.9,
) -> bool:
    stripped = text.strip()
    if len(stripped) < min_length:
        return False
    printable = sum(1 for ch in stripped if ch.isprintable())
    if printable / len(stripped) < min_printable_ratio:
        return False
    if sum(1 for ch in stripped if ch.isalnum()) < min_alnum:
        return False
    if not stripped[0].isalnum():
        return False
    return True


def _hex_bytes(data: bytes) -> str:
    return data.hex(" ")
