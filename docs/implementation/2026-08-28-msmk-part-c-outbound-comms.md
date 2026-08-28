# PART C2 — Sub-plan: Outbound Communications & Outreach

**Ngày:** 2026-08-28  
**Phần của:** [msmk-part-c-business-writes](2026-08-28-msmk-part-c-business-writes.md) · §5  
**Nhánh đề xuất:** `msmk/part-c-outbound-comms`  
**Phụ thuộc:** PART C1 · Connector Grant Gateway  

---

## 1. Context

Truyền thông ra bên ngoài (email, tin nhắn, mạng xã hội) trực tiếp tác động đến thương hiệu và uy tín doanh nghiệp. Toàn bộ các hành động outbound communication đều có rủi ro `HIGH` và bắt buộc Human Approval gate cho từng lượt gửi/batch gửi kèm bản xem trước nội dung (content preview).

---

## 2. Capability Contracts

| Capability ID | Risk Class | Approval Policy | Idempotency | Connector |
| --- | --- | --- | --- | --- |
| `comms.email.send` | `HIGH` | `REQUIRE_APPROVAL` | `payload_deterministic` | Email provider grant (Resend / SendGrid) |
| `comms.sms.send` | `HIGH` | `REQUIRE_APPROVAL` | `payload_deterministic` | SMS provider grant (Twilio) |
| `comms.social.post` | `HIGH` | `REQUIRE_APPROVAL` | `payload_deterministic` | Social media grant (LinkedIn / X) |

---

## 3. Implementation Guidelines

- **Connector Grant:** Phải lấy delegation grant từ `ConnectorGrantHttpClient` trước khi gọi provider ngoài.
- **Approval Payload:** Bắt buộc chứa `recipient_count`, `subject`, `body_preview`, `sample_recipients`.
- **Post-action Verification:** Kiểm tra webhook / delivery receipt status từ provider sau khi gửi.
- **Rate Limit & Sandbox:** Provider sandbox bắt buộc trong môi trường test/CI; rate limiter chống spam.
