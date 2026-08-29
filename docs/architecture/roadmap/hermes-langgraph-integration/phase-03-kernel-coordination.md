# Phase 3 — OpenAI Agents Kernel + Coordination Primitives (+ LangGraph Technical Spike)

> Nguồn gốc: `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` §"Phase 3" (Step 5, P0.4). Bổ sung Hermes/LangGraph theo `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3, §4 — đây là phase có bổ sung lớn nhất trong toàn bộ integration.

## Mục tiêu

`ExecutionKernel` có 1 implementation thật dựa trên OpenAI Agents SDK, `packages/agent/coordination/` có các primitive framework-neutral rút từ hành vi ADK orchestrator cũ — **và** (mới) một LangGraph technical spike độc lập, không ràng buộc production, trả lời câu hỏi feasibility kỹ thuật.

## Điều kiện tiên quyết

- Phase 1 (contracts, đặc biệt `ExecutionKernel` protocol, ADR-KERNEL đã merge) và Phase 2 (nơi lưu checkpoint) đã xong.
- **Riêng cho phần LangGraph spike:** Phase 1 baseline WorkflowEngine (migrate từ `agentos/workflows/*`) phải đã hoàn tất và pass 100% test — đây là baseline bắt buộc để so sánh. Không chạy spike song song với việc harden Phase 1 (lý do: xem Integration Plan §5, rejected alternative #4).

## Việc cụ thể (gốc) — Kernel

1. Thêm `openai-agents` vào dependency riêng của `packages/agent` (file requirements/pyproject riêng — không đụng `agentos/requirements.txt`).
2. Viết `packages/agent/kernel/openai_agents_kernel.py` implement `ExecutionKernel` protocol: `run()`, `resume()`, `cancel()`, `stream()`. **Lưu ý:** file cùng tên đã tồn tại hiện tại là custom loop (492 dòng, dùng `openai` package trần) — đây chính là implementation cần thay thế theo ADR-KERNEL (Phase 1), không phải viết thêm song song.
3. Viết `RunState` serialization adapter: SDK `RunState.to_json()/from_json()` ↔ cột serialized state trong `agent.run_checkpoints`.
4. Implement streaming event mapping sang `agent.run_events` vocabulary đã định nghĩa ở Phase 2.
5. Implement interruption/approval surfacing: khi SDK báo tool-call cần approval, map sang `WaitDescriptor` + tạo row `agent.approvals` (kernel chỉ cần phát đúng signal, xử lý đầy đủ ở Phase 5).
6. Viết DeepSeek compatibility matrix test — 1 test file chạy qua: basic response, structured output, single tool call, parallel tool calls, streaming, tool-call IDs, usage, error propagation, context length, RunState resume, agent-as-tool, approval interruption. Output là bảng capability profile (pass/partial/fail per item).
7. Viết `packages/agent/coordination/` — đọc lại characterization test của `agentos/orchestration/adk/*` (Phase 0) để hiểu behavior, viết mới các primitive: `delegate.py`, `parallel.py`, `supervisor.py`, `risk_classification.py`, `approval_gate.py`, `quality_gate.py`, `synthesis.py` — mỗi primitive dùng `ExecutionKernel` protocol Phase 1, KHÔNG import `google.adk.*`.

## Test bắt buộc (gốc)

- DeepSeek matrix test chạy được và log ra capability profile.
- Mỗi primitive coordination có ít nhất 1 test đối chiếu hành vi với characterization test cũ của ADK orchestrator — giữ đúng invariant (parallel thật sự chạy song song, supervisor thật sự tổng hợp kết quả specialist).

## Bổ sung Hermes/LangGraph — LangGraph Technical Spike (isolated, non-binding)

**Nguyên tắc:** đây là gate **kỹ thuật**, KHÔNG phải gate **adoption**. Quyết định adopt/reject/defer chỉ diễn ra ở Phase 6, sau khi Capability Gateway (Phase 4) và Durable Approval (Phase 5) đã chứng minh boundary integration thật. Ở Phase 3, spike chỉ trả lời một câu hỏi duy nhất: *LangGraph có fit kỹ thuật với WorkflowSpec/runtime model của COSA không?*

**Việc cụ thể:**

1. Tạo branch riêng `experiment/langgraph-spike` — **không merge vào main**.
2. Thêm `langgraph` như dependency isolated trong branch này (không đụng `packages/agent` main dependency tree).
3. Viết `packages/agent/workflows/langgraph_compiler.py` (trong branch): compile `WorkflowSpec` (đã migrate ở Phase 1) → LangGraph `StateGraph`. Mapping tối thiểu cần chứng minh:
   ```text
   DETERMINISTIC → normal graph node
   AGENT          → node gọi ExecutionKernel (giả lập, vì Phase 4/5 chưa xong)
   TOOL_CALL      → node gọi Capability Gateway giả lập
   depends_on     → graph edges/joins
   parallel branches → parallel ready nodes
   ```
4. Viết `packages/agent/workflows/langgraph_runtime.py` (trong branch) implement thử `WorkflowRuntime` protocol thay thế bằng LangGraph.
5. Chạy kịch bản spike workflow tối thiểu (theo supplement gốc §44, rút gọn — KHÔNG dùng approval/governance thật):
   ```text
   START → ReadBusinessContext (mock) → [ResearchA ∥ ResearchB] → AgentStep (kernel giả lập)
         → GovernedWriteProposal (giả lập) → END
   ```
6. Đo và log:
   - Static DAG compile từ WorkflowSpec → StateGraph — có chạy được không, mất bao nhiêu code so với WorkflowEngine native.
   - Parallel superstep: 2 node song song, xác nhận write của node A không thấy được bởi node B trong cùng superstep (invariant Pregel).
   - Postgres checkpointer (native, Option A theo supplement §38): kill process giữa lúc chạy → resume từ checkpoint đúng.
   - Pending-writes: wave A/B/C, A/B thành công, C fail → kill process → resume → chỉ retry C, không rerun A/B.
7. Ghi toàn bộ kết quả vào `docs/architecture/langgraph_spike_results.md`, KHÔNG phải trong `agentos_salvage_inventory.md` (đây là artifact riêng của track LangGraph, không lẫn với salvage inventory của agentos).

**Không làm ở Phase 3 (để dành Phase 4/5/6):**
- Không test approval/governance thật — dùng approval giả lập vì Capability Gateway (Phase 4) và Durable Approval (Phase 5) chưa tồn tại.
- Không quyết định adopt/reject — đó là Phase 6.
- Không merge branch vào main dưới bất kỳ hình thức nào ở phase này.

## Definition of Done — Phase 3

**Gốc:**
- `OpenAIAgentsKernel` chạy được 1 Run thật end-to-end (input → tool call → output) trong môi trường dev, ghi đúng vào `agent.run_events`.
- Capability matrix profile đã document cho ít nhất DeepSeek (route chính hiện có).
- `packages/agent/coordination/` không có import nào từ `google.adk` hay `agentos.*`.
- Không còn dùng `google.adk.workflow._function_node.FunctionNode` hoặc private API tương tự trong code mới.

**Bổ sung:**
- `requirements.txt` (hoặc pyproject riêng của `packages/agent`) có `openai-agents`, xác nhận import trong `kernel/openai_agents_kernel.py` (không còn dùng `openai` package trần cho vòng lặp chính) — đây là bằng chứng ADR-KERNEL đã thực thi, không chỉ ratify trên giấy.
- (Nếu chạy spike) branch `experiment/langgraph-spike` tồn tại, `docs/architecture/langgraph_spike_results.md` có log kết quả DAG compile/superstep/checkpoint/resume/pending-writes.

## Rủi ro/lưu ý

**Gốc:** SDK OpenAI Agents có thể có giới hạn/khác biệt hành vi với DeepSeek qua proxy — capability matrix để phát hiện sớm, không phải rào cản chặn tiến độ; ghi nhận rõ item nào PARTIAL/FAIL.

**Bổ sung:** Rủi ro lớn nhất ở phase này là **lẫn hai track** — để LangGraph spike ảnh hưởng tiến độ/quyết định của việc thay thế kernel custom loop, hoặc ngược lại. Giữ 2 track hoàn toàn tách biệt: kernel work đi vào main branch bình thường theo DoD gốc; LangGraph spike ở branch riêng, không blocking Phase 4 nếu chưa xong (Phase 4 vẫn tiếp tục trên main, chỉ tích hợp LangGraph ToolStep nếu spike branch còn sống).
