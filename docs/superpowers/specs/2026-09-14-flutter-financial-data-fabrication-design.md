# Flutter Financial/Time Data Fabrication Fix — Design

Status: DRAFT (chờ user review)
Ngày: 2026-09-14
Phạm vi: sub-project #5/6 trong đợt audit "Ba blocker lớn nhất" (2026-09-14) — P1.
Các sub-project khác có spec riêng:
[#1 Schedule Project scope](2026-09-14-schedule-project-scope-design.md),
[#2 Python quality gates](2026-09-14-python-quality-gates-design.md),
[#3 Semantic Knowledge production wiring](2026-09-14-semantic-knowledge-production-wiring-design.md),
[#4 Hub Workforce/Approval Project scope](2026-09-14-hub-workforce-approval-project-scope-design.md).

## Vấn đề

Audit ban đầu nêu 2 ví dụ: `finance_legal_models.dart:111` và
`commercial_models.dart:78` — DTO thay số tiền thiếu thành `0.0` và ngày
thiếu/lỗi parse thành `DateTime.now()`, biến "không có dữ liệu" thành dữ
kiện có vẻ hợp lệ, đặc biệt rủi ro ở Finance/Commercial.

**Xác nhận lại và mở rộng phạm vi (2026-09-14):**

- Pattern `?? 0.0` / `?? DateTime.now()` xuất hiện ở **35 chỗ trên 7 file**,
  không chỉ Finance/Commercial: `pilot_run_model.dart`,
  `evidence_model.dart`, `okr_models.dart`, `twelve_wy_model.dart`,
  `commercial_models.dart`, `finance_legal_models.dart`,
  `workflow_models.dart`.
- **Backend đã có kiểu `Money` chuẩn** (`services/company/finance-legal/
  services/money.ts:3-6`, BigInt-based, cột Postgres `numeric(20,2)`/
  `numeric(38,0)`). `FinancialTransactionModel.amount` phía backend **đã
  gửi qua wire dưới dạng string** (`financial-transaction.service.ts:36,
  52,83`) — Flutter parse `(json['amount'] as num?)?.toDouble()` đang mất
  chính xác ngay từ bước parse dù backend đã đúng.
- **2 bug bổ sung phát hiện, không nằm trong audit gốc:**
  - `services/company/commercial/services/marketing.service.ts:77` —
    `Number(row.budget)` tự ép cột `numeric` DB thành JS float trước khi
    trả về client. Đây là **bug ở backend**, không chỉ Flutter — sửa riêng
    Flutter không giải quyết được sai số ở nguồn.
  - `OpportunityModel.amount`/`value` (`commercial_models.dart:83`) parse
    key `amount`/`value`, nhưng backend thật (`services/company/commercial/
    services/opportunity.service.ts:20`) trả `estimatedValue: number |
    null` — **không có key nào tên `amount`/`value`**. Field này luôn rơi
    vào fallback `0.0` bất kể dữ liệu thật, vì đang đọc sai tên field, không
    phải vì dữ liệu thiếu. `CustomerModel.mrr` (`commercial_models.dart:
    175`) tương tự — không tìm thấy field backend tương ứng.
- Frontend hiện **không có phép tính số học nào** trên các field tiền tệ
  này (chỉ hiển thị, xác nhận qua tìm kiếm toàn bộ `frontend/lib/**`) —
  đổi sang decimal-string an toàn, không có rủi ro vỡ công thức tính toán
  đang chạy.
- Chưa có `Money`/decimal utility hay package `decimal` trong
  `pubspec.yaml` — cần thêm mới.
- Ngày: backend gửi ISO8601/date column nhất quán (không thấy epoch) ở
  finance-legal/commercial — `DateTime.tryParse` là đủ, chỉ cần bỏ fallback
  `?? DateTime.now()`.

## Quyết định đã chốt

1. Sửa toàn bộ 7 file (35 chỗ), không giới hạn ở Finance/Commercial — cùng
   1 chính sách parsing, tránh 2 tiêu chuẩn song song trong cùng codebase.
2. Đổi hẳn sang decimal-string/minor-unit thật (không chỉ giữ `double`
   nullable) cho field đã xác nhận backend gửi string chính xác.
3. Sửa luôn 2 bug bổ sung (`marketing.service.ts` float coercion,
   `OpportunityModel`/`CustomerModel` field-mismatch) trong cùng
   sub-project — cùng chủ đề "dữ liệu tài chính không đáng tin cậy".

## Kiến trúc & chính sách chung

**Utility mới** (`frontend/lib/core/money/` — dùng chung cho cả 7 file):

```dart
// pubspec.yaml: thêm dependency package:decimal
class Money {
  final Decimal amount;   // giá trị thập phân chính xác, không qua double
  final String currency;
  const Money({required this.amount, required this.currency});

  static Money? tryParse(dynamic raw, {String currency = 'VND'}) {
    if (raw == null) return null;
    final d = Decimal.tryParse(raw.toString());
    return d == null ? null : Money(amount: d, currency: currency);
  }
}

DateTime? parseStrictDate(dynamic raw) {
  if (raw == null) return null;
  return DateTime.tryParse(raw.toString()); // null nếu parse lỗi, KHÔNG bao giờ DateTime.now()
}
```

**Chính sách áp dụng cho cả 35 chỗ:**

- Field tiền tệ: `double` → `Money?` (nullable). Field ngày: `DateTime` →
  `DateTime?`.
- `null` nghĩa là "dữ liệu thiếu/hỏng từ nguồn" — UI hiển thị
  `UNAVAILABLE`/`INVALID_SOURCE` cho đúng field đó, **không drop cả
  record** (1 giao dịch thiếu ngày vẫn hiển thị category/description, chỉ
  ô ngày báo unavailable) — cân bằng giữa "không bịa" và "không xóa sạch
  thông tin còn dùng được".
- **Chỉ áp `Money` (decimal-string) cho field đã xác nhận backend thật sự
  gửi string/numeric chính xác** — hiện xác nhận đúng cho
  `FinancialTransactionModel.amount`. Các field khác (`mrr`, `budget`,
  `spend`, `roi`, `totalIncome`, `totalExpense`, `netCashflow`,
  `runwayMonths`, các field số trong `okr_models.dart`/`twelve_wy_model.
  dart`/`evidence_model.dart`/`pilot_run_model.dart`/`workflow_models.
  dart`) **phải xác minh lại kiểu backend thật trong lúc viết plan** trước
  khi quyết định `Money` hay giữ `double?` — không đoán bừa kiểu dữ liệu
  khi chưa thấy contract thật của từng endpoint.

## 2 bug bổ sung

1. **`marketing.service.ts:77`** — bỏ `Number(row.budget)`, trả `budget`
   dưới dạng string thô từ cột `numeric` (giống pattern
   `financial-transaction.service.ts` đã làm đúng). Đây là thay đổi
   contract route `services/company` — chạy `make company-boundary-check`
   + `make frontend-api-contract-check` sau khi sửa (Encore Guardrail #6).
2. **`OpportunityModel`**: sửa Flutter đọc đúng key `estimated_value` thay
   vì `amount`/`value`. **`CustomerModel.mrr`**: nếu xác nhận thật sự
   không tồn tại field tương ứng ở backend (`customer360.service.ts`),
   đánh dấu `@Deprecated`, luôn trả `null`, UI hiển thị `UNAVAILABLE` vĩnh
   viễn — không tiếp tục đọc 1 key không tồn tại rồi âm thầm hiện `0.0`.

## Testing

**Unit (`flutter test`):**

1. `Money.tryParse`: `null` → `null`; chuỗi hợp lệ → đúng `Decimal`, không
   mất phần thập phân (test 1 giá trị mà `double` làm tròn sai, vd cộng
   dồn nhiều lần `"0.1"`, chứng minh lý do đổi type là có thật).
2. `parseStrictDate`: `null`/chuỗi rỗng/không parse được → `null`, không
   bao giờ `DateTime.now()`.
3. Mỗi trong 7 file: field tiền/ngày thiếu/sai kiểu → field đó `null`, các
   field khác cùng record vẫn parse đúng (không drop cả record).
4. `FinancialTransactionModel.amount`: fixture JSON giống response thật từ
   `financial-transaction.service.ts` → parse đúng `Money` chính xác.
5. `OpportunityModel`: fixture JSON đúng shape `opportunity.service.ts`
   (dùng `estimated_value`) → parse đúng, không còn đọc key sai.
6. `CustomerModel.mrr`: xác nhận luôn `null`/deprecated, không còn code
   path nào trả `0.0` giả.

**Backend TS** (`services-test-company`):

7. `marketing.service.ts`: `budget` trả đúng string thô, không qua
   `Number()` — test regression với giá trị mà float làm tròn sai (vd
   `999999999.99`).

**Widget/UI:**

8. Widget hiển thị field tiền/ngày nullable: test render
   `UNAVAILABLE`/`INVALID_SOURCE` khi `null`, hiển thị giá trị thật khi có
   dữ liệu — 2 trạng thái phải khác biệt rõ ràng về UI.

**Gate tổng hợp:** `make frontend-test`, `make frontend-analyze`,
`make services-test-company`, `make frontend-api-contract-check` (đổi
field `budget`/`estimated_value` chạm route contract) đều phải xanh trước
khi báo cáo hoàn thành.

## Ngoài phạm vi (out of scope)

- Xác minh kiểu backend thật cho toàn bộ field còn lại ngoài
  `FinancialTransactionModel.amount` — để lại cho implementation plan,
  không đoán trong spec này.
- Đổi kiểu tiền tệ ở các domain khác ngoài Finance/Commercial nếu phát
  hiện thêm trong lúc implementation (vd nếu Sales/CRM có field tiền khác
  chưa xuất hiện trong 7 file đã quét) — ghi nhận riêng nếu phát hiện,
  không tự động mở rộng phạm vi spec này thêm nữa.
