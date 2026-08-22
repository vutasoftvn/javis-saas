# Phase 3 — Governance & Tool system nâng cấp

> Chi tiết thực thi cho Phase 3 của `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md`. Viết mới dựa trên codebase thật, tiếp nối `ToolSpec` đã được mở rộng `risk_level`/`tool_permission` ở Phase 1c.

## 3a. ToolSpecV2 (§10.3)

**Bối cảnh:** sau Phase 1c, `ToolSpec` đã có `risk_level`/`tool_permission`. Phase 3a mở rộng tiếp thành `ToolSpecV2` đầy đủ theo target guide.

**Task:**
1. Định nghĩa `ToolSpecV2` (Pydantic model) trong `agentos/tools/registry.py` hoặc file mới `agentos/tools/spec.py`:
```python
class ToolSpecV2(BaseModel):
    name: str                     # "<domain>.<resource>.<action>"
    version: str                  # "1.0.0"
    description: str
    input_schema: dict            # JSON Schema
    output_schema: dict
    handler: Callable
    permission_class: str         # giữ tương thích ngược, không xoá
    risk_level: ToolRiskLevel     # từ Phase 1c
    tool_permission: ToolPermission  # từ Phase 1c
    write_scope: Literal["workspace", "company", "none"]
    idempotent: bool
    reversible: bool
    approval_policy: Literal["always", "conditional", "never"]
    audit_policy: Literal["full", "minimal"]
    timeout_seconds: int = 15
    tags: list[str] = []
```
2. Viết hàm validate input/output tự động dựa `input_schema`/`output_schema` trước khi gọi `handler` — reject sớm nếu input không khớp schema, tránh handler crash giữa chừng.
3. Migrate từng tool trong `agentos/tools/clusters/*.py` sang khai báo đủ field `ToolSpecV2` (làm tuần tự theo cluster, không cần 1 PR làm hết — nhưng field `version/input_schema/output_schema/write_scope/idempotent/reversible/approval_policy/audit_policy/timeout_seconds` là bắt buộc cho tool mới từ nay trở đi).
4. `approval_policy`/`risk_level` phải được `PolicyEngine.evaluate_access()` (Phase 1c) đọc trực tiếp khi ra quyết định ALLOW/REQUIRE_APPROVAL/DENY — không duplicate logic quyết định approval ở tầng tool.

**Acceptance:**
- [ ] `ToolSpecV2` tồn tại, có test validate input/output schema reject đúng khi input sai kiểu.
- [ ] Ít nhất toàn bộ tool cluster đang active (theo Phase 0b đã audit) khai báo đủ `ToolSpecV2`.
- [ ] Không có logic approval trùng lặp giữa tool handler và `PolicyEngine`.

## 3b. Sửa vi phạm boundary `services/realtime_agent/voice_tools.py`

**Bối cảnh đã xác nhận (audit trực tiếp code):** dòng đầu file hiện có:
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from db.session import SessionLocal
from integrations.realtime import tools as backend_tools
from founder_os.strategy import tools as strategy_tools
from platform_core.vault import vault_tools
```
Và các hàm như `_get_ceo_brief_impl(workspace_id)` gọi `SessionLocal()` trực tiếp — đây là vi phạm chiều cấm `voice → legacy business modules` (§3.1 guide gốc).

**Task:**
1. Liệt kê đầy đủ mọi hàm trong `voice_tools.py` đang import từ `legacy/` — không chỉ 4 import đã biết, grep toàn file tìm hết.
2. Với mỗi hàm, xác định capability tương đương cần có ở Agent API (Phase 4). Nếu Phase 4 (Agent Chat API) **chưa xong** khi làm tới bước này, tạo tạm 1 lớp adapter HTTP nội bộ gọi thẳng `services/operations`, `services/commercial` (v.v.) qua REST/RPC public API hiện có của các service đó — **không** gọi DB trực tiếp, và **không** phụ thuộc `agentos/api/` nếu nó chưa tồn tại (đánh dấu rõ TODO để chuyển sang gọi Agent API khi Phase 4 xong, tránh làm 2 lần).
3. Xoá `sys.path.insert` và toàn bộ import `legacy/`.
4. Viết lại từng hàm thành gọi HTTP client (httpx async) tới endpoint tương ứng, truyền `TenantContext` (Phase 1a) qua header.

**Acceptance:**
- [ ] `grep -r "legacy" services/realtime_agent/voice_tools.py` không còn kết quả.
- [ ] Không còn `sys.path.insert`, không còn `SessionLocal` trong `services/realtime_agent/`.
- [ ] Test: gọi từng voice tool function, xác nhận nó thực hiện HTTP call (mock) thay vì DB call.
- [ ] Nếu đã làm xong Phase 4 trước đó, voice tool gọi thẳng Agent API, không qua lớp adapter tạm.

## 3c. Tool registry + naming convention (§10.4-10.5)

**Task:**
1. Rà soát toàn bộ tool name hiện có trong `agentos/tools/clusters/*.py`, đối chiếu convention `<domain>.<resource>.<action>` (ví dụ `operations.task.create`, `strategy.experiment.create`, `commercial.lead.list`). Đổi tên tool không đúng convention — giữ alias tên cũ (underscore) trong 1 bảng mapping ngắn hạn nếu có caller khác đang dùng tên cũ, để tránh breaking change đột ngột.
2. Xác nhận tool đăng ký chỉ qua đúng 1 composition path (`build_cosa_agent_plane()` từ Phase 0b) — không có `ToolRegistry()` nào được tạo rời rạc trong code production khác.

**Acceptance:**
- [ ] 100% tool active theo naming convention mới hoặc có alias mapping rõ ràng.
- [ ] Grep `ToolRegistry(` trong toàn repo chỉ còn xuất hiện ở đúng 1 composition path + test files.

## 3d. Audit sink + correlation id (§20.1-20.3)

**Task:**
1. Đảm bảo mọi tool call ghi audit record qua `agentos/core/trace_sink.py` (đã redact ở Phase 0a) có đủ field: caller principal (`TenantContext.userId`/`workforceMemberId`), tool name, input đã redact, approval status (ALLOW/REQUIRE_APPROVAL/DENY + ai approve nếu có), outcome (success/fail + lý do), `correlationId` (từ Phase 1a).
2. Đảm bảo `correlationId` được forward từ request gốc (Text Chat/Voice) xuyên suốt: request → AgentRun → tool call → services API call → domain event.
3. Test: 1 tool call full chain có cùng `correlationId` ở mọi điểm ghi log/audit.

**Acceptance:**
- [ ] Audit record có đủ field liệt kê trên, verify bằng test đọc lại từ trace sink.
- [ ] `correlationId` nhất quán xuyên suốt 1 request thật (test end-to-end, không chỉ unit test từng lớp riêng).

## Dependency

3a phụ thuộc Phase 1c (risk_level/tool_permission đã có trên ToolSpec). 3b độc lập về mặt code nhưng nên làm sau khi Phase 4 (Agent API) có sườn cơ bản để tránh viết code tạm rồi bỏ — nếu ưu tiên fix vi phạm boundary sớm, chấp nhận làm lớp adapter tạm như mô tả ở 3b bước 2. 3c có thể làm song song 3a. 3d phụ thuộc 3a (audit_policy field) và Phase 0a (redaction) đã xong.
