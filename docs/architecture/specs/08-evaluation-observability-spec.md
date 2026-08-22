# 08 — Evaluation & Observability Spec

**Blueprint gốc:** §51–§57 của `markdown/AI_Agent_OS_Master_Architecture.md`.
**Áp dụng cho:** `agentos/evals/`, `agentos/observability/` (target) — `legacy/agent_runtime` dùng OpenTelemetry riêng, không hợp nhất.

## Trạng thái hiện tại

| Thành phần | File |
|---|---|
| Trace | `agentos/core/trace.py` (`TraceRecorder`) + `trace_sink.py` (`SqliteTraceSink`, bền vững) |
| Agent Eval | `agentos/evals/agent_eval.py` (`evaluate_agent_run()`) |
| Workflow Eval | `agentos/evals/workflow_eval.py` (`evaluate_workflow()`) |
| Token/cost tracking | `agentos/core/model_provider.py` (`TokenUsage`, thật từ provider API) + `agentos/observability/metrics.py` (`RunMetrics`) + `agentos/observability/pricing.py` (Giai đoạn 3.5) |

Token in/out được cộng dồn thật từ mọi span `model_generation.completed` trong 1 run (Executor ghi span này mỗi lần gọi model, kèm `model`/`input_tokens`/`output_tokens`). `cost_usd` **chỉ tính khi caller tự cung cấp `pricing_table`** với giá thật cho model đã dùng — `agentos/observability/pricing.py` cố tình không hardcode bất kỳ mức giá nào (tránh bịa số liệu tài chính); nếu 1 model trong run không có trong bảng giá, `cost_usd` là `None` cho cả run (không cộng dồn 1 phần để tránh báo thiếu).

## Còn thiếu

- Skill Eval, Business Outcome Eval, Model Eval (3/5 loại eval trong §51) — chưa có, chỉ Agent Eval + Workflow Eval đã implement.
- OpenTelemetry (production, `backend/core/telemetry.py`) và `TraceRecorder`/`SqliteTraceSink` (agentos) là 2 cơ chế trace khác nhau, chưa hợp nhất — chưa có ADR cho việc này.
- `TraceRecorder` hiện ghi span phẳng (không có `parent_span_id` thật từ bất kỳ caller nào) — trace tree đúng nghĩa blueprint §55 vẫn là "honest limitation" đã ghi sẵn trong code.

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A9.
