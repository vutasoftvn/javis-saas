# Founder Trial R1 — Node B + C: CRM/Evidence links & Marketing/Finance read models

> 2 node giữa của DAG R1. Blueprint:
> [`docs/superpowers/specs/2026-09-09-founder-trial-r1-reconciled-plan.md`](../specs/2026-09-09-founder-trial-r1-reconciled-plan.md).
> **Depends on:** Node A1 (Founder Trial Board + manifest). B và C chạy song song.
> Node E (Founder Brief) phụ thuộc B + C.

**Goal:** nối customer signal, marketing experiment và CAS-based cash data vào
đúng project — bằng **liên kết typed per-entity** (không phải link table
polymorphic) — mà không trình bày API chưa sẵn sàng thành dữ liệu rỗng, không
biến gợi ý AI thành hành động tài chính/kế toán.

## Non-negotiable constraints

- Cùng một workspace predicate cho mọi project/commercial/finance/evidence
  reference. Không tin `projectId` từ UI khi chưa chứng minh thuộc workspace.
- Dữ liệu cũ vẫn dùng được khi chưa link. Không bịa project link, interview
  outcome, cash value hay evidence cho record legacy.
- Marketing asset là DRAFT tới khi user gửi/publish qua integration được cấp
  quyền riêng sau. R1 không thêm paid-spend / outreach automation.
- CAS webhook security, inbox dedupe, reconciliation lock, founder/accountant
  confirmation giữ nguyên. R1 không chuyển tiền, không nộp thuế, không auto-confirm sổ.
- **Bỏ hẳn `project_record_links` generic.** Dùng liên kết typed per-entity theo
  pattern `services/company/operations/services/project-link.service.ts`.
- **Không sửa migration đã apply.** Index/cột mới → migration mới (17, rồi 18…).
  Xóa mọi mệnh đề kiểu "sửa migration 16 nếu…".
- Finance: `budget-summary` đã project-scoped → hiển thị nguyên. Cash/runway
  (`financial-snapshot`) là **workspace liquidity**, panel riêng nhãn rõ, KHÔNG
  gọi là "tiền của project".

## File map

| Area | Files |
|---|---|
| B — links | `services/company/commercial/migrations/17_project_links.*`, `services/company/shared/db/schema/commercial.ts`, `services/company/commercial/services/project-record-link.service.ts` (typed), `contact.service.ts`, `lead.service.ts` + handlers |
| B — interview→evidence | `services/company/operations/strategy/services/interview.service.ts`, `evidence-ingestion.service.ts` (reuse), `interview.handler.ts` |
| C — marketing | `services/company/commercial/services/marketing-mvp.service.ts`, `marketing-mvp.handler.ts`, `frontend/lib/modules/marketing/{controllers,services}` |
| C — finance | `services/company/finance-legal/services/{budget-summary,financial-snapshot}.service.ts`, `budget-summary.handler.ts`, `frontend/lib/modules/finance/*` |
| Contracts | `shared/contracts/mvp-surface.json`, `scripts/frontend-api-contract-allowlist.json` |

---

## Node B — CRM / interview / evidence links

### B.1 — Typed project links: test đỏ

**Files:**
- Create: `services/company/commercial/migrations/17_project_links.up.sql` / `.down.sql`
- Modify: `services/company/shared/db/schema/commercial.ts`
- Create: `services/company/commercial/services/project-record-link.service.ts`
- Create: `services/company/commercial/tests/project-record-link.service.test.ts`

**Mô hình (chốt, không polymorphic):**
- `commercial.contact_projects` — bảng join (1 contact có thể là evidence cho
  nhiều project): `id` Snowflake, `workspaceId`, `projectId`, `contactId`,
  `linkedByMemberId`, `createdAt`. Unique `(workspaceId, contactId, projectId)`.
  FK `contactId` → `commercial.contacts`, `projectId` → `strategy.projects`
  (cùng Postgres DB, khác schema — FK thật hợp lệ).
- `commercial.leads.project_id` — cột nullable FK (1 lead → 1 project ở R1).
- `commercial.marketing_campaigns.project_id`, `commercial.marketing_experiments.project_id`
  — cột nullable FK (dùng ở Node C, cùng migration 17).

