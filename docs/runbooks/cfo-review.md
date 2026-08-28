# Runbook: Quy Trình Đánh Giá Tài Chính & Dự Phóng Dòng Tiền (CFO Review Runbook)

**Tài liệu tham chiếu:** `skillpacks/finance/cfo-review/SKILL.md`  
**Chương trình:** [Chương trình tích hợp marketingskills + makerskills vào COSA](../integrations/2026-08-28-marketingskills-makerskills-program.md)  
**Mục đích:** Hướng dẫn chi tiết vận hành quy trình CFO Review định kỳ, đối soát số dư tiền mặt, tính toán tốc độ đốt vốn (Burn Rate), lập kịch bản dự phóng thời gian tồn tại (Runway), phát hiện bất thường tài chính và thiết lập ranh giới an toàn dữ liệu.

---

## 1. Nguyên Tắc Bảo Mật Dữ Liệu Tối Thượng (Zero Raw Banking Data in Prompts)

> [!CAUTION]
> **Nghiêm cấm tuyệt đối đưa dữ liệu tài chính thô nhạy cảm vào prompt của LLM:**
> - KHÔNG nhập thông tin đăng nhập ngân hàng, mật khẩu, API keys, mã OTP.
> - KHÔNG nhập số tài khoản ngân hàng chi tiết, thông tin thẻ tín dụng đầy đủ (PAN/CVV).
> - KHÔNG đưa sao kê thô chứa định danh cá nhân (PII) của khách hàng hoặc nhân sự.
> - **Chỉ xử lý dữ liệu tổng hợp (Aggregated Totals):** Tổng số dư theo tài khoản, tổng doanh thu theo kênh, tổng chi phí theo nhóm danh mục đã được ẩn danh.

---

## 2. Nhịp Vận Hành Đánh Giá Định Kỳ (Review Cadence)

### 2.1. Đánh Giá Hàng Tuần (Weekly Cash Flash Review - 30 Phút)
- **Mục tiêu:** Nắm bắt biến động tiền mặt tức thời và xử lý các khoản chi/thu lớn trong tuần.
- **Các bước thực hiện:**
  1. Tổng hợp số dư tiền mặt khả dụng tại tất cả tài khoản ngân hàng và cổng thanh toán (Stripe, VNPay, v.v.).
  2. Rà soát các khoản tiền thực thu vào (Inflows) và thực chi ra (Outflows) trong 7 ngày qua.
  3. Kiểm tra các khoản thanh toán lớn sắp đến hạn trong tuần tới (> $5,000 hoặc > 50 triệu VNĐ).
  4. Tính toán nhanh Net Cash Change trong tuần.

### 2.2. Đánh Giá Hàng Tháng (Monthly Strategic CFO Review - 90 Phút)
- **Mục tiêu:** Chốt sổ tài chính tháng, tính toán Burn Rate chính xác, cập nhật mô hình Runway và đối chiếu ngân sách kế hoạch (Budget vs Actuals).
- **Các bước thực hiện:**
  1. Hoàn tất đối soát dòng tiền (Cash Reconciliation) giữa sao kê ngân hàng và sổ cái kế toán.
  2. Tính toán Gross Burn và Net Burn trung bình 3 tháng (3-month rolling average).
  3. Cập nhật 3 kịch bản Runway (Base, Worst, Best case).
  4. Rà soát danh mục chi phí tìm kiếm các khoản bất thường hoặc dịch vụ SaaS không còn sử dụng.
  5. Xuất bản báo cáo CFO Brief gửi Hội đồng Quản trị / Ban Lãnh đạo.

---

## 3. Quy Trình Đối Soát Tiền Mặt & Tính Toán Chỉ Số Cốt Lõi

### 3.1. Công Thức Đối Soát Tiền Mặt (Cash Reconciliation)
$$\text{Số Dư Tiền Cuối Kỳ} = \text{Số Dư Đầu Kỳ} + \sum \text{Dòng Tiền Vào} - \sum \text{Dòng Tiền Ra}$$
- Chênh lệch không giải thích được giữa số dư ngân hàng thực tế và sổ cái phải $\le 0.01\%$.

