# Dự án C — Org chart có hiệu lực và wakeup theo sự kiện (heartbeat)

Ngày: 2026-10-05 · Trạng thái: DRAFT chờ duyệt · Phụ thuộc: A (ngữ cảnh), B (kiểm tra trước khi agent tự chủ tạo tác động)

Tương ứng Paperclip: org chart với đường báo cáo, heartbeat thức dậy theo hàng đợi có coalescing; và ảnh Dots: Dot điều phối giao nhánh song song.

> Số dòng lấy từ khảo sát ngày 2026-10-05, cần xác minh lại trước khi sửa.

## 1. Bối cảnh và vấn đề

- `reports_to_assignment_id` (`packages/agent/workforce/models.py:38`, migration `003_add_workforce_member_reference.sql:24`) **chỉ để hiển thị** (`GET /org-chart`, `workforce_routes.py:509-542`). Không FK, không kiểm vòng, không index; cha không active thì con âm thầm thành gốc.
- `governance.py` có `manager_member_id` nhưng không ai dùng. `delegation.py` là ủy quyền founder→principal, **không phải** đường báo cáo.
- Workforce `functional_key` chưa nối thực thi: `schedules/{id}/run-now` trả 501 (`workforce_routes.py:847`). Thực thi thật đi qua `ownerAgentProfile → _SPEC_BY_PROFILE` (`wga_run.py:601`).
- Hàng đợi bền đã đủ tốt: `scheduled_tasks` với `coalescing_key`, `claim_token`, `FOR UPDATE SKIP LOCKED`, backoff, dead-letter, `reclaimStuckTasks` (`control-plane-scheduler.service.ts`). Khóa `evt:` idempotent tuyệt đối; khóa thường chỉ coalesce vào hàng `scheduled`, nếu hàng đang `processing` thì tạo hàng mới ⇒ đúng ngữ nghĩa wakeup (không mất lần đánh thức, tối đa một hàng chờ).
- Cron chỉ dispatch theo giờ (`control-plane.cron.ts`). Không có thức dậy theo sự kiện. Mẫu gần nhất: `execute_workspace_task_sweep_task` (`wga_run.py:769`, khóa `wga:sweep:{ws}:{project|*}`, công tắc `WGA_SWEEP_ENABLED`, giới hạn độ sâu).
- `SAFE_ACTIVITY_KINDS` (`apps/cosa/project_activity/service.py:24`) không có kind giao việc, bình luận, từ chối.
- `BudgetGate` chưa thi hành (kể cả `max_daily_cost_usd`); `tokenBudgetPerRunSnapshot` chỉ chụp, chưa ép.
- `WaitResolver`, `ExpansionManager`, `RunLeaseManager` là in-memory, không sống qua restart. `DurableSupervisor` chưa có nơi gọi trong `apps/`.

## 2. Quyết định thiết kế (đề xuất)

1. **Không thêm broker.** Theo `ADR-LOCAL-EVENT-BACKBONE-001`: wakeup là consumer của outbox/inbox Postgres, payload chỉ chứa tham chiếu.
2. **Wakeup = task loại `agent_wakeup`** trên `scheduled_tasks`, khóa `wake:{ws}:{assignment_id}` (không dùng `evt:` vì phải bắn lặp được). Payload dùng danh sách `reasons[]` (coalescing gộp nông, scalar sẽ bị ghi đè).
3. **Org chart là đường leo thang, không phải đường quyền.** Tiêu đề và đường báo cáo **không bao giờ mở rộng capability** (nguyên tắc có sẵn trong `governance.py`). Ủy quyền xuống không vượt autonomy của người giao.
4. **An toàn trước tự chủ:** chỉ thức dậy khi agent ACTIVE, autonomy ≥ L2, còn ngân sách, chưa vượt hop cap và rate cap. Tác động ghi vẫn đi qua Capability Gateway và, sau Dự án B, qua Verifier.
5. **Founder luôn là gốc cuối:** chuỗi leo thang kết thúc ở operator/founder, giữ hành vi `escalated_to_operator` hiện có.

## 3. Các bước triển khai

### C1. Toàn vẹn org chart
- Migration Agent Core `021_workforce_reporting_integrity.sql` + `.down.sql` (sau `020` của Dự án B): index trên `reports_to_assignment_id`; kiểm cha cùng workspace.
- Kiểm vòng và self-reference ở tầng `create_assignment` (`repository.py:399-451` Postgres, `:1199` InMemory) vì CHECK thuần SQL không bắt được vòng; dùng CTE đệ quy có giới hạn độ sâu.
- Validate cha tồn tại và ACTIVE khi tạo; lộ lỗi rõ thay vì âm thầm thành gốc (sửa `workforce_routes.py:533` thành cảnh báo).
- Repository thêm `list_direct_reports` và `resolve_manager_chain` (Protocol `repository.py:44-178` + hai lớp).
- Test: `tests/agent/workforce/test_repository.py`, `test_models.py`.