**Test đỏ:** link contact thuộc workspace; từ chối contact/project của workspace
khác; duplicate `(contact, project)` bị unique chặn; contact legacy chưa link
vẫn đọc được; unlink có audit; list theo project chỉ trả record có link hợp lệ;
gán `leads.project_id` sang project workspace khác bị từ chối.

### B.2 — Chạy đỏ

```
cd services/company && encore test commercial/tests/project-record-link.service.test.ts
```
Kỳ vọng: FAIL (schema + service chưa có).

### B.3 — Triển khai links

- Migration 17 expand-only: tạo `contact_projects`; `ADD COLUMN … project_id … NULL`
  cho `leads`, `marketing_campaigns`, `marketing_experiments`; index
  `(workspace_id, project_id)` mỗi bảng.
- `project-record-link.service.ts`: `linkContactToProject`, `unlinkContactFromProject`,
  `listContactsByProject`, `setLeadProject`, tất cả nhận `TenantContext`, validate
  cả 2 đầu trong workspace (dùng `getProjectInWorkspace`), tenant filter mọi query.
  **Không** JSON quan hệ không ràng buộc, **không** cross-database FK.
- Schema Drizzle vào `services/company/shared/db/schema/commercial.ts`.

### B.4 — CRM evidence loop tối thiểu

**Files:**
- Modify: `commercial/handlers/{contact,lead}.handler.ts` + services
- Modify: `operations/strategy/handlers/interview.handler.ts` + `interview.service.ts`
- Create: `services/company/commercial/tests/founder-trial-crm.contract.test.ts`
- Modify: `shared/contracts/mvp-surface.json`

**Test đỏ:** tạo contact/lead với `projectId` → link tạo trong **cùng transaction**;
list theo project filter server-side; interview đã project-scoped sẵn — thêm hành
động **tường minh** "submit interview as evidence" tạo `evidence` `status=candidate`
qua `ingestEvidenceSource` (`sourceSystem="crm"`, `sourceRecordId = interview id`);
**không** tự tạo candidate mỗi lần lưu interview; review vẫn qua
`POST /operations/strategy/evidence/:id/review` (privileged, approve/reject).

**Triển khai:** giữ API contact/lead cũ compatible; thêm `projectId` optional vào
command + filter list. Interview "submit as evidence" là endpoint riêng
(`POST /operations/strategy/interviews/:id/submit-evidence`). Đăng ký route mới
trong `mvp-surface.json` + test ownership; regenerate clients.

### B.5 — Chạy xanh

```
cd services/company && encore test commercial/tests/project-record-link.service.test.ts commercial/tests/founder-trial-crm.contract.test.ts operations/tests/interview.service.test.ts commercial/tests/tenant-isolation.test.ts
cd ../.. && make mvp-contracts-check frontend-api-contract-check
```
Kỳ vọng: PASS; interview evidence traceable, không tự approve; legacy compatible.

---

## Node C — Marketing canonical API + CAS/budget read model

### C.1 — Marketing project scope: test đỏ

**Files:**
- Modify: `services/company/commercial/services/marketing-mvp.service.ts` + handler
- Modify: `services/company/commercial/tests/marketing-mvp.contract.test.ts`
- Modify: `shared/contracts/mvp-surface.json`

**Test đỏ:** `POST /commercial/marketing/campaigns` và `/experiments` nhận
`projectId` optional → tạo cột `project_id` (migration 17); `GET` list nhận
`projectId` query và filter **trong SQL**; asset chỉ thấy qua campaign thuộc
workspace; observed metric mang `source` + provider state; workspace khác không
cấp được project/campaign ID.

### C.2 — Chạy đỏ

```
cd services/company && encore test commercial/tests/marketing-mvp.contract.test.ts
```

### C.3 — Triển khai canonical endpoints

- Extend `/commercial/marketing/*` hiện có — **không** hồi sinh
  `/marketing/cockpit-summary` hay `/marketing/funnel`.
- Response giữ `MvpSuccess` envelope với `dataState`, `observedAt`, `sources`.
- Asset generation là DRAFT; UI ghi nhãn DRAFT.
- Đăng ký manifest entry cho campaign/experiment create + read project-filtered.

