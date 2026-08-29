# COSA — Điều chỉnh Harness Agent theo FounderStack: Plan triển khai A/B/C

**Nguồn:** `docs/implementation/2026-08-28-cosa-agent-harness-integration-adjustment.md`
**Ngày:** 2026-08-29
**Phạm vi code:** `packages/agent_core`, `packages/agent_integrations`, `apps/cosa`, `services/company/commercial`

---

## Context

Tài liệu 2026-08-28 chuyển các nguyên tắc vận hành agent (chuẩn đầu ra do hệ thống cưỡng chế, một capability gateway duy nhất, handoff có schema/evidence, workflow có cổng deterministic, lỗi thật → regression replay) thành thay đổi cụ thể cho COSA.

Đã verify toàn bộ claim hiện trạng của tài liệu với code thật (3 exploration pass). **Tất cả claim đều đúng** — khác với một số doc cũ trong repo. Các gap đã xác nhận:

| Gap | Bằng chứng |
|---|---|
| `CosaPolicyEngine` trả `ALLOW` mặc định cho capability không khớp rule | `apps/cosa/policies/evaluator.py:151` |
| Gateway không validate output schema | `packages/agent_core/capabilities/gateway.py` (chỉ `validate_input`) |
| `spec.approval_policy` (floor `ALWAYS`) khai báo nhưng không được cưỡng chế | `contracts/capability.py:75`; Gateway không đọc |
| SDK kernel làm mất `workspace_id/principal/context` khi tạo `GatewayExecutionRequest` | `packages/agent_integrations/openai_agents_sdk/kernel.py:179-184` **và** `packages/agent_core/kernel/openai_agents_kernel.py:656-661` |
| Write handler dùng fallback `"default"` | `apps/cosa/capabilities/engagement_message_send.py:61`, `engagement_assignment_write.py:63`, `apps/cosa/api/skill_registry_routes.py` (8 chỗ `or "default_workspace"`) |
| `ToolCallStep` bypass Gateway, gọi thẳng registry handler | `packages/agent_core/workflows/tool_step.py:228-241` |
| Composition dựng WorkflowEngine chỉ với `tool_registry` | `apps/cosa/composition/agent_plane.py:504-506` |
| Support/autopilot eval chấm payload hard-code, không gọi model, không LLM-judge | `apps/cosa/evals/customer_support_copilot_cases.py:48-64`, `customer_support_autopilot_cases.py:54-110` |
| Chưa có failure-replay pipeline / golden-case DB | `packages/agent_core/evals/repositories.py` |
| Chưa có `InvocationContext` / `PreAuthorizationEvidence` | grep = 0 |

**Phần đã có sẵn (chỉ mở rộng, không xây mới):**
- Monotonic governance accumulator: `InvocationGovernanceState.accumulate` + `GovernanceStateStore` durable — `gateway.py:304-321`.
- Approval ledger keyed `(run_id, tool_call_id, checkpoint_ref)`: `RunApprovalRecord` + `DurableApprovalService.get_by_invocation` — `approval_service.py:154-160`.
- Checkpoint + compensation workflow — `workflows/engine.py`.

**Kết quả mong muốn:** high-risk capability không thể execute nếu thiếu workspace/principal/policy context hoặc exact approval; `approval_policy`+`risk` là floor cưỡng chế ở production composition; workflow production chỉ gọi side effect qua `CapabilityGateway`; output schema validate đầy đủ + versioned; support/research có eval thật; failure-replay có review + provenance + promotion gate; sau đó mới pilot connector.

## Quyết định đã chốt (khác doc gốc)

1. **Plan phủ cả A + B + C.** Batch A ở mức thực thi chi tiết; B/C chi tiết vừa (C phụ thuộc điều kiện tiên quyết bên ngoài — terms nhà cung cấp).
2. **`PreAuthorizationEvidence` + API `services/company/commercial` dời từ A sang B.** Batch A: `ApprovalPolicy.ALWAYS` = **luôn `REQUIRE_APPROVAL`, không đường bypass** (fail-closed tuyệt đối). Bypass là tính năng thêm ở B.
3. **Workflow hợp nhất triệt để:** thay hẳn `ToolCallStep` (side-effect) bằng `GatewayToolCallStep`, thống nhất `tool_call_id` scheme sang UUID lưu checkpoint, sửa test workflow bị ảnh hưởng.
4. **Không deadline** → tối ưu theo độ đúng, không cắt góc theo lịch.

