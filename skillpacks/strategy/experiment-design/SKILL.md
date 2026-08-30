---
name: strategy-experiment-design
description: Quy trình thiết kế thử nghiệm chiến lược tinh gọn (Lean Experiments), khung giả thuyết định lượng, tính toán mẫu và cây quyết định phân nhánh.
---

# Quy Trình Thiết Kế Thử Nghiệm Kiểm Chứng Giả Định (Experiment Design)

## 1. Mục Tiêu (Objective)
Thiết kế các thử nghiệm tinh gọn (Lean Experiments) nhằm thu thập bằng chứng xác thực hoặc bác bỏ giả định với chi phí, nguồn lực và thời gian tối thiểu; chuẩn hóa khung giả thuyết, chỉ số định lượng và kế hoạch hành động tương ứng với kết quả thử nghiệm.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Đã có giả định quan trọng cần kiểm chứng (từ `strategy.assumption-discovery` hoặc `marketing.positioning`).
  - Cần xác định phương pháp test, chỉ số đo lường (metric), cỡ mẫu (sample size) và ngưỡng đạt (success criteria).
  - Cần lập kế hoạch phân nhánh quyết định trước khi bắt đầu thu thập dữ liệu.
- **Khi nào KHÔNG dùng**:
  - Khi chưa có giả định cụ thể nào (dùng `strategy.assumption-discovery` trước).
  - Khi đã có dữ liệu thực tế cần phân tích độ mạnh bằng chứng (dùng `strategy.evidence-synthesis`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Có `projectId` và `assumptionId` (hoặc nội dung giả định cụ thể cần kiểm chứng).

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Chuẩn Hóa Khung Giả Thuyết (Hypothesis Framework)**:
   - Viết giả thuyết theo cấu trúc chuẩn:
     *"NẾU [hành động / giải pháp thử nghiệm], THÌ [kết quả đo lường được], BỞI VÌ [lý do / động lực hành vi của khách hàng]."*
2. **Lựa Chọn Phương Pháp Thử Nghiệm Tinh Gọn**:
   - *Discovery Interview*: Phỏng vấn sâu 1-1 (kiểm chứng vấn đề và nỗi đau).
   - *Smoke Test / Landing Page*: Trang web giới thiệu kèm nút đặt trước / đăng ký waitlist (kiểm chứng nhu cầu thực tế).
   - *Concierge / Wizard of Oz*: Cung cấp giải pháp thủ công phía sau hậu trường (kiểm chứng tính khả thi và giá trị dịch vụ).
   - *Interactive Prototype*: Bản mẫu tương tác (kiểm chứng trải nghiệm sử dụng và độ hiểu sản phẩm).
3. **Xác Định Hệ Chỉ Số & Ngưỡng Thành Công (Metrics & Thresholds)**:
   - *Primary Metric (Chỉ số chính)*: Chỉ số quyết định trực tiếp giả thuyết (ví dụ: *Tỷ lệ đặt cọc >= 5%*).
   - *Secondary Metric (Chỉ số phụ)*: Chỉ số bổ trợ (ví dụ: *Thời gian trung bình trên trang >= 2 phút*).
   - *Guardrail Metric (Chỉ số bảo vệ)*: Đảm bảo không gây tác dụng phụ tiêu cực (ví dụ: *Tỷ lệ khiếu nại <= 1%*).
4. **Xác Định Cỡ Mẫu & Thời Lượng Thử Nghiệm (Sample Size & Duration)**:
   - Đặt thời lượng giới hạn từ 1-2 tuần (Timebox).
   - Cỡ mẫu tối thiểu: Định lượng (ví dụ: tối thiểu 200 lượt xem landing page) hoặc định tính (ví dụ: tối thiểu 10 cuộc phỏng vấn chất lượng cao).
5. **Thiết Lập Khung Quyết Định Phân Nhánh (Decision Log Framework)**:
   - *Kịch bản 1: Validated (Đạt ngưỡng)* -> Chuyển sang giai đoạn phát triển tiếp theo hoặc mở rộng quy mô.
   - *Kịch bản 2: Invalidated (Dưới ngưỡng)* -> Xem xét điều chỉnh giả định hoặc pivot phương án giải pháp.
   - *Kịch bản 3: Inconclusive (Không đủ dữ liệu)* -> Tối ưu kênh phân phối hoặc chạy thêm 1 chu kỳ với mẫu lớn hơn.
6. **Tạo Bản Ghi Thử Nghiệm**:
   - Gọi tool `strategy.experiment.create` với `companyId`, `workspaceId`, `projectId`, `assumptionId`, `hypothesis`, `method`, `successCriteria`.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này. Agent tổng hợp và xuất bản thảo kế hoạch thử nghiệm để founder xem xét và quyết định.

## 6. Điểm Phê Duyệt (Approval Points)
- `strategy.experiment.create` có `risk_level: medium`, yêu cầu policy kiểm tra quyền ghi dữ liệu (`MODIFY_BUSINESS_DATA`).

## 7. Safe Fallback
Khi tool `strategy.experiment.create` chưa khả dụng trong runtime, agent xuất toàn bộ kế hoạch thử nghiệm và khung giả thuyết định lượng dưới dạng markdown hoàn chỉnh để người dùng triển khai thủ công.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Kế Hoạch Thiết Kế Thử Nghiệm Chiến Lược

## 1. Giả Thuyết Thử Nghiệm (Hypothesis)
- **Giả định gốc**: [Nội dung giả định cần kiểm chứng]
- **Khung Giả Thuyết**: *"Nếu [Hành động], thì [Kết quả], vì [Lý do]."*

## 2. Phương Pháp & Quy Trình Triển Khai
- **Phương pháp lựa chọn**: [Landing Page / Phỏng vấn / Concierge / Prototype]
- **Thời lượng thực thi**: [1-2 tuần]
- **Cỡ mẫu tối thiểu (Minimum Sample Size)**: [Số lượng người dùng / lượt xem]

## 3. Hệ Chỉ Số Đo Lường
- **Primary Metric**: [Chỉ số chính] -> **Ngưỡng thành công (Success Threshold)**: [>= X%]
- **Secondary Metrics**: [Các chỉ số bổ trợ]
- **Guardrail Metrics**: [Chỉ số bảo vệ an toàn]

## 4. Cây Quyết Định Phân Nhánh (Decision Branching Plan)
- **Nếu Validated**: [Hành động cụ thể]
- **Nếu Invalidated**: [Phương án điều chỉnh / Pivot]
- **Nếu Inconclusive**: [Kế hoạch thu thập thêm dữ liệu]
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Tiêu chí thành công cảm tính**: Bắt buộc người dùng hoặc kế hoạch phải định lượng hóa tiêu chí (từ chối các tiêu chí mơ hồ như "khách hàng thấy hứng thú").
- **Chi phí thử nghiệm quá lớn**: Đề xuất giảm bớt phạm vi (Scope reduction) bằng phương pháp Concierge hoặc Smoke test thay vì xây dựng sản phẩm hoàn chỉnh.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: coreyhaines31/marketingskills
  commit: b1aaa3619e747f4a836c61e03084c4a531de1262
  skill: ab-testing
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Khung thử nghiệm Lean, Phương pháp A/B test và smoke test
  changed:
    - Chuẩn hóa thuật ngữ COSA
    - Thêm cấu trúc 10 mục bắt buộc và định dạng markdown tiếng Việt
  added:
    - Khung giả thuyết chuẩn (If-Then-Because)
    - Hệ 3 tầng chỉ số (Primary, Secondary, Guardrail metrics)
    - Khung quyết định phân nhánh (Decision Log Branching)
    - Safe fallback khi tool ghi chưa khả dụng
  excluded:
    - Tự động phân bổ ngân sách chạy ads thử nghiệm
```
