---
name: strategy.evidence-synthesis
description: Quy trình tổng hợp, phân tích và đánh giá độ mạnh của bằng chứng thực nghiệm (Evidence Synthesis) hỗ trợ ra quyết định chiến lược.
---

# Quy Trình Tổng Hợp Và Đánh Giá Bằng Chứng Thực Nghiệm (Evidence Synthesis)

## 1. Mục Tiêu (Objective)
Thu thập kết quả từ thử nghiệm, khảo sát hoặc phỏng vấn, đánh giá độ tin cậy và sức mạnh của bằng chứng (`weak`, `medium`, `strong`), hỗ trợ xác thực hoặc bác bỏ giả định.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi hoàn thành 1 chu kỳ thử nghiệm hoặc đợt phỏng vấn người dùng.
  - Cần đánh giá xem dữ liệu thu được đã đủ vững chắc để chuyển stage hoặc ra quyết định chưa.
- **Khi nào KHÔNG dùng**:
  - Khi chưa có dữ liệu thực tế và chỉ đang dự đoán (dùng `strategy.experiment-design`).
  - Khi cần chốt quyết định chiến lược hoặc pivot chính thức (dùng `strategy.decision-capture`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Có `projectId` và dữ liệu thô từ thử nghiệm / khảo sát.

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Lấy danh sách bằng chứng hiện tại**: Gọi `strategy.evidence.list` với `projectId`.
2. **Đánh giá mức độ bằng chứng (Evidence Strength)**:
   - *Weak*: Ý kiến chủ quan, khảo sát không cam kết, số lượng mẫu nhỏ (<5).
   - *Medium*: Hành vi người dùng gián tiếp, đăng ký waitlist, số lượng phỏng vấn 10-20.
   - *Strong*: Đặt cọc tiền thật (pre-payment), hợp đồng LOI có giá trị ràng buộc, dữ liệu chuyển đổi lớn có ý nghĩa thống kê.
3. **Ghi nhận bằng chứng**: Gọi tool `strategy.evidence.create` với `projectId`, `experimentId`, `assumptionId`, `type`, `strength`, `summary`, `data`.
4. **Kết luận tác động**: Đánh giá giả định tương ứng đã được xác thực (Validated), bác bỏ (Invalidated), hay cần thêm dữ liệu (Inconclusive).

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `strategy.evidence.list`: Lấy danh sách bằng chứng đã lưu.
- `strategy.evidence.create`: Lưu trữ bản ghi bằng chứng mới.

## 6. Điểm Phê Duyệt (Approval Points)
- `strategy.evidence.create` có `risk_level: medium`, yêu cầu policy kiểm tra quyền ghi dữ liệu (`MODIFY_BUSINESS_DATA`).

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Báo Cáo Tổng Hợp Bằng Chứng (Evidence Synthesis)
- **Dự Án**: [ID / Tên dự án]
- **Tóm Tắt Bằng Chứng**: [Mô tả dữ liệu thu được]
- **Độ Mạnh (Strength)**: [Weak / Medium / Strong]
- **Tác Động Tới Giả Định**: [Validated / Invalidated / Inconclusive]
- **Khuyến Nghị**: [Gợi ý bước tiếp theo]
```

## 8. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- Dữ liệu mâu thuẫn: Nếu các nhóm khách hàng cho kết quả trái ngược, đánh giá `strength: medium` và đề xuất phân khúc khách hàng sâu hơn.
- Mẫu thử quá nhỏ: Cảnh báo nguy cơ false positive / false negative.

## 9. Ví Dụ Thực Tế (Practical Examples)
- **Input**: "Landing page thu hút 500 visitors, 45 người đăng ký email để lại số điện thoại (tỷ lệ 9%)."
- **Execution**: Đánh giá `strength: medium` -> Gọi `strategy.evidence.create` với summary tương ứng.

## 10. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Mọi bằng chứng phải gắn liền với nguồn dữ liệu cụ thể và số liệu định lượng có thể kiểm chứng.