Thứ tự batch tuyến tính: **A → B → C** (B cần context+floor của A; C cần eval gate+replay của B).

---

## Batch A — Safety wiring

### A0. Contract `InvocationContext`

**File mới:** `packages/agent_core/contracts/invocation.py`

`InvocationContext` (Pydantic `frozen=True`, có `schema_version`):

| Nhóm | Trường |
|---|---|
| Identity call | `run_id`, `tool_call_id`, `checkpoint_ref` |
| Tenancy | `workspace_id`, `principal`, `conversation_id`, `correlation_id` |
| Policy | `policy_snapshot` (hoặc snapshot ref + version) |
| Provenance | `root_spec_identity`, `capability_identity` |
| Mode | `execution_mode`, `delegation_identity` (nullable) |

Quy tắc: adapter **không được** tự ghép context thiếu trường hoặc dùng fallback workspace.

### A1. Policy floor enforcement trong Gateway

**Files:** `packages/agent_core/capabilities/gateway.py`, hàm thuần mới ở `agent_core`

- Thêm `capability_floor(spec.risk, spec.approval_policy)` + `conjoin(a, b)` — hàm thuần, test độc lập. Đặt ở `agent_core` (không đặt trong `CosaPolicyEngine`).
- `conjoin`: `DENY > REQUIRE_APPROVAL > ALLOW` (lấy mức nghiêm ngặt nhất).
- Trong `Gateway.execute`, sau khi có `tenant_decision` từ `policy_evaluator`: `effective = conjoin(capability_floor(spec), tenant_decision)`.
- `ApprovalPolicy.ALWAYS` → floor `REQUIRE_APPROVAL`; Batch A **không** có nhánh hạ xuống `ALLOW`.
- `ApprovalPolicy.NEVER` không vượt `DENY` / revoked principal / emergency lock / connector grant failure.
- **Bỏ** nhánh substring `"payout"`/`"transfer"` trong `capability_id` làm security boundary (`gateway.py:283-289`) — thay bằng floor dựa `spec` đã đăng ký.
- Fail-closed: `policy_snapshot` không lấy được, hoặc `workspace_id`/`principal` thiếu → write/send/execute trả `failed` (typed), không `ALLOW`.
- Feed `effective` vào `InvocationGovernanceState.accumulate` (đã có).

### A2. `InvocationContext` required + fail-closed tenancy

**Files:** `packages/agent_core/capabilities/gateway.py`, các write handler

- `GatewayExecutionRequest` nhận `context: InvocationContext`.
- Đầu `Gateway.execute`: nếu `spec.risk >= MEDIUM` hoặc `spec` có side effect mà `context.workspace_id`/`context.principal` rỗng → `GatewayExecutionResult(status="failed", failure=TenancyUnresolved)`.
- Low-risk in-memory fixture: giữ optional trong giai đoạn migration; production registry reject capability write khi context không đầy đủ.
- Write handlers — bỏ `or "default"` / `or "default_workspace"`, thiếu workspace → raise typed error:
  - `apps/cosa/capabilities/engagement_message_send.py:61`
  - `apps/cosa/capabilities/engagement_assignment_write.py:63`
  - `apps/cosa/api/skill_registry_routes.py` (8 chỗ: dòng ~93, 319, 365, 408, 471, 510, 538, 590)

### A3. Context propagation qua kernel

**Files:** `packages/agent_integrations/openai_agents_sdk/kernel.py`, `packages/agent_core/kernel/openai_agents_kernel.py`

- Đọc `docs/architecture/adr/ADR-RUNTIME-002` để xác định kernel production; fix cái đó trước, cái còn lại fix hoặc xoá nếu là dead code.
- Sửa `_execute_tool` / `_make_tool` để nhận `InvocationContext` dựng từ:
  - `RunRecord`: `workspace_id`, `principal`, `correlation_id`
  - `RunRequest`: `conversation_id`
  - policy snapshot đang giữ trong run loop
