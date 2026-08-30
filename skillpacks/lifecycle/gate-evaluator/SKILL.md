---
name: lifecycle-gate-evaluator
description: Đánh giá mức độ sẵn sàng vượt gate dựa trên bằng chứng đã được duyệt
  (approved evidence) — chỉ mang tính khuyến nghị (recommendation-only).
---

# Stage Gate Readiness Evaluator

## Mục đích & Giới hạn Quyền hạn
Đánh giá mức độ sẵn sàng vượt gate dựa trên bằng chứng đã được duyệt (approved evidence) — chỉ mang tính khuyến nghị (recommendation-only).

> **Quy tắc an toàn & Quản trị vòng đời:**
> Không tự thay đổi project lifecycle stage, không tự phê duyệt evidence/gate, không tự gọi external provider. Khi action cần quyền hoặc evidence đủ chuẩn, tạo proposal/handoff với ID evidence/artifact liên quan.

## Triggers
- Kích hoạt khi cần thực hiện nghiệp vụ `lifecycle.gate-evaluator` trong giai đoạn P0_DISCOVERY, P1_PROBLEM_VALIDATION, P2_SOLUTION_VALIDATION, P3_BUILD_VALIDATE, P4_GO_TO_MARKET, P5_OPERATE_GROWTH, P6_SCALE_GOVERN.

## Anti-triggers
- Không kích hoạt ngoài phạm vi dự án hoặc khi thiếu ngữ cảnh `workspace_id` và `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id` và `stagePolicyId` (id của Stage Policy áp dụng cho stage muốn chuyển tới — KHÔNG phải tên stage dạng chuỗi; do caller/context cung cấp, skill này không có capability tra cứu danh sách stage policy).

## Evidence Rules
- Tuân thủ nguyên tắc anti-self-validation: Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder/Admin trước khi gate evaluation ghi nhận.
- Chỉ evidence đã `approved` mới được backend dùng để tính kết quả — evidence `candidate` không được gate evaluator xét đến.

## Quy trình thực hiện (Steps)
1. **RÀNG BUỘC CỨNG**: Skill tuyệt đối KHÔNG ĐƯỢC tự đặt kết quả Pass/Fail bằng suy luận LLM tự do. Bắt buộc phải gọi tool `strategy.gate_evaluation.create` chứa business logic tất định và stage policy từ backend, sau đó chỉ diễn giải/tóm tắt kết quả trả về từ tool.
2. **Đối chiếu evidence hiện có (tuỳ chọn)**: Gọi tool `strategy.evidence.list` để xem các evidence đã duyệt liên quan tới dự án trước khi đánh giá, giúp diễn giải kết quả rõ ràng hơn.
3. **Gọi tool tạo Gate Evaluation**: Gọi tool `strategy.gate_evaluation.create` với `workspaceId`, `projectId`, `stagePolicyId`. Backend tự tính `requirementsMet`/`evidenceScore`/`result` tất định từ evidence đã duyệt và stage policy — agent KHÔNG tự gán `passed`/`score`.
4. **Diễn giải kết quả**: Trình bày rõ ràng lý do đạt hoặc chưa đạt dựa trên phản hồi của tool (`result`, `rationale`, `blockingRisks`) và stage policy. Gate evaluation **không** tự động chuyển lifecycle stage — nó chỉ tạo một bản ghi khuyến nghị; chuyển stage thật là hành động riêng do con người thực hiện qua route chuyển tiếp canonical.

## Allowed Tool Calls
- `strategy.gate_evaluation.create`: Thực hiện đánh giá và lưu trữ kết quả cổng giai đoạn (chỉ tạo bản ghi đánh giá, không mutate lifecycle stage).
- `strategy.evidence.list`: Đọc danh sách evidence đã duyệt liên quan tới dự án.

## Output Format
```markdown
### Kết Quả Đánh Giá Cổng Giai Đoạn (Stage Gate Evaluation)
- **Dự Án**: [ID / Tên dự án]
- **Stage Policy**: [stagePolicyId]
- **Kết Quả**: [result trả về từ backend, ví dụ "passed" / "failed"]
- **Evidence Score**: [evidenceScore]
- **Requirements Met**: [true / false]
- **Blocking Risks**: [danh sách blockingRisks nếu có]
- **Kết Luận & Hành Động Tiếp Theo**: [Nếu "passed", đề xuất con người thực hiện transition qua route canonical; nếu chưa đạt, nêu rõ khoảng trống còn thiếu]
```

## Fallback & Handoff
- Nếu tool trả về lỗi do vi phạm stage transition policy (ví dụ nhảy cóc nhiều giai đoạn liên tiếp): thông báo rõ ràng lý do policy từ chối.
- Nếu chưa biết `stagePolicyId`: yêu cầu người dùng/context cung cấp, không tự đoán id.
- Khi thiếu dữ liệu hoặc không đủ điều kiện an toàn, tạo thông báo Handoff đề xuất người dùng bổ sung thông tin.

## Eval Notes
- Suite: `evals/lifecycle/gate-evaluator.yaml`
