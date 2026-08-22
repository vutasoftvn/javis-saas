# 08 — Evaluation & Observability Spec

**Blueprint gốc:** §51–§57 của `markdown/AI_Agent_OS_Master_Architecture.md`.
**Áp dụng cho:** `agentos/evals/`, `agentos/observability/` (target) — `legacy/agent_runtime` dùng OpenTelemetry riêng, không hợp nhất.

## Trạng thái hiện tại

| Thành phần | File |
|---|---|
| Trace | `agentos/core/trace.py` (`TraceRecorder`) + `trace_sink.py` (`SqliteTraceSink`, bền vững) |
| Agent Eval | `agentos/evals/agent_eval.py` (`evaluate_agent_run()`) |
| Workflow Eval | `agentos/evals/workflow_eval.py` (`evaluate_workflow()`) |
| Business Outcome Eval | `agentos/evals/business_outcome_eval.py` (`evaluate_business_outcome()` — target vs actual, dùng chung công thức cho Marketing/OKR) |
| Skill Eval | `agentos/evals/skill_eval.py` (`evaluate_skill_run()`, mới 2026-08-22) — cập nhật `SkillManifest.quality` qua exponential moving average từ outcome thật, đóng vòng lặp mà `SkillRouter.score_skill()` đọc `eval_score` nhưng trước đây chưa ai ghi vào |
| Model Eval | `agentos/evals/model_eval.py` (`evaluate_models_across_runs()`, mới 2026-08-22) — so sánh nhiều model qua nhiều run thật (success rate, token, cost) để hỗ trợ quyết định routing §57 |
| Token/cost tracking | `agentos/core/model_provider.py` (`TokenUsage`, thật từ provider API) + `agentos/observability/metrics.py` (`RunMetrics`) + `agentos/observability/pricing.py` (Giai đoạn 3.5) |

**Cả 5/5 loại eval trong blueprint §51 (Model/Agent/Skill/Workflow/Business Outcome) nay đều đã implement** (Business Outcome Eval bị bỏ sót ở lần đọc trước — đã sửa).

Token in/out được cộng dồn thật từ mọi span `model_generation.completed` trong 1 run (Executor ghi span này mỗi lần gọi model, kèm `model`/`input_tokens`/`output_tokens`). `cost_usd` **chỉ tính khi caller tự cung cấp `pricing_table`** với giá thật cho model đã dùng — `agentos/observability/pricing.py` cố tình không hardcode bất kỳ mức giá nào (tránh bịa số liệu tài chính); nếu 1 model trong run không có trong bảng giá, `cost_usd` là `None` cho cả run (không cộng dồn 1 phần để tránh báo thiếu).

## Còn thiếu

- OpenTelemetry (production, `backend/core/telemetry.py`) và `TraceRecorder`/`SqliteTraceSink` (agentos) là 2 cơ chế trace khác nhau, chưa hợp nhất — chưa có ADR cho việc này.
- `TraceRecorder` hiện ghi span phẳng (không có `parent_span_id` thật từ bất kỳ caller nào) — trace tree đúng nghĩa blueprint §55 vẫn là "honest limitation" đã ghi sẵn trong code.

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A9.
