from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ProcessStage:
    id: str
    name: str
    kind: str  # "value_add" | "wait" | "rework"
    duration_minutes: float
    p50_minutes: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in {"value_add", "wait", "rework"}:
            raise ValueError(
                f"Loại công đoạn không hợp lệ: '{self.kind}'. Chỉ chấp nhận: value_add, wait, rework"
            )
        if self.duration_minutes < 0:
            raise ValueError("duration_minutes không được âm")


@dataclass(frozen=True)
class BottleneckFinding:
    stage_id: str
    stage_name: str
    rule_code: str  # "R1_STAGE_P50" | "R2_WAIT_SHARE" | "R3_REWORK_SHARE"
    severity: str  # "high" | "medium" | "low"
    description: str
    recommendation: str


@dataclass(frozen=True)
class ProcessCycleReport:
    total_cycle_minutes: float
    value_add_minutes: float
    wait_minutes: float
    rework_minutes: float
    value_add_share: float
    wait_share: float
    rework_share: float
    bottlenecks: tuple[BottleneckFinding, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cycle_minutes": round(self.total_cycle_minutes, 2),
            "value_add_minutes": round(self.value_add_minutes, 2),
            "wait_minutes": round(self.wait_minutes, 2),
            "rework_minutes": round(self.rework_minutes, 2),
            "value_add_share": round(self.value_add_share, 4),
            "wait_share": round(self.wait_share, 4),
            "rework_share": round(self.rework_share, 4),
            "bottlenecks": [asdict(b) for b in self.bottlenecks],
        }


# Hiệu chỉnh ngưỡng theo profile ngành (SaaS, Dịch vụ, Sản xuất)
INDUSTRY_PROFILES: dict[str, dict[str, float]] = {
    "saas": {
        "stage_multiplier": 2.0,
        "wait_share_max": 0.40,
        "rework_share_max": 0.15,
    },
    "services": {
        "stage_multiplier": 2.5,
        "wait_share_max": 0.50,
        "rework_share_max": 0.15,
    },
    "manufacturing": {
        "stage_multiplier": 1.8,
        "wait_share_max": 0.30,
        "rework_share_max": 0.10,
    },
}


