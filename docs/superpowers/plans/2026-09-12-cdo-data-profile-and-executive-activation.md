# CDO Data Profile + Executive Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`) and execute tasks in order.

**Goal:** Tạo `data` profile dựa trên Data Asset & Quality Dossier và mở CDO advisor cho governance, quality, rights-management và knowledge-integrity assessment.

**Architecture:** Company records catalog metadata, owner, classification, retention/right status, quality checks and Project provenance. Agent Platform reads a bounded snapshot only; it never queries raw Company tables, embeddings, Vault raw files or personal data. CDO advisor is capability-empty and cannot change classification, ACL, retention or deletion state.

**Tech Stack:** Company Operations/metadata contracts, Agent Platform read capability, shared generators, skillpacks, Flutter, Vitest/pytest/E2E.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`.

## Global Constraints

- Metadata is not a backdoor to data: deny values, field samples, embeddings, raw file URI, API credentials and cross-Project lineage.
- Only authorized founder data stewards confirm classification/retention/access changes; CDO proposes a gap/remediation draft, never mutates ACL or deletes records.
- Missing provenance/classification must be returned as missing, not inferred by LLM.

## File structure

| Unit | Files |
| --- | --- |
| Business dossier | `services/company/operations/{migrations,services,handlers,tests}/data-governance-dossier.*` |
| Read/profile | `apps/cosa/capabilities/data_governance_read.py`, agent specs/maps/seed, Company mapping |
| Catalog | shared contracts/generators, `014_data_startup_profile.*` |
| Advisory/proof | `skillpacks/executive/cdo-advisor/**`, Hologram Hub tests, `tests/e2e/test_cdo_data_profile.py` |

### Task 1: Add metadata-only Data Governance Dossier

**Files:** Create listed migration/service/handler/tests.

**Interfaces:** `appendDataGovernanceRevision(ctx, {projectId, assets, classifications, qualitySignals, sourceRefs})`; `readDataGovernanceSnapshot(ctx, projectId)` returns `{revision, assets: [{assetId, classification, qualityStatus}], sourceRefs}`.

- [ ] **Step 1: Write red data-boundary test**

```ts
it("rejects raw values and hides foreign-project metadata", async () => {
  await expect(appendDataGovernanceRevision(ctx, { ...draft, fieldSample: "PII" } as never)).rejects.toMatchObject({ code: "invalid_argument" });
  await expect(readDataGovernanceSnapshot(foreignCtx, projectId)).rejects.toMatchObject({ code: "permission_denied" });
});
```

- [ ] **Step 2: Implement additive/CAS record, run, commit**

```bash
cd services/company && npx vitest run operations/tests/data-governance-dossier.test.ts && npm run typecheck
git add services/company/operations && git commit -m "feat(data): add metadata governance dossier"
```

### Task 2: Register Data/CDO exact identity

**Files:** Create read capability/test; modify registry/seed/maps/Company mapping tests.

**Interfaces:** `data.governance.read`; `cosa.agents.data@1.0.0/L1_PROPOSE`; `cosa.executive.cdo@1.0.0/L1_PROPOSE`, capability-empty.

- [ ] **Step 1: Red test, implement, green run**

```python
def test_cdo_cannot_read_raw_data_or_change_governance():
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.cdo"].capability_refs == []
    assert "data.asset.raw.read" not in AGENT_PROFILE_SPECS["data"].capability_refs
```

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest apps/cosa/tests/test_data_profile.py -v
cd services/company && npx vitest run operations/tests/ai-member.test.ts
```

- [ ] **Step 2: Commit**

```bash
git add apps/cosa services/company/operations && git commit -m "feat(data): add pinned Data and CDO specs"
```

### Task 3: Catalog, advisory and process proof

**Files:** shared contracts/generators/tests; `014_data_startup_profile.{up,down}.sql`; CDO skillpack; board/Flutter/E2E tests.

- [ ] **Step 1: Add red E2E**

```python
async def test_cdo_requires_active_data_and_classified_metadata(client):
    assert (await client.activate_role("cdo", data_template)).code == "DATA_PROFILE_NOT_ACTIVE"
    assert (await client.deliberate("cdo", unclassified_asset)).code == "DATA_EVIDENCE_REQUIRED"
```

- [ ] **Step 2: Implement/regenerate/validate/commit**

Add `data: TEMPLATE/READY`, `cdo: READY`, pair invariant, protected template backfill and skill requiring classification/provenance/quality status. Map/reload state in Flutter.

```bash
node scripts/gen-startup-team-profiles.mjs && node scripts/gen-executive-advisor-roles.mjs
make contracts-check && make skillpacks-validate && make services-test-company
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_cdo_data_profile.py -v
git add shared/contracts scripts services/company/operations apps/cosa skillpacks/executive/cdo-advisor frontend tests/e2e
git commit -m "feat(executive-board): activate CDO advisory path"
```

## Known limitations (post-final-review)

Ghi lại chủ động (established practice từ CHRO trở đi; GC đã làm ở Task 3
của chính plan đó) — không đợi review lần sau phát hiện lại.

1. **Read capability không tới được qua HTTP thật.** `data.governance.read`
   (Task 2) gọi Company qua HTTP dùng ambient COSA-delegation auth, nhưng
   endpoint đọc của Company (`requireWorkspaceAccess`) chỉ chấp nhận token
   ký bởi `JWT_SECRET` (human session) — không chấp nhận
   `COSA_COMPANY_DELEGATION_SECRET`. Kết quả: capability này hiện
   unreachable từ một agent run thật hôm nay. Đây là limitation chung toàn
   portfolio (đã ghi ở CPO/CHRO/CISO/GC), không phải lỗi riêng của Task
   này — không cố sửa ở đây.
2. **`ctx` không mang `project_id` trong pipeline thật.** Handler capability
   nhận `ctx` luôn là plain dict trong production; `project_id` KHÔNG BAO GIỜ
   được thread vào `ctx` ở bất kỳ đường chạy worker/gateway thật nào ngoại
   trừ một path scheduler-only (`apps/cosa/worker/handlers.py`, chỉ gate cho
   `agent_profile == "operations"`). `data_governance_read.py` dùng đúng
   pattern dict-aware `ctx.get("x") if isinstance(ctx, dict) else
   getattr(ctx, "x", None)` cho cả `project_id` và `workspace_id` (mirror
   `legal_issue_read.py`), nhưng vẫn inert với phần lớn run thật vì lý do
   trên.
3. **Không có generic deliberation evidence-gate.** Không có cơ chế nào ép
   buộc một role phải có đủ bằng chứng (evidence) trước khi tham gia
   deliberation — nhất quán trên toàn bộ 11 role hiện có, không phải thiếu
   sót riêng của CDO.
4. **`COSA_EXECUTIVE_CDO_AGENT_SPEC` không nằm trong
   `COSA_DEPLOYED_AGENT_SPECS`** — chỉ có trong `EXECUTIVE_AGENT_SPECS`
   (theo đúng precedent Task 2 đã dùng cho vpe/cpo/chro/ciso/gc). Đây là lần
   thứ **6** một `COSA_EXECUTIVE_<ROLE>_AGENT_SPEC` bị bỏ ngoài danh sách
   deploy chính — nên được quyết định MỘT LẦN, thống nhất, trước khi role #8
   (caio) thêm một trường hợp thứ 7. Chưa quyết định trong phạm vi plan
   này.
5. **`appendDataGovernanceRevision` có full-replace-on-append semantics.**
   Đã xác nhận đọc trực tiếp `services/company/operations/services/
   data-governance-dossier.service.ts`: append yêu cầu lại TOÀN BỘ
   `assets`/`sourceRefs` — không giữ lại giá trị revision trước nếu field
   không được gửi lại (`normalizeAssets`/`normalizeSourceRefs` mặc định về
   `[]` khi field vắng mặt). Đây là cùng pattern đã được document/pin bằng
   test ở Security Posture/People Risk/Legal Issue Dossier (CISO/GC fix-wave)
   — Data Governance Dossier chia sẻ đúng semantics đó, không có gì khác
   biệt cần vá thêm ở Task này.
6. **Heuristic field-sample detection có false-negative shape.** Deep-scan
   `assertNoDataValueShape` (Task 1) chỉ bắt field-sample qua 2 marker cụ
   thể: chuỗi có ≥3 phần tách bằng dấu phẩy (`DELIMITED_ROW_PATTERN`) hoặc
   tab-separated, cộng với ngưỡng độ dài `MAX_FREE_TEXT_LENGTH = 300`. Một
   field sample KHÔNG delimited và KHÔNG vượt 300 ký tự — ví dụ một giá trị
   dữ liệu đơn lẻ ngắn như một số CMND/email/tên khách hàng riêng lẻ
   (`"nguyen.van.a@example.com"` hay `"0912345678"`) — sẽ **không** bị heuristic
   này bắt, vì nó không "trông giống một hàng dữ liệu phân tách" và không đủ
   dài. Đây là trade-off có chủ đích của Task 1 (heuristic thực dụng, không
   phải bộ phát hiện hoàn hảo) — không phải bug của Task 3, nhưng cần nói
   thẳng thay vì ngụ ý heuristic bắt được mọi field sample.
7. **Embedding-vector-shaped rejection không reachable qua HTTP endpoint
   thật (phát hiện mới trong Task 3, tương tự cách GC tự phát hiện gap ở
   review cuối của chính họ).** `deepAssertSafeShape`/`isEmbeddingVectorShaped`
   trong `data-governance-dossier.service.ts` có chặn mảng toàn số, nhưng
   MỌI field trên `DataAsset`/`DataSourceRef` được khai báo kiểu `string`
   trong Encore-typed request body của handler
   (`data-governance-dossier.handler.ts`) — nên một giá trị JSON dạng mảng
   số bị chính request decoder của Encore từ chối trước
   ("invalid type: sequence, expected a string") — request KHÔNG BAO GIỜ tới
   được nhánh deep-scan của service qua endpoint public thật. Test unit của
   Task 1 (`data-governance-dossier.test.ts`) chỉ chạm được nhánh này bằng
   cách gọi thẳng service function với cast `as never` để bỏ qua type hệ
   thống — không phải qua HTTP thật. E2E của Task 3
   (`tests/e2e/test_cdo_data_profile.py`) do đó chỉ verify 2/3 category thật
   sự reachable qua HTTP (raw-file-URI, field-sample) — không assert
   embedding category vì nó unreachable ở transport layer hiện tại. Không
   phải lỗ hổng bảo mật (dữ liệu không lọt ra ngoài, chỉ là category rejection
   một không có đường chạm tới) nhưng nên biết trước khi tuyên bố "cả 5 category
   đều test qua HTTP thật".
