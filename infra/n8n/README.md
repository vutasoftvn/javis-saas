# Customer-Owned n8n Deployment & Local Testing Guide

Tài liệu hướng dẫn triển khai n8n trên Docker Local để phục vụ phát triển/kiểm thử (dev/test) và triển khai trên VPS/Infrastructure riêng của khách hàng cho COSA Automation.

---

## 1. Kiến trúc kết nối Local (COSA <-> n8n)

```
+--------------------------+                 +---------------------------+
|    COSA Backend (Host)   |                 |    n8n Docker Container   |
|   (http://localhost:8000)|                 |  (http://localhost:5678)  |
+--------------------------+                 +---------------------------+
             |                                             |
             | ---- POST /webhook/cosa/<key> ------------> | (Trigger)
             |      (HMAC-SHA256 Signed Payload)           |
             |                                             | (Execute Workflow)
             | <--- POST /api/v1/automations/callback ---- | (host.docker.internal:8000)
             |      (Execution result)                     |
```

---

## 2. Khởi chạy n8n Local với Docker Compose

### Cách 1: Chạy trực tiếp từ thư mục `infra/n8n/`

```bash
# Khởi động container n8n
docker compose -f infra/n8n/docker-compose.yml up -d

# Xem logs của n8n
docker compose -f infra/n8n/docker-compose.yml logs -f n8n

# Dừng container
docker compose -f infra/n8n/docker-compose.yml down
```

### File cấu hình `infra/n8n/docker-compose.yml`:

```yaml
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    container_name: javis_n8n
    restart: unless-stopped
    ports:
      - "127.0.0.1:5678:5678"
    environment:
      - N8N_HOST=localhost
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=http://localhost:5678/
      - GENERIC_TIMEZONE=Asia/Ho_Chi_Minh
      - NODE_ENV=production
      - N8N_DIAGNOSTICS_ENABLED=false
      - N8N_PERSONALIZATION_ENABLED=false
      - N8N_VERSION_NOTIFICATIONS_ENABLED=false
    volumes:
      - n8n_data:/home/node/.n8n
      - ./workflows:/data/workflows
    extra_hosts:
      - "host.docker.internal:host-gateway"

volumes:
  n8n_data:
```

---

## 3. Thiết lập ban đầu trên Giao diện n8n (Web UI)

1. Mở trình duyệt truy cập: `http://localhost:5678`
2. **Tạo tài khoản Owner** (Email & Password cho môi trường local dev).
3. **Import Workflow mẫu**:
   - Trong n8n UI, chọn menu **Workflows** -> **Add workflow** -> click vào menu `...` góc phải trên -> chọn **Import from File...**
   - Chọn file [`infra/n8n/workflows/cosa_sample_workflow.json`](file:///Volumes/SSD/javis-saas/infra/n8n/workflows/cosa_sample_workflow.json).
   - Bật chuyển trạng thái workflow sang **Active** (gạt công tắc Active ở góc phải trên).

---

## 4. Cấu hình biến môi trường trên COSA Backend (`.env`)

Để COSA backend kết nối tới n8n container local:

```bash
COSA_AUTOMATION_PROVIDER=n8n
N8N_BASE_URL=http://localhost:5678
N8N_WEBHOOK_SECRET=cosa-n8n-default-secret
```

---

## 5. Kiểm thử (Testing)

### 5.1. Chạy script kiểm tra nhanh
Dự án cung cấp sẵn script Python để test healthcheck và webhook trigger có chữ ký HMAC:

```bash
# Kiểm tra healthcheck & trigger active webhook:
python infra/n8n/test_local_n8n.py

# Hoặc nếu đang mở tab editor n8n ở chế độ 'Listen for test event':
python infra/n8n/test_local_n8n.py --test
```

### 5.2. Chạy bộ unit / integration tests của COSA Backend
```bash
pytest backend/app/tests/automations/test_automation_runtime.py -v
```

---

## 6. Danh mục Automation Mẫu (Catalog Keys)

- `system.telegram_notification`: Gửi cảnh báo hệ thống/leads qua Telegram bot của doanh nghiệp.
- `system.email_notification`: Gửi email thông báo tự động.
- `sales.followup_email`: Kích hoạt workflow gửi email chăm sóc sau khi Founder phê duyệt.
- `marketing.publish_social`: Đăng bài truyền thông lên kênh social theo lịch đã duyệt.
