# Frontend Endpoint Inventory & Backend Parity Map

**Ngày lập:** 2026-08-28  
**Trạng thái:** Canonical Inventory — Deliverable PHẦN 3a ([`2026-08-28-remediation-part3-task-contract-slice.md`](./2026-08-28-remediation-part3-task-contract-slice.md))  
**Phạm vi:** Toàn bộ API calls trong `frontend/lib/**/services/*.dart` kết hợp router mapping của `ApiClient::normalizeEndpoint` và `resolveUri`.

---

## 1. Nguyên tắc Định tuyến & Tiêu chuẩn Phân loại

### 1.1 Gateway Targets
- **Local Company Microservices (`:4000`)**: `identity`, `operations`, `commercial`, `finance-legal`.
- **COSA Central Control Plane (`:4001`)**: `/platform/*`.
- **AgentOS AI Plane (`:8001` - `cosa-api`)**: `/agent/*`.
- **Desktop Loopback Worker (`:8765`)**: `/local-worker/*`.

### 1.2 Parity Status Definition
- **`OK`**: Endpoint đã có route thực tế trên backend, schema DTO khớp, auth & workspace scoping hoạt động đúng chuẩn.
- **`DTO-MISMATCH`**: Endpoint có tồn tại nhưng cấu trúc request/response DTO giữa Flutter và Backend có sự sai lệch trường hoặc kiểu dữ liệu.
- **`MISSING`**: Flutter gọi endpoint nhưng Backend chưa có handler tương ứng (trả 404).
- **`LEGACY-ONLY`**: Đường dẫn cũ (ví dụ `/tasks`, `/sales/*`, `/finance/*`) chỉ hoạt động nhờ hàm `normalizeEndpoint()` của `ApiClient`.

---

## 2. Bảng Thống kê Endpoint Toàn diện

