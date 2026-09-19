from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from agent.workflows.schema import LoopTerminalState, StepType, WorkflowSpec

ALL_TERMINAL_STATES = {
    LoopTerminalState.SUCCESS,
    LoopTerminalState.NOOP,
    LoopTerminalState.BLOCKED,
    LoopTerminalState.NEED_APPROVAL,
    LoopTerminalState.EXHAUSTED,
    LoopTerminalState.STAGNATED,
}

SELF_WAKEUP_PATTERNS = [
    r"tự\s+(?:gọi|đánh thức|chạy)(?:\s+lại)?\s+chính\s+mình",
    r"sau\s+\d+\s+phút",
    r"chạy\s+(?:tiếp\s+)?mãi\s+mãi",
    r"call\s+(?:yourself|again)(?:\s+after)?",
    r"sleep\s+\d+",
    r"repeat\s+forever",
    r"while\s+true",
]


@dataclass(frozen=True)
class LoopDoctorReport:
    workflow_id: str
    has_bounded_feedback: bool
    terminal_states_declared: tuple[str, ...]
    missing_terminal_states: tuple[str, ...]
    has_independent_verifier: bool
    anti_patterns_found: tuple[str, ...]
    verdict: str  # "CLEAN" | "WARNINGS" | "CRITICAL_RISK"
    recommendations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "has_bounded_feedback": self.has_bounded_feedback,
            "terminal_states_declared": list(self.terminal_states_declared),
            "missing_terminal_states": list(self.missing_terminal_states),
            "has_independent_verifier": self.has_independent_verifier,
            "anti_patterns_found": list(self.anti_patterns_found),
            "verdict": self.verdict,
            "recommendations": list(self.recommendations),
        }


class LoopDoctor:
    """Bộ công cụ chẩn đoán và kiểm toán an toàn vòng lặp tự hành theo chuẩn Loop Library."""

    @classmethod
    def audit_workflow_spec(cls, spec: WorkflowSpec) -> LoopDoctorReport:
        anti_patterns: list[str] = []
        recommendations: list[str] = []

        declared_terminals: set[LoopTerminalState] = set()
        has_verifier = False

        for step in spec.steps:
            if step.terminal_state:
                declared_terminals.add(step.terminal_state)

            # Check independent verifier
            if step.verifier_step_id:
                if step.verifier_step_id == step.id:
                    anti_patterns.append(
                        f"Bước '{step.id}' vi phạm Anti-pattern Self-Grading: "
                        f"verifier_step_id trỏ vào chính nó."
                    )
                else:
                    has_verifier = True

            # Check approval gates on high-risk side effects
            if (
                step.type == StepType.TOOL_CALL
                and step.autonomy_level == "L3_AUTONOMOUS"
                and not any(s.type == StepType.APPROVAL_GATE for s in spec.steps)
            ):
                anti_patterns.append(
                    f"Bước '{step.id}' có quyền tự trị L3_AUTONOMOUS nhưng thiếu approval gate trong workflow."
                )

        missing_terminals = [st.value for st in ALL_TERMINAL_STATES if st not in declared_terminals]

        if not has_verifier:
            recommendations.append(
                "Nên cấu hình ít nhất 1 bước thẩm định độc lập (verifier_step_id) tách biệt với bước thực thi."
            )

        if not declared_terminals:
            recommendations.append(
                "Nên khai báo các trạng thái kết thúc chuẩn (SUCCESS, NOOP, BLOCKED, EXHAUSTED) để engine xử lý tất định."
            )

        has_bounded_feedback = len(declared_terminals) > 0 or has_verifier

        if any("Self-Grading" in ap or "L3_AUTONOMOUS" in ap for ap in anti_patterns):
            verdict = "CRITICAL_RISK"
        elif anti_patterns or not has_bounded_feedback:
            verdict = "WARNINGS"
        else:
            verdict = "CLEAN"

        return LoopDoctorReport(
            workflow_id=spec.id,
            has_bounded_feedback=has_bounded_feedback,
            terminal_states_declared=tuple(st.value for st in declared_terminals),
            missing_terminal_states=tuple(missing_terminals),
            has_independent_verifier=has_verifier,
            anti_patterns_found=tuple(anti_patterns),
            verdict=verdict,
            recommendations=tuple(recommendations),
        )

    @classmethod
    def audit_prompt_text(cls, prompt: str) -> dict[str, Any]:
        """Kiểm toán nội dung prompt để phát hiện các anti-pattern tự đánh thức hoặc lặp vô hạn."""
        issues: list[str] = []
        for pattern in SELF_WAKEUP_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                issues.append(
                    f"Phát hiện anti-pattern tự đánh thức / lặp vô hạn khớp mẫu: '{pattern}'"
                )

        has_stop = bool(
            re.search(r"(dừng|stop|kết thúc|hoàn thành|when|until)", prompt, re.IGNORECASE)
        )
        if not has_stop:
            issues.append("Prompt không nêu rõ điều kiện dừng (Stopping condition / Finish line).")

        return {
            "is_safe": len(issues) == 0,
            "issues": issues,
            "recommendation": (
                "Áp dụng chuẩn Loop Library: 'Sau mỗi thay đổi, [chạy kiểm tra độc lập] "
                "và dừng khi [đạt mục tiêu hoặc không tiến triển]. Xin phép trước khi [thao tác rủi ro].'"
                if issues
                else "Prompt tuân thủ tốt nguyên tắc vòng lặp có biên giới hữu hạn."
            ),
        }
