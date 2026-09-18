# B2B SaaS Unit Economics & Efficiency Guide

> **Tài liệu tham chiếu chuyên sâu dành cho:** CFO Advisor & Revenue Leadership  
> **Nguyên tắc cốt lõi:** LTV/CAC $\ge 3.0$, CAC Payback $< 24$ tuần, Gross Margin $\ge 75\%$.

---

## 1. Công Thức Chuẩn Hóa Unit Economics Theo Tuần

### 1. Thời Gian Hoàn Vốn CAC (CAC Payback Weeks)
Đo lường thời gian cần thiết để một khách hàng mới chi trả toàn bộ chi phí bán hàng và tiếp thị đã bỏ ra để có được họ:

$$\text{CAC Payback Weeks} = \frac{\text{CAC}}{\text{ARPU Hàng Tuần} \times \text{Gross Margin \%}}$$

- **Benchmark Đẳng Cấp:**
  - **Dưới 12 tuần (1 Chu kỳ 12WY):** Hiệu quả xuất sắc, cỗ máy in tiền, nên đổ thêm vốn mở rộng.
  - **12 - 24 tuần (1 - 2 Chu kỳ 12WY):** Mức chuẩn của B2B SaaS tăng trưởng lành mạnh.
  - **Trên 24 tuần:** Kém hiệu quả, rủi ro cạn tiền trước khi thu hồi vốn; cần tái cấu trúc kênh acquisition.

### 2. Tỷ Lệ Giá Trị Vòng Đời Trên Chi Phí Thu Hút (LTV / CAC)
$$\text{LTV} = \frac{\text{ARPU Hàng Tuần} \times \text{Gross Margin \%}}{\text{Weekly Churn Rate}}$$
$$\text{LTV / CAC Ratio} = \frac{\text{LTV}}{\text{CAC}}$$

- **Ngưỡng Đánh Giá:**
  - $\text{Ratio} \ge 3.0$: Doanh nghiệp tăng trưởng hiệu quả, bền vững.
  - $2.0 \le \text{Ratio} < 3.0$: Vùng cảnh báo, chi phí marketing/sales đang ăn mòn lợi nhuận.
  - $\text{Ratio} < 2.0$: Mô hình kinh doanh đang phá hủy giá trị ("đốt tiền mua người dùng").

---

## 2. Biên Lợi Nhuận Gộp (Gross Margin) Cho Sản Phẩm SaaS

$$\text{Gross Margin \%} = \frac{\text{Doanh Thu Tuần} - \text{COGS Tuần}}{\text{Doanh Thu Tuần}} \times 100\%$$

Trong đó COGS cho phần mềm SaaS bao gồm:
1. Chi phí hạ tầng đám mây (AWS, GCP, Supabase, Cloudflare).
2. Chi phí API AI của bên thứ ba (OpenAI, Anthropic token usage).
3. Chi phí cổng thanh toán (Stripe, bank processing fees).
4. Lương của đội ngũ hỗ trợ kỹ thuật khách hàng trực tiếp (Tier 1 Support).

> **Ngưỡng Tối Thiểu Bắt Buộc:** Gross Margin phải đạt $\ge 75\%$. Nếu dưới $70\%$, CTO và CAIO phải tối ưu hóa ngay kiến trúc hạ tầng và chi phí token.

---

## 3. Bảng Đối Chuẩn Sức Khỏe Tài Chính SaaS (Benchmark Matrix)

| Chỉ Số | Xuất Sắc (Top 10%) | Khỏe Mạnh (Median) | Cần Can Thiệp |
| :--- | :--- | :--- | :--- |
| **CAC Payback** | $< 12$ tuần | $12 - 24$ tuần | $> 24$ tuần |
| **LTV / CAC** | $\ge 4.0$ | $3.0 - 4.0$ | $< 2.5$ |
| **Gross Margin** | $\ge 80\%$ | $75 - 80\%$ | $< 70\%$ |
| **Net Retention (NRR)**| $\ge 120\%$ | $105 - 115\%$ | $< 100\%$ |
| **Weekly Churn Rate** | $< 0.2\%$ | $0.2\% - 0.5\%$ | $> 1.0\%$ |
| **Rule of 40** | $\ge 50\%$ | $40\%$ | $< 20\%$ |
