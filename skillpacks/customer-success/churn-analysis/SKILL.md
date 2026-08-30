---
name: customer-success-churn-analysis
description: Hướng dẫn thực hiện phân tích nguyên nhân gốc rễ khách hàng rời bỏ và lưu trữ bằng chứng cải tiến.
---

# Quy Trình Phân Tích Khách Hàng Rời Bỏ (Churn Root Cause Audit)

## 1. Mục Tiêu (Objective)
Điều tra có hệ thống các trường hợp hủy gói/dừng sử dụng để phân loại nguyên nhân cốt lõi (sản phẩm không phù hợp, giá bán, chất lượng dịch vụ, hay đối thủ cạnh tranh), từ đó đưa ra các phản hồi cải tiến cho Product và Strategy.

## 2. Khi Nào Dùng & Khi Nào Không Dùng
- **Khi nào dùng**:
  - Khi có khách hàng pilot hoặc khách hàng trả phí thông báo dừng sử dụng.
  - Phân tích xu hướng rời bỏ định kỳ hàng tháng/quý.
- **Khi nào KHÔNG dùng**:
  - Khi xử lý khiếu nại đang cần hỗ trợ kỹ thuật tức thời.

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- `projectId` hợp lệ trong workspace.

## 4. Các Bước Thực Hiện (Deterministic Steps)
1. **Kiểm tra Metric Contracts**: Gọi `analytics.metric_contract.get` để đối chiếu với các ngưỡng mục tiêu về retention/churn của dự án.
2. **Thu thập dữ liệu Exit Interview & Usage Log**:
   - Phỏng vấn ngắn gọn người quyết định hủy hoặc phân tích tin nhắn phản hồi lý do.
3. **Phân loại nguyên nhân theo 4 nhóm chính**:
   - **Bad Fit ICP**: Khách hàng không thuộc tệp mục tiêu ban đầu.
   - **Missing Feature / UX**: Thiếu tính năng cốt lõi hoặc trải nghiệm khó dùng.
   - **Value vs. Price**: Khách hàng không nhận đủ giá trị tương xứng với chi phí bỏ ra.
   - **Champion Left / Org Change**: Người ủng hộ nội bộ chuyển công tác hoặc công ty tái cấu trúc.
4. **Tạo Evidence Candidate**: Gọi `strategy.evidence.create` để ghi nhận bằng chứng phản bác (refutes claim) hoặc bằng chứng cải tiến cho Product Backlog.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `analytics.metric_contract.get`: Đọc hợp đồng chỉ số đo lường.
- `strategy.evidence.create`: Tạo bản ghi bằng chứng từ phân tích rời bỏ.

## 6. Điểm Phê Duyệt (Approval Points)
- Bằng chứng tạo mới ở trạng thái `candidate` chờ Founder xem xét.
- **Cấm sử dụng thuộc tính nhạy cảm/được bảo vệ** (ví dụ: giới tính, chủng tộc, tôn giáo, độ tuổi, tình trạng khuyết tật, nguồn gốc quốc gia) làm tín hiệu để phân loại nguyên nhân rời bỏ — chỉ dùng dữ liệu sản phẩm, giá, dịch vụ và bối cảnh tổ chức khách hàng.
- Đầu ra là tín hiệu/bằng chứng cố vấn có thể giải thích; skill không tự động thực hiện hành động lên tài khoản (không tự hủy/giữ chân, không tự gửi ưu đãi).

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Báo Cáo Phân Tích Rời Bỏ (Churn Post-Mortem Card)
- **Tài Khoản / Khách Hàng**: [Tên / Phân Khúc]
- **Nhóm Nguyên Nhân Chính**: [Bad Fit ICP | Missing Feature | Value/Price | Org Change]
- **Tóm Tắt Phân Tích**: [Mô tả chi tiết bối cảnh và lý do]
- **Hành Động Khắc Phục Đề Xuất**: [Cải tiến sản phẩm / Điều chỉnh ICP]
- **Bằng Chứng Tạo Mới**: `candidate`
```
