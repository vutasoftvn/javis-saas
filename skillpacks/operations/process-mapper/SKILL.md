---
name: operations-process-mapper
description: Lập bản đồ dòng chảy quy trình, phân tích hiệu suất chu kỳ (Value-Add vs Wait vs Rework), và phát hiện điểm nghẽn theo Theory of Constraints (TOC) và Lean Six Sigma.
---

# Lập Bản Đồ Quy Trình & Phát Hiện Điểm Nghẽn Vận Hành (Process Flow & TOC Bottleneck Analysis)

## 1. Mục Tiêu (Objective)
Cung cấp phương pháp luận và công cụ chuẩn mực để phân rã và đánh giá một quy trình nghiệp vụ nội bộ theo chuẩn BPMN và Lean Six Sigma. Trả lời câu hỏi trọng tâm của người làm vận hành: *"Công việc đang dành phần lớn thời gian nằm chờ ở đâu?"* bằng cách phân tích tỷ lệ giữa **Value-add Time** (thời gian tạo giá trị thật), **Wait Time** (thời gian chờ đợi hàng đợi/chuyển giao), và **Rework Time** (thời gian làm lại do sai sót), đồng thời áp dụng các quy tắc tất định để định vị điểm nghẽn cốt lõi (Bottleneck).

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi một quy trình (Onboarding khách hàng, xử lý khiếu nại, triển khai phần mềm, tuyển dụng) bị phản ánh là chậm trễ hoặc gây bức xúc nhưng không rõ nguyên nhân ở khâu nào.
  - Khi chuẩn bị tối ưu hóa hoặc tự động hóa một quy trình thủ công phức tạp (phải hiểu rõ dòng chảy và điểm nghẽn trước khi lập trình automation).
  - Khi rà soát vận hành định kỳ theo chu kỳ 12-Week Year (12WY) cùng COO Advisor.
- **Khi nào KHÔNG dùng**:
  - Khi quy trình hoàn toàn mới chưa từng chạy lần nào (dùng `operations.automation-design` hoặc thiết kế sơ bộ).
  - Khi chỉ cần ghi lại các bước thao tác hướng dẫn đơn giản không cần phân tích thời gian (dùng `operations.sop-builder`).
  - Khi tự ý thay đổi quy trình vận hành trực tiếp trên hệ thống mà không có sự đồng thuận của Process Owner.

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Ngữ cảnh bắt buộc: `workspace_id`, `project_id`.
- Dữ liệu đầu vào: Danh sách các công đoạn của quy trình kèm ước lượng thời gian (phút hoặc giờ) và phân loại tính chất từng công đoạn (`value_add`, `wait`, `rework`).
- Nắm vững các quy tắc chẩn đoán của `ProcessCycleAnalyzer` (`agent.operations.analyzers.process_cycle_analyzer`).

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Thu Thập Danh Sách Công Đoạn**: Liệt kê tuần tự các bước từ điểm bắt đầu (Trigger) đến điểm kết thúc (Outcome) của quy trình.
2. **Gán Nhãn Phân Loại & Đo Lường Thời Gian**:
   - Gán đúng 1 trong 3 loại: `value_add` (bước trực tiếp tạo ra giá trị cho khách hàng/kết quả cuối), `wait` (bước công việc nằm trong hàng đợi hoặc chờ duyệt), `rework` (bước sửa lỗi, trả về làm lại).
   - Xác định thời lượng trung bình (`duration_minutes`) và thời lượng trung vị (`p50_minutes`).
3. **Phân Tích Hiệu Suất Chu Kỳ Qua ProcessCycleAnalyzer**:
   - Tính tổng thời gian chu kỳ và tỷ lệ phần trăm của từng loại thời gian: $\text{Value-Add } \%$, $\text{Wait } \%$, $\text{Rework } \%$.
4. **Phát Hiện Điểm Nghẽn Theo 3 Quy Tắc TOC**:
   - *Quy tắc R1 (Stage Bottleneck)*: Công đoạn có thời gian $> 2\times$ trung bình các công đoạn sinh giá trị.
   - *Quy tắc R2 (Handoff Bottleneck)*: Tỷ lệ thời gian chờ $> 40\%$ tổng chu kỳ (cho phép hiệu chỉnh theo profile ngành).
   - *Quy tắc R3 (Quality Bottleneck)*: Tỷ lệ thời gian làm lại $> 15\%$ tổng chu kỳ.
