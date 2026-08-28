# Part 2F — Hoãn nhưng ghi quyết định

**Master:** [`2026-08-28-test-prod-readiness.md`](./2026-08-28-test-prod-readiness.md)
**Phụ thuộc:** —
**Ước lượng:** 0.5 ngày (chỉ ADR/ticket) hoặc +1–2 ngày nếu chọn implement
**Nhánh:** `tpr/part2f-deferred-decisions`

## Mục tiêu

Các hạng mục không chặn go-live nhưng phải có **quyết định chính thức** (ADR hoặc ticket) trước prod, để không rơi vào "self-report Wave hoàn thành" mà thực chất còn stub (CLAUDE.md — bài học §29.1).

## Trạng thái hiện tại (verify bằng code)

| Hạng mục | Trạng thái | Bằng chứng |
| --- | --- | --- |
| Conversation history port | **STUB** | `apps/cosa/conversations/stub.py` — `StubConversationHistoryPort` trả rỗng/an toàn. Repository Postgres đã có ở `packages/agent_core/conversations/`. Hệ quả: context đa lượt chỉ có lượt hiện tại. |
| Runtime agent registration API | **KHÔNG CÓ** | 3 agent hard-code (`apps/cosa/agents/specs.py`), seed lúc startup (`seed.py`). Không endpoint publish spec runtime. Thêm agent = sửa code + redeploy. |
| Operations evidence-scoring weights | **CHƯA CALIBRATE** | TODO trong `services/company/operations` — "tinh chỉnh trọng số theo thực nghiệm vận hành". |
| Manual tool loop kernel | Legacy, opt-in | `runtime="manual_tool_loop"` — giữ làm fallback, không phải path chính. |

## Thay đổi cụ thể

### 2F.1 Conversation history port — ADR hoặc implement

**Khuyến nghị: implement** (repository đã có, chi phí thấp, ảnh hưởng chất lượng agent đa lượt lớn):
- `apps/cosa/conversations/postgres_port.py`: `PostgresConversationHistoryPort` implement cùng interface `StubConversationHistoryPort`, dùng `packages/agent_core/conversations/` repository (in-memory + Postgres backend đã tồn tại).
- Wire trong `apps/cosa/composition/agent_plane.py`: production dùng Postgres port, test dùng stub/in-memory.
- Giới hạn context window (N lượt gần nhất hoặc token budget) trong `context_assembler.py`.
- Test: `tests/apps/cosa/conversations/test_postgres_port.py` — lưu + đọc lại lịch sử, scope theo `workspace_id` + `conversation_id`, cắt theo N.

Nếu **không** implement kịp: `docs/architecture/adr/ADR-CONV-001-single-turn-launch.md` chấp nhận single-turn context cho launch, ticket follow-up, ghi rõ hệ quả UX.

### 2F.2 Runtime agent registration API — ADR + ticket

- `docs/architecture/adr/ADR-AGENT-REG-001.md`: chấp nhận **3 agent seed** cho launch (đủ MVP), registration API là feature post-launch.
- Ticket mô tả scope tương lai: endpoint `POST /agents/specs` trong `apps/cosa/api`, validate `prompt_ref` + `model_policy_ref` tồn tại (invariant INV-A3), ghi spec registry, immutability qua `definition_hash`. Reuse `PostgresSpecRegistryRepository`.
- Ghi vào master §5 (deferred) + link.

### 2F.3 Evidence-scoring weights — ticket

- Ticket: thu thập dữ liệu vận hành thật sau launch → calibrate trọng số. Cho tới lúc đó dùng default hiện tại, ghi chú "chưa hiệu chỉnh" ở nơi hiển thị điểm.

### 2F.4 Bảng "deferred" hợp nhất

Thêm mục "Deferred — quyết định chính thức" vào `docs/implementation/readiness-reporting-standard.md` hoặc master, liệt kê từng hạng mục + link ADR/ticket + điều kiện re-open.

## Reuse

- `packages/agent_core/conversations/` repository (Postgres + in-memory).
- `apps/cosa/composition/agent_plane.py` factory pattern (production vs test).
- `PostgresSpecRegistryRepository`, invariant INV-A3.
- Format ADR trong `docs/architecture/adr/`.

## Test / verify

- (Nếu implement 2F.1) `test_postgres_port.py` xanh; golden-path E2E-3 kiểm agent đa lượt nhớ được lượt trước.
- ADR files review + approve.
- Master §5 + readiness-reporting-standard cập nhật, `check-doc-links` xanh.

## Definition of Done

- [ ] Conversation history: hoặc `PostgresConversationHistoryPort` wired + test, hoặc `ADR-CONV-001` + ticket.
- [ ] `ADR-AGENT-REG-001` + ticket registration API.
- [ ] Ticket calibrate evidence-scoring weights.
- [ ] Bảng "deferred" hợp nhất, mỗi mục có link + điều kiện re-open.

## Rủi ro

- Nếu để conversation port stub mà UX kỳ vọng đa lượt → phàn nàn sớm ở prod. Ưu tiên implement.
- ADR "chấp nhận hoãn" dễ bị quên → mỗi ADR phải có "điều kiện re-open" cụ thể + ticket có owner.
