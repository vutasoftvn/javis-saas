---
name: operations-capacity-planner
description: Định biên nhân sự vận hành và hỗ trợ khách hàng dựa trên lý thuyết hàng đợi Erlang-C, tính toán tỷ lệ khai thác, cảnh báo nguy cơ kiệt sức và lập lộ trình tuyển dụng theo tuần 12WY.
---

# Quy Hoạch Năng Lực Đội Ngũ & Định Biên Vận Hành (Erlang-C Capacity Planning)

## 1. Mục Tiêu (Objective)
Cung cấp phương pháp định biên quy mô nhân sự (Workforce Sizing) dựa trên cơ sở toán học hàng đợi **Erlang-C**, áp dụng cho đội ngũ vận hành, trực ca hỗ trợ khách hàng (CS), onboard và xử lý yêu cầu nội bộ. Giúp Founder và COO trả lời dứt khoát câu hỏi: *"Đội ngũ hiện tại có đủ quy mô để đáp ứng nhu cầu cao điểm mà không bị kiệt sức (burnout) hay làm vỡ cam kết SLA không?"*.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi lập kế hoạch nhân sự cho chu kỳ 12-Week Year (12WY) mới dựa trên dự báo tăng trưởng người dùng hoặc khối lượng ticket.
  - Khi tỷ lệ phản hồi chậm trễ tăng cao và Founder cần biết chính xác cần tuyển thêm bao nhiêu người để đạt SLA mong muốn.
  - Khi muốn kiểm tra xem đội ngũ có đang hoạt động vượt ngưỡng an toàn ($Utilization > 85\%$) dẫn tới nguy cơ nghỉ việc hàng loạt.
- **Khi nào KHÔNG dùng**:
  - Khi quy hoạch năng lực kỹ sư phần mềm / sprint velocity (dùng `vpe-advisor` hoặc `engineering_capacity`).
  - Khi tính toán chi phí lương và thang bảng lương chi tiết (dùng `chro-advisor` hoặc `finance.cfo-review`).
  - Khi tự động phát lệnh đăng tuyển hoặc sa thải nhân sự trên các cổng tuyển dụng.

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Ngữ cảnh: `workspace_id`, `project_id`.
- Dữ liệu đầu vào:
  - Khối lượng yêu cầu đến mỗi giờ trong giờ cao điểm ($\lambda$ requests/hour).
  - Thời gian xử lý trung bình mỗi yêu cầu ($AHT$ theo phút).
  - Mục tiêu SLA dịch vụ (ví dụ: $80\%$ yêu cầu được tiếp nhận trong vòng $120$ giây).
- Nắm vững các hàm tính toán của `WorkforceCapacityModeler` (`agent.operations.analyzers.workforce_capacity_modeler`).

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Thu Thập Thông Số Tải Thực Tế**:
   - Xác định tốc độ yêu cầu đến trung bình và cao điểm trong tuần.
   - Đo lường thời gian xử lý trung bình ($AHT$) từ dữ liệu log hoặc hệ thống ticket.
2. **Tính Toán Cường Độ Lưu Lượng (Traffic Intensity)**:
   - Tính thông số Erlangs: $A = (\lambda / 60) \times AHT$.
3. **Mô Hình Hóa Bằng Thuật Toán Erlang-C**:
   - Sử dụng `WorkforceCapacityModeler.calculate_erlang_c` để tìm số lượng nhân sự trực tiếp nhỏ nhất ($N$) thỏa mãn cả 2 điều kiện:
     1. $N > A$ (Đảm bảo hàng đợi không bị bùng nổ vô hạn).
     2. Tỷ lệ phục vụ đạt mục tiêu $SLA$ đặt ra.
4. **Kiểm Soát Tỷ Lệ Khai Thác & Ngưỡng Kiệt Sức (Burnout Check)**:
   - Tính tỷ lệ khai thác $Utilization = A / N$.
   - Nếu $Utilization > 85\%$, kích hoạt cờ cảnh báo đỏ `burnout_warning: true` và đề xuất bổ sung nhân sự dự phòng (Buffer Headcount) để đảm bảo độ bền vững của con người.
5. **Lập Lộ Trình Tuyển Dụng Theo Chu Kỳ 12WY (Hiring Sequencer)**:
   - Dự phóng nhu cầu qua 12 tuần của chu kỳ 12WY.
   - Lùi lại thời gian tuyển dụng và đào tạo hòa nhập (Ramp-up, thường từ 2 - 4 tuần) để khuyến nghị chính xác tuần nào Founder cần duyệt tuyển dụng.
