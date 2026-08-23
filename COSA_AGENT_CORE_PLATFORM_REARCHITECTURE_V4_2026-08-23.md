# COSA Agent Core Platform Re-architecture V4 — Phân tích & Phản biện V3, Roadmap "Promotion"

> **Revision:** V4 — 2026-08-23
> **Loại tài liệu:** Phản biện tài liệu V3 + Roadmap tái cấu trúc đã điều chỉnh, dựa trên audit code thật
> **Đối chiếu với:** `COSA_AGENT_CORE_PLATFORM_REARCHITECTURE_V3_2026-08-23.md` (cùng thư mục)
> **Phương pháp:** 8 lượt audit code/ADR thật (Explore agent, đọc code trực tiếp — không suy đoán) qua nhiều vòng phản biện với founder
> **Kết luận cốt lõi:** V3 đúng gần như toàn bộ về mặt kỹ thuật (verified line-by-line), nhưng chọn **sai problem class** — viết như đang migrate một hệ đang chạy production, trong khi thực tế là promotion một prototype inert lên canonical lần đầu tiên. Roadmap trong tài liệu này viết lại theo đúng bài toán thật.

# Phân tích & Phản biện: COSA Agent Core Platform Re-architecture V3 → Roadmap điều chỉnh

## Context

Tài liệu `COSA_AGENT_CORE_PLATFORM_REARCHITECTURE_V3_2026-08-23.md` đề xuất tách `agent_core` khỏi `agentos`, retire god-runtime (`runtime.py`/`executor.py`), adopt OpenAI Agents SDK làm execution kernel chính, và xây durable run/checkpoint/approval/connector/memory/knowledge/artifact architecture — với mục tiêu cuối là một Agent Platform tái sử dụng được cho nhiều app, không chỉ COSA.

Tôi đã cho 3 Explore agent đối chiếu **từng claim cụ thể** của tài liệu với code thật (baseline `eedfbac`, đúng như tài liệu ghi), và tự kiểm tra thêm `COSA_CANONICAL_OWNERSHIP_MAP.md`. Kết luận: **các claim kỹ thuật của tài liệu đều đúng với code**, nhưng tài liệu có những **khoảng trống chiến lược quan trọng** — không đối chiếu với tài sản đã tồn tại, không đối chiếu với 3 ADR (013/014/015) đã chốt hướng trong repo, và không nhắc tới ràng buộc `WorkforceMember`/CLAUDE.md. Founder đã xác nhận: `agentos/` **hiện chưa chạy production** (đúng như ADR-AGENTOS-001 khẳng định, dù bảng đầu ownership map ghi nhầm là "Active — Production Canonical") — nghĩa là đây là cơ hội tốt để rearchitect mạnh dạn, vì chưa có traffic thật phụ thuộc.

Founder đã chọn: viết **toàn bộ roadmap** (chiến lược, chưa code) để duyệt hướng trước khi lập plan chi tiết từng phase.

**Điều chỉnh quan trọng sau các vòng phản hồi:** bản nháp đầu tiên coi việc "agentos/ chưa wired production" chỉ là một tình tiết giảm nhẹ rủi ro, rồi vẫn đề xuất roadmap kiểu *migration* (làm durable dần dần trên chính `runtime.py`/`executor.py`, wrap `Executor` cũ thành `LegacyNativeKernel`, port module-theo-module...). Qua các vòng phản hồi, founder chỉ ra đúng: đây không chỉ là roadmap cần nhanh hơn, mà là **V3 chọn sai problem class**.

V3 giải bài toán:
```text
production runtime đang chạy → phải giữ traffic/state/contracts → migrate an toàn → compatibility → cutover
```
Trong khi thực tế COSA đang ở bài toán:
```text
prototype inert → chưa có production ownership → chưa có state/traffic cần bảo toàn → xây target runtime đúng ngay → promotion gate → wire lần đầu
```
Hai bài toán này dẫn tới kiến trúc và thứ tự triển khai khác nhau căn bản — không phải cùng một roadmap chạy nhanh hơn. Từ đây, mọi chỗ trong tài liệu này dùng chữ **"promotion"** (đưa VNext lên làm canonical + wire lần đầu) thay cho **"migration"** (di dời một hệ đang chạy) — để không ai, kể cả coding agent, hiểu nhầm rằng code hiện tại cần được bảo toàn.

---

## Operational Reality Before Architecture (bắt buộc đọc trước khi thiết kế bất kỳ phase nào)

Lỗi gốc của V3 là gộp chung nhiều khái niệm khác nhau vào một nhãn "Active"/"canonical". Sau audit P0.1 (xem box P0 bên dưới), lỗi này còn sâu hơn ban đầu tưởng: không chỉ có 1 trục "wired hay không", mà có **3 trục độc lập** cần tách bạch cho từng module:

```text
CANONICAL OWNERSHIP  ≠  CODE LIFECYCLE STATUS  ≠  RUNTIME SERVING STATUS
```

Một module hoàn toàn có thể vừa KHÔNG phải canonical owner, vừa FROZEN (không nhận feature mới), vừa **đang phục vụ traffic thật** — cả ba đúng cùng lúc, không mâu thuẫn nhau (ví dụ nghi vấn `legacy/agent_runtime/workforce`, xem P0 box). Bảng ownership map hiện tại (1 cột "Operational status") không đủ sức biểu diễn việc này — cần redesign thành nhiều cột độc lập:

| Component | Design ownership | Lifecycle | Wired | Deployed | Serving | Canonical target | Replacement |
|---|---|---|---|---|---|---|---|
| `agentos/*` | Agent platform candidate | Active dev | No | No | No | TBD — nguồn design experiment cho VNext | VNext |
| `legacy/agent_runtime/workforce` | Legacy | Frozen (ADR-012) | Referenced (route tồn tại) | Yes (port 8000, gated `--profile legacy`) | **No — xác nhận qua P0.0**: Flutter gọi `localhost:4000/cofounder/chat`, backend thật nghe `localhost:8000/api/v1/cofounder/chat`, không có rewrite/gateway nào nối 2 đầu → path mismatch có thật, feature hiện không hoạt động qua đường này. Đã được ghi nhận sẵn trong `docs/architecture/reports/2026-08-22-pre-frontend-integration-readiness.md`, không phải phát hiện mới. `legacy/backend` còn **không build được** (ADR-012). | No | VNext (không cutover từ hệ đang chạy vì không có gì đang chạy qua đường Flutter — nhưng vẫn là **nguồn requirement nghiệp vụ** giá trị nhất, xem 2.5) |
| VNext Agent Core (`packages/agent_core/`) | New | Planned | No | No | No | **Yes** | — |

