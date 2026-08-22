# Phase 4 — Agent Chat API & Text Chat MVP

> Chi tiết thực thi cho Phase 4 của `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md`. `agentos/api/` hiện **không tồn tại** (top-level `agentos/` chỉ có `agents, core, evals, improvement, knowledge, memory, observability, skills, tools, workflows`) — đây là phần greenfield lớn nhất của toàn bộ roadmap. Viết mới hoàn toàn, không port code cũ từ `legacy/`.

## 4a. Route + event contract (§17.1.1-17.1.2)

**Task:**
1. Tạo `agentos/api/` với cấu trúc:
```
agentos/api/
├── __init__.py
├── app.py                 # FastAPI (hoặc framework HTTP đang dùng trong agentos/) app instance
├── chat/
│   ├── routes.py           # 8 route bên dưới
│   ├── schemas.py          # Pydantic request/response DTO
│   └── event_stream.py     # SSE encode/sequence logic
└── tests/
```
2. Implement 8 route:
```
POST   /agent/conversations
GET    /agent/conversations
GET    /agent/conversations/{conversation_id}
PATCH  /agent/conversations/{conversation_id}
POST   /agent/conversations/{conversation_id}/messages
POST   /agent/runs/{run_id}/cancel
POST   /agent/approvals/{approval_id}/decision
GET    /agent/runs/{run_id}/events     # SSE
```
3. Mọi route xác thực qua `TenantContext` (Phase 1a) — client gửi `Authorization` header, server tự resolve company/workspace/role, **không nhận** `PermissionLevel`/role/tenant policy trực tiếp từ client.
4. Event type (SSE, mỗi event có `run_id, conversation_id, sequence (monotonic trong 1 run), event_type, timestamp, payload, correlation_id`):
```
run.started, message.started, message.delta, reasoning.status,
tool.requested, tool.started, tool.completed, tool.failed,
approval.required, approval.resolved, citation, attachment.processed,
run.completed, run.cancelled, run.failed
```
5. `GET /agent/runs/{run_id}/events` hỗ trợ resume: client gửi `Last-Event-ID` (chuẩn SSE) hoặc query param `since_sequence` → server trả lại từ sequence đó, không phát lại toàn bộ từ đầu, không bỏ sót.
6. `reasoning.status` chỉ chứa status/metadata (ví dụ "thinking", "calling tool X"), **không** chứa nội dung chain-of-thought thật.

**Acceptance:**
- [ ] 8 route hoạt động, có test cho từng route (unauthenticated → 401, cross-tenant → 403/404 không lộ thông tin).
- [ ] SSE stream phát đúng thứ tự event, sequence monotonic trong 1 run.
- [ ] Test resume: ngắt kết nối giữa chừng, reconnect với `since_sequence` → nhận đúng phần còn thiếu, không duplicate, không thiếu.
- [ ] Không route nào tin tưởng permission/role do client tự gửi.

## 4b. Conversation/Message/Attachment/RunEvent persistence (§7.2)

**Quyết định ownership DB (làm trước khi viết migration):** Agent Plane sở hữu conversation store theo guide gốc. Chọn 1 trong 2 hướng và ghi rõ lý do trong PR đầu tiên của bước này:
- (a) Dùng chung Postgres cluster hiện có của `services/`, tách schema riêng (ví dụ schema `agentos_chat`), truy cập qua kết nối riêng từ Python (không qua Encore/Drizzle).
- (b) Postgres riêng cho AgentOS.

Khuyến nghị (a) — không cần hạ tầng Postgres thứ hai — trừ khi có lý do vận hành cụ thể phát sinh khi implement.

**Task:**
1. Định nghĩa 4 bảng (SQLAlchemy hoặc ORM Python đang dùng trong `agentos/`, nhất quán với cách `agentos/memory`/`agentos/knowledge` kết nối DB):
```
Conversation: id, company_id, workspace_id, created_by_principal, title,
              active_agent_profile, created_at, updated_at, archived_at

Message: id, conversation_id, role, content, run_id, parent_message_id,
         status, created_at

MessageAttachment: id, message_id, object_ref, media_type, file_name,
                    size, checksum, knowledge_ingest_status

RunEvent: run_id, sequence, event_type, payload_redacted, created_at
```
2. Viết migration tương ứng (Alembic hoặc tool migration Python đang dùng trong repo — kiểm tra `agentos/` đã có sẵn migration tool nào chưa trước khi chọn công cụ mới).
3. `RunEvent.payload_redacted` phải đi qua `redact_payload()` (Phase 0a) trước khi lưu — dùng lại đúng hàm redaction, không viết logic redact thứ hai.
4. Attachment binary lưu object storage (MinIO hoặc tương đương đang có trong `infra/`), `MessageAttachment.object_ref` chỉ lưu reference, không lưu binary trong DB.
5. Soft-delete (`archived_at`) cho conversation — list mặc định không trả conversation đã archive.

