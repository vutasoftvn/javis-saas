"""Goal → Execution Plan decomposition (WGA).

Pure helpers: the fixed JSON schema the agent must emit, the prompt that asks
for it, and a strict parser that rejects malformed output. No I/O, no LLM call
here — the worker (`goal_decomposition_run.py`) runs the kernel and feeds the
raw text to `parse_plan_output`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

__all__ = [
    "PLAN_OUTPUT_JSON_SCHEMA",
    "PlanItemDraft",
    "PlanSchemaError",
    "build_decomposition_prompt",
    "parse_plan_output",
]

_VALID_PRIORITIES = {"low", "medium", "high", "urgent"}


class PlanSchemaError(ValueError):
    """Raised when the agent's plan output does not match the required schema."""


@dataclass
class PlanItemDraft:
    title: str
    decision_reason: str
    evidence_refs: list[str]
    suggested_domain: str | None
    expected_capability: str | None
    depends_on_titles: list[str] = field(default_factory=list)
    priority: str = "medium"


# Shape the agent is instructed to return. Kept small and reference-only.
PLAN_OUTPUT_JSON_SCHEMA: dict = {
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["title", "decision_reason", "evidence_refs"],
                "properties": {
                    "title": {"type": "string", "minLength": 1},
                    "decision_reason": {"type": "string", "minLength": 5},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    "suggested_domain": {"type": ["string", "null"]},
                    "expected_capability": {"type": ["string", "null"]},
                    "depends_on_titles": {"type": "array", "items": {"type": "string"}},
                    "priority": {"type": "string", "enum": sorted(_VALID_PRIORITIES)},
                },
            },
        }
    },
}


def build_decomposition_prompt(goal_text: str, context: dict) -> str:
    """Build the English prompt that asks the agent to decompose a weekly goal.

    `context` may carry: lifecycle_stage, next_best_actions (list[str]),
    existing_task_titles (list[str]).
    """
    stage = context.get("lifecycle_stage") or "unknown"
    nba = context.get("next_best_actions") or []
    existing = context.get("existing_task_titles") or []

    nba_block = "\n".join(f"- {x}" for x in nba) if nba else "- (none)"
    existing_block = "\n".join(f"- {x}" for x in existing) if existing else "- (none)"

    return (
        "You are decomposing a founder's WEEKLY GOAL into concrete work items for "
        "an AI workforce.\n\n"
        f"WEEKLY GOAL:\n{goal_text.strip()}\n\n"
        f"PROJECT LIFECYCLE STAGE: {stage}\n\n"
        f"DETERMINISTIC NEXT-BEST-ACTIONS (advisory):\n{nba_block}\n\n"
        f"TASKS THAT ALREADY EXIST (do not duplicate):\n{existing_block}\n\n"
        "Produce 2-7 items. Each item MUST have:\n"
        "- title: an imperative action phrase (starts with a verb)\n"
        "- decision_reason: >=5 chars, why this item serves the goal\n"
        "- evidence_refs: array of reference strings in this workspace (may be "
        "empty for items only a human can do)\n"
        "- suggested_domain: one of 'operations' | 'finance' | 'marketing', or null\n"
        "- expected_capability: the single capability id the AI would call to do "
        "this (e.g. 'operations.sop.draft'), or null if NO capability can do it "
        "(interviews, calls, meetings, strategic decisions -> null)\n"
        "- depends_on_titles: array of other item titles that must finish first\n"
        "- priority: 'low' | 'medium' | 'high' | 'urgent'\n\n"
        "If an item is purely human work (e.g. 'Interview 3 customers'), set both "
        "suggested_domain and expected_capability to null.\n\n"
        "Return ONLY a JSON object of the form "
        '{"items": [ ... ]} with no prose, no markdown fences.'
    )


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        # remove leading ```json / ``` and trailing ```
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def parse_plan_output(raw: str) -> list[PlanItemDraft]:
    """Parse + validate the agent's plan output. Raises PlanSchemaError on any
    structural problem (never returns a partial list)."""
    if not raw or not raw.strip():
        raise PlanSchemaError("empty plan output")

    try:
        data = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as exc:
        raise PlanSchemaError(f"invalid JSON: {exc}") from exc

    if not isinstance(data, dict) or "items" not in data:
        raise PlanSchemaError("top-level object must have an 'items' array")
    items = data["items"]
    if not isinstance(items, list) or len(items) == 0:
        raise PlanSchemaError("'items' must be a non-empty array")

    drafts: list[PlanItemDraft] = []
    seen_titles: set[str] = set()
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise PlanSchemaError(f"item[{i}] must be an object")

        title = it.get("title")
        if not isinstance(title, str) or not title.strip():
            raise PlanSchemaError(f"item[{i}].title must be a non-empty string")
        title = title.strip()

        reason = it.get("decision_reason")
        if not isinstance(reason, str) or len(reason.strip()) < 5:
            raise PlanSchemaError(f"item[{i}].decision_reason must be >=5 chars")

        refs = it.get("evidence_refs", [])
        if not isinstance(refs, list) or not all(isinstance(r, str) for r in refs):
            raise PlanSchemaError(f"item[{i}].evidence_refs must be an array of strings")

        domain = it.get("suggested_domain")
        if domain is not None and not isinstance(domain, str):
            raise PlanSchemaError(f"item[{i}].suggested_domain must be string or null")

        cap = it.get("expected_capability")
        if cap is not None and not isinstance(cap, str):
            raise PlanSchemaError(f"item[{i}].expected_capability must be string or null")

        deps = it.get("depends_on_titles", [])
        if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
            raise PlanSchemaError(f"item[{i}].depends_on_titles must be an array of strings")

        priority = it.get("priority", "medium")
        if priority not in _VALID_PRIORITIES:
            raise PlanSchemaError(f"item[{i}].priority must be one of {sorted(_VALID_PRIORITIES)}")

        drafts.append(
            PlanItemDraft(
                title=title,
                decision_reason=reason.strip(),
                evidence_refs=[r.strip() for r in refs],
                suggested_domain=domain.strip() if isinstance(domain, str) else None,
                expected_capability=cap.strip() if isinstance(cap, str) else None,
                depends_on_titles=[d.strip() for d in deps],
                priority=priority,
            )
        )
        seen_titles.add(title)

    # depends_on_titles must reference sibling titles that exist in this plan.
    for i, d in enumerate(drafts):
        for dep in d.depends_on_titles:
            if dep not in seen_titles:
                raise PlanSchemaError(f"item[{i}] depends on unknown title {dep!r}")
            if dep == d.title:
                raise PlanSchemaError(f"item[{i}] depends on itself")

    return drafts
