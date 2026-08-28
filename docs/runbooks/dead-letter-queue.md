# Runbook: Dead Letter Queue (DLQ)

> Part 2E.4. COSA có **hai** DLQ độc lập. Runbook này là điểm vào chung; chi
> tiết event-outbox nằm ở runtime runbook (không chép lại ở đây).

| DLQ | Nguồn | "dead" khi | Vận hành |
|---|---|---|---|
| **Scheduled tasks** | `control_plane.scheduled_tasks` (`services/cosa`, Postgres) | `attempt_count >= max_attempts` (mặc định 5) sau khi fail hoặc sweeper reclaim → `status='failed'`, `dead_letter_reason` set | §1 dưới đây (SQL) |
| **Event outbox** | `integration.event_outbox` (`services/cosa`) | vượt `max_attempts = 8` retry → `status='dead'` | [`docs/operations/event-driven-agent-runtime-runbook.md`](../operations/event-driven-agent-runtime-runbook.md) §2 "DLQ Triage" (`GET /events/outbox?status=dead`, `POST /events/outbox/{id}/retry`) |

Cả hai được feed bởi cron mỗi phút (`services/cosa/control-plane.cron.ts`:
`reclaim-stuck-scheduled-tasks` cho scheduler; outbox relay cron cho events).

---

## 1. Scheduled tasks DLQ

### 1.1 Xem DLQ

```sql
-- Task đã dead-letter, mới nhất trước
SELECT id, target_spec_id, attempt_count, max_attempts,
       dead_letter_reason, updated_at, input_payload
FROM control_plane.scheduled_tasks
WHERE status = 'failed'
ORDER BY updated_at DESC
LIMIT 50;

-- Đếm theo nguyên nhân (phát hiện lỗi hàng loạt — worker chết đồng loạt)
SELECT dead_letter_reason, count(*)
FROM control_plane.scheduled_tasks
WHERE status = 'failed'
GROUP BY dead_letter_reason
ORDER BY 2 DESC;
```

Dấu hiệu **worker chết hàng loạt**: nhiều row `dead_letter_reason =
'visibility timeout exceeded, max attempts reached'` trong khoảng thời gian
ngắn → kiểm tra `cosa-worker` container (crash loop? OOM? mất kết nối control
plane?). Xem `docker logs cosa_prod_worker`, `restart: unless-stopped` phải
đưa lại. (Metric `cosa_scheduler_reclaimed_total` + alert: Part 2B, chưa land.)

### 1.2 Replay 1 task sau khi fix nguyên nhân

```sql
-- Đưa task về hàng đợi. Reset attempt_count để không dead-letter lại ngay.
-- Chỉ chạy SAU khi đã xác định + sửa nguyên nhân gốc.
UPDATE control_plane.scheduled_tasks
SET status = 'scheduled',
    attempt_count = 0,
    claimed_by = NULL,
    claim_token = NULL,
    visibility_timeout_at = NULL,
    dead_letter_reason = NULL,
    run_at = now(),
    updated_at = now()
WHERE id = '<task_id>' AND status = 'failed';
```

Cron sweeper / worker poll kế tiếp sẽ nhặt task. Verify:

```sql
SELECT id, status, attempt_count, claimed_by FROM control_plane.scheduled_tasks WHERE id = '<task_id>';
```

Replay hàng loạt (cùng nguyên nhân, đã fix): thêm `AND dead_letter_reason =
'<reason>'` thay cho `AND id = ...`. **Không** replay mù toàn bộ — kiểm từng
nhóm nguyên nhân.

### 1.3 Purge (dọn task dead-letter cũ)

```sql
-- Chỉ purge task đã dead-letter > 30 ngày và đã xác nhận không cần replay.
DELETE FROM control_plane.scheduled_tasks
WHERE status = 'failed'
  AND updated_at < now() - interval '30 days';
```

Trước khi purge: export ra file để lưu vết nếu cần điều tra sau
(`\copy (SELECT ...) TO 'dlq-scheduled-YYYYMMDD.csv' CSV HEADER`).

### 1.4 Child tasks

Task con (`scheduled_task_child_edges`) khi parent dead-letter: kiểm
`listChildTasks` — nếu join chưa resolve, parent replay sẽ re-fan-out. Không
replay child riêng lẻ trừ khi hiểu rõ DAG (xem `child-scheduler.service.ts`).

---

## 2. Kiểm thử

- Scheduler DLQ path: `services/cosa/tests/control-plane-scheduler-crash-recovery.test.ts` (test 7: retry vượt `max_attempts` → dead-letter) + `services/cosa/tests/control-plane-cron.test.ts` (cron endpoint reclaim).
- Cả hai cần Postgres thật → chạy trong CI job `services` / `services-test-cosa`, không chạy local nếu chưa `docker compose up postgres`.

## 3. Liên quan
- `docs/operations/event-driven-agent-runtime-runbook.md` — DLQ event outbox.
- `docs/operations/disaster-recovery.md` — restore rehearsal.
- `docs/runbooks/prod-cutover.md` §5 — abort nếu "task bị kẹt zombie / dead-letter bất thường".
