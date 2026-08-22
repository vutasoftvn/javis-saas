# Phase 0 — Land WIP đã có sẵn + P0 fix

> Chi tiết thực thi cho Phase 0 của `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md`. Phase này chặn tất cả các phase sau vì mọi thứ downstream phụ thuộc vào composition root (`AgentRuntime`/`ContextBuilder`/`ToolRegistry`) và trace sink ổn định.

## 0a. Trace redaction (§7.4 — P0 security)

**Task:**
1. Đọc kỹ diff hiện tại của `agentos/core/redaction.py` và `agentos/core/trace_sink.py` (`git diff agentos/core/redaction.py agentos/core/trace_sink.py`).
2. Review danh sách sensitive key trong `redaction.py`: xác nhận có đủ các pattern thường gặp — `api_key`, `apikey`, `secret`, `password`, `passwd`, `token`, `access_token`, `refresh_token`, `authorization`, `auth`, `bearer`, `private_key`, `client_secret`, `credit_card`, `ssn`. Bổ sung field nào còn thiếu trực tiếp vào bảng trong `redaction.py`.
3. Xác nhận `redact_payload()` xử lý đúng: nested dict, list of dict, list of primitive, giá trị `None`, số (không redact nhầm số thành chuỗi).
4. Chạy `pytest tests/agentos/test_redaction.py tests/agentos/test_trace_sink.py -v` — toàn bộ phải pass.
5. Kiểm tra `agentos/core/trace_sink.py` có đúng 1 điểm gọi `redact_payload()` trước khi ghi SQLite (không có nhánh nào ghi payload thô còn sót — ví dụ log debug, export function khác).
6. Kiểm tra §7.4 còn yêu cầu: retention, maximum payload size, correlation_id, tenant scoping — nếu chưa có trong `trace_sink.py`, thêm tối thiểu: giới hạn kích thước payload (truncate + đánh dấu `truncated: true`), cột `correlation_id`, cột `company_id/workspace_id` để scope theo tenant.
7. Commit riêng, message dạng `fix(agentos): redact sensitive trace payloads before persistence (P0)`.

**Acceptance:**
- [ ] Test `test_redaction.py`, `test_trace_sink.py` pass.
- [ ] Không còn field nhạy cảm nào (api_key, password, authorization, token...) xuất hiện raw trong SQLite trace sau khi ghi.
- [ ] Payload vượt kích thước tối đa bị truncate có đánh dấu, không bị silently drop toàn bộ record.
- [ ] Mỗi trace record có `correlation_id` và tenant scope.
- [ ] Diff được commit riêng, không gộp với 0b.

## 0b. Composition root (§9.2)

**Task:**
1. `git diff agentos/core/factory.py agentos/core/runtime.py agentos/core/adapters/contracts.py` — đọc kỹ toàn bộ.
2. Grep toàn repo (`agentos/`, `tests/`, mọi entrypoint server nếu có) tìm tất cả nơi gọi `build_default_runtime(`. Với mỗi chỗ: xác định có phải test cố ý dùng runtime tối giản không (giữ nguyên) hay là code path production/thực thi thật (phải đổi sang `build_cosa_agent_plane()`).
3. Xác nhận `build_cosa_agent_plane()` nhận đủ tham số cần thiết để chạy thật (encore_client hoặc HTTP client tới `services/`, memory retriever, skill router, skill instruction loader) và không có tham số nào bị `None` một cách âm thầm dẫn đến quay lại hành vi cũ.
4. Chạy `pytest tests/agentos/test_factory_composition.py tests/agentos/test_runtime_adapter_contract.py tests/agentos/test_runtime_convergence.py -v`.
5. Nếu chưa có, thêm 1 test end-to-end xác nhận: gọi `build_cosa_agent_plane()` xong, tool registry không rỗng (`len(registry.list_tools()) > 0`).
6. Commit riêng, message dạng `feat(agentos): make build_cosa_agent_plane the canonical production composition root`.

**Acceptance:**
- [ ] Không còn code path production nào gọi `build_default_runtime()` (chỉ còn lại trong test cố ý dùng runtime tối giản, nếu có, phải có comment giải thích rõ).
- [ ] `test_runtime_convergence.py` pass — governance/approval hoạt động độc lập với model provider.
- [ ] Tool registry sau khi composition có tool thật (không rỗng).
- [ ] Diff commit riêng, không gộp với 0a hoặc 0c.

## 0c. `agentos/improvement/` — quyết định: KEEP + document

**Task:**
1. Tạo `agentos/improvement/README.md` với nội dung tối thiểu:
   - Mục đích: Phase 10 Self-Improvement loop (gap detection → skill candidate → supply chain pipeline → human approval → promotion → ACTIVE).
   - Ownership: `agentos/improvement/`.
   - Operational status: `IMPLEMENTED / TESTED / NOT YET WIRED TO PRODUCTION EVAL PIPELINE`.
   - Gap còn lại: `GapDetector` hiện nhận `CapabilityOutcome` do caller đưa vào thủ công, chưa có nguồn cấp tự động từ eval history thật — việc wire này để ở Phase 10 (Observability & Eval), không xử lý ở Phase 0.
2. Thêm dòng tương ứng vào `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` (capability "Agent Self-Improvement", canonical owner `agentos/improvement/`, operational status như trên).
3. Không refactor/xoá bất kỳ file nào trong `agentos/improvement/` ở phase này.

**Acceptance:**
- [ ] `agentos/improvement/README.md` tồn tại và mô tả đúng trạng thái.
- [ ] `COSA_CANONICAL_OWNERSHIP_MAP.md` có dòng tương ứng, không còn là "thư mục không rõ nguồn gốc".

## Thứ tự thực hiện & rủi ro

0a và 0b độc lập, có thể làm song song bởi 2 người/2 nhánh khác nhau nhưng nên commit tách biệt để dễ revert nếu 1 trong 2 có vấn đề. 0c có thể làm bất cứ lúc nào, không phụ thuộc 0a/0b, ưu tiên thấp nhất trong Phase 0.

**Rủi ro chính:** đổi `build_default_runtime()` → `build_cosa_agent_plane()` có thể làm lộ ra các test/behavior cũ đang ngầm dựa vào `ToolRegistry` rỗng (ví dụ test kỳ vọng "no tool available" là hành vi mong muốn). Phải chạy full `pytest tests/agentos` sau khi cutover, không chỉ 3 file test liên quan trực tiếp.
