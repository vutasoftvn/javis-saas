# Plan: Dashboard quản lý đầy đủ (Thiết lập & Agent → CRM → Tài chính → Business)

Ngày: 2026-09-26. Yêu cầu founder: "trong dashboard tôi cần quản lý full business,
agent, crm, tài chính, thiết lập... để cosa hoạt động được", triển khai theo thứ tự.

## Hiện trạng (đã kiểm tra bằng grep, không suy đoán)

- Backend đã tồn tại cho cả 4 vùng:
  - Agent: `apps/cosa/api/workforce_routes.py` (`/agent/workforce/*` — roster,
    org-chart, assignments, runs, approvals, schedules, health, cost...), đều trả
    envelope MVP.
  - CRM: `services/company/commercial` (`/commercial/accounts|contacts|leads|
    opportunities|invoices|customers`, project CRM).
  - Tài chính: `services/company/finance-legal` (`/finance-legal/transactions|
    accounting-periods|payment-requests`, `/finance/books|reports|budget-summary`).
  - Business: `/operations/projects/:projectId/operating-loop/*`, OKR, goals.
- Frontend: service tương ứng bị thay bằng `MvpRequestClient.unavailable(...)`
  ("removed from the Founder Trial R1 contract"); route `WorkspaceModule.agents`,
  `sales`, `marketing` là `_plannedRoute` (thẻ roadmap).
- Contract `shared/contracts/mvp-surface.json` thiếu các capability trên
  → `make frontend-api-contract-check` chặn gọi route không khai báo.

## Nguyên tắc

- Không tạo backend mới khi đã có; chỉ thêm khi màn hình cần mà backend thiếu.
- Mỗi route frontend gọi phải có capability `enabled` trong `mvp-surface.json`
  + sinh lại bằng `node scripts/gen-mvp-contracts.mjs`.
- Service trả `ApiResult` thật, không nuốt lỗi thành rỗng (rule 7 CLAUDE.md).
- Mutation rủi ro cao vẫn qua governance/approval hiện có (không bypass).
- Mỗi đợt: test service (MockClient) + `flutter analyze` + gate contract, rồi
  commit riêng.

## Đợt 1 — Thiết lập & Agent

1. Contract `workforce.*` cho `/agent/workforce/*` (roster, org-chart,
   composition, dashboard-summary, runs, run detail/events/artifacts,
   approvals list/decision, assignments list/create/retire, capabilities,
   health, cost-observations, schedules list/create/run-now, work products,
   exceptions, stage-roster).
2. `WorkforceMvpService` + `WorkforceService` gọi endpoint thật.
3. `AgentsService.getRunDetail` dùng `/agent/workforce/runs/:runId`; bỏ các
   lời gọi tới route không tồn tại (`/workforce/agents*`, `/workforce/runtimes`,
   `/agents/*`) — UI hiện trạng thái "chưa hỗ trợ" thay vì lỗi ngầm.
4. Bật route `/work/agents` với `AgentsView` + mục sidebar "Đội ngũ AI".
5. Thiết lập: provider model (đã xong ở commit trước), skills
   (`/agent/settings/skills` đã có backend).

## Đợt 2 — CRM

Contract + `SalesService`/`CrmService` cho accounts, contacts, leads (list/
create/stage), opportunities (create/stage), customers; bật route `/work/sales`
với `SalesView`/`CustomerView`. Bổ sung list endpoint Company nếu màn hình cần
mà backend chỉ có get-by-id.

## Đợt 3 — Tài chính

Contract + `FinanceService` cho transactions, accounting periods, payment
requests, books/reports, budget summary; nối các tab `FinanceView` hiện có.

## Đợt 4 — Business (Chu kỳ & Chiến lược)

Nối `StrategyMvpClient` (20 stub) vào operating-loop/OKR/goals đã có contract;
màn "Chưa có Objective nào" phải có CTA tạo objective/KR/task thật.

## Kiểm chứng mỗi đợt

`flutter analyze`, test Flutter của module, `make frontend-api-contract-check`,
`node scripts/gen-mvp-contracts.mjs --check`, `scripts/mvp_surface_check.py
--check`, `route_inventory.py --check`; test backend liên quan nếu sửa backend.
