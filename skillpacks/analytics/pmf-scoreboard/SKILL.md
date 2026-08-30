---
name: analytics-pmf-scoreboard
description: Hướng dẫn giải thích bảng điểm PMF tái lập được và trình bày đề xuất cố vấn cho Founder.
---

# Quy Trình Diễn Giải Bảng Điểm PMF (PMF Scoreboard Advisory)

## 1. Mục Tiêu (Objective)
Truy vấn bảng điểm PMF đã tính toán tất định trong Company Services và cấu trúc hóa đề xuất cố vấn thành 3 thành phần rõ ràng: **ACTION** (hành động tiếp theo), **DECISION** (quyết định khuyến nghị), **LEARN** (bài học và cờ cảnh báo dữ liệu).

## 2. Khi Nào Dùng & Khi Nào Không Dùng
- **Khi nào dùng**:
  - Founder cần xem tiến độ PMF hiện tại của dự án.
  - Chuẩn bị bước vào phiên thẩm định Gate G4 hoặc xem xét phân bổ ngân sách.
- **Khi nào KHÔNG dùng**:
  - Khi muốn tự ý can thiệp thuật toán hoặc tính điểm ngẫu hứng bằng LLM (mọi phép tính phải thực hiện qua backend company services).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- `projectId` hợp lệ trong workspace.

## 4. Các Bước Thực Hiện (Deterministic Steps)
1. **RÀNG BUỘC CỨNG (INVARIANT §5.2)**:
   > **Skill tuyệt đối KHÔNG ĐƯỢC tự tính điểm số hoặc tự quyết định kết quả PMF bằng mô hình ngôn ngữ**.
   > Bắt buộc phải gọi `analytics.pmf_scoreboard.get` để lấy kết quả tính toán tất định hoặc gọi `analytics.pmf_scoreboard.propose` để tạo bản ghi nhớ cố vấn.
2. **Kiểm tra Metric Contracts**: Gọi `analytics.metric_contract.get` để xác nhận các hợp đồng chỉ số đang hoạt động.
3. **Lấy kết quả Scoreboard Run**: Gọi `analytics.pmf_scoreboard.get` với `projectId` để đọc:
   - Phân loại: `PROMISING`, `MIXED`, `CONCERNING`, hoặc `INSUFFICIENT_DATA`.
   - `calculationHash`: Mã hash bất biến của lượt tính toán.
   - `missingDataFlags` & `reliabilityFlags`: Các cảnh báo về dữ liệu thiếu hoặc dữ liệu cũ (stale).
4. **Tạo Đề Xuất Cố Vấn**: Gọi `analytics.pmf_scoreboard.propose` để chuẩn bị memo hành động.
5. **Trình bày trực quan**: Diễn giải các thành phần điểm số, cảnh báo chất lượng dữ liệu và gợi ý bước tiếp theo cho Founder.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `analytics.metric_contract.get`: Đọc hợp đồng chỉ số đo lường.
- `analytics.pmf_scoreboard.get`: Đọc kết quả tính toán bảng điểm PMF.
- `analytics.pmf_scoreboard.propose`: Tạo đề xuất cố vấn dựa trên kết quả tính toán.

## 6. Điểm Phê Duyệt (Approval Points)
- Không có quyền tự động chuyển stage. Mọi chuyển đổi Gate đòi hỏi Founder phê duyệt có chữ ký kiểm toán.

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Bảng Điểm PMF & Cố Vấn Chiến Lược
- **Dự Án**: [ID / Title]
- **Phân Loại PMF**: [PROMISING | MIXED | CONCERNING | INSUFFICIENT_DATA]
- **Mã Kiểm Toán (Calculation Hash)**: `[Hash]`
- **Chất Lượng Dữ Liệu**:
  - *Missing Flags*: [Danh sách cờ thiếu dữ liệu nếu có]
  - *Reliability Flags*: [Danh sách cờ độ tin cậy/stale nếu có]
- **Đề Xuất Cố Vấn (Memo)**:
  - **ACTION**: [Hành động tiếp theo đề xuất]
  - **DECISION**: [Khuyến nghị quyết định]
  - **LEARN**: [Bài học rút ra từ dữ liệu]
- **Người Phụ Trách (Human Owner)**: Founder / Product DRI
```