### C.4 — Dọn false-empty Flutter marketing

**Files:**
- Modify: `frontend/lib/modules/marketing/controllers/marketing_controller.dart`
- Modify: `frontend/lib/modules/marketing/services/marketing_mvp_service.dart`
- Delete (dần): các call trong `frontend/lib/modules/marketing/services/marketing_service.dart`
- Modify: `scripts/frontend-api-contract-allowlist.json`
- Tests: `frontend/test/marketing_mvp_service_test.dart`, `frontend/test/modules/marketing/marketing_controller_test.dart`

**Bước 0 — inventory (front-load, bắt buộc trước khi sửa):** liệt kê toàn bộ
~23 endpoint mà `MarketingController.loadAllData()` + `reloadValidation()` +
`MarketingService` gọi (1 controller + 1 service file). Với mỗi endpoint quyết
định: **AVAILABLE** (map sang canonical `/commercial/marketing/*` hoặc endpoint
đã có owner) hay **PLANNED** (ẩn sau manifest, không gọi). Ghi bảng vào PR.

**Triển khai:**
- Xóa pattern `Future.wait([... .catchError((_) => <...>[] / {})])` trong
  `loadAllData()` và `reloadValidation()`. Mỗi dependency render typed state
  (loading / data / unavailable / configuration_required / planned) qua
  `MarketingMvpService`.
- Gỡ dòng allowlist wildcard `/marketing/:await` và các dòng `/marketing/...`
  legacy khác khỏi `scripts/frontend-api-contract-allowlist.json` **khi** caller
  đã migrate hoặc đặt PLANNED — nằm trong định nghĩa "done" của node.
- Retire call `MarketingService` cũ chỉ sau khi mọi UI caller đã chuyển.

### C.5 — Finance read model project-scoped

**Files:**
- Modify: `services/company/finance-legal/handlers/budget-summary.handler.ts` (nếu cần expose thêm field)
- Modify: `services/company/finance-legal/services/financial-snapshot.service.ts` (đọc)
- Create: `services/company/finance-legal/tests/founder-trial-finance.test.ts`
- Create: `frontend/lib/modules/finance/project_finance_panel_service.dart`
- Modify: `shared/contracts/mvp-surface.json`

**Test đỏ:** `GET /finance/budget-summary?projectId=…` trả `BudgetSummaryView`
(`coverage: NO_ENVELOPE | COMPLETE`, amounts minor-unit string, `asOf`); panel
**workspace liquidity** riêng từ `getFinancialSnapshotsService(workspaceId)` —
nhãn "workspace", không trộn vào project budget; CAS không có active connection
→ surface `CONFIGURATION_REQUIRED` với precondition thiếu; finance record
workspace khác bị từ chối.

**Triển khai:**
- **Không** bảng/ledger `project-finance-summary` mới, **không** query CAS
  provider trực tiếp từ route này, **không** recalculate ledger ngầm.
- UI hiển thị 2 khối cạnh nhau: "Project budget coverage" (`budget-summary`) và
  "Workspace liquidity" (`financial-snapshot`), nhãn rõ ràng.
- Mutation (classification, adjustment, reconciliation, accounting document,
  payment) vẫn qua flow người-xác-nhận hiện có; panel chỉ deep-link khi surface
  AVAILABLE. **Không** compliance-success badge.

### C.6 — Verify

```
cd services/company && encore test commercial/tests/marketing-mvp.contract.test.ts finance-legal/tests/founder-trial-finance.test.ts finance-legal/tests/cas-webhook.service.test.ts
cd ../../frontend && flutter test test/marketing_mvp_service_test.dart test/modules/marketing/marketing_controller_test.dart && flutter analyze --no-pub
cd .. && make mvp-contracts-check mvp-surface-check frontend-api-contract-check route-inventory-check
```
Kỳ vọng: PASS; HTTP fail hiện là fail, không phải list rỗng; không route
`/marketing/*` legacy nào feed một surface R1 "live".

---

## Node E — Founder Brief (mặc định KHÔNG có agent recommendation)

**Depends on:** B + C. Đây là node cuối trước R1 ship.

### E.1 — Test đỏ

