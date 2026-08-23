from __future__ import annotations

from typing import Any
from google.adk.workflow._function_node import FunctionNode


async def quality_gate_fn(ctx: Any) -> dict[str, Any]:
    specialist_reports: dict[str, Any] = ctx.state.get("specialist_reports", {})
    quality_results: dict[str, Any] = {}
    any_failed = False

    for domain, report in specialist_reports.items():
        findings = report.get("findings") if isinstance(report, dict) else report
        # Basic quality invariant: specialist report must be non-empty and not an explicit error
        is_valid = bool(findings) and "error:" not in str(findings).lower()
        quality_results[domain] = {
            "verdict": "PASS" if is_valid else "FAIL",
            "has_content": bool(findings),
        }
        if not is_valid:
            any_failed = True

    ctx.state["quality_gate_results"] = quality_results
    ctx.route = "failed" if any_failed else "passed"

    return {"any_failed": any_failed, "quality_results": quality_results}


def build_quality_gate_node() -> FunctionNode:
    return FunctionNode(func=quality_gate_fn, name="quality_gate_node")