**Quy tắc suy ra hành động (theo cột "Serving", trục quan trọng nhất cho quyết định migrate-hay-không):**
- `Serving = No` (dù Wired/Deployed có thể Yes, như `agentos/`) → không port implementation, không cần preserve behavior; chỉ là nguồn design experiment/invariant.
- `Serving = Yes` hoặc chưa verify được (như `legacy/agent_runtime/workforce`) → **không migrate implementation, nhưng phải audit và inventory observable behavior/contract** trước khi VNext được coi là đủ để cutover (xem P0.1B).
- `Canonical target = Yes` (VNext) → build sạch theo ADR invariants, lấy behavior requirement từ nguồn Serving=Yes, lấy design experiment từ nguồn Wired/Active-dev — nhưng **kiến trúc không thuộc về bất kỳ nguồn nào trong số đó**, nó được thiết kế mới.

## P0 — Đã audit vs còn phải verify (thứ tự điều tra đã cập nhật lần 2)

```text
P0.0  Resolve actual Flutter → backend routing (CHƯA XONG — path /cofounder/chat vs /api/v1/cofounder/chat chưa khớp)
        │
        ▼
P0.1  Correct architecture/runtime truth — agentos=INERT (đã verify) | legacy serving=PENDING P0.0
        │
        ▼
P0.1B Audit legacy serving behavior (Legacy Serving Behavior Inventory — xem bên dưới)
        │
        ├──────────────┐
        ▼              ▼
   P0.2 ADR-014    P0.3 ADR-015/workflows      (cả 2 đã audit xong — xem box "P0 audit")
        │              │
        └──────┬───────┘
               ▼
   P0.4  DeepSeek + Agents SDK spike (compatibility matrix — trong Vertical Slice 1)
               │
               ▼
        V4 Architecture Freeze → VNext Build → Legacy behavior/eval gate → Canonical entrypoint cutover
```

**Chỉ dùng cụm "legacy đang serving traffic" không kèm dấu hỏi SAU KHI P0.0 xong.** Trước đó, coi là 4 khả năng chưa phân biệt được: `DEPLOYED` (có chạy) / `REACHABLE` (có thể gọi tới) / `REFERENCED` (có code trỏ tới) / `TRAFFIC-SERVING` (có request thật đi qua) — không gộp chung thành "Active".

### P0.0 + P0.1B — Kết quả (2026-08-23): legacy KHÔNG serving, nhưng là nguồn requirement giá trị nhất trong repo

**P0.0** xác nhận `TRAFFIC-SERVING = No` cho đường Flutter→legacy: `frontend/lib/core/network/api_client.dart` có 2 base URL riêng (`baseUrl`→`localhost:4000` cho `services/`, `agentOsBaseUrl`→`localhost:8000`), nhưng `cofounder_api_service.dart:114-115` gọi `/cofounder/chat` qua `ApiClient.post` mặc định dùng `baseUrl` (port 4000) — trong khi route thật `/api/v1/cofounder/chat` chỉ tồn tại trên port 8000. Không có rewrite/gateway nối 2 đầu. **Đây là path mismatch có thật, đã được ghi nhận từ trước** trong `docs/architecture/reports/2026-08-22-pre-frontend-integration-readiness.md:44-45`. Thêm nữa, `legacy/backend` bị freeze theo ADR-012 và **hiện không build được** — chỉ chạy được (nếu build lại) qua `docker compose --profile legacy` (không phải default).

→ **Kết luận cập nhật**: không có hệ nào (kể cả `legacy/agent_runtime/workforce`) đang thực sự serving traffic qua Flutter hiện tại. Bảng 3-cột ở trên đã cập nhật `Serving = No` cho `legacy/agent_runtime/workforce`. Bước 10 vì vậy **không cần thiết kế "cutover từ traffic đang chạy"** — nhưng KHÔNG có nghĩa bỏ qua P0.1B: module này vẫn là nguồn thiết kế nghiệp vụ sâu nhất trong repo, chỉ là không cần một API-edge compatibility shim khẩn cấp như giả định ban đầu (xem 2.5 đã điều chỉnh).

**P0.1B** (Legacy Behavior Inventory, 17 mục, đầy đủ trong 2.5) cho thấy `legacy/agent_runtime/workforce` có nghiệp vụ **sâu và cụ thể hơn nhiều** so với `agentos/` (generic, chưa gắn business context): intent routing 6 bước (greeting fast-path, FOUNDER_REVIEW→company pulse, FOUNDER_DECISION/COMMAND→mission orchestration qua `ChiefOfStaffOrchestrator`, Challenge Mode phát hiện Solution Bias), stage-aware context (`company_stage` S0-S3, `StageResolverService`), streaming qua Postgres LISTEN/NOTIFY (không phải SSE giả như `agentos`), risk gating **R0/R2/R3/R4** (khác cả `ToolRiskLevel` LOW/MEDIUM/HIGH/CRITICAL của `agentos` lẫn `PermissionLevel` L0-L3 của ADR-014 — **phát hiện thêm: đây là vocabulary risk/permission thứ 3 trong repo**, cần reconcile ở Bước 7 cùng với ADR-014, không chỉ 2 hệ như đã tưởng).

---

## Đã thống nhất qua nhiều vòng phản biện (không cần bàn lại)

- **Problem class**: đây không phải "migrate hệ đang production" mà là "promotion của một prototype inert lên canonical lần đầu". Toàn bộ compatibility machinery kiểu migration (dual-write, resume-compat, `LegacyNativeKernel` production, gradual traffic split) **không cần thiết**.
- **`agentos/core/runtime.py`/`executor.py`/`orchestration/adk/orchestrator.py`/`api/chat/routes.py`**: freeze, không refactor sâu thêm; chỉ giữ làm reference/test harness; xoá ở Bước 11 sau khi VNext qua gate.
- **`packages/agent_core/` + `apps/cosa/`**: dựng ngay từ đầu (không đặt trong `agentos/vnext/`, không đợi ổn định rồi mới tách).
- **OpenAI Agents SDK**: kernel chính ngay từ đầu, không qua bước trung gian legacy kernel; spike DeepSeek-compat nằm trong Vertical Slice 1, không phải gate riêng chặn cả roadmap — và spike phải ra **compatibility matrix** (basic response, structured output, single/parallel tool call, streaming, tool-call IDs, usage, error propagation, context length, RunState resume, agent-as-tool, approval interruption), không chỉ PASS/FAIL — vì DeepSeek có thể dùng được cho một số `AgentSpec` mà không cần đạt 100% tương thích.
- **`PermissionLevel` (L0-L3) vs Risk/Approval**: **đã được ADR-014 chốt sẵn** đúng mô hình 3 lớp (permission = autonomy ceiling, tool risk = intrinsic classification, `evaluate_access()` 6-dimension kết hợp cả hai) — không cần thiết kế lại, chỉ cần hoàn thiện cutover (xem P0.2 bên dưới). **Giữ và mở rộng L0-L3, không thay bằng `RiskPolicy` độc lập.**
- **`agentos/workflows/`**: kiến trúc sạch, không coupling với `executor.py`, khớp đúng ontology `ExecutionKernel` (probabilistic) ⟂ `WorkflowEngine` (deterministic) cùng gọi xuống Capability Layer chung — port gần nguyên kiến trúc này vào VNext (giống `agentos/knowledge/`), chỉ thêm HTTP API + durable checkpoint store.
- **Bước 10 đổi tên**: gọi là **"canonical integration entrypoint"**, không phải "production entrypoint" — vì COSA còn dev; production promotion là quyết định riêng sau này khi sản phẩm sẵn sàng.
- **Nguyên tắc port**: port invariant đã chứng minh đúng (policy formula, tool spec field set, audit semantics), không copy nguyên file/class — trừ `agentos/knowledge/` và `mcp_adapter.py` (ít business coupling, port gần nguyên logic).
- **`Principal`**: phải là adapter/projection của `WorkforceMember` ngay từ contract đầu tiên, không map muộn.
- **Thuật ngữ**: dùng "promotion", tránh "migration" trong toàn bộ tài liệu.
- **Validation strategy**: 2 vertical slice (read-path, write+approval-path) thay vì gate go/no-go nặng nề tách riêng.

