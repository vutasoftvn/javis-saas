---
name: finance-saas-metrics-diagnostic
description: Chẩn đoán sức khỏe tài chính SaaS 4 chiều, tính toán Churn kép chuẩn xác, đánh giá LTV/CAC vs Payback, phân bổ chi phí COGS/OpEx và phân tích ROI đầu tư tính năng.
---

# Chẩn Đoán Sức Khỏe Doanh Nghiệp SaaS & Chỉ Số Kinh Doanh

## 1. Mục đích & Giới hạn Quyền hạn
Cung cấp khung chẩn đoán định lượng toàn diện về sức khỏe tài chính của doanh nghiệp SaaS:
- Kiểm chuẩn 32 chỉ số SaaS cốt lõi phân tầng theo các giai đoạn doanh thu (<$10M, $10M-$50M, $50M+ ARR).
- Tính toán chính xác **Tỷ lệ Rời Bỏ Lũy Kế (Compounded Churn)**, tránh bẫy nhân 12 tai hại.
- Cân bằng giữa tỷ lệ **LTV:CAC** và **Thời gian thu hồi vốn (CAC Payback Period)**.
- Đánh giá tính khả thi tài chính của các ván cược tính năng sản phẩm (Feature Investment ROI).

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ phân tích dữ liệu và đề xuất bảng chẩn đoán cảnh báo (L1_PROPOSE). Quyết định cắt giảm ngân sách, thay đổi biểu phí hoặc điều chỉnh kế hoạch tài chính thuộc thẩm quyền của Founder / CFO con người.

## 2. Triggers
- Kích hoạt khi chuẩn bị báo cáo định kỳ cho Ban điều hành hoặc HĐQT (Board Meeting Prep).
- Kích hoạt khi cân nhắc tăng ngân sách Marketing/Sales (scale acquisition) để kiểm tra xem sản phẩm có đang là "chiếc thùng rỉ" (leaky bucket) hay không.
- Kích hoạt khi Founder cần quyết định có nên đầu tư phát triển một tính năng lớn dựa trên bài toán hoàn vốn.

## 3. Anti-triggers & Cạm Bẫy Chỉ Số (Vanity & Blended Metric Traps)
- **Bẫy Doanh thu không biên lợi nhuận:** $1M ARR ở biên lợi nhuận 80% giá trị hơn rất nhiều $2M ARR ở biên lợi nhuận 20%.
- **Bẫy Churn nhân 12:** Tuyệt đối không dùng $3\% \times 12 = 36\%$. Công thức lãi kép chính xác là $1 - (1 - 0.03)^{12} \approx 30.62\%$. Ngược lại, $5\%$ tháng tương đương với $\approx 46\%$ năm.
- **Bẫy LTV:CAC không tính Payback:** Tỷ lệ LTV:CAC đạt 4:1 nhưng thời gian thu hồi vốn lên tới 36 tháng là một cái bẫy dòng tiền (cash trap). Tỷ lệ 3:1 với payback 8 tháng lành mạnh hơn nhiều cho sự tăng trưởng.
- **Bẫy Chỉ số Trung bình Gộp (Blended Averages):** Cấm dùng trung bình gộp để ra quyết định. Bắt buộc phân tách theo kênh (Channel), phân khúc (Segment), và đoàn hệ (Cohort).
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## 4. Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `saas_financial_inputs`: Các dữ kiện tài chính sẵn có (MRR, Churn, CAC, Gross Margin, Burn Rate, Runway).

## 5. Evidence Rules
- Dữ liệu tài chính phải đối chiếu với các nguồn ghi nhận thực tế (sổ cái, báo cáo ngân hàng, dữ liệu Stripe/cổng thanh toán).
- Các dự báo dòng tiền phải ghi rõ kịch bản cơ sở (Base), bi quan (Bear) và lạc quan (Bull).

