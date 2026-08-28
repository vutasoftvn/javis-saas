# PART C4 — Sub-plan: Web Tracking & Structured Schema Deployment

**Ngày:** 2026-08-28  
**Phần của:** [msmk-part-c-business-writes](2026-08-28-msmk-part-c-business-writes.md) · §5  
**Nhánh đề xuất:** `msmk/part-c-web-deploy`  
**Phụ thuộc:** PART C1 · Connector Grant Gateway  

---

## 1. Context

Kỹ năng `marketing.seo-plan` và tối ưu hóa hạ tầng kỹ thuật có thể xuất bản mã theo dõi (analytics/tracking tag) và cấu trúc dữ liệu JSON-LD (Schema.org). Việc triển khai lên môi trường sản xuất có thể ảnh hưởng đến hiệu năng trang và trải nghiệm người dùng, do đó yêu cầu phê duyệt triển khai và cơ chế xác thực/rollback.

---

## 2. Capability Contracts

| Capability ID | Risk Class | Approval Policy | Idempotency | Connector |
| --- | --- | --- | --- | --- |
| `web.tracking.deploy` | `MEDIUM` | `REQUIRE_APPROVAL` | `payload_deterministic` | Web Hosting / Tag Manager grant |
| `web.schema.deploy` | `LOW` | `REQUIRE_APPROVAL` | `payload_deterministic` | Web CMS / Hosting grant |

---

## 3. Implementation Guidelines

- **Staging First:** Triển khai thử nghiệm trên môi trường staging/preview trước khi phê duyệt lên production.
- **Validation Gate:** Kiểm tra cú pháp JSON-LD / HTML trước khi deploy.
- **Rollback Path:** Giữ bản sao lưu phiên bản trước đó để khôi phục ngay lập tức nếu phát hiện lỗi.
