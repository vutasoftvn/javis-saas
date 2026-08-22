> **[ARCHIVED 2026-08-22]** Tài liệu này đã lỗi thời, được di chuyển vào `_archive/` để không gây nhầm lẫn khi tìm kiếm. Tham khảo tài liệu hiện hành: `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`, `docs/architecture/adr/ADR-012-legacy-backend-agentos-services-integration-plan.md`, và các ADR mới nhất trong `docs/architecture/adr/`. Nội dung gốc giữ nguyên bên dưới để tra cứu lịch sử.

# COSA — Current Architecture (code-verified)

**Ngày lập:** 2026-08-17
**Phương pháp:** Đọc trực tiếp code (`backend/app`, `frontend/lib`), grep xác nhận call site thật, không suy đoán từ tài liệu markdown. Chéo kiểm với `markdown/C1-C2-C3` (2026-08-16) và cập nhật những điểm đã lệch pha kể từ commit `4da4b7f`.
**Phạm vi:** Đáp ứng yêu cầu audit của `markdown/d1.md` §77/§88 — xác định chat entrypoint, websocket/streaming, agent code, prompt location, project logic, tools, integrations, authentication, authorization, models/providers, database tables, LiveKit, n8n, Claude Code integration, sandbox, tests.

---

## 1. Chat entrypoint

- Route: `backend/app/main.py:137` mount `chat.router` tại `/api/v1/chat` (`backend/app/modules/chat/router.py`).
- Message submit: `POST /{brain_id}/sessions/{session_id}/messages` (`router.py:375-437`) — lưu message, gọi `notify_user_message_submitted()` để đánh thức worker async.
- Đọc kết quả: `GET .../stream` (`router.py:156-258`) dùng `EventSourceResponse` (SSE) — **không phải WebSocket**.
- Xử lý turn thật: `backend/app/modules/chat/chat_execution_service.py::_execute_turn()` (dòng 276).

### 1.1 Conversation Gate — intent-before-context (đã đúng invariant)

`backend/app/modules/chat/conversation_gate.py`:
- `resolve(text)` → `GateDecision(intent, verb, needs_project, needs_tools, allowed_namespaces, route, should_route)`.
- `SOCIAL_GREETING_PATTERNS` (dòng 53-60) khớp "chào", "hi"... → trả ngay `GateDecision(needs_project=False, needs_tools=False, allowed_namespaces=frozenset(), route="chat_llm")` (dòng 106-120).
- Đã có `CanonicalVerb` enum (dòng 16-22): `CONVERSE / SHAPE / INVESTIGATE / JUDGE / EXECUTE / FINISH / LEARN` — map trực tiếp từ `GateDecision`.
- `chat_execution_service.py:355-356`: nếu `gate_decision.needs_project=False` → bỏ qua vault/RAG retrieval; `_tools_for(..., allowed_namespaces=frozenset())` (dòng 378-382) → `company_tools.tool_specs()` lọc **toàn bộ** tool project/CRM/finance ra khỏi danh sách khả dụng cho LLM.
- Lớp nền: `backend/app/modules/company_runtime/intent_classifier.py::WorkIntentClassifier` — được `conversation_gate.resolve()` gọi làm base classifier (dòng 104), hợp lệ (layering có chủ đích, không phải trùng lặp).
- **Kết quả xác nhận: "Chào" hôm nay đã không kích hoạt bất kỳ project/CRM/finance tool nào** — đúng mục tiêu cốt lõi §6/§9 của d1.md, đã triển khai xong, có test (`backend/app/tests/chat/test_conversation_gate.py`).
- Ghi chú kỹ thuật: biến `gate_enabled` (dòng 339, đọc từ `FLAG_CONVERSATION_GATE_V13_2`) được tính nhưng không dùng lại — gate luôn chạy bất kể flag, không phải bug chức năng nhưng flag hiện vô nghĩa.

### 1.2 Fragment thứ 2 và thứ 3 của "Intent Router"

- `backend/app/agents/control_plane/intent.py::IntentClassifier` (CHAT/QUERY/COMMAND/GOAL/EVENT) — **không mount trong `main.py`**, chỉ có caller trong chính package `control_plane` (`__init__.py`, `router_api.py`) và 1 test (`test_control_plane.py`). Không phải đường sản xuất.
- `backend/app/core/function_router.py` — bộ phân loại phòng ban (LEGAL/MARKETING/SALES/TECH/FINANCE) theo keyword-score, tiện ích nhỏ độc lập, không phải Intent Router.

---

## 2. Websocket / Realtime streaming (LiveKit)

