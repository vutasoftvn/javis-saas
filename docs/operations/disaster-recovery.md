# Vận hành: Disaster Recovery

## Trạng thái: CHƯA có runbook thật, CHƯA drill

Không có disaster-recovery drill nào chạy trong phiên Wave 0-11 (không có Postgres/hạ tầng thật trong môi trường dev). Nội dung dưới đây là điểm cần runbook thật dựa trên invariant đã build, không phải quy trình đã kiểm chứng bằng drill.

## Invariant đã build hỗ trợ recovery (đã test bằng code thật, KHÔNG phải bằng drill hạ tầng)

- **Exact invocation identity** `(run_id, tool_call_id)` không bao giờ regenerate — nghĩa là sau khi restore DB từ backup, resume 1 run dở dang vẫn map đúng lại invocation cũ, không tạo tool call trùng/lệch.
- **Governance accumulator durable** (`GovernanceStateStore`, fix trong phiên này) — restart process không làm mất governance state đã tích luỹ, vì state load lại từ Postgres mỗi lần cần, không giữ trong RAM.
- **Idempotency claims atomic** (`INSERT ... ON CONFLICT DO NOTHING`) — nếu phải replay event sau khi restore từ backup có thể có gap thời gian, claim atomic ngăn double side-effect miễn là bảng `idempotency_claims` được restore cùng backup point với `runs`.
- **CAS approval decisions** (`decision_version`) — race giữa 2 approval request sau failover không làm mất-approve/double-approve.

## Rủi ro CHƯA giải quyết

- **Wave 7 control-plane split DB**: `agent_core` (Python/Postgres riêng) và `control_plane` (schema trong `services/cosa` Encore DB) là 2 nguồn dữ liệu riêng. Nếu chỉ 1 trong 2 được restore từ backup (point-in-time khác nhau), `runtime_leases`/`scheduled_tasks` (Encore) có thể tham chiếu `run_id` không còn tồn tại bên `agent_core`, hoặc ngược lại. **Chưa có cross-DB consistency check hay runbook xử lý trường hợp này.**
- Chưa xác nhận backup schedule/retention cho cả 2 Postgres instance (agent_core DB, services Encore DB).
- Chưa test full restore-and-resume end-to-end (cần Postgres thật).

## Việc cần làm trước khi coi hệ thống production-ready

1. Thiết lập backup đồng bộ thời điểm (hoặc ít nhất ghi rõ RPO lệch nhau tối đa bao lâu) giữa 2 Postgres instance.
2. Viết + chạy thử drill: kill process giữa 1 run có tool call đang chờ approval, restore từ backup, resume ở process khác — xác nhận không double-execute, không mất governance state (test unit đã pass trong process test, nhưng chưa qua drill hạ tầng thật).
3. Runbook xử lý cross-DB reference lệch (mục trên) khi 1 trong 2 DB restore muộn hơn DB kia.
