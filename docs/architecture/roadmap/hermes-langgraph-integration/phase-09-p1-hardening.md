# Phase 9 — P1 Hardening (+ Full Hermes Implementation: Context, Delegation, Skills, Readiness, Hard-Deny)

> Nguồn gốc: `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` §"Phase 9". Bổ sung Hermes/LangGraph theo `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3 — **phase có khối lượng bổ sung lớn nhất, chia thành 3 track độc lập.**

## Mục tiêu

Đóng các gap còn lại theo P1 của Master doc §43, hoàn tất promote-after-audit cho memory/knowledge/evals — và (mới) implement đầy đủ Track Hermes (context, delegation, skills, readiness, hard-deny) cộng track LangGraph full engineering nếu Phase 6 đã Adopt.

## Điều kiện tiên quyết

Phase 8 xong — có 1 canonical entrypoint sống để các P1 item này có chỗ dùng thật, tránh xây "cho có". ADR-LANGGRAPH đã đóng ở Phase 6 (Adopt/Reject/Defer).

## Việc cụ thể (gốc) — theo thứ tự Master doc §43 P1

1. `WaitDescriptor` routable thật (không chỉ contract Phase 1) — API resolve "ai/cái gì unblock, event nào, resume checkpoint nào" thành hành động thật.
2. Durable workflow definition repository — đóng gap: registry hiện tại (Phase 1) cần thêm persisted immutable definition repository, cross-process load exact definition.
3. `ExecutionTargetSnapshot` full shape — điền đủ field thật từ connector/credential system.
4. `ConnectorGrant` normalization — scope theo tenant/company, principal/agent, account, capability/actions, resource scope, expiry/revocation.
5. Exact-once delegation/fanout: `ExpansionFingerprint` — `source_run_id`, source node/decision/spec revision, expansion semantic key; đảm bảo không tạo sibling tree thứ hai cho cùng fingerprint.
6. Recovery service — chỉ restore liveness (requeue, restore lease, retry same owner, restore provider session, load checkpoint, resume, reconcile idempotent side effect, surface operator action) — KHÔNG tự ý gán quyền cao hơn/switch agent/rewrite ownership/skip approval/resolve spec mới nhất.
7. Low-trust delegation provenance — gắn trust metadata lên external ticket/uploaded doc/web result/review output/agent delegation result/connector content.
8. Budget/run-level gate — budget threshold → deny/pause protected execution mới, optionally cancel safe-to-cancel work; budget là ambient/current, không phải invocation historical accumulator.
9. Artifact lifecycle — artifact provenance (run_id, source inputs, spec identity, creator principal/agent, timestamp, version/hash), `RunResult` chỉ reference artifact record.
10. **Memory/Knowledge PROMOTE-after-audit:** audit coupling ngầm vào `AgentRuntime`/`Executor`/`PermissionLevel` cũ trước khi copy sang `packages/agent/{memory,knowledge}/`. Bổ sung field canonical còn thiếu (tenant scope, ACL, provenance, retention, sensitivity, supersession...).
11. **Evals PROMOTE thẳng:** dùng evals/regression harness hiện có trong `agentos/` làm baseline test suite cho 4 nhóm eval (model/kernel capability, business correctness, durability/recovery, security/governance).

## Test bắt buộc (gốc)

Mỗi mục 1–9 có ít nhất 1 test/case chứng minh, tham chiếu đúng section Master doc tương ứng.

---

## Bổ sung Hermes/LangGraph — Track 9A: Context (full production)

Chỉ implement full nếu Phase 7 đã chứng minh giá trị use case thật (không mở rộng "cho đủ bộ" nếu chưa có consumer thứ 2).

1. Hoàn thiện `apps/cosa/composition/context_assembler.py` (bắt đầu ở Phase 7) — mở rộng số lượng `ContextIntent` được hỗ trợ dựa trên nhu cầu sản phẩm thật đã phát sinh sau Phase 8.
2. Implement `apps/cosa/conversations/repository.py` — database model cho conversation history, dùng contract `ConversationHistoryPort` đã đóng băng ở Phase 8.
3. Implement lexical/full-text search cho conversation — staged retrieval theo supplement gốc §10: structured filters → exact/lexical FTS → optional trigram/fuzzy → semantic retrieval nếu cần → LLM synthesis sau retrieval.
4. **Test bắt buộc (HL-03):** conversation search không leak cross-tenant — 2 tenant riêng biệt, search của tenant A không bao giờ trả kết quả của tenant B dù cùng nội dung message.
5. Nếu progressive disclosure L0-L5 (salvage từ `compiler.py` ở Phase 0) cần hoàn thiện thật: implement L5 (Artifacts/Evidence) còn thiếu, và token rebalancing thật (không chỉ đánh dấu `is_trimmed=True` như bản legacy) — chỉ làm nếu có use case cụ thể cần budget vượt ngưỡng thường xuyên.

## Bổ sung Hermes/LangGraph — Track 9B: Delegation (DelegationEnvelope đầy đủ)

1. Contract đầy đủ (mở rộng từ `coordination/delegate.py` hiện tại — 31 dòng thin wrapper):
   ```text
   DelegationEnvelope: delegation_id, parent_run_id, child_run_id, parent_spec_identity,
                        child_spec_identity, goal, context_snapshot_ref,
                        delegated_capability_ceiling, budget, depth,
                        model_policy_override?, status, created_at, started_at?, completed_at?
   DelegationEvent: delegation_id, event_type (delegation.created|started|steer_requested|
                     cancel_requested|completed|failed), created_at, steer_input?, reason?
   ```
2. **Invariant authority attenuation (BẮT BUỘC test):**
   ```text
   Authority(child) ⊆ Authority(parent) ∩ current governance ∩ current connector grant
   ```
   Effective child authority = delegated capability ceiling ∩ child AgentSpec capability_refs ∩ current PrincipalAuthorization ∩ current TenantPolicy ∩ current ConnectorGrant ∩ current CapabilityGovernance.
3. Durable steer/cancel events — control event phải đi qua child Run input/control channel thật (durable row `DelegationEvent`), **KHÔNG** mutate in-memory Python object.
4. Context isolation mặc định: child chỉ nhận explicit delegated task + selected context (dùng `ContextSnapshot` từ Track 9A) + selected skills/capabilities, không nhận toàn bộ parent transcript.
5. Return boundary mặc định: parent nhận structured result + summary + artifacts + citations + status, không nhận mọi child internal model/tool event (trace chi tiết vẫn inspectable qua observability).

**Test bắt buộc:**
- HL-06: child capability set không vượt trần dù child AgentSpec khai báo rộng hơn.
- HL-07: revoke connector/principal permission ở giữa chừng → child execution sau đó bị chặn.
- HL-08: child Run restart resume đúng execution đã pin, không duplicate side effect.

## Bổ sung Hermes/LangGraph — Track 9C: Readiness (full implementation)

Mở rộng từ minimum enforcement đã có ở Phase 4:

1. Connector health check thật (network/API call tới connector, không chỉ kiểm tra config tồn tại).
2. Credential TTL/expiry tracking.
3. Dependency readiness (capability phụ thuộc capability khác chưa sẵn sàng).
4. Cache ngắn hạn cho readiness — chỉ cache technical health, KHÔNG BAO GIỜ cache/reuse stale authorization (invariant từ supplement gốc §18.2).

## Bổ sung Hermes/LangGraph — Track 9D: SkillSpec (publication only, KHÔNG execution)

1. `packages/agent/skills/`:
   ```text
   contracts.py    — SkillSpec (id, version, definition_hash, description, instructions,
                      applicability, required_capabilities, required_knowledge, references,
                      provenance, publisher, status: DRAFT|CANDIDATE|EVALUATED|APPROVED|PUBLISHED|RETIRED)
   registry.py      — load/publish immutable version
   candidates.py    — SkillCandidate (parent_run_id, parent_outcome, candidate_skill, evidence_refs, eval_result)
   evaluation.py    — eval pipeline cho candidate
   publication.py   — publish lifecycle, chỉ tạo version mới, KHÔNG mutate version cũ
   ```
2. Progressive disclosure L0-L2 (đúng tinh thần Hermes): L0 = skill index (id/name/description/tags), L1 = selected SkillSpec instructions, L2 = referenced examples/templates loaded on-demand.
3. **Giới hạn quan trọng — KHÁC supplement gốc §15/§25:** publication được phép, nhưng **cấm runtime consumption qua floating reference** cho tới khi có ADR-SKILL-IDENTITY (Phase 10). Nghĩa là: một Run đang chạy KHÔNG được resolve `skill_ref: "finance-close"` (tên không version) — kể cả trong cùng một Run pause/resume, không chỉ trường hợp child-inherit. Nếu AgentSpec có `skill_refs` field (đã thêm placeholder ở Phase 1), field này giữ rỗng cho tới khi ADR-SKILL-IDENTITY xong.

**Test bắt buộc:**
- HL-04: chỉ index (L0) load global; đúng version skill đã chọn mới load full instructions.
- HL-05: publish SkillSpec v2 không ảnh hưởng Run đang chạy dùng v1 (vì runtime consumption qua floating ref bị cấm, invariant này gần như tự động đúng — vẫn cần test tường minh).

## Bổ sung Hermes/LangGraph — Track 9E: Hard Non-Approvable Safety Floor

1. Thêm policy level `NON_APPROVABLE` vào governance, dominate cả approval evidence lẫn autonomy level:
   ```text
   Hard Deny > Current Governance > Approval Evidence > Autonomy Level
   ```
2. Domain examples ban đầu (cần xác nhận với người dùng trước khi hardcode — đây là quyết định chính sách, không phải kỹ thuật thuần): disable_audit, export_all_secrets, delete_tenant, mutate_governance, transfer_ownership.

**Test bắt buộc:**
- HL-10: action `NON_APPROVABLE` vẫn bị deny dù có approval evidence hợp lệ và autonomy level cao nhất.

## Bổ sung Hermes/LangGraph — Track 9F: LangGraph Full Engineering (điều kiện: ADR-LANGGRAPH = Adopt)

**Chỉ thực hiện nếu Phase 6 quyết định Adopt.** Nếu Reject: bỏ qua track này, thay bằng việc áp dụng ý tưởng supersteps/reducer/pending-writes/state-context-separation vào WorkflowEngine native (đã build ở Phase 1) ngay trong track này.

- Nếu **Adopt**: merge `experiment/langgraph-spike` vào main, migrate cẩn trọng các workflow usage hiện tại từ WorkflowEngine native sang LangGraph runtime (không big-bang một lần), full compiler/checkpoint persistence production-grade.
- Nếu **Reject**: implement trực tiếp vào `packages/agent/workflows/engine.py`:
  - superstep execution (tách rõ PLAN/EXECUTE/UPDATE thay vì `asyncio.gather` đơn giản hiện tại);
  - reducer-based writes cho parallel branch thay vì shared dict mutation ngầm định;
  - pending-write durability (partial parallel success → successful branch results persist, recovery chỉ retry phần fail);
  - State vs Context separation tường minh hơn (đã có contract từ Phase 1, giờ thực thi trong engine thật);
  - checkpoint ancestry (parent checkpoint links) và Run fork semantics cơ bản.

## Definition of Done — Phase 9

**Gốc:**
- Mỗi mục 1–9 (gốc) có ít nhất 1 test/case chứng minh, tham chiếu đúng section Master doc tương ứng.
- Memory/Knowledge đã promote vào `packages/agent/`, pass toàn bộ test cũ + audit coupling document hóa trong `agentos_salvage_inventory.md`.
- 4 nhóm eval chạy được như 1 suite, dùng baseline từ `agentos/` evals cũ.

**Bổ sung (theo track, chỉ áp dụng track đã kích hoạt thật):**
- Track 9A: HL-03 pass (no cross-tenant leakage).
- Track 9B: HL-06, HL-07, HL-08 pass.
- Track 9C: readiness full implementation có test connector health thật, credential TTL, không cache authorization.
- Track 9D: HL-04, HL-05 pass; `skill_refs` field trong AgentSpec vẫn giữ rỗng/không dùng cho execution.
- Track 9E: HL-10 pass; danh sách `NON_APPROVABLE` domain đã được người dùng xác nhận.
- Track 9F: (nếu Adopt) HL-11→HL-18 pass full trên main branch; (nếu Reject) supersteps/reducer/pending-writes đã implement trong WorkflowEngine native với test tương ứng.

## Rủi ro/lưu ý

**Gốc:** Phạm vi P1 rộng — làm tuần tự theo đúng thứ tự liệt kê, không song song hóa nhiều mục cùng lúc vì một số mục phụ thuộc lẫn nhau (vd. budget gate cần recovery service đã có khái niệm "safe-to-cancel").

**Bổ sung:** Phase này là nơi dễ scope-creep nhất trong toàn bộ integration — 6 track (9A-9F) đều hấp dẫn để làm "cho đủ". Kỷ luật bắt buộc: mỗi track chỉ implement phần đã có consumer/use case thật từ Phase 7-8, không implement "vì roadmap liệt kê". Đặc biệt Track 9D (Skills) — publication được phép nhưng execution consumption vẫn bị khóa cho tới ADR-SKILL-IDENTITY; đừng để áp lực "SkillSpec đã publish rồi, dùng luôn cho tiện" phá vỡ gate này.
