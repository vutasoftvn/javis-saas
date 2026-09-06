# Thiết kế F6a — Budget Summary Backend (project budget envelope + enforcement)

**Ngày:** 2026-09-06. **Nguồn yêu cầu:**
`docs/superpowers/plans/2026-09-05-business-agents-finance.md` (mục F6,
dòng 159-187, phần "Budget contract"). **Bối cảnh:** F6 được quyết định
tách thành 3 phần độc lập — F6a (backend budget, việc này) → F6b (nối UI
TT58 Flutter) → F6c (UI payment Flutter + agent tools mới, phụ thuộc F6a's
`finance.budget.read`).

## Vấn đề

`services/company/operations/strategy/services/project-action-context.service.ts:296-305`
có 2 field `cashSummary`/`budgetSummary` trả cứng `availability: "UNAVAILABLE"`
với lý do ghi rõ "scheduled in F6" — được
`operations/strategy/tests/project-action-context.test.ts:152-163` khẳng
định đúng hành vi stub này. Không có khái niệm "ngân sách dự án" nào tồn
tại trong hệ thống; `approvePaymentRequestService`
(`finance-legal/services/payment-request.service.ts:374-435`, đã có từ F4)
duyệt chi không kiểm tra bất kỳ giới hạn ngân sách nào — chỉ kiểm quyền
theo role qua `requireCommandAuthority`.

## Thiết kế

### 1. Schema

Migration mới `44_project_budget_envelopes.up.sql` (tiếp theo migration 43,
xác nhận bằng `ls migrations/*.up.sql` lúc bắt đầu task):

```sql
CREATE TABLE finance.project_budget_envelopes (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  legal_entity_id BIGINT NOT NULL,
  currency VARCHAR(10) NOT NULL DEFAULT 'VND',
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  limit_minor NUMERIC(38, 0) NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  owner_member_id BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_budget_envelopes_project ON finance.project_budget_envelopes(project_id, period_start, period_end);

ALTER TABLE finance.payment_requests
  ADD COLUMN IF NOT EXISTS budget_override_reason TEXT,
  ADD COLUMN IF NOT EXISTS budget_override_by_member_id BIGINT;
```

Không có unique constraint bắt buộc 1-envelope-1-kỳ — một project có thể
có nhiều envelope chồng kỳ (ví dụ envelope quý + envelope năm) là hợp lệ ở
schema; task này chỉ implement lookup "envelope mới nhất phủ ngày `asOf`",
không validate/from chặn chồng kỳ (out of scope, YAGNI — chưa có yêu cầu
thật).

### 2. Ngữ nghĩa budget summary

Hàm dùng chung `computeProjectBudgetPosition(tx, {workspaceId, projectId,
currency, asOf})` trong `budget-summary.service.ts`, dùng bởi cả
`getBudgetSummary` (đọc) và `approvePaymentRequestService` (enforcement,
mục 3). Không cần tham số loại trừ request đang duyệt: tại thời điểm kiểm
tra, request đó vẫn ở `approval_state='SUBMITTED'` (transition sang
APPROVED chưa xảy ra — đã kiểm ở bước state-machine phía trên), nên tự nó
không nằm trong tổng `committedUnpaid` (chỉ cộng request `APPROVED`).

- **Tìm envelope**: `SELECT ... WHERE workspace_id=? AND project_id=?
  AND currency=? AND period_start <= asOf AND period_end >= asOf AND
  deleted_at IS NULL ORDER BY created_at DESC LIMIT 1` — có `.for("update")`
  khi gọi từ enforcement (mục 3), không lock khi gọi từ read-only summary.
  `legal_entity_id` trên envelope là metadata mô tả (dùng khi tạo envelope
  qua API mục 5), KHÔNG phải điều kiện lọc lúc tìm envelope — một project
  trong hệ thống này luôn thuộc đúng 1 legal entity trên thực tế (chưa có
  ca dùng thật nào ngược lại), nên lookup chỉ cần khóa theo
  `project_id` là đủ, tránh tham số thừa gây mơ hồ ở `getBudgetSummary`.