6. **Đóng Gói Báo Cáo Định Biên Artifact**: Kết xuất tài liệu `capacity-plan-report` trình COO và Founder.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Quy trình được thực thi và kiểm thử thông qua các module chuẩn của agent.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Khối lượng yêu cầu và thời gian xử lý phải có nguồn trích xuất từ dữ liệu thực tế (ticket log, call log) hoặc kịch bản tăng trưởng kinh doanh đã được duyệt.
- Kết quả báo cáo phải ghi rõ công thức tính và xác suất phải chờ $P(W>0)$.

## 7. Safe Fallback & Nghiêm Cấm Anti-Patterns
- **CẤM TÍNH TOÁN TUYẾN TÍNH ĐƠN GIẢN (Average-based Sizing Anti-Pattern):** Cấm lấy tổng số giờ chia đều cho 8 tiếng/ngày mà không tính đến tính chất ngẫu nhiên và đỉnh nhọn của dòng yêu cầu đến (Queueing bursts). Bắt buộc phải áp dụng Erlang-C.
- **CẤM ÉP TỶ LỆ KHAI THÁC 100%:** Trong vận hành thực tế, khi utilization tiệm cận $100\%$, thời gian chờ trong hàng đợi sẽ tiến tới vô cùng theo định luật Kingman.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Báo Cáo Định Biên Năng Lực Đội Ngũ (Workforce Capacity Plan)

## 1. Thông Số Tải Đầu Vào
- **Tốc độ yêu cầu cao điểm ($\lambda$)**: [XX yêu cầu / giờ]
- **Thời gian xử lý trung bình ($AHT$)**: [YY phút / yêu cầu]
- **Cường độ lưu lượng ($A$)**: [ZZ.Z Erlangs]
- **Mục tiêu cam kết SLA**: [XX% tiếp nhận trong YY giây]

## 2. Kết Quả Định Biên Erlang-C
- **Số lượng nhân sự khuyến nghị ($N$)**: **[NN người]**
- **Tỷ lệ dịch vụ thực tế đạt được**: [XX.X%]
- **Xác suất yêu cầu phải chờ trong hàng đợi $P(W>0)$**: [YY.Y%]
- **Tỷ lệ khai thác (Utilization)**: [ZZ.Z%] — **[AN TOÀN / CẢNH BÁO QUÁ TẢI]**

## 3. Lộ Trình Tuyển Dụng 12-Week Year (Hiring Milestones)
| Tuần 12WY | Nhu Cầu Dự Phóng | Nhân Sự Cần Có | Nhân Sự Hiện Có | Thâm Hụt | Tuần Phải Tuyển (Lead Time) |
|---|---|---|---|---|---|
| W1 | [X req/h] | [N] | [N] | 0 | - |
| W6 | [X req/h] | [N+2] | [N] | 2 | W2 (Cần duyệt tuyển trước 4 tuần) |
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Tải đột biến ngắn hạn (Spike Traffic)**: Khi có sự kiện ra mắt tính năng lớn, đề xuất kích hoạt nhân sự dự phòng chéo giữa các phòng ban (Swarm Support) thay vì tuyển dụng biên chế cố định.
- **Dữ liệu đầu vào bằng 0 hoặc âm**: Trả về kế hoạch rỗng với cảnh báo dữ liệu không hợp lệ.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: alirezarezvani/claude-skills
  commit: 19392f7a08264ed00486a251f5b2098321771f94
  skill: capacity-planner
  upstream_version: 2.8.0
  license: MIT
adaptation:
  kept:
    - Lý thuyết toán hàng đợi Erlang-C và công thức xác suất chờ P(W>0)
    - Ngưỡng kiệt sức đội ngũ 85% utilization
  changed:
    - Chuyển đổi sang quy chuẩn 10 mục COSA tiếng Việt
    - Tích hợp chuỗi tuyển dụng với nhịp tuần 12WY (W1 - W12)
  added:
    - Tích hợp trực tiếp với WorkforceCapacityModeler trong packages/agent/operations/analyzers
    - Định luật Kingman chống anti-pattern tính toán trung bình tuyến tính
  excluded:
    - Bỏ các script shell vẽ đồ thị ASCII ở terminal
```