## P0 audit — đã điều tra xong (2026-08-23), cập nhật quyết định

### P0.1 — DEV-WIRED trace: KẾT LUẬN → `agentos/` INERT thật, nhưng phát hiện thêm quan trọng hơn câu hỏi gốc

`agentos/api/chat/routes.py` **xác nhận INERT** — không có HTTP entrypoint nào chạy nó (không service trong `docker-compose.yml`, không `agentos/main.py`, `agentos/api/app.py` chỉ được import trong test files). `build_cosa_agent_plane()` chỉ được gọi từ tests.

**Nhưng**: Flutter (`cofounder_api_service.dart:115`) gọi `POST /cofounder/chat` → nghi vấn ban đầu là có một backend thật đang chạy phục vụ nhánh này: `legacy/agent_runtime/workforce/api/cofounder_api.py` (route `/api/v1/cofounder/chat`), mount qua `legacy/backend/bootstrap/create_app.py` → `legacy/entrypoints/full_main.py` → `docker-compose.yml:118` (`uvicorn main:app --port 8000`).

⚠️ **Path không khớp tuyệt đối** (`/cofounder/chat` từ Flutter vs `/api/v1/cofounder/chat` ở backend) — audit ban đầu không tìm thấy gateway/rewrite nào giải thích chênh lệch này, cần verify runtime thực tế thêm.

**Hệ quả cho roadmap (tại thời điểm P0.1, trước khi P0.0 verify path)**: `legacy/agent_runtime/workforce` — thứ mà ownership map gọi là "Frozen migration source — KHÔNG phải canonical owner" — bị nghi ngờ là nhánh đang chạy phục vụ cofounder-chat. **Cập nhật sau P0.0 (xem box "P0.0 + P0.1B — Kết quả" phía trên): nghi ngờ này SAI** — path mismatch có thật, không có traffic nào đi qua. Đoạn kết luận gốc bên trên (giữ lại để thấy quá trình suy luận) đã bị thay thế: Bước 10 KHÔNG cutover từ traffic đang chạy của `legacy/agent_runtime/workforce` (vì không có), nhưng vẫn dùng nó làm nguồn requirement qua Legacy Behavior Inventory (2.5).

### P0.2 — ADR-014/PermissionLevel: KẾT LUẬN → hypothesis đã được ADR chốt sẵn, chỉ cần hoàn thiện cutover, không cần thiết kế lại

ADR-014 (`docs/architecture/adr/ADR-014-permission-model-L0-L3-canonical.md`) đã chốt đúng mô hình 3 lớp: `PermissionLevel` (L0-L3, autonomy ceiling) tách biệt `ToolRiskLevel`/`ToolPermission` (intrinsic risk của tool, đã có trên toàn bộ 17 tool trong `ToolSpecV2`), kết hợp qua `evaluate_access()` 6-dimension (`agentos/core/policy.py:293-417`, intersection: DENY > REQUIRE_APPROVAL > ALLOW). **Không cần quyết định kiến trúc mới** — chỉ cần hoàn thiện cutover: `executor.py` và `workflows/tool_step.py` chưa truyền đủ `execution_mode` vào `evaluate_access()` (tool_step.py hardcode `APPROVED_WORKFLOW`), và `PermissionClass` (lookup 1D cũ) vẫn sống song song chưa bị loại bỏ. → Việc ở Bước 7 đổi từ "thiết kế reconcile" thành "hoàn thiện cutover đã được ADR-014 định nghĩa" — rẻ hơn nhiều so với giả định ban đầu.

### P0.3 — ADR-015/workflows: KẾT LUẬN → kiến trúc đã đúng ontology đề xuất, sẵn sàng làm WorkflowEngine của VNext

`agentos/workflows/` (DAG engine, `ParallelStep`/`RetryStep`/`CompensatingStep`/`ApprovalGateStep`, YAML loader, `WorkflowDefinitionRegistry` có version history) **không có coupling hai chiều** với `executor.py`/`runtime.py` (0 import chéo, đã grep xác nhận) — khớp đúng ontology đề xuất:
```text
ExecutionKernel (probabilistic, ReAct)          WorkflowEngine (deterministic, DAG)
        │                                                │
        └──────────────── Capability Layer (ToolRegistry + PolicyEngine, dùng chung) ──┘
```
Chỉ thiếu 2 thứ trước khi cutover: HTTP API (hiện chỉ Python-internal) và durable checkpoint store (hiện in-memory `Workflow.checkpoints`, không persist qua restart). Không có design debt — chỉ là gap tính năng. → Bước 6/8: port gần nguyên kiến trúc `agentos/workflows/` (giống trường hợp `agentos/knowledge/`), thêm 2 gap trên.

## Còn mở thật sự — đã audit xong P0.0/P0.1B, chỉ còn 2 mục thật sự mở

| Câu hỏi mở | Mức | Cần gì để chốt |
|---|---|---|
| ~~Path mismatch~~ | ~~P0~~ | **Đã xong** — xác nhận path mismatch có thật, feature không chạy qua đường Flutter hiện tại (xem P0.0/P0.1B ở box trên) |
| ~~`legacy/agent_runtime/` archaeology~~ | ~~P1~~ | **Đã xong** — Legacy Behavior Inventory đầy đủ ở 2.5, dùng trực tiếp làm requirement cho `cofounder.yaml` |
| ~~Reconcile 3 hệ risk/permission vocabulary~~ | ~~P0~~ | **Đã chốt** — xem 2.6 "V4 Architecture Freeze: risk/autonomy model" bên dưới, không còn là câu hỏi mở |
| Spike DeepSeek-qua-OpenAI-Agents-SDK — compatibility matrix (basic response, structured output, single/parallel tool call, streaming, tool-call IDs, usage, error propagation, context length, RunState resume, agent-as-tool, approval interruption) | **P0, nhưng cô lập ở Model Port — không chặn việc xây Core** | Chạy trong Vertical Slice 1; kết quả là ma trận capability theo model (không PASS/FAIL nhị phân) đưa vào `ModelPolicy`/resolver — Bước 3-8 (Core, Capability, Workflow, Governance) build song song, không chờ spike này |
| Entrypoint "canonical integration" cụ thể ở Bước 10 — chỉ cần build đúng, không cần quyết định cutover vì không có traffic cũ | **P1 — product** | Không còn chặn kiến trúc, chỉ là lịch làm việc |

