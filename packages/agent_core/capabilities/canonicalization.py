from __future__ import annotations

import hashlib
import json
from typing import Any

__all__ = ["canonicalize_payload", "compute_payload_hash"]


def _normalize_item(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(k): _normalize_item(v)
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_item(v) for v in value]
    if isinstance(value, set):
        return sorted([_normalize_item(v) for v in value], key=str)
    if isinstance(value, float):
        # Định dạng float nhất quán
        return round(value, 8)
    return value


def canonicalize_payload(payload: Any) -> str:
    """Chuẩn hoá dữ liệu structured payload: sort keys đệ quy, chuẩn hoá kiểu dữ liệu, loại bỏ khoảng trắng thừa."""
    normalized = _normalize_item(payload)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_payload_hash(payload: Any) -> str:
    """Tạo SHA-256 hash từ payload đã canonicalize theo Master Guide §17.2."""
    canonical_json = canonicalize_payload(payload)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
