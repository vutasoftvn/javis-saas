# COSA — Migration Map

**Ngày lập:** 2026-08-17 (v1); **cập nhật cùng ngày (v2)** — vài dòng REFACTOR đã được thực thi (chưa commit) ngay sau khi v1 viết, đánh dấu ✅ DONE bên dưới. Xem bảng đối chiếu đầy đủ ở đầu `IMPLEMENTATION_PLAN.md`.
**Cách đọc:** Mỗi dòng = 1 module/quyết định. Cột "Phase" trỏ tới phase tương ứng trong `IMPLEMENTATION_PLAN.md`. KEEP = giữ nguyên, không sửa. REFACTOR = sửa tại chỗ, không đổi vị trí. MOVE = đổi vị trí/API nhưng giữ logic. REPLACE = thay bằng thứ khác (có strangler pattern). DISABLE = tắt/gỡ khỏi đường sản xuất (không nhất thiết xoá file ngay). NEW = chưa tồn tại, cần viết mới.

---

## Routing / Intent

| Module | Quyết định | Phase | Ghi chú |
|---|---|---|---|
| `modules/chat/conversation_gate.py` | **KEEP** | — | Canonical intent+verb router, đúng invariant, có test |
| `modules/company_runtime/intent_classifier.py::WorkIntentClassifier` | **KEEP** | — | Base classifier hợp lệ, được gọi từ trong gate |
| `agents/control_plane/intent.py` | **DISABLE** | 3c | Orphaned — 0 caller sản xuất, không mount `main.py` |
| `agents/control_plane/router_api.py` | **DISABLE** (nếu chỉ phục vụ `intent.py`) | 3c | ❌ v2: docstring đã tự sửa thành "[DEPRECATED] deprecated and unmounted" nhưng **vẫn mounted thật** qua `agents/gateway/router.py:12,24` (`/api/v1/agent`), `POST /intent/classify` vẫn sống. Docstring hiện sai — audit caller thật rồi disable dứt điểm hoặc sửa lại docstring |
| `core/function_router.py` | **KEEP** | — | Tiện ích department-keyword riêng, không phải Intent Router, không xung đột |

## Agent Gateway / Governance

| Module | Quyết định | Phase | Ghi chú |
|---|---|---|---|
| `agents/governance/kernel.py::GovernanceKernel` | **KEEP + mở rộng vai trò** | 3a | Trở thành chokepoint duy nhất |
| `agents/capabilities/service.py::CapabilityGateway` | **REFACTOR** | 3a | Gọi `GovernanceKernel` bên trong thay vì tự đánh giá `PolicyEngine` riêng |
| `agents/governance/policy_engine.py::PolicyEngine` | **KEEP** | — | Canonical policy evaluator |
| `agents/orchestrator/service.py::PolicyEngine` (class trùng tên) | **REFACTOR (đổi tên)** | 3a | Đổi tên tránh nhầm với governance PolicyEngine, xác nhận không trùng logic |
| `agents/orchestration/chief_of_staff.py:148,156` (bypass) | **REFACTOR — ✅ DONE** | 2 | v2: dòng 210,263 giờ gọi `GovernanceKernel.evaluate_and_audit_tool_call` trước khi gọi `get_pipeline_summary`/`get_financial_summary` |
| `agents/context/builder.py` (bypass) | **REFACTOR — còn treo** | 2 | Chưa re-verify ở v2, khả năng vẫn gọi thẳng |
| `modules/chat/company_tools.py:109` (bypass) | **REFACTOR — ✅ DONE** | 2 | v2: `execute_tool()` giờ luôn gọi `GovernanceKernel.evaluate_and_audit_tool_call` trước dispatch |
| `agents/governance/budget.py` | **REFACTOR (wire) — ✅ DONE** | 1 | v2: `chief_of_staff.py::check_governance()` (dòng 152-162) instantiate và gọi thật, có test abort path |
| `agents/governance/stuck_detector.py` | **REFACTOR (wire) — ✅ DONE** | 1 | v2: cùng `check_governance()`, wired thật |
| `agents/governance/quality_gate.py` | **KEEP** | — | Đã wired đúng vào `chief_of_staff.py` |
| `agents/execution/credential_broker.py::CredentialBroker` | **KEEP** | — | Secret Broker đúng mẫu, không lộ credential cho LLM |

## Model Gateway

| Module | Quyết định | Phase | Ghi chú |
|---|---|---|---|
| `agents/reliability/model_gateway.py::ModelGateway` | **KEEP** | 3b | Canonical sau hợp nhất |
| `agents/reliability/model_profiles.py::ModelProfileRegistry` | **KEEP** | — | |
| `ai/model_policy/dspy_lm_factory.py::DSPyLMFactory` | **REFACTOR — 🔶 một phần** | 3b | v2: `get_lm` đã lấy model name từ `ModelProfileRegistry` chung, nhưng lệnh gọi LM vẫn tự `dspy.LM(...)`, chưa qua `ModelGateway.invoke()` |

## Prompt

| Module | Quyết định | Phase | Ghi chú |
|---|---|---|---|
| `ai/prompt_registry.py::PromptRegistry` | **KEEP** | — | Đã đúng chuẩn, mạnh hơn spec |
| `core/protected_resources/` | **KEEP** | — | Backing store versioning dùng chung |
| `agents/orchestration/chief_of_staff.py::_build_synthesis_prompt` | **MOVE — ✅ DONE** | 3d | v2: đã load qua `PromptRegistry.render_effective(domain="cosa", name="chief_of_staff_synthesis")`; `_build_synthesis_prompt` giữ lại làm fallback khi registry lỗi |

## Verification / Reality

