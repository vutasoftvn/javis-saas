# PART C1 — Sub-plan: Marketing Business Writes & Experiments

**Ngày:** 2026-08-28  
**Phần của:** [msmk-part-c-business-writes](2026-08-28-msmk-part-c-business-writes.md) · §5  
**Nhánh:** `msmk/part-c-marketing-write`  
**Phụ thuộc:** PART CTX (Canonical Marketing Context API) · PART B1  

---

## 1. Context

Sau khi hoàn tất read-only runtime (Part B1), các kỹ năng sáng tạo nội dung và chiến lược như `marketing.copywriting`, `marketing.campaign-review`, và `strategy.experiment-design` cần năng lực ghi dữ liệu thật vào Company Commercial service:
- Cập nhật định vị / thông điệp marketing (`commercial.marketing_context.write`).
- Lưu trữ tài liệu chiến dịch / bản thảo đã duyệt (`commercial.campaign_asset.write`).
- Khởi tạo giả định và thử nghiệm thị trường (`commercial.experiment.write`).

Mọi thay đổi đối với marketing context cốt lõi (single source of truth) đều là hành động có rủi ro `MEDIUM` và bắt buộc Human Approval gate (người sáng lập/admin duyệt) cùng cơ chế kiểm soát đồng thời lạc quan (`expectedRevision`).

---

## 2. Capability Contracts

| Capability ID | Risk Class | Approval Policy | Idempotency | Input Schema | Output Schema |
| --- | --- | --- | --- | --- | --- |
| `commercial.marketing_context.write` | `MEDIUM` | `REQUIRE_APPROVAL` | `payload_deterministic` | `workspace_id`, `expected_revision`, `patch_data`, `idempotency_key` | `id`, `revision`, `status`, `updated_at` |
| `commercial.campaign_asset.write` | `LOW` | `NEVER` | `payload_deterministic` | `workspace_id`, `asset_name`, `content`, `asset_type` | `asset_id`, `object_ref`, `created_at` |
| `commercial.experiment.write` | `MEDIUM` | `REQUIRE_APPROVAL` | `payload_deterministic` | `workspace_id`, `hypothesis`, `metric`, `target_value` | `experiment_id`, `status`, `created_at` |

---

## 3. Handler & Implementation

- **Handler File:** `apps/cosa/capabilities/marketing_write.py`
- **Tích hợp:** `build_cosa_agent_plane()` trong `apps/cosa/composition/agent_plane.py` gọi `CompanyServiceClient` qua endpoint `/commercial/marketing-context` (PATCH) và `/commercial/campaign-assets` / `/commercial/experiments` với header `X-Workspace-Id`.
- **Policy:** Đăng ký trong `CosaPolicyEngine` với `ApprovalPolicy.REQUIRE_APPROVAL` cho `commercial.marketing_context.write` và `commercial.experiment.write`.
- **Approval Binding:** Bind `run_id + tool_call_id + checkpoint_ref`.

---

## 4. Test & Verification Plan

1. **Integration Test (`tests/apps/cosa/test_agent_plane_marketing_write.py`):**
   - Plane expose đủ 3 capability spec.
   - Thử nghiệm ghi có conflict `expected_revision` → trả lỗi conflict `409`.
   - Cross-workspace isolation: không thể ghi đè sang workspace khác.
2. **Approval Bind & Resume:**
   - Kiểm tra `DurableApprovalService` bind `run_id + tool_call_id + checkpoint_ref`.
3. **Boundary Invariants:**
   - `test_agent_plane_skillpack_boundary.py` xanh (10 capabilities explicit).
