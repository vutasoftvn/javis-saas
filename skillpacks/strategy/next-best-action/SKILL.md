---
name: strategy.next-best-action
description: Quy trình tư vấn hành động tiếp theo tối ưu (Next Best Action) dựa trên thuật toán xếp hạng tất định của hệ thống Strategy.
---

# Quy Trình Đề Xuất Hành Động Tối Ưu Tiếp Theo (Next Best Action)

## 1. Mục Tiêu (Objective)
Cung cấp cho Founder và đội ngũ danh sách các hành động có tác động lớn nhất cần thực hiện tiếp theo dựa trên trạng thái giả định, thử nghiệm và giai đoạn hiện tại.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Founder phân vân không biết nên ưu tiên việc gì trong tuần này.
  - Cần lấy danh sách việc quan trọng nhất được xếp hạng theo thuật toán hệ thống.
- **Khi nào KHÔNG dùng**:
  - Khi cần tạo hoặc cập nhật trạng thái task chi tiết (dùng `operations.tasks`).
  - Khi thiết kế thử nghiệm mới từ đầu (dùng `strategy.experiment-design`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Có `projectId` hợp lệ trong hệ thống.

## 4. Các Bước Tất Định (Deterministic Steps)
1. **RÀNG BUỘC CỨNG (INVARIANT §5.2)**:
   > **Skill tuyệt đối KHÔNG ĐƯỢC tự sinh danh sách next-best-action candidate hoặc tự gán điểm ưu tiên bằng LLM tự do**.
   > Bắt buộc phải gọi tool `strategy.next_best_action.get` (truy vấn endpoint `GET /operations/strategy/projects/:id/next-best-actions` chứa thuật toán ranking tất định từ Phase 2c/2d), sau đó giải thích, tóm tắt và trình bày lại cho người dùng.
2. **Gọi tool lấy Next Best Actions**: Gọi `strategy.next_best_action.get` với `projectId`.
3. **Phân tích và diễn giải**: Trình bày danh sách hành động theo đúng thứ tự ưu tiên mà backend đã tính toán, giải thích lý do tại sao hành động đó lại quan trọng nhất ở thời điểm hiện tại.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `strategy.next_best_action.get`: Lấy danh sách hành động tối ưu được xếp hạng.

## 6. Điểm Phê Duyệt (Approval Points)
- Không có (Thao tác chỉ đọc `READ_LOCAL`, risk level LOW).

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Danh Sách Hành Động Tối Ưu Tiếp Theo (Next Best Actions)
- **Dự Án**: [ID / Tên dự án]
- **Hành Động Ưu Tiên Hàng Đầu (Top Priority)**:
  1. **[Tiêu đề hành động]** (Điểm ưu tiên: [Score])
     - *Lý do*: [Giải thích bối cảnh và tác động]
     - *Mục tiêu liên quan*: [Giả định / Gate / Task liên quan]
- **Các Hành Động Khác**:
  2. **[Hành động 2]**
  3. **[Hành động 3]**
```

## 8. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- Chưa có candidate nào trong DB: Hướng dẫn người dùng rà soát lại giả định và thử nghiệm để hệ thống có dữ liệu tính toán.

## 9. Ví Dụ Thực Tế (Practical Examples)
- **Input**: "Tuần này tôi nên làm việc gì tiếp theo cho venture EduAI?"
- **Execution**: Gọi `strategy.next_best_action.get(projectId='eduai-1')` -> Trả về danh sách [Action 1: Phỏng vấn 5 khách hàng B2B, Action 2: Smoke test giá 500k] -> Trình bày diễn giải cho Founder.

## 10. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Mọi thứ tự ưu tiên hành động phải phản ánh chính xác kết quả trả về từ `strategy.next_best_action.get`.
