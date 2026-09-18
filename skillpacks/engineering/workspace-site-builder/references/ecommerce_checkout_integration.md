# E-Commerce Storefront & 1-Page Checkout Integration

Tài liệu đặc tả kiến trúc Cửa Hàng Trực Tuyến và Thanh Toán Đơn Trang (1-Page Checkout) dành cho **CTO Agent** khi triển khai trong Sandbox. Kiến trúc này kế thừa những ưu điểm của WooCommerce nhưng loại bỏ sự nặng nề của PHP/MySQL cũ kỹ, sử dụng Next.js, tích hợp VietQR tự động và Stripe.

---

## 1. Mô Hình Dữ Liệu Sản Phẩm & Dịch Vụ (`catalog.json`)

Hệ thống hỗ trợ 3 loại hình sản phẩm/dịch vụ linh hoạt:

```json
{
  "currency": "VND",
  "products": [
    {
      "id": "prod-ebook-ai-growth",
      "sku": "EB-AI-01",
      "name": "Ebook: Cẩm Nang Ứng Dụng AI Tự Động Hóa Vận Hành",
      "type": "digital",
      "price": 299000,
      "originalPrice": 599000,
      "shortDescription": "Tài liệu thực chiến 120 trang kèm template triển khai.",
      "thumbnail": "/images/products/ebook-ai.webp",
      "digitalDelivery": {
        "type": "download_link",
        "assetUrl": "https://storage.cosa.site/assets/ebook-ai.pdf"
      }
    },
    {
      "id": "prod-consulting-session",
      "sku": "SV-CONSULT-01",
      "name": "Phiên Tư Vấn Chiến Lược Chuyển Đổi Số 1-1 (60 Phút)",
      "type": "service",
      "price": 1500000,
      "originalPrice": 2000000,
      "shortDescription": "Tư vấn trực tiếp với chuyên gia công nghệ cao cấp.",
      "thumbnail": "/images/products/consulting.webp",
      "serviceDelivery": {
        "bookingUrl": "https://cal.cosa.site/booking"
      }
    },
    {
      "id": "prod-smart-device",
      "sku": "HW-IOT-01",
      "name": "Thiết Bị Cảm Biến IoT Thông Minh",
      "type": "physical",
      "price": 850000,
      "originalPrice": 1100000,
      "shortDescription": "Cảm biến kết nối không dây, bảo hành 12 tháng.",
      "thumbnail": "/images/products/iot-sensor.webp",
      "inventory": { "stockQuantity": 50, "allowBackorder": false }
    }
  ]
}
```

---

## 2. Trải Nghiệm Mua Sắm & Mini-Cart Drawer

- **Thêm vào giỏ nhanh (Instant Add-to-Cart):**
  - Không cần tải lại trang.
  - Ngăn kéo Mini-Cart trượt ra từ bên phải màn hình hiển thị danh sách sản phẩm, số lượng, tổng tiền tạm tính và nút `Tiến Hành Thanh Toán`.
  - Dữ liệu giỏ hàng được đồng bộ mượt mà qua `localStorage` phía trình duyệt người dùng.

---

## 3. Kiến Trúc Thanh Toán Đơn Trang (1-Page Checkout Flow)

Trang thanh toán gom toàn bộ quy trình vào một màn hình duy nhất nhằm tối đa hóa tỷ lệ chuyển đổi:

```
┌────────────────────────────────────────────────────────┐
│                   1-PAGE CHECKOUT                      │
├──────────────────────────┬─────────────────────────────┤
│ CỘT 1: THÔNG TIN KHÁCH   │ CỘT 2: TỔNG QUAN ĐƠN HÀNG   │
│ - Họ và tên              │ - Danh sách sản phẩm        │
│ - Email nhận hóa đơn     │ - Ô nhập mã giảm giá        │
│ - Số điện thoại          │ - Tạm tính: 1,500,000 đ     │
│ - Địa chỉ giao hàng      │ - Giảm giá: -200,000 đ      │
│   (nếu là hàng vật lý)   │ - TỔNG CỘNG: 1,300,000 đ    │
│                          ├─────────────────────────────┤
│ CHỌN PHƯƠNG THỨC:        │                             │
│ (•) Chuyển khoản VietQR  │ [ NÚT HOÀN TẤT ĐẶT HÀNG ]   │
│ ( ) Thẻ Visa/Mastercard  │                             │
└──────────────────────────┴─────────────────────────────┘
```

