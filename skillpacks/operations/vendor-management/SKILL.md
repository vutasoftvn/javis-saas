---
name: operations-vendor-management
description: Quản trị nhà cung cấp và đối tác bên thứ ba, chấm điểm Scorecard đa tiêu chí, theo dõi vi phạm SLA có bồi hoàn dịch vụ và phân loại rủi ro chuỗi cung ứng theo chuẩn NIST SP 800-161 và ISO 27036.
---

# Quản Trị Nhà Cung Cấp & Rủi Ro Bên Thứ Ba (Vendor Management & SLA Governance)

## 1. Mục Tiêu (Objective)
Thiết lập quy chuẩn kiểm soát và đánh giá toàn diện các nhà cung cấp dịch vụ, hạ tầng và phần mềm (SaaS) bên thứ ba cho doanh nghiệp. Giúp Founder và BizOps trả lời dứt khoát 2 câu hỏi: *"Nhà cung cấp này có đang thực hiện đúng cam kết dịch vụ không?"* và *"Mức độ thiệt hại và rủi ro nếu họ sụp đổ là gì?"*. Cung cấp công cụ tính điểm Scorecard định kỳ, theo dõi vi phạm SLA kèm số tiền bồi hoàn (Service Credit) và phân tầng rủi ro chuỗi cung ứng theo tiêu chuẩn NIST SP 800-161.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi tiến hành rà soát định kỳ hiệu quả hoạt động của các đối tác/công cụ theo chu kỳ 12-Week Year (12WY).
  - Khi xảy ra sự cố gián đoạn dịch vụ (Outage / Degradation) từ phía nhà cung cấp và cần tính toán số phút vi phạm SLA để yêu cầu bồi hoàn.
  - Khi chuẩn bị gia hạn hợp đồng hoặc đàm phán lại chi phí với nhà cung cấp.
  - Khi đánh giá an ninh chuỗi cung ứng cho các dịch vụ mới xử lý dữ liệu khách hàng.
- **Khi nào KHÔNG dùng**:
  - Khi cần phân loại danh mục tổng thể chi tiêu phần mềm toàn công ty (dùng `finance.procurement-optimizer`).
  - Khi tự ý đơn phương gửi yêu cầu đòi tiền phạt hoặc đơn phương chấm dứt hợp đồng mà không qua Founder / Finance Lead.

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Ngữ cảnh: `workspace_id`, `project_id`.
- Dữ liệu hợp đồng/SLA: Ngưỡng thời gian xử lý sự cố tối đa (MTTR), tỷ lệ uptime cam kết, chi phí hàng tháng/hàng năm.
- Nắm vững các hàm tính toán của `VendorGovernanceCalculator` (`agent.operations.analyzers.vendor_governance_calculator`).

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Thu Thập Hồ Sơ & Cam Kết SLA**: Xác định tên nhà cung cấp, gói dịch vụ, người chịu trách nhiệm đầu mối nội bộ, và điều khoản SLA đã ký kết.
2. **Chấm Điểm Đa Tiêu Chí (Scorecard Calculation)**:
   - Thu thập điểm số thực tế trên 4 trụ cột: Giao hàng / Tính sẵn sàng (`delivery`: trọng số 30%), Chất lượng dịch vụ (`quality`: 30%), An ninh & Tuân thủ (`security`: 25%), Hỗ trợ kỹ thuật (`support`: 15%).
   - Tính điểm trung bình có trọng số qua `VendorGovernanceCalculator.calculate_score` và xếp hạng từ A đến D.
3. **Theo Dõi Vi Phạm SLA & Tính Bồi Hoàn (SLA Breach Tracking)**:
   - Khi có sự cố, ghi nhận mức độ nghiêm trọng (P1, P2, P3), MTTR cam kết so với thời gian khôi phục thực tế.
   - Tính toán số phút trễ hạn và tỷ lệ phần trăm tiền bồi hoàn (Service Credit) khấu trừ vào hóa đơn tiếp theo.
4. **Phân Tầng Rủi Ro Chuỗi Cung Ứng (NIST SP 800-161 Risk Classification)**:
   - Đánh giá 3 yếu tố: Xử lý dữ liệu cá nhân/tài chính (PII), là thành phần phụ thuộc cốt lõi của production (SPOF), và quy mô chi tiêu.
   - Phân loại:
     - **Tier 1 (Critical)**: Bắt buộc phải có kịch bản chuyển mạch dự phòng khẩn cấp (**Break-glass plan**) và chu kỳ rà soát 4 tuần/lần.
     - **Tier 2 (High)**: Rà soát mỗi chu kỳ 12 tuần.
     - **Tier 3 (Medium/Low)**: Rà soát 24 tuần/lần.