---

## Phần 1 — Phản biện tài liệu V3

### 1.1 Những gì V3 đúng và nên giữ

- **Chẩn đoán god-runtime chính xác 100%**: `runtime.py` build context + quản lý AgentRun + trace + route theo `task.metadata` (`orchestration_mode`, `preferred_runtime`) + xử lý approval exception + giữ `last_run/last_trace/last_context` mutable module-level — verified từng dòng.
- **`executor.py` đúng là mini agent framework tự viết** (MAX_TOOL_ROUNDS=5, ReAct loop, policy/approval/tool/trace/audit lồng trong 1 file) — complexity này sẽ phình to khi thêm parallel tool calls, nested delegation, resume-after-restart.
- **`agentos/api/chat/routes.py` có đúng 7 vấn đề nền tảng** tài liệu nêu: `_pending_runs` dict module-level (dòng 186), approval replay-from-scratch thay vì resume checkpoint (dòng 605-619), `asyncio.create_task()` không durable (dòng 501), request-scoped DB session lọt vào background task (dòng 508), cancel chỉ emit event chứ không cancel thật (522-546), streaming giả (full output nhét vào 1 `message.delta`, dòng 305-315), đọc citation từ `runtime.last_context` có race condition (318, 339).
- **`orchestration/adk/orchestrator.py` đúng là tên sai bản chất**: không dùng Google ADK runtime thật, tự chạy `asyncio.gather()` rồi synthesis bằng model_provider trực tiếp.
- **Định hướng lớn đúng**: tách contract (`RunRequest`/`RunResult`/`AgentSpec`/`ExecutionKernel`) khỏi execution engine cụ thể; durable run/checkpoint thay vì in-memory; approval resume chính xác thay vì rerun; typed control thay vì `metadata` dict untyped — đều là sửa đúng bệnh, không phải speculative.

### 1.2 Những gì V3 bỏ sót hoặc sai lệch — cần phản biện

**(a) Tài liệu phân loại sai bài toán: coi prototype như production cần migrate** *(đã thống nhất — xem box trên; giữ lại đây phần bằng chứng cụ thể)*
`agentos/` được ADR-AGENTOS-001 xác nhận là **explicitly inert, parallel runtime — chưa wired vào bất kỳ production entrypoint nào** (ghi lại 2 lần trong ownership map, lần cuối 2026-08-22, dòng 124 và dòng 189). Bảng tổng hợp ở đầu file ownership map lại ghi nhầm dòng "Agent Runtime (native) ... Active — Production Canonical turn runtime" — mâu thuẫn nội bộ này là lý do V3 lẫn giữa 4 trạng thái INERT/DEV-WIRED/PRODUCTION-WIRED/TARGET, dẫn tới roadmap thiên toàn bộ về *migration an toàn cho hệ đang chạy* (durable-hoá dần tại chỗ, giữ compatibility layer, wrap `Executor` cũ thành `LegacyNativeKernel`). `AgentRuntime`, `_pending_runs`, approval-replay-from-scratch, `asyncio.create_task()` không phải production incident cần vá tại chỗ — chúng là bằng chứng thiết kế cho thấy nhánh prototype này không nên được promote nguyên trạng.

**(b) Bỏ sót tài sản đã tồn tại — nguyên tắc port invariant đã thống nhất, đây là bằng chứng cụ thể (file:line) cho từng tài sản**

| V3 đề xuất xây mới | Source material đã có trong `agentos/` — invariant cần giữ (không copy nguyên file) |
|---|---|
| `connectors/` first-class, OAuth/credential vault, MCP normalization (§10, Phase 7) | `agentos/connectors/` đã chứng minh đúng shape 2-tier transport/tool adapter + `SecretStore`/`InMemoryVaultStore` (Vault) + Slack connector — giữ shape protocol này, thêm Gmail/Calendar/GitHub |
| `CapabilitySpec` với idempotency/retry/timeout/audit policy (§9.2) | `ToolSpecV2` (`agentos/tools/spec.py`) đã chứng minh đúng field set: `version`, `write_scope`, `idempotent`, `reversible`, `tags`, `approval_policy`, `audit_policy`, `timeout_seconds` — giữ field set này làm invariant cho `CapabilitySpec`, thêm `kind` đa dạng (MCP/CONNECTOR/AGENT/WORKFLOW) |
| MCP integration (Phase 7) | `agentos/tools/mcp_adapter.py` (`MCPToolAdapter`, `make_mcp_tool_spec()`) là ngoại lệ port gần nguyên logic — MCP transport layer ít business coupling |
| Knowledge ingest→embed→retrieve→citation (§14) | `agentos/knowledge/` là ngoại lệ port gần nguyên logic (2.3): pipeline ingest/parse/chunk/embed/index/retrieve/citation đã chạy được end-to-end với pgvector thật — chỉ thiếu **rerank** |
| Self-improvement evidence→proposal→approval→promotion (§34) | `agentos/improvement/` (`GapDetector`, `proposal.py`, `approval_gate.py`, `distillation.py`) — giữ invariant luồng evidence→proposal→approval; phần thật sự mới cần làm là wiring vào live eval feed (tự nhận gap trong README) |
| Audit ledger (§18.4) | `agentos/core/audit_sink.py` (`SqliteAuditSink`) — giữ invariant audit semantics (ai làm gì, tenant nào, policy nào, ai approve), không nhất thiết giữ SQLite làm storage |

→ Nếu viết lại các phần này từ đầu **mà không đối chiếu** (bỏ qua thuật toán/protocol đã đúng, ví dụ 6-dimension policy formula hay pgvector retrieval đã chạy được), sẽ tái diễn đúng sự cố "4 model Agent/AgentDefinition/AgentProfile/WorkforceMember trùng lặp" mà CLAUDE.md §14 dùng làm bài học — chỉ khác là lãng phí công sức thay vì trùng lặp runtime.

**(c) Bỏ qua 3 ADR đã chốt hướng trong repo (013/014/015)**
- ADR-013: `agentos/` là target, `legacy/agent_runtime/` bị phase out — khớp hướng V3, nhưng V3 không dẫn chiếu, có nguy cơ tạo tài liệu kiến trúc thứ hai xung đột thẩm quyền với ownership map. *(đã thống nhất: Bước 1 sửa ownership map sẽ dẫn chiếu ADR-013 luôn)*
- ADR-014 (`PermissionLevel` L0-L3) và ADR-015 (`agentos/workflows/` là workflow engine canonical) — tại thời điểm phản biện ban đầu chưa rõ cách reconcile với `CapabilitySpec`/coordination của VNext; đã được audit và chốt ở P0.2/P0.3 và mục 2.6.