**Files:**
- Create: `services/company/operations/strategy/services/founder-brief.service.ts`
- Create: `services/company/operations/strategy/handlers/founder-brief.handler.ts`
- Create: `services/company/operations/tests/founder-brief.service.test.ts`
- Modify: `services/company/operations/strategy/services/cycle-review.service.ts`
- Create: `frontend/lib/modules/strategy/founder_trial/founder_brief_*.dart`
- Tests Flutter: `frontend/test/modules/strategy/founder_brief_view_test.dart`

Seed confirmed cycle + approved/candidate evidence + CRM interview outcome +
marketing observation + finance cash snapshot metadata + blocked work. Verify:
- 5 trục readiness (problem, solution, traction, economics, compliance), mỗi trục
  có `state` + evidence refs + known gaps + `lastObservedAt`.
- Mọi section ghi `sourceLabel` + `observedAt`; phân biệt absent data vs connector error.
- Loại record của workspace khác.
- Evidence `candidate` và evidence `unlinked` (không `experimentId`) **nằm ngoài**
  mọi kết luận readiness; chỉ hiển thị dạng "chưa liên kết hypothesis/experiment".
- Brief có thể kèm **một** gợi ý DRAFT tính tất định (vd "3/3 top assumption vẫn
  untested → đề xuất tiếp tục discovery"), ghi rõ non-authoritative. **Không**
  recommendation do agent sinh trong R1.
- `DecisionRecord` chỉ tạo bởi command tường minh của founder, map enum sẵn có
  `proceed | pivot | kill | hold`.

### E.2 — Chạy đỏ

```
cd services/company && encore test operations/tests/founder-brief.service.test.ts
cd frontend && flutter test test/modules/strategy/founder_brief_view_test.dart
```

### E.3 — Triển khai

- `GET /operations/projects/:projectId/founder-brief` — read model project-scoped,
  compose từ Founder Trial Board (A1.2) + `financial-snapshot` workspace-liquidity
  panel + budget-summary. Finance/marketing adapter trả typed `unavailable` /
  `configuration_required`.
- `cycle-review.service.ts` weekly/end-cycle tham chiếu Brief **không** bịa
  evidence/cash/decision.
- Flutter: Brief tích hợp vào `founder_trial_board_view`; mỗi section hiện nhãn
  evidence / configuration / unavailable / empty-real-data.

### E.4 — Chạy xanh

```
cd services/company && encore test operations/tests/founder-brief.service.test.ts operations/tests/cycle-review.service.test.ts
cd frontend && flutter test test/modules/strategy/founder_brief_view_test.dart && flutter analyze --no-pub
```

---

## R1 ship gate (sau khi A0 + A1 + B + C + E xanh)

### Gate hẹp theo vùng

```
make mvp-contracts-check mvp-surface-check frontend-api-contract-check route-inventory-check company-boundary-check encore-handler-boundary-check ts-suppression-check
```

### Process E2E (Postgres disposable, không mock authority/scheduler/finance callback)

Tạo project → cấu hình Operating Cycle 1–12 tuần → thêm assumption → tạo
experiment Founder-Trial (ép `assumptionId` + `method` + `successCriteria`) →
submit interview thành evidence candidate → review approve → ghi marketing
experiment project-scoped → xử lý 1 CAS transaction đã ký → đọc budget summary +
workspace liquidity → render Founder Brief → ghi 1 founder decision
(`proceed | pivot | kill | hold`). Case workspace thứ 2 (negative) ở **mọi** biên
read và mutation.

### Không phải R1 blocker (E3)

Lỗi locale-seeding trong AI-compliance E2E suite và bug B5 company-service-500
→ ticket/triage độc lập. Không được biến thành điều kiện chặn ngầm mọi feature R1.
Không mark một 503 hiện có là "kết quả sản phẩm chấp nhận được".

### Release decision

R1 shippable chỉ khi: customer/marketing/finance data mỗi loại mang source +
freshness state; mọi mutation có tenant/policy proof; UI không còn stale legacy
marketing/revenue-engine request feed một surface R1 "live"; và **không có agent
chạy thật** — Founder Brief mặc định không recommendation. Domain-agent
orchestration là Node D, sau R1.
