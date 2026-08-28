# Event backbone capacity review

**Reference:** [ADR-LOCAL-EVENT-BACKBONE-001](../architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md) · [Runtime runbook](event-driven-agent-runtime-runbook.md)

Tài liệu này cung cấp **dữ liệu đo được** cho quyết định broker trong `ADR-LOCAL-EVENT-BACKBONE-001`.
Chạy **hằng quý**, hoặc **sớm hơn** nếu một SLO bị vi phạm liên tục > 15 phút trong production
(alert từ metric ở [runbook §2/§3](event-driven-agent-runtime-runbook.md)).

Quyết định broker **không** dựa sở thích vendor. Không thêm `kafka` / `redpanda` / `nats` vào bất kỳ
deployment manifest nào cho tới khi `## Review log` có một entry với verdict cho phép PoC **và** cả ba
`## Adoption preconditions` của ADR được đánh dấu thoả.

---

## Decision inputs & sources

| Decision input | Nguồn số đo | SLO khởi điểm (review lại mỗi quý) |
| --- | --- | --- |
| **p95 delivery latency** (outbox append → inbox recorded) | `event_delivery_latency_seconds` histogram (runbook metrics) | p95 ≤ 5s ở steady state; ≤ 30s khi đang retry |
| **Sustained outbox backlog** | `event_outbox_backlog` gauge *(chưa có — xem "Metric gaps")* + `SELECT count(*), min(created_at) FROM integration.event_outbox WHERE status='pending'` | tuổi p95 của row `pending` ≤ 60s; count < 1000 sustained > 15 phút thì mở review |
| **Consumer fan-out** | Số `consumer_name` phân biệt trong `event_inbox` theo `event_type` | ≤ 5 consumer / event type với thiết kế single-relay hiện tại |
| **Replay window** | Thời gian replay 24h outbox, đo thủ công trong drill (`event_replay_duration_seconds` khi có) | replay một ngày ≤ 10 phút |
| **Node resource use** | Host metrics (CPU %, RSS) của process relay + Postgres outbox load | relay < 10% CPU node; < 500 MB RSS |
| **Operator recovery time** | Incident log — MTTR cho sự cố "relay stuck" ([runbook §3](event-driven-agent-runtime-runbook.md)) | ≤ 15 phút với runbook |
| **Data-residency requirement** | Chính sách hiện hành ([ADR-LOCAL-FIRST-001 §Data residency](../architecture/adr/ADR-LOCAL-FIRST-001-workspace-runtime-node-data-residency.md)) | business payload không rời local node — mọi backbone kể cả broker phải giữ ràng buộc này |
| **Cost & operational overhead** | Kích thước `integration.event_outbox` sau retention 30d, theo workspace; bề mặt vận hành thêm | < 2 GB / workspace ở tải dự kiến; không tăng bề mặt vận hành ngoài tầm kiểm soát operator |

Bảng này phải **khớp** phần `## Decision inputs` của `ADR-LOCAL-EVENT-BACKBONE-001` — sửa một bên thì sửa cả hai.

---

## Metric gaps

Các metric còn thiếu để review đầy đủ (chỉ **đề xuất**, không implement trong P2 — mở ticket khi chạy
review thật đầu tiên):

- `event_outbox_backlog` gauge — số row `status='pending'` và tuổi row cũ nhất, scrape định kỳ.
- `event_replay_duration_seconds` — đo thời lượng một lần replay drill (24h window).

Cho tới khi có, các cột tương ứng trong `## Review log` điền bằng số đo thủ công (SQL query ở bảng trên)
hoặc `insufficient data`.

---

## How to run a review

1. **Chọn data window** — quý gần nhất, tối thiểu 30 ngày production data. Nếu chưa đủ: ghi
   `insufficient data` và verdict mặc định `keep Postgres outbox relay (no broker)`.
2. **Kéo từng số đo** ở bảng `## Decision inputs & sources` cho window đó.
3. **So với SLO khởi điểm.** Ghi rõ số đo nào vượt ngưỡng và trong bao lâu.
4. **Áp `## Adoption preconditions` của ADR** — cả ba điều kiện phải thoả mới cân nhắc PoC broker:
   một unmet documented Postgres outbox SLO, một workload cần fan-out/replay scale độc lập, và một
   operator-approved local deployment/backup model.
5. **Ghi verdict** vào `## Review log` (append một hàng, không sửa hàng cũ). Ký tên: owner event
   runtime + một reviewer độc lập. Verdict là một trong ba outcome của ADR.

---

## Review log

Append-only. Mỗi chu kỳ review thêm đúng một hàng.

| Quarter | Data window | p95 delivery latency | Sustained outbox backlog | Consumer fan-out | Replay window | Node resource | Operator MTTR | Storage cost | Verdict | Signed-off by | Date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Initial (P2 setup) | N/A | insufficient data | insufficient data | insufficient data | insufficient data | insufficient data | insufficient data | insufficient data | keep Postgres outbox relay (no broker) | _(điền khi chạy)_ | _(điền khi chạy)_ |
