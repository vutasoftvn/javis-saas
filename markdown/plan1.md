# Phân tích DeepSeek Harness & Đề xuất cấu trúc lại COSA

## Context

Người dùng muốn tham khảo kiến trúc **DeepSeek Harness** (`dsh`, https://deepseek.com/harness/en/ và https://github.com/deepseek-ai/deepseek-harness — repo có thật, 169k+ stars, TypeScript, MIT license) để rút ra pattern áp dụng cho core/tool/plugin của **COSA**. Mục tiêu không phải fork hay bọc dsh vào COSA — CLAUDE.md §6/§7/§15 đã cấm việc này ("Never couple COSA Business Core directly to DeepSeek Harness internals", "Do not fork DeepSeek Harness into COSA core") — mà là học pattern kiến trúc tốt để làm COSA vững hơn, đúng tinh thần §18 (composition tốt hơn, logic tất định tốt hơn, trừu tượng COSA thay vì lệ thuộc vendor).

Phát hiện quan trọng trong quá trình khảo sát: COSA hiện đang **vi phạm chính rule #14 của mình** ("No Duplicate Architecture") — có hai bộ khung song song cho gần như mọi khái niệm cốt lõi (Agent Runtime, Skills, Tools, Executors). Việc dọn dẹp này nên là ưu tiên trước khi làm gì khác, và nhiều pattern của dsh giúp định hình lại cách dọn dẹp đó.

Tài liệu này vừa là **phân tích đối chiếu**, vừa là **danh sách đề xuất đã ưu tiên hóa (P0/P1/P2)** kèm file cụ thể — coi như bản backlog kiến trúc để bạn chọn hạng mục triển khai sau.

---

## 1. Kiến trúc DeepSeek Harness (tóm tắt đối chiếu)

`dsh` xây trên **Cordis**, một plugin framework theo triết lý **"Everything is a plugin"** — không có core đặc quyền nào cả:

- **Plugin = object implement `Service`**; **context (`ctx`)** là kho chứa service, mỗi service giữ một khóa ổn định `ctx.<key>` (`ctx.tools`, `ctx.llm`, `ctx.sessions`...). Plugin khác tìm nhau qua khóa, không import trực tiếp implementation. Phụ thuộc khai báo qua `inject` (thứ tự boot suy ra từ yêu cầu service, không cần sequencing thủ công). Đăng ký (tool schema, adapter, listener...) là **reversible effect** (`ctx.effect()`/`ctx.on()`) — gỡ plugin thì tự động unwind.
- **Capability seam** — đơn vị mở rộng trung tâm: **Service Definition** (abstract class sở hữu `ctx.<key>`) + một/nhiều **Service Provider** (implementation) + một/nhiều **Consumer** (thường là tool cho model). Đổi 1 provider là đổi cả sản phẩm mà không fork gì (vd: trỏ filesystem+subprocess provider sang sandbox từ xa thì Bash/PTY/LSP đi theo luôn).
- **Profile & Bundle**: Profile là tổ hợp plugin có tên (`web`, `headless`), xếp chồng nhiều **bundle** (đơn vị phân phối plugin+config, cài/gỡ qua CLI: `dsh plugin --profile <name> add @pkg`), rồi patch theo layer (`cordis.patch.yml`). `dsh --profile web --dump-config` in ra toàn bộ cây đã resolve.
- **Core packages ("product API spine")**: `core/session` (`ctx.sessions`, event log append-only — nguồn sự thật duy nhất), `core/tools` (`ctx.tools`, registry + pipeline `pre-execute→execute→post-execute`), `core/agent` (interface + registry), `core/agent-loop` (driver mặc định, thay được), `core/scope` (đăng ký theo phạm vi 1 agent), `llm/llm` (adapter seam cho model).
- **Turn/Step/Round**: step = 1 request model + tool calls của nó; turn = 0..n step; round = 1 vòng chính sách bên ngoài (goal round, Ralph round). Pipeline hook rõ ràng: `turn/start → agent/pre-step → step/start → agent/request → llm/stream → tool/call* → tools/pre-execute→execute→post-execute → step/end → agent/turn-stopping → turn/end`.
- **Bất biến "model-visible means logged"**: bất cứ gì model thấy được đều phải suy ra được từ session log — nguồn sự thật duy nhất cho context.
- **Agent scope**: đăng ký là *global* hoặc *scoped* (1 agent sở hữu), 2 tầng phẳng, không kế thừa xuống subagent. *Shadowing*: tool/section theo scope đè tool cùng tên ở global cho riêng agent đó.
- **Agent Preset** (`packages/preset`): thư mục `agent.cordis.yml`, mount theo scope của 1 **session** cụ thể (không phải theo role) → nhiều agent cấu hình khác nhau chạy chung 1 process mà không đụng nhau. Preset cố đăng ký service process-global thì bị từ chối lúc mount.
- **Skill family**: `ctx.skills` catalog trung lập nhà cung cấp, nằm ngoài core spine — nguồn local/embedded/remote đều được mà không đổi hợp đồng model-facing.
- **Subagent family**: `ctx.subagents`, nhiều provider cùng tồn tại (spawn/fork in-process, ACP, Codex, Claude Code SDK, dsh-sdk). Codex/Claude-Code provider là **bundle tùy chọn độc lập**, cài/gỡ không đụng core.
- **Workflow family**: orchestration **do model tự viết**, chạy trong worker thread; `tool-ralph` là 1 policy cố định (Ralph loop — mỗi round là 1 fresh child session, chỉ nhận "Ralph handoff" report + workspace chung, không nhận lịch sử hội thoại).
- **Goal system**: mục tiêu bền vững theo session (`active/paused/blocked/complete`), state nằm trong session log. *Goal activation* (`armed`/`disarmed`) cố ý KHÔNG bền vững — resume tự động sau gián đoạn bắt buộc phải qua lệnh người dùng `/goal` hoặc tool call, không tự resume ngầm.
- **MCP bridge**: MCP chỉ là 1 tool provider khác đăng ký thẳng vào `ctx.tools`, không có đường dẫn đặc biệt riêng.
- **Extensions (self-referential runtime)**: agent có tool để tự soi/tự viết/tự gỡ plugin runtime của chính nó (sandbox `node:vm`) — tính năng rủi ro cao, cờ đỏ với triết lý governance của COSA.

---

## 2. Hiện trạng COSA (đã xác minh qua code, không suy đoán)

Repo đang **giữa chừng migration** (commit gần nhất: "migrate Business Core + Agent Runtime data models to backend/core/ và backend/agent_runtime/"). Có **hai bộ khung song song**:

**(A) Production / đã wire thật** — nằm dưới `backend/app/workforce/`:
- `adapters/{base.py,claude_adapter.py,deepseek_adapter.py,gemini_adapter.py,http_generic_adapter.py,factory.py}` — seam LLM thật, có factory.
- `agents/runtime/{base.py,types.py,tool_bridge.py}` — turn loop / tool bridge thật (`AgentRuntime`).
- `agents/runtime/adapters/deepseek_harness.py` — **`DeepSeekHarnessAdapter` đã tồn tại**, bọc package PyPI `deepseek-harness-sdk` qua JSON-RPC subprocess, implement `AgentRuntime`. `resume`/`fork` chưa làm (Phase 1 spike) — đúng như CLAUDE.md §6 mô tả (`COSA AgentRuntime → DeepSeekHarnessAdapter`).
- `skills/{skill_registry.py,skill_loader.py,schema.py}` + `tools/{auto_register.py,base.py,...}` — registry thật, có bảng SQLAlchemy (`ToolDefinition`, `PlatformToolVersion`).
- `agents/governance/kernel.py` — `GovernanceKernel.evaluate_and_audit_tool_call()` gọi `PolicyEngine.evaluate()`, trả ALLOW/DENY/REQUIRE_APPROVAL, audit mọi call thành `AgentToolCall`. Vừa fix (`ff0efa1`) để chặn thật thay vì chỉ log.
- `agents/capabilities/providers/claude_code_provider.py` — tích hợp Claude Code CLI thật qua subprocess.
- `tools/transports/mcp_adapter.py` (`MCPToolAdapter`), wired trong `gateway/gateway.py:47` — **MCP không hoàn toàn vắng mặt** như phỏng đoán ban đầu, nhưng chỉ là transport đơn giản (POST JSON-RPC `tools/call`, không có `initialize`/`tools/list` discovery). Tool MCP vẫn phải khai tay từng dòng, vd `mcp.github_search` trong `registry/defaults.py:555-558`.
- `agents/governance/models.py` (Postgres `AgentToolCall`/`AgentEventRecord`) + `agents/events/agent_event_bus.py` + `app/core/telemetry.py` (OTel) — lưu trữ trace/event production thật (Postgres, KHÔNG dùng SQLite scaffold).
- `backend/app/integrations/channels/plugins/plugin_host.py` — **xác nhận là stub thật**: `load_plugins()` trả `[]` với comment "In MVP, this is a placeholder"; `execute_plugin()` luôn trả `{"status": "success", "result": None}`.

**(B) Scaffold "canonical" mới** — phần lớn chưa wire, chỉ được test bởi `backend/app/tests/unit/test_phase*.py`, docstring tiếng Việt trích `markdown/Structure.md`:
- `backend/core/{finance,legal,marketing,sales,tasks,strategy,learning,validation}/models.py` — phần NÀY đã là canonical thật (SQLAlchemy models), `app/business/*`/`app/founder_os/*` cũ re-export từ đây.
- `backend/agent_runtime/{runtime,models,profiles,events,sessions,...}/` — phần lớn trùng lặp (B) so với (A): `runtime/base.py` trùng `app/workforce/agents/runtime/base.py`; `models/gateway.py`+`providers/*` trùng `app/workforce/adapters/*`. **Ngoại lệ đáng giữ**: `profiles/schema.py` (`AgentProfile`) + `profiles/registry.py` (singleton, tự đăng ký 12 profile: marketing/sales/finance/legal/research/product/tech/operations/hr/growth/customer_success/cofounder) — đã xác minh code, khớp chính xác công thức §4 (`skills + tools + workflows + model_policy + permissions`), chỉ là chưa được runtime thật tiêu thụ.
- `backend/skills/*`, `backend/tools/*` — trùng lặp registry của (A).
- `backend/workflows/base.py` (`WorkflowDefinition`/`WorkflowStep`) — workflow **tĩnh/tất định** (khác dsh — dsh cho model tự viết script động). Điều này thực ra ĐÚNG tinh thần §18, nên giữ tĩnh làm mặc định.
- `backend/executors/claude_code_executor.py` — **stub giả lập**, không gọi subprocess thật (khác hẳn `ClaudeCodeProvider` thật ở (A)).
- `backend/storage/sqlite/connection.py` + `agent_runtime/events/sqlite_event_store.py` + `agent_runtime/sessions/session_manager.py` — chỉ chạy trong phase-test; production dùng Postgres thay vì SQLite dù CLAUDE.md §10 nói SQLite mới đúng chỗ cho sessions/traces.

---

## 3. Đề xuất theo ưu tiên

### P0 — Sửa vi phạm rule đang tồn tại / thay stub MVP, rủi ro thấp

**P0.1 — Dọn dẹp trùng lặp scaffold-vs-production (vi phạm §14 đang diễn ra)**
Pattern mượn: nguyên tắc dsh — một Service Definition chỉ sở hữu một `ctx.<key>`, không có 2 implementation cạnh tranh cho cùng 1 năng lực. Quyết định: `backend/app/workforce/*` là canonical. Nghỉ hưu các bản trùng: `backend/agent_runtime/runtime/base.py`, `backend/agent_runtime/models/gateway.py`+`providers/*`, `backend/skills/*`, `backend/tools/*`, `backend/executors/claude_code_executor.py` (stub giả). **Giữ lại và di dời**: `backend/agent_runtime/profiles/*` (xem P1.2), `backend/storage/sqlite/*` (xem P1.4). Cập nhật `backend/app/tests/unit/test_phase*.py` theo. Size: **M**.

**P0.2 — Thay `PluginHost` bằng seam tool-provider MCP thật (gộp 2 việc: MCP thật + xóa stub plugin)**
Pattern mượn: MCP chỉ là 1 tool provider sau seam chung, không có đường riêng. Mở rộng `MCPToolAdapter` để làm handshake `initialize`/`tools/list` thật, rồi `PluginHost.load_plugins()` gọi discovery đó và đăng ký kết quả thành `ToolDefinition` qua đúng con đường `skill_registry.py`/`tools/auto_register.py` đã có — thay vì trả `[]`. Xóa nhu cầu khai tay từng dòng như `mcp.github_search`. File: `plugin_host.py`, `tools/transports/mcp_adapter.py`, `skill_registry.py`, `tools/auto_register.py`. Size: **M**.

**P0.3 — Tài liệu hóa turn/step lifecycle + bảng "extension point map"**
Thuần tài liệu, rủi ro 0, ngăn vi phạm §14 tương lai bằng cách cho contributor 1 bản đồ duy nhất. Dựa trên loop thật ở `agents/runtime/base.py`, `runtime/tool_bridge.py`, `agents/governance/kernel.py`. Thêm doc mới dẫn từ CLAUDE.md, kiểu bảng "muốn thêm X → đăng ký ở đâu" (thêm model provider → `adapters/factory.py`; thêm tool transport → `tools/transports/*`; thêm coding executor → `executors/registry.py`/`capabilities/providers/*`; thêm permission logic → chỉ ở `governance/kernel.py`, không bao giờ inline trong tool). Size: **S**.

### P1 — Cải thiện kiến trúc có ý nghĩa, effort trung bình

**P1.1 — Chính thức hóa "capability seam" làm quy ước adapter chung của COSA**
COSA đã có nửa pattern này: `tools/transports/base.py` (`BaseToolAdapter`) và `adapters/factory.py` có hình dạng Definition/Provider giống hệt dsh. Viết 1 ADR ngắn đặt tên rõ bộ ba (Definition = abstract base + vocabulary; Provider = adapter cụ thể; Consumer = call site), rà soát idiom đăng ký cho nhất quán giữa `adapters/factory.py`, `tools/transports/__init__.py`, `executors/registry.py` (hiện không nhất quán). Áp dụng cùng khung cho `claude_code_provider.py`. Size: **M**.

**P1.2 — Wire `agent_runtime/profiles/*` vào runtime thật**
Di dời `backend/agent_runtime/profiles/` → `backend/app/workforce/agents/profiles/`, rồi để việc khởi tạo agent (`agents/execution/manager.py`, `agents/runtime/base.py`) lấy tool/skill set và permission baseline từ `AgentProfile` thay vì wiring thủ công, đưa permission khai báo trong profile vào `GovernanceKernel`. Size: **M-L**.

**P1.3 — Lớp preset/override theo session, chồng lên `AgentProfile` theo role**
Pattern mượn: Agent Preset của dsh — mount theo scope 1 session, đè global cho riêng agent đó, có guard chống đụng service process-global. Thiết kế: `SessionOverride` trên `ExecutionContext` (`identity/context.py`), resolve tại `tool_bridge.py`. **Ràng buộc khác dsh, để tôn trọng §11**: override chỉ được thu hẹp/thêm *tầm nhìn* tool — không bao giờ được bỏ qua `GovernanceKernel.evaluate_and_audit_tool_call()`. Size: **M**.

**P1.4 — Một session/trace event log duy nhất**
Hiện có 3 nơi lưu: Postgres (`governance/models.py`, production thật), OTel (`core/telemetry.py`), và SQLite scaffold chết (`storage/sqlite/*`). Theo CLAUDE.md §10 (SQLite cho sessions/traces/cache), làm SQLite thành thật: áp bất biến "model-visible ⇒ logged" của dsh — turn loop trong `agents/runtime/base.py` append mọi turn/step/tool-call vào SQLite, context/prompt được suy ra từ log đó. Giữ Postgres `AgentToolCall` làm bản chiếu audit tuân thủ bền vững song song, OTel cho tracing liên dịch vụ — 3 thứ bổ trợ nhau thay vì lặp 3 lần. Size: **L**.

**P1.5 — Mức đầu tư cho `DeepSeekHarnessAdapter`**
Khuyến nghị: giữ mỏng. KHÔNG xây song song 1 bộ session/tool/agent-loop trong COSA để khớp nội bộ dsh. Chỉ làm `resume`/`fork` khi có yêu cầu sản phẩm cụ thể cần continuation-semantics của dsh; ROI thực sự nằm ở việc khai thác *pattern* (P0-P1 ở trên) vào runtime riêng của COSA, không phải đào sâu adapter. Khớp hoàn toàn §6/§7/§15 và thiết kế hiện tại của adapter.

### P2 — Suy đoán, chỉ làm khi có nhu cầu sản phẩm thật

- **Workflow engine động do model tự viết** (dsh `packages/workflow`) — `backend/workflows/definitions/*` cố tình tĩnh; §18 ưu tiên logic tất định hơn prompt logic, nên giữ tĩnh làm mặc định. Chỉ xây engine động nếu có nhu cầu orchestration thật. Size: L.
- **Họ subagent-provider có thể cắm nhiều loại** (dsh `packages/subagent`) — chỉ cần nếu COSA phải chạy nhiều agent được cấu hình khác nhau, cùng sống song song, nhiều hơn những gì `agents/execution/manager.py` làm hôm nay.
- **Seam catalog skill trung lập nhà cung cấp** — chỉ gộp `skill_registry.py`/`skill_loader.py` thành Definition/Provider tách bạch khi có nguồn skill thứ hai (catalog từ xa) xuất hiện thật.

---

## 4. Những gì KHÔNG nên copy từ dsh

- **Tool tự soi/tự sửa runtime của chính nó** (dsh `packages/extensions`) — mâu thuẫn trực tiếp §11 ("permission phải do code tất định thực thi, không phải LLM") và §12 (traceability). Không bao giờ cho tool của agent quyền sửa registry tool/skill của chính COSA.
- **Toàn bộ kernel DI/event Cordis** — over-engineering ở quy mô COSA hiện tại; FastAPI DI sẵn có + quy ước adapter/factory (P1.1) đã lấy được lợi ích thật mà không phải nhập 1 framework ngoại lai (chính nó lại vi phạm §14/§15).
- **Goal "armed/disarmed" tự resume mặc định (Ralph loop)** — có thể tham khảo làm pattern tài liệu, nhưng bất kỳ vòng lặp tự resume nhiều round nào cũng phải khóa việc re-arm sau `GovernanceKernel`, không bao giờ tự resume ngầm sau restart. Tối đa P2.
- **Mặt phẳng lệnh slash `ctx.commands` cho người dùng** — chưa thấy nhu cầu; `chat_execution_service.py` đã tách luồng chat/tool-call khỏi hành động platform rồi.

---

## 5. File trọng yếu (tham chiếu nhanh)

- `backend/app/workforce/agents/runtime/base.py`, `runtime/tool_bridge.py` — turn loop thật
- `backend/app/workforce/agents/runtime/adapters/deepseek_harness.py` — adapter dsh hiện có
- `backend/app/workforce/tools/transports/mcp_adapter.py`, `gateway/gateway.py` — MCP hiện tại
- `backend/app/integrations/channels/plugins/plugin_host.py` — stub cần thay
- `backend/agent_runtime/profiles/{schema.py,registry.py,definitions/}` — phần scaffold đáng giữ
- `backend/app/workforce/agents/governance/kernel.py`, `governance/models.py` — governance + audit thật
- `backend/storage/sqlite/connection.py`, `agent_runtime/events/sqlite_event_store.py` — SQLite scaffold chết, có thể hồi sinh
- `backend/app/tests/unit/test_phase*.py` — test đang neo vào scaffold, cần cập nhật khi dọn (B)

## 6. Xác minh

Đây là tài liệu phân tích/đề xuất, chưa đổi code. Khi bắt đầu triển khai bất kỳ hạng mục nào ở trên:
1. Chạy `git status` trước khi đổi để không đụng việc dở dang khác.
2. Với P0.1 (xóa scaffold trùng lặp): chạy `pytest backend/app/tests/unit/test_phase*.py` trước để biết baseline, cập nhật/xóa test theo quyết định giữ (A) làm canonical, chạy lại toàn bộ test suite backend sau khi dọn.
3. Với P0.2 (MCP thật): viết test tích hợp giả lập 1 MCP server trả `tools/list`, xác nhận `PluginHost.load_plugins()` trả đúng danh sách tool và tool được gọi qua `GovernanceKernel` như tool thường (không bypass permission).
4. Với P1.3 (session override): test đảm bảo override không bao giờ bypass `GovernanceKernel.evaluate_and_audit_tool_call()` — đây là yêu cầu an toàn cứng, không phải tùy chọn.
5. Với P1.4 (hợp nhất event log): so sánh số lượng event ghi vào Postgres trước/sau để đảm bảo audit trail không bị mất khi chuyển nguồn sự thật sang SQLite.