**(d) "Tránh vendor coupling" (CLAUDE.md §18) vẫn đúng — đã thống nhất: `ExecutionKernel` port giữ được nguyên tắc này, spike gộp vào Vertical Slice 1 thay vì gate riêng.** Kết quả spike vẫn là ẩn số thật (P0.4), nhưng không còn chặn việc xây Core (xem "Còn mở thật sự" phía trên).

**(e) `Principal`/identity model của V3 không nhắc `WorkforceMember`**
CLAUDE.md §5 và ownership map đều khẳng định: workforce (human hoặc AI) phải resolve qua **một** identity thống nhất `WorkforceMember` (`services/identity`, bảng `core.workforce_members`) — không tách policy Human/Agent. V3 §4.3/§18.1 định nghĩa `Principal`, `AgentIdentity` như khái niệm core mới mà không map rõ vào `WorkforceMember` hiện có. Vì VNext được thiết kế sạch ngay từ đầu (không phải migrate dần), đây là thời điểm rẻ nhất để làm đúng: **`Principal` trong `agent_core` phải là adapter/projection của `WorkforceMember` ngay từ bản thiết kế contract đầu tiên**, không map muộn ở cuối roadmap.

**(f) Packaging `packages/agent_core` nên bắt đầu ngay từ đầu, không để cuối cùng**
Khác với đánh giá ban đầu (đợi ổn định rồi mới tách), vì đây là greenfield build trong dev phase — dựng thẳng `packages/agent_core/` (core, không biết gì về COSA domain) + `apps/cosa/` (composition) làm skeleton từ Phase VNext đầu tiên là rẻ hơn, đúng như V3 §39 mong muốn (core phải chứng minh được bằng app thứ 2). Việc "tách sau" chỉ hợp lý khi đang sửa một hệ đang chạy; ở đây không có ràng buộc đó.

### 1.3 Kết luận phần phản biện

Tài liệu V3 kỹ thuật đúng và framework tốt (đặc biệt: durable run, typed contract, capability gateway, event protocol, execution kernel port) — giữ nguyên triết lý nền tảng: Python cho Agent Core, OpenAI Agents SDK là execution kernel chứ không phải domain architecture, business truth thuộc `services/`, Policy/Approval/Audit/tenant scope do COSA sở hữu, connectors/memory/knowledge/artifacts/evals là first-class. Nhưng nó viết như đang tái cấu trúc một hệ **đang chạy sản xuất**, nên thiên về an toàn/tuần tự/tương thích ngược. Với COSA còn dev và `agentos/` chưa từng có traffic, hướng đúng là quyết đoán hơn nhiều: **freeze prototype cũ → xây VNext sạch trực tiếp trong boundary mới → integrate/eval → chuyển entrypoint dev sang VNext → xoá/archive runtime cũ.** Roadmap Phần 2 dưới đây viết lại theo hướng đó.

---

## Phần 2 — V4: Roadmap "Promotion", không phải "Migration"

### 2.1 Bảng thay đổi quyết định so với V3

| V3 | V4 sửa thành |
|---|---|
| Durable-hoá runtime hiện tại trước | **Không.** Xây durability trong VNext mới, không đụng `runtime.py`/`executor.py` |
| Wrap `Executor` thành `LegacyNativeKernel` | **Không bắt buộc** — chỉ reference/test harness nếu cần đối chiếu hành vi |
| Preserve approval/run compatibility với code cũ | **Bỏ hoàn toàn** — không có state/traffic nào cần bảo toàn |
| Gradual migration nhiều phase tuần tự | **Promotion + first cutover** — xây xong, qua gate, wire lần đầu |
| Refactor `AgentRuntime` | **Không đầu tư** — freeze prototype |
| Refactor `api/chat/routes.py` | **Không** — viết API target mới trong `apps/cosa/api/` |
| Dual-run/dual-write | **Không cần**, trừ khi dùng tạm để benchmark VNext vs prototype |
| Incremental package restructuring | **Đổi package boundary ngay** — `packages/agent_core/` + `apps/cosa/` từ đầu, không đặt trong `agentos/vnext/` |
| Giữ old contracts để giảm breakage | **Chỉ giữ contract nào DEV-WIRED thật cần** (xem action item Bước 1) |
| "Migration phases" | **Build phases + promotion gates** |
| Port module-theo-module (`ToolRegistry` → `capabilities/registry.py`, ...) | **Port invariants đã được chứng minh đúng, không port nguyên file** — xem 2.3 |

### 2.2 Target lifecycle (11 bước, không phải "migration phases")

```text
1. Correct architecture truth
2. Freeze inert prototype
3. Define VNext contracts
4. Build clean reusable Agent Core
5. Integrate OpenAI Agents kernel
6. Add durable run/checkpoint/event model
7. Add governance/capability/connector layer
8. Compose COSA app on top
9. Run eval + integration + security gates
10. Wire first canonical integration entrypoint
11. Archive/delete inert prototype
```

Bước 3–7 **không cần làm tuần tự** — có thể triển khai song song theo vertical slice (2.4), miễn là mỗi slice đi xuyên hết chiều dọc thay vì hoàn thiện từng layer riêng lẻ rồi mới ráp lại.

**Bước 1 — Correct architecture truth** *(P0.1 đã audit xong — cập nhật addendum theo kết quả thật)*
- Sửa `COSA_CANONICAL_OWNERSHIP_MAP.md`: xoá mâu thuẫn "Production Canonical" vs ADR-AGENTOS-001. Thêm addendum: *"`agentos/` is an inert parallel/prototype AgentOS implementation. It is not currently wired to any entrypoint (dev or production) — confirmed by trace audit 2026-08-23: no service, dockerfile, or `main.py` runs `agentos/api/app.py`; `build_cosa_agent_plane()` is invoked only from tests. 'Active' in the previous summary referred to active development/canonical design direction, not runtime ownership."*
- Thêm addendum thứ hai cho `legacy/agent_runtime/`: hiện ghi "Frozen migration source — KHÔNG phải canonical owner", audit 2026-08-23 xác nhận thêm route tồn tại và có docker-compose service (gated `--profile legacy`) nhưng KHÔNG serving traffic thật (path mismatch — xem P0.0). Cần làm rõ: "frozen" ở đây nghĩa là "không nhận thêm feature mới", không phải "đang chạy production" lẫn không phải "hoàn toàn chết" — nó là nguồn requirement nghiệp vụ (xem 2.5).
- Gắn đúng trạng thái theo bảng 3-cột "Operational Reality" phía trên: `agentos/*` = Serving No, nguồn design experiment; `legacy/agent_runtime/workforce` = Serving No (path mismatch xác nhận), nguồn Legacy Behavior Inventory.

