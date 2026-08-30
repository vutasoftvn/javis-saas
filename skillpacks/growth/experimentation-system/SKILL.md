---
name: growth-experimentation-system
description: Hướng dẫn thiết kế và ghi nhận các thử nghiệm tăng trưởng gắn với Metric Contract.
---

# Hệ Thống Thử Nghiệm Tăng Trưởng Khoa Học (Growth Experimentation)

## 1. Mục Tiêu (Objective)
Xây dựng chu trình thử nghiệm tăng trưởng có kỷ luật: Phát biểu giả thuyết rõ ràng, gắn với hợp đồng chỉ số (Metric Contract) đo lường cụ thể, và ghi nhận kết quả để đưa ra quyết định tiếp tục/dừng.

## 2. Khi Nào Dùng & Khi Nào Không Dùng
- **Khi nào dùng**:
  - Muốn tối ưu kênh chuyển đổi, activation funnels, hoặc thử nghiệm giá bán/ưu đãi.
  - Chuẩn bị chạy A/B test hoặc multivariate test trên tệp người dùng thực.
- **Khi nào KHÔNG dùng**:
  - Khi chưa có hệ thống đo lường (chưa thiết lập Metric Contract).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- `projectId` hợp lệ trong workspace.

## 4. Các Bước Thực Hiện (Deterministic Steps)
1. **Kiểm tra Metric Contracts**: Gọi `analytics.metric_contract.get` để xác định chỉ số mục tiêu (Primary Metric) cho thử nghiệm.
2. **Cấu trúc hóa giả thuyết**:
   - *Nếu chúng tôi làm [Hành động], thì [Chỉ số mục tiêu] sẽ tăng từ [A] lên [B], bởi vì [Lý do hành vi].*
3. **Xác định quy mô mẫu & thời gian**: Tính toán số lượng mẫu tối thiểu để đạt độ tin cậy thống kê (Confidence 95%).
4. **Ghi nhận Thử Nghiệm**: Gọi `commercial.experiment.write` để lưu trữ bản nháp thử nghiệm vào hệ thống.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `analytics.metric_contract.get`: Đọc thông tin hợp đồng chỉ số đo lường.
- `commercial.experiment.write`: Tạo hoặc cập nhật thông tin thử nghiệm.

## 6. Điểm Phê Duyệt (Approval Points)
- Thử nghiệm tạo mới cần Founder/Lead phê duyệt trước khi kích hoạt phân bổ lưu lượng (Traffic allocation).

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Hồ Sơ Thiết Kế Thử Nghiệm (Growth Experiment Card)
- **Tên Thử Nghiệm**: [Tên]
- **Giả Thuyết (Hypothesis)**: [Câu phát biểu giả thuyết]
- **Chỉ Số Mục Tiêu (Primary Metric)**: [Tên chỉ số từ Metric Contract]
- **Biến Thể (Variants)**: Control (A) vs. Test (B)
- **Thời Gian Dự Kiến**: [Số tuần / ngày]
```
