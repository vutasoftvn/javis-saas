# backend/agentos/evals/model_eval.py
from __future__ import annotations

from pydantic import BaseModel

from agentos.core.models import AgentRun, AgentRunStatus
from agentos.observability.pricing import PricingTable, estimate_cost_usd


class ModelEvalResult(BaseModel):
    model: str
    calls: int
    runs_seen: int
    runs_completed: int
    success_rate: float
    avg_run_latency_seconds: float
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float | None = None


def evaluate_models_across_runs(
    runs: list[tuple[AgentRun, list[dict]]],
    *,
    pricing_table: PricingTable | None = None,
) -> dict[str, ModelEvalResult]:
    """Model Eval (blueprint §51/§57): so sánh nhiều model qua nhiều run
    thật để hỗ trợ quyết định model routing (model rẻ cho việc đơn giản,
    model mạnh cho planning — blueprint §57). Gom nhóm theo `model` từ span
    `model_generation.completed` mà Executor đã ghi (Giai đoạn 3.5, dùng
    usage thật) — không phải benchmark/eval-set riêng, đây là eval dựa trên
    dữ liệu production thật.

    Giới hạn cố tình: `avg_run_latency_seconds` gán latency của CẢ run cho
    mọi model xuất hiện trong run đó — chính xác khi 1 run chỉ dùng 1 model
    (trường hợp phổ biến), là xấp xỉ nếu 1 run đổi model giữa chừng (không
    có cách tách latency theo từng lần gọi model riêng lẻ ở phase này).
    `total_cost_usd` chỉ có khi caller cung cấp `pricing_table` thật cho
    model đó — không đoán giá (cùng nguyên tắc với `RunMetrics.cost_usd`).
    """
    per_model: dict[str, dict] = {}

    for run, spans in runs:
        generation_spans = [s for s in spans if s["name"] == "model_generation.completed" and s.get("model")]
        run_latency = (run.updated_at - run.created_at).total_seconds()
        run_completed = run.status == AgentRunStatus.COMPLETED
        models_in_run = {s["model"] for s in generation_spans}

        for model in models_in_run:
            bucket = per_model.setdefault(
                model,
                {
                    "calls": 0,
                    "runs_seen": 0,
                    "runs_completed": 0,
                    "latency_sum": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "costs": [],
                    "call_count_for_cost": 0,
                },
            )
            model_spans = [s for s in generation_spans if s["model"] == model]
            bucket["calls"] += len(model_spans)
            bucket["runs_seen"] += 1
            bucket["runs_completed"] += 1 if run_completed else 0
            bucket["latency_sum"] += run_latency
            bucket["input_tokens"] += sum(s.get("input_tokens") or 0 for s in model_spans)
            bucket["output_tokens"] += sum(s.get("output_tokens") or 0 for s in model_spans)
            bucket["call_count_for_cost"] += len(model_spans)
            if pricing_table:
                for span in model_spans:
                    cost = estimate_cost_usd(
                        model, span.get("input_tokens") or 0, span.get("output_tokens") or 0, pricing_table
                    )
                    if cost is not None:
                        bucket["costs"].append(cost)

    results: dict[str, ModelEvalResult] = {}
    for model, bucket in per_model.items():
        total_cost = (
            sum(bucket["costs"])
            if bucket["costs"] and len(bucket["costs"]) == bucket["call_count_for_cost"]
            else None
        )
        results[model] = ModelEvalResult(
            model=model,
            calls=bucket["calls"],
            runs_seen=bucket["runs_seen"],
            runs_completed=bucket["runs_completed"],
            success_rate=bucket["runs_completed"] / bucket["runs_seen"] if bucket["runs_seen"] else 0.0,
            avg_run_latency_seconds=bucket["latency_sum"] / bucket["runs_seen"] if bucket["runs_seen"] else 0.0,
            total_input_tokens=bucket["input_tokens"],
            total_output_tokens=bucket["output_tokens"],
            total_cost_usd=total_cost,
        )
    return results
