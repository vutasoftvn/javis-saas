# backend/app/workforce/agents/orchestration/adk/nodes/synthesis_node.py
"""Gọi thật qua CosaModelGatewayLlm -> ModelGateway.invoke() — đây là phần
"reasoning thật, là hàm thật của goal/snapshot" (không phải text mẫu), y hệt
chief_of_staff.py::orchestrate bước "3. Real synthesis call through AgentRuntime"."""
from typing import Any

from google.adk.models.llm_request import LlmRequest
from google.adk.workflow._function_node import FunctionNode
from google.genai import types as genai_types

from db.session import SessionLocal
from founder_os.outcomes.models import RunStep
from workforce.agents.orchestration.adk.model_adapter import CosaModelGatewayLlm
from workforce.agents.orchestration.synthesis_helpers import build_synthesis_prompt
from workforce.agents.runtime.json_output import parse_structured_output


def _fetch_specialist_reports(outcome_run_id: int) -> dict[str, Any]:
    """Đọc RunStep.result_jsonb đã hoàn tất — y hệt cách
    chief_of_staff.py::resume_after_delegation đọc reports (dòng ~955-959).
    Đây là nguồn sự thật duy nhất; KHÔNG tin dữ liệu specialist report nào khác
    (kể cả payload đính kèm interrupt response khi resume)."""
    db = SessionLocal()
    try:
        steps = db.query(RunStep).filter(RunStep.run_id == outcome_run_id).all()
        return {
            step.inputs_jsonb["report_key"]: (step.result_jsonb or {})
            for step in steps
            if isinstance(step.inputs_jsonb, dict)
            and step.inputs_jsonb.get("mission_kind") == "chief_of_staff_specialist"
            and step.status == "completed"
        }
    finally:
        db.close()


async def synthesis_fn(ctx: Any) -> dict[str, Any]:
    goal = ctx.state["goal"]
    # Cho phép test/caller bơm sẵn specialist_reports để bỏ qua truy vấn DB;
    # production luôn để trống ở đây nên sẽ fetch thật từ RunStep.
    specialist_reports: dict[str, Any] = ctx.state.get("specialist_reports") or _fetch_specialist_reports(
        ctx.state["outcome_run_id"]
    )
    ctx.state["specialist_reports"] = specialist_reports
    sales_data = specialist_reports.get("sales", {})
    fin_data = specialist_reports.get("finance", {})

    prompt = build_synthesis_prompt(goal, sales_data, fin_data)
    llm = CosaModelGatewayLlm(model="deepseek/deepseek-reasoner", profile_name="reasoning")
    llm_request = LlmRequest(contents=[genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])])

    diagnosis = ""
    finish_ok = True
    async for resp in llm.generate_content_async(llm_request):
        diagnosis = "\n".join(p.text for p in (resp.content.parts or []) if p.text)
        finish_ok = resp.finish_reason == genai_types.FinishReason.STOP

    parsed = parse_structured_output(diagnosis)
    if parsed is not None:
        diagnosis = parsed.get("diagnosis", diagnosis)
        status = "completed" if finish_ok else "partial"
    else:
        status = "partial" if finish_ok else "failed"

    ctx.state["diagnosis"] = diagnosis
    ctx.state["synthesis_status"] = status
    return {"diagnosis": diagnosis, "status": status}


def build_synthesis_node() -> FunctionNode:
    return FunctionNode(func=synthesis_fn, name="synthesis_node")