- **Không có endpoint WebSocket nào** trong `backend/app` (`grep -rln "@.*\.websocket("` = rỗng).
- `backend/app/modules/realtime/` (`router.py`, `provider.py`, `token_service.py`, `transport_resolver.py`, `tools.py`) mount tại `/api/v1/realtime` (`main.py:152`).
- `POST /sessions` (`router.py:58-120`) tạo `RealtimeSession`, resolve transport local/cloud, mint LiveKit token qua `generate_livekit_token()`. Client Flutter kết nối **trực tiếp tới LiveKit server** bằng token này — không đi qua FastAPI nữa.
- `/health` (`router.py:174-188`) báo trạng thái `LIVEKIT_URL/API_KEY/API_SECRET` + `GOOGLE_API_KEY` (cho voice agent).
- **Realtime là đường tách biệt hoàn toàn khỏi `chat_execution_service.py`** — không qua Conversation Gate/orchestrator loop. Voice traffic chạy trên WebRTC/WS riêng của LiveKit.
- Frontend: `frontend/lib/modules/realtime_voice/data/livekit_realtime_session_gateway.dart`, `.../voice_session_controller.dart`.

---

## 3. Agent code (`backend/app/agents/`)

| Thư mục | Vai trò thật | File chính |
|---|---|---|
| `registry/` | Agent Registry (Python dataclass, không DB) | `presets.py::AGENT_PRESETS` (6 agent: chief_of_staff, sales_specialist, finance_specialist, data_analyst, researcher, coding_agent) |
| `orchestration/` | Mission Orchestrator (chief-of-staff) | `chief_of_staff.py::ChiefOfStaffOrchestrator.orchestrate` (53-435) |
| `orchestrator/` | Deterministic chat/voice command router riêng | `service.py::WorkOrchestratorService` (có `PolicyEngine` riêng, trùng tên với `governance/policy_engine.py`) |
| `control_plane/` | Goal→Plan→Step engine (gần nhất với "graph workflow") | `execution.py::ControlPlaneExecutionManager.execute_step` (30-433, gateway-mediated đúng chuẩn), `planner.py::GoalDecomposer`, `router.py::DomainCapabilityRouter` |
| `governance/` | Policy/Approval/Audit/Budget/Stuck/QualityGate | `kernel.py::GovernanceKernel`, `policy_engine.py`, `approval_service.py`, `budget.py`, `stuck_detector.py`, `quality_gate.py`, `models.py` |
| `capabilities/` | Capability Gateway (catalog + risk + grant) | `service.py::CapabilityGateway`, `registry.py::CAPABILITY_CATALOG` (~35 capability L0-L5) |
| `execution/` | Sandbox execution | `manager.py`, `service.py::run_execution_job` (gateway-mediated), `policies.py::SandboxPolicy`, `adapters/opensandbox.py` |
| `verification/` | Reality Verifier | `reality_verifier.py::RealityVerifier` |
| `domains/{sales,finance,marketing,legal,learning}/` | Business logic thuần (research/data/reasoning/communication/action/evaluation) | gọi **chỉ** từ `control_plane/execution.py` sau khi gateway check pass |
| `reliability/` | Model Gateway #1 + resilience | `model_gateway.py::ModelGateway`, `model_profiles.py::ModelProfileRegistry`, `reliability.py` |
| `context/` | Context priming cho agent | `builder.py::build_agent_context` |
| `events/` | Event publish | `agent_event_bus.py::publish_agent_event` |
| `proposals/` | Human-review-gated mutation | `service.py::AgentProposalService` |
| `jobs/` | Job dispatch binding | `job_router.py::route_to_job` |
| `skills_library/` | Skill manifest (SKILL.md) | `resolver.py::SkillResolver` (mới có sales/marketing) |

---

## 4. Prompt location

- Registry thật: `backend/app/ai/prompt_registry.py::PromptRegistry` — load `backend/app/prompts/**/*.md` (29 file, domain: `sales/quality/cosa/marketing/finance/legal`), sha256 versioning, `render()`/`render_effective()` (override qua `protected_resources`), candidate lifecycle `register_candidate → record_candidate_eval → promote_candidate` (bắt buộc `approved_by_user_id`, dòng 231-235).
- Backing store cho admin-edit/versioning: `backend/app/core/protected_resources/` — generic versioned resource (revision-0-là-default, checksum, reset-to-default, audit-logged) — dùng chung cho prompt/spec/skill/policy.
- **Ngoại lệ hardcode**: `backend/app/agents/orchestration/chief_of_staff.py::_build_synthesis_prompt` (327-336) là f-string trực tiếp, không qua `PromptRegistry`.

---

## 5. Project logic / Company context loading

