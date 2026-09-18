# Cash Flow & Runway Management Playbook (Chuẩn 12WY)

> **Tài liệu tham chiếu chuyên sâu dành cho:** CFO Advisor & Ban Giám Đốc  
> **Nguyên tắc cốt lõi:** Quy chuẩn theo số tuần ($W$), Stress-Test định kỳ, Kỷ luật ngân sách chu kỳ 12 tuần.

---

## 1. Công Thức Đo Lường Dòng Tiền & Runway Theo Tuần

Không sử dụng số tháng ước lượng mơ hồ. Toàn bộ tính toán sinh tồn của doanh nghiệp phải dựa trên số tuần sống sót chính xác:

$$\text{Weeks of Runway} = \frac{\text{Tổng Tiền Mặt Khả Dụng (Cash in Bank)}}{\text{Burn Rate Ròng Mỗi Tuần (Net Weekly Burn)}}$$

Trong đó:
$$\text{Net Weekly Burn} = (\text{COGS Tuần} + \text{OPEX Tuần}) - \text{Doanh Thu Thực Nhận Tuần}$$

### Ba Vùng Cảnh Báo Runway (Runway Alert Zones)
1. **Vùng Xanh ($\ge 24$ tuần ~ 2 Chu kỳ 12WY):**
   - Trạng thái: An toàn tài chính cao.
   - Hành động: Tập trung tối đa vào tăng trưởng, tuyển dụng theo kế hoạch, thử nghiệm các ván cược sản phẩm mới.
2. **Vùng Vàng ($16 - 24$ tuần):**
   - Trạng thái: Cần thận trọng cao độ.
   - Hành động: Đóng băng tuyển dụng ngoài kế hoạch, rà soát cắt giảm $15\%$ chi phí SaaS/hạ tầng tùy ý, bắt đầu kích hoạt quy trình chuẩn bị gọi vốn (Fundraising Sprint).
3. **Vùng Đỏ Khẩn Cấp ($< 16$ tuần):**
   - Trạng thái: Báo động sinh tồn.
   - Hành động: Kích hoạt kế hoạch cắt giảm chi phí khẩn cấp (Emergency Cost Cutting), đình chỉ mọi khoản chi không trực tiếp tạo ra doanh thu trong 2 tuần tiếp theo, Founder trực tiếp phê duyệt từng hóa đơn $> \$500$.

---

## 2. Kịch Bản Áp Lực Dòng Tiền (Cash Runway Stress Test)

Mỗi khi xem xét một quyết định đầu tư lớn hoặc định kỳ ở **Tuần 06 (Mid-cycle Checkpoint)**, CFO Advisor phải chạy mô phỏng áp lực với giả định doanh thu sụt giảm $30\%$:

$$\text{Stressed Revenue} = \text{Weekly Revenue} \times 0.70$$
$$\text{Stressed Net Burn} = (\text{COGS} + \text{OPEX}) - \text{Stressed Revenue}$$
$$\text{Stressed Runway Weeks} = \frac{\text{Cash in Bank}}{\text{Stressed Net Burn}}$$

> **Tiêu chuẩn An Toàn Bắt Buộc:** Nếu sau khi giả định giảm 30% doanh thu mà `Stressed Runway Weeks < 16 tuần`, kế hoạch chi tiêu mới phải bị BÁC BỎ hoặc thu hẹp quy mô ngay lập tức.

---

## 3. Khung Phân Bổ Vốn Chu Kỳ 12 Tuần (Capital Allocation Hierarchy)

Mỗi đồng vốn chi ra trong chu kỳ 12 tuần phải tuân theo thứ tự ưu tiên 4 tầng bất khả xâm phạm:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. DUY TRÌ VẬN HÀNH (Keep the lights on)                   │
│    Lương cốt lõi, server database, tuân thủ pháp lý/thuế     │
├─────────────────────────────────────────────────────────────┤
│ 2. BẢO VỆ NĂNG LỰC LÕI (Protect the core)                  │
│    Chất lượng sản phẩm chính, bảo mật, giữ chân khách hàng   │
├─────────────────────────────────────────────────────────────┤
│ 3. MỞ RỘNG ĐỘNG CƠ ĐÃ CHỨNG MINH (Grow the proven engine)  │
│    Tăng ngân sách cho kênh acquisition có CAC Payback < 24w │
├─────────────────────────────────────────────────────────────┤
│ 4. ĐẦU TƯ CƯỢC MỚI (Fund new exploratory bets)             │
│    Thử nghiệm tính năng mới (Tối đa 10-15% ngân sách chu kỳ)│
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Kỷ Luật Ngân Sách Tuần 13 (Buffer & Closeout Protocol)

- **Tuần 12:** Khóa toàn bộ các khoản chi mới ngoài ngân sách đã cam kết.
- **Tuần 13:**
  - Đối chiếu chênh lệch ngân sách (Budget vs Actual Variance).
  - Thu hồi các khoản công nợ quá hạn $> 30$ ngày.
  - Chốt số dư tiền mặt đóng băng cho Snapshot Startup OS mới.
