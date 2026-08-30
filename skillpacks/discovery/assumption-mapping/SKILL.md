---
name: discovery-assumption-mapping
description: 'Phân loại các giả định dự án theo 4 trục: Khả năng mong muốn (Desirability),
  Tính khả thi (Feasibility), Khả năng sống sót (Viability), Tính trách nhiệm (Responsibility).'
---

# Venture Assumption Mapping & Classification

## Mục đích & Giới hạn Quyền hạn
Phân loại các giả định dự án theo 4 trục: Khả năng mong muốn (Desirability), Tính khả thi (Feasibility), Khả năng sống sót (Viability), Tính trách nhiệm (Responsibility).

> **Quy tắc an toàn & Quản trị vòng đời:**
> Không tự thay đổi project lifecycle stage, không tự phê duyệt evidence/gate, không tự gọi external provider. Khi action cần quyền hoặc evidence đủ chuẩn, tạo proposal/handoff với ID evidence/artifact liên quan.

## Triggers
- Kích hoạt khi cần thực hiện nghiệp vụ `discovery.assumption-mapping` trong giai đoạn P1_PROBLEM_VALIDATION.

## Anti-triggers
- Không kích hoạt ngoài phạm vi dự án hoặc khi thiếu ngữ cảnh `workspace_id` và `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Tuân thủ nguyên tắc anti-self-validation: Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder/Admin trước khi gate evaluation ghi nhận.

## Quy trình thực hiện (Steps)
1. **Rà soát giả định đã biết**: Đọc các giả định đã ghi nhận trước đó từ context/memory được cung cấp để tránh trùng lặp.
2. **Bóc tách giả định ẩn**: Phân tích mô hình kinh doanh, chiến lược hoặc ý tưởng venture để tìm ra các giả định chưa được nói rõ.
3. **Phân loại theo 4 trục**:
   - *Desirability (Mong muốn)*: Khách hàng có thực sự muốn và cần giải pháp này không?
   - *Feasibility (Khả thi)*: Đội ngũ có thể xây dựng và vận hành giải pháp này không?
   - *Viability (Sống sót)*: Mô hình có tạo ra doanh thu/lợi nhuận bền vững không?
   - *Responsibility (Trách nhiệm)*: Giải pháp có gây rủi ro đạo đức, pháp lý, hoặc tác động tiêu cực ngoài ý muốn không?
4. **Soạn dự thảo mỗi giả định**: Với mỗi giả định, đề xuất `statement` (nội dung), trục phân loại, và câu hỏi kiểm chứng rõ ràng tương ứng.
5. **Xác nhận kết quả**: Phản hồi danh sách giả định đã phân loại kèm câu hỏi kiểm chứng để founder xem xét (thứ tự ưu tiên kiểm chứng do `discovery.assumption-prioritization` đảm nhiệm).

## Allowed Tool Calls
Không có công cụ trực tiếp (Artifact/Proposal only). Skill này hiện chưa có capability ghi dữ liệu vào hệ thống — mọi giả định là dự thảo văn bản do con người nhập lại nếu muốn lưu trữ chính thức.

## Output Format
```markdown
### Danh Sách Giả Định Đã Phân Loại
- **Dự Án**: [ID / Tên dự án]
- **Giả Định**:
  1. **[Statement]** — Trục: [Desirability / Feasibility / Viability / Responsibility]
     - Câu hỏi kiểm chứng: [Câu hỏi cụ thể để test giả định]
- **Giả định trùng lặp** (nếu có): [Ghi chú và đề xuất hợp nhất thay vì tạo mới]
```

## Fallback & Handoff
- Khi thiếu dữ liệu hoặc không đủ điều kiện an toàn, tạo thông báo Handoff đề xuất người dùng bổ sung thông tin.
- Khi phát hiện giả định nội dung tương tự giả định đã có: nhắc nhở user và đề xuất cập nhật thay vì tạo mới.

## Eval Notes
- Suite: `evals/discovery/assumption-mapping.yaml`