| Method | Flutter Endpoint Call | Path sau Normalize | Request DTO | Response DTO | Auth | X-Workspace-Id? | Owner Service | Parity Status | Ghi chú |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :--- | :---: | :--- |
| **POST** | `/identity/register` | `/identity/register` | `RegisterRequest` | `RegisterResponse` | ❌ | ❌ | `identity` | `OK` | Đăng ký tài khoản & workspace |
| **POST** | `/identity/login` | `/identity/login` | `LoginRequest` | `LoginResponse` | ❌ | ❌ | `identity` | `OK` | Đăng nhập JWT |
| **GET** | `/identity/me` | `/identity/me` | — | `UserIdentity` | ✅ | ❌ | `identity` | `OK` | Thông tin user hiện tại |
| **GET** | `/identity/workspaces` | `/identity/workspaces` | — | `List<Workspace>` | ✅ | ❌ | `identity` | `OK` | Danh sách workspace của user |
| **GET** | `/identity/workspaces/:id` | `/identity/workspaces/:id` | — | `Workspace` | ✅ | ❌ | `identity` | `OK` | Chi tiết workspace |
| **GET** | `/operations/tasks` | `/operations/tasks` | — | `{ tasks: Task[] }` | ✅ | ✅ | `operations` | `OK` | Đã chuẩn hóa qua Header |
| **POST** | `/operations/tasks` | `/operations/tasks` | `CreateTaskParams` | `Task` | ✅ | ✅ | `operations` | `OK` | Tạo task mới |
| **GET** | `/operations/tasks/:id` | `/operations/tasks/:id` | — | `Task` | ✅ | ✅ | `operations` | `OK` | Lấy chi tiết task theo tenant |
| **POST** | `/operations/tasks/:id/status` | `/operations/tasks/:id/status` | `{ status: string }` | `Task` | ✅ | ✅ | `operations` | `OK` | Cập nhật trạng thái task |
| **POST** | `/operations/tasks/:id/projects` | `/operations/tasks/:id/projects` | `{ projectIds: [] }`| `{ projectIds: [] }` | ✅ | ✅ | `operations` | `OK` | Link task vào projects |
| **GET** | `/commercial/customers` | `/commercial/customers` | — | `Customer` | ✅ | ✅ | `commercial` | `OK` | Danh sách/tạo khách hàng |
| **POST** | `/commercial/customers` | `/commercial/customers` | `CreateCustomerParams` | `Customer` | ✅ | ✅ | `commercial` | `OK` | Tạo khách hàng |
| **GET** | `/commercial/customers/:id` | `/commercial/customers/:id` | — | `Customer` | ✅ | ✅ | `commercial` | `OK` | Chi tiết khách hàng (tenant query scope) |
| **POST** | `/commercial/contacts` | `/commercial/contacts` | `CreateContactParams` | `Contact` | ✅ | ✅ | `commercial` | `OK` | Tạo liên hệ |
| **GET** | `/commercial/contacts/:id` | `/commercial/contacts/:id` | — | `Contact` | ✅ | ✅ | `commercial` | `OK` | Chi tiết liên hệ |
| **POST** | `/commercial/accounts` | `/commercial/accounts` | `CreateAccountParams` | `Account` | ✅ | ✅ | `commercial` | `OK` | Tạo account B2B |
| **GET** | `/commercial/accounts/:id` | `/commercial/accounts/:id` | — | `Account` | ✅ | ✅ | `commercial` | `OK` | Chi tiết account B2B |
| **POST** | `/commercial/leads` | `/commercial/leads` | `CreateLeadParams` | `SalesLead` | ✅ | ✅ | `commercial` | `OK` | Tạo sales lead |
| **GET** | `/commercial/leads` | `/commercial/leads` | — | `{ leads: [] }` | ✅ | ✅ | `commercial` | `OK` | Danh sách sales leads |
| **GET** | `/commercial/leads/:id` | `/commercial/leads/:id` | — | `SalesLead` | ✅ | ✅ | `commercial` | `OK` | Chi tiết lead |
| **POST** | `/commercial/leads/:id/stage` | `/commercial/leads/:id/stage` | `{ stage: string }` | `SalesLead` | ✅ | ✅ | `commercial` | `OK` | Cập nhật stage lead |
| **POST** | `/commercial/opportunities` | `/commercial/opportunities` | `CreateOppParams` | `Opportunity` | ✅ | ✅ | `commercial` | `OK` | Tạo cơ hội bán hàng |
| **GET** | `/commercial/opportunities/:id` | `/commercial/opportunities/:id` | — | `Opportunity` | ✅ | ✅ | `commercial` | `OK` | Chi tiết opportunity |
| **POST** | `/commercial/opportunities/:id/stage` | `/commercial/opportunities/:id/stage` | `{ stage: string }` | `Opportunity` | ✅ | ✅ | `commercial` | `OK` | Cập nhật stage opportunity |
| **POST** | `/finance-legal/transactions` | `/finance-legal/transactions` | `RecordTxnParams` | `FinancialTransaction` | ✅ | ✅ | `finance-legal` | `OK` | Ghi nhận giao dịch |
| **GET** | `/finance-legal/transactions` | `/finance-legal/transactions` | — | `{ transactions: [] }` | ✅ | ✅ | `finance-legal` | `OK` | Danh sách giao dịch tài chính |
| **GET** | `/finance-legal/transactions/:id` | `/finance-legal/transactions/:id` | — | `FinancialTransaction` | ✅ | ✅ | `finance-legal` | `OK` | Chi tiết giao dịch |
| **POST** | `/finance-legal/transactions/:id/approve` | `/finance-legal/transactions/:id/approve` | — | `FinancialTransaction` | ✅ | ✅ | `finance-legal` | `OK` | Duyệt giao dịch vượt ngưỡng (founder) |
| **POST** | `/finance-legal/obligations` | `/finance-legal/obligations` | `CreateObligationParams` | `LegalObligation` | ✅ | ✅ | `finance-legal` | `OK` | Tạo nghĩa vụ pháp lý |
| **GET** | `/finance-legal/obligations/:id` | `/finance-legal/obligations/:id` | — | `LegalObligation` | ✅ | ✅ | `finance-legal` | `OK` | Chi tiết nghĩa vụ pháp lý |
| **POST** | `/finance-legal/obligations/:id/fulfill` | `/finance-legal/obligations/:id/fulfill` | — | `LegalObligation` | ✅ | ✅ | `finance-legal` | `OK` | Đánh dấu hoàn thành nghĩa vụ |
| **GET** | `/operations/workspaces/:id/cycles` | `/operations/workspaces/:id/cycles` | — | `List<Cycle>` | ✅ | ✅ | `operations` | `OK` | 12 Week Year Cycles |
| **POST** | `/operations/plans` | `/operations/plans` | `CreatePlanParams` | `Plan` | ✅ | ✅ | `operations` | `OK` | 12 Week Year Plans |
| **GET** | `/platform/companies` | `/platform/companies` | — | `List<Company>` | ✅ | ❌ | `cosa control-plane` | `OK` | Central companies |
| **GET** | `/platform/licenses` | `/platform/licenses` | — | `List<License>` | ✅ | ❌ | `cosa control-plane` | `OK` | Central licenses |
| **POST** | `/agent/workflows/runs` | `/agent/workflows/runs` | `WorkflowRunInput` | `WorkflowRun` | ✅ | ✅ | `cosa-api` (:8001) | `OK` | Kích hoạt AI workflow run |
| **GET** | `/agent/workflows/runs/:id` | `/agent/workflows/runs/:id` | — | `WorkflowRunDetail` | ✅ | ✅ | `cosa-api` (:8001) | `OK` | Theo dõi AI workflow run |

---

## 3. Các Nhóm Chưa Có Parity (Ghi nhận, Ngoài phạm vi Phần 3)

