"""Nhãn hiển thị cho lifecycle stage (P0..P6). Mã `P0_DISCOVERY` là KEY nội bộ — không đưa
thẳng cho người dùng. Bảng này phải khớp `displayNameVi/En` ở frontend
(`frontend/lib/data/models/stage_model.dart`)."""

from __future__ import annotations

__all__ = ["lifecycle_stage_label"]

_LABELS: dict[str, dict[str, str]] = {
    "P0_DISCOVERY": {
        "vi": "P0 - Khám phá & Đánh giá cơ hội",
        "en": "P0 - Discovery & Opportunity Evaluation",
    },
    "P1_PROBLEM_VALIDATION": {
        "vi": "P1 - Xác thực vấn đề",
        "en": "P1 - Problem Validation",
    },
    "P2_SOLUTION_VALIDATION": {
        "vi": "P2 - Xác thực giải pháp",
        "en": "P2 - Solution Validation",
    },
    "P3_BUILD_VALIDATE": {
        "vi": "P3 - Xây dựng & Thử nghiệm",
        "en": "P3 - Build & Validate",
    },
    "P4_GO_TO_MARKET": {
        "vi": "P4 - Đưa ra thị trường",
        "en": "P4 - Go-to-Market",
    },
    "P5_OPERATE_GROWTH": {
        "vi": "P5 - Vận hành & Tăng trưởng",
        "en": "P5 - Operate & Grow",
    },
    "P6_SCALE_GOVERN": {
        "vi": "P6 - Mở rộng & Quản trị",
        "en": "P6 - Scale & Govern",
    },
}


def lifecycle_stage_label(stage: object, locale: str | None = None) -> str | None:
    """Nhãn theo ngôn ngữ (`vi` mặc định); None nếu không nhận ra mã."""
    entry = _LABELS.get(str(stage or "").strip().upper())
    if entry is None:
        return None
    lang = "en" if (locale or "").lower().startswith("en") else "vi"
    return entry[lang]
