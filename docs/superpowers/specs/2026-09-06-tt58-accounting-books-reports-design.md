# Thiết kế F5 — Chế độ TT58 có nguồn, sổ và báo cáo theo pháp nhân/kỳ

**Ngày:** 2026-09-06. **Nguồn yêu cầu:**
`docs/superpowers/plans/2026-09-05-business-agents-finance.md` (mục F5,
dòng 138-157). **Bối cảnh:** F4 (payment request/QR/settlement) đã có đầu
ra một phần (commit `abb74b37`, `2db86a45`); F5/F6/H1 vẫn "chưa có đầu ra
chính" theo `docs/architecture/overview/09-implementation-audit-2026-09-06.md`.
Thứ tự triển khai đã thống nhất với người dùng: F5 → F6 (trừ QR) → H1.

## Vấn đề

`services/company/finance-legal` chưa có sổ (books) hay báo cáo (reports)
TT58 nào được sinh ra có nguồn gốc — không có `accounting-books.service.ts`,
`accounting-reports.service.ts`, `accounting-mapping.ts`, fixture, hay
migration cho report snapshot. Phía Flutter
(`frontend/lib/modules/finance/services/finance_tt58_service.dart`) mọi
method (`getFounderLiteMetrics`, `createAndPostDocument`, `voidDocument`,
`getReportB01/B02/B03/F01`) đều `throw UnimplementedError` không điều kiện.

