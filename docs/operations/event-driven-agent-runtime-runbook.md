# Event-Driven Agent Operating Model — Runtime Runbook

**Status:** ACTIVE (P0 Local-First Baseline)  
**Reference Architecture:** [ADR-LOCAL-FIRST-001](../architecture/adr/ADR-LOCAL-FIRST-001-workspace-runtime-node-data-residency.md) | [ADR-LOCAL-EVENT-BACKBONE-001](../architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md)

---

## 1. Local Topology

Mô hình hướng sự kiện cục bộ (local-first) kết nối Company Services (Encore / TypeScript) và AgentOS (Python / FastAPI) hoàn toàn bên trong ranh giới của Workspace Runtime Node. Không có message broker tập trung (Kafka, RabbitMQ, SQS) và không có payload nghiệp vụ nào vượt ranh giới node ra ngoài mạng công cộng.

```mermaid
graph TD
  subgraph Workspace Runtime Node [Workspace Runtime Node (Local Machine / Private Node)]
    subgraph Company Services [Company Services (Encore / TS)]
      DomainTx["Domain Transaction (Postgres)"]
      OutboxTable["integration.event_outbox"]
      RelayWorker["Outbox Relay Worker (Cron 1m)"]
      DomainTx -->|Writes in-tx| OutboxTable
      OutboxTable -->|FOR UPDATE SKIP LOCKED| RelayWorker
    end

    subgraph AgentOS [AgentOS Execution Plane (FastAPI / Python)]
      IntakeRoute["POST /agent/internal/events (HMAC Local Sig)"]
      InboxTable["event_inbox (Idempotency)"]
      TriggerPolicy["Trigger Policy Engine"]
      ExecScheduler["Execution Scheduler"]
      IntakeRoute --> InboxTable
      InboxTable --> TriggerPolicy
      TriggerPolicy -->|Accepted (Ref-only)| ExecScheduler
    end

    RelayWorker -->|Local HTTP POST| IntakeRoute
  end
```

---

## 2. DLQ Triage

Khi một outbox event vượt quá số lần retry tối đa (`max_attempts = 8`), trạng thái của dòng sẽ chuyển sang `dead` (Dead Letter Queue).

### 2.1. Liệt kê các Dead-Letter Events
Operator gọi endpoint truy vấn tóm tắt (không bao gồm payload nhạy cảm):
```http
GET /events/outbox?workspaceId={workspaceId}&status=dead
Authorization: Bearer {operator_token}
```
Phản hồi mẫu:
```json
{
  "items": [
    {
      "eventId": "3c90f28e-52f1-4b11-9a74-d4dc30919864",
      "eventType": "operations.task.created.v1",
      "aggregateType": "task",
      "aggregateId": "task_123",
      "status": "dead",
      "attemptCount": 8,
      "lastError": "status=503 body={\"detail\":\"database unavailable\"}",
      "deadLetterReason": "Exceeded maximum attempts (8)",
      "occurredAt": "2026-08-28T10:15:00.000Z"
    }
  ]
}
```

### 2.2. Khắc phục & Requeue
1. Kiểm tra trường `deadLetterReason` và `lastError` để xác định lỗi gốc (ví dụ: AgentOS service down, cấu hình trigger policy không hợp lệ, hoặc database lock).
2. Sau khi đã sửa lỗi gốc, yêu cầu requeue sự kiện:
```http
POST /events/outbox/3c90f28e-52f1-4b11-9a74-d4dc30919864/retry
Authorization: Bearer {operator_token}
Content-Type: application/json

{
  "workspaceId": "ws_123"
}
```
3. Trạng thái outbox row sẽ chuyển về `pending`, `attempt_count` đặt lại về `0`, và sự kiện sẽ được outbox relay xử lý trong chu kỳ cron tiếp theo. Thao tác retry được ghi vết vào bảng `integration.event_audit`.

---

## 3. Incident: Relay Stuck

### Triệu chứng
- Các sự kiện mới ở trạng thái `pending` hoặc `claimed` tích tụ mà không chuyển sang `delivered`.
- Agent không nhận được trigger từ các thay đổi domain state.

### Các bước chẩn đoán
1. **Kiểm tra tiến trình Outbox Relay Cron:**
   - Đảm bảo cron job `outbox-relay` (`services/company/events/outbox-relay.cron.ts`) đang hoạt động (`/events/relay/tick`).
   - Kiểm tra log của service `events`.
2. **Kiểm tra kết nối tới AgentOS:**
   - Kiểm tra xem biến môi trường `COSA_AGENTOS_INTAKE_URL` (mặc định `http://127.0.0.1:8081`) có thể truy cập được từ Company Service hay không.
   - Xác nhận `COSA_LOCAL_SERVICE_SECRET` khớp giữa hai phía để chữ ký `X-COSA-Local-Signature` được xác thực hợp lệ (HTTP 401 nếu sai secret).
3. **Kiểm tra các dòng bị kẹt ở trạng thái `claimed`:**
   - Nếu relay worker bị crash đột ngột trong khi đang gửi event, các dòng có thể vẫn ở trạng thái `claimed`.
   - Cơ chế visibility timeout (`visibility_timeout_at < now()`, mặc định 60 giây) sẽ tự động giải phóng các dòng này cho worker tiếp theo claim lại.

---

## 4. Replay Window & Idempotency

- Tầng AgentOS được bảo vệ bởi bảng `event_inbox` với ràng buộc duy nhất:
  ```sql
  UNIQUE (workspace_id, event_id, consumer_name)
  ```
