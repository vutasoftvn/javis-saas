# COSA Architecture Review & Decision Record — 2026-08-22

**Status:** Review & Decision Record — áp dụng cho baseline commit `57c6c2c3d8581dcb4c879b18e26e24137eb5926d`
**Supersedes:** không tài liệu nào (đây là tài liệu bổ sung, không thay thế `COSA_ARCHITECTURE_ADJUSTMENT_ADDENDUM_2026-08-22.md`)
**Liên quan:** `docs/architecture/COSA_ARCHITECTURE_ADJUSTMENT_ADDENDUM_2026-08-22.md`, `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`, `docs/architecture/2026-08-22-cosa-core-extraction-plan.md`

## Mục đích

Tài liệu này ghi lại (a) kết quả đối chiếu từng claim của `COSA_ARCHITECTURE_ADJUSTMENT_ADDENDUM_2026-08-22.md` với code thật, và (b) các quyết định kiến trúc được chốt trong lượt review này cùng lý do — để người đọc sau (kể cả một coding agent khác) không phải suy luận lại từ đầu.

---

## Phần 1 — Đối chiếu claim của addendum với code thật

### 1.1 `agentos/core/`

| Claim trong addendum | Thực tế | Bằng chứng |
|---|---|---|
| Custom `AgentRuntime`/`Executor` tự chạy ReAct/tool loop | ĐÚNG | `agentos/core/runtime.py:26`, `executor.py:52` (MAX_TOOL_ROUNDS=5) |
| `ContextBuilder` nhận `MemoryRetriever`/`SkillRouter`/`SkillInstructionLoader` nhưng `AgentRuntime` không wire | ĐÚNG | `context_builder.py:22-24` (optional param); `runtime.py:43` gọi `ContextBuilder(tool_registry)` — bỏ trống phần còn lại |
| `build_default_runtime()` có thể tạo `ToolRegistry()` rỗng | ĐÚNG | `factory.py:34` |
| Có cả `PermissionClass` và `PermissionLevel` là 2 khái niệm khác nhau | ĐÚNG | `policy.py:8-20` (11 permission class), `policy.py:132-144` (L0-L3) |
| `SqliteTraceSink` ghi raw payload, chưa có redaction | ĐÚNG — rủi ro bảo mật thật, đang tồn tại | `trace_sink.py:47-52`, `json.dumps(event.payload, default=str)` không lọc |
| DeepSeek Harness hiện chỉ là `generate() -> string`, chưa phải execution runtime | ĐÚNG, có chủ đích thiết kế | `deepseek_harness_provider.py:82-96`, comment dòng 24-29 nói rõ tool-calling loop và budget governance bị lược bỏ có chủ đích |
| Không có Google ADK trong `agentos/` | ĐÚNG trong `agentos/` — nhưng cần phân biệt với ADK thật nằm ở `legacy/`, xem Phần 2 mục 3 | `grep -ri adk agentos/` = 0 kết quả |
| `ToolSpec` chỉ có name/description/handler/permission_class | ĐÚNG, thiếu `input_schema`/`risk_level` như đề xuất ToolSpecV2 | `registry.py:8-12` |
| `factory.py` là "production composition root" | ĐÚNG NHƯNG chỉ ở mức sơ khai — wire được model/policy/approval/trace, thiếu memory/skill/knowledge | Không phải "hoàn toàn thiếu", nhưng cũng chưa đủ như mô tả §7 |
| `agentos/runtime/{native,adapters}/` là cấu trúc đang tồn tại | SAI — đây là đề xuất trong addendum §6.5, chưa có thư mục `agentos/runtime/` nào | Chỉ có `agentos/core/adapters/` hiện tại |

### 1.2 `agentos/memory/` và `agentos/knowledge/`