### C2. Bộ phân giải leo thang (hàm thuần)
- Module mới `packages/agent/workforce/escalation.py`: `next_escalation_target(assignment, chain, reason)`, tách khỏi `governance.py`. Trả về người quản lý kế tiếp hoặc `operator` khi hết chuỗi hoặc đạt hop cap.
- Test thuộc tính: không vòng, dừng đúng hop cap, không nới capability.

### C3. Dịch vụ wakeup và nhánh worker
- `WakeupService`: kiểm theo thứ tự (a) ACTIVE (chưa có kiểm tra ngoài lúc tạo assignment, cần thêm), (b) autonomy ≥ L2 (`governance/contracts.py:97`), (c) ngân sách + trần/ngày theo assignment dựa trên `RunCostObservationRecord`/`run_usage` thay vì `BudgetGate` chưa nối, (d) hop cap và rate cap/debounce (`run_at`), rồi `scheduler.schedule(task_type="agent_wakeup", coalescing_key=..., payload=refs)`.
- `apps/cosa/worker/main.py::dispatch_one_task` (~L494-520): thêm nhánh `agent_wakeup` (`task_type` lạ hiện làm task fail ở ~L581). Dùng fencing theo task như sweep; chỉ lấy lease run nếu bắt đầu run.
- Resolve mục tiêu thực thi qua `ownerAgentProfile → _SPEC_BY_PROFILE` và allowlist `SUPPORTED_AGENT_PROFILES` (`event_run_contract.py`), **không** qua workforce `functional_key` (chưa nối).
- Đi qua cùng đường `prepare_run` để `assert_initiative_run_allowed` (`initiative_policy.py`) áp dụng, tránh mở cổng sau.
- Công tắc `AGENT_WAKEUP_ENABLED` (mặc định tắt) giống `WGA_SWEEP_ENABLED`.
- Test: `tests/apps/cosa/events/test_event_worker_contract.py`, `services/cosa/tests/control-plane-scheduler-crash-recovery.test.ts` (coalescing + visibility).

### C4. Nguồn sự kiện
- Thêm kind `assignment.created`, `comment.created`, `approval.rejected` vào `SAFE_ACTIVITY_KINDS`, chỉ khi có bản ghi canonical bền (yêu cầu ghi trong code comment). Phát qua `company_event_projector.py`/inbox.
- Dedup inbox theo `(workspace_id, event_id, consumer_name)`. Payload chỉ tham chiếu.
- Test: `tests/apps/cosa/project_activity/test_worker_wiring.py`, `test_runtime_projection.py`.

### C5. Leo thang khi thất bại / bị từ chối
- Khi `run.failed`, `approval.rejected` hoặc `RunRecoveryService` trả `escalated_to_operator` (`runs/recovery.py`): gọi C2 để đánh thức người quản lý với `reason` + `source_ref`, nếu hết chuỗi mới tới operator.
- Chống bão: hop cap, rate cap/assignment, và khóa chống lặp theo `(source_ref, target)`.

### C6. Fan-out quản lý → cấp dưới (làm sau, nếu cần)
- Dùng `DurableSupervisor` (hiện chưa có caller) để manager chia nhiệm vụ cho `list_direct_reports`, với join policy và ngân sách. Chỉ mẫu phân cấp; các thành phần in-memory (`WaitResolver`, `ExpansionManager`) cần backing bền trước khi dựa vào chúng.

## 4. Rủi ro

- Bão thức dậy và vòng leo thang ⇒ hop cap, rate cap, debounce, công tắc tắt.
- Coalescing gộp nông (khóa cuối thắng) ⇒ `reasons[]`/bộ đếm.
- Khóa `evt:` không bắn lại cùng event_id ⇒ dùng khóa `wake:`.
- `workforce` chưa nối thực thi ⇒ phạm vi C chỉ dựa trên `ownerAgentProfile`; nối `functional_key` là việc riêng, ngoài phạm vi.
- Agent tự chủ làm tác động ngoài mà chưa có Verifier ⇒ **không bật wakeup cho tác vụ ghi trước khi B xong.**
- Migration thứ tự Agent → COSA → Company; số `020` đã dành cho B.

## 5. Xác minh

```bash
make agent-test
make apps-cosa-test
make services-test-cosa            # cd services/cosa && encore test
make lint typecheck-py migration-check
make boundary-check
```

Kiểm tra: (1) tạo chuỗi A→B→C, vòng và tự tham chiếu bị từ chối; (2) giao việc phát wakeup, nhiều sự kiện liên tiếp coalesce thành một lần chạy với `reasons[]` đủ; (3) run thất bại leo lên đúng quản lý rồi tới operator và dừng ở hop cap; (4) tắt cờ ⇒ không có wakeup; (5) agent SUSPENDED hoặc autonomy < L2 ⇒ không thức dậy.

## 6. Quyết định cần chủ dự án chốt

1. Mức tự chủ tối thiểu để thức dậy: L2 (đề xuất) hay L3?
2. Trần chi phí/ngày cho mỗi assignment bao nhiêu, và hop cap bao nhiêu (đề xuất 3)?
3. Có nối workforce `functional_key` vào thực thi (bỏ 501 của `run-now`) trong dự án này không, hay để riêng?
