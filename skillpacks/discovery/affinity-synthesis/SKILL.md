---
name: discovery-affinity-synthesis
description: Quy trình tổng hợp ghi chú phỏng vấn và phản hồi khách hàng thành các cụm insight có bằng chứng.
---

# Quy Trình Tổng Hợp Affinity Diagram & Nhóm Insight

## 1. Mục Tiêu (Objective)
Cung cấp phương pháp hệ thống để gom cụm các trích dẫn, phản hồi và quan sát phỏng vấn thành các nhóm chủ đề, từ đó ghi nhận các evidence candidate hỗ trợ quyết định giai đoạn P4.

## 2. Khi Nào Dùng & Khi Nào Không Dùng
- **Khi nào dùng**:
  - Đã hoàn thành 3-10 cuộc phỏng vấn khám phá khách hàng hoặc pilot debrief.
  - Cần chuyển đổi ghi chú phân tán thành các phát hiện có cấu trúc.
- **Khi nào KHÔNG dùng**:
  - Khi cần tính toán chỉ số định lượng telemetry (dùng `analytics.pmf-scoreboard`).
  - Khi cần gửi tin nhắn trực tiếp cho khách hàng (dùng `engagement.message.send`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- `projectId` hợp lệ trong workspace.
- Danh sách ghi chú phỏng vấn hoặc raw feedback từ khách hàng.

## 4. Các Bước Thực Hiện (Workflow Steps)
1. **Truy vấn bằng chứng hiện có**: Gọi `strategy.evidence.list` với `projectId` để nắm bối cảnh.
2. **Trích xuất quan sát**: Đọc ghi chú và phân rã thành các mẩu dữ liệu độc lập (Quotes, Pains, Desires, Workarounds).
3. **Gom cụm Affinity**: Nhóm các mẩu dữ liệu tương đồng vào từng chủ đề lớn (Themes/Patterns).
4. **Xác định tuyên bố giá trị**: Rút ra kết luận cốt lõi cho mỗi cụm và đánh giá độ mạnh/tin cậy.
5. **Tạo Evidence Candidate**: Gọi tool `strategy.evidence.create` để lưu trữ bằng chứng vào hệ thống cho Founder duyệt.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `strategy.evidence.list`: Đọc danh sách bằng chứng hiện tại của dự án.
- `strategy.evidence.create`: Tạo bản ghi bằng chứng mới ở trạng thái candidate.

## Referenced Capabilities (not callable)
- `engagement.message.send`: hand off gửi tin nhắn trực tiếp cho khách hàng cho
  quy trình engagement đã phê duyệt — không gọi trực tiếp từ skillpack này.

## 6. Điểm Phê Duyệt (Approval Points)
- Bằng chứng tạo ra luôn ở trạng thái `candidate` (chờ Founder/DRI duyệt, không tự động duyệt).

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Bảng Tổng Hợp Affinity Diagram
- **Dự Án**: [ID / Title]
- **Số Lượng Phỏng Vấn Phân Tích**: [N]
- **Các Cụm Chủ Đề Chính**:
  1. **[Tên Cụm 1]** (Số quan sát: [X])
     - *Insight cốt lõi*: [Mô tả ngắn]
     - *Trích dẫn đại diện*: "[Trích dẫn thực tế]"
     - *Evidence ID được đề xuất*: `candidate`
```

## 8. Xử Lý Lỗi & Edge Cases
- Nếu các quan sát mâu thuẫn nhau: Tách thành 2 cụm độc lập và ghi chú phân khúc người dùng khác nhau.
- **Cảnh báo thiên lệch mẫu (response/sample bias)**: Nếu phần lớn phỏng vấn/phản hồi đến từ một nhóm khách hàng hẹp (ví dụ chỉ khách hàng hài lòng tự nguyện phản hồi, hoặc một phân khúc/kênh duy nhất), phải ghi rõ giới hạn lệch mẫu này trong evidence candidate và không được khái quát hóa kết luận cho toàn bộ tệp khách hàng.