---

## 4. Tích Hợp Cổng Thanh Toán

### 4.1. Thanh Toán Chuyển Khoản Tự Động Qua VietQR (PayOS / SePay)
Phương thức phổ biến và tối ưu chi phí nhất tại thị trường Việt Nam (phí giao dịch 0% hoặc siêu thấp so với thẻ tín dụng quốc tế):

1. **Khởi tạo thanh toán:**
   - Khách bấm Đặt Hàng ➔ Backend Sandbox gọi API PayOS/SePay sinh mã QR thanh toán động.
   - Nội dung chuyển khoản chứa mã đơn hàng duy nhất (ví dụ: `DH10293`).
2. **Hiển thị & Polling:**
   - Màn hình hiển thị mã QR VietQR chuẩn NAPAS 24/7, kèm nút copy số tài khoản, số tiền chính xác từng đồng.
   - Client mở kết nối Polling (hoặc Server-Sent Events/WebSocket) mỗi 2 giây để kiểm tra trạng thái đơn hàng.
3. **Webhook Xác Nhận Tức Thời:**
   - Khi tiền vào tài khoản ngân hàng, hệ thống cổng thanh toán bắn Webhook tới `POST /api/checkout/webhook/vietqr`.
   - Webhook kiểm tra chữ ký checksum (HMAC SHA256) ➔ Đánh dấu đơn hàng `PAID` ➔ Giao diện người dùng lập tức chuyển sang màn hình Cảm Ơn trong 2–3 giây.

### 4.2. Thanh Toán Thẻ Quốc Tế (Stripe Checkout / Elements)
Dành cho khách hàng quốc tế hoặc người dùng chuộng quẹt thẻ tín dụng:
- Tích hợp Stripe PaymentIntent API.
- Hỗ trợ 3D Secure 2.0 (OTP ngân hàng) chống gian lận thẻ.
- Webhook `POST /api/checkout/webhook/stripe` lắng nghe sự kiện `payment_intent.succeeded`.

---

## 5. Máy Trạng Thái Đơn Hàng (Order State Machine)

```
[ PENDING_PAYMENT ]
       │
       ├──(Webhook xác nhận tiền về)──► [ PAID ] ──► [ FULFILLED ]
       │                                   │
       └──(Hết hạn sau 15 phút)           └──(Hoàn tiền)──► [ REFUNDED ]
               │
               ▼
         [ CANCELLED ]
```

---

## 6. Tiêu Chuẩn Bảo Mật Webhook (Webhook Hardening)

1. **Kiểm Tra Chữ Ký (Signature Verification):**
   - Mọi Webhook gửi đến bắt buộc phải được verify chữ ký qua Secret Key (ví dụ `PayOS Checksum Key` hoặc `Stripe Webhook Secret`).
   - Nếu chữ ký không khớp ➔ Trả về HTTP 400 và từ chối xử lý.
2. **Xử Lý Trùng Lặp (Idempotency Guard):**
   - Lưu trữ `transaction_id` hoặc `webhook_event_id` vào bảng ghi đã xử lý.
   - Nếu sự kiện bị gửi lại lần 2 (do retry) ➔ Kiểm tra nếu đơn hàng đã ở trạng thái `PAID` thì lập tức trả về HTTP 200 mà không kích hoạt xử lý đơn hàng lần nữa.
3. **Giao Hàng Tự Động (Post-Payment Automation):**
   - Đơn hàng `PAID` tự động gửi email xác nhận hóa đơn kèm liên kết tải file (nếu là sản phẩm số) hoặc link đặt lịch họp (nếu là dịch vụ tư vấn).
   - Gửi thông báo tức thời về kênh Telegram của chủ doanh nghiệp: `"Đơn hàng mới #DH10293 đã được thanh toán thành công 1,300,000 VND qua VietQR"`.