| Claim | Thực tế | Bằng chứng |
|---|---|---|
| `PgVectorMemoryStore` chưa dùng vector similarity thật, chỉ lọc + sort theo `created_at` | ĐÚNG | `pgvector_store.py:51-94` — không có cột embedding, không có operator `<=>`; token-overlap nằm riêng ở `retrieval.py:21-32` (`score_relevance`, comment "Naive term-overlap... placeholder for real embedding-based semantic retrieval") |
| Isolation key hiện tại chỉ dựa `agent_key` | PARTIALLY ĐÚNG — thực ra là compound `workspace_id + agent_key`, không có `company_id`/`principal`/`namespace` như đề xuất §11.5 | `models.py:19-28` (`MemoryItem`), `pgvector_store.py:29,63-68` |
| `agentos/knowledge` có cosine similarity pgvector thật | ĐÚNG | `knowledge/store.py:165` (`1 - (embedding <=> :query_embedding) AS score`), `store.py:168` (`ORDER BY embedding <=> :query_embedding`) |
| Knowledge chưa có migration cho `knowledge.sources`/`knowledge.chunks`, có chủ đích | ĐÚNG | `knowledge/store.py:91-99` — comment tiếng Việt nói rõ đây là quyết định ownership DB chưa chốt (liên quan ADR-012), không phải thiếu sót vô tình; `find ... *migrations*` dưới `agentos/` không ra kết quả |
| Provider adapter pattern (`agentos/memory/providers/{local_sqlite,pgvector,tencent_agent_memory}.py`) đã tồn tại | SAI — đây là đề xuất, chưa có thư mục `providers/` | `ls agentos/memory/` không có `providers/` |
| 5 memory kind (WORKING/EPISODIC/SEMANTIC/PROCEDURAL/ORGANIZATIONAL) | ĐÚNG | `models.py:11-16` |

### 1.3 `services/realtime_agent` và cấu trúc `services/`

| Claim | Thực tế | Bằng chứng |
|---|---|---|
| `voice_tools.py` chèn `sys.path` vào `backend` và gọi `SessionLocal()` trực tiếp, import `founder_os.strategy.tools` | ĐÚNG | `voice_tools.py:11` (`sys.path.insert`), `:14-20` (imports), lặp lại `SessionLocal()` dòng 54-575 |
| 7 subfolder `services/` (control-plane, identity, operations, commercial, finance-legal, shared, realtime_agent) | ĐÚNG | `ls services/` |
| `services/operations/strategy/` (startup methodology bounded context) đã tồn tại | SAI — chưa tồn tại, đúng là đề xuất mới | `operations/` hiện chỉ có `handlers/ models/ migrations/ services/` |
| `legacy/` có `founder_os` với strategy/next-best-action/gate logic | ĐÚNG | `legacy/domains/founder_os/strategy/` có `project_orchestration_service.py`, `next_best_action_service.py`, `portfolio_service.py`, `cycle_governance_service.py` |
| `syncFromPlatformService()` tồn tại, làm anti-corruption layer Company↔Workspace | ĐÚNG | `services/identity/services/sync.service.ts:21` |
| Schema `cosa.users/companies/company_roles` và `core.users/workspaces/workspace_members/organizations/workforce_members` | ĐÚNG | `services/shared/db/schema/{control-plane,identity}.ts` |

Lưu ý quan trọng: `voice_tools.py` trỏ `sys.path` vào một `backend/` **không còn tồn tại ở top-level** — runtime này nhiều khả năng đang broken hoặc trỏ nhầm; cần verify riêng khi vào Phase 4 (Realtime Decoupling) của addendum, không thuộc phạm vi doc-only của review này.

---

## Phần 2 — Sáu phát hiện kiến trúc quan trọng

### 1. `backend/` không tồn tại top-level

Xác nhận bằng `ls`: chỉ còn `agentos/`, `services/`, `legacy/backend/` (không có `backend/` đứng riêng). Code Python monolith cũ đã bị tách vào `legacy/{backend,agent_runtime,platform,business,domains,entrypoints}` từ commit `5c5bc85`. Đây là **triệu chứng**, không phải nguyên nhân gốc của vấn đề ở mục 2.

### 2. Nguyên nhân gốc để supersede `2026-08-22-cosa-core-extraction-plan.md`: trùng lặp Control Plane, không chỉ path chết

`docs/architecture/2026-08-22-cosa-core-extraction-plan.md` — status gốc "Đã duyệt — bắt đầu triển khai Đợt 1", cùng ngày 2026-08-22 — đề xuất tạo `backend/cosa_core/` gồm cả agent runtime (ADK, DeepSeek Harness, GovernanceKernel) lẫn `auth`/`control_plane`/`identity`/multi-tenancy/`WorkforceMember`.

