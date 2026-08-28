# ADR-LOCAL-FIRST-001: Workspace Runtime Node data residency & execution-plane boundary

## Status
ACCEPTED 2026-08-28 (Lưu ý: ACCEPTED ≠ IMPLEMENTED ≠ WIRED ≠ VERIFIED ≠ PRODUCTION).

## Context
Kiến trúc COSA được chia thành 4 vùng kiến trúc theo CLAUDE.md. Trong hiện trạng mã nguồn, chỉ tồn tại một biến môi trường cấu hình `COSA_CONTROL_PLANE_URL` (`apps/cosa/composition/agent_plane.py:273-275`) đang được dùng chung cho cả scheduler, lease, knowledge và connector. Các tài liệu thiết kế ban đầu (`COSA_FINAL_INTEGRATION_...`, `BLUEPRINT_V2_RECONCILED_...`) không còn trong repo và thư mục `docs/architecture/adr/` chưa có ghi nhận chính thức về ranh giới data residency cho mô hình runtime node local-first.

Để đảm bảo quyền riêng tư dữ liệu doanh nghiệp và vận hành tự trị, cần xác định rõ ràng ranh giới phân định trách nhiệm và nơi cư trú của dữ liệu (data residency) giữa Workspace Runtime Node đặt tại hạ tầng local của khách hàng và VPS Platform Control Plane.

## Decision
Mỗi Workspace Runtime Node chạy cục bộ (local-first) là ranh giới tự trị độc lập chứa:
1. **Company Services (business truth)**: Dữ liệu nghiệp vụ, trạng thái domain, PostgreSQL nghiệp vụ.
2. **AgentOS & Agent Core**: PostgreSQL của Agent Core, local execution scheduler, transactional outbox và inbox.
3. **Evidence, Artifacts & Knowledge**: Toàn bộ kết quả thực thi, artifact, RAG source và vector embeddings.

VPS Platform Control Plane từ xa chỉ chịu trách nhiệm:
1. Xác thực danh tính nền tảng (platform identity/license).
2. Phân phối chính sách/entitlement đã lọc.
3. Metadata của registry/promotion.
4. Telemetry tổng hợp ở dạng đã sanitize/redacted (không chứa dữ liệu thô).

## Data residency

| Class | Local node | VPS allowed | Example |
| --- | --- | --- | --- |
| Business fact payload | Yes | No by default | Chi tiết công việc, thông tin khách hàng, nội dung giao dịch |
| Run / checkpoint / tool result | Yes | No by default | Checkpoint agent run, kết quả thực thi công cụ cục bộ |
| RAG source / chunk / embedding | Yes | No by default | Tài liệu nội bộ, vector embedding, tri thức RAG |
| Incident evidence | Local | Explicit redacted export only | Snapshot debug, error trace chi tiết |
| Skill / agent / policy identity | Cached / pinned | Yes | Manifest, spec version, definition hash |
| Event envelope metadata | Yes | Only aggregate-sanitized | Correlation ID, event type, aggregate ref |

## Execution-plane rule
1. `apps/cosa` tuyệt đối **không bao giờ** silently fallback từ URL thực thi cục bộ (`COSA_EXECUTION_PLANE_URL`) sang URL platform từ xa (`COSA_PLATFORM_CONTROL_PLANE_URL`).
2. Scheduler task payload chỉ lưu **reference** (`workspace_id`, `event_id`, `correlation_id`, artifact/ref IDs, exact spec pins), tuyệt đối không nhân bản payload nghiệp vụ thô (`raw business payload`).
3. Phân định rõ hai biến cấu hình:
   - `COSA_EXECUTION_PLANE_URL`: Điểm cuối của local scheduler/lease trên Workspace Runtime Node.
   - `COSA_PLATFORM_CONTROL_PLANE_URL`: Điểm cuối kết nối platform identity/license/connector.
   Việc hoàn thiện chuyển đổi toàn diện các call-site thuộc phạm vi `SPEC-EXEC-PLANE-SPLIT`.

## Event backbone
PostgreSQL transactional outbox relay là event backbone mặc định cho P0/P1. Các hệ thống message broker phức tạp như Kafka, Redpanda hoặc NATS **không** phải là dependency mặc định của hệ thống. Quyết định bổ sung broker chỉ được đánh giá lại thông qua `ADR-LOCAL-EVENT-BACKBONE-001` khi có đầy đủ số đo vận hành chứng minh PostgreSQL relay không đáp ứng được ngưỡng tải.

## Relates
- Bổ sung deployment profile local cho `ADR-CONTROLPLANE-001` (control-plane primitives tại `services/cosa` — vẫn giữ nguyên giá trị).
- Không supersede ADR nào.
