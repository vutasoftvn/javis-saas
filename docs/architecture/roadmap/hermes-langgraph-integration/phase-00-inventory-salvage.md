# Phase 0 — Architecture Freeze + Asset Inventory & Salvage Classification

> Nguồn gốc: `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` §"Phase 0" (Step 1–2). Bổ sung Hermes/LangGraph theo `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3.

## Mục tiêu

Chốt bảng phân loại salvage cho từng subsystem của `agentos/` (PROMOTE CODE / PROMOTE-after-audit / PROMOTE semantics / SUPERSEDE / RETIRE), đóng băng kiến trúc `agentos/` (không phải code freeze tuyệt đối), và — bổ sung mới — audit toàn bộ prior art context-assembly trong `legacy/agent_runtime/` trước khi bất kỳ phase sau nào thiết kế `context/` mới.

## Định nghĩa freeze cho giai đoạn này

Cấm từ thời điểm này trong `agentos/`:
- thêm execution framework mới;
- thêm composition root mới hoặc mở rộng `build_cosa_agent_plane()` thành kiến trúc cuối;
- tiếp tục làm `AgentRuntime`/`Executor`/`ADK orchestrator` "production-ready" hơn;
- thêm durable architecture mới chỉ tồn tại ở `agentos` (không có kế hoạch promote).

Vẫn cho phép: characterization test, extraction adapter, invariant-proof, bugfix cần thiết để xác định chính xác thứ sẽ promote.

## Bảng phân loại salvage theo subsystem (chốt trước khi sang Phase 1)

| Subsystem | Disposition | Việc cụ thể |
|---|---|---|
| `AgentRuntime` / `Executor` / `Planner` | **SUPERSEDE implementation** | Runtime ownership chuyển hẳn sang OpenAI Agents SDK kernel (Phase 3). Không port code, chỉ đọc để hiểu hành vi hiện có khi viết characterization test |
| `build_cosa_agent_plane()` | **PROMOTE composition knowledge, REWRITE implementation** | Dependency graph (model provider + ToolRegistry + MemoryRetriever + KnowledgeRetriever + skills + profiles + PolicyEngine + ApprovalService + trace/audit) làm checklist cho `apps/cosa/composition/`; code thật viết lại |
| `agentos/orchestration/adk/*` | **PROMOTE patterns/invariants only, KHÔNG port framework code** | Semantics đáng giữ: delegate / parallel / supervisor / risk classification / approval gate / quality gate / synthesis → đưa vào `packages/agent_core/coordination/` như primitive framework-neutral. Không mang theo import private API (`google.adk.workflow._function_node.FunctionNode`) |
| `agentos/workflows/*` (schema, loader, engine, definition_registry, tool_step) | **PROMOTE CODE mạnh** | DAG, approval pause, compensation, YAML loader, retry, version pinning là tài sản thật — migrate trực tiếp vào `packages/agent_core/workflows/`, giữ nguyên logic, chỉ thay storage/durability (Phase 2) |
| Governance/policy semantics (`agentos/core/policy.py::evaluate_access`, temporal accumulator) | **PROMOTE mạnh** | Đã bắt đầu đúng hướng ở `packages/agent_core/governance/` — tiếp tục theo Phase 1 |
| Memory contracts/providers (`agentos/memory/*`) | **PROMOTE-after-audit** | Audit coupling trước khi copy sang `packages/agent_core/memory/` (Phase 9) |
| Knowledge ingest/retrieval/chunking (pgvector) | **PROMOTE-after-audit** | Tương tự memory — audit rồi promote ở Phase 9 |
| Evals/regression harness | **PROMOTE** | Không viết lại từ zero — dùng làm baseline cho Phase 9 eval suite |
| Agent profiles/skills | **PROMOTE semantics + definitions** | Framework-neutral hơn runtime, giữ định nghĩa, viết lại phần load/bind vào kernel mới |
| `/agent/*` HTTP schema + SSE event vocabulary | **PROMOTE thành contract candidate** | Flutter đã consume trực tiếp — dùng làm input khi thiết kế `apps/cosa/api/` (Phase 7–8) |
| FastAPI chat route implementation (`agentos/api/chat/routes.py`) | **REWRITE** | `_pending_runs: dict` giữ resume state trong RAM; `db: Session` truyền thẳng vào background task; `cancel_run()` không thật sự cancel kernel. Giữ contract, bỏ toàn bộ lifecycle implementation |
| In-memory approval/run/event state | **RETIRE** | Trái thẳng Step 6 durable model — không mang theo dưới bất kỳ hình thức nào |
| Google ADK làm architecture root | **SUPERSEDE** | Coordination primitives cứu được; ownership/ADK-as-root thì không |
| **(MỚI) `legacy/agent_runtime/workforce/agents/context/*`** | **PROMOTE invariants/concepts only, KHÔNG port code** | Xem mục "Audit context prior art" bên dưới — 4 file, không production-grade nhưng có invariant đáng giữ |

## Việc cụ thể (gốc)

1. Với mỗi dòng PROMOTE CODE / PROMOTE-after-audit ở trên: viết 1 mục trong `docs/architecture/agentos_salvage_inventory.md` liệt kê module nguồn → đích dự kiến trong `packages/agent_core/` → điều kiện audit (nếu có) → test hiện có nào sẽ trở thành characterization harness.
2. Cập nhật `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` để phản ánh đúng bảng phân loại — không còn ghi "agentos hoàn toàn inert/disposable".
3. Xóa/archive các file supplement đã bị Master doc hợp nhất — xác nhận với người dùng trước khi commit xóa (hành động phá hủy).
4. Không sửa `agentos/core/runtime.py`, `executor.py`, ADK orchestrator ngoài bugfix/characterization-test tối thiểu.

## Bổ sung Hermes/LangGraph — Audit context prior art (BẮT BUỘC, mới)

**Lý do:** Supplement Hermes/LangGraph §8 đề xuất `packages/agent_core/context/` như "ADD" (greenfield). Verify code thật cho thấy `legacy/agent_runtime/workforce/agents/context/` đã có 4 file với prior art đáng kể. Viết context module mới mà không audit trước vi phạm CLAUDE.md rule 4 ("không nhân bản kiến trúc — tìm trong repo trước khi thêm mới").

**Việc cụ thể:**

1. Audit đầy đủ 4 file, viết `docs/architecture/CONTEXT_ASSEMBLER_AUDIT.md`:
   - `assembler.py` (`CofounderContextAssembler`): intent-based scoping (5 loại intent: greeting → `{}`; general chat → workspace + founder_profile; founder strategic intent → workspace + project + stage + founder_profile + 12-week cycle + pending decisions + business signals + weekly plan + blockers + approvals + evidence + outcomes), graceful degradation qua từng field (`except Exception: return {}`), reuse `SPECIALIST_REGISTRY.fetch_snapshot()` thay vì query lại business signals lần hai. **Coupling cần lưu ý:** query trực tiếp SQLAlchemy business models (`Workspace`, `Project`, `TwelveWeekCycle`, `WeeklyPlan`, `FounderDecision`, `ApprovalRequest`, `EvidenceItem`, `Outcome`) — nếu port nguyên vào `packages/agent_core/` sẽ vi phạm boundary "agent_core không import business domain".
   - `builder.py`: `ContextSection` (`data`/`source`/`fetched_at`/`status`/`error`) — đánh giá governance **trước khi fetch** data, không chỉ audit sau đó. Đây là invariant provenance-aware đáng giữ.
   - `compiler.py` (`ProgressiveContextCompiler`, `ContextBudget`): concept L0-L5 (Session/Company/Project/Domain/Skill/Artifacts), gần với Hermes progressive disclosure. **Verify thực tế (KHÔNG production-ready):** L0-L4 compile được, L5 (Artifacts) chưa thực sự implement dù có placeholder trong `to_system_prompt_addition()`; token estimate chỉ là `len(text)//4`; khi vượt `max_total_tokens` chỉ đánh dấu `is_trimmed=True`, không redistribute token thật.
   - `scope_resolver.py` (`ScopeResolver`): `ScopeSet` với `allowed_namespaces`, `token_budget`, `needs_heavy_priming`. Invariant "No Job → No Heavy Priming" chỉ đúng có điều kiện (`not gate_decision.needs_job AND not gate_decision.needs_project`), không phải absolute — ghi rõ điều kiện thật khi salvage.
2. Kết luận audit phải trả lời rõ: invariant nào giữ (governance-before-fetch, progressive-disclosure concept, ScopeSet/token_budget shape) vs phần nào KHÔNG mang theo (L5 rỗng, token estimate thô, rebalance giả, direct SQLAlchemy business import).
3. Audit delegation pattern trong `agentos/orchestration/` (nếu tồn tại) đối chiếu Hermes §16 (authority attenuation, context isolation) — ghi vào cùng file inventory salvage, không tạo file riêng.

## Bổ sung Hermes/LangGraph — LangGraph (research-only, KHÔNG code)

- Chỉ đọc source theo pin đã có trong supplement gốc §53 (`langchain-ai/langgraph@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`, `langgraph==1.2.11`), tập trung `libs/langgraph/langgraph/graph/state.py`, `pregel/`, `func/`, `libs/checkpoint*`.
- **Không thêm dependency, không code** trong Phase 0 — spike kỹ thuật thật sự chỉ bắt đầu ở Phase 3, sau khi Phase 1 đã harden baseline WorkflowEngine (lý do: không có baseline để so sánh nếu spike chạy song song với việc harden).

## Definition of Done — Phase 0

**Gốc:**
- `docs/architecture/agentos_salvage_inventory.md` tồn tại, mỗi dòng PROMOTE trong bảng có ít nhất 1 mục tương ứng.
- `COSA_CANONICAL_OWNERSHIP_MAP.md` không còn câu nào mô tả agentos là "inert, không cần preserve behavior" mà không có qualifier đúng.
- Không có commit mới nào trong `agentos/` thêm feature (chỉ bugfix/characterization test) kể từ mốc Phase 0.
- Quyết định về các file supplement `D` trong `git status` đã được người dùng xác nhận rõ ràng.

**Bổ sung:**
- `docs/architecture/CONTEXT_ASSEMBLER_AUDIT.md` tồn tại, liệt kê rõ invariant giữ/bỏ từ 4 file `legacy/agent_runtime/workforce/agents/context/`.
- Dòng "PROMOTE invariants/concepts only" cho context prior art đã được thêm vào bảng salvage trong `agentos_salvage_inventory.md`.

## Rủi ro/lưu ý

- Phase thuần tài liệu + inventory, không đổi hành vi runtime — rủi ro thấp, nhưng là gate bắt buộc: Phase 1 không nên bắt đầu migrate code khi bảng salvage chưa chốt.
- Audit context prior art dễ bị làm hời hợt (chỉ đọc `assembler.py`, bỏ qua 3 file kia) — đây chính xác là lỗi đã phát hiện ở vòng research đầu tiên của Integration Plan; đảm bảo audit cả 4 file, không chỉ file có tên gợi nhớ nhất.
