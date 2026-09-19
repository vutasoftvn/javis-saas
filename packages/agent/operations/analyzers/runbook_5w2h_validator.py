from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

FORBIDDEN_OWNERS = {
    "",
    "team",
    "the team",
    "ops",
    "ops team",
    "dev",
    "devs",
    "ai",
    "agent",
    "tbd",
    "n/a",
    "none",
    "everyone",
    "chưa có",
    "đội ngũ",
}


@dataclass(frozen=True)
class RunbookStep:
    step_no: int
    title: str
    owner: str
    expected_duration_minutes: float
    success_signal: str
    failure_signal: str
    rollback: str
    escalation: str


@dataclass(frozen=True)
class StepValidationResult:
    step_no: int
    title: str
    is_valid: bool
    missing_attributes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunbookValidationReport:
    runbook_name: str
    total_steps: int
    valid_steps: int
    hygiene_score: float  # 0.0 to 100.0
    verdict: str  # "SAFE-TO-USE" | "USE-WITH-CAUTION" | "NOT-SAFE"
    must_fix_issues: tuple[str, ...] = ()
    step_results: tuple[StepValidationResult, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "runbook_name": self.runbook_name,
            "total_steps": self.total_steps,
            "valid_steps": self.valid_steps,
            "hygiene_score": round(self.hygiene_score, 1),
            "verdict": self.verdict,
            "must_fix_issues": list(self.must_fix_issues),
            "step_results": [r.to_dict() for r in self.step_results],
        }


class Runbook5W2HValidator:
    """Kiểm định vệ sinh và độ hoàn thiện của tài liệu SOP / Runbook theo chuẩn 5W2H.
    Đảm bảo không đưa runbook thiếu an toàn vào vận hành production.
    """

    @classmethod
    def validate_steps(
        cls,
        runbook_name: str,
        steps: list[RunbookStep],
    ) -> RunbookValidationReport:
        if not steps:
            return RunbookValidationReport(
                runbook_name=runbook_name,
                total_steps=0,
                valid_steps=0,
                hygiene_score=0.0,
                verdict="NOT-SAFE",
                must_fix_issues=("Runbook không có bước thực hiện nào.",),
                step_results=(),
            )

        step_results: list[StepValidationResult] = []
        must_fix_issues: list[str] = []
        total_checks = len(steps) * 6
        passed_checks = 0

        for s in steps:
            missing: list[str] = []
            warnings: list[str] = []

            # 1. Named owner
            clean_owner = s.owner.strip().lower()
            if not clean_owner or clean_owner in FORBIDDEN_OWNERS:
                missing.append("named_owner")
                must_fix_issues.append(
                    f"Bước {s.step_no} ('{s.title}'): Thiếu người chịu trách nhiệm được chỉ định cụ thể (hiện tại: '{s.owner}')."
                )
            else:
                passed_checks += 1

            # 2. Expected duration
            if s.expected_duration_minutes <= 0:
                missing.append("expected_duration")
                must_fix_issues.append(
                    f"Bước {s.step_no} ('{s.title}'): Thời lượng dự kiến phải là số dương (>0 phút)."
                )
            else:
                passed_checks += 1

            # 3. Observable success signal
            if not s.success_signal or len(s.success_signal.strip()) < 5:
                missing.append("observable_success_signal")
                must_fix_issues.append(
                    f"Bước {s.step_no} ('{s.title}'): Tín hiệu thành công quá mơ hồ hoặc để trống."
                )
            else:
                passed_checks += 1

            # 4. Observable failure signal
            if not s.failure_signal or len(s.failure_signal.strip()) < 5:
                missing.append("observable_failure_signal")
                must_fix_issues.append(
                    f"Bước {s.step_no} ('{s.title}'): Tín hiệu lỗi quá mơ hồ hoặc để trống."
                )
            else:
                passed_checks += 1

            # 5. Rollback path
            clean_rollback = s.rollback.strip().lower()
            if not clean_rollback or len(clean_rollback) < 3:
                missing.append("rollback_path")
                must_fix_issues.append(
                    f"Bước {s.step_no} ('{s.title}'): Thiếu quy trình hoàn tác (Rollback) hoặc chỉ định khẩn cấp."
                )
            else:
                passed_checks += 1

            # 6. Escalation contact
            clean_esc = s.escalation.strip()
            if not clean_esc or len(clean_esc) < 3 or clean_esc.lower() in FORBIDDEN_OWNERS:
                missing.append("escalation_contact")
                must_fix_issues.append(
                    f"Bước {s.step_no} ('{s.title}'): Thiếu đầu mối leo thang khi gặp sự cố."
                )
            else:
                passed_checks += 1

            step_is_valid = len(missing) == 0
            step_results.append(
                StepValidationResult(
                    step_no=s.step_no,
                    title=s.title,
                    is_valid=step_is_valid,
                    missing_attributes=tuple(missing),
                    warnings=tuple(warnings),
                )
            )

        score = (passed_checks / total_checks) * 100.0 if total_checks > 0 else 0.0

        if score >= 80.0 and len(must_fix_issues) <= len(steps):
            verdict = "SAFE-TO-USE"
        elif score >= 60.0:
            verdict = "USE-WITH-CAUTION"
        else:
            verdict = "NOT-SAFE"

        valid_count = sum(1 for r in step_results if r.is_valid)

        return RunbookValidationReport(
            runbook_name=runbook_name,
            total_steps=len(steps),
            valid_steps=valid_count,
            hygiene_score=round(score, 1),
            verdict=verdict,
            must_fix_issues=tuple(must_fix_issues),
            step_results=tuple(step_results),
        )

    @classmethod
    def validate_dict(cls, data: dict[str, Any]) -> RunbookValidationReport:
        runbook_name = data.get("runbook_name") or data.get("title") or "Unnamed Runbook"
        raw_steps = data.get("steps", [])
        steps: list[RunbookStep] = []
        for idx, item in enumerate(raw_steps, start=1):
            steps.append(
                RunbookStep(
                    step_no=int(item.get("step_no", idx)),
                    title=str(item.get("title", f"Bước {idx}")),
                    owner=str(item.get("owner", "")),
                    expected_duration_minutes=float(
                        item.get("duration_minutes", item.get("expected_duration_minutes", 0))
                    ),
                    success_signal=str(item.get("success_signal", "")),
                    failure_signal=str(item.get("failure_signal", "")),
                    rollback=str(item.get("rollback", "")),
                    escalation=str(item.get("escalation", "")),
                )
            )
        return cls.validate_steps(runbook_name, steps)