Theo quy định §6 và Non-goals. **Cập nhật 2026-08-31 (Task 11 của
[`2026-08-31-agentos-auth-contract-frontend-parity.md`](../superpowers/plans/2026-08-31-agentos-auth-contract-frontend-parity.md)):**
đối chiếu với route inventory sinh tự động
([`docs/architecture/generated/route-inventory.md`](../architecture/generated/route-inventory.md),
mục "2. Frontend company-bound call sites — trạng thái resolve") xác nhận
các route dưới đây vẫn `✗ GHOST` (Flutter gọi nhưng backend không có route
đăng ký) tính đến SHA ghi trong
[`docs/operations/release-checklists/agentos-authorization-parity.md`](../operations/release-checklists/agentos-authorization-parity.md).
Task 9 của cùng plan đã đổi hành vi Flutter cho các route này từ "âm thầm
trả `[]`" sang "báo lỗi rõ ràng" (`StrategyListResult.failure`), nhưng đó là
sửa hành vi *client*, không phải tạo ra backend contract — các route này vẫn
chưa tồn tại ở backend. Đánh dấu tường minh `UNAVAILABLE` ở đây thay vì
`MISSING`/`DTO-MISMATCH` để tránh nhầm là "sắp có", và để chặn UI mới expose
các route này cho tới khi có spec được duyệt (xem "Explicit follow-up plans"
trong plan trên, mục 1–2).

1. **Nhóm Strategy & Lenses (`/strategy/*`, `/strategy/lenses/*`)**:
   - Status: `UNAVAILABLE` (đã xác nhận GHOST trong route inventory — không có
     handler backend nào đăng ký các path này ở `services/company`).
   - Routes cụ thể: `/strategy/canvases` (GET/POST/DELETE), `/strategy/revisions`
     (GET/POST), `/strategy/lenses/summary`, `/strategy/lenses/pestel`,
     `/strategy/lenses/swot`, `/strategy/lenses/tows`, `/strategy/lenses/bsc`,
     `/strategy/initiatives` (GET/DELETE), `/strategy/founder-profile`,
     `/strategy/portfolios`, `/strategy/projects`, `/strategy/workspace-templates`,
     cùng nhóm `/execution/*` và `/okrs/*` gọi từ `strategy_service.dart` (xem
     route inventory §2 để có danh sách đầy đủ, có số dòng nguồn).
   - Owner: unassigned — needs product decision. Không có tài liệu nào trong repo
     (kể cả các brief/report của plan này) ghi nhận owner được chỉ định cho nhóm
     route này; không tự suy diễn tên.
   - Điều kiện expose lại UI: cần spec Company DTO + handler + Flutter model +
     migration được duyệt riêng trước khi bật lại các màn hình canvas/lens (xem
     "Explicit follow-up plans" mục 1 của plan 2026-08-31).
   - Lưu ý phân biệt: `/operations/strategy/*` (assumptions, decision-records,
     evidence, gate-evaluations, maturity-assessments, metric-contracts,
     metric-snapshots, pilots, pmf-scoreboards, stage-context, stage-policies,
     stage-transitions, projects) **đã có** handler thật và **không** thuộc
     nhóm UNAVAILABLE này — đây là namespace khác (`/operations/strategy/*` vs
     `/strategy/*`), đừng nhầm lẫn khi đọc route inventory.
2. **Nhóm Validation Engine (`/projects`, `/projects/:id/validation/*`)**:
   - Status: `UNAVAILABLE` (xác nhận GHOST — `GET /projects` và `POST /projects`
     từ `validation_service.dart` không có route backend tương ứng).
   - `validation_service.dart` gọi 15+ sub-endpoint liên quan session, claims,
     risk-matrix, hypotheses, interviews — chưa di dời sang Company Service handler.
   - Owner: unassigned — needs product decision. Chưa có tài liệu nào trong repo
     gán owner cho Validation Engine.
   - Điều kiện expose lại UI: cần plan riêng định nghĩa persistence, authorization,
     lifecycle và DTO trước khi mở lại cho 15+ caller hiện tại (xem "Explicit
     follow-up plans" mục 2 của plan 2026-08-31).
3. **Nhóm OKRs / Objectives (`/operations/objectives/*`)**:
   - Status: `DTO-MISMATCH` (không đổi — `/operations/objectives` **có** route
     backend thật theo route inventory, khác với nhóm `/okrs/*` ở trên vốn
     GHOST; đây thuần là lệch DTO, không phải thiếu route).
   - Backend schema hiện sử dụng model OKR theo chuẩn mới, Flutter DTO ở
     `outcomes_service.dart` cần một slice refactor riêng sau này.

---

## 4. Kế hoạch Dọn dẹp Route Legacy Normalizer

- Sau khi hoàn thành PHẦN 3b (Task slice), toàn bộ Flutter code gọi `/operations/tasks` trực tiếp.
- Giữ normalizer `/sales/*`, `/finance/*`, `/legal/*` tạm thời cho đến khi các module UI tương ứng được rà soát đồng bộ hoàn toàn.
