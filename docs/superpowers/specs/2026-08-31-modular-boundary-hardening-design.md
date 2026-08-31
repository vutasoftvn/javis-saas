# Modular Boundary Hardening — Thiết kế

**Trạng thái:** Design đã duyệt, chờ implementation plan

**Ngày:** 2026-08-31

## Bối cảnh

Trước design này đã tồn tại một spec cùng chủ đề — [2026-08-31-maintainable-modular-truthful-mvp-design.md](2026-08-31-maintainable-modular-truthful-mvp-design.md) — và commit gần nhất trước phiên này (`7c92d905`) tự báo "complete modular MVP architecture". Khi audit lại bằng file-size scan và 3 agent nghiên cứu song song (Python agent platform, Encore services, Flutter frontend), các hotspot mà spec cũ nhắm tới vẫn còn nguyên: `apps/cosa/api/routes.py` vẫn 1397 dòng, `strategy_service.dart` vẫn 1878 dòng, thư mục `frontend/lib/features/` vẫn chỉ là scaffold rỗng (chỉ có `public.dart` barrel file, chưa có implementation thật). Vì vậy design này được viết lại từ đầu, dựa trên khảo sát code thật tại thời điểm 2026-08-31, không kế thừa giả định "đã xong" từ spec cũ.

## Mục tiêu

Giảm rủi ro regression khi sửa lỗi hoặc thêm tính năng, bằng cách thu nhỏ blast-radius: tách các file/class ôm nhiều trách nhiệm không liên quan theo đúng ranh giới nghiệp vụ, và xử lý các vi phạm quy tắc kiến trúc cứng đã phát hiện được.

## Phạm vi

Bao quát 3 vùng kiến trúc: `packages/agent` + `apps/cosa` (Python), `services/company` + `services/cosa` (Encore/TypeScript), `frontend/lib` (Flutter). Không bao gồm `desktop_worker`, `landing`, `evals`, `scripts` — các vùng này chưa được khảo sát trong đợt này.

**Không nằm trong phạm vi (non-goals):**
- Không tạo service deploy mới, không đổi topology 4 vùng kiến trúc hiện có.
- Không đổi API contract, business logic, hay migration đã áp dụng.
- Không làm lại toàn bộ migration `modules/` → `features/` ở frontend trong đợt này — đây là nỗ lực riêng, scope lớn hơn, cần spec/plan của chính nó. Design này chỉ tách nội bộ trong `modules/<feature>/` hiện có.

Mỗi giai đoạn phải tự đứng được, ship riêng: tách 1 file/class, giữ nguyên public interface và hành vi, test xanh, commit độc lập — không gộp nhiều giai đoạn vào 1 commit.

## Khảo sát hiện trạng (regression-risk ranked)

### packages/agent + apps/cosa (Python)

1. `apps/cosa/api/routes.py` (1397 dòng) — mega-router trộn 6+ domain: conversation CRUD, message/run creation, approval workflow, SSE/timeline, knowledge ingestion, connector management, scheduling.
2. `packages/agent/capabilities/gateway.py` — `_execute_internal()` (600+ dòng) làm 10 việc khác nhau: tenancy verification, input validation, idempotency claim, enablement check, policy eval, approval gate, governance accumulation, compliance audit, connector resolution. 26 file phụ thuộc trực tiếp — điểm blast-radius cao nhất tìm được.
3. `apps/cosa/composition/agent_plane.py` (820 dòng) — god-object giữ 23 dependency công khai (repository, gateway, policy_engine, scheduler, v.v.); 12 file truy cập trực tiếp `.gateway`, `.repository`... không qua interface hẹp.
4. 6 file repository (~3600 dòng tổng) lặp lại cùng 1 pattern CRUD/pagination/tenancy-SQL — sửa bug ở 1 nơi không lan sang nơi khác.
5. `routes.py` và `workforce_routes.py` có endpoint approval/run-query gần như trùng nhau — dễ lệch schema khi 1 bên được cập nhật mà bên kia thì không.
6. `apps/cosa/worker/handlers.py` (677 dòng) — `execute_run_task()` trộn dispatch branching, logging, metrics, error recovery trong cùng 1 hàm.

Xác nhận: `packages/agent` không import gì từ `services/company` hay `services/cosa` — ranh giới này đang được giữ đúng, không cần sửa.

### services/company + services/cosa (TypeScript/Encore)

1. **Vi phạm rule cứng — handler query DB trực tiếp:** `commercial/handlers/customer-engagement/channel-admin.handler.ts`, `commercial/handlers/customer-engagement/automation.handler.ts`, `cosa/handlers/workspace-schedule.handler.ts`.
2. **Vi phạm rule cứng — raw `Error` thay vì `APIError`:** `company/identity/services/platform.client.ts`, `company/identity/services/token.service.ts`.
3. `marketing-context.service.ts` (787 dòng) — trộn 4 workflow không liên quan: product positioning, customer research/ICP, customer language capture, evidence management.
4. Db layer import chéo schema giữa domain (finance-legal ↔ legal, commercial ↔ customer-engagement) không có ranh giới "private vs shared" tường minh.
5. Auth/workspace-membership extraction bị copy-paste ~50+ lần trên các handler thay vì dùng middleware chung.

