"""Declarative, versioned policy-evaluation contracts for built-in skillpacks.

The loader validates suite ownership and case shape only. It deliberately does
not claim to execute or score LLM behaviour; execution evidence belongs in the
agent evaluation runtime and its durable result store.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

__all__ = [
    "SkillEvalCase",
    "SkillEvalContractError",
    "SkillEvalExpected",
    "SkillEvalSuite",
    "load_skill_eval_suite",
]

EVAL_API_VERSION = "cosa.ai/skill-eval/v1"
EVAL_KIND = "SkillEvalSuite"


class SkillEvalContractError(ValueError):
    """Raised when an evaluation suite is malformed or unsupported."""


@dataclass(frozen=True)
class SkillEvalExpected:
    outcome: Literal["accept", "reject"]
    reason: str | None = None


@dataclass(frozen=True)
class SkillEvalCase:
    id: str
    input: dict[str, Any]
    expected: SkillEvalExpected


@dataclass(frozen=True)
class SkillEvalSuite:
    skill_id: str
    skill_version: str
    cases: tuple[SkillEvalCase, ...]


def _require_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SkillEvalContractError(f"{label} must be a mapping")
    return value


def _require_non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SkillEvalContractError(f"{label} must be a non-empty string")
    return value


def load_skill_eval_suite(path: Path) -> SkillEvalSuite:
    """Load one policy-evaluation YAML suite and reject any ambiguous shape."""
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SkillEvalContractError(f"Cannot read evaluation suite {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise SkillEvalContractError(f"Cannot parse evaluation suite {path}: {exc}") from exc

    root = _require_mapping(document, "Evaluation suite")
    if root.get("apiVersion") != EVAL_API_VERSION:
        raise SkillEvalContractError(
            f"Unsupported apiVersion {root.get('apiVersion')!r}; expected {EVAL_API_VERSION}"
        )
    if root.get("kind") != EVAL_KIND:
        raise SkillEvalContractError(f"Unsupported kind {root.get('kind')!r}; expected {EVAL_KIND}")

    skill = _require_mapping(root.get("skill"), "skill")
    skill_id = _require_non_empty_string(skill.get("id"), "skill.id")
    skill_version = _require_non_empty_string(skill.get("version"), "skill.version")

    raw_cases = root.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise SkillEvalContractError("cases must be a non-empty list")

    case_ids: set[str] = set()
    cases: list[SkillEvalCase] = []
    for index, raw_case in enumerate(raw_cases):
        case = _require_mapping(raw_case, f"cases[{index}]")
        case_id = _require_non_empty_string(case.get("id"), f"cases[{index}].id")
        if case_id in case_ids:
            raise SkillEvalContractError(f"duplicate case id: {case_id}")
        case_ids.add(case_id)

        input_payload = _require_mapping(case.get("input"), f"cases[{index}].input")
        expected = _require_mapping(case.get("expected"), f"cases[{index}].expected")
        outcome = expected.get("outcome")
        if outcome not in {"accept", "reject"}:
            raise SkillEvalContractError(
                f"cases[{index}].expected.outcome must be accept or reject"
            )
        reason = expected.get("reason")
        if reason is not None and (not isinstance(reason, str) or not reason.strip()):
            raise SkillEvalContractError(f"cases[{index}].expected.reason must be a string")

        cases.append(
            SkillEvalCase(
                id=case_id,
                input=input_payload,
                expected=SkillEvalExpected(outcome=outcome, reason=reason),
            )
        )

    return SkillEvalSuite(
        skill_id=skill_id,
        skill_version=skill_version,
        cases=tuple(cases),
    )
