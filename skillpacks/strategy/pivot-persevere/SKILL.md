---
name: strategy-pivot-persevere
description: Hướng dẫn phân tích dữ liệu pilot và PMF để đề xuất quyết định Pivot, Persevere hoặc Kill cho Founder.
---

# Khung Quyết Định Pivot vs. Persevere (P4 Advisory)

## 1. Mục Tiêu (Objective)
Cung cấp cho Founder bức tranh phân tích toàn diện, đa chiều giữa các tín hiệu định lượng (PMF Scoreboard) và định tính (Customer Evidence) để đưa ra quyết định chiến lược: Tiếp tục mở rộng (Persevere), Điều chỉnh hướng đi (Pivot), hoặc Dừng dự án (Kill).

## 2. Khi Nào Dùng & Khi Nào Không Dùng
- **Khi nào dùng**:
  - Khi pilot kết thúc hoặc khi các chỉ số retention/activation đi ngang/giảm sút.
  - Khi chuẩn bị phiên họp chiến lược định kỳ của Founder.
- **Khi nào KHÔNG dùng**:
  - Khi dự án chưa có dữ liệu thử nghiệm thực tế (chưa có telemetry snapshot hoặc evidence).
  - Khi cần tự động chuyển stage (quyết định Pivot thuộc về con người, không có tool auto-pivot).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- `projectId` hợp lệ trong workspace.

## 4. Các Bước Thực Hiện (Deterministic Steps)
1. **Truy vấn trạng thái dự án**: Gọi `strategy.project.get` để lấy thông tin giai đoạn hiện tại.
2. **Lấy kết quả PMF Scoreboard**: Gọi `analytics.pmf_scoreboard.get` để đọc phân loại (`PROMISING`, `MIXED`, `CONCERNING`, `INSUFFICIENT_DATA`) và các cảnh báo thiếu hụt/độ tin cậy dữ liệu.
3. **Tổng hợp bằng chứng khách hàng**: Gọi `strategy.evidence.list` để đánh giá mức độ hài lòng, sự sẵn sàng chi trả và phản hồi tiêu cực.
4. **Phân tích đối chiếu 3 kịch bản**:
   - **Persevere**: Nếu PMF Scoreboard là `PROMISING` và retention ổn định.
   - **Pivot (Customer / Problem / Solution / Growth Engine)**: Nếu PMF Scoreboard là `MIXED` hoặc `CONCERNING` nhưng có nhóm khách hàng ngách thể hiện sự gắn kết cao.
   - **Kill / Park**: Nếu toàn bộ giả định cốt lõi bị bác bỏ và chi phí duy trì vượt quá tiềm năng.
5. **Trình bày Decision Memo**: Lập bản ghi nhớ cố vấn (Advisory Memo) để Founder xem xét.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `strategy.project.get`: Đọc thông tin dự án.
- `analytics.pmf_scoreboard.get`: Đọc kết quả bảng điểm PMF đã tính toán.
- `strategy.evidence.list`: Đọc danh sách bằng chứng đã duyệt.

## 6. Điểm Phê Duyệt (Approval Points)
- Quyết định chiến lược cuối cùng hoàn toàn thuộc thẩm quyền của Founder (Human Authorization).

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Bản Ghi Nhớ Cố Vấn Chiến Lược (Pivot / Persevere Memo)
- **Dự Án**: [Project ID / Title]
- **Tín Hiệu PMF Scoreboard**: [PROMISING | MIXED | CONCERNING | INSUFFICIENT_DATA]
- **Đánh Giá Trọng Yếu**:
  - *Điểm mạnh đã kiểm chứng*: [Danh sách]
  - *Rủi ro & Khoảng trống dữ liệu*: [Danh sách]
- **Khuyến Nghị Cố Vấn**: [Persevere / Pivot đề xuất / Kill]
- **Hành Động Tiếp Theo Cho Founder**: [Danh sách việc cần làm]
```
