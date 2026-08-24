# Integration: AG-UI

## 1. Mục đích

Normalize `RunEventRecord` (event nội bộ COSA) sang vocabulary AG-UI chung — Flutter/Web/Desktop tiêu thụ CÙNG 1 mapping, không nhận raw event nội bộ của từng runtime.

## 2. Khi nào sử dụng

Ở tầng SSE/streaming trước khi trả event cho client UI.

## 3. Không dùng cho việc gì

Chưa certify chính thức với AG-UI spec gốc — không dùng làm bằng chứng tuân thủ spec, chỉ là best-effort mapping theo mô tả Blueprint V2 §10.3.

## 4. Kiến trúc và luồng dữ liệu

```
map_run_event_to_ag_ui(event: RunEventRecord) -> AGUIEvent
  event_type nội bộ ("run.started", "tool.requested", ...) → AG-UI type (RUN_STARTED, TOOL_CALL_START, ...)
  không có tương đương rõ ràng (approval.required/resolved) → CUSTOM, giữ cosa_event_type gốc trong data
```

Event taxonomy nội bộ COSA **CHƯA versioned** (`run.started` không phải `run.started.v1` như Blueprint V2 §37 đề xuất) — quyết định không rename hàng loạt để tránh rủi ro.

## 5. Public contracts/API

`agent_integrations.ag_ui.event_mapper.{AGUIEvent, map_run_event_to_ag_ui}`.

## 6. Database/schema liên quan

Không có — đọc từ `agent_core.run_events` qua `RunRepository.list_events()`.

## 7. Cấu hình

Không có.

## 8. Ví dụ sử dụng

```python
events = await repo.list_events(run_id)
ag_ui_events = [map_run_event_to_ag_ui(e) for e in events]
```

## 9. Cách bổ sung implementation mới

Thêm entry vào `_EVENT_TYPE_MAP` khi có event_type nội bộ mới cần mapping rõ ràng (mặc định fallback `CUSTOM`).

## 10. Security/governance

Không tự lọc sensitive data — payload gốc pass-through vào `data`, caller (SSE endpoint) chịu trách nhiệm redaction nếu cần.

## 11. Error handling

Không raise exception — event không map được luôn có fallback `CUSTOM`.

## 12. Observability

Đây chính là cầu nối observability cho UI — `sequence_no` giữ nguyên để client resume qua Last-Event-ID.

## 13. Testing

`packages/agent_testkit/protocol_conformance/test_ag_ui_event_mapper.py` — map chuỗi event THẬT từ `OpenAIAgentsKernel.run()` thật (không phải fixture giả lập), verify thứ tự RUN_STARTED→...→RUN_FINISHED.

## 14. Migration/backward compatibility

Package mới hoàn toàn.

## 15. Troubleshooting

Client thấy nhiều `CUSTOM` không mong đợi: kiểm tra `_EVENT_TYPE_MAP` có entry cho event_type đó chưa.

## 16. Definition of Done

- [x] Mapping + test qua Run thật
- [ ] Certify với AG-UI spec chính thức (chưa có kết nối tài liệu spec trong môi trường phát triển)
- [ ] Versioned event taxonomy nội bộ (`.v1` suffix) nếu cần đa client version