- Cơ chế gửi từ outbox relay là **At-Least-Once Delivery**.
- Khi outbox relay gửi lại một event (ví dụ do mạng chập chờn sau khi AgentOS đã xử lý xong nhưng ACK chưa kịp trả về), AgentOS sẽ phát hiện bản ghi đã tồn tại trong `event_inbox`, trả về HTTP 200 `{ "outcome": "duplicate" }`, và không kích hoạt run thứ hai.
- Relay nhận được `outcome: duplicate` sẽ đánh dấu outbox row là `delivered`, chấm dứt vòng lặp retry.

---

## 5. Disable a Runaway Trigger Rule

Trong trường hợp một trigger rule gây ra quá nhiều tác vụ hoặc hành vi lặp vô tận do cấu hình sai:

1. Xác định `rule_id` và `workspace_id`.
2. Vô hiệu hóa rule bằng cách cập nhật cấu hình rule (hoặc set `enabled = false`):
```http
POST /events/rules/{ruleId}/disable
Authorization: Bearer {operator_token}
Content-Type: application/json

{
  "workspaceId": "ws_123"
}
```
3. Khi rule đã bị vô hiệu hóa (`enabled = false`), AgentOS intake router sẽ trả về `ignored_rule_disabled` và không lên lịch bất kỳ execution run nào.

---

## 6. Redacted Workspace Export & Correlation Chain

### 6.1. Tra cứu chuỗi correlation
Để theo dõi vết từ business event ban đầu cho tới artifact cuối cùng:
```http
GET /agent/events/correlation/{correlationId}?workspaceId={workspaceId}
```
Phản hồi cung cấp danh sách các bước có cấu trúc theo thứ tự:
```json
{
  "correlation_id": "corr_abc123",
  "workspace_id": "ws_123",
  "chain": [
    { "kind": "event", "id": "event_uuid", "at": "2026-08-28T10:00:00Z", "refs": { "event_type": "operations.task.created.v1" } },
    { "kind": "inbox", "id": "inbox_event_uuid", "at": "2026-08-28T10:00:01Z", "refs": { "event_id": "event_uuid" } },
    { "kind": "scheduled_task", "id": "task_123", "at": "2026-08-28T10:00:02Z", "refs": { "run_id": "run_456" } },
    { "kind": "run", "id": "run_456", "at": "2026-08-28T10:00:03Z", "refs": { "task_id": "task_123" } },
    { "kind": "artifact", "id": "art_789", "at": "2026-08-28T10:00:05Z", "refs": { "run_id": "run_456" } }
  ]
}
```

### 6.2. Chính sách Redaction
- Chuỗi correlation **tuyệt đối không bao gồm** tool raw output, token xác thực, hoặc payload chi tiết của nghiệp vụ.
- Tại thời điểm lưu trữ SSE stream events, mọi event không thuộc `UX_EVENT_TYPES` đều được chuyển đổi thành reference-only record:
  ```json
  {
    "event_ref": "<uuid>",
    "hash": "<sha256>",
    "classification": "internal"
  }
  ```

---

## 7. Capacity Review & Broker Gate

Tham chiếu: [`docs/operations/event-backbone-capacity-review.md`](event-backbone-capacity-review.md) · [ADR-LOCAL-EVENT-BACKBONE-001](../architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md)

**Broker (Kafka / Redpanda / NATS) KHÔNG được cài mặc định.** Trước khi bất kỳ ai thêm `kafka` / `redpanda` / `nats` vào một deployment manifest (`docker-compose*.yml`, k8s, infra): phải có một entry trong `## Review log` của capacity review với verdict cho phép PoC **và** cả ba `## Adoption preconditions` của ADR được đánh dấu thoả. Test `tests/architecture/test_event_backbone_adr_references.py::test_no_broker_in_deployment_manifests` chặn vi phạm này ở CI.

### 7.1. Lịch review
- **Hằng quý** — chạy quy trình `## How to run a review` trong capacity review doc với data window ≥ 30 ngày production.
- **Sớm hơn lịch quý** khi một trong hai SLO sau bị vi phạm liên tục > 15 phút trong production:
  - `p95 delivery latency` (metric `event_delivery_latency_seconds`) vượt 5s steady / 30s under retry.
  - `sustained outbox backlog` — số row `integration.event_outbox` ở `status='pending'` > 1000, hoặc tuổi p95 của row `pending` > 60s.

### 7.2. Kéo số đo nhanh
```sql
-- Sustained outbox backlog
SELECT count(*) AS pending, now() - min(created_at) AS oldest_age
FROM integration.event_outbox WHERE status = 'pending';

-- Consumer fan-out theo event type
SELECT event_type, count(DISTINCT consumer_name) AS consumers
FROM event_inbox GROUP BY event_type ORDER BY consumers DESC;

-- Storage cost (retention 30d)
SELECT pg_size_pretty(pg_total_relation_size('integration.event_outbox')) AS outbox_size;
```
`event_delivery_latency_seconds`, `event_retry_total`, `event_dlq_total`, `event_dedupe_total` lấy từ Prometheus scrape của metrics logger (`cosa.knowledge_ingestion.metrics` pattern — xem §2/§3).

### 7.3. Ai ký verdict
Mỗi entry `## Review log` cần chữ ký của **owner event runtime** + **một reviewer độc lập**. Verdict là một trong ba outcome của ADR: `keep Postgres outbox relay`, `add local optional broker profile`, hoặc `reject broker`. Verdict không tự động chuyển `ADR-LOCAL-EVENT-BACKBONE-001` sang `ACCEPTED` — xem `## Promotion of this ADR` trong ADR đó.
