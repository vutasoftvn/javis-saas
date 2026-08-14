# Customer-Owned n8n Deployment Guide

Tài liệu hướng dẫn triển khai n8n trên VPS/Infrastructure riêng của khách hàng để phục vụ Automation Provider của COSA.

---

## 1. Nguyên tắc bản quyền & Kiến trúc (License-Safe Boundary)

1. **n8n thuộc sở hữu của khách hàng**: Khách hàng trực tiếp quản trị instance n8n và các thông tin xác thực (Credentials) bên thứ ba (Telegram bot token, SMTP, CRM, v.v.).
2. **COSA không bundle source hay binary của n8n**: Quá trình cài đặt sử dụng Docker image chính thức (`docker.n8n.io/n8nio/n8n:latest`).
3. **Kết nối qua REST Webhook có xác thực HMAC**: Toàn bộ giao tiếp giữa COSA và n8n được bảo vệ bằng chữ ký HMAC-SHA256 và chống replay.

---

## 2. File Docker Compose Mẫu (`docker-compose.yml`)

Khách hàng khởi chạy n8n trên VPS riêng bằng cấu hình sau:

```yaml
version: '3.8'

services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=CHANGE_THIS_STRONG_PASSWORD
      - N8N_HOST=n8n.yourcompany.com
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://n8n.yourcompany.com/
      - GENERIC_TIMEZONE=Asia/Ho_Chi_Minh
    volumes:
      - n8n_data:/home/node/.n8n

volumes:
  n8n_data:
```

---

## 3. Cấu hình biến môi trường trên COSA Backend

Trên hệ thống COSA, cấu hình các biến môi trường để kết nối tới instance n8n của khách hàng:

```bash
COSA_AUTOMATION_PROVIDER=n8n
N8N_BASE_URL=https://n8n.yourcompany.com
N8N_API_KEY=n8n_api_key_from_customer_instance
N8N_WEBHOOK_SECRET=your_shared_hmac_secret
```

---

## 4. Danh mục Automation Mẫu (Catalog)

- `system.telegram_notification`: Gửi cảnh báo hệ thống/leads qua Telegram bot của doanh nghiệp.
- `sales.followup_email`: Kích hoạt workflow gửi email chăm sóc sau khi Founder phê duyệt.
- `marketing.publish_social`: Đăng bài truyền thông lên kênh social theo lịch đã duyệt.