Spec gốc yêu cầu: mỗi dòng sổ/báo cáo phải có mã chính thức, nguồn điều/phụ
lục/trang, quy tắc opening/movement/closing, dấu, rounding; dòng chưa có
mapping/data phải trả `status=INCOMPLETE` kèm lý do — không được lặng lẽ trả
0 rồi coi là đầy đủ; chỉ đạt `status=VERIFIED` khi mọi dòng bắt buộc có
mapping/data **và có người xác nhận** bộ fixture (spec gốc gọi là "reviewer
kế toán").

**Điều chỉnh đã thống nhất với người dùng:** hệ thống hiện chưa có vai trò
kế toán riêng — founder là người quyết định. Vai trò "reviewer xác nhận" của
spec gốc được ánh xạ thành **founder xác nhận qua API có kiểm quyền**
(`requireFounderCommand`), không chặn tiến độ code, chỉ chặn việc tự ý tuyên
bố `VERIFIED` khi chưa có xác nhận thật.

## Thiết kế

### 1. Mapping content: hard-code + seed vào DB theo exact-hash

`accounting-mapping.ts` là nguồn nội dung duy nhất (TS, review qua PR — nội
dung cần chính xác pháp lý nên không sửa trực tiếp qua DB không kiểm soát).
Mỗi entry khai báo `regimeCode`, `mappingVersion`, và danh sách dòng báo cáo
theo `reportCode` (B01/B02/B03/F01) với `lineCode`, `officialCode`, `name`,
`sourceRef` (điều/phụ lục/trang), `ruleType` (`opening`/`movement`/`closing`),
`sign`, `rounding`.

Lúc migrate/khởi động, nội dung này được seed vào bảng
`finance.accounting_report_mappings` (regime_code, mapping_version,
report_code, line_code, official_code, name, source_ref, rule_type, sign,
rounding, definition_hash). Report generation **luôn đọc từ DB theo
`definition_hash`** — không tin trực tiếp object TS đang import, đúng
pattern `SpecResolver`/skillpack registry đã dùng cho AgentSpec (tránh drift
khi rolling-deploy nhiều instance chạy code khác nhau). Thêm chế độ mới
(TT199/TT200) sau này = thêm entry mới cùng file với `regime_code` khác,
không đổi schema.

Bảng founder-confirm riêng: `finance.accounting_mapping_confirmations`
(`regime_code`, `mapping_version`, `confirmed_by_member_id`,
`confirmed_at`, unique `(regime_code, mapping_version)`). Endpoint
`POST /finance/accounting-mapping/:regimeCode/:mappingVersion/confirm` gọi
`requireFounderCommand(ctx, "finance.accounting_mapping.confirm")` (helper
có sẵn tại `services/company/identity/services/command-authority.service.ts:12`,
dùng lại y hệt pattern IA01/IA19). Report chỉ đạt `status=VERIFIED` khi
mapping_version đang dùng đã có xác nhận này; chưa có → `status=INCOMPLETE`
với issue `"mapping_not_confirmed_by_founder"`.

### 2. Schema

**Sửa nhầm lẫn phát hiện khi tự rà soát:** repo đã có 2 bảng khác nhau dễ
nhầm là một — `finance.accounting_periods` (migration 1, đã
`legal_entity_id`-scoped từ migration 35, có `start_date/end_date/status
OPEN|CLOSED/closed_at`, đây chính là khái niệm "kỳ" mà F1 khóa sổ và spec F5
nói tới khi dùng `periodId`/`expectedPeriodVersion`) và
`finance.accounting_fiscal_profiles` (migration 5, chọn regime/mode TT58
cho một năm, đang được `services/legal-applicability.service.ts:70-88` đọc
chung). Thiết kế dưới đây tách rõ hai bảng, không gộp.

**`accounting_periods`** (sửa, không tạo mới): thêm `fiscal_profile_id
BIGINT` (FK tới `accounting_fiscal_profiles`, nullable — một kỳ thuộc đúng
một fiscal profile/regime) và `version INTEGER NOT NULL DEFAULT 1` (tăng
mỗi lần đổi `status`, dùng cho CAS `expectedPeriodVersion` ở
`POST /finance/reports/generate` — cùng pattern `expectedVersion` đã dùng
trong `services/payment-request.service.ts:205,250`). Không có version này
thì hai request generate/close cùng lúc có thể race trên period đang đóng.

**`accounting_fiscal_profiles`** (sửa): thêm `legal_entity_id BIGINT`,
`year_end DATE` (giữ `fiscal_year` hiện có làm `year_start`),
`mapping_version VARCHAR(50)`, `applicability_decision_id BIGINT`. Đổi
unique constraint `(workspace_id, fiscal_year)` thành unique index trên
`(workspace_id, COALESCE(legal_entity_id, 0), fiscal_year)` — dùng đúng kỹ
thuật COALESCE-unique-index đã áp dụng ở migration 38
(`38_financial_snapshot_entity_isolation.up.sql`, IA12) để NULL không trùng
vô hạn. Fiscal period ở đây luôn là 1 năm dương lịch — "không overlap active
periods" quy về đúng unique constraint này; không cần EXCLUDE/GIST cho date
range chưa từng xuất hiện trong domain thật (YAGNI).

Vì `legal-applicability.service.ts:83-88` hiện fallback `.limit(1)` không
lọc theo entity khi caller không truyền `fiscalProfileId` — sau khi thêm
`legal_entity_id` vào bảng nó đọc, fallback này sẽ lọc thêm theo
`legalEntityId` đang xử lý, tránh chọn nhầm fiscal profile của entity khác
trong cùng workspace. Đây là hệ quả trực tiếp của đổi schema, không phải
refactor ngoài phạm vi.

Bảng mới:
- `finance.accounting_book_entries`: `id`, `workspace_id`, `legal_entity_id`,
  `period_id` (FK `accounting_periods`), `document_id` (FK
  `accounting_documents` đã có), `item`, `category`
  (`capital`/`loan`/`internal_transfer`/`revenue`/`cost`/`advance`/
  `payable`/`receivable`), `amount_minor NUMERIC` (không dùng `double`),
  `currency`, `effective_date`, `source`, `version`.
- `finance.accounting_report_snapshots`: `id`, `workspace_id`,
  `legal_entity_id`, `period_id`, `mapping_version`, `input_watermark`,
  `lines JSONB`, `status` (`INCOMPLETE`/`PROVIDER_NOT_READY`/`VERIFIED`),
  `issues JSONB`, `generated_at`.
- `finance.accounting_report_mappings`, `finance.accounting_mapping_confirmations`
  (mô tả ở mục 1).

### 3. API

- `GET /finance/books?legalEntityId=&periodId=&bookCode=`
- `GET /finance/reports?legalEntityId=&periodId=&reportCode=`
- `POST /finance/reports/generate` — input `scope`, `mappingVersion`,
  `expectedPeriodVersion` (CAS chống stale write); trả report view, source
  coverage, và `issues`.
- `POST /finance/accounting-mapping/:regimeCode/:mappingVersion/confirm`
  (founder-only, mục 1).

Default regime chỉ là gợi ý — không tự áp cho mọi workspace, đúng spec gốc.

### 4. Idempotency & classification

`input_watermark` = hash ổn định (dùng canonicalizer hiện có trong repo,
không `JSON.stringify` tùy thứ tự — cùng yêu cầu đã áp cho F4 payment
request hash) của tập book entries liên quan + `mapping_version`. Sinh lại
report với input/version không đổi phải ra watermark giống hệt; input đổi
→ tạo snapshot version mới, giữ nguyên bản cũ (audit trail, không ghi đè).

Classification (`capital`/`loan`/`internal_transfer`/`revenue`/`cost`/
`advance`/`payable`/`receivable`) tái dùng logic phân loại đã có trong
`financial-snapshot.service.ts` (IA12) làm điểm khởi đầu, mở rộng thêm các
category còn thiếu. Bank allocation (F4) chỉ chứng minh settlement, không tự
suy ra category nghiệp vụ.

### 5. Trạng thái lỗi

- Dòng bắt buộc chưa có mapping/data → `status=INCOMPLETE`, `issues` liệt kê
  từng dòng thiếu kèm lý do.
- `mapping_version` chưa được founder confirm → `INCOMPLETE`,
  issue `mapping_not_confirmed_by_founder`.
- Regime hoàn toàn chưa hỗ trợ (không có entry trong
  `accounting_report_mappings`) → `PROVIDER_NOT_READY`.
- Không bao giờ throw lỗi chung chung (`UnimplementedError` generic) — đây
  chính là hành vi cần thay ở F6, nhưng backend F5 phải trả status/issues có
  cấu trúc để F6 tiêu thụ được ngay từ đầu.

### 6. Fixture & test

Fixture độc lập với implementation tại
`services/company/finance-legal/tests/fixtures/tt58-2026/` — đúng bộ số
trong spec gốc: góp vốn 100.000.000, vay 20.000.000, doanh thu 10.000.000
(thu 6.000.000, còn phải thu 4.000.000), chi phí 2.000.000 (đã nhận, đã
trả). Kỳ vọng: cash=124.000.000, phải thu=4.000.000, nợ vay=20.000.000,
vốn+lợi nhuận=108.000.000, tài sản=128.000.000 — kiểm bất biến
`assets = liabilities + equity`. Không có thuế (fixture rút gọn, ghi rõ
trong file).

`tt58-reports.test.ts`: viết trước (RED), verify mapping engine, watermark
idempotency, amendment tạo version mới, và kỳ khóa (F1) chặn report generate
mới cho kỳ đã đóng. Chạy `DBTEST company finance-legal/tests/tt58-reports.test.ts`.

## Ngoài phạm vi (rõ ràng, tránh scope creep)

- Không làm F6 (Flutter UI, budget summary) hay H1 (E2E) trong lần này —
  sẽ là spec/plan riêng theo đúng thứ tự đã thống nhất.
- Không thêm entry TT199/TT200 thật — chỉ thiết kế schema sẵn sàng cho việc
  đó, không tự bịa nội dung mapping của các thông tư chưa được yêu cầu.
- Không sửa `legal-applicability.service.ts` gì khác ngoài filter theo
  `legal_entity_id` ở đúng fallback bị ảnh hưởng bởi đổi schema.
- Không tự phát minh quy định thuế/tài sản không có trong fixture — giữ đúng
  yêu cầu "founder xác nhận trước khi coi là VERIFIED".

## Kiểm chứng

- `DBTEST company finance-legal/tests/tt58-reports.test.ts` RED trước khi
  có mapping, GREEN sau khi implement.
- `cd services/company && npm run typecheck`.
- `make company-boundary-check`, `make encore-handler-boundary-check`,
  `make ts-suppression-check` (đổi handler/service trong `services/company`).
- Test riêng cho `legal-applicability.service.ts` fallback sau khi thêm
  filter entity (đảm bảo không breaking test cũ IA19).
- Không tuyên bố F5 "hoàn tất" — chỉ tuyên bố "infrastructure sẵn sàng,
  mapping_version chờ founder confirm" cho tới khi có xác nhận thật qua API.
