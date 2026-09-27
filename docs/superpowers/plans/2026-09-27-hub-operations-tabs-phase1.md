# Hub: card vận hành 4 tab (đợt 1) — Kế hoạch triển khai

Spec: `docs/superpowers/specs/2026-09-27-hub-operations-workspace-design.md` (mục 3, đợt 1).
Điều kiện bắt đầu: PR #14 (chat business actions) đã merge — tab Công cụ dùng grant của PR đó.

**Goal:** Một card ở hub với 4 tab Tasks / Lịch / Công cụ / Agent, lọc theo Project đang chọn,
quản lý những thứ đã có: đổi trạng thái task, tạm dừng/tiếp tục/lưu trữ lịch, xem và thu hồi quyền
của agent, tạm dừng/kích hoạt agent. Không có hành động agent-tự-tạo mới ở đợt này.

**Nguyên tắc:** tái dùng endpoint sẵn có; endpoint mới qua contract `shared/contracts/mvp-surface.json`
(`make frontend-api-contract-check`); handler Encore không truy cập DB; chuỗi vi/en qua `AppCopy`.

## Task 1 — Backend lịch: tạm dừng / tiếp tục / lưu trữ + lịch sử chạy

Files: `services/cosa/services/workspace-schedule.service.ts`,
`services/cosa/handlers/workspace-schedule.handler.ts`, `services/cosa/tests/…`,
`apps/cosa/api/schedule_routes.py`, `tests/apps/cosa/api/test_schedule_routes*.py`,
`shared/contracts/mvp-surface.json` (+ `make mvp-contracts-gen`).

- [ ] `POST /cosa/schedules/:scheduleId/state` body `{state: "enabled"|"paused"|"archived"}`:
      chỉ founder/owner của organization (cùng guard `/cosa/schedules`); `archived` là trạng thái
      cuối (không mở lại); `enabled` tính lại `next_run_at`. Không xoá bản ghi (expand-only).
- [ ] `GET /cosa/schedules/:scheduleId/executions?limit=5` — lần chạy gần nhất (state, runId,
      conversationId, error rút gọn).
- [ ] Dispatcher bỏ qua lịch `paused|archived` (kiểm test đã có; thêm nếu thiếu).
- [ ] Proxy apps/cosa: `POST /agent/schedules/{id}/state`, `GET /agent/schedules/{id}/executions`
      (tenant guard theo identity như các route lịch hiện có).
- [ ] Test: vitest services/cosa (guard, chuyển trạng thái hợp lệ/không hợp lệ, archived không mở
      lại, dispatcher bỏ qua); pytest proxy.

## Task 2 — Backend quyền agent theo Project

Files: `services/company/identity/services/agent-authorization.service.ts` (hoặc service mới
cạnh `operations/services/agent-profile-grants.service.ts`), handler `operations/handlers/…`,
test vitest, contract.

- [ ] `GET /operations/projects/:projectId/agent-capability-grants`: grant ACTIVE/REVOKED của AI
      member thuộc startup team trong Project, kèm `profileKey`, nhãn capability vi/en (không trả
      enum thô làm nội dung chính), `grantedAt`, người cấp. Guard: `requireWorkspaceAccess` +
      thành viên Project; chỉ đọc.
- [ ] Thu hồi dùng endpoint sẵn có `POST /identity/agent-capability-grants/:grantId/revoke`
      (founder-only) — kiểm lại guard + test.
- [ ] Nhãn capability: bảng `CAPABILITY_LABELS` (vi/en) cạnh `AGENT_PROFILE_GRANTED_CAPABILITIES`;
      test parity Python: mọi capability trong bảng grant có nhãn.

## Task 3 — Frontend: khung card + tab Tasks

Files: `frontend/lib/modules/hologram_hub/widgets/hub_operations_card.dart` (mới),
`…/controllers/hub_operations_controller.dart` (mới, tách khỏi controller 1400+ dòng),
`hologram_hub_view.dart` (đặt card ở `leftColumn()` dưới `ProjectOperatingWeekCard`),
`core/ui/app_copy.dart`, test widget.

- [ ] Card `DefaultTabController` 4 tab, nạp lười theo tab, làm mới khi đổi Project (epoch guard
      như các mixin hub hiện có).
- [ ] Tab Tasks: lọc Của tôi / Agent / Tất cả; dòng task: tiêu đề, trạng thái (nhãn), người phụ
      trách, nhãn "do agent tạo" (từ `source`/assignee AI — kiểm field thật trước khi code); đổi
      trạng thái bằng endpoint operating-loop sẵn có; "Xem tất cả" → màn `tasks`.
- [ ] Test widget: hiển thị, lọc, đổi trạng thái gọi service, không lộ ID.

## Task 4 — Frontend: tab Lịch

- [ ] Danh sách lịch của Project (API `/agent/schedules` sẵn có, lọc `projectId`): tên/lời nhắc
      rút gọn, giờ chạy theo múi giờ, lần chạy gần nhất + trạng thái, agent chạy.
- [ ] Hành động: Chạy ngay (sẵn có), Tạm dừng/Tiếp tục, Lưu trữ (xác nhận 1 bước).
- [ ] Test widget + service.

## Task 5 — Frontend: tab Công cụ

- [ ] Phần "Kết nối": connector của organization (`connectors_service.dart` / endpoint
      `/platform/organizations/:organizationId/connectors`), trạng thái, nút "Quản lý" mở Settings.
- [ ] Phần "Agent được phép làm gì trong dự án": danh sách grant (Task 2) nhóm theo agent, nút
      Thu hồi (xác nhận), sau thu hồi làm mới danh sách.
- [ ] Test widget.

## Task 6 — Frontend: tab Agent

- [ ] Agent startup team của Project (`GET /operations/projects/:projectId/startup-team` sẵn có):
      tên, trạng thái, phiên bản đang ghim; cảnh báo "Có phiên bản mới — kích hoạt lại để cập
      nhật" khi pin khác phiên bản built-in hiện hành (server trả kèm, không so ở client).
- [ ] Tạm dừng / Kích hoạt bằng endpoint sẵn có (optimistic concurrency `expectedVersion`).
- [ ] Test widget.

## Task 7 — Kiểm chứng và tài liệu

- [ ] `make frontend-api-contract-check`, `flutter analyze`, `flutter test test/modules/hologram_hub`,
      tsc company/cosa, boundary checks, pytest apps/cosa liên quan.
- [ ] Thử tay trên dev stack: đổi Project → 4 tab nạp đúng; tạm dừng lịch → dispatcher không chạy;
      thu hồi quyền → agent chat bị từ chối ticket ở lần gọi kế tiếp.
- [ ] Cập nhật nhật ký roadmap; không đổi ADR (đợt 2 mới cần ADR-FOUNDER-CHANNEL-001).
