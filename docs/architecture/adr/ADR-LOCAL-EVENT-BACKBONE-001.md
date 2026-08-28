# ADR-LOCAL-EVENT-BACKBONE-001: Event backbone capacity gate

## Status
PROPOSED — awaiting P2 capacity data (Số đo thực tế sẽ được thu thập và điền tại giai đoạn P2 - spec Task 9).

## Decision inputs
Các chỉ số vận hành cần thu thập để đánh giá ngưỡng năng lực:
- **p95 delivery latency**: Độ trễ phân phối sự kiện từ lúc commit outbox đến khi inbox tiếp nhận.
- **Sustained outbox backlog**: Số lượng bản ghi tích tụ trong outbox qua các khung giờ cao điểm.
- **Consumer fan-out**: Mức độ phân nhánh consumer cho từng loại sự kiện trên cùng một runtime node.
- **Replay window**: Thời gian và chi phí tài nguyên khi cần replay một tập sự kiện trong quá khứ.
- **Node resource use**: Mức tiêu thụ CPU/RAM/IOPS của tiến trình outbox relay so với database engine.
- **Operator recovery time**: Thời gian khắc phục sự cố khi relay hoặc consumer bị nghẽn (MTTR).
- **Data-residency requirement**: Đảm bảo toàn bộ luồng sự kiện tuyệt đối không rò rỉ ra ngoài node cục bộ.
- **Cost & Operational overhead**: Chi phí vận hành, bảo trì và tính đơn giản trong triển khai cho khách hàng.

## Candidate outcomes
1. **Keep Postgres outbox relay**: Giữ nguyên PostgreSQL outbox relay làm backbone duy nhất nếu đáp ứng đủ SLA.
2. **Add local optional broker profile per Workspace Runtime Node**: Bổ sung profile broker cục bộ (nhúng hoặc container local) cho các node có tải đặc thù cao.
3. **Reject broker**: Tiếp tục tối ưu hoá Postgres outbox (batching, partitioning, notification) và từ chối đưa thêm broker bên ngoài vào kiến trúc.

## Migration invariants
Bất kể kiến trúc backbone trong tương lai có thay đổi hay nâng cấp, các bất biến sau phải được duy trì tuyệt đối:
1. **Canonical event envelope**: Giữ nguyên cấu trúc envelope chuẩn hoá (`event-envelope.schema.json`).
2. **Inbox idempotency**: Tính chất dedup đúng-một-lần tại consumer dựa trên khoá duy nhất `(workspace_id, event_id, consumer_name)`.
3. **Local-first isolation**: Toàn bộ luồng truyền tải không rời khỏi Workspace Runtime Node.
