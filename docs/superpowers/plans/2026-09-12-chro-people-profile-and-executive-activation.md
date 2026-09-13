# CHRO People Profile + Executive Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`) and execute tasks in order.

**Goal:** Tạo `people` profile với People Risk Dossier tối thiểu, privacy-first và mở `chro` chỉ để tư vấn organizational design, hiring process và people risk.

**Architecture:** Company owns Project People Risk Dossier: redacted workforce capacity/risk metadata, source provenance and Founder-reviewed revisions. Agent Platform reads only that snapshot. CHRO is a capability-empty advisor, never an HR system, applicant tracker, performance evaluator or hiring decision-maker.

**Tech Stack:** Company Operations/Drizzle/Encore, Python agent/capability registry, shared contracts, skillpacks, Flutter, Vitest/pytest/E2E.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`.

## Global Constraints

- Never store/retrieve CVs, compensation, protected characteristics, performance notes, health data or contact PII in this dossier, skillpack, board frame or model prompt.
- A founder alone confirms a people policy/decision. CHRO can draft a rubric/risk question but cannot rank candidates, change a WorkforceMember, invite/terminate anyone or message a person.
- `people` and `chro` only become READY after Project isolation, PII rejection and Founder-confirmation process tests pass.

## File structure

| Unit | Files |
| --- | --- |
| Business record | `services/company/operations/{migrations,services,handlers,tests}/people-risk-dossier.*` |
| Read capability/specs | `apps/cosa/capabilities/people_risk_read.py`, `apps/cosa/agents/{specs,agent_profile_specs,seed}.py` |
| Identity/catalog | Company `ai-member.service.ts`, shared contracts/generators/generated files, `011_people_startup_profile.*` |
| Advisory/proof | `skillpacks/executive/chro-advisor/**`, Hologram Hub tests, `tests/e2e/test_chro_people_profile.py` |

### Task 1: Build a redacted People Risk Dossier

**Files:** Create the business record migration/service/handler/tests above.

**Interfaces:** `createPeopleRiskDossier(ctx, {projectId, capacityBands, riskSignals, sourceRefs})`; `appendPeopleRiskRevision(ctx, dossierId, expectedVersion, draft)`; `readPeopleRiskSnapshot(ctx, projectId)` returns only classified aggregate data.

- [ ] **Step 1: Write failing privacy/isolation tests**

```ts
it("rejects PII fields and foreign-project reads", async () => {
  await expect(createPeopleRiskDossier(ctx, { ...draft, candidateEmail: "a@b.test" } as never))
    .rejects.toMatchObject({ code: "invalid_argument" });
  await expect(readPeopleRiskSnapshot(foreignCtx, projectId)).rejects.toMatchObject({ code: "permission_denied" });
});
```

- [ ] **Step 2: Run red, implement additive CAS record, run green**

```bash
cd services/company && npx vitest run operations/tests/people-risk-dossier.test.ts && npm run typecheck
```

Validate a fixed allowlist schema, append immutable revisions, audit Founder confirmation and return no raw attachments. Do not create an HR CRUD surface.

- [ ] **Step 3: Commit**

```bash
git add services/company/operations
git commit -m "feat(people): add redacted people risk dossier"
```

### Task 2: Add explicit People/CHRO specs

**Files:** Create read capability/test; modify agent specs/maps/seed, Company mapping/tests.

**Interfaces:** `people.risk.read`; `COSA_PEOPLE_AGENT_SPEC = cosa.agents.people@1.0.0/L1_PROPOSE`; `COSA_EXECUTIVE_CHRO_AGENT_SPEC = cosa.executive.chro@1.0.0/L1_PROPOSE` with empty capabilities.

- [ ] **Step 1: Write red spec test**

```python
async def test_people_profile_cannot_read_pii_and_chro_cannot_mutate_workforce(gateway):
    assert AGENT_PROFILE_SPECS["people"].id == "cosa.agents.people"
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.chro"].capability_refs == []
    with pytest.raises(CapabilityDenied): await gateway.execute(people_request(project_id="foreign"))
```

- [ ] **Step 2: Implement exact maps and run green**

Use only `people.risk.read`; compute Python hash then copy literal ID/version/hash into Company maps. Add no behavioral keyword fallback outside known profile routing.

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest apps/cosa/tests/test_people_profile.py -v
cd services/company && npx vitest run operations/tests/ai-member.test.ts
```

- [ ] **Step 3: Commit**

```bash
git add apps/cosa services/company/operations
git commit -m "feat(people): add pinned People and CHRO specs"
```

### Task 3: Catalog, skillpack and activation evidence

**Files:** shared contracts/generators/tests; `011_people_startup_profile.{up,down}.sql`; `skillpacks/executive/chro-advisor/**`; Company/Flutter/E2E tests.

- [ ] **Step 1: Write red readiness test**

```python
async def test_chro_needs_active_people_profile_and_never_auto_activates(client):
    assert (await client.activate_role("chro", people_template)).code == "PEOPLE_PROFILE_NOT_ACTIVE"
    assert (await client.role("chro")).display_state == "UNAVAILABLE"
```

- [ ] **Step 2: Implement and regenerate**

Add `people: TEMPLATE/READY`, `chro: READY`, generator mismatch guard, safe migration backfill/down guard and skillpack requiring aggregate source/revision plus discrimination/privacy caveats. Reuse Board activation; Flutter reloads Company truth after receipt.

- [ ] **Step 3: Verify/commit**

```bash
node scripts/gen-startup-team-profiles.mjs && node scripts/gen-executive-advisor-roles.mjs
make contracts-check && make skillpacks-validate && make services-test-company
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_chro_people_profile.py -v
git add shared/contracts scripts services/company/operations apps/cosa skillpacks/executive/chro-advisor frontend tests/e2e
git commit -m "feat(executive-board): activate CHRO advisory path"
```

## Known limitations (post-final-review)

Ghi lại từ đợt review toàn nhánh sau khi cả 3 task đã merge — bốn điểm sau đây
là giới hạn đã biết, KHÔNG phải bug được fix trong đợt review đó (mỗi điểm cần
plan riêng hoặc quyết định portfolio-wide theo đúng quy tắc CLAUDE.md "nhiều
bước → viết plan trước khi sửa code").

- **Project-isolation guard trong `people_risk_read.py` đúng về logic nhưng
  KHÔNG có hiệu lực trong pipeline invocation thật — cùng loại gap với
  `product_decision_read.py` phía sibling CPO.** Đã verify trực tiếp:
  `apps/cosa/worker/run_core.py` build `run_metadata` từ `extra_metadata`
  (dòng ~96-101, `run_metadata.update(extra_metadata)`); `extra_md` được
  populate trong `apps/cosa/worker/handlers.py` (dòng ~606-624) chỉ với
  `agent_workforce_member_id`, `company_workforce_member_id`, `assignment_id`,
  `direct_message_data_access`, `role_id`, `locale_source` — **không nơi nào
  đặt `project_id` vào metadata trở thành `ctx` của capability handler.** Do
  đó `ctx.get("project_id")` (trong `_resolve_project_id` của
  `people_risk_read.py`) luôn là `None` tại runtime, khiến hàm luôn rơi về
  `args["project_id"]` do model cung cấp — nghĩa là cross-project read trong
  cùng workspace KHÔNG thực sự bị chặn bởi guard này ở thời điểm hiện tại;
  hàng rào duy nhất còn lại là check `project ∈ workspace` phía Company (
  `readPeopleRiskSnapshot` — workspace-level isolation vẫn giữ, project-level
  thì không). Nói thẳng: Global Constraint của plan này ("`people` và `chro`
  chỉ được chuyển READY sau khi test Project isolation ... pass") chỉ được
  thỏa mãn ở mức unit test (dùng `ctx` dạng dict giả lập trực tiếp), KHÔNG
  được chứng minh trên đường invocation thật của production — cùng hạng mục
  gap mà known-limitations của plan CPO đã ghi cho capability sibling của nó,
  không phải lỗi mới phát sinh riêng ở đây, nhưng phải nêu rõ cho catalog
  entry của role này vì `runtimeReadiness` đã được chuyển sang READY.

- **Read capability HTTP auth unreachable — cùng giới hạn dùng chung với
  CPO/sales, không phải gap riêng của role này.** Lời gọi của
  `people.risk.read` sang Company được xác thực bằng header COSA-delegation
  "ambient", nhưng `readPeopleRiskSnapshotEndpoint` được bảo vệ bởi
  `requireWorkspaceAccess` — hàm này chỉ chấp nhận session token ký bằng
  `JWT_SECRET` của người dùng thật, không chấp nhận COSA-delegation token
  (cùng gap với `product_decision_read.py`/`project_crm_read.py`). Xem lại
  ghi chú tương ứng trong known-limitations của plan CPO thay vì suy diễn lại
  từ đầu — đây là gap ở tầng portfolio, không phải riêng role này, cần một
  task thiết kế follow-up riêng.

- **`COSA_EXECUTIVE_CHRO_AGENT_SPEC` không nằm trong `COSA_DEPLOYED_AGENT_SPECS`,
  và `EXECUTIVE_AGENT_SPECS` (định nghĩa tại `apps/cosa/agents/specs.py`)
  hiện chưa có consumer non-test nào** — nhất quán với tiền lệ đã có của
  `vpe`/`cpo`, không phải regression, nhưng cần đánh dấu: câu hỏi mở này (có
  nên seed executive advisor spec vào deployed-specs registry hay không) nên
  được quyết định một lần, thống nhất cho `vpe`/`cpo`/`chro` cùng lúc trước
  khi role thứ 5 tạo thêm một instance thứ tư của cùng một pattern chưa được
  giải quyết — không fix trong commit này.

- **Đường reject strict-key allowlist chỉ được chứng minh ở tầng service
  function, chưa qua HTTP thật.** Vì fix của Task 3 cho handler giờ chỉ
  destructure các field đã biết trước khi gọi service, một request HTTP có
  body chứa key lạ (vd. `candidateEmail`) sẽ bị destructuring đó âm thầm loại
  bỏ trước khi có cơ hội chạm tới logic reject-on-unknown-key của
  `assertOnlyAllowedKeys`. Đây KHÔNG phải lỗ hổng rò rỉ dữ liệu (field bị loại
  bỏ không bao giờ được persist), nhưng có nghĩa hành vi "reject unknown key"
  (khác với "âm thầm drop unknown key") hiện chỉ được exercise trong vitest ở
  tầng service, chưa được chứng minh end-to-end qua HTTP thật. Việc quét PII
  giá trị sâu (email/phone pattern nằm trong một field đã được allowlist) THÌ
  ĐÃ được chứng minh end-to-end (case
  `test_people_risk_dossier_rejects_pii_shaped_field` trong E2E).
