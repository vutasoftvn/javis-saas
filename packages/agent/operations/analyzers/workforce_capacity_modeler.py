from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CapacityPlan:
    arrival_rate_per_hour: float
    handle_time_minutes: float
    target_wait_seconds: float
    target_service_level: float
    traffic_intensity_erlangs: float
    recommended_headcount: int
    expected_service_level: float
    waiting_probability: float  # Erlang-C P(W>0)
    utilization_rate: float
    burnout_warning: bool
    burnout_threshold: float = 0.85

    def to_dict(self) -> dict[str, Any]:
        return {
            "arrival_rate_per_hour": round(self.arrival_rate_per_hour, 1),
            "handle_time_minutes": round(self.handle_time_minutes, 1),
            "target_wait_seconds": self.target_wait_seconds,
            "target_service_level": round(self.target_service_level, 4),
            "traffic_intensity_erlangs": round(self.traffic_intensity_erlangs, 2),
            "recommended_headcount": self.recommended_headcount,
            "expected_service_level": round(self.expected_service_level, 4),
            "waiting_probability": round(self.waiting_probability, 4),
            "utilization_rate": round(self.utilization_rate, 4),
            "burnout_warning": self.burnout_warning,
        }


@dataclass(frozen=True)
class HiringMilestone:
    week_no: int
    projected_demand_rate_per_hour: float
    required_headcount: int
    active_headcount: int
    headcount_deficit: int
    recommended_hire_order_week: int  # Tuần cần ra quyết định tuyển dụng (tính cả ramp-up)
    notes: str


class WorkforceCapacityModeler:
    """Bộ mô hình hóa định biên năng lực đội ngũ vận hành / CS dựa trên toán hàng đợi Erlang-C.
    100% Python stdlib tất định.
    """

    @classmethod
    def _erlang_c_raw(cls, A: float, N: int) -> float:
        """Tính P(W>0) bằng Erlang-C."""
        if N <= A:
            return 1.0

        # Tính tổng sum(A^k / k!) cho k = 0 .. N-1
        sum_terms = 0.0
        term = 1.0
        for k in range(N):
            sum_terms += term
            term *= A / (k + 1)

        # term lúc này là A^N / N!
        numerator = term * (N / (N - A))
        denominator = sum_terms + numerator

        if denominator <= 0:
            return 1.0
        return min(1.0, max(0.0, numerator / denominator))

    @classmethod
    def calculate_erlang_c(
        cls,
        arrival_rate_per_hour: float,
        handle_time_minutes: float,
        target_wait_seconds: float = 120.0,
        target_service_level: float = 0.80,
        max_agents_search: int = 500,
    ) -> CapacityPlan:
        if arrival_rate_per_hour <= 0 or handle_time_minutes <= 0:
            return CapacityPlan(
                arrival_rate_per_hour=arrival_rate_per_hour,
                handle_time_minutes=handle_time_minutes,
                target_wait_seconds=target_wait_seconds,
                target_service_level=target_service_level,
                traffic_intensity_erlangs=0.0,
                recommended_headcount=0,
                expected_service_level=1.0,
                waiting_probability=0.0,
                utilization_rate=0.0,
                burnout_warning=False,
            )

        # Cường độ lưu lượng A (Erlangs) = lambda (cuộc/phút) * tm (phút)
        arrival_rate_per_minute = arrival_rate_per_hour / 60.0
        A = arrival_rate_per_minute * handle_time_minutes

        min_agents = max(1, math.floor(A) + 1)
        target_wait_minutes = target_wait_seconds / 60.0

        chosen_n = min_agents
        best_sl = 0.0
        best_pw = 1.0

        for n in range(min_agents, max_agents_search):
            pw = cls._erlang_c_raw(A, n)
            # Service level = 1 - P(W>0) * exp(-(N - A) * (T / tm))
            decay = math.exp(-(n - A) * (target_wait_minutes / handle_time_minutes))
            sl = 1.0 - (pw * decay)
            chosen_n = n
            best_sl = sl
            best_pw = pw
            if sl >= target_service_level:
                break

        utilization = A / chosen_n if chosen_n > 0 else 0.0
        burnout = utilization > 0.85

        return CapacityPlan(
            arrival_rate_per_hour=arrival_rate_per_hour,
            handle_time_minutes=handle_time_minutes,
            target_wait_seconds=target_wait_seconds,
            target_service_level=target_service_level,
            traffic_intensity_erlangs=A,
            recommended_headcount=chosen_n,
            expected_service_level=best_sl,
            waiting_probability=best_pw,
            utilization_rate=utilization,
            burnout_warning=burnout,
        )

    @classmethod
    def plan_12wy_hiring(
        cls,
        weekly_arrival_hourly_peak: list[float],
        current_headcount: int,
        handle_time_minutes: float,
        target_wait_seconds: float = 120.0,
        target_service_level: float = 0.80,
        ramp_weeks: int = 4,
    ) -> list[HiringMilestone]:
        """Lập kế hoạch lộ trình nhân sự theo 12 tuần của 12WY."""
        milestones: list[HiringMilestone] = []

        for week_idx, peak_rate in enumerate(weekly_arrival_hourly_peak, start=1):
            plan = cls.calculate_erlang_c(
                arrival_rate_per_hour=peak_rate,
                handle_time_minutes=handle_time_minutes,
                target_wait_seconds=target_wait_seconds,
                target_service_level=target_service_level,
            )
            required = plan.recommended_headcount
            deficit = max(0, required - current_headcount)
            hire_order_week = max(1, week_idx - ramp_weeks)

            if deficit > 0:
                notes = (
                    f"Thiếu {deficit} nhân sự ở tuần W{week_idx}. "
                    f"Cần duyệt tuyển dụng tại tuần W{hire_order_week} để kịp ramp-up {ramp_weeks} tuần."
                )
            else:
                notes = (
                    f"Đội ngũ hiện tại ({current_headcount} người) đủ đáp ứng SLA (cần {required})."
                )

            milestones.append(
                HiringMilestone(
                    week_no=week_idx,
                    projected_demand_rate_per_hour=peak_rate,
                    required_headcount=required,
                    active_headcount=current_headcount,
                    headcount_deficit=deficit,
                    recommended_hire_order_week=hire_order_week,
                    notes=notes,
                )
            )

        return milestones