### 3.2. Tính Toán Tốc Độ Tiêu Hao Vốn (Burn Rate)
- **Gross Burn (Chi tiêu gộp hàng tháng):**
  $$\text{Gross Burn} = \text{Chi Phí Nhân Sự} + \text{Chi Phí Hạ Tầng/SaaS} + \text{Marketing \& Ads} + \text{Thuê Nhà/Văn Phòng} + \text{Phí Khác}$$
- **Net Burn (Tiêu hao vốn ròng hàng tháng):**
  $$\text{Net Burn} = \text{Gross Burn} - \text{Doanh Thu Tiền Mặt Thực Thu (Cash Inflow)}$$

### 3.3. Mô Hình Dự Phóng Thời Gian Tồn Tại (Runway Scenario Planning)
$$\text{Runway (Tháng)} = \frac{\text{Số Dư Tiền Mặt Khả Dụng}}{\text{Net Burn Hàng Tháng}}$$

| Kịch Bản (Scenario) | Giả Định Tăng Trưởng Doanh Thu | Giả Định Biến Động Chi Phí | Hành Động Kích Hoạt |
| --- | --- | --- | --- |
| **Base Case** | Tăng trưởng 10% - 15% / tháng | Chi phí tăng theo kế hoạch nhân sự | Vận hành bình thường theo OKR quý |
| **Worst Case (Zero Growth)** | Tăng trưởng 0% (Doanh thu đi ngang) | Chi phí đóng băng các vị trí chưa tuyển dụng | Cảnh báo; rà soát giảm 15% chi phí SaaS/Marketing |
| **Emergency Case** | Doanh thu sụt giảm 20% | Cắt giảm toàn bộ chi tiêu tùy chọn (Discretionary) | Runway $\le 6$ tháng: Kích hoạt kế hoạch sinh tồn khẩn cấp |

---

## 4. Danh Mục Kiểm Tra Bất Thường Tài Chính (Anomaly Checklist)

- [ ] **Chi phí SaaS / Cloud tăng vọt:** Chi phí AWS, GCP, OpenAI/Anthropic API tăng $> 25\%$ so với tháng trước mà không tương ứng với mức tăng trưởng lưu lượng người dùng.
- [ ] **Đăng ký trùng lặp hoặc tài khoản không hoạt động:** Nhiều phòng ban cùng mua các công cụ có tính năng trùng nhau (ví dụ: Zoom vs Google Meet, Figma seats không sử dụng).
- [ ] **Công nợ khách hàng quá hạn (A/R Aging):** Hóa đơn B2B chưa thanh toán quá hạn 45 ngày; cần chuyên viên CS/Finance can thiệp nhắc nợ trực tiếp.
- [ ] **Lỗi trừ tiền thẻ tín dụng (Involuntary Churn):** Tỷ lệ thanh toán thất bại của khách hàng tăng đột biến, cần kiểm tra cổng thanh toán.

---

## 5. Phác Thảo Capability Contract Finance-Legal (Cho Part C Triển Khai)

Trong giai đoạn mở rộng Part C (Business Writes), mọi tác vụ liên quan đến dữ liệu tài chính và giao dịch tiền tệ phải tuân thủ nghiêm ngặt hợp đồng năng lực sau:

```yaml
capability_contract:
  domain: finance_legal
  connector_grant_required: true  # Bắt buộc Workspace Admin cấp quyền kết nối
  approval_policy:
    risk_level: high
    require_human_approval: true # Mọi lệnh chi tiền hoặc sửa sổ cái phải qua cổng Approval
    approval_timeout_sec: 86400  # 24 giờ
  audit_logging:
    immutable_audit_trail: true
    capture_fields:
      - workspace_id
      - actor_id
      - transaction_amount
      - currency
      - justification_notes
      - approval_request_id
```

- Tuyệt đối không cho phép AI tự động ký duyệt lệnh chuyển tiền ra ngoài mà không có chữ ký số hoặc phê duyệt tường minh của người quản trị có thẩm quyền.