- `context` dict hiện dựng ở `kernel.py:243` nhưng mất ở `kernel.py:149-151` — nối lại chuỗi `run() → _build_tools → _execute_tool → GatewayExecutionRequest`.
- Cả 2 file dựng request chỉ với 4 trường (`kernel.py:179-184`, `openai_agents_kernel.py:656-661`) → thêm `context=InvocationContext(...)`.

### A4. Re-check ngay trước side effect

**File:** `packages/agent_core/capabilities/gateway.py` (ngay trước `handler(...)` ở `gateway.py:458-460`)

- Trích phần "ambient governance re-eval" trong `DurableApprovalService` resume path (`approval_service.py:231-419`) thành hàm dùng chung.
- Gọi cả ở execute path lần đầu **và** resume: policy snapshot còn hiệu lực (chưa emergency lock/revoke), connector grant chưa revoke, thread ownership (với `engagement.*`), human-takeover / kill switch chưa bật. Bất kỳ cái nào fail → fail-closed.

### A5. `GatewayToolCallStep` — workflow hợp nhất

**Files:** `packages/agent_core/workflows/tool_step.py`, `packages/agent_core/workflows/engine.py`, `apps/cosa/composition/agent_plane.py`

- Tạo `GatewayToolCallStep` nhận `CapabilityGateway` (không nhận `tool_registry` cho side-effect step).
- `tool_call_id`: UUID sinh lần chạy đầu, **lưu vào checkpoint**, tái dùng qua retry/resume. Bỏ scheme `f"{run_id}:{tool_name}"` (`tool_step.py:85`) — vỡ khi 1 workflow gọi cùng tool 2 lần.
- Gọi `gateway.execute(GatewayExecutionRequest(context=InvocationContext(...), checkpoint_ref=<step checkpoint>))`. Approval lookup dùng `(run_id, tool_call_id, checkpoint_ref)`.
- `WorkflowEngine.__init__` trong composition (`agent_plane.py:504-506`, hiện chỉ `tool_registry=cap_registry`): inject `gateway`, `policy_engine`, `approval_service`, `governance_store` — **cùng instance** với kernel (`agent_plane.py:443-475`).
- `build_steps_from_spec`: `StepType.TOOL_CALL` → `GatewayToolCallStep`. Pure/compute/transform step giữ đường cũ. Guard compile-time: engine không có gateway mà spec có `TOOL_CALL` side-effect → raise.
- Sửa test giữ nguyên invariant (approval pause; không nới lỏng khi policy đổi giữa pause; compensation `on_failure`):
  - `tests/agent_core/workflows/test_workflow_governance.py`
  - `tests/agent_core/workflows/test_workflow_compensation.py`

### A6. Production-composition tests

**Files:** mở rộng `tests/apps/cosa/test_cosa_plane.py`, `tests/apps/cosa/test_vertical_slice_2_write_approval.py`; test contract `tests/agent_integrations/openai_agents_sdk/test_contract.py`

