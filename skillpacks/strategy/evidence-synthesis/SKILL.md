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
2. **Xác định `sourceType` và dữ liệu thô**: Chọn đúng loại nguồn (`financial_transaction`, `customer_interview`, `prototype_test`, `experiment_metric`, `survey`, `3rd_party_data`, `observation`) — backend tự tính `strength`/`confidence` tất định từ `sourceType` + `rawStrength`/`rawConfidence`/`sampleSize` (nếu có), agent KHÔNG tự gán mức độ mạnh/yếu.
3. **Ghi nhận bằng chứng**: Gọi tool `strategy.evidence.create` với `companyId`, `workspaceId`, `projectId`, `experimentId`, `sourceType`, `claim` (nội dung bằng chứng), `rawStrength`/`rawConfidence`/`sampleSize` nếu có số liệu thô, `supportsOrRefutes` (`supports`/`refutes`/`neutral`).
4. **Kết luận tác động**: Dựa trên `strength`/`confidence` backend trả về, đánh giá giả định tương ứng đã được xác thực (Validated), bác bỏ (Invalidated), hay cần thêm dữ liệu (Inconclusive).

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
- Dữ liệu mâu thuẫn: Nếu các nhóm khách hàng cho kết quả trái ngược, ghi nhận `claim` mô tả rõ mâu thuẫn và đề xuất phân khúc khách hàng sâu hơn — không tự làm tròn thành 1 kết luận đơn giản hoá.
- Mẫu thử quá nhỏ: Truyền `sampleSize` thật để backend tính `confidence` phản ánh đúng độ tin cậy thấp, không tự ý nâng `rawConfidence`.

## 9. Ví Dụ Thực Tế (Practical Examples)
- **Input**: "Landing page thu hút 500 visitors, 45 người đăng ký email để lại số điện thoại (tỷ lệ 9%)."
- **Execution**: Gọi `strategy.evidence.create` với `sourceType: "experiment_metric"`, `claim: "500 visitors, 45 waitlist signups (9% conversion)"`, `sampleSize: 500`.

## 10. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Mọi bằng chứng phải gắn liền với nguồn dữ liệu cụ thể và số liệu định lượng có thể kiểm chứng.
