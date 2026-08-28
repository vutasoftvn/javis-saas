# ADR-LOCAL-EVENT-BACKBONE-001: Event backbone capacity gate

## Status
PROPOSED — awaiting P2 capacity data (Số đo thực tế sẽ được thu thập và điền tại giai đoạn P2 - spec Task 9). Chuyển `ACCEPTED` chỉ khi `## Promotion of this ADR` thoả.

## Context
PostgreSQL transactional outbox relay là backbone P0/P1 ([ADR-LOCAL-FIRST-001 §Event backbone](ADR-LOCAL-FIRST-001-workspace-runtime-node-data-residency.md)). Có áp lực định kỳ đề xuất Kafka "cho scale"; ADR này đặt một gate **dựa số đo**, không dựa sở thích vendor. Business payload không rời local node — ràng buộc này áp cho **mọi** backbone kể cả broker.

## Decision inputs
Các chỉ số vận hành cần thu thập để đánh giá ngưỡng năng lực. Bảng này phải **khớp** phần "Decision inputs & sources" của [`event-backbone-capacity-review.md`](../../operations/event-backbone-capacity-review.md) — sửa một bên thì sửa cả hai.

| Input | Ý nghĩa | SLO khởi điểm (review lại mỗi quý) |
| --- | --- | --- |
| **p95 delivery latency** | Độ trễ phân phối sự kiện từ lúc commit outbox đến khi inbox tiếp nhận. | p95 ≤ 5s steady; ≤ 30s khi đang retry |
| **Sustained outbox backlog** | Số lượng bản ghi tích tụ trong outbox qua các khung giờ cao điểm. | tuổi p95 row `pending` ≤ 60s; count < 1000 sustained |
| **Consumer fan-out** | Mức độ phân nhánh consumer cho từng loại sự kiện trên cùng một runtime node. | ≤ 5 consumer / event type (thiết kế single-relay) |
| **Replay window** | Thời gian và chi phí tài nguyên khi cần replay một tập sự kiện trong quá khứ. | replay một ngày ≤ 10 phút |
| **Node resource use** | Mức tiêu thụ CPU/RAM/IOPS của tiến trình outbox relay so với database engine. | relay < 10% CPU node; < 500 MB RSS |
| **Operator recovery time** | Thời gian khắc phục sự cố khi relay hoặc consumer bị nghẽn (MTTR). | ≤ 15 phút với runbook |
| **Data-residency requirement** | Đảm bảo toàn bộ luồng sự kiện tuyệt đối không rò rỉ ra ngoài node cục bộ. | business payload không rời local node |
| **Cost & operational overhead** | Chi phí vận hành, bảo trì và tính đơn giản trong triển khai cho khách hàng. | < 2 GB / workspace ở tải dự kiến; không tăng bề mặt vận hành ngoài tầm operator |

## Candidate outcomes
1. **Keep Postgres outbox relay**: Giữ nguyên PostgreSQL outbox relay làm backbone duy nhất nếu đáp ứng đủ SLA.
2. **Add local optional broker profile per Workspace Runtime Node**: Bổ sung profile broker cục bộ (nhúng hoặc container local) cho các node có tải đặc thù cao.
3. **Reject broker**: Tiếp tục tối ưu hoá Postgres outbox (batching, partitioning, notification) và từ chối đưa thêm broker bên ngoài vào kiến trúc.

## Migration invariants
Bất kể kiến trúc backbone trong tương lai có thay đổi hay nâng cấp, các bất biến sau phải được duy trì tuyệt đối:
1. **Canonical event envelope**: Giữ nguyên cấu trúc envelope chuẩn hoá (`event-envelope.schema.json`).
2. **Inbox idempotency**: Tính chất dedup đúng-một-lần tại consumer dựa trên khoá duy nhất `(workspace_id, event_id, consumer_name)`.
3. **Local-first isolation**: Toàn bộ luồng truyền tải không rời khỏi Workspace Runtime Node.
4. **Outbox vẫn là điểm ghi trong domain transaction**: broker (nếu có) là transport phía sau relay, không thay outbox. Relay đổi target từ HTTP intake sang broker publish nhưng at-least-once + post-condition verification không đổi.

## Adoption preconditions
Cả **ba** điều kiện sau PHẢI được ghi nhận là thoả (trong một entry `## Review log` của capacity review) trước khi bất kỳ PoC broker nào được bắt đầu:

1. **Unmet documented Postgres outbox SLO** — có ít nhất một entry `## Review log` với số đo vi phạm một SLO ở `## Decision inputs`, kèm data window và thời lượng vi phạm.
2. **Workload cần independently scalable fan-out/replay** — single-relay không đáp ứng: fan-out > 5 consumer / event type, hoặc replay 24h > 10 phút, và không thể khắc phục bằng tối ưu Postgres (batching, partitioning, `LISTEN/NOTIFY`).
3. **Operator-approved local deployment/backup model** — mô hình triển khai + backup cho broker **trên** Workspace Runtime Node đã được operator duyệt; không tăng bề mặt vận hành ra ngoài tầm kiểm soát; giữ nguyên data residency.

Nếu thiếu bất kỳ điều kiện nào → outcome là `keep Postgres outbox relay` hoặc `reject broker`.

## Promotion of this ADR
`## Status` chuyển từ `PROPOSED` sang `ACCEPTED` chỉ khi:
- Có ≥ 1 entry `## Review log` trong [`event-backbone-capacity-review.md`](../../operations/event-backbone-capacity-review.md) với `Data window` ≥ 30 ngày production data, **và**
- Verdict của entry đó được ký bởi owner event runtime + một reviewer độc lập.

Trước đó ADR giữ `PROPOSED`. Verdict "keep Postgres outbox relay" cũng đủ để promote (nó là một quyết định có bằng chứng), miễn thoả hai điều kiện trên.

## Relates
- [ADR-LOCAL-FIRST-001](ADR-LOCAL-FIRST-001-workspace-runtime-node-data-residency.md) — §Event backbone (ADR này chi tiết hoá gate broker mà ADR đó đặt ra).
- [`docs/operations/event-backbone-capacity-review.md`](../../operations/event-backbone-capacity-review.md) — quy trình + log review.
- [`docs/operations/event-driven-agent-runtime-runbook.md`](../../operations/event-driven-agent-runtime-runbook.md) §7 — broker gate vận hành.