**Bước 2 — Freeze inert prototype**
- Ngừng refactor sâu vào `runtime.py`, `executor.py`, `planner.py`, `orchestration/adk/orchestrator.py`, `api/chat/routes.py` (native planner, `_pending_runs`, approval replay, `last_context`...).
- Giữ đủ để đọc làm reference, chạy test hiện có, làm baseline đối chiếu hành vi khi cần.
- Xoá thật ở Bước 11, sau khi qua gate Bước 9 và wire xong Bước 10.

**Bước 3-4 — Define VNext contracts + Build clean reusable Agent Core**
- Dựng thẳng `packages/agent_core/` (không biết gì về COSA domain) + `apps/cosa/` (composition), theo cấu trúc target V3 §22-23.
- Contract đầu tiên: `RunRequest`, `RunResult`, `AgentSpec`, `ExecutionKernel` protocol (V3 §4) — **`Principal` map thẳng vào `WorkforceMember`** ngay từ bản đầu, không hoãn.
- `agent_core/coordination/` (delegation/parallel/sequential/debate/supervisor/synthesis) thay thế `orchestration/adk` ngay từ tên gọi đầu tiên — không đợi phase sau mới rename.

**Bước 5 — Integrate OpenAI Agents kernel**
- `OpenAIAgentsKernel` là kernel chính từ đầu, không qua bước trung gian "LegacyNativeKernel production".
- Spike nhanh DeepSeek-qua-Agents-SDK (tool-call compatibility, streaming/usage) làm ngay trong vertical slice 1 (2.4) — không phải một gate riêng chặn cả roadmap.
- Model layer thiết kế theo `ModelPolicy`/routing đúng target (V3 §11), không giữ shape `ModelProvider.generate(...)` cũ nếu nó giới hạn runtime mới.

**Bước 6 — Durable run/checkpoint/event model**
- Schema Postgres mới (`agent_core.runs/run_checkpoints/run_events/run_tool_calls/approvals`) thiết kế đúng target, không ràng buộc tương thích với `RunEvent` cũ.
- Approval flow đúng ngay lần đầu: SDK interruption → persist RunState → approval record (bind `run_id`/`tool_call_id`/`checkpoint_ref`) → resume đúng checkpoint.
- API có thể breaking so với `routes.py` cũ — sửa cả API và phía gọi cùng lúc, không dựng compatibility adapter dài hạn.

**Bước 7 — Governance/capability/connector/workflow layer** *(P0.2 + P0.3 đã audit xong — phạm vi rẻ hơn giả định ban đầu)*
- Port **invariant**, không port file (xem 2.3): tenant scope enforcement, role/permission evaluation, risk classification, approval requirement, audit semantics — viết lại contract mới (`CapabilitySpec`) cho các invariant này.
- **`AutonomyLevel`/`CapabilityRisk`/`ApprovalPolicy` — đã chốt kiến trúc ở 2.6**: 2 dimension trực giao (không gộp permission+risk thành 1 enum), Governance Engine kế thừa công thức 6-dimension `evaluate_access()` đã có (ADR-014), không viết lại. Việc cần làm ở Bước này là **implement theo 2.6**: đổi tên type `PermissionLevel`→`AutonomyLevel`, normalize `R0-R4` (legacy, xem 2.5) và giữ nguyên `ToolRiskLevel` làm `CapabilityRisk`, đảm bảo `execution_mode` được truyền đủ (chỗ cũ `executor.py`/`tool_step.py` thiếu/hardcode), không mang `PermissionClass` (lookup 1D cũ) sang VNext.
- **`WorkflowEngine`**: port gần nguyên kiến trúc `agentos/workflows/` (DAG, `ParallelStep`/`RetryStep`/`CompensatingStep`/`ApprovalGateStep`, YAML loader) như một nhánh riêng song song `ExecutionKernel`, cùng gọi xuống Capability Layer chung (xem sơ đồ P0.3) — không nhét workflow execution vào OpenAI Agents SDK. Thêm 2 gap đã xác nhận: HTTP API + durable checkpoint store (thay in-memory `Workflow.checkpoints`).
- Connector: mở rộng theo `Connector` protocol (Gmail/Calendar/GitHub), tham khảo shape 2-tier transport/tool adapter đã chứng minh đúng ở `agentos/connectors/`.

**Bước 8 — Compose COSA app on top**
- `apps/cosa/agents/` (cofounder.yaml, finance.yaml, sales.yaml,...) là `AgentSpec` đầu tiên dùng thật capability/connector/workflow từ Bước 7.
- Memory/Knowledge/Artifacts/Evals wire vào ở đây: knowledge port gần nguyên logic (pgvector pipeline đã đúng), memory thiết kế semantic/embedding ngay từ đầu (không vá sau), `ArtifactStore` là phần mới hoàn toàn, mỗi `AgentSpec` có eval suite kèm theo ngay khi tạo.
- **Dùng Legacy Behavior Inventory (2.5, đã audit xong P0.1B)** làm requirement input trực tiếp cho `cofounder.yaml` AgentSpec: intent routing 6-bước, stage-aware context, Challenge Mode, streaming delta protocol — đây không còn là "archaeology cần làm" mà là dữ liệu đã có sẵn để thiết kế.

**Bước 9 — Eval + integration + security gates**
- Kernel contract tests + durability tests + security tests (V3 §30) chạy trên VNext trước khi wire.

**Bước 10 — Wire first canonical integration entrypoint** *(đổi tên từ "production entrypoint" — COSA còn dev)*
- Đây là lần **đầu tiên** một entrypoint thật, được cả team công nhận ("mọi dev mới của Agent Core đi qua đây"), trỏ vào `agent_core`-descendant code — và (theo kết quả P0.0) cũng là lần đầu tiên tính năng cofounder-chat thực sự chạy được end-to-end qua Flutter, vì đường cũ chưa bao giờ hoạt động.
- Sửa `cofounder_api_service.dart` gọi đúng entrypoint VNext mới — không cần giữ nguyên path `/cofounder/chat` hay dựng compatibility shim, vì không có behavior cũ nào đang chạy để giữ tương thích.
- Production promotion (nếu có khách hàng thật) là quyết định sản phẩm riêng, sau bước này.

**Bước 11 — Archive/delete inert prototype**
- Sau khi VNext chạy ổn định qua Bước 10: archive/xoá `agentos/core/runtime.py`, `executor.py`, `planner.py`, `orchestration/adk/orchestrator.py`, `api/chat/routes.py` (INERT, xác nhận) **và** `legacy/agent_runtime/workforce` (Serving=No, xác nhận qua P0.0 — không cần đợi "cutover từ traffic đang chạy" vì không có traffic nào cả; chỉ cần đảm bảo Legacy Behavior Inventory (2.5) đã được phản ánh đủ vào VNext trước khi xoá).

### 2.3 Nguyên tắc port: invariant, không phải module