- `backend/app/modules/company_runtime/` — mọi service nhận `workspace_id` tường minh, lọc DB theo đó (vd `tools.py:43-45,78`).
- `backend/app/modules/organization/service.py::bootstrap_organization` scoped theo `workspace_id`.
- Context **lazy-load theo intent**: `_tools_for()` chỉ trả tool spec theo `allowed_namespaces`; dữ liệu thật (project/CRM/finance) chỉ fetch khi LLM thật sự gọi tool trong vòng lặp `MAX_TOOL_ROUNDS` (`chat_execution_service.py:431-502`).

---

## 6. Tools / Tool Registry

- `backend/app/core/tool_registry.py::ToolSpec` + `@register()` decorator + `_registry` dict — in-process, **không** có bảng `tool_definitions`. Có field `risk_level`, `permission_level`, `requires_approval`, `allowed_agent_keys`, và (từ commit gần nhất) `mutating: bool`, `external: bool`.
- Dispatch an toàn: `backend/app/core/tool_dispatch.py::execute_tool_spec` — strip `workspace_id`/`user_id` do model tự đưa vào.
- **2 caller khác nhau về mức độ mediation:**
  - `agents/runtime/tool_bridge.py` → **có** gọi `GovernanceKernel.evaluate_and_audit_tool_call` trước dispatch (đúng chuẩn).
  - `modules/chat/company_tools.py:109` → gọi `execute_tool_spec` **trực tiếp**, không qua gateway nào (tự ghi chú trong docstring của `tool_registry.py:109-112`).

---

## 7. Integrations

### 7.1 n8n
- `backend/app/automations/runtime/adapters/n8n.py::N8nAdapter` — HMAC-SHA256 signed webhook calls tới n8n instance khách hàng tự host. n8n = **executor**, không phải brain.
- `backend/app/agents/execution/n8n_bridge.py` — signed callback dispatch từ agent execution layer.
- `backend/app/modules/integrations/n8n_gateway_service.py::dispatch_n8n_workflow` — check `risk_level`/`approval_mode` trước khi dispatch, tạo `AutomationRun`.
- REST: `backend/app/automations/router.py` (`/health`, `/definitions`, `/execute`, `/callback`, `/runs/{id}`).
- Không có cron/scheduler nội bộ — scheduling là trách nhiệm của n8n.

### 7.2 Claude Code / Developer Agent
- `backend/app/agents/execution/coding_agent_provider.py::ClaudeCodeLandingProvider` — build prompt + shell commands, queue vào `ExecutionJob` pipeline (**đi qua sandbox `opensandbox`**, không shell trực tiếp).
- `desktop_worker/main.py` (top-level, 57 dòng) — FastAPI chạy **trên máy dev**, bind `127.0.0.1:8765` (loopback only). `/execute-task` (30-51) chạy `subprocess.run(cmd, shell=True, cwd=..., timeout=...)` **trực tiếp trên host filesystem/shell — KHÔNG sandbox**. Chỉ được bảo vệ bằng network scope (loopback) + device-token auth ở backend. Đây là **con đường Claude Code thật sự chạy** khi trigger từ `backend/app/modules/devices/router.py` (device job model: enroll → create job → claim → submit-results, auth qua `get_current_device`).
- **Kết luận quan trọng**: có 2 con đường "code execution" khác nhau trong repo — (a) `agents/execution/adapters/opensandbox.py` (sandbox thật, ephemeral container) cho `ExecutionJob` nói chung, và (b) `desktop_worker/main.py` (không sandbox, host thật) cho Claude Code cụ thể. d1.md nguyên tắc #16 ("Code execution phải qua sandbox") **chưa đúng cho path (b)**.

---

## 8. Authentication / Authorization

- `backend/app/core/auth.py`: `get_current_user` (JWT bearer, dòng 12) → `get_current_workspace_member` (dòng 33, 403 nếu không có `WorkspaceMember` khớp `workspace_id`) — dependency chuẩn cho mọi route chat/realtime. `get_current_device` (50-76) — device-token riêng cho worker plane, không dùng JWT user.
- `backend/app/core/authz.py::authorize(member, action, resource)` (dòng 51) — RBAC cho **protected actions** (sửa prompt/spec/skill/policy, cấu hình agent/tool, quản lý nhân sự): `owner(4) > admin(3) > editor/member(2) > viewer(1)`. `prompt.update`/`prompt.reset` yêu cầu `owner` (45-48).
- `backend/app/core/tenancy.py` — helper `get_*_scoped()` chống IDOR xuyên tenant (đã có ghi chú trong code về 1 bug cross-tenant từng xảy ra ở `vault.py`).

---

