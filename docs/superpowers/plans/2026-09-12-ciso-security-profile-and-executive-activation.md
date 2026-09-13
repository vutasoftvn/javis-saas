# CISO Security Profile + Executive Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`) and execute tasks in order.

**Goal:** Tạo `security` profile từ Security Posture Dossier không chứa secret, rồi kích hoạt CISO advisor cho threat-model/privacy/compliance gap assessment có provenance.

**Architecture:** Company owns Project security posture revisions and remediation proposal status; Agent Platform gets only redacted control metadata, severity and source references. CISO has no scanner, shell, credential, policy-write or incident-response capability; it is an advisory lens over evidence already ingested by a governed path.

**Tech Stack:** Company Operations, agent capability/registry, shared contracts, skillpack, Flutter, Vitest/pytest/disposable E2E.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`.

## Global Constraints

- Reject passwords, tokens, private keys, full request headers, raw vulnerability payloads and infrastructure topology from all dossier inputs/logs.
- CISO may propose risk/control gaps only; it cannot scan a target, rotate secret, disable user, patch/deploy or declare compliance/certification.
- Security evidence requires Project scope and classification. Cross-project, stale or unclassified evidence produces `SECURITY_EVIDENCE_REQUIRED`, never a guessed model conclusion.

## File structure

| Unit | Files |
| --- | --- |
| Posture record | `services/company/operations/{migrations,services,handlers,tests}/security-posture.*` |
| Read/spec | `apps/cosa/capabilities/security_posture_read.py`, agent specs/maps/seed |
| Catalog | shared contracts/generators, `012_security_startup_profile.*` |
| Advisory/proof | `skillpacks/executive/ciso-advisor/**`, Hologram Hub tests, `tests/e2e/test_ciso_security_profile.py` |

### Task 1: Create secret-free Security Posture Dossier

**Files:** Create the listed migration/service/handler/tests.

**Interfaces:** `appendSecurityPostureRevision(ctx, {projectId, controls, findings, evidenceRefs})` and `readSecurityPostureSnapshot(ctx, projectId)` return `{revision, severity, controlStates, evidenceRefs}`.

- [ ] **Step 1: Write red rejection/isolation cases**

```ts
it("rejects secret-bearing input and foreign workspace snapshot", async () => {
  await expect(appendSecurityPostureRevision(ctx, { ...draft, token: "secret" } as never)).rejects.toMatchObject({ code: "invalid_argument" });
  await expect(readSecurityPostureSnapshot(foreignCtx, projectId)).rejects.toMatchObject({ code: "permission_denied" });
});
```

- [ ] **Step 2: Implement and run green**

```bash
cd services/company && npx vitest run operations/tests/security-posture.test.ts && npm run typecheck
```

Fixed metadata schema, append-only revision/CAS, source provenance and audit only; no target/scanner integration.

- [ ] **Step 3: Commit**

```bash
git add services/company/operations && git commit -m "feat(security): add secret-free posture dossier"
```

### Task 2: Register Security/CISO with no effect capability

**Files:** Create read capability/test; modify specs/maps/seed/Company mapping tests.

**Interfaces:** `security.posture.read`; `cosa.agents.security@1.0.0/L1_PROPOSE`; `cosa.executive.ciso@1.0.0/L1_PROPOSE` with `capability_refs=[]`.

- [ ] **Step 1: Red test**

```python
def test_ciso_is_capability_empty_and_security_cannot_scan_or_access_secret():
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.ciso"].capability_refs == []
    assert "security.scan" not in AGENT_PROFILE_SPECS["security"].capability_refs
```

- [ ] **Step 2: Implement exact pins, run and commit**

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest apps/cosa/tests/test_security_profile.py -v
cd services/company && npx vitest run operations/tests/ai-member.test.ts
git add apps/cosa services/company/operations && git commit -m "feat(security): add pinned Security and CISO specs"
```

### Task 3: Release catalog truth and prove Board boundary

**Files:** shared contracts/generators/tests; `012_security_startup_profile.{up,down}.sql`; CISO skillpack; Company/Flutter/E2E tests.

- [ ] **Step 1: Add red E2E**

```python
async def test_ciso_requires_active_security_and_classified_snapshot(client):
    assert (await client.activate_role("ciso", security_template)).code == "SECURITY_PROFILE_NOT_ACTIVE"
    assert (await client.deliberate("ciso", unclassified_evidence)).code == "SECURITY_EVIDENCE_REQUIRED"
```

- [ ] **Step 2: Implement source changes**

Add `security: TEMPLATE/READY`, `ciso: READY`, generator invariant, template-only backfill and protected down. Skillpack states it is not a security certification or incident response, asks for evidence/scope/revision and reports uncertainty. UI reloads Company response.

- [ ] **Step 3: Validate/commit**

```bash
node scripts/gen-startup-team-profiles.mjs && node scripts/gen-executive-advisor-roles.mjs
make contracts-check && make skillpacks-validate && make services-test-company
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_ciso_security_profile.py -v
git add shared/contracts scripts services/company/operations apps/cosa skillpacks/executive/ciso-advisor frontend tests/e2e
git commit -m "feat(executive-board): activate CISO advisory path"
```

## Known limitations (post-final-review)

Ghi lại từ đợt review toàn nhánh sau khi cả 3 task đã merge — sáu điểm sau đây
là giới hạn đã biết, KHÔNG phải bug được fix trong đợt review đó (mỗi điểm cần
plan riêng hoặc quyết định portfolio-wide theo đúng quy tắc CLAUDE.md "nhiều
bước → viết plan trước khi sửa code").

- **Read capability HTTP auth unreachable — cùng giới hạn dùng chung với
  CPO/CHRO, không phải gap riêng của role này.** Lời gọi của
  `security.posture.read` sang Company được xác thực bằng header
  COSA-delegation "ambient", nhưng `readSecurityPostureSnapshotEndpoint` được
  bảo vệ bởi `requireWorkspaceAccess` — hàm này chỉ chấp nhận session token ký
  bằng `JWT_SECRET` của người dùng thật, không chấp nhận COSA-delegation
  token. Cùng gap portfolio-wide đã ghi trong known-limitations của
  `product_decision_read.py`/`people_risk_read.py`, không phải lỗi mới phát
  sinh riêng ở đây.

- **`ctx` không bao giờ mang `project_id` trong pipeline invocation thật.**
  Đã verify trực tiếp: `apps/cosa/worker/copilot_run.py` build `ctx` (dòng
  ~242-247) chỉ với `workspace_id`, `run_id`, `delegation_token`, `token` —
  không có `project_id`. `apps/cosa/worker/handlers.py` (quanh dòng ~1167) là
  nơi DUY NHẤT đặt `project_id` vào `run_payload`, nhưng đó là đường
  scheduler (`service:scheduler` chạy `agent_profile == "operations"`), không
  phải đường invocation capability chung. Nói thẳng: `_resolve_project_id`
  trong `security_posture_read.py` được code đúng (dict-aware, ctx thắng
  args), nhưng vô hiệu trên hầu hết đường invocation thật hiện nay vì
  `project_id` không được thread vào `ctx` ở đó — cùng hạng mục gap đã ghi
  cho capability sibling `product`/`people`.

- **Không có generic deliberation evidence-gate nào** — nhất quán với
  cro/vpe/cpo/chro, không phải regression.

- **`COSA_EXECUTIVE_CISO_AGENT_SPEC` không nằm trong
  `COSA_DEPLOYED_AGENT_SPECS`, và câu hỏi mở này (lần đầu được nêu trong
  chính known-limitations của plan CHRO, nói nên giải quyết thống nhất
  "trước khi role thứ 5") giờ đã bị hoãn tới lần thứ TƯ (vpe, cpo, chro, ciso
  đều cùng chia sẻ pattern chưa giải quyết này) mà không có quyết định nào.**
  Nói thẳng: việc này cần được giải quyết một lần, thống nhất, cho cả bốn
  executive spec, trước khi role thứ 6 (gc) tạo thêm một instance thứ năm của
  cùng pattern chưa giải quyết — plan này không tự ý giải quyết một mình.

- **CISO-specific: Global Constraint #3 của plan ("Cross-project, stale or
  unclassified evidence produces `SECURITY_EVIDENCE_REQUIRED`, never a
  guessed model conclusion") chưa được implement ở bất kỳ đâu.** Đã verify
  trực tiếp: `grep -rn "SECURITY_EVIDENCE_REQUIRED\|SECURITY_PROFILE_NOT_ACTIVE"
  --include="*.ts" --include="*.py" --include="*.dart" .` trả về 0 kết quả.
  Nói thẳng: hành vi thực tế đã ship cho một lần đọc security evidence chưa
  phân loại/cũ/chéo project là lỗi generic `permission_denied`/`not_found`/
  `aborted` sẵn có của Company (cùng cơ chế generic như mọi role khác — không
  role nào trong số đó tự implement bespoke evidence-required error code
  riêng) — đây là pseudocode mang tính minh hoạ ở red test Step 1 của Task 3
  trong plan, không phải thứ Task 3 thực sự xây hay được kỳ vọng phải xây,
  theo đúng tiền lệ portfolio-wide đã có là KHÔNG xây bespoke deliberation
  gate riêng cho từng role. `runtimeReadiness: READY` của `security`/`ciso`
  phản ánh mức sẵn sàng của activation-plumbing, không phải ngôn ngữ evidence-
  gating mạnh hơn ở headline của plan — nêu rõ điều này để không ai lầm tưởng
  đã có gate `SECURITY_EVIDENCE_REQUIRED`.

- **CISO-specific: `appendSecurityPostureRevision` dùng full-replace, không
  phải merge semantics — một hành động Founder `CONFIRMED` với payload rỗng/
  một phần sẽ âm thầm xoá controls/findings cũ và tính lại severity chỉ từ
  danh sách findings mới (có thể rỗng), có khả năng hạ một severity HIGH đã
  ghi trước đó xuống LOW với 0 finding.** Đã verify trực tiếp: đọc
  `services/company/operations/services/security-posture.service.ts`'s hàm
  `appendSecurityPostureRevision` và các hàm `normalizeControls`/
  `normalizeFindings`/`normalizeEvidenceRefs` khi nhận input `undefined`
  (mặc định về `[]`), và cách `severity`/`computeAggregateSeverity` được tính
  hoàn toàn từ `findings` của revision mới, không merge với findings của
  revision trước. Nói thẳng: đây là semantics kế thừa giống hệt sibling
  `people-risk-dossier.service.ts` (không phải regression do task này gây
  ra), nhưng hậu quả nghiêm trọng hơn đối với một bản ghi security-severity,
  và hiện chưa có test nào pin/assert tường minh hành vi này (test founder-
  confirmation hiện có chỉ assert `status`/`revision`, không assert nội dung
  `controls`/`findings`/`severity` kết quả). Đề xuất follow-up: (a) thêm một
  quyết định tường minh merge-vs-replace (áp dụng nhất quán cho cả
  `security-posture` và `people-risk-dossier` cùng lúc, không chỉ một bên),
  hoặc (b) tối thiểu, bắt buộc caller luôn resubmit toàn bộ state hiện tại
  (đã đúng theo schema này) và thêm cảnh báo UI/skillpack rằng append thay
  thế toàn bộ thay vì merge. KHÔNG đổi hành vi thật của service trong đợt fix
  này — đây là fix documentation-only cho task này; một thay đổi hành vi cần
  một đợt design riêng ảnh hưởng cả hai dossier liên quan.
