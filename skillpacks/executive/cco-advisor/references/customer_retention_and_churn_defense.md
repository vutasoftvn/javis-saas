# Customer Retention & Churn Defense Playbook (Chuẩn 12WY)

> **Tài liệu tham chiếu chuyên sâu dành cho:** CCO Advisor & Customer Success Teams  
> **Nguyên tắc cốt lõi:** Bảo vệ NRR $\ge 110\%$, Giải cứu tài khoản Red Health Score trong 48h, Triệt tiêu churn chủ quan.

---

## 1. Phân Biệt Hai Dạng Rời Bỏ (Voluntary vs Involuntary Churn)

Để phòng chống rời bỏ hiệu quả, trước hết phải phân loại chính xác bản chất:

1. **Rời Bỏ Do Kỹ Thuật / Thanh Toán (Involuntary Churn - Chiếm 20-40%):**
   - Nguyên nhân: Thẻ tín dụng hết hạn, hạn mức thẻ bị từ chối, lỗi cổng thanh toán Stripe/Bank.
   - Giải pháp tự động: Kích hoạt hệ thống gửi email nhắc nhở thông minh (Dunning sequence) ở các ngày thứ 1, 3, 5, 7 và cơ chế tự động thử lại thẻ (Smart Retry).
2. **Rời Bỏ Chủ Quan Do Thất Vọng (Voluntary Churn):**
   - Nguyên nhân: Không nhận được giá trị như kỳ vọng, sản phẩm có bug khó chịu, thay đổi nhân sự phía khách hàng, hoặc tìm được giải pháp thay thế.
   - Giải pháp: Bắt buộc phải phát hiện sớm qua **Chỉ số Sức khỏe Tài khoản (Health Score)** trước khi khách hàng bấm nút hủy dịch vụ.

---

## 2. Quy Trình Cứu Vãn Tài Khoản Vùng Đỏ (Red Account Rescue Protocol)

Khi một tài khoản rơi xuống mức **Health Score $< 50$ điểm**:

```
[BƯỚC 1: TRONG 24H]
CS Lead rà soát toàn bộ lịch sử sử dụng, vé hỗ trợ (tickets) và log lỗi gần nhất của khách hàng.
       ↓
[BƯỚC 2: TRONG 48H]
Đặt lịch họp khẩn cấp (Executive Sponsor Call) giữa CCO/Founder và Lãnh đạo phía khách hàng.
Không bán hàng; chỉ tập trung vào lắng nghe nỗi bức xúc của họ.
       ↓
[BƯỚC 3: TRONG 7 NGÀY]
Cùng khách hàng xác lập một "Kế Hoạch Khôi Phục Giá Trị 14 Ngày" (14-Day Value Recovery Plan) 
với cam kết kỹ thuật cụ thể từ CPO/CTO.
       ↓
[BƯỚC 4: THEO DÕI TUẦN]
Báo cáo tiến độ trực tiếp cho khách hàng mỗi thứ Sáu cho đến khi Health Score phục hồi về Vàng/Xanh.
```

---

## 3. Phân Tích Nguyên Nhân Gốc Rễ Rời Bỏ (5 Whys Churn RCA)

Mỗi khi có một khách hàng đóng tài khoản, CCO Advisor phải chủ trì buổi phân tích nguyên nhân gốc rễ (Root Cause Analysis):

- Không dừng lại ở lý do bề mặt: *"Họ nói sản phẩm quá đắt."*
- Phải đào sâu 5 tầng:
  1. *Tại sao họ thấy đắt?* $\rightarrow$ Vì họ không dùng các tính năng nâng cao.
  2. *Tại sao họ không dùng tính năng nâng cao?* $\rightarrow$ Vì đội ngũ của họ không biết cách cài đặt.
  3. *Tại sao họ không biết cách cài đặt?* $\rightarrow$ Vì tài liệu hướng dẫn quá sơ sài.
  4. *Tại sao tài liệu sơ sài?* $\rightarrow$ Vì kỹ sư không có thời gian viết tài liệu khi release tính năng.
  5. *Giải pháp bền vững:* $\rightarrow$ Bổ sung tiêu chí "Tài liệu hướng dẫn hoàn chỉnh" vào Definition of Done của Sprint kỹ thuật.
