# backend/agentos/evals/skill_eval.py
from __future__ import annotations

from pydantic import BaseModel

from agentos.skills.manifest import SkillManifest

DEFAULT_SAMPLE_WEIGHT = 0.2


class SkillEvalResult(BaseModel):
    skill_id: str
    success: bool
    latency_seconds: float
    updated_eval_score: float
    updated_success_rate: float


def evaluate_skill_run(
    manifest: SkillManifest,
    *,
    success: bool,
    latency_seconds: float,
    sample_weight: float = DEFAULT_SAMPLE_WEIGHT,
) -> SkillEvalResult:
    """Skill Eval (blueprint §51/§32): cập nhật `SkillManifest.quality`
    (`eval_score`, `success_rate`) qua exponential moving average từ kết
    quả 1 lần chạy skill thật — không phải LLM judge, chỉ dựa trên outcome
    quan sát được (thành công hay không, latency). Đóng vòng lặp mà
    `SkillRouter.score_skill()` (`agentos/skills/router.py`) đã đọc
    `manifest.quality.eval_score` từ trước nhưng chưa từng có gì ghi vào đó.

    Trả về `SkillEvalResult` thuần túy (không mutate `manifest` hay đụng
    `SkillRegistry`) — theo đúng convention của agent_eval.py/workflow_eval.py:
    eval là pure computation, caller tự quyết định persist bằng cách nào
    (vd. `SkillRegistry` record hiện tại là `@dataclass` có thể gán lại
    `record.manifest.quality`).

    Các dimension khác của §51 (accuracy, tool correctness, policy
    compliance, security, human_acceptance) cần instrumentation chưa có ở
    phase này (không có SkillRun record riêng biệt với AgentRun) — deliberately
    out of scope, giống cách agent_eval.py/workflow_eval.py đã tự giới hạn.
    """
    if not (0.0 < sample_weight <= 1.0):
        raise ValueError("sample_weight must be in (0.0, 1.0]")

    outcome = 1.0 if success else 0.0
    updated_eval_score = manifest.quality.eval_score * (1 - sample_weight) + outcome * sample_weight
    updated_success_rate = manifest.quality.success_rate * (1 - sample_weight) + outcome * sample_weight
    return SkillEvalResult(
        skill_id=manifest.metadata.id,
        success=success,
        latency_seconds=latency_seconds,
        updated_eval_score=updated_eval_score,
        updated_success_rate=updated_success_rate,
    )