- **actualPaid**: `SUM(payment_allocations.amount_minor)` với
  `status='ACTIVE'`, join `payment_requests` theo `request_id` lọc
  `project_id`/`workspace_id`/`currency` — đây là tiền đã đối soát khớp
  bank thật (F4), KHÔNG phải chi phí kế toán dồn tích của F5. Hai con số
  này cố tình tách biệt, không được gộp.
- **committedUnpaid**: với mỗi `payment_requests` có
  `approval_state='APPROVED'` và `settlement_state IN ('UNPAID','REPORTED',
  'PARTIAL','EXCEPTION')` (loại `excludeRequestId` nếu có — dùng khi tính
  "nếu duyệt request này thì có vượt không" mà chưa cộng chính nó vào),
  cộng `amount_minor - SUM(allocations ACTIVE của request đó)` (phần chưa
  thanh toán).
- **forecastUnapproved**: tổng `amount_minor` của các request
  `approval_state IN ('DRAFT','SUBMITTED')` — chỉ tham khảo, KHÔNG trừ vào
  `remainingAfterCommitments` (đúng ví dụ số trong spec gốc: remaining =
  limit − actualPaid − committedUnpaid; forecast đứng ngoài công thức).
- **remainingAfterCommitments** = `limit_minor − actualPaid − committedUnpaid`
  (có thể âm — không clamp về 0, số âm là tín hiệu thật đã vượt ngân sách).
- **coverage**: `"NO_ENVELOPE"` nếu không tìm thấy envelope phủ `asOf`
  (không throw — trạng thái hợp lệ, dự án chưa bật budget tracking);
  `"COMPLETE"` nếu có envelope. Không thêm giá trị coverage nào khác ở
  task này (không có khái niệm "dữ liệu bank chưa đồng bộ đủ" cho budget —
  đó là concern của F1 snapshot, không lặp lại ở đây).

`getBudgetSummary(ctx, projectId): Promise<BudgetSummaryView>` trả về
đúng shape ví dụ trong spec gốc (`limitMinor`, `actualPaidMinor`,
`committedUnpaidMinor`, `forecastUnapprovedMinor`,
`remainingAfterCommitmentsMinor`, `coverage`, `asOf`, `currency`) — dùng
`asOf = new Date()` mặc định, không nhận tham số ngày tùy ý ở task này
(YAGNI — chưa có yêu cầu xem lịch sử budget theo ngày quá khứ).

### 3. Enforcement trong `approvePaymentRequestService`

Sửa `finance-legal/services/payment-request.service.ts:374-435`. Thêm
tham số `overrideReason?: string` vào input. Trong CÙNG
`db.transaction` bao bọc update hiện có (không mở transaction mới):

1. Nếu `current.projectId` là null → bỏ qua bước này hoàn toàn, giữ luồng
   cũ nguyên vẹn.
2. Nếu có `projectId`: gọi `computeProjectBudgetPosition(tx, {workspaceId:
   ctx.workspaceId, projectId: current.projectId, currency: current.currency,
   asOf: now})` với `.for("update")` trên dòng envelope tìm thấy (nếu có) —
   khóa để 2 request đồng thời không cùng đọc "còn dư" rồi cùng được duyệt.
3. Nếu không có envelope (`coverage="NO_ENVELOPE"`) → không chặn, duyệt
   bình thường.
4. Nếu có envelope: tính `wouldBeTotal = committedUnpaid + actualPaid +
   current.amountMinor`. Nếu `wouldBeTotal > limitMinor`:
   - Gọi `requireFounderCommand(ctx, "finance.budget.override")` — không
     phải founder thì throw ngay (giữ nguyên lỗi từ helper, không tự chế
     message khác).
   - Nếu là founder nhưng `!p.overrideReason?.trim()` → throw
     `APIError.failedPrecondition("BUDGET_LIMIT_EXCEEDED: cần overrideReason khi duyệt vượt ngân sách")`.
   - Nếu founder + có reason: cho qua, ghi
     `budgetOverrideReason: p.overrideReason`,
     `budgetOverrideByMemberId: BigInt(ctx.workforceMemberId ?? ctx.userId)`
     vào cùng câu `UPDATE` đang có (không thêm câu UPDATE riêng).
5. Nếu trong limit: duyệt bình thường, không set 2 cột override (giữ NULL).

