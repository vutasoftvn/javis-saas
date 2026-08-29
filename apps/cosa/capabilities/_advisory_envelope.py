from __future__ import annotations

from typing import Any, Literal

__all__ = ["wrap_advisory"]

AdvisoryLayer = Literal["CURRENT_LAW", "POLICY_WATCH", "PROFESSIONAL_REVIEW"]
AdvisoryLabel = Literal["insight", "proposal", "requires_professional_review"]


def wrap_advisory(
    layer: AdvisoryLayer,
    label: AdvisoryLabel,
    content: str,
    sources: list[dict[str, Any]],
    assumptions: list[str] | None = None,
    alternatives: list[str] | None = None,
    confidence: float | None = None,
    next_actions: list[str] | None = None,
) -> dict[str, Any]:
    """Bọc kết quả tư vấn pháp lý / chiến lược theo chuẩn COSA 3-layer advisory:
    Layers:
      - CURRENT_LAW: Văn bản QPPL đang có hiệu lực.
      - POLICY_WATCH: Dự thảo, nghị quyết định hướng, chính sách sắp ban hành.
      - PROFESSIONAL_REVIEW: Trường hợp phức tạp, thiếu dữ kiện, bắt buộc chuyên gia duyệt.

    Labels:
      - insight: Thông tin phân tích, giải thích.
      - proposal: Kiến nghị giải pháp cụ thể.
      - requires_professional_review: Cảnh báo cần chuyên gia đánh giá.
    """
    valid_layers = ("CURRENT_LAW", "POLICY_WATCH", "PROFESSIONAL_REVIEW")
    valid_labels = ("insight", "proposal", "requires_professional_review")

    if layer not in valid_layers:
        raise ValueError(f"Invalid advisory layer: {layer}. Must be one of {valid_layers}")

    if label not in valid_labels:
        raise ValueError(f"Invalid advisory label: {label}. Must be one of {valid_labels}")

    return {
        "layer": layer,
        "label": label,
        "content": content,
        "sources": sources or [],
        "assumptions": assumptions or [],
        "alternatives": alternatives or [],
        "confidence": confidence if confidence is not None else 1.0,
        "next_actions": next_actions or [],
    }
