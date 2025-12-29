from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ByteReader:
    data: bytes
    offset: int = 0

    def remaining(self) -> int:
        return len(self.data) - self.offset

    def tell(self) -> int:
        return self.offset

    def seek(self, offset: int) -> None:
        if offset < 0 or offset > len(self.data):
            raise ValueError("Offset out of range.")
        self.offset = offset

    def skip(self, count: int) -> None:
        self.seek(self.offset + count)

    def read_bytes(self, count: int) -> bytes:
        if count < 0:
            raise ValueError("Count must be non-negative.")
        end = self.offset + count
        if end > len(self.data):
            raise ValueError("Not enough bytes to read.")
        chunk = self.data[self.offset:end]
        self.offset = end
        return chunk

    def peek_bytes(self, count: int) -> bytes:
        if count < 0:
            raise ValueError("Count must be non-negative.")
        end = self.offset + count
        if end > len(self.data):
            raise ValueError("Not enough bytes to peek.")
        return self.data[self.offset:end]

    def read_u8(self) -> int:
        return self._read_int(1, "big")

    def read_u16_be(self) -> int:
        return self._read_int(2, "big")

    def read_u16_le(self) -> int:
        return self._read_int(2, "little")

    def read_u32_be(self) -> int:
        return self._read_int(4, "big")

    def read_u32_le(self) -> int:
        return self._read_int(4, "little")

    def read_u24_be(self) -> int:
        return self._read_int(3, "big")

    def read_fixed_str(self, length: int, encoding: str = "latin-1") -> str:
        raw = self.read_bytes(length)
        return raw.rstrip(b"\x00").decode(encoding, errors="replace").strip()

    def read_bcd(self, length: int) -> str:
        raw = self.read_bytes(length)
        digits = []
        for byte in raw:
            high = (byte >> 4) & 0x0F
            low = byte & 0x0F
            digits.append(_bcd_digit(high))
            digits.append(_bcd_digit(low))
        return "".join(digits)

    def read_time_real_raw(self) -> int:
        # TimeReal is defined in the spec; keep this as raw 32-bit value for now.
        return self.read_u32_be()

    def _read_int(self, length: int, endian: str) -> int:
        return int.from_bytes(self.read_bytes(length), endian)


def _bcd_digit(value: int) -> str:
    if 0 <= value <= 9:
        return str(value)
    return "?"


def bits_from_byte(value: int) -> tuple[int, ...]:
    return tuple((value >> bit) & 1 for bit in range(8))
