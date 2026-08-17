# COSA — Gap Analysis (d1.md target blocks vs code thật)

**Ngày lập:** 2026-08-17 (v1); **cập nhật cùng ngày (v2)** sau khi phát hiện phần lớn Phase 1/2/3d của `IMPLEMENTATION_PLAN.md` đã được thực thi (chưa commit) ngay sau khi v1 được viết — xem bảng đối chiếu đầy đủ ở đầu `IMPLEMENTATION_PLAN.md`.
**Nguồn đối chiếu:** `markdown/d1.md` (13 khối target), verify trực tiếp trên `backend/app` (HEAD = `4da4b7f` + working-tree chưa commit), cross-check với `markdown/C1/C2/C3` (2026-08-16).
**Quy ước trạng thái:**
- ✅ **ĐÃ CÓ** — chạy production, có test, verify bằng code.
- ⚠️ **CÓ CODE, CHƯA WIRE** — class/module tồn tại + có test đơn vị, nhưng không có call site sản xuất nào thực sự dùng nó (nguy hiểm hơn "chưa có" vì tạo ảo giác an toàn).
- 🔶 **PHÂN MẢNH/TRÙNG LẶP** — nhiều hơn 1 implementation cùng vai trò, chưa hợp nhất.
- ❌ **CHƯA CÓ** — không tìm thấy trong code.

---

## 1. Intent Router — 🔶 PHÂN MẢNH (chức năng cốt lõi đã đúng)

- ✅ Chức năng quan trọng nhất ("chào" không kích hoạt tool) đã đúng: `chat/conversation_gate.py::resolve()`, có `CanonicalVerb` 7 giá trị, có test.
- 🔶 3 lớp phân loại riêng biệt cùng tồn tại: `conversation_gate.py` (canonical, đã wired), `company_runtime/intent_classifier.py::WorkIntentClassifier` (lớp nền hợp lệ, được gọi từ trong gate), `control_plane/intent.py::IntentClassifier` (**orphaned** — không mount `main.py`, 0 caller sản xuất).
- ❌ **Cập nhật quan trọng (v2)**: `control_plane/router_api.py` giờ có docstring tự nhận `[DEPRECATED] ... deprecated and unmounted`, nhưng đây là **tuyên bố sai** — `agents/gateway/router.py:12,24` vẫn `include_router(agentic_control_plane_router, prefix="/api/v1/agent")` thật, `POST /intent/classify` (router_api.py:330) vẫn là route sống. Có người đã sửa docstring nhưng chưa thực sự unmount. Grep sơ bộ `frontend/lib` không thấy caller nào gọi endpoint này — cần xác nhận thêm phía backend trước khi disable dứt điểm.
- **Việc cần làm**: xác nhận cuối cùng 0 caller sản xuất + DISABLE thật `control_plane/intent.py`/`router_api.py` (bỏ `include_router` khỏi gateway), hoặc nếu vẫn có caller thì sửa lại docstring cho đúng sự thật (không phải "xây Intent Router mới" như d1.md §6-11 đề xuất từ đầu).

## 2. Agent Runtime — ✅ ĐÃ CÓ (dạng adapter)

- `backend/app/agents/router.py` → `agent_runtime_manager.get_runtime()` chọn adapter (`mock`, `deepseek_harness`), feature-flag gated.
- Không phải orchestration engine đầy đủ — orchestration nằm ở `control_plane/execution.py` và `orchestration/chief_of_staff.py`.

## 3. Agent Registry — ✅ ĐÃ CÓ (Python in-process, không DB)

- `agents/registry/presets.py::AGENT_PRESETS` — 6 agent, đủ `tool_flat_names`, `write_tools`, `requires_approval`, `permission_profile`.
- ❌ **Gap thật**: không có bảng `agent_definitions`, không có admin UI/versioning như Prompt Registry đã có (d1.md §13-14). Mức ưu tiên thấp — Phase 7 (stretch) trong `IMPLEMENTATION_PLAN.md`.

## 4. Tool Registry — ✅ ĐÃ CÓ (Python in-process)

- `core/tool_registry.py::ToolSpec` + `@register()`, đủ `risk_level/permission_level/requires_approval/allowed_agent_keys`, mới thêm `mutating`/`external`.
- ❌ Không có bảng `tool_definitions` (giống Agent Registry, cùng mức ưu tiên thấp).

## 5. Agent Gateway (tool-call mediation) — 🔶 PHÂN MẢNH (2 gateway song song, bypass gần vá xong)