**Acceptance:**
- [ ] 4 bảng tồn tại, migration chạy được.
- [ ] Test: tạo conversation → gửi message → tạo run → ghi run event → đọc lại đúng thứ tự.
- [ ] Test: message persist sống sót qua restart server (không phải in-memory).
- [ ] Test: `RunEvent.payload_redacted` không chứa secret khi payload gốc có field nhạy cảm.
- [ ] Attachment binary không nằm trong bảng `Message`/`MessageAttachment`.

## 4c. Wire ContextBuilder đủ các lớp context (§5.3)

**Task:**
1. Khi có message mới, `ContextBuilder` (đã wire memory/skill ở Phase 0b, Knowledge ở Phase 7 nếu đã xong) build context gồm: recent conversation turns (đọc từ `Message` bảng ở 4b), memory snippets, knowledge snippets (nếu Phase 7 xong, nếu chưa thì để rỗng có test xác nhận graceful — không crash), skill instructions, business snapshot qua read tool (gọi tool `risk_level=low`/read-only qua Tool Gateway).
2. Nếu Phase 7 (Knowledge) chưa xong khi làm tới bước này, `knowledge_snippets` trả `[]` một cách tường minh, có log/warning rõ ràng — không giả vờ có citation.

**Acceptance:**
- [ ] Test: context build từ 1 conversation có lịch sử → chứa đúng N turn gần nhất.
- [ ] Test: context không leak dữ liệu cross-tenant (2 conversation khác company → context tách biệt hoàn toàn).

## 4d. Flutter Chat UI MVP (§2.1, §17.1.3)

> Chưa audit `frontend/` độc lập trong roadmap tổng — trước khi ước lượng effort chi tiết, khảo sát nhanh cấu trúc `frontend/lib/` hiện có (module nào, pattern GetX đang dùng ở đâu) để tái dùng đúng convention thay vì tạo pattern mới.

**Task:**
1. Khảo sát `frontend/lib/modules/` xem đã có module chat/conversation nào chưa (kể cả dead code không route tới) — nếu có, đánh giá tái dùng thay vì viết mới.
2. Màn hình tối thiểu: sidebar conversation list, nút New chat, message composer, streaming Markdown render, attachment chip, tool activity card, approval card (approve/reject), cancel/retry button, agent/specialist identity indicator, run status, error/reconnect state.
3. Kết nối SSE (`GET /agent/runs/{run_id}/events`) — xử lý reconnect dùng `since_sequence` (4a).
4. Không render raw trace/secret/private reasoning chain — chỉ render field `reasoning.status` (status/metadata), không render nội dung suy luận nội bộ nếu backend có lỡ gửi kèm.

**Acceptance:**
- [ ] Conversation list, composer, streaming response hoạt động thật trên thiết bị/emulator.
- [ ] Approval card approve/reject gọi đúng `POST /agent/approvals/{approval_id}/decision`, UI cập nhật theo `approval.resolved` event.
- [ ] Test thủ công: ngắt mạng giữa response đang stream → UI reconnect, không mất/lặp nội dung.

## Dependency

4a độc lập (chỉ cần Phase 1a TenantContext + Phase 0b composition root). 4b có thể làm song song 4a, cần chốt DB ownership trước khi viết migration. 4c phụ thuộc 4a+4b, và phụ thuộc Phase 0b (memory/skill wiring) — Knowledge (Phase 7) là optional dependency, không chặn. 4d phụ thuộc 4a có route thật để gọi (có thể làm song song bằng mock trước khi 4a xong, nhưng cần audit `frontend/` trước).

## Ghi chú cho người triển khai bằng công cụ khác (Antigravity)

File này tự chứa đủ ngữ cảnh để thực thi độc lập, không cần đọc lại toàn bộ roadmap tổng — nhưng nếu có xung đột hiểu về `TenantContext`, `redact_payload()`, hay composition root, tham chiếu `docs/architecture/roadmap/phase-0-land-wip.md` và `phase-1-tenant-rbac.md` vì Phase 4 phụ thuộc trực tiếp 2 phase đó.
