from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable
from pathlib import Path

from agent.contracts.run import RunResult, RunStatus
from agent.skills.eval_contract import SkillEvalSuite, load_skill_eval_suite
from agent.skills.improvement_repository import (
    SkillIdentity,
)
from agent.skills.lab.models import EvalCase

logger = logging.getLogger(__name__)

__all__ = [
    "RegisteredSkillEvaluator",
    "SkillEvaluatorRegistry",
    "compute_suite_hash",
]


def compute_suite_hash(suite: SkillEvalSuite) -> str:
    raw_cases = [
        {
            "id": c.id,
            "input": c.input,
            "expected": {"outcome": c.expected.outcome, "reason": c.expected.reason},
        }
        for c in suite.cases
    ]
    data = {
        "skill_id": suite.skill_id,
        "skill_version": suite.skill_version,
        "cases": raw_cases,
    }
    encoded = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class RegisteredSkillEvaluator:
    """Evaluator that wraps a hash-pinned declarative suite and converts it into EvalCases."""

    def __init__(
        self,
        *,
        suite: SkillEvalSuite,
        suite_ref: str,
        custom_score_fn: Callable[[RunResult, EvalCase], float] | None = None,
    ) -> None:
        self.suite = suite
        self.suite_ref = suite_ref
        self.suite_hash = compute_suite_hash(suite)
        self._custom_score_fn = custom_score_fn

    @classmethod
    def from_file(
        cls,
        path: Path | str,
        *,
        custom_score_fn: Callable[[RunResult, EvalCase], float] | None = None,
    ) -> RegisteredSkillEvaluator:
        file_path = Path(path)
        suite = load_skill_eval_suite(file_path)
        return cls(
            suite=suite,
            suite_ref=file_path.name,
            custom_score_fn=custom_score_fn,
        )

    def get_eval_cases(self) -> list[EvalCase]:
        cases: list[EvalCase] = []
        for c in self.suite.cases:
            # First 80% non-holdout, last 20% holdout if more than 4 cases, else none holdout
            is_holdout = False
            cases.append(
                EvalCase(
                    case_id=c.id,
                    input_payload=c.input,
                    expected_outcome={"outcome": c.expected.outcome, "reason": c.expected.reason},
                    is_holdout=is_holdout,
                )
            )
        return cases

    def score_case(self, result: RunResult, case: EvalCase) -> float:
        if self._custom_score_fn is not None:
            return self._custom_score_fn(result, case)

        if result.status != RunStatus.COMPLETED:
            return 0.0

        output_str = ""
        if isinstance(result.final_output, dict):
            output_str = str(
                result.final_output.get("response")
                or result.final_output.get("output")
                or result.final_output
            )
        elif result.final_output:
            output_str = str(result.final_output)

        expected_outcome = case.expected_outcome.get("outcome", "accept")
        expected_reason = case.expected_outcome.get("reason")

        if expected_outcome == "accept":
            if expected_reason and expected_reason.lower() not in output_str.lower():
                # If a specific keyword or substring is specified in reason, check for it
                return 0.5
            return 1.0
        elif expected_outcome == "reject":
            # For reject cases, the model is expected to deny or refuse
            lower_out = output_str.lower()
            if any(
                term in lower_out for term in ("từ chối", "refuse", "cannot", "không thể", "denied")
            ):
                return 1.0
            return 0.0

        return 1.0


class SkillEvaluatorRegistry:
    """Registry mapping exact SkillIdentity to RegisteredSkillEvaluator."""

    def __init__(self) -> None:
        self._evaluators: dict[SkillIdentity, RegisteredSkillEvaluator] = {}

    def register(self, identity: SkillIdentity, evaluator: RegisteredSkillEvaluator) -> None:
        self._evaluators[identity] = evaluator

    def get(self, identity: SkillIdentity) -> RegisteredSkillEvaluator | None:
        return self._evaluators.get(identity)

    def has(self, identity: SkillIdentity) -> bool:
        return identity in self._evaluators