class ProcessCycleAnalyzer:
    """Bộ phân tích chu kỳ dòng chảy công việc và nhận diện điểm nghẽn (Theory of Constraints / Lean).
    100% Python stdlib, tất định.
    """

    @classmethod
    def analyze(
        cls,
        stages: list[ProcessStage],
        profile: str = "saas",
    ) -> ProcessCycleReport:
        if not stages:
            return ProcessCycleReport(
                total_cycle_minutes=0.0,
                value_add_minutes=0.0,
                wait_minutes=0.0,
                rework_minutes=0.0,
                value_add_share=0.0,
                wait_share=0.0,
                rework_share=0.0,
                bottlenecks=(),
            )

        thresholds = INDUSTRY_PROFILES.get(profile, INDUSTRY_PROFILES["saas"])

        value_add_minutes = sum(s.duration_minutes for s in stages if s.kind == "value_add")
        wait_minutes = sum(s.duration_minutes for s in stages if s.kind == "wait")
        rework_minutes = sum(s.duration_minutes for s in stages if s.kind == "rework")
        total_minutes = value_add_minutes + wait_minutes + rework_minutes

        if total_minutes <= 0:
            return ProcessCycleReport(
                total_cycle_minutes=0.0,
                value_add_minutes=0.0,
                wait_minutes=0.0,
                rework_minutes=0.0,
                value_add_share=0.0,
                wait_share=0.0,
                rework_share=0.0,
                bottlenecks=(),
            )

        value_add_share = value_add_minutes / total_minutes
        wait_share = wait_minutes / total_minutes
        rework_share = rework_minutes / total_minutes

        value_add_stages = [s for s in stages if s.kind == "value_add"]
        mean_value_add = (
            statistics.mean(s.duration_minutes for s in value_add_stages)
            if value_add_stages
            else 0.0
        )

        bottlenecks: list[BottleneckFinding] = []

        # R1: Stage P50 hoặc duration > stage_multiplier * mean(value_add stages)
        stage_mult = thresholds["stage_multiplier"]
        for s in stages:
            effective_duration = max(s.duration_minutes, s.p50_minutes)
            if mean_value_add > 0 and effective_duration > stage_mult * mean_value_add:
                bottlenecks.append(
                    BottleneckFinding(
                        stage_id=s.id,
                        stage_name=s.name,
                        rule_code="R1_STAGE_P50",
                        severity="high",
                        description=(
                            f"Thời gian công đoạn ({effective_duration:.1f}m) vượt quá {stage_mult}x "
                            f"trung bình các công đoạn sinh giá trị ({mean_value_add:.1f}m)"
                        ),
                        recommendation=(
                            f"Áp dụng Theory of Constraints: Tách nhỏ công đoạn '{s.name}' hoặc "
                            "tự động hóa để giải phóng năng lực thông lượng (throughput)."
                        ),
                    )
                )

        # R2: Wait share > wait_share_max (Handoff bottleneck)
        max_wait = thresholds["wait_share_max"]
        if wait_share > max_wait:
            top_wait_stage = max(
                (s for s in stages if s.kind == "wait"),
                key=lambda s: s.duration_minutes,
                default=None,
            )
            stage_id = top_wait_stage.id if top_wait_stage else "global_wait"
            stage_name = top_wait_stage.name if top_wait_stage else "Các bước chờ / chuyển giao"
            bottlenecks.append(
                BottleneckFinding(
                    stage_id=stage_id,
                    stage_name=stage_name,
                    rule_code="R2_WAIT_SHARE",
                    severity="high" if wait_share > max_wait * 1.25 else "medium",
                    description=(
                        f"Tỷ lệ thời gian chờ ({wait_share * 100:.1f}%) vượt ngưỡng an toàn "
                        f"({max_wait * 100:.1f}%) của ngành {profile}."
                    ),
                    recommendation=(
                        "Rà soát hàng đợi và cơ chế bàn giao giữa các phòng ban. "
                        "Thiết lập SLA phản hồi tối đa cho khâu chờ duyệt."
                    ),
                )
            )

        # R3: Rework share > rework_share_max (Quality bottleneck)
        max_rework = thresholds["rework_share_max"]
        if rework_share > max_rework:
            top_rework_stage = max(
                (s for s in stages if s.kind == "rework"),
                key=lambda s: s.duration_minutes,
                default=None,
            )
            stage_id = top_rework_stage.id if top_rework_stage else "global_rework"
            stage_name = top_rework_stage.name if top_rework_stage else "Các bước làm lại / sửa lỗi"
            bottlenecks.append(
                BottleneckFinding(
                    stage_id=stage_id,
                    stage_name=stage_name,
                    rule_code="R3_REWORK_SHARE",
                    severity="high" if rework_share > max_rework * 1.5 else "medium",
                    description=(
                        f"Tỷ lệ thời gian làm lại ({rework_share * 100:.1f}%) vượt trần "
                        f"({max_rework * 100:.1f}%) của ngành {profile}."
                    ),
                    recommendation=(
                        "Thiết lập tiêu chuẩn nghiệm thu rõ ràng (Definition of Done) và chốt kiểm "
                        "chất lượng tự động trước khi chuyển giao công đoạn."
                    ),
                )
            )

        return ProcessCycleReport(
            total_cycle_minutes=total_minutes,
            value_add_minutes=value_add_minutes,
            wait_minutes=wait_minutes,
            rework_minutes=rework_minutes,
            value_add_share=value_add_share,
            wait_share=wait_share,
            rework_share=rework_share,
            bottlenecks=tuple(bottlenecks),
        )