5. **Kết Xuất Báo Cáo Thẩm Định Đối Tác**: Tạo bản ghi `vendor-review-dossier` để Founder/Ban lãnh đạo duyệt hành động.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Quy trình được thực thi và kiểm thử thông qua các module chuẩn của agent.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Mọi khiếu nại vi phạm SLA phải đi kèm log sự cố, mã ticket hoặc thông báo gián đoạn dịch vụ chính thức từ status page của nhà cung cấp.
- Mọi đề xuất thay đổi nhà cung cấp Tier 1 phải có tài liệu so sánh giải pháp thay thế.

## 7. Safe Fallback & Nghiêm Cấm Anti-Patterns
- **CẤM THIẾU KẾ HOẠCH DỰ PHÒNG CHO TIER-1 (No Break-Glass Anti-Pattern):** Bất kỳ dịch vụ nào được xếp hạng Tier-1 Critical mà không có phương án ứng phó khi họ sập hoàn toàn đều bị gắn cờ đỏ cảnh báo an ninh.
- **CẤM ĐƠN PHƯƠNG KÍCH HOẠT CHẾ TÀI:** Các tính toán bồi hoàn chỉ mang tính đề xuất cơ sở pháp lý cho đội ngũ tài chính và đàm phán con người.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Báo Cáo Đánh Giá Nhà Cung Cấp & Rủi Ro (Vendor Review Dossier)

## 1. Thông Tin Đối Tác & Phân Tầng Rủi Ro
- **Tên nhà cung cấp**: [Tên đối tác]
- **Phân loại rủi ro (NIST SP 800-161)**: [TIER_1_CRITICAL | TIER_2_HIGH | TIER_3_MEDIUM_LOW]
- **Yêu cầu Break-glass Plan**: [BẮT BUỘC / KHÔNG]
- **Chu kỳ rà soát**: [X tuần/lần]
- **Các yếu tố rủi ro**: [Liệt kê các yếu tố PII, SPOF, chi tiêu]

## 2. Bảng Điểm Hiệu Năng (Vendor Scorecard)
- **Điểm tổng hợp**: [XX.X / 100] — **Xếp loại: [Hạng A / B / C / D]**
  - Giao hàng & Sẵn sàng (30%): [XX điểm]
  - Chất lượng dịch vụ (30%): [XX điểm]
  - An ninh & Tuân thủ (25%): [XX điểm]
  - Hỗ trợ kỹ thuật (15%): [XX điểm]

## 3. Hồ Sơ Vi Phạm Cam Kết SLA (Nếu có)
- **Mã sự cố**: [INC-XXXX] — Mức độ: [P1/P2/P3]
- **MTTR cam kết**: [XX phút] | **Thời gian xử lý thực tế**: [YY phút]
- **Thời gian vi phạm**: [ZZ phút]
- **Khoản bồi hoàn đề xuất (Service Credit)**: [X% tương đương $YYY USD]
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Nhà cung cấp không công bố SLA chi tiết trong hợp đồng**: Áp dụng ngưỡng tiêu chuẩn ngành SaaS (Uptime 99.9%, MTTR P1 $\le 60$ phút) và gắn nhãn là SLA tham chiếu mặc định cần chính thức hóa trong đợt tái ký.
- **Tranh chấp dữ liệu sự cố**: Đối chiếu log bên trong hệ thống COSA với báo cáo sự cố độc lập từ bên thứ ba trước khi kết luận vi phạm.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: alirezarezvani/claude-skills
  commit: 19392f7a08264ed00486a251f5b2098321771f94
  skill: vendor-management
  upstream_version: 2.8.0
  license: MIT
adaptation:
  kept:
    - Khung phân tầng rủi ro chuỗi cung ứng NIST SP 800-161 và ISO 27036
    - Cơ chế chấm điểm Scorecard 4 trụ cột và tính toán bồi hoàn Service Credit
  changed:
    - Chuyển đổi sang quy chuẩn 10 mục COSA tiếng Việt
    - Liên kết chặt chẽ với nhịp tuần 12WY (chu kỳ rà soát 4w / 12w / 24w)
  added:
    - Tích hợp trực tiếp với VendorGovernanceCalculator trong packages/agent/operations/analyzers
    - Quy tắc cấm đơn phương kích hoạt chế tài tài chính
  excluded:
    - Bỏ các script shell đọc file CSV cục bộ
```