Test từ `build_cosa_agent_plane`, chứng minh:
1. `engagement.message.send` không gửi trước khi có approval khớp đúng `(run_id, tool_call_id, checkpoint_ref)`.
2. Approval của tool call A không mở tool call B.
3. Request workspace khác → reject.
4. Context không rơi về `"default"` — assert typed failure khi thiếu workspace.
5. Rule disable / human takeover → chặn resume.
6. Cross-process recovery: resume sau restart **process thật** (CLAUDE.md #6 — không tạo instance thứ 2 cùng process).
7. `test_contract.py`: assert `workspace_id`/`principal` từ `RunRequest` tới được handler.

**Exit gate A:** không tồn tại test hay production path nào cho phép high-risk send/write execute khi thiếu workspace, thiếu exact approval, hoặc policy/context unavailable.

**Docs sau A:** `docs/features/capability-gateway.md` (invariant "đường thực thi duy nhất" + test production-composition), `docs/features/workflows.md` (Gateway-only workflow + exact approval identity).

---

## Batch B — Output contract + eval gate

### B1. JSON Schema validator chuẩn

**Files:** `packages/agent_core/contracts/capability.py`, `packages/agent_core/capabilities/gateway.py`, capability registry

- Thay validator primitive tự viết bằng `jsonschema` (Draft 2020-12): `required`, nested object/array, `minItems`, `minLength`, `enum`, `pattern`, `format`, `additionalProperties`.
- Validate **output** trước persistence/idempotency completion. Output invalid → `failed`, không `completed`, không vào idempotency cache.
- Redact output trước khi ghi event/SSE/log (dùng lại util redaction; thêm ở `agent_core` nếu chưa có).
- Publish `schema_version` + `schema_hash` cùng `CapabilityImplementationIdentity`.

### B2. Output contracts

**File:** `packages/agent_core/contracts/` (hoặc `apps/cosa/contracts/`)

| Contract | Trường bắt buộc | Dùng cho |
|---|---|---|
| `SupportDraftV1` | `draft_body`, `intent`, `evidence_refs`, `uncertainty`, `escalation_reason` | Copilot hỗ trợ KH |
| `ResearchBriefV1` | claim, source URL, supporting excerpt, `retrieved_at`, confidence, `insufficient_evidence` | Research/marketing/strategy |
| `ActionProposalV1` | capability, canonical payload hash, policy decision, required approval, rollback/compensation, evidence refs | Mọi đề xuất write/send/execute |

Factual claim không có evidence ref hợp lệ → ép `insufficient_evidence` (enforce ở validator, không ở prompt).

### B3. `PreAuthorizationEvidence` + verification cross-plane

**Files:** `packages/agent_core/contracts/`, `packages/agent_core/capabilities/gateway.py`, `services/company/commercial/*`

- Contract: `id`, `workspace`, `capability_id`, template/version hoặc payload scope, `issuer`, `expiry`, `revocation`, `hash`.
- Endpoint nội bộ `services/company/commercial` (`expose: false`, Encore/TS, có migration nếu cần bảng) xác thực evidence; agent plane gọi qua company client đã có.
- Gateway match: capability + workspace + template/version + payload scope + expiry + revocation + hash — **tất cả** khớp thì `ApprovalPolicy.ALWAYS` mới bypass approval. `template_ref` trong payload tự nó **không** là bằng chứng.
- `conjoin` (từ A1) thêm nhánh: `REQUIRE_APPROVAL` + valid `PreAuthorizationEvidence` → `ALLOW` (chỉ nhánh này, điều kiện chặt).

### B4. Eval thật cho support & research

**Files:** `apps/cosa/evals/*`, `packages/agent_core/evals/*`

- Mỗi scenario: input fixture immutable, context/evidence pin, output contract, deterministic expectations, optional LLM-judge rubric, expected action boundary.
- Runner gọi model/kernel ở test mode có kiểm soát; output qua Gateway giả hoặc dry-run capability, **không gửi ra ngoài**.
- Tách judge "safety/evidence" khỏi judge "voice/usefulness"; không dùng score chung để cho phép write.
- Thay case hard-code: `customer_support_copilot_cases.py:48-64`, `customer_support_autopilot_cases.py:54-110`.
- Golden scenarios: PII, unsupported claim, free-form promise, stale evidence, wrong tenant, duplicate tool call, human takeover.
- Live-provider eval chỉ nightly/staging, không phải điều kiện duy nhất của CI.

### B5. Failure-replay library

**Files:** `packages/agent_core/evals/*`, repository mới, `packages/agent_core/evals/promotion_gate.py`

- Event `accepted`/`edited`/`rejected`/policy denial/tool error/human takeover = tín hiệu đầu vào **không tin cậy**.
- Reviewer chọn → redact PII → freeze fixture → lưu reason code + rubric version → mới promote thành eval case.
- Mở rộng `PromotionGate.check` (`promotion_gate.py:30-54`): thêm bước **replay** affected cases theo fingerprint khi prompt/model/capability/policy/connector đổi, không chỉ so fingerprint. Fail → không promote trigger/write rule.

**Exit gate B:** 100% deterministic safety/tenant/action test pass; 100% factual claim trong corpus có citation hợp lệ hoặc `insufficient_evidence`; không có output contract violation nào persist thành `completed`.

**Docs sau B:** `docs/features/evals.md` (phân biệt conformance test vs output eval/replay; trạng thái repository/persistence).

---

## Batch C — Feedback loop + connector pilot

### C1. Review queue

- Pipeline + UI cho reviewer chuyển feedback/error đã chuẩn hoá thành failure-replay case (nối vào B5).

### C2. Connector pilot (chỉ sau A+B xanh)

| Workload | Capability | Boundary |
|---|---|---|
| Social / FeedHive | `social.post.draft`, `social.post.publish`, `social.analytics.read` | Publish cần approval hoặc pre-auth theo calendar/template; token qua connector grant |
| Support / Aidbase | Mở rộng `engagement.*` | Copilot mặc định artifact-only; autopilot chỉ FAQ/template evidence-bound |
| Link / LinkDrip | `acquisition.link.create`, `acquisition.link.metrics.read`, event ingest | COSA giữ canonical attribution; provider chỉ short-link/tracking |
| Signup / SignupGate | `identity.signup_risk.assess` (read-only) | Không tự block account/chuyển tiền; decision cần human review hoặc rule deterministic đã duyệt |

Điều kiện trước mỗi connector: terms/API nhà cung cấp verify, OAuth/credential qua connector grant, webhook có signature validation + rate limit + idempotency + tenant mapping.

### C3. Dashboard theo spec/version

- pass rate, evidence coverage, policy denial, approval latency, human takeover, duplicate prevention, connector failure, feedback accept/edit/reject.
- Không log raw PII/prompt/evidence vào telemetry.

**Exit gate C:** dashboard đầy đủ theo spec/version; connector pilot chạy trong boundary; không enforcement tự động (block account / giải ngân / hoàn tiền / pháp lý).

**Docs sau C:** `docs/adr/ADR-ENGAGEMENT-AUTOPILOT-PROD-GATE.md` — thay checkbox xác nhận bằng evidence truy xuất được.

---

## Out of scope (giữ nguyên doc §8)

- Clone UI/feature set của FeedHive/Aidbase/LinkDrip/SignupGate.
- Tự gửi social post / tự block account / tự giải ngân / tự hoàn tiền / quyết định pháp lý-tài chính ngoài policy/approval code.
- Dùng prompt như security boundary.
- Chuyển mọi feedback người dùng thành training/eval data tự động, không review/redaction.

## Ma trận test bắt buộc (doc §6)

| Mức | Ví dụ bắt buộc |
|---|---|
| Unit | `ALWAYS` không bị tenant `ALLOW` nới lỏng; (B) pre-auth expired/revoked/wrong template bị reject; (B) schema output invalid fail |
| Gateway | cùng `tool_call_id` resume idempotent; approval khác checkpoint bị reject; connector grant revoke sau approval → không execute |
| Runtime adapter | SDK truyền workspace/principal/policy snapshot không mất trường; tool call identity giữ nguyên |
| Workflow | Workflow không gọi handler trực tiếp; gateway deny/approval/compensation tạo đúng state; recovery đúng process |
| Vertical slice | Customer support free-form message chờ approval; (B) FAQ pre-authorized có evidence thật; takeover/kill switch/stale policy chặn gửi |
| Eval/replay | (B) Model/prompt mới phải fail known-bad cases trước promotion; feedback fixture chỉ tạo sau reviewer/redaction |

---

## Verification end-to-end

**Batch A (blocking, deterministic CI):**
```
# unit floor + conjoin
pytest tests/agent_core/capabilities/ -k "floor or conjoin or governance"
# gateway context + fail-closed tenancy
pytest tests/agent_core/capabilities/test_gateway*.py
# runtime adapter context propagation
pytest tests/agent_integrations/openai_agents_sdk/test_contract.py
# workflow gateway-only + compensation + không nới lỏng khi policy đổi
pytest tests/agent_core/workflows/test_workflow_governance.py tests/agent_core/workflows/test_workflow_compensation.py
# production composition + cross-process recovery
pytest tests/apps/cosa/test_cosa_plane.py tests/apps/cosa/test_vertical_slice_2_write_approval.py tests/apps/cosa/test_tenant_isolation.py
```
Chốt A khi: grep toàn repo không còn `or "default"` / `or "default_workspace"` cho write path; không có path nào execute high-risk khi thiếu workspace/approval/context.

**Batch B:**
```
pytest tests/agent_core/evals/ tests/apps/cosa/evals/
# services/company: sau khi thêm endpoint verify pre-auth
cd services/company && encore test   # hoặc make services-test-company
node scripts/migrate.mjs             # nếu có migration mới
```
Chốt B khi: 100% deterministic safety/tenant/action pass; mọi factual claim trong corpus có citation hợp lệ hoặc `insufficient_evidence`; không có output contract violation persist `completed`.

**Batch C:**
- Dashboard render đủ metric theo spec/version (staging).
- Connector pilot: chạy read/draft trong sandbox nhà cung cấp; publish chỉ sau approval; không có enforcement tự động.
- Kiểm telemetry: không có raw PII/prompt/evidence.

**Toàn bộ:** live-provider test tách khỏi deterministic CI gate (nightly/staging).

---

## File ảnh hưởng chính

| Khu vực | File | Trách nhiệm sau thay đổi |
|---|---|---|
| Contract | `packages/agent_core/contracts/invocation.py` (mới), `contracts/capability.py` | `InvocationContext`, `PreAuthorizationEvidence` (B), schema version/hash |
| Governance | `apps/cosa/policies/evaluator.py` | Tenant policy giữ nguyên; floor sống ở Gateway, fail-closed |
| Gateway | `packages/agent_core/capabilities/gateway.py` | `capability_floor`+`conjoin`, validate input/output (B), re-check trước side effect, audit/redaction |
| Runtime | `packages/agent_integrations/openai_agents_sdk/kernel.py`, `packages/agent_core/kernel/openai_agents_kernel.py` | Không đánh mất execution context/identity |
| Workflow | `packages/agent_core/workflows/{engine,tool_step}.py` | `GatewayToolCallStep`, tool_call_id UUID lưu checkpoint |
| Composition | `apps/cosa/composition/agent_plane.py` | Inject cùng gateway/policy/approval/governance vào runtime **và** workflow |
| Support | `apps/cosa/capabilities/engagement_message_send.py`, `engagement_assignment_write.py`, `apps/cosa/api/skill_registry_routes.py`, `services/company/commercial/*` (B) | Bỏ fallback workspace, typed failure; evidence-bound template auth (B) |
| Evals | `apps/cosa/evals/*`, `packages/agent_core/evals/*`, `tests/*` | Real fixtures, independent grading, replay, release evidence |
| Docs | `docs/features/{capability-gateway,evals,workflows}.md`, `docs/adr/ADR-ENGAGEMENT-AUTOPILOT-PROD-GATE.md` | Cập nhật sau mỗi batch tương ứng |

## Definition of Done (doc §9)

- [ ] High-risk capability không execute nếu thiếu workspace/principal/policy context hoặc exact approval.
- [ ] `approval_policy` + `risk` cưỡng chế như floor ở production composition, không chỉ trong fixture.
- [ ] Mọi write handler fail-closed khi không resolve được tenant scope; không còn fallback workspace cho write.
- [ ] Workflow production chỉ gọi side effect qua `CapabilityGateway`.
- [ ] Capability input/output schema validate đầy đủ, versioned, có test invalid cases.
- [ ] Support và research có eval thật dựa fixture/evidence pin; static self-fulfilling eval bị loại bỏ.
- [ ] Failure replay có review, redaction, provenance, promotion gate theo fingerprint.
- [ ] Toàn bộ test matrix §6 xanh; live-provider test tách khỏi deterministic CI gate.
- [ ] Chỉ sau đó mới pilot connector social/link/signup theo Batch C.