Vấn đề thật không phải chỉ là path `backend/` đã chết — mà là **bounded-context decomposition của plan đó đã lỗi thời** so với thực tế repo hiện nay. `services/control-plane` + `services/identity` (TypeScript/Encore) đã là tenant authority thật:

```text
services/control-plane   (cosa.users, cosa.companies, cosa.company_roles)
services/identity        (core.users, core.workspaces, core.workspace_members, core.organizations, core.workforce_members)
```

Nếu `cosa_core` được triển khai đúng scope đã ghi (đưa `auth`, `control_plane`, `identity`, multi-tenancy, `WorkforceMember` vào Python), COSA sẽ có:

```text
services/control-plane   <-- TypeScript, tenant authority thật
services/identity        <-- TypeScript
        vs
cosa_core/control_plane  <-- Python, tenant authority thứ hai
cosa_core/identity       <-- Python
cosa_core/auth           <-- Python
```

Đây là duplication nguy hiểm hơn nhiều so với trùng lặp agent runtime, vì ảnh hưởng trực tiếp tenant authority, authentication, membership, roles, authorization, company/workspace mapping, database ownership — đúng loại lỗi mà CLAUDE.md §14 đã ghi nhận lịch sử ("4 duplicate Agent/AgentDefinition/AgentProfile/WorkforceMember models phát hiện 2026-08-20") như một bài học cụ thể cần tránh lặp lại, lần này ở tầng identity/tenant.

**Thứ tự ưu tiên lý do supersede:**
1. **(Chính)** Trùng lặp Control Plane — `cosa_core` sẽ tạo tenant authority thứ hai.
2. **(Phụ)** Giả định sai về codebase — plan mở đầu bằng "javis-saas hiện là một backend Python monolith" và đề xuất tách từ `backend/`, nhưng path đó không còn tồn tại; toàn bộ đã tách vào `legacy/*` và bị frozen theo ADR-012 (xem mục 3).

### 3. ADK: có code thật, nhưng không nên gọi là "production-tested" hay "current production"

Một implementation Google ADK orchestration thật tồn tại tại `legacy/agent_runtime/workforce/agents/orchestration/adk/`, dùng `from google.adk.workflow...` thật (`google-adk==2.7.0`), dựng graph thật với planning, specialist delegation, governance gate, synthesis, quality gate, approval và execution — theo mô tả trong `2026-08-22-cosa-core-extraction-plan.md`.

Tuy nhiên, `COSA_CANONICAL_OWNERSHIP_MAP.md` (cập nhật ADR-012, cùng ngày 2026-08-22) xác nhận: `legacy/backend`/`legacy/agent_runtime` đang **frozen-in-place, biết là broken** — restructure commit `5c5bc85` tách thành 6 thư mục `legacy/*` mà không cập nhật Docker build, nên known-broken hôm nay; `brain-api`/`agent-worker` bị gate sau `docker compose --profile legacy`, không chạy mặc định; quyết định là **không resurrect**.

| Khẳng định | Có bằng chứng? |
|---|---|
| Code ADK thật tồn tại, dùng `google.adk.workflow` thật | Có |
| Dựng graph thật: planning/delegation/governance-gate/synthesis/quality-gate/approval | Có |
| Từng có kiểm thử/lịch sử kiến trúc | Có |
| Stack `legacy/` hiện build/chạy tốt trong production hôm nay | **Không** — biết là broken, gated `--profile legacy` |
| Có traffic production hiện tại đi qua ADK này | Chưa thấy bằng chứng |
| Nên gọi là "production-tested" ở thì hiện tại | **Không nên** |

**Diễn đạt đúng:** ADK là *real legacy implementation, migration reference đã được kiểm thử trong quá khứ* — không phải production runtime hiện hành.

### 4. ADK migration nên là "port qua ports", không phải "move nguyên khối"

`legacy/agent_runtime/workforce/agents/orchestration/adk/workflow.py` còn coupling với `workforce.agents.orchestration.specialist_registry` và `founder_os.outcomes.models`. Hướng di chuyển đúng:

```text
legacy ADK behavior + tests
        │ trích xuất invariant (mission lifecycle, R0-R4 gate semantics,
        │ approval semantics, pause/resume, delegation semantics,
        │ test chống ADK bypass GovernanceKernel)
        ▼
AgentOS Orchestration Port (interface trong agentos/orchestration/)
        │
        └── GoogleADKOrchestrator adapter (implementation mới)
```

Không mang sang: legacy import path, legacy persistence model, FastAPI assumption, `founder_os` coupling. Test chống ADK bypass GovernanceKernel là ràng buộc bắt buộc phải giữ — chính `2026-08-22-cosa-core-extraction-plan.md` cũng nhấn mạnh điều này (lý do lần tích hợp ADK đầu tiên thất bại).

### 5. Nguy cơ 2 execution loop cạnh tranh ngay trong Agent Plane — đã CHỐT hướng trong addendum, còn thiếu implementation

**Sửa (sau phản biện của người dùng, đã sửa nhầm lẫn ban đầu):** hướng này KHÔNG phải "quyết định chưa chốt" — addendum §6.4/§6.5 và ADR-B (§22) đã chốt rõ: DeepSeek Harness = production execution runtime, native `agentos/core/executor.py` = fallback/test adapter. Cái còn thiếu chỉ là **implementation** — hiện `deepseek_harness_provider.py` mới là `generate()`-only adapter, chưa phải execution runtime thật đúng nghĩa addendum §6.4 yêu cầu (nhận tool request, đi qua COSA Policy/Approval, gọi Encore API — không execute business write trực tiếp). Đây chính là Phase 3 (Runtime Convergence, addendum §19) của migration plan. Hướng đích:

```text
agentos/
├── orchestration/adk/        (Google ADK — chọn/giao việc, chưa làm trong Phase 3 lần này)
└── runtime/
    ├── deepseek_harness/     (production specialist execution)
    └── native/               (fallback/test only)
```

### 6. Startup Methodology thuộc `services/operations/strategy`, không migrate vào `agentos/`

Addendum §16 đã đề xuất đúng hướng: domain knowledge (Stage → Assumption → Experiment → Evidence → Gate → Decision → Next Action) là business truth, thuộc Business Plane. AgentOS chỉ orchestrate các domain primitive này qua Tool Gateway, không sở hữu chúng. Không có thay đổi hành động nào thêm ngoài những gì addendum §16 đã ghi.

---

## Quyết định đã chốt trong lượt review này

1. **Supersede** `docs/architecture/2026-08-22-cosa-core-extraction-plan.md` — lý do chính: duplication Control Plane (mục 2); lý do phụ: path `backend/` không tồn tại.
2. **Diễn đạt ADK** trong mọi tài liệu canonical từ nay: "real legacy implementation / migration reference", không dùng "production-tested"/"current production" (mục 3).
3. **Redesign `COSA_CANONICAL_OWNERSHIP_MAP.md`** thành mô hình 2 cột — Target canonical owner (luôn phải trỏ path còn tồn tại) và Operational status (Active/Pilot/Planned/Frozen) — thay vì giữ "canonical owner" trỏ path chết kèm chú thích tự mâu thuẫn. Nội dung cũ (dòng mô tả `backend/workforce/agents/...`) chuyển xuống mục "Historical ownership", không còn là canonical hiện hành.
4. **Open ADR backlog** — các quyết định thật sự chưa chốt, không tự quyết trong lượt review này: memory provider contract (`MemoryService` interface), knowledge DB ownership, ADR A-G đề xuất tại addendum §22 chưa thành file ADR riêng. (DSH-vs-native-executor KHÔNG thuộc danh sách này nữa — xem sửa ở mục 5: hướng đã chốt trong addendum, chỉ còn implementation.)

## Việc không làm trong lượt review này

- Không sửa code (`context_builder.py`, `trace_sink.py`, `voice_tools.py`...).
- Không tự chốt Open ADR backlog — chỉ liệt kê.
- Không viết CI/automation cho architecture consistency checklist — chạy tay một lần, kết quả ghi trong PR/commit liên quan.
- Không đổi `agentos/knowledge` sang có migration thật (quyết định ownership DB cần người quyết).
