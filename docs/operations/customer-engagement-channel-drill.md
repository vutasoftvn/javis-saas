# Customer Engagement P2 — Channel Provider Sandbox Drill

Tài liệu kịch bản diễn tập tích hợp (Integration Drill) và kiểm tra Rollout Gate cho kênh giao tiếp khách hàng thực tế (Zalo OA).

---

## 1. Mục tiêu diễn tập

Xác thực tính toàn vẹn 2 chiều của kênh Zalo OA trước khi mở traffic production:
1. **Inbound Verification**: Chữ ký HMAC `X-Zalo-Signature` được xác thực an toàn trên raw body trước khi parse JSON.
2. **Deduplication**: Replay cùng một `provider_delivery_id` / `msg_id` tạo **0** message trùng, **0** outbox event trùng.
3. **Outbound Relay**: Gửi tin qua `engagement_outbound_deliveries` với token phân giải an toàn từ `secret_ref`, không lộ token trong DB/log.
4. **Error Classification & DLQ**: Phân loại lỗi `permanent` (401/403/invalid token) vs `transient` (429/timeout), visibility cho WorkforceMember qua `GET /commercial/engagement/channels/:id/deliveries?status=failed`.
5. **CRM Identity Sync**: Link Contact/Account khi chắc chắn, tạo Review Item khi nhập nhằng, tạo Contact mới khi bật `auto_create_contact`, **tuyệt đối không bao giờ merge**.

---

## 2. Kịch bản chạy Sandbox Drill

### Bước 1: Chuẩn bị Credentials trên Sandbox
- `OA_ID`: ID tài khoản Zalo Official Account thử nghiệm.
- `APP_SECRET`: App Secret dùng để tính HMAC signature.
- `ACCESS_TOKEN`: Access token có quyền gửi tin nhắn OA.

### Bước 2: Onboard Connector & Endpoint
```bash
# 1. Onboard Connector qua Control Plane
POST /cosa/connectors/install
{ "workspaceId": "<WS_ID>", "connectorKey": "zalo_oa_sandbox" }

POST /cosa/connectors/authorize
{ "workspaceId": "<WS_ID>", "installationId": "<INST_ID>", "secretRef": "sec_zalo_sandbox_1", "grantedScopes": ["send", "read"] }

# 2. Tạo Channel Endpoint
POST /commercial/engagement/channels
{
  "workspaceId": "<WS_ID>",
  "inboxId": "<INBOX_ID>",
  "providerRef": "<OA_ID>",
  "connectorKey": "zalo_oa_sandbox",
  "inboundRoutingKey": "<OA_ID>",
  "verificationConfigRef": "cfg_zalo_sandbox_1",
  "autoCreateContact": true
}

# 3. Kích hoạt Endpoint (Fail-closed Gate)
POST /commercial/engagement/channels/<ENDPOINT_ID>/activate
```

### Bước 3: Diễn tập Inbound (Webhook Testing)
1. Gửi raw POST webhook kèm chữ ký HMAC hợp lệ vào `/commercial/engagement/channels/zalo/webhook`.
   - **Kỳ vọng:** Trả về `200 OK`, `outcome: "accepted"`, tạo mới Thread và Message trong `engagement_messages`, outbox event `engagement.message.received.v1`.
2. Gửi lại request với cùng `msg_id` (Provider Replay).
   - **Kỳ vọng:** Trả về `200 OK`, `outcome: "duplicate"`, số lượng Message không đổi.
3. Sửa 1 byte trong body và gửi lại.
   - **Kỳ vọng:** Trả về `401 Unauthorized`, `outcome: "rejected_signature"`, 0 message được tạo.

### Bước 4: Diễn tập Outbound & Error Handling
1. Nhân viên gửi tin nhắn outbound qua Desk API (`sendPublicMessage`).
   - `delivery-relay` tick xử lý: Lấy token từ `assertConnectorGrant` + `resolveChannelSecret` → Gửi sang Zalo Send API.
   - **Kỳ vọng:** Tin nhắn chuyển trạng thái `sent`, `external_message_id` lưu trên delivery record.
2. Thử nghiệm với Access Token sai / hết hạn (401).
   - **Kỳ vọng:** Delivery chuyển `failed` ngay lập tức, `deadLetterReason` ghi rõ lỗi, hiển thị trên danh sách DLQ của Desk.

---

## 3. Rollout Gate Checklist
- [x] Chữ ký HMAC timing-safe verify pass trên mọi request inbound.
- [x] Idempotency dedupe ở cả layer raw inbound event và layer message.
- [x] Outbound token không xuất hiện trong database và log.
- [x] Mọi kịch bản CRM identity sync không làm merge bất kỳ Contact/Account nào.
