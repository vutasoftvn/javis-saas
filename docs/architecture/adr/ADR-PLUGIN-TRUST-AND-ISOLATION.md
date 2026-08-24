# ADR-PLUGIN-TRUST-AND-ISOLATION: Trust tier + lifecycle cho plugin bên thứ ba

- **Trạng thái:** PROPOSED — **CHƯA implement**, khác 5 ADR còn lại trong đợt này (đều đã có code). Ghi lại quyết định kiến trúc mục tiêu, không phải trạng thái đã đạt được.
- **Ngày quyết định:** 2026-08-24
- **Tác giả:** COSA Core Architecture Team
- **Tham chiếu:**
  - `COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md` §11
  - `packages/agent_core/plugins/manifest.py`
  - `plugins/README.md`

---

## 1. Bối cảnh

`packages/agent_core/plugins/manifest.py` đã có `PluginManifest`/`PluginRegistry` (plugin_id, name, version, publisher, capabilities, permissions) và `plugins/<plugin-name>/{manifest.yaml,skills/,tools/,resources/,ui/}` đã có convention filesystem — nhưng **KHÔNG có**:
- Trust tier (T0 built-in / T1 signed internal / T2 third-party isolated).
- Lifecycle state (`DISCOVERED → INSTALLED → VERIFIED → ENABLED → DEGRADED/DISABLED → RETIRED`).
- Signature/hash verification.
- Isolation mechanism cho Tier 2 (process/container/MCP/A2A/sandbox).

Đây là gap thật, khác với các gap khác đã audit trong phiên này (schema tồn tại nhưng thiếu code) — ở đây CẢ schema lẫn code cho trust/lifecycle đều chưa tồn tại.

## 2. Quyết định (mục tiêu, chưa implement)

1. **Mở rộng `PluginManifest`** thêm: `trust_tier: Literal["T0","T1","T2"]`, `signature: Optional[str]`, `required_core_version: str`, `isolation: Literal["in_process","process","container","mcp","a2a","sandbox"]`, `lifecycle_state`.
2. **Tier 0** (built-in, in-process): không cần signature, chạy cùng process `agent_core`.
3. **Tier 1** (signed internal): phải có signature hợp lệ, pinned version, chạy in-process nhưng bị giới hạn `permissions` khai báo trong manifest — Gateway enforce, không tự ý mở rộng quyền.
4. **Tier 2** (third-party): BẮT BUỘC isolation ngoài process chính (`SandboxProvider` — chưa có Protocol này trong `agent_core`, cần tạo cùng lúc) hoặc qua MCP/A2A đã có (Wave 9).
5. **Lifecycle transition** phải qua state machine tường minh, mỗi transition ghi audit event — không cho phép skip trạng thái (vd DISCOVERED → ENABLED trực tiếp, bỏ qua VERIFIED).
6. **Migration mới cần** (chưa đặt tên/số cụ thể) để lưu `plugin_registrations` durable — hiện `PluginRegistry` chỉ in-memory (`self._plugins: dict[...]`), cùng loại gap như các subsystem khác trước khi được Postgres-hoá.

## 3. Lý do KHÔNG implement trong đợt Wave 0-11 này

1. Không có plugin bên thứ ba thật nào cần cài trong codebase hiện tại — implement trust/isolation cho use case chưa tồn tại là premature (đúng nguyên tắc CLAUDE.md "Không tạo feature khi chưa cần", đã áp dụng nhất quán cho các quyết định hoãn khác trong phiên này — Skill Optimization Lab là ngoại lệ vì có trigger thật do người dùng xác nhận).
2. `SandboxProvider` Protocol (cần cho Tier 2 isolation) chưa tồn tại — đây là phụ thuộc chưa giải quyết, nằm ngoài phạm vi Blueprint V2 Wave 0-11 đã thực hiện.

## 4. Điều kiện kích hoạt lại

Giống mẫu `ADR-SKILL-IDENTITY`: implement khi có plugin bên thứ ba THẬT cần tích hợp — không prebuild trước.
