"""LeafId — UUIDv7 cho entity cardinality cao do runtime sinh (M2 §3, ADR-ID-MODEL-001).

UUIDv7 (RFC 9562): 48-bit Unix ms timestamp | version=7 | 12-bit rand_a |
variant=0b10 | 62-bit rand_b. Time-ordered ⇒ so sánh chuỗi canonical giữ đúng
thứ tự thời gian; prefix + truncate hex vẫn giữ tính đơn điệu vì timestamp nằm
ở 48 bit đầu.

Python 3.11 chưa có `uuid.uuid7()` (thêm ở 3.14) và repo chưa cài `uuid6` lib,
nên tự cài đặt tối thiểu ở đây. KHÔNG dùng cho SpineId (workspace/project/…):
những entity đó là Snowflake do control-plane mint.
"""

from __future__ import annotations

import os
import time
import uuid

__all__ = ["is_uuidv7", "uuid7", "uuid7_str"]


def uuid7() -> uuid.UUID:
    """Sinh một UUIDv7 mới."""
    unix_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand = int.from_bytes(os.urandom(10), "big")  # 80 bit ngẫu nhiên
    rand_a = (rand >> 64) & 0x0FFF  # 12 bit
    rand_b = rand & ((1 << 62) - 1)  # 62 bit

    value = unix_ms << 80
    value |= 0x7 << 76  # version = 7
    value |= rand_a << 64
    value |= 0b10 << 62  # variant = RFC 4122
    value |= rand_b
    return uuid.UUID(int=value)


def uuid7_str() -> str:
    """UUIDv7 dạng chuỗi canonical (dùng làm `default_factory` cho field `str`)."""
    return str(uuid7())


def is_uuidv7(value: str | uuid.UUID) -> bool:
    """True nếu `value` là UUIDv7 hợp lệ (version nibble 7, variant 10xx)."""
    try:
        u = value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except (ValueError, AttributeError):
        return False
    return u.version == 7 and (u.int >> 62) & 0b11 == 0b10
