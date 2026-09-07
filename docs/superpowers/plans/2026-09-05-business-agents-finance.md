# Kế hoạch finance, Cas.so, chi QR và TT58

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đóng F07/F08/F09, thay workflow payout chưa hỗ trợ bằng đề nghị chi–QR founder chuyển–đối soát, nối finance UI tới sổ và báo cáo có căn cứ.

**Architecture:** Cas adapter chỉ cung cấp dữ liệu ngân hàng/grant; Company sở hữu payment request, allocation, chứng từ và kỳ kế toán. Dữ liệu ngân hàng bất biến tách khỏi diễn giải kế toán; founder chuyển tiền ngoài hệ thống qua app ngân hàng, agent hỗ trợ đề xuất và đối soát theo quyền.

**Tech Stack:** Encore/TypeScript/Drizzle/PostgreSQL, Cas.so/Cas Link, adapter QR VietQR.io được xác nhận, Flutter/GetX, Vitest/pytest.

**Spec:** [07](/docs/architecture/overview/07-code-audit-business-agents-2026-09-05.md), [08](/docs/architecture/overview/08-phan-tich-cycle-cas-permissions-2026-09-05.md), [plan tổng](/docs/superpowers/plans/2026-09-05-business-agents-master.md).

## Global Constraints

- Kế thừa Global Constraints và test conventions của plan tổng; A1 bắt buộc cho mutation, A2/A3 trước khi mở agent tool mới.
- “Không ghi PAID khi tạo QR hoặc khi agent nói hoàn tất.”
- “CAS là nguồn dữ liệu ngân hàng”; TT58 là lớp ghi sổ/báo cáo có applicability theo pháp nhân/năm tài chính.
- API Cas.so trước đây là bankHub; không mặc định dùng contract developer.casso.vn. QR Pay thu theo đơn hàng khác QR trả người thụ hưởng bất kỳ.
- Money truyền decimal/minor string; tính bằng NUMERIC/BigInt minor theo currency, không parseFloat. Không cộng các currency nếu không có tỷ giá/version/ngày đã xác minh.
- Không gọi chuyển tiền, không giữ OTP/PIN ngân hàng trong agent, không cấp payout tool. Không tự nộp báo cáo thuế/pháp lý.
- Migration finance được dành số 35–40, sau legal L1–L3 dùng 32–34; xác nhận lại sequence trước thực thi theo H0. Mỗi file mới là Expand.

## F1 — Khóa kỳ, chống đối soát đồng thời và tính tiền đúng currency

**Files sửa:** [accounting-period.service.ts](/services/company/finance-legal/services/accounting-period.service.ts), [accounting-document.service.ts](/services/company/finance-legal/services/accounting-document.service.ts), [financial-transaction.service.ts](/services/company/finance-legal/services/financial-transaction.service.ts), [reconciliation-proposal.service.ts](/services/company/finance-legal/services/reconciliation-proposal.service.ts), [financial-snapshot.service.ts](/services/company/finance-legal/services/financial-snapshot.service.ts), [finance-snapshot.service.ts](/services/company/finance-legal/services/finance-snapshot.service.ts), [finance-legal schema](/services/company/shared/db/schema/finance-legal.ts).

**Files tạo:** [money.ts](/services/company/finance-legal/services/money.ts), [posting-guard.service.ts](/services/company/finance-legal/services/posting-guard.service.ts), [financial-integrity.test.ts](/services/company/finance-legal/tests/financial-integrity.test.ts), [35_financial_integrity.up.sql](/services/company/finance-legal/migrations/35_financial_integrity.up.sql).

**Interfaces:** `assertOpenPostingPeriod(tx,{workspaceId,legalEntityId,postingDate})` kiểm kỳ OPEN đúng entity; `addMoney(a:Money,b:Money):Money` từ plan tổng; `acceptReconciliation` nhận expectedVersion và conditional bank-row claim. Close kỳ phải tranh cùng khóa với posting: serialize theo entity/period row, không SELECT trạng thái rồi UPDATE không khóa.

