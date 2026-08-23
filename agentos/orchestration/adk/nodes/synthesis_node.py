from __future__ import annotations

from typing import Any, Optional
from google.adk.workflow._function_node import FunctionNode

from agentos.core.model_provider import ModelProvider


def build_synthesis_node(model_provider: Optional[ModelProvider] = None) -> FunctionNode:
    async def synthesis_fn(ctx: Any) -> dict[str, Any]:
        goal = ctx.state.get("goal", "")
        specialist_reports: dict[str, Any] = ctx.state.get("specialist_reports", {})

        report_summaries = []
        for domain, report in specialist_reports.items():
            findings = report.get("findings") if isinstance(report, dict) else str(report)
            report_summaries.append(f"[{domain.upper()}]: {findings}")

        combined_context = "\n".join(report_summaries)

        if model_provider is not None:
            prompt = (
                f"You are the Co-founder synthesizing specialist findings for the mission: '{goal}'.\n\n"
                f"Specialist Reports:\n{combined_context}\n\n"
                f"Provide a structured synthesis, diagnosis, and action plan."
            )
            resp = await model_provider.generate(
                system_prompt="Synthesize specialist reports into an actionable executive summary.",
                messages=[{"role": "user", "content": prompt}],
            )
            synthesis_output = resp.text or combined_context
        else:
            synthesis_output = f"Mission Goal: {goal}\n\nSynthesized Findings:\n{combined_context}"

        ctx.state["synthesis_output"] = synthesis_output
        ctx.state["diagnosis"] = synthesis_output
        ctx.state["synthesis_status"] = "completed"

        return {"synthesis_output": synthesis_output, "status": "completed"}

    return FunctionNode(func=synthesis_fn, name="synthesis_node")