### Flutter frontend

1. `strategy_service.dart` (1878 dòng) — 6 domain không liên quan (Canvas, OKR, 12-Week, Project, Portfolio, Founder Profile) trong 1 class; lỗi ở decode helper dùng chung ảnh hưởng cả 6.
2. `dashboard_view.dart` (1054 dòng) — eager-import 20+ feature; 1 feature lỗi null-safety có thể sập cả app lúc khởi động.
3. `frontend/lib/features/` tồn tại nhưng chỉ là scaffold rỗng (barrel file trống) — toàn bộ code thật vẫn ở `modules/`. Migration này coi như **chưa bắt đầu**, không phải "đang dở dang".
4. `Map<String, dynamic>` không kiểm tra kiểu rải rác trong UI code (vd. `project_kickoff_view.dart`) — vỡ âm thầm khi backend đổi tên field.
5. 8 exception class tự viết tay + helper decode HTTP trùng lặp giữa các `*_service.dart`.
6. `hologram_hub` import trực tiếp `strategy_service`, `approvals_service`, `agent_chat_service` — đồ thị phụ thuộc chéo-feature vô hình, đổi tên hàm ở nơi khác không báo lỗi compile, chỉ vỡ lúc runtime.

## Thứ tự triển khai theo giai đoạn

### Giai đoạn 0 — Vá vi phạm quy tắc cứng (làm trước tiên, rủi ro thấp, giá trị cao)

- Chuyển query DB ra khỏi 3 handler đã liệt kê, vào `services/` tương ứng.
- Đổi `throw new Error()` trong `platform.client.ts`, `token.service.ts` sang `APIError` với code phù hợp.

### Giai đoạn 1 — Điểm blast-radius cao nhất

- Tách `gateway.py::_execute_internal()` thành các helper trách nhiệm rõ: `TenancyVerifier`, `IdempotencyCoordinator`, `EnablementValidator`, `ComplianceAuditor`, `ApprovalGateDecider`. Hàm gốc trở thành orchestrator gọi tuần tự các helper này.

### Giai đoạn 2 — God-object và mega-router

- `agent_plane.py`: nhóm 23 dependency thành `RunExecutionService`, `WorkflowOrchestration`, `ComplianceCoordination`; module khác chỉ nhận interface hẹp, không nhận cả object graph.
- `routes.py`: tách thành `conversation_routes.py`, `approval_routes.py`, `knowledge_routes.py`, `connector_routes.py`; gộp phần approval trùng với `workforce_routes.py` về 1 nơi canonical duy nhất (chỉ định `workforce_routes.py`).
- `marketing-context.service.ts`: tách `product-marketing.service.ts`, `customer-research.service.ts`, `marketing-snapshot.service.ts`.
- `strategy_service.dart`: tách theo domain (Canvas, OKR, 12-Week, Project, Portfolio, Founder Profile) — vẫn nằm trong `modules/strategy/services/`, không chuyển sang `features/`.

### Giai đoạn 3 — Duplication & shared helper

- Base class chung cho 6 repository Python (CRUD/pagination/tenancy-SQL).
- Middleware auth/workspace-membership dùng chung ở Encore.
- Gộp exception class + HTTP-decode helper trùng lặp ở Flutter vào `core/network/`.
- `dashboard_view.dart` chuyển sang lazy route builder thay vì eager-import toàn bộ feature.

## Kiểm chứng mỗi giai đoạn

- Trước khi tách: chạy suite test hiện có của file/module đó, ghi baseline.
- Nếu chưa có test bao phủ đủ hành vi hiện tại, viết characterization test trước khi tách — không tách "mù".
- Sau khi tách: public interface (chữ ký hàm, route path, response schema) giữ nguyên, không đổi hành vi.
- Chạy lại đúng bộ test + lint/type-check tương ứng (ruff/mypy cho Python; tsc/vitest cho Encore; `flutter analyze`/test cho Dart) — xanh mới commit.
- Mỗi giai đoạn commit riêng.
- Không tự báo "xong toàn bộ" ở cấp master — chỉ báo cáo đúng giai đoạn đã verify bằng lệnh thật, giai đoạn nào chưa làm, tránh lặp lại vấn đề đã ghi nhận với commit `7c92d905`.

## Tiêu chí hoàn thành

- Giai đoạn 0: không còn handler nào query DB trực tiếp trong 3 file đã liệt kê; không còn `throw new Error()` trần trong 2 service đã liệt kê.
- Giai đoạn 1: `gateway.py::_execute_internal` không còn là 1 khối logic đơn; mỗi concern có class/hàm riêng kèm test riêng.
- Giai đoạn 2: `routes.py`, `agent_plane.py`, `marketing-context.service.ts`, `strategy_service.dart` không còn ôm nhiều domain không liên quan; endpoint approval không còn trùng lặp giữa 2 router.
- Giai đoạn 3: có 1 base repository dùng chung, 1 auth middleware dùng chung, 1 exception/decode helper dùng chung ở Flutter; `dashboard_view.dart` không eager-import toàn bộ feature.
- Toàn bộ 4 giai đoạn: mỗi thay đổi có test tương ứng chạy xanh, không đổi API contract/behavior, không đổi migration đã áp dụng.