Không hỏi "làm sao migrate `ToolRegistry`?" — hỏi "invariant nào của capability execution đã được chứng minh đúng?" rồi viết lại contract mới cho VNext. Áp dụng cho toàn bộ Bước 7:
- `PolicyEngine` → giữ **công thức 6-dimension** (RBAC ∩ TenantPolicy ∩ PermissionLevel ∩ ToolRisk ∩ ExecutionMode ∩ DataScope), không nhất thiết copy class — công thức này đã được ADR-014 xác nhận đúng, không phải giả thuyết cần kiểm chứng nữa.
- `ToolRegistry`/`ToolSpecV2` → giữ **field đã đúng** (idempotent, write_scope, reversible, timeout, approval_policy, audit_policy) làm invariant cho `CapabilitySpec`, không copy class.
- `SqliteAuditSink` → giữ **audit semantics** (ai làm gì, tenant nào, policy nào, ai approve), đổi storage nếu cần.
- `agentos/knowledge/` và `agentos/workflows/` là 2 ngoại lệ hợp lý để port gần nguyên kiến trúc — đây là 2 pipeline đã chứng minh đúng end-to-end (knowledge: ingest→embed→pgvector retrieve→citation; workflows: DAG→approval gate→checkpoint→compensation) và không coupling với phần sẽ bị thay thế (`executor.py`), không phải chỉ có invariant rời rạc.

### 2.4 Vertical slice đầu tiên để validate rủi ro nền tảng trước khi build rộng

**Slice 1 — read path:**
```text
User message → new API → durable Run → OpenAI Agents kernel
→ one read-only business capability → streamed events → final message → trace/usage
```

**Slice 2 — write + approval path:**
```text
write capability → policy → approval → persist exact RunState
→ process restart simulation → approve → exact resume → idempotent side effect
```

### 2.5 Legacy Behavior Inventory (nguồn requirement, không phải hệ cần cutover) — kết quả P0.1B

**Quyết định đã chốt**: dù P0.0 xác nhận `legacy/agent_runtime/workforce` KHÔNG serving traffic thật, nó vẫn là nguồn thiết kế nghiệp vụ giá trị nhất trong repo (business logic sâu hơn hẳn `agentos/`). VNext **không** đưa code/class của nó vào `packages/agent_core/` theo kiểu wrap-adapter (giống đã loại bỏ `LegacyNativeKernel` cho `agentos/Executor`):
```text
legacy observable behavior → extract thành requirement/test → implement lại bằng capability/context/AgentSpec mới trong VNext
```
KHÔNG: `legacy class → wrap adapter → nhét vào VNext core`.

**Legacy Behavior Inventory** (17 mục, đầy đủ file:line trong báo cáo audit — đây là bản tóm tắt để đưa vào thiết kế `AgentSpec`/`CapabilitySpec` VNext):

| Behavior | Legacy hiện có gì | VNext requirement |
|---|---|---|
| API contract | 6 endpoint (`/chat`, `/pulse`, `/top3`, `/challenge`, `/decisions` GET+POST, `/decisions/{id}/resolve`) | Thiết kế lại thành capability/`AgentSpec` action, không copy Pydantic schema nguyên xi |
| Orchestration | 6-bước intent routing: greeting fast-path (0 query) → FOUNDER_REVIEW (company pulse) → FOUNDER_DECISION/COMMAND (`ChiefOfStaffOrchestrator.orchestrate()`) → domain routing fallback | Đây là invariant nghiệp vụ đáng giữ nhất — map vào `agent_core/coordination/` (delegation/supervisor) |
| Model/provider | Kira AI Gateway mặc định (`deepseek-v4-pro-free`), fallback chain qua env/workspace_secrets, hỗ trợ 6 provider | Thiết kế lại theo `ModelPolicy` (Bước 5), không copy registry cũ |
| Prompts | System prompt + GROUNDING_PROMPT (bắt buộc gọi tool, cấm bịa) + Challenge Mode (phát hiện Solution Bias) + Stage-aware context block | Nội dung prompt là invariant nghiệp vụ thật, nên giữ ý tưởng (grounding, challenge, stage-aware), viết lại theo `AgentSpec.instructions` |
| Tools | 20+ tool theo domain, risk **R0/R2/R3/R4**, max 6 tool round | Port field risk vào `CapabilitySpec` — đây là vocabulary risk thứ 3 (khác `ToolRiskLevel` LOW-CRITICAL của `agentos`, khác `PermissionLevel` L0-L3 của ADR-014) — đã reconcile ở 2.6 |
| Memory | TencentDB-Agent-Memory, scope PERSONAL→SYSTEM, history ≤20 message, promotion candidate→knowledge_object/sop/skill/playbook | So sánh với thiết kế Memory V2 (Bước 8) — scope model đáng tham khảo, không port provider |
| Context | `WorkspaceContext` (company_stage S0-S3, entitlement_plan), `StageResolverService` | Đây là **company context** mà `agentos/context_builder.py` hiện chưa có — invariant quan trọng cần đưa vào `context_sources/` của `apps/cosa/` |
| Auth | JWT (OAuth2PasswordBearer), verify `WorkspaceMember` tồn tại (403 nếu không) | Map vào `Principal`=`WorkforceMember` (đã thống nhất ở 1.2e) — giữ nguyên tắc, không copy code |
| Tenant scoping | Bắt buộc filter `workspace_id` trên mọi query, auto-resolve nếu user chỉ có 1 workspace | Invariant bắt buộc giữ — đúng tinh thần `TenantScope` của V3 §3.2 |
| Permissions | `UnifiedPermission` (principal×resource×action) + `AgentToolPermission` matrix + risk R0-R4 → gate | Input chính cho việc reconcile risk vocabulary ở Bước 7 (xem 2.6) |
| Streaming | SSE qua Postgres LISTEN/NOTIFY, delta theo offset, resync nếu lệch | Thật hơn nhiều so với `agentos` (full-output-1-delta giả) — đáng tham khảo cho Bước 6 (Event Protocol) |
| Side effects | Mission creation có `mission_id` nhưng **không có idempotency-key thật** (tự nhận trong audit) | VNext phải làm đúng hơn — đã là nguyên tắc chuẩn V3 §6.4/§26.5 |
| Tests | 2 file test (`test_phase2_cofounder_engine.py`, `test_phase5_cofounder_e2e.py`) mô tả rõ hành vi mong đợi (greeting=0 query, FOUNDER_REVIEW→pulse thật, challenge mode detect) | Dùng làm acceptance criteria tham khảo cho eval suite của `cofounder.yaml` AgentSpec (Bước 8/9) |

**Vì không có traffic thật cần bảo toàn, không cần API-edge compatibility shim khẩn cấp.** Bước 10 chỉ cần: (1) build `apps/cosa/api/` mới đúng theo yêu cầu rút ra từ inventory trên, (2) sửa `cofounder_api_service.dart` gọi đúng entrypoint mới — không cần giữ path `/cofounder/chat` cũ vì nó chưa từng hoạt động.

