# General Counsel Legal Profile + Executive Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`) and execute tasks in order.

**Goal:** Bổ sung `legal` functional profile qua Legal Issue Dossier Project-bound và mở `gc` advisor để issue-spotting/escalation, không tạo tư vấn pháp lý có thẩm quyền hay thay đổi Company legal records.

**Architecture:** Finance-Legal remains business truth for legal entity/applicability. A Company Operations dossier holds only Project-scoped questions, applicable-record references, risk category, provenance and Founder decision status. Legal profile reads the redacted snapshot; GC is capability-empty and labels every output “not legal advice; seek qualified counsel”.

**Tech Stack:** Company Finance-Legal + Operations, Python registry/capability, contracts/generators, skillpacks, Flutter, Vitest/pytest/process E2E.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`.

## Global Constraints

- GC cannot create/alter legal entity, sign/approve a contract, set legal applicability, file/regulator-contact, retain counsel or make a legal conclusion. Existing finance-legal services remain authoritative.
- Do not project contract bodies, personal data or privileged advice; retain a classification, source reference, jurisdiction/applicability status and redacted question only.
- `legal`/`gc` are READY only when source reference integrity and tenant/project E2E pass; missing applicability is an explicit unknown/escalation.

## File structure

| Unit | Files |
| --- | --- |
| Dossier | `services/company/operations/{migrations,services,handlers,tests}/legal-issue-dossier.*` |
| Read/profile | `apps/cosa/capabilities/legal_issue_read.py`, agent specs/maps/seed, Company `ai-member.service.ts` |
| Catalog/skill | shared contracts/generators, `013_legal_startup_profile.*`, `skillpacks/executive/gc-advisor/**` |
| Proof | Board/Hologram Hub tests, `tests/e2e/test_gc_legal_profile.py` |

### Task 1: Add a non-authoritative Legal Issue Dossier

**Files:** Create listed Operations migration/service/handler/tests; use existing Finance-Legal read service, not SQL cross-schema access.

**Interfaces:** `createLegalIssueDossier(ctx, {projectId, issueCategory, legalRecordRefs, redactedQuestion})`; `readLegalIssueSnapshot(ctx, projectId)` returns `{revision, issueCategory, applicabilityStatus, sourceRefs}`.

- [ ] **Step 1: Write failing authority tests**

```ts
it("rejects foreign/legal-body input and cannot change legal applicability", async () => {
  await expect(createLegalIssueDossier(foreignCtx, draft)).rejects.toMatchObject({ code: "permission_denied" });
  await expect(createLegalIssueDossier(ctx, { ...draft, contractBody: "private" } as never)).rejects.toMatchObject({ code: "invalid_argument" });
});
```

- [ ] **Step 2: Implement append-only reference record and green run**

```bash
cd services/company && npx vitest run operations/tests/legal-issue-dossier.test.ts finance-legal/tests/legal-applicability-integrity.test.ts && npm run typecheck
```

Validate referenced legal records through a service port, maintain CAS/audit and surface unavailable applicability as an explicit state.

- [ ] **Step 3: Commit**

```bash
git add services/company/operations services/company/finance-legal && git commit -m "feat(legal): add project legal issue dossier"
```

### Task 2: Register read-only Legal and GC specs

**Files:** Create `legal_issue_read.py` and tests; modify agent registry/map/seed and Company mappings/tests.

**Interfaces:** `legal.issue.read`; `cosa.agents.legal@1.0.0/L1_PROPOSE`; `cosa.executive.gc@1.0.0/L1_PROPOSE` capability-empty.

- [ ] **Step 1: Red test**

```python
async def test_legal_profile_has_no_write_and_gc_has_no_capability(gateway):
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.gc"].capability_refs == []
    with pytest.raises(CapabilityDenied): await gateway.execute(legal_request(project_id="foreign"))
```

- [ ] **Step 2: Implement pins and commit**

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest apps/cosa/tests/test_legal_profile.py -v
cd services/company && npx vitest run operations/tests/ai-member.test.ts
git add apps/cosa services/company/operations && git commit -m "feat(legal): add pinned Legal and GC specs"
```

### Task 3: Catalog/skill/activation release proof

**Files:** shared contracts/generators/tests; `013_legal_startup_profile.{up,down}.sql`; GC skillpack; Board/Flutter/E2E tests.

- [ ] **Step 1: Red E2E**

```python
async def test_gc_requires_active_legal_and_never_resolves_unknown_applicability(client):
    assert (await client.activate_role("gc", legal_template)).code == "LEGAL_PROFILE_NOT_ACTIVE"
    assert (await client.deliberate("gc", unknown_applicability)).code == "LEGAL_EVIDENCE_REQUIRED"
```

- [ ] **Step 2: Implement and verify**

Set `legal: TEMPLATE/READY`, `gc: READY`; generator enforces pairing; migration is template-only with active/frame-referenced down guard. Skill requires jurisdiction/source/revision and legal-counsel caveat. Flutter maps/reloads Company truth.

```bash
node scripts/gen-startup-team-profiles.mjs && node scripts/gen-executive-advisor-roles.mjs
make contracts-check && make skillpacks-validate && make services-test-company
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_gc_legal_profile.py -v
git add shared/contracts scripts services/company/operations apps/cosa skillpacks/executive/gc-advisor frontend tests/e2e
git commit -m "feat(executive-board): activate GC advisory path"
```

## Known limitations (post-final-review)

Ghi lại chủ động ngay trong Task 3 (không đợi final review nhắc lần thứ ba —
CHRO's plan bị dinged Important vì thiếu mục này, CISO's plan bị dinged lại
CHÍNH XÁC cùng lỗi ở plan kế tiếp). Các điểm sau là giới hạn đã biết, KHÔNG
phải bug được fix trong task này (mỗi điểm cần plan riêng hoặc quyết định
portfolio-wide theo đúng quy tắc CLAUDE.md "nhiều bước → viết plan trước khi
sửa code").

- **Read capability HTTP auth unreachable — cùng giới hạn dùng chung với
  CPO/CHRO/CISO, không phải gap riêng của role này.** Lời gọi của
  `legal.issue.read` sang Company được xác thực bằng header COSA-delegation
  "ambient", nhưng `readLegalIssueSnapshotEndpoint` được bảo vệ bởi
  `requireWorkspaceAccess` — hàm này chỉ chấp nhận session token ký bằng
  `JWT_SECRET` của người dùng thật, không chấp nhận COSA-delegation token
  (đã verify trực tiếp bằng test "rejects a COSA-delegation-signed token
  before any TenantContext is built" trong `legal-issue-dossier.test.ts`).
  Cùng gap portfolio-wide đã ghi trong known-limitations của
  `product_decision_read.py`/`people_risk_read.py`/`security_posture_read.py`,
  không phải lỗi mới phát sinh riêng ở đây.

- **`ctx` không bao giờ mang `project_id` trong pipeline invocation thật.**
  Đã verify trực tiếp: `apps/cosa/worker/copilot_run.py` build `ctx` (dòng
  242-247) chỉ với `workspace_id`, `run_id`, `delegation_token`, `token` —
  mặc dù `project_id` CÓ sẵn trong `payload` (dòng 154, dùng cho các mục đích
  khác ở dòng 185/204/236), nó KHÔNG được đưa vào `ctx` truyền cho capability
  handler. `apps/cosa/worker/handlers.py` (quanh dòng ~1167) vẫn là nơi DUY
  NHẤT đặt `project_id` vào `run_payload`, nhưng đó là đường scheduler
  (`agent_profile == "operations"`), không phải đường invocation capability
  chung. Nói thẳng: một `_resolve_project_id` dict-aware, ctx-precedence
  trong `legal_issue_read.py` (nếu implement đúng pattern
  `people_risk_read.py`/`security_posture_read.py`) vẫn vô hiệu trên hầu hết
  đường invocation thật hiện nay — cùng hạng mục gap đã ghi cho capability
  sibling `product`/`people`/`security`.

- **Không có generic deliberation evidence-gate nào** — nhất quán với
  cro/vpe/cpo/chro/ciso, không phải regression riêng của GC.

- **`COSA_EXECUTIVE_GC_AGENT_SPEC` không nằm trong
  `COSA_DEPLOYED_AGENT_SPECS`** (chỉ có trong `EXECUTIVE_AGENT_SPECS`, đã
  verify trực tiếp trong `apps/cosa/agents/specs.py`) — câu hỏi mở này giờ đã
  bị hoãn tới lần thứ NĂM (vpe, cpo, chro, ciso, gc đều cùng chia sẻ pattern
  chưa giải quyết này) mà không có quyết định nào. Nói thẳng: việc này cần
  được giải quyết một lần, thống nhất, cho cả năm executive spec, trước khi
  role thứ 7 (cdo) tạo thêm một instance thứ sáu của cùng pattern chưa giải
  quyết — plan này không tự ý giải quyết một mình.

- **GC-specific: applicability `UNKNOWN`/`ESCALATED` là enum tường minh đã
  implement đúng ở Task 1, nhưng KHÔNG có bespoke deliberation-time
  enforcement gate nào chặn một deliberation của GC khi applicability đang
  UNKNOWN.** Đã verify trực tiếp: `grep -rn "LEGAL_EVIDENCE_REQUIRED\|LEGAL_PROFILE_NOT_ACTIVE"
  --include="*.ts" --include="*.py" --include="*.dart" .` trả về 0 kết quả.
  Nói thẳng: hành vi thực tế đã ship cho một deliberation với applicability
  UNKNOWN/ESCALATED là luồng chung sẵn có của Company (draft → frame →
  ANALYSIS_QUEUED không phân biệt applicability), cùng cơ chế generic như
  mọi role khác — không role nào trong số đó tự implement bespoke
  evidence-required error code riêng, đúng tiền lệ portfolio-wide đã ghi ở
  known-limitations của CISO. `runtimeReadiness: READY` của `legal`/`gc`
  phản ánh mức sẵn sàng của activation-plumbing, không phải một gate chặn
  applicability chưa xác định — nêu rõ điều này để không ai lầm tưởng đã có
  gate `LEGAL_EVIDENCE_REQUIRED` như red-test pseudocode minh hoạ ở Task 3
  Step 1 (không phải thứ Task 3 thực sự xây hay được kỳ vọng phải xây).

- **GC-specific: `appendLegalIssueRevision` dùng full-replace, không phải
  merge semantics — giống hệt `appendSecurityPostureRevision`/
  `appendPeopleRiskRevision` của các sibling dossier.** Đã verify trực tiếp:
  đọc `services/company/operations/services/legal-issue-dossier.service.ts`'s
  `appendLegalIssueRevision` — `issueCategory`/`redactedQuestion` luôn bắt
  buộc lại đầy đủ (không giữ nguyên giá trị revision trước), và
  `normalizeLegalRecordRefs(undefined)` mặc định về `[]` — một append không
  kèm `legalRecordRefs` sẽ âm thầm xoá sạch reference cũ. Đây là semantics kế
  thừa nhất quán (không phải regression do task này gây ra), nhưng trước bản
  vá này CHƯA có test nào pin/assert tường minh hành vi này. Đã thêm test
  "documents full-replace (not merge) append semantics: an append without
  legalRecordRefs drops the prior reference" vào
  `legal-issue-dossier.test.ts` trong task này (mirror CISO's fix-wave
  pattern) — biến hành vi này thành contract rõ ràng thay vì để ngầm định:
  nếu ai đó sau này đổi sang merge semantics, test đó PHẢI được sửa có chủ ý
  thay vì đổi hành vi một cách âm thầm. KHÔNG đổi hành vi thật của service
  trong task này — một thay đổi hành vi merge-vs-replace cần một đợt design
  riêng ảnh hưởng cả ba dossier liên quan (legal/security/people).

- **Pre-existing, unrelated test drift phát hiện trong lúc chạy gate của task
  này (đã verify bằng `git stash` để xác nhận cùng lỗi tồn tại TRƯỚC khi có
  bất kỳ thay đổi nào của task này):** `services/company` có 4 test thất bại
  từ trước (`project-startup-team.handler.test.ts`,
  `project-startup-team.service.test.ts` — lệch kỳ vọng
  `DEFERRED_CODING`/số lượng profile catalog cho `coding`) và `apps/cosa` có
  15 test thất bại từ trước (`test_seed_publishes_every_deployed_agent_spec`,
  `test_project_crm_read_success`, `test_run_delegation.py` cả file,
  `test_worker_wiring.py` 2 case, `test_founder_knowledge_context.py` 2
  case, `test_tranche_c_full_95_catalog_inventory_sync`,
  `test_scheduled_session_worker.py`, `test_vertical_slice_1_read_path.py`,
  `test_workspace_execution_e2e.py`). KHÔNG do task này gây ra — không sửa
  trong phạm vi task này (ngoài scope, cần điều tra riêng).

- **`legalRecordRefs` chỉ được xác thực theo workspace, KHÔNG theo project —
  phát hiện bởi final whole-branch review, chưa được ghi trước đó.**
  `legal_obligations` (`services/company/shared/db/schema/finance-legal.ts`)
  không có cột `project_id` — obligation chỉ scope theo workspace.
  `assertLegalRecordRefsResolve` (`legal-issue-dossier.service.ts`) gọi
  `getObligationService` và chỉ kiểm tra obligation resolve được trong đúng
  `ctx.workspaceId`; nó không có cách nào kiểm tra obligation đó có thật sự
  liên quan tới đúng Project của dossier hay không, vì bản ghi obligation
  không mang khái niệm Project. Hệ quả cụ thể: Founder tạo Legal Issue
  Dossier cho Project B nhưng tham chiếu một obligation thật sự được tạo cho
  Project A (cùng workspace) — tham chiếu này vẫn resolve hợp lệ và được
  chấp nhận, vì không có gì ràng buộc obligation vào đúng Project. Đây KHÔNG
  phải lỗ hổng cross-tenant (vẫn nằm trong cùng workspace/tenant boundary),
  chỉ là vấn đề vệ sinh dữ liệu/độ chính xác provenance — nhưng chưa có test
  nào exercise case same-workspace-khác-project này (chỉ có test
  same-workspace-same-project và cross-workspace). Đây là hạn chế kiến trúc
  mới, chưa từng gặp ở các dossier sibling (product/people/security không có
  tích hợp cross-service tương tự) do CISO/CHRO không để lại tiền lệ nào cho
  việc này. Cần một task follow-up nếu muốn Project-scope obligation
  reference chặt hơn (vd. thêm `project_id` optional vào obligation, hoặc
  chấp nhận rủi ro này như một trade-off có chủ đích).
