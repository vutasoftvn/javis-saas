# Product Bet & Prioritization Framework (Chuẩn 12WY)

> **Tài liệu tham chiếu chuyên sâu dành cho:** CPO Advisor & Product Leadership  
> **Nguyên tắc cốt lõi:** Mỗi tính năng là một ván cược có cấu trúc, RICE theo tuần công, Tiêu chí khai tử sau 6 tuần.

---

## 1. Bản Chất Của Một Product Bet (Ván Cược Sản Phẩm)

Trong mô hình 12WY, không duy trì một backlog vô tận gồm hàng trăm ý tưởng rời rạc. Mọi nỗ lực phát triển sản phẩm đều phải được đóng gói thành một **Product Bet** rõ ràng với 4 thành tố:

1. **Giả thuyết giá trị (Value Hypothesis):** *"Nếu chúng ta xây dựng X cho tệp người dùng Y, họ sẽ giải quyết được vấn đề Z và giúp công ty tăng chỉ số Leading Metric W thêm K%."*
2. **Ngân sách thực thi (Effort in Weeks):** Giới hạn tối đa trong 2 - 4 sprints (4 - 8 tuần công).
3. **Mức độ đảo ngược được (Reversibility):** Quyết định loại 1 (không thể đảo ngược - One-way door) hay Loại 2 (dễ dàng đảo ngược hoặc tắt feature flag).
4. **Tiêu chuẩn thành công & Điều kiện dừng (Success & Kill Criteria):** Xác định trước mốc đo lường vào Tuần thứ 6 sau khi ra mắt.

---

## 2. Khung Chấm Điểm RICE Chuẩn Hóa Theo Tuần Công

$$\text{RICE Score} = \frac{\text{Reach (Người dùng tiếp cận/tuần)} \times \text{Impact} \times \text{Confidence}}{\text{Effort (Số tuần công kỹ sư)}}$$

### Thang Đo Chuẩn Hóa:
- **Impact (Tác động lên mục tiêu 12WY):**
  - $3.0$: Massive (Thay đổi cuộc chơi, tăng trực tiếp ARR hoặc giảm 50% churn).
  - $2.0$: High (Tác động lớn đến trải nghiệm cốt lõi của ICP).
  - $1.0$: Medium (Cải tiến chất lượng trải nghiệm đáng kể).
  - $0.5$: Low (Tối ưu hóa vi mô, tính năng phụ).
- **Confidence (Mức độ tự tin dựa trên bằng chứng):**
  - $1.0$ (Cao): Đã phỏng vấn $> 10$ khách hàng sẵn sàng trả tiền trước, có dữ liệu sử dụng thực tế.
  - $0.8$ (Trung bình): Có tín hiệu gián tiếp từ thị trường hoặc yêu cầu từ 3-5 khách hàng tiềm năng.
  - $0.5$ (Thấp): Phỏng đoán dựa trên cảm tính hoặc đối thủ có tính năng tương tự.
- **Effort (Số tuần công kỹ sư):** Bắt buộc $> 0$. Nếu một tính năng cần $> 8$ tuần công, phải chia nhỏ thành các slice nhỏ hơn có thể release độc lập.

---

## 3. Tiêu Chí Khai Tử Tính Năng (Kill Criteria Sau 6 Tuần)

Mỗi tính năng ra mắt đều được gắn cờ theo dõi chặt chẽ sau 6 tuần (Mid-cycle check):

| Tỷ Lệ Đón Nhận (Adoption Rate) | Đánh Giá Tình Trạng | Hành Động Bắt Buộc |
| :--- | :--- | :--- |
| $\ge 40\%$ | **Thắng Lợi Lớn (Strong)** | Tối ưu hóa trải nghiệm, tích hợp sâu vào luồng onboarding chính. |
| $20\% - 39\%$ | **Tạm Chấp Nhận (Moderate)** | Thu thập phản hồi chuyên sâu để tinh chỉnh UI/UX trong 2 tuần tiếp theo. |
| $< 15\%$ sau 6 tuần | **Nguy Cơ Thất Bại (At Risk)** | **Ứng viên khai tử (Kill Candidate):** Tắt feature flag hoặc gỡ bỏ code để tránh phình to nợ kỹ thuật. |

> **Nguyên Tắc Bất Di Bất Dịch:** Tự hào loại bỏ một tính năng không ai dùng là bằng chứng của năng lực quản trị sản phẩm xuất sắc, không phải là sự thất bại.
