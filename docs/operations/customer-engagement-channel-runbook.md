# Customer Engagement Channel Operations Runbook

Tài liệu hướng dẫn vận hành, xử lý sự cố và quản trị các kênh tích hợp ngoại vi (Zalo OA, SMS, Email, API) trong phân hệ Customer Engagement.

---

## 1. Quản lý Secret & Access Token

### 1.1 Xoay vòng Webhook Secret (Webhook Secret Rotation)
1. **Chuẩn bị secret mới:** Cập nhật secret mới trong Secret Manager hoặc env `CHANNEL_SECRET_<NEW_REF>`.
2. **Tạo Verification Config mới:** Lưu config mới với `secretRef` mới.
3. **Cập nhật Endpoint:** Cập nhật `verification_config_ref` trên `engagement_channel_endpoints`.
4. **Cập nhật Webhook Provider:** Cập nhật Secret trên cổng quản trị Zalo OA / Provider.
5. **Kiểm tra logs:** Xác nhận các inbound webhook tiếp tục trả về `200 OK` và `outcome: "accepted"`.

### 1.2 Xoay vòng Access Token (Outbound Token Rotation)
1. Cấp mới token trên trang Zalo Developer / OA Dashboard.
2. Lưu token vào Secret Vault / Key Management Service với `secretRef` mới.
3. Gọi API Control Plane để cập nhật authorization:
   ```bash
   POST /cosa/connectors/authorize
   {
     "workspaceId": "<WS_ID>",
     "installationId": "<INST_ID>",
     "secretRef": "<NEW_SECRET_REF>",
     "grantedScopes": ["send", "read"],
     "expiresAt": "..."
   }
   ```
4. Kiểm tra outbound delivery tiếp theo được chuyển sang trạng thái `sent`.

---

## 2. Xử lý sự cố Outbound Dead Letter Queue (DLQ)

Khi một tin nhắn gửi đi thất bại vĩnh viễn (`permanent error`) hoặc vượt quá `max_attempts`:
1. **Kiểm tra danh sách tin nhắn lỗi:**
   ```bash
   GET /commercial/engagement/channels/:id/deliveries?status=failed
   ```
2. **Phân loại nguyên nhân qua `deadLetterReason`:**
   - `invalid_token` / `401 Unauthorized`: Access token của OA đã hết hạn hoặc bị thu hồi. Thực hiện bước 1.2 xoay vòng token.
   - `rate_limit_exceeded` / `429 Too Many Requests`: Đạt giới hạn gửi tin của provider.
   - `connector_grant_unavailable`: Quyền gửi tin trên Control Plane bị thu hồi hoặc endpoint chưa active.
   - `user_blocked_oa` / `recipient_unavailable`: Khách hàng đã chặn hoặc không cho phép OA gửi tin.
3. **Retry tin nhắn sau khi khắc phục nguyên nhân gốc:**
   ```bash
   POST /commercial/engagement/deliveries/:id/retry
   ```
   Delivery sẽ được đưa về trạng thái `queued` và xử lý trong tick relay tiếp theo.

---

## 3. Tạm dừng Kênh khẩn cấp (Emergency Channel Pause)

Nếu phát hiện spam, rò rỉ secret hoặc tấn công flood webhook:
1. **Tạm dừng Endpoint:**
   ```bash
   POST /commercial/engagement/channels/:id/pause
   ```
   Sau khi tạm dừng:
   - Toàn bộ webhook gửi đến sẽ nhận phản hồi `200 OK` nhưng được ghi nhận là `outcome: "dropped_paused"`, **không tạo thêm Thread hay Message** trong hệ thống.
   - Các tin nhắn outbound từ phía hệ thống đến kênh này sẽ tạm dừng xử lý.
2. **Kích hoạt lại sau khi xử lý:**
   ```bash
   POST /commercial/engagement/channels/:id/activate
   ```
   Endpoint sẽ thực hiện kiểm tra Fail-Closed (chữ ký hợp lệ & connector grant sẵn sàng) trước khi chuyển lại `active`.

---

## 4. Đối soát trạng thái gửi tin (Housekeeping Reconcile)

- Worker housekeeping chạy định kỳ quét các bản ghi `sent` chưa nhận được `delivered_at` sau 10 phút.
- Đối với provider hỗ trợ kiểm tra trạng thái, hệ thống gọi `adapter.getDeliveryStatus(externalMessageId)` để chuyển thành `delivered` hoặc `failed`.
- Sau 24 giờ nếu provider vẫn trả về `unknown`, hệ thống tự động ghi nhận `assumed_delivered` (best effort) để hoàn tất vòng đời đối soát.