| Module | Quyết định | Phase | Ghi chú |
|---|---|---|---|
| `agents/verification/reality_verifier.py::RealityVerifier` | **REFACTOR (mở rộng)** | 4 | Đã đúng cho CRM lead, thêm email/finance/deploy |
| `modules/outcomes/models.py::OutcomeRun.verification_status/jsonb` | **KEEP** | — | Cột đã có sẵn từ commit trước |
| `agents/domains/sales/communication.py` | **AUDIT rồi REFACTOR nếu cần** | 4 | Xác minh có đi qua gateway trước khi gửi email hay không |

## Orchestration / Workflow engine

| Module | Quyết định | Phase | Ghi chú |
|---|---|---|---|
| `agents/control_plane/execution.py::ControlPlaneExecutionManager` | **KEEP tạm thời, REPLACE dần** | 5 | Giữ nguyên, strangler pattern qua ADK; KHÔNG xoá trong phạm vi plan này |
| `agents/control_plane/planner.py::GoalDecomposer` | **KEEP tạm thời** | 5 | Nguồn logic để map sang ADK graph cho domain pilot |
| `agents/control_plane/router.py::DomainCapabilityRouter` | **KEEP** | — | Route table domain:capability, không đổi |
| `agents/orchestration/chief_of_staff.py::ChiefOfStaffOrchestrator` | **RETIRED (2026-08-21)** | Quyết định 1 | Đã xoá vĩnh viễn và thay thế hoàn toàn bằng `AdkCofounderWorkflow` (`app.workforce.agents.orchestration.adk.workflow`) |
| `agents/orchestration/mission_control_bus.py::MissionControlBus` | **KEEP** | — | Đã publish qua `core/events.py::EventBroker` cross-process (P0.4 của C3 đã xong) |
| `modules/outcomes/*` (Mission Ledger) | **KEEP** | — | ~15 module phụ thuộc, không viết lại; bridge `AgentRun.outcome_run_id ↔ OutcomeRun.agent_run_id` đã có 2 chiều |
| `agents/domains/{sales,finance,marketing,legal,learning}/*.py` | **KEEP** | — | Business logic thuần, tái dùng làm node function cho ADK ở Phase 5 |
| `agents/adk_runtime/` → `app.workforce.agents.orchestration.adk` | **COMPLETED (2026-08-21)** | Quyết định 1 | Đã triển khai chuẩn Google ADK 2.0 (`google-adk==2.7.0`) với `AdkCofounderWorkflow`, `FunctionNode` tất định, `CosaGovernedTool`, `CosaModelGatewayLlm`, và `MissionResumeJob` |

## Sandbox

| Module | Quyết định | Phase | Ghi chú |
|---|---|---|---|
| `agents/execution/adapters/opensandbox.py` | **KEEP** | — | Sandbox thật, gateway-mediated, đúng chuẩn |
| `agents/execution/policies.py::SandboxPolicy` | **KEEP** | — | |
| `desktop_worker/main.py` | **GHI NHẬN GAP, NGOÀI PHẠM VI** | — | `subprocess shell=True` trực tiếp host, không sandbox — cần plan riêng nếu muốn sandbox hoá Claude Code path |

## Observability

| Module | Quyết định | Phase | Ghi chú |
|---|---|---|---|
| OpenTelemetry integration | **NEW** | 6 | Bọc quanh 3 audit table hiện có, không thay thế |
| `core/audit.py::AuditLog` | **KEEP** | 6 | Giữ làm 1 trong 3 nguồn audit, thêm span xung quanh |
| `agents/governance/models.py::AgentToolCall/AgentEventRecord` | **KEEP** | 6 | Giữ, thêm span xung quanh |
| `modules/outcomes::RunEvent` | **KEEP** | 6 | Giữ, thêm span xung quanh |
| `modules/platform/missions_router.py` | **REFACTOR (mở rộng)** | 6 | Thêm endpoint trả span/timeline cho Hologram Hub |

## Registry (thấp ưu tiên / stretch)

| Module | Quyết định | Phase | Ghi chú |
|---|---|---|---|
| `agents/registry/presets.py::AGENT_PRESETS` | **KEEP** | — | Hoạt động tốt, có test |
| `core/tool_registry.py::ToolSpec` | **KEEP** | — | Hoạt động tốt, có test |
| DB-backed `agent_definitions`/`tool_definitions` + admin UI | **NEW (stretch, Phase 7)** | 7 | Chỉ làm nếu admin cần sửa config không qua deploy |

## Frontend

| Module | Quyết định | Phase | Ghi chú |
|---|---|---|---|
| `frontend/lib/modules/chat/*` | **KEEP** | — | Đã sạch legacy reference, không đổi trong plan này |
| `frontend/lib/modules/hologram_hub/*` | **KEEP, nối dây thêm ở Phase 6** | 6 | UI đã đúng mẫu, chỉ cần API mission/trace mới |

---

## Không nằm trong phạm vi P0-P7 của `IMPLEMENTATION_PLAN.md` (ghi nhận, chưa lên kế hoạch thực thi)

- Sandbox hoá `desktop_worker/main.py` (Claude Code path).
- Tách 7 tầng Memory (Conversation/Session/User/Company/Project/Domain/Agent Working) theo đúng literal d1.md §27.
- Đổi tên class `PolicyEngine` trùng ở `agents/orchestrator/service.py` — ghi nhận trong bảng trên nhưng để Phase 3a xử lý cùng lúc với gateway unification, không tách task riêng.
- P1-P5 nghiệp vụ (Revenue Engine, Automation Channels, Finance/Legal Ops, Intelligence/Self-improvement) theo `markdown/C3` mục 3-7 — tiếp tục theo roadmap C3 đã có, không lặp lại trong tài liệu này vì không phải trọng tâm "Agent Platform foundation" mà d1.md yêu cầu.