## 9. Models / Providers (2 Model Gateway song song, chưa hợp nhất)

- **Gateway #1** (generic, agent runtime): `backend/app/agents/reliability/model_gateway.py::ModelGateway.invoke` — retry + circuit breaker + fallback provider. `model_profiles.py::ModelProfileRegistry`: `chat_fast/reasoning/extraction/local_embedding` → deepseek/anthropic/openai/local + cost per 1k token.
- **Gateway #2** (DSPy-only): `backend/app/ai/model_policy/dspy_lm_factory.py::DSPyLMFactory.get_lm` — policy-name→provider/model riêng (fast/deep_reasoning/creative → deepseek).
- Provider adapter thô: `backend/app/integrations/{anthropic,deepseek,gemini,openai,openrouter}_client.py`, `_openai_compatible.py`.

---

## 10. Database tables (tên thật, không phải giả định của d1.md)

| Khái niệm | Bảng/Model thật |
|---|---|
| Agent runs | `agent_runs` (`AgentRun`, có `outcome_run_id` FK → `outcome_runs.id`) |
| Agent audit events | `agent_events` (`AgentEventRecord`) |
| Tool-call audit | `agent_tool_calls` (`AgentToolCall`) |
| Approvals | `agent_approvals` (`AgentApproval`) |
| Goal/Plan/Step | `agent_goals`, `agent_plans`, `agent_plan_steps` |
| Agent memory | `agent_business_memories` (`AgentMemoryItem`) + mem0 tables riêng |
| Proposals | `agent_proposals` (`AgentProposal`) |
| Capability grants | `capability_grants` (`CapabilityGrant`) |
| Sandbox jobs | `execution_jobs`, `execution_steps`, `sandbox_policies` |
| Prompt/spec/skill versioning | `protected_resources`, `protected_resource_revisions` (generic, không phải bảng prompt riêng) |
| Generic audit | `audit_logs` (`AuditLog`, `modules/platform/models.py`) |
| Mission Ledger (rộng nhất) | `outcomes/outcome_runs/run_steps/run_events/artifacts` (`modules/outcomes/models.py`, dùng bởi ~15 module khác) |

**Không tồn tại**: `agent_definitions`, `tool_definitions`, `agent_tool_permissions`, `prompt_templates`/`prompt_versions` như d1.md §13/§15/§33 giả định — Agent/Tool Registry là Python in-process, Prompt Registry dùng file + `protected_resources`.

Toàn bộ model agent-platform dùng `SnowflakeIDMixin`/`generate_snowflake_id()` — đúng chuẩn CLAUDE.md, đã verify 23+ occurrence.

---

## 11. Sandbox

- Thật: `backend/app/agents/execution/adapters/opensandbox.py` — SDK `opensandbox`, `Sandbox.create/commands.run/files.write_files/destroy`, ephemeral container.
- `backend/app/agents/execution/policies.py::SandboxPolicy` — preset theo domain (`safe_analysis/research/marketing/finance/coding`), `network_default="deny"`, allowlist command/fs, override qua `SandboxPolicyRecord` per workspace.
- `backend/app/agents/execution/service.py::run_execution_job` — gateway-mediated đúng chuẩn: `CapabilityGateway.check(capability="code.execute", permission_profile="l3_execute")` trước khi tạo sandbox, resolve credential qua `CredentialBroker` (không lộ cho LLM), luôn `destroy()` trong `finally`.
- **Ngoại lệ**: `desktop_worker/main.py` (mục 7.2) — không sandbox.

---

## 12. Tests

- `backend/app/tests/` — cấu trúc theo module, không phải 1 thư mục `routers/agents/permissions` phẳng: `agents/` (execution_contract, runtime_contract), `automations/`, `chat/` (`test_conversation_gate.py`, `test_model_gateway_and_apiai.py`), `company_runtime/` (10 file), `finance/`, `governance/`, `integrations/`, `realtime/`, `sales/`.
- Test riêng cho platform: `test_p0_intent_router.py`, `test_architectural_invariants.py` (318 dòng), `test_tool_registry.py`, `test_agent_memory_claude_code_capture.py`, `test_p3_automation_gateway.py`, `test_p2_revenue_engine.py`, `test_devices.py`.
- **`test_p0_memory_layers.py` không tồn tại** (khoảng trống test duy nhất còn ghi nhận từ PHASE_0 plan).

---

## 13. Frontend

- `frontend/lib/modules/chat/` gọi qua `ApiClient` (`data/services/chat_service.dart`), không HTTP trực tiếp.
- Xác nhận sạch legacy reference: `rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib` → **0 kết quả** (đúng rule CLAUDE.md).