5. **Xây Dựng Khuyến Nghị Khai Thông**:
   - Với điểm nghẽn công đoạn (R1): Đề xuất phân rã nhỏ bước, tăng năng lực xử lý hoặc tự động hóa.
   - Với điểm nghẽn chuyển giao (R2): Đề xuất tinh giản cấp duyệt, thiết lập SLA chuyển giao rõ ràng.
   - Với điểm nghẽn chất lượng (R3): Bổ sung tiêu chuẩn nghiệm thu và chốt kiểm tra tự động trước khi chuyển giao.
6. **Đóng Gói Báo Cáo Phân Tích Dòng Chảy**: Kết xuất tài liệu `process-map-audit` trình COO/Founder xem xét.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Quy trình được thực thi và kiểm thử thông qua các module chuẩn của agent.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Mọi kết luận về điểm nghẽn phải dẫn xuất từ số liệu thời gian thực tế thu thập qua phỏng vấn nhân sự hoặc log hệ thống.
- Bắt buộc đính kèm bảng phân bổ thời gian có tổng số phút và tỷ trọng phần trăm.

## 7. Safe Fallback & Nghiêm Cấm Anti-Patterns
- **CẤM TỰ ĐỘNG CẮT BỎ BƯỚC DUYỆT CỦA CON NGƯỜI:** Các đề xuất tinh giản phê duyệt chỉ ở mức khuyến nghị `L1_PROPOSE`, cấm tự ý xóa bỏ các chốt kiểm soát rủi ro.
- **CẤM TỐI ƯU HÓA CÔNG ĐOẠN KHÔNG PHẢI NÚT THẮT (TOC Principle):** Tối ưu hóa một công đoạn bất kỳ mà không phải là công đoạn nghẽn trên đường găng (Critical Path) sẽ không làm tăng thông lượng toàn hệ thống mà chỉ gây ùn ứ thêm hàng đợi.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Báo Cáo Phân Tích Dòng Chảy Quy Trình & Điểm Nghẽn (Process Flow Audit)

## 1. Thông Số Chu Kỳ Vận Hành
- **Tên quy trình**: [Tên quy trình]
- **Tổng thời gian chu kỳ**: [XXX phút]
- **Thời gian sinh giá trị thật (Value-Add)**: [XX phút] ([YY%])
- **Thời gian chờ đợi / Hàng đợi (Wait)**: [XX phút] ([YY%])
- **Thời gian làm lại do lỗi (Rework)**: [XX phút] ([YY%])

## 2. Bảng Phân Rã Các Công Đoạn
| STT | Tên Công Đoạn | Phân Loại | Thời Lượng | P50 | Ghi Chú |
|---|---|---|---|---|---|
| 1 | [Tên bước] | [value_add / wait / rework] | [XX m] | [YY m] | [Mô tả] |

## 3. Danh Sách Điểm Nghẽn Cốt Lõi Được Phát Hiện
- 🔴 **[Tên điểm nghẽn]** ([Mã quy tắc R1/R2/R3] - Mức độ: [High/Medium])
  - *Mô tả*: [Chi tiết hiện tượng tắc nghẽn]
  - *Khuyến nghị khai thông*: [Giải pháp can thiệp cụ thể]
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Thiếu dữ liệu thời gian chính xác**: Sử dụng phương pháp ước lượng 3 điểm (Three-point estimation: Best, Likely, Worst) và ghi rõ trong báo cáo là số liệu giả định cần kiểm chứng sau 2 tuần.
- **Dữ liệu mâu thuẫn**: Nếu tổng thời gian nhỏ hơn hoặc bằng 0, từ chối kết xuất báo cáo và yêu cầu bổ sung số liệu.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: alirezarezvani/claude-skills
  commit: 19392f7a08264ed00486a251f5b2098321771f94
  skill: process-mapper
  upstream_version: 2.8.0
  license: MIT
adaptation:
  kept:
    - 3 quy tắc chẩn đoán điểm nghẽn TOC (R1: Stage P50 > 2x mean, R2: Wait share > 40%, R3: Rework share > 15%)
    - Khung phân tích Lean Six Sigma (Value-Add vs Wait vs Rework)
  changed:
    - Chuyển đổi sang quy chuẩn 10 mục COSA tiếng Việt
    - Cấu hình theo mô hình profile ngành (SaaS, Services, Manufacturing)
  added:
    - Tích hợp trực tiếp với ProcessCycleAnalyzer trong packages/agent/operations/analyzers
    - Quy tắc cấm tối ưu hóa cục bộ không thuộc đường găng
  excluded:
    - Bỏ các script sinh sơ đồ Mermaid trực tiếp ở CLI; gom vào cấu trúc báo cáo artifact
```