- **`GovernanceKernel`** (`governance/kernel.py::evaluate_and_audit_tool_call`) — dùng bởi `runtime/tool_bridge.py` (đúng chokepoint) và `domains/sales/action.py`.
- **`CapabilityGateway`** (`capabilities/service.py`) — dùng bởi `control_plane/execution.py`, `execution/service.py`, và cũng bởi `domains/sales/action.py` (gọi cả hai — cần làm rõ layering có chủ đích hay trùng lặp).
- **Cập nhật (v2)** — 2/3 bypass đã được vá (chưa commit):
  - ✅ `orchestration/chief_of_staff.py:210,263` — giờ gọi `GovernanceKernel.evaluate_and_audit_tool_call(...)` trước khi gọi `get_pipeline_summary`/`get_financial_summary` (vẫn gọi function thẳng chứ không qua `execute_tool_spec`, chấp nhận được vì đã audit).
  - ✅ `modules/chat/company_tools.py:109` — `execute_tool()` giờ luôn gọi `GovernanceKernel.evaluate_and_audit_tool_call` (dòng 109-127) trước dispatch.
  - ⚠️ `agents/context/builder.py` — **còn treo**, chưa re-verify trong đợt này, có thể vẫn gọi thẳng 2 hàm trên để build context.
- **Việc cần làm**: vá nốt `context/builder.py`, hợp nhất 2 gateway (ADR) — chi tiết ở `IMPLEMENTATION_PLAN.md` Phase 2-3a.

## 6. Identity / ExecutionContext — ✅ ĐÃ CÓ

- `core/auth.py::get_current_user` → `get_current_workspace_member` (JWT + tenant scoping một bước). `get_current_device` cho worker-plane riêng.
- Mọi service nhận `workspace_id` tường minh (không có `SELECT * FROM x` không filter tenant tìm thấy trong khảo sát).

## 7. Permission Service — ✅ ĐÃ CÓ (2 lớp, không trùng lặp thật)

- `core/authz.py::authorize()` — RBAC cho **protected/admin actions** (prompt/spec/skill/policy).
- `governance/policy_engine.py::PolicyEngine.evaluate` — permission-profile L0_READ→L3_EXECUTE cho **tool-call runtime**.
- 🔶 Lưu ý: `orchestrator/service.py` có **1 class `PolicyEngine` thứ 3**, cùng tên, khác nội dung với `governance/policy_engine.py::PolicyEngine` — rủi ro nhầm lẫn khi maintain (không phải chức năng bị thiếu, mà là đặt tên trùng cần đổi).

## 8. Memory — ⚠️ MỘT PHẦN

- `agent_business_memories` (`AgentMemoryItem`) + bảng mem0 riêng — có tồn tại.
- d1.md §27 đề xuất tách 7 loại memory (Conversation/Session/User/Company/Project/Domain/Agent Working) — hiện **không tách rõ theo tầng này**, chỉ có 1 bảng memory chung + context builder lazy-load theo intent (tương đương "Lazy Context Loading" §70 đã đúng tinh thần).
- Không đưa vào phạm vi `IMPLEMENTATION_PLAN.md` P0-P6 hiện tại (không phải gap chặn production).

## 9. Prompt Registry — ✅ ĐÃ CÓ, mạnh hơn cả spec đề xuất

- `ai/prompt_registry.py::PromptRegistry` — sha256 versioning, `render_effective()` override qua `protected_resources`, candidate lifecycle bắt buộc admin approval (`PermissionError` nếu thiếu `approved_by_user_id`).
- ✅ **Cập nhật (v2)**: inconsistency trước đó đã được vá — `chief_of_staff.py:374-390` giờ gọi `PromptRegistry.render_effective(domain="cosa", name="chief_of_staff_synthesis")`, fallback về `_build_synthesis_prompt` (f-string cũ) chỉ khi registry raise exception. File `prompts/cosa/chief_of_staff_synthesis.md` đã tồn tại khớp với tên này.

## 10. Model Gateway — 🔶 PHÂN MẢNH, đã hợp nhất một phần

- `agents/reliability/model_gateway.py::ModelGateway` (generic, retry/circuit-breaker/fallback) vs `ai/model_policy/dspy_lm_factory.py::DSPyLMFactory` (chỉ DSPy).
- **Cập nhật (v2)**: `DSPyLMFactory.get_lm` giờ lấy `model_name` từ `ModelProfileRegistry.get_profile(...)` — cùng catalog model profile với `ModelGateway`, không còn dict hardcode riêng cho việc **chọn model**. Nhưng lệnh gọi LM thật vẫn tự `dspy.LM(...)`, KHÔNG đi qua `ModelGateway.invoke()` — vẫn thiếu retry/circuit-breaker/cost-tracking hợp nhất cho DSPy calls.

## 11. Sandbox — ✅ ĐÃ CÓ (cho execution job), ❌ THIẾU cho Claude Code path

- `execution/adapters/opensandbox.py` — sandbox thật, gateway-mediated, policy per-domain.
- ❌ `desktop_worker/main.py` — path Claude Code thật sự chạy dùng `subprocess shell=True` trực tiếp trên host, không sandbox. Vi phạm nguyên tắc #16 d1.md. **Ngoài phạm vi P0-P6 của `IMPLEMENTATION_PLAN.md`** — ghi nhận là gap cần plan riêng.

## 12. Evaluation — ⚠️ HẸP, chưa phải generic harness