## 6. Khung Chẩn Đoán Sức Khỏe 4 Chiều (Four-Dimension Diagnostic Framework)

### 6.1. Chiều 1: Tăng Trưởng & Giữ Chân (Growth & Retention)
- **ARR / MRR:** Tách bạch 4 cấu phần: `Mới + Mở rộng (Expansion) - Rời bỏ (Churn) - Thu hẹp (Contraction)`.
- **NRR (Net Revenue Retention):** Mục tiêu > 110-120%. NRR < 90% là tín hiệu báo động đỏ.
- **Quick Ratio:** $\frac{\text{New MRR} + \text{Expansion MRR}}{\text{Churned MRR} + \text{Contraction MRR}}$. Chuẩn lành mạnh: > 2.0 - 4.0. Dưới 2.0: Ngừng scale acquisition, tập trung vá thùng rỉ.

### 6.2. Chiều 2: Đơn Vị Kinh Tế (Unit Economics)
- **Gross Margin:** (Doanh thu - COGS) / Doanh thu. Chuẩn SaaS: 70 - 85%. Dưới 60%: Nguy hiểm.
- **LTV chuẩn xác:** $\frac{ARPU \times \text{Gross Margin \%}}{\text{Monthly Churn Rate}}$.
- **CAC Payback chuẩn:** $\frac{CAC}{Monthly ARPU \times \text{Gross Margin \%}}$. Mục tiêu: < 12 tháng. Trên 24 tháng: Quá rủi ro.

### 6.3. Chiều 3: Hiệu Quả Sử Dụng Vốn (Capital Efficiency)
- **Net Burn & Runway:** Runway < 6 tháng = Trạng thái khẩn cấp sống còn. Bắt buộc chuẩn bị gọi vốn hoặc cắt giảm burn từ mốc 9-12 tháng.
- **Rule of 40:** Tỷ lệ tăng trưởng doanh thu % + Biên lợi nhuận %. Chuẩn lành mạnh: > 40.
- **Magic Number:** $\frac{(Q_n - Q_{n-1}) \times 4}{S\&M Spend_{n-1}}$. Trên 0.75: Tăng tốc đầu tư; 0.5 - 0.75: Tối ưu hóa; Dưới 0.5: Rà soát lại bộ máy GTM.

### 6.4. Chiều 4: Đánh Giá Đầu Tư Tính Năng (Feature ROI Framework)
Phân loại tính năng thành 4 nhóm tác động tài chính:
1. *Thương mại hóa trực tiếp (Direct monetization):* Gói mới, add-on trả phí. Yêu cầu ROI năm đầu > 3x.
2. *Cải thiện giữ chân (Retention improvement):* Tác động LTV kỳ vọng > 5x chi phí phát triển.
3. *Tối ưu chuyển đổi (Conversion lift):* Nâng tỷ lệ trial-to-paid.
4. *Bảo vệ hào chiến lược (Strategic moat):* Tuân thủ pháp lý, nền tảng cốt lõi (Cần kiểm soát trần chi phí).

Tích hợp trực tiếp các analyzers:
- `calculate_compounded_churn()`
- `diagnose_saas_health_scorecard()`
- `analyze_feature_investment_roi()`

## 7. Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## 8. Output Format
- **saas-health-scorecard**: Bản báo cáo chẩn đoán sức khỏe SaaS 4 chiều, danh sách Red Flags phân loại theo mức độ (Critical, High, Medium), bảng tính Churn kép và khuyến nghị ưu tiên hành động.

## 9. Fallback & Handoff
- Khi thiếu dữ liệu tài chính chi tiết, thực hiện chẩn đoán sơ bộ dựa trên 3 chỉ số tối thiểu: Monthly Burn, Cash Balance (Runway) và Gross Margin ước tính, sau đó handoff cho CFO/Finance Specialist bổ sung.

## 10. Eval Notes
- Suite: `evals/finance/saas-metrics-diagnostic.yaml`
