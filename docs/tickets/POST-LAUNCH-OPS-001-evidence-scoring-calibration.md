# POST-LAUNCH-OPS-001 — Calibrate evidence-scoring weights

**Loại:** follow-up (post-launch, Business Ops / Methodology)
**Owner:** _(chưa gán — Business Ops)_
**Nguồn:** `services/company/operations/strategy/services/evidence-scoring.service.ts:29` (`TODO [Business Ops / Methodology]`)

## Vấn đề

`SOURCE_TYPE_BASE_WEIGHTS` (baseStrength / defaultConfidence theo loại nguồn:
`financial_transaction`, `customer_interview`, `survey`, ...) hiện là **giá
trị mặc định theo phán đoán phương pháp luận**, chưa hiệu chỉnh theo dữ liệu
vận hành thật.

## Scope

1. Sau launch: thu thập dữ liệu thật — kết quả thực tế của các quyết định
   dựa trên evidence có sourceType tương ứng (dự đoán vs thực tế).
2. Hiệu chỉnh `baseStrength` / `defaultConfidence` bằng phân tích hồi cứu
   (ví dụ: source type nào over/under-predict outcome).
3. Cập nhật weights + bỏ dòng `TODO`; ghi phương pháp calibrate vào comment
   hoặc doc methodology.

## Cho tới khi hiệu chỉnh

- Dùng default hiện tại.
- Ở nơi hiển thị điểm evidence cho người dùng (UI/report): ghi chú **"trọng
  số chưa hiệu chỉnh theo vận hành"** để không tạo cảm giác chính xác giả.

## DoD

- [ ] Weights cập nhật dựa trên ≥ 1 chu kỳ dữ liệu vận hành thật.
- [ ] `TODO` ở `evidence-scoring.service.ts:29` được gỡ.
- [ ] Test `deterministic-services.test.ts` cập nhật theo weights mới.
- [ ] Chú thích "chưa hiệu chỉnh" được gỡ khỏi UI khi hoàn tất.