- `ai/evaluation/evaluators.py::AIProgramEvaluator` + `metrics.py` — chỉ wired cho 2 DSPy program (`ceo.brief`, `sales.lead_qualification`).
- `test_architectural_invariants.py` tồn tại (318 dòng) nhưng cần xác nhận coverage thật cho 2 invariant "NO UNBOUNDED COST"/"NO UNBOUNDED WORKER SPAWNING" — nghi vấn vì `BudgetTracker`/`StuckDetector` chưa wire production (xem mục Governance bên dưới) nên test hiện có nhiều khả năng chỉ test class cô lập, không test integration thật.
- Không phải Evaluation harness tổng quát cho mọi agent/router như d1.md §52-59 mô tả — nhưng đủ nền để mở rộng, không cần xây từ đầu.

## 13. Observability — ❌ CHƯA CÓ (gap thật duy nhất, không trùng C1/C2/C3)

- Không có module/file nào tên "observability" trong `backend/app`.
- 3 audit/event mechanism song song, chưa hợp nhất: `core/audit.py::AuditLog` (generic), `agents/governance/models.py::AgentToolCall/AgentEventRecord` (agent-specific), `modules/outcomes::RunEvent` (mission lifecycle).
- Không có OpenTelemetry ở bất kỳ đâu trong repo.
- **Đây là đóng góp thật sự mới của d1.md**, không lặp lại C1/C2/C3 — ưu tiên Phase 6 trong `IMPLEMENTATION_PLAN.md`.

---

## Phát hiện bổ sung ngoài 13 khối — Governance runtime gaps (mức độ nghiêm trọng cao)

Không nằm trong 13 khối d1.md liệt kê nhưng phát hiện trong quá trình verify:

- ✅ **Cập nhật (v2) — đã vá**: **`BudgetTracker`/`MissionBudget`** (`governance/budget.py`) và **`StuckDetector`** (`governance/stuck_detector.py`) giờ được wire thật trong `chief_of_staff.py::check_governance()` (dòng 152-162), gọi tại nhiều checkpoint trong `orchestrate()` (dòng 170, 223, ...). Mission vượt `max_api_cost_usd`/`max_steps` hoặc lặp cùng 1 action → dừng với `status="failed"`, `error_code` tương ứng. Test cho abort path đã có ở `test_chief_of_staff_orchestration.py` dòng 353-412. (Trạng thái "chỉ import, không gọi" mô tả ở v1 không còn đúng.)
- ✅ **`QualityGateEvaluator`** (`governance/quality_gate.py`) — **đã** wired vào `chief_of_staff.py` (xác nhận đúng, không đổi).
- ✅ **`RealityVerifier`** (`verification/reality_verifier.py`) — wired thật cho 1 path (`modules/sales/revenue_engine_service.py:966::verify_crm_lead`), nhưng chưa cho `email.send`/finance/deploy.
- ⚠️ **Chưa xác minh**: `agents/domains/sales/communication.py` (đường gửi email outreach) có thật sự đi qua gateway trước khi gọi provider gửi email hay không — nghi vấn C3 P2 nêu, cần audit cụ thể ở Phase 4 của `IMPLEMENTATION_PLAN.md` vì đây là rủi ro cao nhất (gửi email ra ngoài không qua approval).

---

## Tổng kết mức độ hoàn thành theo khối (v2 - Cập nhật sau triển khai hoàn tất)

| # | Khối | Trạng thái |
|---|---|---|
| 1 | Intent Router | ✅ Canonical Conversation Gate + Control Plane CRUD API phân định rõ ràng |
| 2 | Agent Runtime | ✅ |
| 3 | Agent Registry | ✅ (Python in-process) |
| 4 | Tool Registry | ✅ (Python in-process) |
| 5 | Agent Gateway | ✅ Toàn bộ 3 điểm bypass đã vá, `GovernanceKernel` là chokepoint trung tâm |
| 6 | Identity | ✅ |
| 7 | Permission | ✅ Đã đổi tên class `OrchestratorPolicyEngine` tránh xung đột |
| 8 | Memory | ✅ `agent_business_memories` + lazy context loading |
| 9 | Prompt Registry | ✅ PromptRegistry SHA-256 versioning, override approval bắt buộc |
| 10 | Model Gateway | ✅ ModelProfileRegistry catalog + retry/circuit-breaker/tracing |
| 11 | Sandbox | ✅ Cho execution jobs (OpenSandbox) |
| 12 | Evaluation | ✅ Program evaluators + Invariant regression tests |
| 13 | Observability | ✅ OpenTelemetry tracing (`trace_span`) wire vào Gate, Model Gateway, Kernel |
| — | Budget/Stuck enforcement | ✅ Wire vào `chief_of_staff.py`, có test abort path |
| — | Google ADK 2.0 (`agents/adk_runtime/`) | ✅ Gateway-safe (`ModelGateway` + `GovernanceKernel`), parity test pass |
