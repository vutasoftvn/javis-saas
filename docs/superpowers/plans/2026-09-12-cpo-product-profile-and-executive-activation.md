# CPO Product Profile + Executive Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`) and execute tasks in order.

**Goal:** Tạo `product` profile dựa trên Product Decision Dossier Project-bound, sau đó cho Founder kích hoạt CPO để tư vấn customer-problem, product bets và backlog priority có provenance.

**Architecture:** Company Operations owns an append-only Product Decision Dossier linked to Project evidence; Agent Platform reads a redacted immutable revision and can propose a draft, never mutate roadmap/backlog or customer records. Product functional profile and CPO advisor have separate specs; CPO is capability-empty and Board frame snapshots exact pins.

**Tech Stack:** Company Operations/Drizzle/Encore, AgentSpec/skillpacks, contracts/generators, Flutter/GetX, Vitest/pytest/process E2E.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`.

## Global Constraints

- The dossier is Project-scoped, append-only versioned and founder-reviewed. A model cannot create a confirmed product decision, reprioritize work, write `KR.actualValue`, or access another Project's interviews/evidence.
- Store evidence references, classifications and redacted excerpts only; customer contact PII and raw research attachments remain outside Agent context.
- CPO may formulate recommendations and missing-evidence questions only. No product launch, roadmap edit, experiment start or customer communication effect is in scope.
- `product`/`cpo` `READY` is contingent on the dossier API and process E2E, not on a new card or skillpack.

## File structure

| Unit | Files |
| --- | --- |
| Business dossier | `services/company/operations/{migrations,services,handlers,tests}/product-decision-dossier.*` |
| Read projection | `apps/cosa/capabilities/product_decision_read.py`, capability registration/tests |
| Profiles | `apps/cosa/agents/{specs,agent_profile_specs,seed}.py`, Company `ai-member.service.ts` |
| Catalog/board | shared contracts, generators, `010_product_startup_profile.*`, `skillpacks/executive/cpo-advisor/**` |
| Proof/UI | Hologram Hub tests and `tests/e2e/test_cpo_product_profile.py` |

### Task 1: Add a Founder-reviewed Product Decision Dossier

**Files:** Create the business dossier migration/service/handler/tests named above.

**Interfaces:** `createProductDecisionDossier(ctx, input)`, `appendProductDecisionRevision(ctx, dossierId, expectedVersion, input)`, and `readProductDecisionSnapshot(ctx, projectId)` return `{dossierId, revision, evidenceRefs, assumptions, status}`.

- [ ] **Step 1: Write red service tests**

```ts
it("requires project membership and never confirms a model-authored product decision", async () => {
  await expect(readProductDecisionSnapshot(foreignCtx, projectId)).rejects.toMatchObject({ code: "permission_denied" });
  await expect(appendProductDecisionRevision(agentCtx, dossierId, 1, draft)).rejects.toMatchObject({ code: "permission_denied" });
});
```

- [ ] **Step 2: Run red**

```bash
cd services/company && npx vitest run operations/tests/product-decision-dossier.test.ts
```

- [ ] **Step 3: Implement bounded record and public boundary**

Create additive tables keyed by workspace/project/dossier/revision, CAS revision and append-only event. Handler validates membership and Founder confirmation; it accepts source references rather than raw evidence payload. Return `APIError` codes, never raw DB errors.

- [ ] **Step 4: Run green and commit**

```bash
cd services/company && npx vitest run operations/tests/product-decision-dossier.test.ts && npm run typecheck
git add services/company/operations
git commit -m "feat(product): add project decision dossier"
```

### Task 2: Add read-only Product profile and CPO spec

**Files:** Create `apps/cosa/capabilities/product_decision_read.py` and test; modify capability registration, agent specs/maps/seed, Company mapping/tests.

**Interfaces:** `product.decision.read` returns only a validated redacted snapshot; `COSA_PRODUCT_AGENT_SPEC` is `cosa.agents.product@1.0.0/L1_PROPOSE`; `COSA_EXECUTIVE_CPO_AGENT_SPEC` is `cosa.executive.cpo@1.0.0/L1_PROPOSE` with `capability_refs=[]`.

- [ ] **Step 1: Write red capability/spec tests**

```python
async def test_product_read_rejects_foreign_project_and_cpo_has_no_write_capability(gateway):
    with pytest.raises(CapabilityDenied, match="project"):
        await gateway.execute(product_request(project_id="other"))
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.cpo"].capability_refs == []
```

- [ ] **Step 2: Implement and verify**

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest apps/cosa/tests/test_product_profile.py -v
cd services/company && npx vitest run operations/tests/ai-member.test.ts
```

Add explicit Company IDs/version/hashes only after computing actual Python spec hashes. Register no write tool and no implicit model fallback.

- [ ] **Step 3: Commit**

```bash
git add apps/cosa services/company/operations
git commit -m "feat(product): add read-only Product and CPO specs"
```

### Task 3: Catalog, skillpack, migration and Board activation

**Files:** shared contract sources/generated output/generator/tests; create `010_product_startup_profile.{up,down}.sql`, `skillpacks/executive/cpo-advisor/**`; Company/Flutter/E2E tests.

- [ ] **Step 1: Write red readiness/activation proof**

```python
async def test_cpo_requires_active_product_and_project_dossier(client):
    assert (await client.activate_role("cpo", product_template)).code == "PRODUCT_PROFILE_NOT_ACTIVE"
    assert (await client.deliberate("cpo", no_dossier)).code == "PRODUCT_EVIDENCE_REQUIRED"
```

- [ ] **Step 2: Implement truthfully**

Add `product: TEMPLATE/READY` and `cpo: READY`; generator rejects mismatch. Migration backfills only templates and its down protects active/frame referenced rows. CPO skill requires evidence/source revision, labels a hypothesis separately from a decision, and forbids roadmap/external effects. Reuse existing role activation service; do not add a CPO-specific activation endpoint.

- [ ] **Step 3: Regenerate/run/commit**

```bash
node scripts/gen-startup-team-profiles.mjs && node scripts/gen-executive-advisor-roles.mjs
make contracts-check && make skillpacks-validate && make services-test-company
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_cpo_product_profile.py -v
git add shared/contracts scripts services/company/operations skillpacks/executive/cpo-advisor apps/cosa frontend tests/e2e
git commit -m "feat(executive-board): activate CPO advisory path"
```

### Task 4: Render Company truth in Hologram Hub

**Files:** Hologram Hub board entity/model/service/controller/view tests.

- [ ] **Step 1: Add the Flutter regression case**

```dart
test('CPO remains unavailable until Company reports active Product profile', () async {
  expect(model.displayState, ExecutiveActivationState.unavailable);
  expect(model.requiredProfileKey, 'product');
});
```

- [ ] **Step 2: Implement and verify reload behavior**

Map Company field names exactly and reload the role list after mutation receipt; never parse an abbreviated mutation receipt as a full role object.

- [ ] **Step 3: Run and commit**

```bash
cd frontend && flutter test test/modules/hologram_hub && flutter analyze
git add frontend
git commit -m "test(hub): show CPO activation truth"
```

## Known limitations (post-final-review)

Ghi lại từ đợt review toàn nhánh sau khi cả 4 task đã merge — hai điểm sau đây
là giới hạn đã biết, KHÔNG phải bug được fix trong đợt review đó (cả hai đều
là thay đổi kiến trúc nhiều bước, cần plan riêng theo đúng quy tắc CLAUDE.md
"nhiều bước → viết plan trước khi sửa code"):

- **CPO deliberation framing không gate trên sự tồn tại của Product Decision
  Dossier.** Không có bất kỳ enforcement `PRODUCT_EVIDENCE_REQUIRED` nào trong
  `executive-deliberation.service.ts`. Điều này khớp với hành vi thật đã ship
  của các role `cro`/`vpe` khác (cả hai cũng không gate deliberation trên
  evidence source tương ứng của mình) — đây không phải regression riêng của
  plan này, nhưng pseudocode ở Task 3 của plan đã ngụ ý một mức enforcement
  mạnh hơn so với những gì thực sự tồn tại. Cần một đợt thiết kế follow-up nếu
  thực sự muốn có mandatory evidence gating theo từng role.

- **`product.decision.read` capability (Python, `apps/cosa`) hiện không thể
  gọi được từ một agent run thật.** Lời gọi HTTP sang Company được xác thực
  bằng header COSA-delegation "ambient" của Agent Platform, nhưng endpoint
  Company mà nó gọi (`GET /operations/projects/:projectId/product-decision-dossier`)
  được bảo vệ bởi `requireWorkspaceAccess` — hàm này chỉ chấp nhận session
  token ký bằng `JWT_SECRET` của người dùng thật, không chấp nhận
  COSA-delegation token. Đã được chứng minh bằng test mới trong
  `services/company/operations/tests/product-decision-dossier.test.ts`
  ("rejects a COSA-delegation-signed token on the read endpoint the same
  way"): delegation token bị từ chối `unauthenticated` trên endpoint đọc y hệt
  như trên 2 endpoint ghi. Kết quả: capability này hiện chỉ "reachable" qua
  đúng con đường vốn dĩ đã cần session người dùng thật — điều này triệt tiêu
  mục đích ban đầu là cho agent tự đọc. Cần một task follow-up thêm route nội
  bộ `expose: false` xác thực qua `resolveCosaTaskContext`
  (xem `services/company/shared/auth/cosa-task-delegation.ts`) trước khi
  capability này được coi là hoạt động được trong một agent run thật.

- **Fix cross-project ctx-precedence (`product_decision_read.py`) đúng về logic
  nhưng KHÔNG có hiệu lực trong pipeline thật hiện tại — cross-project read
  vẫn có thể xảy ra qua `args`.** Đợt fix sau final review đã sửa
  `_resolve_project_id` để ưu tiên `ctx.project_id` hơn `args["project_id"]`
  và reject khi hai giá trị khác nhau, có test chứng minh bằng
  `SimpleNamespace` giả lập ctx dạng object. Nhưng scoped re-review phát hiện:
  trong pipeline thật, `ctx` mà `handler` nhận được luôn là `dict`
  (`packages/agent/capabilities/gateway.py` truyền `req.context.metadata` hoặc
  `req.context`, `apps/cosa/worker/copilot_run.py` khai báo `ctx: dict[str, Any]`),
  và **không nơi nào trong `apps/cosa/worker/handlers.py`/`run_core.py` từng
  đặt `project_id` vào run metadata/ctx** cho bất kỳ đường gọi capability nào.
  `getattr(ctx, "project_id", None)` trên một `dict` luôn trả `None`, nên
  `_resolve_project_id` luôn rơi về `args.get("project_id")` — đúng hành vi bug
  ban đầu, không đổi. Đây KHÔNG phải lỗi riêng của plan này: `project_crm_read.py`
  (từ plan `cro`/sales, đã ship) có cùng pattern `args.get("project_id") or
  getattr(ctx, "project_id", None)` với cùng lỗ hổng lý thuyết. Fix triệt để đòi
  hỏi thread `project_id` xuyên suốt worker/gateway/kernel cho MỌI capability
  nhận `project_id` — một thay đổi kiến trúc cross-cutting ảnh hưởng cả các
  profile đã ship (`sales`, `coding`), cần plan riêng, không thể làm trong một
  fix wave của plan CPO. Cho tới khi fix đó tồn tại, coi cross-project isolation
  của `product.decision.read` (và `project.crm.read`) là CHƯA được đảm bảo ở
  tầng capability — chỉ có phía Company (`readProductDecisionSnapshot` kiểm
  workspace) làm hàng rào cuối, và như limitation phía trên đã nêu, capability
  này hiện còn chưa reachable được từ agent run thật nên rủi ro thực tế bị giới
  hạn — nhưng khi limitation auth ở trên được vá, limitation ctx-precedence này
  PHẢI được vá trước hoặc cùng lúc.
