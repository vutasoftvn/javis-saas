"""Kiểm tra tiêu chí hoàn thành của task WGA (Dự án B): logic thuần, không I/O."""

from agent.verification.combine import combine
from agent.verification.deterministic import evaluate_deterministic
from agent.verification.judge import JudgeOutputError, build_judge_prompt, parse_judge_output
from agent.verification.models import (
    ArtifactFact,
    CriterionResult,
    CriterionVerdict,
    RunFacts,
    Verdict,
)

__all__ = [
    "ArtifactFact",
    "CriterionResult",
    "CriterionVerdict",
    "JudgeOutputError",
    "RunFacts",
    "Verdict",
    "build_judge_prompt",
    "combine",
    "evaluate_deterministic",
    "parse_judge_output",
]
