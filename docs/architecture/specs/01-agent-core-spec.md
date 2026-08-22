# 01 — Agent Core & Runtime Spec

**Blueprint gốc:** §5–§7, §55, §58–§60, §73, §89 của `markdown/AI_Agent_OS_Master_Architecture.md`.
**Áp dụng cho:** `agentos/` (target theo ADR-013) — song song `legacy/agent_runtime` vẫn phục vụ production hiện tại.

## Trạng thái hiện tại

`agentos/core/` hiện thực đủ các thành phần blueprint §5.3 liệt kê:

| Thành phần | File |
|---|---|
| ContextBuilder | `agentos/core/context_builder.py` |
| Planner | `agentos/core/planner.py` |
| Executor + tool loop | `agentos/core/executor.py` |
| PolicyEngine (ALLOW/DENY/REQUIRE_APPROVAL) | `agentos/core/policy.py` |
| TraceRecorder + persist | `agentos/core/trace.py`, `trace_sink.py` |
| Model abstraction | `agentos/core/model_provider.py` + `agentos/core/adapters/{openai_compatible,anthropic,deepseek_harness}_provider.py`, `model_gateway.py` |

Executor giờ ghi `model_generation.completed` span cho mỗi lần gọi model (token usage thật, xem spec 08) và thread `run_id` xuống PolicyEngine/ApprovalService để audit (xem spec 07).

Production thật (`legacy/agent_runtime`) dùng kiến trúc khác: ADK orchestration + DeepSeek Harness adapter, `PermissionLevel` (L0-L3A-L3) thay vì `PermissionClass`, OpenTelemetry thay vì `TraceRecorder`/SqliteTraceSink, `reliability/model_gateway.py` (LiteLLM) thay vì `agentos/core/adapters/model_gateway.py`.

## Multi-Agent (blueprint §9–§10)

`agentos/agents/` có đủ 4 pattern §9.2:

| Pattern | File |
|---|---|
| Sequential | `agentos/agents/sequential.py` (`SequentialPipeline`) |
| Parallel | `agentos/agents/parallel.py` (`ParallelFanOut`) + `agentos/workflows/steps.py` (`ParallelStep`, tích hợp vào WorkflowEngine) |
| Supervisor | `agentos/agents/supervisor.py` (`SupervisorAgent`, chọn specialist theo relevance score qua `AgentRegistry`) |
| Debate/Critic | `agentos/agents/debate.py` (`DebateLoop`, generator↔critic tối đa `max_rounds`) |

Production dùng ADK: `legacy/agent_runtime/workforce/agents/orchestration/adk/nodes/specialist_delegation_node.py` (supervisor pattern thật, qua `TaskBoardService` — hỗ trợ durable delegation, worker lease, retry/cancel/continuation mà `agentos/agents/agent_registry.py` chưa có tương đương).

## Còn thiếu / cần quyết định

- `PermissionLevel` đã port vào `agentos/core/policy.py` (ADR-014 bước 1, xem spec 07) — cutover Executor/tool binding thật sang dùng nó (bước 2) vẫn chưa làm.
- `legacy/agent_runtime/workforce/agents/reliability/model_gateway.py` hỗ trợ nhiều provider hơn (LiteLLM) so với `agentos/core/adapters/model_gateway.py` (DeepSeek/OpenAI/OpenRouter/Anthropic) — chưa port Gemini/Kira/apiai_vn.
- ContextBuilder tương đương ở phía `legacy/agent_runtime` chưa xác nhận có tách riêng thành 1 class hay nằm rải trong orchestration nodes — cần audit nếu có kế hoạch port ngược.

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A1.