- [ ] Test Postgres hai connection: confirm/close đồng thời không để chứng từ lọt sau close; hai proposal claim cùng bank transaction chỉ một được nhận. Test money:

```ts
expect(addMoney({minor:"1500000",currency:"VND"},{minor:"500000",currency:"VND"}))
  .toEqual({minor:"2000000",currency:"VND"});
expect(() => addMoney({minor:"1",currency:"VND"},{minor:"1",currency:"USD"})).toThrow();
```

- [ ] Chạy `DBTEST company finance-legal/tests/financial-integrity.test.ts`; dùng barrier phối hợp hai transaction thật, không Promise.all trên cùng connection giả. Ghi RED từ interleaving F07/F08/F09.
- [ ] Posting guard áp dụng create/post transaction, confirm/void document và điều chỉnh có tác động sổ. Chứng từ draft có thể soạn trước, nhưng không ghi sổ kỳ đóng. Ingestion raw bank vẫn nhận cả giao dịch trễ trong kỳ đóng; phát exception cần xử lý, không bỏ dữ liệu vì period closed.
- [ ] SQL claim tối thiểu trước F4 allocation:

```sql
UPDATE finance.bank_transactions
SET status = 'MATCHED', matched_accounting_document_id = $3, updated_at = NOW()
WHERE id = $1 AND workspace_id = $2
  AND status = 'UNRECONCILED'
RETURNING id;
```

SQL dùng đúng cột status và trạng thái MATCHED của baseline; kiểm chứng document $3 cùng workspace, không VOID trước claim. Nếu RETURNING rỗng rollback proposal accept. Proposal/state/audit trong cùng transaction.
- [ ] Snapshot chia theo currency/account/entity; current balance có source/asOf/opening coverage. Thiếu opening balance trả cash unavailable thay vì tổng net flow là số dư. Burn chỉ lấy flow được phân loại operating, loại transfer/capital/loan; chưa đủ phân loại trả estimated với coverage. Dùng minor BigInt nội bộ và string khi JSON.
- [ ] Test posting đúng boundary ngày/kỳ không chồng lấn, VND/USD tách, internal transfer không tăng burn. Migration/Company gates; commit `fix: enforce posting locks reconciliation claims and currency integrity`.

## F2 — Contract Cas chính thức và liên kết tài khoản qua grant

**Files sửa:** [bank-connection.service.ts](/services/company/finance-legal/services/bank-connection.service.ts), [finance-tt58.handler.ts](/services/company/finance-legal/handlers/finance-tt58.handler.ts), [finance-legal schema](/services/company/shared/db/schema/finance-legal.ts), [mvp-surface.json](/shared/contracts/mvp-surface.json).

**Files tạo:** [cas-client.ts](/services/company/finance-legal/services/cas-client.ts), [cas-contract.ts](/services/company/finance-legal/services/cas-contract.ts), [cas-link.service.ts](/services/company/finance-legal/services/cas-link.service.ts), [cas-link.handler.ts](/services/company/finance-legal/handlers/cas-link.handler.ts), [cas-link.test.ts](/services/company/finance-legal/tests/cas-link.test.ts), [36_cas_grant_binding.up.sql](/services/company/finance-legal/migrations/36_cas_grant_binding.up.sql), `cas-so-contract.md`, `cas fixtures directory`.

**Đầu ra contract trước khi bật provider:** tài liệu ghi environment/base URL/API version/auth headers; transactions response/direction/amount/timezone/pagination; webhook envelope/security/retry/event identity; grant lifecycle/scopes; account ownership/fiId; supported bank matrix. Lưu raw sample sandbox đã khử PII, hash, nguồn và ngày kiểm. Phải phân biệt sample docs và sample gọi sandbox thực.