`payment-request.handler.ts`'s `approvePaymentRequest` endpoint nhận thêm
`overrideReason?: string` optional, truyền thẳng xuống service — không đổi
gì khác trong handler.

### 4. Nối S4 context

Sửa `operations/strategy/services/project-action-context.service.ts:296-305`:

- `cashSummary`: đọc snapshot F1 mới nhất — dùng
  `getFinancialSnapshotsService(BigInt(ctx.workspaceId))` (đã có sẵn từ F1,
  `finance-legal/services/financial-snapshot.service.ts`), lấy phần tử đầu
  (mới nhất theo `snapshotDate`). Map `cashBalance: Number(currentCash) ??
  0`, `monthlyBurn: Number(monthlyNetBurn) ?? 0`,
  `runwayMonths: Number(runwayMonths) ?? 0`. Không có snapshot nào →
  `availability: "UNAVAILABLE", reason: "Chưa có finance snapshot nào cho workspace này"`
  (khác lý do "scheduled in F6" cũ — giờ là thiếu dữ liệu thật, không phải
  thiếu tính năng).
- `budgetSummary`: gọi `getBudgetSummary(ctx, projectId)` (mục 2). Nếu
  `coverage==="NO_ENVELOPE"` → `availability: "UNAVAILABLE", reason: "Dự án chưa có budget envelope"`.
  Có envelope → `availability:"READY"`, map
  `totalBudget: Number(limitMinor)`, `spent: Number(actualPaidMinor) + Number(committedUnpaidMinor)`,
  `remaining: Number(remainingAfterCommitmentsMinor)`.

Cập nhật test `project-action-context.test.ts:152-163`
("marks cashSummary and budgetSummary as UNAVAILABLE...") — đổi tên/nội
dung để phản ánh đúng hành vi mới: 1 case không có snapshot/envelope vẫn
`UNAVAILABLE` (lý do khác), 1 case có snapshot+envelope thật thì `READY`
với số đúng.

### 5. API

- `POST /finance/budget-envelopes` — tạo envelope mới, founder-only
  (`requireFounderCommand(ctx, "finance.budget.envelope.set")`). Input:
  `projectId, legalEntityId, currency?, periodStart, periodEnd, limitMinor`.
- `GET /finance/budget-summary?projectId=` — trả `BudgetSummaryView` (mục 2).

## Ngoài phạm vi

- Không làm UI Flutter cho envelope hay budget (F6c).
- Không làm agent tool `finance.budget.read` (F6c — tool đó sẽ gọi thẳng
  `GET /finance/budget-summary` khi được implement).
- Không validate/chặn 2 envelope chồng kỳ cho cùng project (YAGNI).
- Không thêm tham số "asOf tùy ý" cho `getBudgetSummary` (chỉ dùng ngày
  hiện tại).
- Không đổi gì trong `payment-request.service.ts` ngoài đúng đoạn
  enforcement mô tả ở mục 3 — không refactor thêm.

## Kiểm chứng

- `budget-summary.test.ts`: fixture request DRAFT/APPROVED/PAID lẫn lộn,
  kiểm đúng công thức mục 2 (bao gồm case forecast không trừ remaining,
  case không có envelope trả NO_ENVELOPE).
- Test approve vượt ngưỡng: non-founder bị từ chối; founder không có
  `overrideReason` bị từ chối; founder có reason thì qua và cột override
  được ghi đúng.
- Test approve KHÔNG vượt ngưỡng: không cần founder đặc biệt (giữ nguyên
  luồng `requireCommandAuthority` cũ), không set cột override.
- Test 2 request đồng thời cùng gần chạm limit — dùng lock, chỉ 1 được
  APPROVED trong giới hạn, request kia phải qua nhánh override hoặc bị từ
  chối tùy thứ tự — không được cả hai cùng ALLOW khi tổng vượt limit.
- `project-action-context.test.ts` cập nhật 2 case cashSummary/budgetSummary
  đúng theo mục 4, các test khác trong file không được regress.
- `cd services/company && npm run typecheck`, `make company-boundary-check`,
  `make encore-handler-boundary-check`, `make ts-suppression-check`.