Nếu 2 slice này chạy tốt (bao gồm spike DeepSeek-qua-SDK trong Slice 1), phần lớn rủi ro nền tảng (execution kernel, durable resume, idempotency) đã được chứng minh trước khi mở rộng ra toàn bộ Bước 6-8.

### 2.6 V4 Architecture Freeze: risk/autonomy model (thay cho "reconcile 3→1")

Phản biện đúng: không nên ép 3 vocabulary thành 1 enum `CapabilitySpec.risk` duy nhất — `PermissionLevel`/`AutonomyLevel` (agent được tự chủ đến đâu) và risk (action nguy hiểm đến đâu) là hai **dimension trực giao**, gộp chung sẽ mất khả năng phân biệt "cùng risk HIGH nhưng agent L0 vs L3 cần xử lý khác nhau" hoặc "cùng L3 nhưng amount $20 vs $50,000 cần khác nhau". Chốt kiến trúc:

```python
class CapabilityRisk(Enum):      # intrinsic risk của action — canonical đã có sẵn, giữ nguyên
    LOW = "low"; MEDIUM = "medium"; HIGH = "high"; CRITICAL = "critical"

class AutonomyLevel(IntEnum):    # đổi tên từ PermissionLevel — tránh nhầm với RBAC/authorization
    L0 = 0; L1 = 1; L2 = 2; L3 = 3

@dataclass(frozen=True)
class CapabilitySpec:
    ...
    risk: CapabilityRisk
    approval_policy: ApprovalPolicy

@dataclass(frozen=True)
class AgentSpec:
    ...
    autonomy_level: AutonomyLevel
```
Governance Engine (kế thừa `evaluate_access()` 6-dimension đã có, không viết lại từ đầu) kết hợp `AutonomyLevel × CapabilityRisk × context` → `PolicyDecision(outcome, reasons, required_approvals)` — không hard-code một ma trận cố định trong enum, vì cùng 1 capability risk=HIGH có thể ALLOW/REQUIRE_APPROVAL/DENY khác nhau tuỳ argument (ví dụ `finance.invoice.send` $20 nội bộ vs $50,000 khách hàng).

**Normalize 3 nguồn hiện có → 2 dimension chuẩn:**
- `ToolRiskLevel` (agentos, LOW-CRITICAL) → **giữ nguyên làm `CapabilityRisk` canonical**, không cần enum thứ 4.
- `PermissionLevel` L0-L3 (ADR-014) → đổi tên thành `AutonomyLevel` trong VNext (lý do: COSA còn có Role/TenantPermission/ConnectorGrant/CapabilityEligibility — gọi tất cả là "permission" sẽ khó phân biệt trong PolicyEngine). Về mặt giá trị/số lượng level, giữ nguyên L0-L3 của ADR-014, chỉ đổi tên type.
- `R0/R2/R3/R4` (legacy) → default mapping R0→LOW, R2→MEDIUM, R3→HIGH, R4→CRITICAL khi port từng capability từ Legacy Behavior Inventory (2.5) — nhưng đây là **default migration mapping, không phải tương đương toán học**: nếu inventory cho thấy một R2 cụ thể có side effect ngoài hệ thống không thể đảo ngược, capability đó có quyền override lên HIGH khi viết `CapabilitySpec` mới. Sau VNext, `R0-R4` biến mất khỏi runtime vocabulary, chỉ còn trong lịch sử/inventory.
- `ApprovalPolicy` nâng cấp từ string đơn giản thành `NEVER | ALWAYS | CONDITIONAL | POLICY_DRIVEN` với constraint kèm theo (amount threshold, external recipient, destructive operation, sensitive data, new connector destination, irreversible action, production environment) — quyết định cuối vẫn do Governance Engine, không phải LLM (đúng CLAUDE.md §11).

**Canonical vocabulary sau VNext (freeze terminology, dùng nhất quán trong toàn bộ `packages/agent_core/governance/`):**

| Concept | Canonical type |
|---|---|
| User/service authority | `PrincipalAuthorization` (map từ `WorkforceMember`) |
| Agent tự chủ đến đâu | `AutonomyLevel` L0-L3 |
| Action nguy hiểm nội tại đến đâu | `CapabilityRisk` LOW-CRITICAL |
| Capability có được expose không | `CapabilityEligibility` |
| Quyền của connected account | `ConnectorGrant` |
| Có cần người quyết định không | `ApprovalPolicy`/`ApprovalRequirement` |
| Phán quyết cuối cùng | `PolicyDecision` |
| `R0-R4` cũ | **Chỉ còn trong lịch sử — loại khỏi runtime** |

### 2.7 Chứng minh reusability (V3 §39, giữ nguyên)
Chỉ coi `agent_core` tách thành công khi dựng được app thứ 2 (vd. Internal Dev Agent) dùng chung `RunService`/`Kernel`/`Event`/`Memory` mà **không import module COSA company/finance/sales/operations**.

---

## Phần 3 — Rủi ro chính cần theo dõi

1. **Ownership map mâu thuẫn chưa sửa** → phải sửa ở Bước 1 trước khi bất kỳ ai (người hoặc coding agent) dùng nó làm architecture truth (cả 2 addendum: `agentos/` inert, `legacy/agent_runtime` frozen+not-serving).
2. **Không được lặng lẽ quay lại `Executor` cũ làm fallback production** nếu spike SDK (trong Slice 1) gặp trục trặc — quyết định phải tường minh (đổi model adapter hoặc viết native kernel mới cho VNext), vì `Executor` cũ chỉ còn vai trò test/reference theo quyết định ở Bước 2.
3. **Đừng quay lại gộp `AutonomyLevel`/`CapabilityRisk` thành 1 enum** khi implement Bước 7 — kiến trúc 2-dimension trực giao đã chốt ở 2.6, gộp lại sẽ mất khả năng phân biệt autonomy vs intrinsic risk.
4. **Port invariant chứ không port module** (2.3) — rủi ro nếu coding agent thực thi sau này copy nguyên file `agentos/core/policy.py` v.v. thay vì viết lại contract mới, sẽ tái tạo coupling với shape cũ. Áp dụng tương tự cho Legacy Behavior Inventory (2.5): lấy requirement, không copy class từ `legacy/agent_runtime/`.
5. **Comment mới phải bằng tiếng Việt** (CLAUDE.md §19) khi code các bước trên.

---

## Xác nhận / bước tiếp theo

Đây là tài liệu chiến lược (roadmap), chưa động tới code. Khi hướng này được duyệt, bước tiếp theo hợp lý là lập plan chi tiết thực thi cho **Bước 1 (architecture truth) + Vertical Slice 1** (2.4) trong một phiên plan riêng — đây là phần chứng minh rủi ro nền tảng (kernel, durable run, idempotency) sớm nhất, trước khi đầu tư dựng rộng toàn bộ `packages/agent_core/`.
