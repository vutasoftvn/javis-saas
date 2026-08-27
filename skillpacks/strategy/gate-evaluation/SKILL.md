---
name: strategy-gate-evaluation
description: Quy trình thẩm định chuyển giai đoạn (Stage Gate Evaluation) tuân thủ chính sách tất định (Deterministic Stage Policy).
---

# Quy Trình Đánh Giá Cổng Giai Đoạn (Stage Gate Evaluation)

## 1. Mục Tiêu (Objective)
Đánh giá mức độ hoàn thành các điều kiện bắt buộc của giai đoạn hiện tại để quyết định dự án có đủ điều kiện chuyển sang giai đoạn kế tiếp hay không.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi hoàn thành các mục tiêu thử nghiệm chính của stage và đề xuất chuyển stage.
  - Khi cần chốt kết quả đánh giá cổng giai đoạn chính thức vào hệ thống.
- **Khi nào KHÔNG dùng**:
  - Khi chỉ cần tra cứu thông tin stage hiện tại (dùng `strategy.stage-assessment`).
  - Khi chưa có đủ bằng chứng thực nghiệm (dùng `strategy.evidence-synthesis` trước).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Có `projectId` và `stagePolicyId` (id của Stage Policy đang áp dụng cho stage muốn chuyển tới — KHÔNG phải tên stage dạng chuỗi).
- Các thử nghiệm và bằng chứng liên quan đã được ghi nhận đầy đủ.

## 4. Các Bước Tất Định (Deterministic Steps)
1. **RÀNG BUỘC CỨNG (INVARIANT §5.2)**:
   > **Skill tuyệt đối KHÔNG ĐƯỢC tự đặt kết quả Pass/Fail bằng suy luận LLM tự do**.
   > Bắt buộc phải gọi tool `strategy.gate_evaluation.create` chứa business logic tất định và stage policy từ backend Phase 2, sau đó chỉ diễn giải/tóm tắt kết quả trả về từ tool.
2. **Xác định `stagePolicyId`**: Gọi `strategy.stage_policy.list` với `workspaceId`/`companyId` (và `stageKey` nếu biết tên stage muốn chuyển tới) để lấy đúng `id` — KHÔNG tự bịa id.
3. **Gọi tool tạo Gate Evaluation**: Gọi `strategy.gate_evaluation.create` với `companyId`, `workspaceId`, `projectId`, `stagePolicyId`. Backend tự tính `requirementsMet`/`evidenceScore`/`result` tất định từ evidence hiện có và stage policy — agent KHÔNG tự gán `passed`/`score`.
4. **Diễn giải kết quả**: Trình bày rõ ràng lý do đạt hoặc chưa đạt dựa trên phản hồi của tool (`result`, `rationale`, `blockingRisks`) và stage policy.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `strategy.gate_evaluation.create`: Thực hiện đánh giá và lưu trữ kết quả cổng giai đoạn.

## 5a. Context & Prerequisites (Caller-Provided)
Stage policy lookup via `stagePolicyId` and `stageKey` liên quan tới stage policy hiện có trong workspace context do caller cung cấp (không phải tool call thực thi được trong pack này). Backend sẽ xác thực `stagePolicyId` hợp lệ khi `strategy.gate_evaluation.create` được gọi.

## 6. Điểm Phê Duyệt (Approval Points)
- `strategy.gate_evaluation.create` có `risk_level: medium`, yêu cầu policy kiểm tra quyền ghi dữ liệu (`MODIFY_BUSINESS_DATA`).

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Kết Quả Đánh Giá Cổng Giai Đoạn (Stage Gate Evaluation)
- **Dự Án**: [ID / Tên dự án]
- **Stage Policy**: [stagePolicyId / stageKey]
- **Kết Quả**: [result trả về từ backend, ví dụ "passed" / "failed"]
- **Evidence Score**: [evidenceScore]
- **Requirements Met**: [true / false]
- **Blocking Risks**: [danh sách blockingRisks nếu có]
- **Kết Luận & Hành Động Tiếp Theo**: [Kế hoạch hành động tiếp theo]
```

## 8. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- Nếu tool trả về lỗi do vi phạm stage transition policy (ví dụ nhảy cóc từ Genesis lên Scale): Thông báo rõ ràng lý do policy từ chối.
- Nếu chưa biết `stagePolicyId`: bắt buộc gọi `strategy.stage_policy.list` trước, không tự đoán id.

## 9. Ví Dụ Thực Tế (Practical Examples)
- **Input**: "Kiểm tra xem dự án EduAI có đủ điều kiện từ Discovery (S1) sang Validation (S2) không."
- **Execution**: Gọi `strategy.stage_policy.list(workspaceId=..., stageKey='S2_VALIDATION')` để lấy `stagePolicyId`, sau đó `strategy.gate_evaluation.create(companyId=..., workspaceId=..., projectId=..., stagePolicyId=...)` -> Trả về kết quả đánh giá từ backend.

## 10. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Quyết định pass gate bắt buộc phải liên kết với các ID bằng chứng thực nghiệm đã được xác thực trong hệ thống.
