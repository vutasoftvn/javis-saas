# PART C5 — Sub-plan: Finance & Reconciliation Controls

**Ngày:** 2026-08-28  
**Phần của:** [msmk-part-c-business-writes](2026-08-28-msmk-part-c-business-writes.md) · §5  
**Nhánh đề xuất:** `msmk/part-c-finance-cfo`  
**Phụ thuộc:** PART C1 · Finance-Legal Governance Policy  

---

## 1. Context

Kỹ năng `finance.cfo-review` và các quy trình đối soát tài chính đòi hỏi quyền hạn đặc thù với tính bảo mật cao. Tuyệt đối không đưa dữ liệu tài khoản ngân hàng thô vào context/prompt; mọi thao tác đối soát và khóa kỳ kế toán phải tuân thủ chính sách Finance-Legal.

---

## 2. Capability Contracts

| Capability ID | Risk Class | Approval Policy | Idempotency | Connector |
| --- | --- | --- | --- | --- |
| `finance.reconciliation.execute` | `HIGH` | `REQUIRE_APPROVAL` | `payload_deterministic` | Banking / Accounting grant |
| `finance.period.lock` | `HIGH` | `REQUIRE_APPROVAL` | `payload_deterministic` | Internal Finance-Legal service |

---

## 3. Implementation Guidelines

- **Financial Isolation:** Dữ liệu tài chính chỉ được xử lý qua các service trung gian đã lọc và ẩn danh dữ liệu nhạy cảm.
- **Audit & Retention:** Mọi thao tác đều phải ghi nhật ký kiểm toán không thể xóa (tamper-evident audit log) với thời hạn lưu trữ theo quy định pháp lý.
