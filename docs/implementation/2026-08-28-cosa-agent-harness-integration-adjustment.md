# COSA — Điều chỉnh Harness Agent và tích hợp theo mô hình FounderStack

**Ngày:** 2026-08-28  
**Trạng thái:** Đề xuất triển khai — chưa thay đổi runtime  
**Phạm vi:** `packages/agent`, `packages/agent_integrations`, `apps/cosa`, `services/company/commercial`

## 1. Mục đích

Tài liệu này chuyển các nguyên tắc vận hành agent trong nội dung nguồn thành thay đổi cụ thể cho COSA:

1. tiêu chuẩn đầu ra do COSA cưỡng chế, không do model tự nhớ;
2. mọi action có hệ quả đi qua một capability gateway duy nhất;
3. mọi handoff có schema, evidence và provenance rõ ràng;
4. mọi workflow quan trọng có cổng deterministic, approval và recovery;
5. lỗi thực tế được chuyển thành regression replay trước khi đổi prompt, skill hoặc model.

Nguồn tham chiếu sản phẩm là [FounderStack](https://www.founderstack.pro/): FeedHive (social publishing), Aidbase (AI support), LinkDrip (link tracking) và SignupGate (signup/abuse protection). COSA không đặt mục tiêu sao chép bốn sản phẩm này. COSA là control plane và operating system để con người cùng agent vận hành các năng lực đó một cách an toàn, có bằng chứng và có thể kiểm toán.

## 2. Quyết định kiến trúc

### 2.1. Capability policy là ràng buộc cứng

`CapabilitySpec.risk` và `CapabilitySpec.approval_policy` là **sàn an toàn**. Tenant policy chỉ được làm quyết định nghiêm ngặt hơn, ngoại trừ một ngoại lệ đã được đăng ký bằng dữ liệu có cấu trúc.

Thứ tự quyết định cho một invocation là:

```text
current tenant/principal gate
  -> capability policy floor
  -> tenant policy snapshot
  -> authorization evidence cho ngoại lệ hẹp
  -> monotonic governance accumulator
  -> approval / deny / execute
```

Các quy tắc bắt buộc:

- `DENY` luôn thắng mọi quyết định còn lại.
- `ApprovalPolicy.ALWAYS` luôn cho ra `REQUIRE_APPROVAL`, trừ khi có `PreAuthorizationEvidence` còn hiệu lực và khớp đúng capability, workspace, template/version, payload scope và expiry.
- `ApprovalPolicy.NEVER` không thể vượt `DENY`, revoked principal, emergency lock, connector grant failure hoặc requirement an toàn khác.
- Không dùng substring của capability như `"payout"` hoặc một `template_ref` tự do làm security boundary.
- Khi policy snapshot không lấy được hoặc workspace/principal thiếu, mọi write/send/execute phải fail-closed.

Điều này giải quyết mâu thuẫn hiện tại: `engagement.message.send` được khai báo `HIGH` và `ALWAYS`, nhưng `CosaPolicyEngine` trả về `ALLOW` mặc định cho capability không khớp rule payout/transaction. Khi composition truyền evaluator đó vào Gateway, fallback risk-based của Gateway không còn được dùng.

### 2.2. Invocation context là hợp đồng bất biến xuyên suốt

Thêm `InvocationContext` vào `agent.contracts` và bắt buộc đi cùng mọi `GatewayExecutionRequest`:

```text
run_id, tool_call_id, checkpoint_ref
workspace_id, principal, conversation_id, correlation_id
policy_snapshot, root_spec_identity, capability_identity
execution_mode, delegation identity
```

Runtime adapter chỉ được tạo tool intent; adapter không được tự ghép context thiếu trường hoặc dùng fallback workspace. `RealOpenAIAgentsSDKKernel` phải truyền context từ `RunRequest` khi gọi Gateway. Handler write không được dùng `"default"` khi thiếu workspace.

`GatewayExecutionRequest.workspace_id` và `principal` trở thành required đối với capability medium/high risk hoặc bất kỳ capability có side effect. Có thể giữ optional trong giai đoạn migration chỉ cho low-risk, in-memory test fixture; production registry phải reject capability write khi context không đầy đủ.

### 2.3. Schema contract bao gồm đầu vào, đầu ra và evidence

`CapabilityRegistry` phải validate JSON Schema đầy đủ cho input **và** output:

- required, type, nested object/array, `minItems`, `minLength`, enum, pattern, format và `additionalProperties`;
- output invalid biến invocation thành `failed`, không được ghi `completed` hoặc đưa vào idempotency cache;
- output được redaction trước khi ghi event/SSE/log.

Ba deliverable contract đầu tiên:

| Contract | Bắt buộc | Dùng cho |
|---|---|---|
| `SupportDraftV1` | `draft_body`, `intent`, `evidence_refs`, `uncertainty`, `escalation_reason` | Copilot hỗ trợ khách hàng |
| `ResearchBriefV1` | claim, source URL, supporting excerpt, retrieved time, confidence và `insufficient_evidence` | Research/marketing/strategy |
| `ActionProposalV1` | capability, canonical payload hash, policy decision, required approval, rollback/compensation và evidence refs | Bất kỳ đề xuất write/send/execute |

Mọi factual claim không có evidence ref hợp lệ phải được chuyển thành `insufficient_evidence`; model không được tự thay thế evidence bằng câu trả lời tự tin.

### 2.4. Một đường thực thi side effect duy nhất

`CapabilityGateway` là đường thực thi duy nhất cho tool/capability có side effect. `WorkflowEngine` không được gọi handler từ `CapabilityRegistry` trực tiếp.

Thay `ToolCallStep` hiện tại bằng `GatewayToolCallStep` hoặc inject `CapabilityGateway` vào step đó. Mỗi step tạo stable `tool_call_id`, duy trì cùng ID qua retry/resume, rồi gọi Gateway với `InvocationContext` đầy đủ. Approval lookup luôn dùng bộ ba `(run_id, tool_call_id, checkpoint_ref)`, không tìm theo tên action.

Workflow tự do của model chỉ quyết định nội dung trong step được phép. Thứ tự thực thi và cổng chuyển trạng thái nằm trong code:

```text
evidence collected
  -> schema valid
  -> deterministic checks pass
  -> quality/safety eval pass
  -> approval if required
  -> gateway execute
  -> verify result / compensate or complete
```

## 3. Đánh giá hiện trạng và gap cần đóng

| Lớp harness | Có trong COSA | Gap cần đóng |
|---|---|---|
| Eval classifier | `CanonicalEvalRunner`, promotion evidence, eval migrations | Support/autopilot eval hiện kiểm payload hard-code, không chấm output của model hay tool execution thật. |
| Schema contract | `CapabilitySpec.input_schema` và `output_schema` | Registry chỉ kiểm required + kiểu primitive input; Gateway không kiểm output. |
| Least privilege | Capability registry, Gateway, connector grant, tenant policy snapshot, approval ledger | SDK bridge làm mất workspace/principal/context khi tạo gateway request; policy floor chưa được cưỡng chế. |
| Deterministic workflow | DAG, checkpoint, approval, compensation | Composition khởi tạo workflow engine chỉ với tool registry; tool step có thể bypass Gateway. |
| Failure replay | persistence cho eval/promotion, feedback Copilot, drift/durability tests | Chưa có pipeline đưa lỗi/feedback đã review vào golden case và chạy trước promotion. |

Các phát hiện này không phủ định những lớp bảo vệ đã có; chúng xác định nơi wiring hiện tại chưa đạt yêu cầu “company standard is code”.

## 4. Phạm vi triển khai

### 4.1. P0 — bắt buộc trước khi mở autopilot write ở production

1. **Policy floor và pre-authorization có bằng chứng**
   - Sửa `apps/cosa/policies/evaluator.py`, `packages/agent/capabilities/gateway.py` và contracts liên quan.
   - Tạo `PreAuthorizationEvidence` với ID, workspace, capability ID, template/version hoặc payload scope, issuer, expiry, revocation và hash.
   - `engagement.message.send` chỉ bypass approval khi evidence được Company service xác thực; `template_ref` trong payload không tự nó là bằng chứng.

2. **Context propagation và fail-closed tenancy**
   - Sửa `packages/agent_integrations/openai_agents_sdk/kernel.py` để giữ `workspace_id`, principal, conversation, correlation và policy snapshot khi tạo request cho Gateway.
   - Sửa tất cả write handlers để thiếu workspace là lỗi typed; bỏ fallback `"default"`.
   - Re-check policy snapshot, connector grant, thread ownership và human takeover ngay trước side effect.

3. **Gateway-only execution path**
   - Sửa `packages/agent/workflows/tool_step.py`, `packages/agent/workflows/engine.py` và `apps/cosa/composition/agent_plane.py`.
   - Inject `gateway`, `policy_engine`, `approval_service` và durable governance store vào workflow engine; cấm direct handler execute trong workflow production.

4. **Production-composition tests**
   - Test từ `build_cosa_agent_plane`, không chỉ Gateway fixture.
   - Chứng minh message send không gửi trước approval, approval của tool call A không mở tool call B, workspace khác bị reject, context không thể rơi về `default`, và rule disable/human takeover chặn resume.

### 4.2. P1 — biến output quality thành release gate

1. **JSON Schema validator và output contracts**
   - Dùng validator chuẩn thay cho kiểm tra primitive tự viết.
   - Validate output trước persistence/idempotency completion.
   - Publish version/hash của schema cùng `CapabilityImplementationIdentity`.

2. **Eval thật cho support và research**
   - Mỗi scenario có input fixture immutable, context/evidence pin, output contract, deterministic expectations, optional LLM-judge rubric và expected action boundary.
   - Runner gọi model/kernels trong test mode đã kiểm soát; output đi qua Gateway giả hoặc dry-run capability, không gửi ra ngoài.
   - Tách judge “safety/evidence” khỏi judge “voice/usefulness”; không dùng score chung để cho phép write.

3. **Failure replay library**
   - Sự kiện `accepted`, `edited`, `rejected`, policy denial, tool error và human takeover chỉ là tín hiệu đầu vào không tin cậy.
   - Một reviewer chọn, redact PII, freeze fixture và lưu reason code/rubric version trước khi promote thành eval case.
   - Prompt, model policy, capability implementation, policy rule hoặc connector thay đổi phải chạy lại affected cases; fail thì không promote trigger/write rule.

### 4.3. P2 — tích hợp workload của FounderStack bằng connector hẹp

Không xây clone của FounderStack trong COSA. Bổ sung capability/connector sau khi P0/P1 xanh:

| Workload | Capability đề xuất | Boundary |
|---|---|---|
| Social publishing / FeedHive | `social.post.draft`, `social.post.publish`, `social.analytics.read` | Publish cần approval hoặc pre-authorization theo calendar/template; token do connector grant quản lý. |
| AI support / Aidbase | Mở rộng `engagement.*` hiện có | Copilot mặc định artifact-only; autopilot chỉ FAQ/template evidence-bound. |
| Link tracking / LinkDrip | `acquisition.link.create`, `acquisition.link.metrics.read`, event ingest | COSA lưu canonical attribution/evidence; external link provider chỉ làm short-link/tracking. |
| Signup/abuse / SignupGate | `identity.signup_risk.assess` chỉ đọc trước | Không tự block account/chuyển tiền trong phase đầu; decision request cần human review hoặc rule deterministic đã phê duyệt. |

Điều kiện trước khi thêm connector: API/terms của nhà cung cấp được xác minh, OAuth/API credential được quản lý qua connector grant, inbound webhook có signature validation, rate limit, idempotency và tenant mapping.

## 5. Kế hoạch migration theo batch

### Batch A — Safety wiring

- Thêm contracts cho invocation context và pre-authorization evidence.
- Enforce policy floor tại Gateway, giữ monotonic accumulator.
- Propagate context SDK → Gateway → handler; bỏ fallback write workspace.
- Chuyển workflow tool step sang Gateway-only.
- Chạy unit, vertical-slice approval/resume, tenant isolation và cross-process recovery tests.

**Exit gate:** Không tồn tại test hoặc production path nào cho phép high-risk send/write execute khi thiếu workspace, thiếu exact approval hoặc policy/context bị unavailable.

### Batch B — Output contract và eval gate

- Bổ sung validator input/output, `SupportDraftV1`, `ResearchBriefV1`, `ActionProposalV1`.
- Viết golden scenarios cho PII, unsupported claim, free-form promise, stale evidence, wrong tenant, duplicate tool call và human takeover.
- Chạy eval qua kernel/model fake reproducible; live-provider eval chỉ là nightly/staging, không phải điều kiện duy nhất của CI.
- Persist evidence/fingerprint để event trigger proposal/write chỉ enable khi evidence còn fresh.

**Exit gate:** 100% deterministic safety/tenant/action tests pass; 100% factual claim trong corpus có citation hợp lệ hoặc `insufficient_evidence`; không có output contract violation được persisted as completed.

### Batch C — Học từ feedback và connector pilot

- Xây review queue để chuyển feedback/error được chuẩn hóa thành failure replay case.
- Pilot read/draft social connector, sau đó publish với approval.
- Pilot link metrics read; không thực hiện signup enforcement tự động.

**Exit gate:** Có dashboard theo spec/version: pass rate, evidence coverage, policy denial, approval latency, human takeover, duplicate prevention, connector failure và feedback acceptance/edit/reject. Không log raw PII/prompt/evidence vào telemetry.

## 6. Ma trận test bắt buộc

| Mức test | Ví dụ bắt buộc |
|---|---|
| Unit | `ALWAYS` không bị tenant `ALLOW` nới lỏng; pre-authorization expired/revoked/wrong template bị reject; schema output invalid fail. |
| Gateway | cùng `tool_call_id` resume idempotent; approval khác checkpoint bị reject; connector grant bị revoke sau approval thì không execute. |
| Runtime adapter | SDK truyền workspace/principal/policy snapshot không mất trường; tool call identity được giữ nguyên. |
| Workflow | Workflow không gọi handler trực tiếp; gateway deny/approval/compensation tạo đúng state và recovery đúng process. |
| Vertical slice | Customer support free-form message chờ approval; FAQ pre-authorized phải có evidence thật; takeover/kill switch/stale policy chặn gửi. |
| Eval/replay | Model/prompt mới phải fail known-bad cases trước khi promotion; feedback fixture chỉ được tạo sau reviewer/redaction. |

## 7. File ảnh hưởng chính

| Khu vực | File hiện có cần sửa | Trách nhiệm sau thay đổi |
|---|---|---|
| Governance | `apps/cosa/policies/evaluator.py` | Tenant policy và capability floor được hợp nhất, fail-closed. |
| Gateway | `packages/agent/capabilities/gateway.py` | Validate input/output, enforce effective policy, audit/redaction. |
| Contract | `packages/agent/contracts/capability.py`, module invocation mới | Capability schema, pre-authorization và invocation context versioned. |
| Runtime | `packages/agent_integrations/openai_agents_sdk/kernel.py` | Không đánh mất execution context/identity. |
| Workflow | `packages/agent/workflows/{engine,tool_step}.py` | Gateway-only tool step. |
| Composition | `apps/cosa/composition/agent_plane.py` | Inject cùng gateway/policy/approval/governance vào runtime và workflow. |
| Support | `apps/cosa/capabilities/engagement_message_send.py`, `services/company/commercial/*` | Evidence-bound template authorization, ownership re-check, typed failure. |
| Evals | `apps/cosa/evals/*`, `packages/agent/evals/*`, `tests/*` | Real fixtures, independent grading, replay và release evidence. |

## 8. Out of scope

- Clone UI/feature set của FeedHive, Aidbase, LinkDrip hoặc SignupGate.
- Tự gửi social post, tự block account, tự giải ngân, tự xử lý hoàn tiền hoặc quyết định pháp lý/tài chính ngoài policy/approval code.
- Dùng prompt như security boundary.
- Chuyển mọi feedback người dùng thành training/eval data tự động, không có review và redaction.

## 9. Definition of Done

- [ ] High-risk capability không thể execute nếu thiếu workspace/principal/policy context hoặc exact approval.
- [ ] `approval_policy` và `risk` được cưỡng chế như floor ở production composition, không chỉ trong fixture test.
- [ ] Mọi write handler fail-closed khi không resolve được tenant scope; không còn fallback workspace cho write.
- [ ] Workflow production chỉ gọi side effect qua `CapabilityGateway`.
- [ ] Capability input/output schema được validate đầy đủ, versioned và có test invalid cases.
- [ ] Support và research có eval thật dựa trên fixture/evidence pin; hiện tượng static self-fulfilling eval bị loại bỏ.
- [ ] Failure replay có review, redaction, provenance và promotion gate theo fingerprint.
- [ ] Tất cả test matrix ở mục 6 xanh; live-provider test được tách khỏi deterministic CI gate.
- [ ] Chỉ sau đó mới pilot connector social/link/signup theo Batch C.

## 10. Tài liệu cần cập nhật khi triển khai

- `docs/features/capability-gateway.md`: cập nhật claim “đường thực thi duy nhất” bằng invariant và test production-composition thực tế.
- `docs/features/evals.md`: cập nhật trạng thái repository/persistence đang có và phân biệt conformance test với output eval/replay.
- `docs/features/workflows.md`: mô tả Gateway-only workflow execution và exact approval identity.
- `docs/adr/ADR-ENGAGEMENT-AUTOPILOT-PROD-GATE.md`: thay các checkbox xác nhận bằng evidence có thể truy xuất sau khi Batch A/B đạt exit gate.
