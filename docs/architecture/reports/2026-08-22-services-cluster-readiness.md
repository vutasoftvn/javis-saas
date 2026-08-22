# Services Cluster Readiness (Phase 1 parity, hợp nhất)

**Ngày lập:** 2026-08-22
**Nguồn:** hợp nhất từ 4 file plan gốc (giữ nguyên, không xoá) — `docs/superpowers/plans/2026-08-22-services-identity-cluster.md`, `2026-08-23-services-operations-cluster.md`, `2026-08-23-services-commercial-cluster.md`, `2026-08-23-services-finance-legal-cluster.md` — và git log.
**Xem thêm bối cảnh tổng thể:** `docs/architecture/adr/ADR-012-legacy-backend-agentos-services-integration-plan.md`.

> **Lưu ý quan trọng:** "Phase 1 parity: done" nghĩa là schema + logic của cluster khớp với model Python gốc và test riêng cluster đó pass — **không** nghĩa là cluster đã có consumer thật (frontend/backend/agent) gọi qua HTTP. Xem mục "Trạng thái tiêu thụ" cuối file.

## `services/identity` — Phase 1: done
Ported: Workspace, User, WorkspaceMember, Organization, WorkforceMember (tên cột/kiểu khớp bản gốc).
Gap cố ý hoãn: ID dùng Postgres `BIGSERIAL` thay vì snowflake generator của Python; `control_plane` (đồng bộ PlatformUser/Company lên cloud) chưa port — vẫn chỉ có ở Python; `Department`/`DepartmentMembership`/`AgentRelation`/`WorkforceRelation` chưa port (chưa có consumer).

## `services/operations` — Phase 1: done
Ported: Task (đủ field canonical), Initiative, OkrCycle/OkrObjective/KeyResult; đã xoá 2 prototype cũ `services/tasks`, `services/okr`.
Gap cố ý hoãn: `TaskDependency`/`TaskSchedule`/`OkrLink` chưa port; `TwelveWeekCycle`/`WeeklyPlan`/`WeeklyCommitment` chưa port (nên `Task.weeklyCommitmentId` không được validate); `Portfolio`/`StrategyCanvas`/`Project`/`Offering`/`Templates`/`Capability`/`Stage`/`Founder`/`NextAction` chưa port.
Gap kế thừa từ `identity`: `Brain` chưa từng được port, nên `Initiative.brainId`/`OkrCycle.brainId` là nullable thay vì `NOT NULL` như bản canonical — cần giải quyết khi có consumer thật cần module `knowledge`/Brain.

## `services/commercial` — Phase 1: done
Ported: Account, Contact, SalesLead, SalesOpportunity, Customer (từ `backend/business_core/sales/models.py`).
Gap cố ý hoãn: `SalesActivity` chưa port; toàn bộ domain Marketing (17 bảng, `backend/business_core/marketing/models.py`) chưa port — cluster hiện tại chỉ là CRM/Sales, Marketing cần plan riêng (có thể cả cluster riêng do quy mô); Billing chưa bắt đầu (chưa có Python source để đối chiếu). `SalesLead.keyResultId`/`SalesOpportunity.cycleId` là tham chiếu chéo cluster vào `operations` chưa được validate (chưa có endpoint `getKeyResult`/`getTwelveWeekCycle`).

## `services/finance-legal` — Phase 1: done
Ported: AccountingProfile, AccountingPeriod, FinancialTransaction, FinanceException, FinanceManagementSnapshot (từ `backend/business_core/finance/models.py`); LegalChecklistItem, LegalObligation (từ `backend/business_core/legal/models.py`).
Gap cố ý hoãn: toàn bộ khung kế toán VN TT58/TT199 (9/14 bảng finance) chưa port, cùng config tĩnh `backend/regulations/vn/`; toàn bộ domain Validation (~17 bảng) chưa port — bị chặn về cấu trúc bởi `Project` (đang hoãn ở plan `operations`), không chỉ là hoãn do độ lớn.
**Ghi chú quan trọng:** với Marketing bị hoãn khỏi `commercial`, mô hình 4-cluster ban đầu trong `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md` trên thực tế đã giao một MVP surface gọn hơn dự kiến ban đầu — Marketing, Validation, và khung kế toán VN là việc tương lai thật, không phải scope bị bỏ rơi.

## Xác minh trực tiếp (2026-08-22, sau khi các bản ghi parity ở trên được đối chiếu với build/test thật)

Theo đúng kỷ luật "không tin tài liệu, phải build/test thật" rút ra từ ADR-012: đã chạy trực tiếp `encore test` (31 file, 112 test — toàn bộ 4 cluster) và `npx tsc --noEmit` từ `services/`. **Cả hai đều pass sạch, không lỗi.** Khác với `legacy/backend` (tài liệu nói "canonical production" nhưng build gãy thật) và `agentos`/`services` nói chung (tài liệu nói "done" nhưng chưa ai gọi qua HTTP), phần schema/logic nội bộ của 4 cluster `services/` là **xác nhận đúng thật** — vấn đề duy nhất của chúng vẫn là "chưa có consumer", không phải "code sai/gãy".

## Trạng thái tiêu thụ (consumption) — điểm mấu chốt trước khi nối Frontend

Theo đúng ghi chú trong `services/operations` plan: **không có consumer nào (`backend/`, `frontend/`, `services/realtime_agent/`) gọi `services/tasks` hay `services/okr` qua HTTP tại thời điểm parity được ghi nhận.** Tình trạng này áp dụng chung cho cả 4 cluster — Phase 1 là parity-tested độc lập, chưa phải integration-tested end-to-end với bất kỳ caller thật nào. Xem ADR-012 để biết điều kiện cần trước khi coi `services/` (`:4000`) là nguồn duy nhất cho `frontend/`.
