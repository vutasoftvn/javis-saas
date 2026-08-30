---
name: strategy-decision-capture
description: Quy trình ghi nhận quyết định chiến lược (Persevere, Pivot, Kill, Hold), trả lời câu hỏi chịu lực, lập luận đánh đổi, kết quả kỳ vọng và mốc ngày tái đánh giá.
---

# Quy Trình Ghi Nhận Quyết Định Chiến Lược (Strategic Decision Capture)

## 1. Mục Tiêu (Objective)
Ghi nhận bền vững các quyết định chiến lược quan trọng của Founder/Ban điều hành (tiếp tục theo đuổi - Persevere, chuyển hướng - Pivot, dừng dự án - Kill, tạm hoãn - Hold), kèm theo các câu hỏi chịu lực (load-bearing questions), phân tích đánh đổi (tradeoffs), kết quả kỳ vọng và mốc ngày tái đánh giá (Revisit Date).

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Founder/Ban điều hành chốt thay đổi phân khúc khách hàng, mô hình giá, định vị hoặc tính năng cốt lõi (Pivot).
  - Quyết định dừng một dự án hoặc sáng kiến không đạt sau chu kỳ thử nghiệm (Kill).
  - Chốt duy trì lộ trình sau các đợt đánh giá cổng chiến lược (Persevere / Proceed).
- **Khi nào KHÔNG dùng**:
  - Khi phân chia và quản lý công việc tác vụ hàng ngày (dùng `tasks`).
  - Khi thiết lập mục tiêu OKR quý (dùng `okr`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Có `projectId`, loại quyết định `decision` (`proceed` / `pivot` / `kill` / `hold`).
- Lý do cốt lõi và các bằng chứng thực tế liên quan.
- Ngữ cảnh đánh giá cổng (nếu có: `gateEvaluationId` được truyền như thông tin ngữ cảnh đầu vào - input context, không phải là một tool call runtime chưa khai báo).

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Trả lời các Câu hỏi Chịu lực (Load-Bearing Questions)**:
   - *Câu hỏi 1 (Vấn đề cốt lõi)*: Quyết định này giải quyết vấn đề lớn nhất nào hiện tại?
   - *Câu hỏi 2 (Đánh đổi - Tradeoffs)*: Chúng ta từ bỏ điều gì khi chọn phương án này?
   - *Câu hỏi 3 (Bằng chứng then chốt)*: Dữ liệu/bằng chứng nào khiến chúng ta tự tin ra quyết định này?
   - *Câu hỏi 4 (Rủi ro tiềm ẩn)*: Điều gì tồi tệ nhất có thể xảy ra nếu quyết định này sai?
2. **Xác lập Kết Quả Kỳ Vọng (Expected Outcomes)**:
   - Các chỉ số hoặc cột mốc cụ thể cần đạt được sau khi thực thi quyết định trong vòng 30 - 90 ngày.
3. **Ấn định Mốc Ngày Tái Đánh Giá Bắt Buộc (Revisit Date)**:
   - Bắt buộc ấn định ngày cụ thể (YYYY-MM-DD) để xem xét lại tính hiệu quả của quyết định.
4. **Soạn dự thảo bản ghi quyết định**:
   - Tổng hợp `projectId`, `decision`, `gateEvaluationId` (nếu có trong context), `notes` (rationale, tradeoffs, expected outcomes, revisit date) thành một bản ghi dự thảo hoàn chỉnh.
5. **Cập nhật định hướng & Lan tỏa**:
   - Tóm tắt tác động của quyết định tới OKR, kế hoạch 12 tuần và danh sách công việc tiếp theo.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call trực tiếp (Artifact & Proposal only). Skill này hiện chưa có capability ghi dữ liệu vào hệ thống — bản ghi quyết định là dự thảo văn bản, founder xem xét và lưu trữ chính thức thủ công.

## 6. Điểm Phê Duyệt (Approval Points)
- Không có (thuần artifact/proposal, không ghi dữ liệu). Quyết định thật do Founder/Ban điều hành phê duyệt và lưu trữ ngoài phạm vi skill này.

## 7. Safe Fallback
Agent luôn xuất toàn bộ bản ghi quyết định với đầy đủ các câu hỏi chịu lực và mốc tái đánh giá dưới dạng markdown để founder lưu trữ thủ công.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Bản Ghi Quyết Định Chiến Lược (Strategic Decision Record)

## 1. Thông Tin Quyết Định
- **Dự Án**: [ID / Tên dự án]
- **Loại Quyết Định**: [proceed / pivot / kill / hold]
- **Gate Evaluation Liên Kết (Input Context)**: [gateEvaluationId nếu có]
- **Mốc Tái Đánh Giá (Revisit Date)**: [YYYY-MM-DD]

## 2. Câu Hỏi Chịu Lực & Lập Luận (Load-Bearing Rationale)
- **Vấn đề giải quyết**: [Mô tả vấn đề cốt lõi]
- **Sự đánh đổi (Tradeoffs)**: [Điều chấp nhận từ bỏ]
- **Bằng chứng hỗ trợ**: [Dẫn chứng từ evidence synthesis / metrics]
- **Rủi ro & Giảm thiểu**: [Rủi ro chính và phương án phòng vệ]

## 3. Kết Quả Kỳ Vọng (Expected Outcomes)
- [Chỉ số / Cột mốc định lượng trong 30-90 ngày]

## 4. Tác Động Tới Kế Hoạch Tiếp Theo
- [Điều chỉnh OKR / Kế hoạch 12 tuần / Tác vụ]
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Thiếu Revisit Date**: Bắt buộc yêu cầu ấn định ngày tái đánh giá trước khi hoàn tất bản ghi để tránh tình trạng quyết định bị lãng quên.
- **Quyết định không có sự đánh đổi (Free lunch fallacy)**: Nhắc nhở người ra quyết định làm rõ các chi phí cơ hội và nguồn lực bị cắt giảm.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: coreyhaines31/makerskills
  commit: 33cb3870685a34522d91287869aef62170bdbcf7
  skill: decide
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Khung ra quyết định chiến lược, Phân loại Proceed/Pivot/Kill/Hold, Rationale và Expected outcomes
  changed:
    - Chuẩn hóa thuật ngữ COSA
    - Thêm cấu trúc 10 mục bắt buộc và định dạng markdown tiếng Việt
  added:
    - Khung câu hỏi chịu lực (Load-bearing questions)
    - Mốc ngày tái đánh giá bắt buộc (Revisit Date)
    - Nhận diện gateEvaluationId là input context
    - Safe fallback khi tool chưa khả dụng
  excluded:
    - Tự động thay đổi quyền hạn hoặc chấm dứt hợp đồng nhân sự/nhà cung cấp
```