Nguồn khởi điểm: [Transactions](https://cas.so/product/transactions/), [Cas Link](https://cas.so/general/link/), [Webhook](https://cas.so/general/api/webhook/), [QR Pay](https://cas.so/product/qr-pay/). Chưa có tài liệu đủ về signature/production bank support thì providerStatus=NOT_READY và chỉ cho contract tests chạy; không bỏ verify để thông đường.

**Schema:** connection thêm legal_entity_id, provider_environment, provider_grant_id, external_account_id, institution_id, account_fingerprint, granted_scopes, grant_expires_at, provider_contract_version; unique(provider,environment,grant_id,external_account_id). Grant có thể chứa nhiều account, không ép grant_id một-một account. Mapping active account không được gắn hai tenant mà không có thiết kế quyền rõ; duplicate kết nối trong cùng workspace là idempotent. Link session có state hash, workspace/member/entity, allowed redirect, expiry, consumedAt.

**Contracts API:** POST `/finance/cas/link-sessions` input legalEntityId/scopes; trả linkUrl/sessionId/expiresAt. POST `/finance/cas/link-sessions/:id/exchange` input publicToken/state; trả sanitized bank connections. POST `/finance/bank-connections/:id/revoke`; POST `/finance/bank-connections/:id/reauthorize`. Không trả accessToken/secretRef nhạy cảm ra model hoặc UI.

```json
{"legalEntityId":"701","scopes":["transaction"],"returnPath":"/finance"}
```

- [ ] Viết test request→grant/token, callback state/expiry/single use, exchange token storage qua connector secret store hiện có. Mock provider HTTP contract; redirectUri từ allowlist cấu hình, không cho arbitrary URL.
- [ ] Chạy `DBTEST company finance-legal/tests/cas-link.test.ts`; RED vì create connection hiện chỉ tạo PENDING. Test stolen state khác workspace/member bị chặn; account identity response không đúng entity đưa needs_review, không auto GRANTED.
- [ ] Implement client có timeout, retry GET an toàn và idempotency theo provider contract; không retry token exchange mù sau kết quả không chắc. Secrets lưu backend/vault, log chỉ correlationId/provider requestId. Tạo token có scope tối thiểu transaction; qrpay/VA chỉ khi tính năng thu dùng đến.
- [ ] Revoke/expired/reauth_required cập nhật consent state và dừng mọi sync/tool dùng grant ngay; nhận late webhook lưu inbox nhưng không cấp lại quyền. Reauthorize bind account identity cũ hoặc bắt review nếu đổi account.
- [ ] Chạy sandbox đọc/consent khi credential đã được cấp; ghi request/response đã che dữ liệu vào contract evidence. Không đánh “sandbox verified” bằng mock pass. Contract gate + typecheck/migration; commit `feat: connect Cas bank accounts with scoped grant lifecycle`.

## F3 — GET + webhook vào cùng ingestion có retry bền

**Files sửa:** [cas-webhook.handler.ts](/services/company/finance-legal/handlers/cas-webhook.handler.ts), [cas-webhook.service.ts](/services/company/finance-legal/services/cas-webhook.service.ts), [ingestion.service.ts](/services/company/finance-legal/services/ingestion.service.ts), [bank-transaction.service.ts](/services/company/finance-legal/services/bank-transaction.service.ts).

**Files tạo:** [cas-normalizer.ts](/services/company/finance-legal/services/cas-normalizer.ts), [cas-sync.service.ts](/services/company/finance-legal/services/cas-sync.service.ts), [cas-inbox-worker.service.ts](/services/company/finance-legal/services/cas-inbox-worker.service.ts), [cas-ingestion-contract.test.ts](/services/company/finance-legal/tests/cas-ingestion-contract.test.ts), [37_cas_sync_inbox.up.sql](/services/company/finance-legal/migrations/37_cas_sync_inbox.up.sql).

**Interfaces:** `normalizeCasTransaction(raw:unknown,verifiedContract,connection)` trả CanonicalBankTransaction hoặc typed reject; `syncCasConnection(connectionId,expectedGrantVersion)` pull lịch sử/cursor; `processCasInboxBatch({limit,now})` claim lease + retry. Worker được đăng ký vào cơ chế background/scheduler service hiện có, có test boot/dispatch; không chỉ thêm file không caller.

```ts
export type CanonicalBankTransaction = {
  workspaceId: string; bankConnectionId: string; externalTransactionId: string;
  bookedAt: string; amountMinor: string; currency: string; direction: "IN" | "OUT";
  counterpartyAccount: string | null; description: string;
  providerReference: string | null; rawPayloadRef: string; contractVersion: string;
};
```

**Schema:** unique(bank_connection_id,external_transaction_id); sync cursor/version/last_success_at/coverage_start; inbox dedup(provider,environment,event_identity), attempts/next_attempt_at/lease_until/error_code/raw_bytes_ref. Nếu provider thiếu event ID, identity từ contract-defined grant/account/transaction/type/version, không raw hash đơn độc làm transaction identity. Correction/reversal là event mới có relation, không overwrite âm thầm record đã đối soát.

- [ ] Viết test fixtures F2: raw JSON webhook thật không bọc rawPayload string; GET+webhook cùng giao dịch một canonical row; thiếu amount/direction/time trả INVALID_PROVIDER_PAYLOAD, không 0/IN/now mặc định.
- [ ] Chạy `DBTEST company finance-legal/tests/cas-ingestion-contract.test.ts finance-legal/tests/cas-webhook.test.ts`; cập nhật test HMAC giả định chỉ khi security contract đã xác nhận, không giữ nó như chứng minh Cas tương thích.
- [ ] Handler raw bytes verify theo F2 trước parse; resolve tenant từ server grant/account mapping; unknown grant quarantine. Durable inbox commit rồi ACK nhanh; xử lý business bên worker, lease/attempt/backoff nội bộ. Duplicate FAILED vẫn được worker retry, không chỉ skip vì đã có event.
- [ ] Sync first connect có page/cursor checkpoint; periodic incremental có overlap window để bù late transactions; mỗi page chỉ advance cursor sau canonical writes commit. 401/403 grant lỗi→reauth/revoked, 429/5xx retry bounded theo provider hint. Không giả định webhook phổ biến cho mọi transaction scope/ngân hàng.
- [ ] Test crash sau inbox ACK trước ingest, process restart tiếp tục; retry sau expiry không gọi provider; hai worker claim không double ingest; stale callback không đổi tenant. Query UI trả syncStatus/coverage/asOf và dữ liệu cũ khi provider lỗi, không xóa giao dịch đã biết. Commit `feat: ingest Cas transactions with durable sync and verified webhooks`.

## F4 — Đề nghị chi, QR và phân bổ thanh toán

**Files sửa:** [finance-legal schema](/services/company/shared/db/schema/finance-legal.ts), [reconciliation-proposal.service.ts](/services/company/finance-legal/services/reconciliation-proposal.service.ts), [workflow specs](/apps/cosa/workflows/specs.py).

**Files tạo:** [payment-request.service.ts](/services/company/finance-legal/services/payment-request.service.ts), `payment-qr.service.ts`, [payment-allocation.service.ts](/services/company/finance-legal/services/payment-allocation.service.ts), [payment-request.handler.ts](/services/company/finance-legal/handlers/payment-request.handler.ts), [payment-request.test.ts](/services/company/finance-legal/tests/payment-request.test.ts), [payment-allocation.test.ts](/services/company/finance-legal/tests/payment-allocation.test.ts), [40_payment_requests.up.sql](/services/company/finance-legal/migrations/40_payment_requests.up.sql), [41_payment_allocations.up.sql](/services/company/finance-legal/migrations/41_payment_allocations.up.sql).

**Schema:** payment_requests UUID, workspace/entity/project/budget/owner, amount_minor NUMERIC(38,0), currency, beneficiary_bank/account/name, source_document_refs, purpose, due_at, transfer_reference unique trong scope, version, approval_state DRAFT/SUBMITTED/APPROVED/REJECTED/CANCELLED; settlement_state UNPAID/REPORTED/PARTIAL/PAID/EXCEPTION; accounting_state UNCLASSIFIED/DRAFT/POSTED/REVIEW_REQUIRED. Approval record dùng existing workflow proof + resource_hash/version. payment_allocations UUID, bank_transaction_id, request_id, amount_minor,currency,status ACTIVE/REVERSED,evidence/source; unique(idempotency_key,workspace). Accounting document allocation riêng nếu một payment settlement phục vụ nhiều chứng từ; không cộng tổng request+document allocations hai lần.

**API:** GET/POST `/finance/payment-requests`; PATCH `/finance/payment-requests/:id`; POST `/:id/submit`, `/:id/approve`, `/:id/qr`, `/:id/report-transfer`, `/:id/allocations`, `/:id/cancel`. Mutation nhận expectedVersion/idempotencyKey. QR response qrImage/qrPayload + approvedVersion + beneficiary summary + request reference; không chứa secret ngân hàng.

```json
{"legalEntityId":"701","projectId":"401","amount":{"minor":"1500000","currency":"VND"},
 "beneficiary":{"bankBin":"970415","accountNumber":"123456789","name":"NHA CUNG CAP"},
 "purpose":"Phi dich vu onboarding","documentRefs":["doc-101"],"idempotencyKey":"req-onboarding-1"}
```

- [ ] Test state machine draft không tạo QR, APPROVED tạo QR vẫn UNPAID, founder report-transfer chỉ REPORTED, sửa beneficiary/amount sau duyệt làm proof cũ invalid. Chạy DBTEST hai file để ghi RED.
- [ ] Canonical hash gồm workspace/entity/requestId/version/beneficiary/amount/currency/transferReference; dùng stable canonicalizer/hash hiện có, không JSON.stringify object tùy thứ tự. Approval exact hash; thay trường ảnh hưởng thanh toán→DRAFT/SUBMITTED cần duyệt lại; account owner data không lấy tự do từ model khi tạo QR.
- [ ] Tích hợp QR recipient adapter dựa [VietQR generate](https://vietqr.io/en/generate/) khi contract/credential xác nhận: amount VND nguyên, bank BIN/account/reference theo giới hạn provider; không dùng Cas QR Pay cho tùy ý người nhận. Frontend hiển thị cả thông tin chữ để founder đối chiếu trên bank app. App expiry/hủy request không được coi đã vô hiệu QR lưu ngoài app.
- [ ] Allocation lock bank transaction + request theo thứ tự ID để tránh deadlock; kiểm tenant/entity/currency/direction OUT, available balance và request remainder trong transaction. Pseudocode nghiệp vụ:

```ts
const amount = BigInt(input.amountMinor);
if (amount <= 0n || amount > bankRemaining || amount > requestRemaining) {
  throw APIError.failedPrecondition("ALLOCATION_EXCEEDED");
}
const nextRemaining = requestRemaining - amount;
const settlementState = nextRemaining === 0n ? "PAID" : "PARTIAL";
```

Không tự match chỉ bằng amount/time; provider reference + account scope và beneficiary nếu có. Missing/ambiguous→review. Reversal tạo allocation đảo có audit và điều chỉnh settlement, không xóa lịch sử PAID. Khoản trả dư→exception/unallocated phần dư; nhiều request cùng bank txn không vượt tổng.
- [ ] Migrate accepted reconciliation cũ sang allocation khi 1:1 và amount có căn cứ; missing data→review, không đặt tự paid. Founder chi bằng account cá nhân chưa nối→manual evidence source khác BANK_VERIFIED và xử lý chi hộ/hoàn ứng, không giả bank transaction.
- [ ] Test concurrent allocations, partial 500k+1m, duplicate approval/QR/retry, late payment sau cancel, QR screenshot dùng lại→exception. Vô hiệu workflow finance.payout.execute và thay bằng request workflow có trạng thái, không đăng ký payout executor. Commit `feat: add founder-approved payment requests qr and settlement allocations`.

## F5 — Chế độ TT58 có nguồn, sổ và báo cáo theo pháp nhân/kỳ

**Files sửa:** [accounting-regime.service.ts](/services/company/finance-legal/services/accounting-regime.service.ts), [accounting-regime-policy.service.ts](/services/company/finance-legal/services/accounting-regime-policy.service.ts), [accounting-profile.service.ts](/services/company/finance-legal/services/accounting-profile.service.ts), [accounting-document.service.ts](/services/company/finance-legal/services/accounting-document.service.ts), [finance-tt58.handler.ts](/services/company/finance-legal/handlers/finance-tt58.handler.ts).

**Files tạo:** [accounting-books.service.ts](/services/company/finance-legal/services/accounting-books.service.ts), [accounting-reports.service.ts](/services/company/finance-legal/services/accounting-reports.service.ts), [accounting-mapping.ts](/services/company/finance-legal/services/accounting-mapping.ts), [tt58-reports.test.ts](/services/company/finance-legal/tests/tt58-reports.test.ts), [42_tt58_accounting_reports.up.sql](/services/company/finance-legal/migrations/42_tt58_accounting_reports.up.sql), [tt58-2026-mapping.md](/docs/finance/tt58-2026-mapping.md), [fixtures/tt58-2026](/services/company/finance-legal/tests/fixtures/tt58-2026).

**Prerequisite ngoài code:** thu thập toàn văn/phụ lục chính thức và reviewer kế toán xác nhận matrix applicability/books/report lines. Nguồn khởi điểm [Bộ Tài chính](https://www.mof.gov.vn/tin-tuc-tai-chinh/tin-chinh-sach-tai-chinh/quy-dinh-moi-ve-che-do-ke-toan-cho-doanh-nghiep-sieu-nho). Giữ ngày hiệu lực, kỳ bắt đầu áp dụng, source hash/version riêng. Không tự suy TT58_MODE_1..4 hoặc code B03/F01 trong UI cũ là biểu mẫu bắt buộc của TT58/2026.

**Deliverable mapping:** mỗi report/book line có mã chính thức, tên, nguồn điều/phụ lục/trang, loại nghiệp vụ, opening/movement/closing rule, dấu, rounding, cross-check. Unsupported line/data không trả 0 rồi coi đầy đủ; report `status=INCOMPLETE` + issues. Chỉ `status=VERIFIED` khi mọi dòng bắt buộc có mapping/data và reviewer chấp nhận bộ fixture.

**Schema:** fiscal profile entity_id/year_start/year_end/regime_code/regime_version/mapping_version/applicability_decision_id; unique(entity,year_start) và không overlap active periods. Book entries có document/item/category/amount/currency/effective_date/source/version; report snapshot entity/period/mapping_version/input_watermark/lines/status/issues/generated_at. Áp dụng NUMERIC, không biến mọi book thành double-entry nếu chế độ không yêu cầu; reuse tài khoản kế toán hiện có cho chế độ cần.

**API:** GET `/finance/books?legalEntityId=&periodId=&bookCode=`; GET `/finance/reports?legalEntityId=&periodId=&reportCode=`; POST `/finance/reports/generate` input scope/mappingVersion/expectedPeriodVersion. Trả report view, source coverage và issues; default regime chỉ là gợi ý cần founder/accounting reviewer xác nhận, không áp tự động cho mọi workspace.

- [ ] Tạo fixture nghiệp vụ độc lập với implementation: góp vốn 100m; vay 20m; bán dịch vụ hoàn tất 10m thu 6m còn phải thu 4m; dịch vụ mua đã nhận 2m đã trả; bỏ thuế chỉ trong fixture ghi rõ là bài kiểm tra mô hình rút gọn. Expected cash=124m, phải thu=4m, nợ vay=20m, vốn+lợi nhuận=108m, tài sản=128m. Reviewer thêm fixture đầy đủ thuế/asset/payable/advance theo chế độ thật.
- [ ] Chạy `DBTEST company finance-legal/tests/tt58-reports.test.ts`; RED trước mapping. Expected file là dữ liệu kiểm chứng viết độc lập, không sinh bằng chính report generator.
- [ ] Triển khai classification phân biệt capital/loan/internal transfer/revenue/cost/advance/payable/receivable; bank allocation chỉ chứng minh settlement. Dịch vụ đã phát sinh có thể ghi nhận trước thanh toán theo hồ sơ/chế độ; chưa đủ hồ sơ→draft/needs_review, không tự revenue từ IN.
- [ ] Rule applicability kết nối L1: entity/fiscal start/regime version rõ; calendar year bắt đầu trước mốc chế độ không tự chuyển giữa kỳ. Không đổi nhãn TT58/2024 cũ thành 2026 mà giữ nguyên mapping chưa đối chiếu. Report capability chưa verified trả PROVIDER_NOT_READY hoặc INCOMPLETE có lý do, không throw UnimplementedError generic.
- [ ] Test kỳ khóa F1, report input watermark ổn định, generated lại không đổi khi inputs/version như nhau, amendment tạo version mới. Kiểm assets=liabilities+equity và reconciliation book opening+movement=closing; matched bank không có doanh thu ghi đôi. Fixture taxes/assets do source mapping quyết định, không phát minh quy định.
- [ ] Migration/gates + reviewer evidence; commit `feat: generate entity-scoped accounting books and verified tt58 reports`. Nếu reviewer/source chưa đủ, commit infrastructure với feature disabled và báo phần mapping chưa nghiệm thu; task F5 chưa được đánh hoàn tất toàn bộ.

## F6 — Finance Flutter, budget và tool agent theo quyền

**Files sửa:** [finance_tt58_service.dart](/frontend/lib/modules/finance/services/finance_tt58_service.dart), [finance_service.dart](/frontend/lib/modules/finance/services/finance_service.dart), [finance_controller.dart](/frontend/lib/modules/finance/controllers/finance_controller.dart), [finance_view.dart](/frontend/lib/modules/finance/views/finance_view.dart), [transactions_tab.dart](/frontend/lib/modules/finance/views/tabs/transactions_tab.dart), [books_tab.dart](/frontend/lib/modules/finance/views/tabs/books_tab.dart), [reports_tab.dart](/frontend/lib/modules/finance/views/tabs/reports_tab.dart), [reconciliation_card.dart](/frontend/lib/modules/finance/widgets/reconciliation_card.dart), [finance_read.py](/apps/cosa/capabilities/finance_read.py), [finance_write.py](/apps/cosa/capabilities/finance_write.py), [capability_registration.py](/apps/cosa/composition/capability_registration.py), [mvp-surface.json](/shared/contracts/mvp-surface.json).

**Files tạo:** `payment_models.dart`, `payment_service.dart`, `payment_controller.dart`, `payments_tab.dart`, `bank_connections_panel.dart`, [budget-summary.service.ts](/services/company/finance-legal/services/budget-summary.service.ts), [budget-summary.handler.ts](/services/company/finance-legal/handlers/budget-summary.handler.ts), [44_project_budget_envelopes.up.sql](/services/company/finance-legal/migrations/44_project_budget_envelopes.up.sql), [budget-summary.test.ts](/services/company/finance-legal/tests/budget-summary.test.ts), `payment_flow_test.dart`, `finance_reports_flow_test.dart`.

**Budget contract:** budget envelope workspace/project/entity/currency/period/limit/version/owner; `getBudgetSummary(ctx,projectId)` trả limit, actualPaid, committedUnpaid, forecastUnapproved, remainingAfterCommitments, coverage/asOf. Không gộp actual accounting expense với cash paid trong cùng metric. Forecast draft không trừ ngân sách như đã duyệt; payment allocation một lần dù cả bank và manual transaction có record về cùng khoản.

```json
{"currency":"VND","limitMinor":"10000000","actualPaidMinor":"1500000",
 "committedUnpaidMinor":"2000000","forecastUnapprovedMinor":"1000000",
 "remainingAfterCommitmentsMinor":"6500000","coverage":"COMPLETE"}
```

- [ ] Test budget partial payment làm committed giảm tương ứng, cancelled request không còn committed; transfer giữa hai account không tạo expense/actual project hai lần. Flutter test bank connect canceled, provider unavailable giữ lịch sử; request QR không có khi draft; partial/paid reload đúng. Chạy DBTEST budget và FLUTTER hai file mới để ghi RED.
- [ ] Implement backend budget summary từ request/allocation/F1 cash coverage; nối S4 context bằng typed source envelope. Budget limit vượt ngưỡng yêu cầu founder approval có snapshot budget/version; khóa budget row khi approve để hai request đồng thời không vượt mà cùng nhận ALLOW. Nếu founder override, lưu reason và explicit authority.
- [ ] Thay toàn bộ frontend TT58 throw bằng API DTO có status; không gọi report không được regime hỗ trợ. Tab bank/transactions: asOf, sync coverage, reconnect; payment: detail→approve→QR→reported→partial/paid; books/reports: entity+period+source/mapping version, issues. Poll bounded khi chờ bank, stop khi rời trang/paid/revoked; không poll vô hạn nền.
- [ ] UI số tiền/ngân hàng/tài khoản/người nhận/reference hiển thị rõ; trên mobile cùng thiết bị cho lưu/copy QR hoặc deep link nếu provider đã xác nhận hỗ trợ, vẫn yêu cầu founder xác nhận trên bank app. Không coi việc mở deep link là chuyển thành công. Account cá nhân chưa kết nối hiện “chưa xác minh ngân hàng”, không “đã đối soát”.
- [ ] Agent tools mới chỉ `finance.transaction.list`, `finance.snapshot.read`, `finance.document.read`, `finance.payment_request.create`, `finance.reconciliation.propose`, `finance.budget.read`; đăng ký capability/spec đúng hash ở R3. Tên này là contract mới cần đưa vào catalog, không suy có sẵn. Tool approve/transfer không cấp finance agent mặc định. Kernel trả draft request ID và trạng thái, không câu “đã thanh toán”.
- [ ] Widget assertions sau server confirmed response:

```dart
expect(find.text('Đã duyệt — chưa thanh toán'), findsOneWidget);
expect(find.byKey(const ValueKey('payment-qr')), findsOneWidget);
expect(find.text('Đã thanh toán'), findsNothing);
```

Test server 500 giữ form/error inline; denied permission ẩn/disable thao tác và API vẫn chặn; stale entity response không đổi màn hình project/entity mới.
- [ ] Regenerate contracts; frontend-api-contract-check, relevant Flutter analyze/tests, Company typecheck/boundary gates, Python finance tool tests. Commit `feat: deliver founder finance workflows budgets and scoped agent tools`.

**Nghiệm thu toàn plan:** F07/F08/F09 có test DB concurrency/currency; Cas sandbox contract evidence riêng mock tests; no payout executor; QR không PAID; allocations không vượt ngân hàng/request; TT58 có source+mapping+expected fixture; frontend không báo thành công cho stub. Late/corrected/reversed/duplicate data có trạng thái xử lý và audit, không bị xóa để làm snapshot khớp.
