# COSA JaredRhod Integration & OPC Admin RBAC — Implementation Plan

> **Source spec:** `COSA_JaredRhod_Integration_OPC_Admin_RBAC.md` (repo root, 34 mục).
> **Trạng thái:** Roadmap triển khai P0→P6 + mục 15A, dựa trên audit trực tiếp code
> (`backend/app/agents/`, `backend/app/modules/chat/`, `frontend/lib/modules/hologram_hub/`),
> không suy đoán từ tên module hay commit message.
> **Audit date:** 2026-08-16.

---

## Context

Spec `COSA_JaredRhod_Integration_OPC_Admin_RBAC.md` (34 mục) đề xuất tích hợp các pattern kiến trúc từ Jared Rhod (Conversation Gate, Intent Router, Priming Engine, Job/Skill Runtime, Action Runtime, Observe/Verify/Learn, Voice hybrid, Hologram Hub Visualizer) và một tầng OPC Admin RBAC governance cho "Protected System Resources" (Build Spec, Prompt, Skill, Policy...).

Động lực gốc: bug hành vi thật đang tồn tại — chat "Chào" có thể khiến COSA tự động gọi project lookup/tool dù user chưa yêu cầu, vì hiện tại **toàn bộ tool list công ty luôn được đưa cho LLM bất kể nội dung câu hỏi**, và kết quả phân loại intent (`WorkIntentClassifier`) bị tính rồi vứt bỏ cho mọi trường hợp trừ `CYCLE_CHANGE`. Đã xác nhận chính xác trong `chat_execution_service.py:308-310` và `chat_execution_service.py:533-535`.

Sau khi khảo sát toàn bộ `backend/app/agents/` và `frontend/lib/modules/hologram_hub/` (3 vòng research + 1 vòng thiết kế, tất cả đọc trực tiếp code, không suy đoán), phát hiện quan trọng nhất là: **phần lớn kiến trúc mà spec đề xuất "xây mới" (Agent registry, Tool risk/permission gating, Policy/Risk Engine, Approval Engine, Job/Execution runtime, LiveKit voice hybrid, Hologram Hub UI) đã tồn tại và khá trưởng thành.** Chỉ có 2 khoảng trống thật:

1. **P0 — Conversation Gate / Intent Router chưa nối vào chat path chính** → đây chính là bug "Chào".
2. **Mục 15A — RBAC/Protected Resource governance chưa có `authorize()` tập trung** → prompt/spec hiện sửa được bởi bất kỳ workspace member nào, không versioning, không audit, không reset-to-default.

Plan này bao quát **toàn bộ roadmap P0→P6 + 15A** (mục 26 của spec), ở mức chi tiết khác nhau — P0 và 15A chi tiết đầy đủ (2 khoảng trống thật), các phần còn lại ở mức roadmap ghi rõ "extend hạ tầng có sẵn" thay vì thiết kế lại.

**Nguyên tắc chỉ đạo xuyên suốt mọi phase:**
- KHÔNG viết lại `PolicyEngine`, `ApprovalService`, `tool_registry`, `CapabilityGateway`, `ExecutionJob`, `RealtimeTransportResolver`, `EventBroker` — mọi phase chỉ **nối vào**.
- Thay đổi hành vi router/gate PHẢI gate sau feature flag mới (`backend/app/core/feature_flags.py`), rollback tức thời được.
- Bảng mới PHẢI dùng `SnowflakeIDMixin` (`backend/app/db/snowflake_model.py`), đăng ký ở `backend/app/db/base.py` — theo đúng convention `agents/*` mới, không theo convention cũ tự khai `id` (`strategy/models.py`).
- Tenancy: enforce qua `get_current_workspace_member` (`backend/app/core/auth.py:33-47`) như hiện tại, không trust client-supplied `workspace_id`/`brain_id`.

---

## P0 — Conversation Gate / Intent Router / Tool Permission Gate (chi tiết đầy đủ, ưu tiên cao nhất)

### Root cause đã xác nhận

`backend/app/modules/chat/chat_execution_service.py`:
- `_execute_turn` (231-449) gọi `_dispatch_cycle_change_command` (284-287, định nghĩa 519-568) trước LLM, nhưng hàm này chỉ hành động khi `WorkIntentClassifier.classify()` (`company_runtime/intent_classifier.py:74-144`) trả về `CYCLE_CHANGE` (line 533-535 `if classification["intent"] != "CYCLE_CHANGE": return False`). **5/6 intent** (`CHAT`, `QUICK_TASK`, `COMPANY_WORK`, `STRATEGIC`, `APPROVAL`) bị tính rồi bỏ.
- `_tools_for` (199-217) trả **toàn bộ** `company_tools.tool_specs()` không lọc theo intent/nội dung — gọi tại dòng 308-310, không có tham số nào giới hạn theo ngữ cảnh.
- `GROUNDING_PROMPT` (37-54) còn chủ động khuyến khích gọi tool khi thấy tên dự án, không có hướng dẫn "bỏ qua tool cho lời chào/hỏi chung".

### Thiết kế

**Không thay thế `WorkIntentClassifier`** (rẻ, regex-based, đã đúng vai trò phân loại thô). Thêm lớp **Conversation Gate** mới ngay sau nó.

File mới: `backend/app/modules/chat/conversation_gate.py`

```python
class GateIntent(str, Enum):
    SOCIAL_CHAT = "social_chat"
    GENERAL_QUESTION = "general_question"
    PROJECT_DISCOVERY = "project_discovery"
    PROJECT_QUERY = "project_query"
    PROJECT_ANALYSIS = "project_analysis"
    DOMAIN_JOB = "domain_job"      # map từ CYCLE_CHANGE/STRATEGIC/COMPANY_WORK/APPROVAL hiện có
    TOOL_ACTION = "tool_action"    # map từ QUICK_TASK hiện có
    AMBIGUOUS = "ambiguous"

@dataclass(frozen=True)
class GateDecision:
    intent: GateIntent
    confidence: float
    needs_project: bool
    needs_tools: bool
    needs_job: bool
    allowed_namespaces: frozenset[str]   # rỗng = NO_TOOL hợp lệ
    route: Literal["orchestrator", "chat_llm"]

def resolve(text: str) -> GateDecision:
    base = WorkIntentClassifier.classify(text)   # tái dùng nguyên, không viết lại
    if base["intent"] in {"CYCLE_CHANGE", "STRATEGIC", "COMPANY_WORK", "APPROVAL"}:
        return GateDecision(intent=GateIntent.DOMAIN_JOB, route="orchestrator", ...)
    if base["intent"] == "QUICK_TASK":
        return GateDecision(intent=GateIntent.TOOL_ACTION, route="chat_llm",
                             allowed_namespaces=frozenset({"tasks", "runtime"}), ...)
    return _classify_chat_subintent(text)   # base["intent"] == "CHAT" → phân loại tinh hơn
```

`_classify_chat_subintent` dùng cùng kỹ thuật keyword-set như `WorkIntentClassifier` (không cần thêm AI call):
- Ngắn + khớp social-greeting pattern ("chào", "hi", "hello", "bạn là ai", "cảm ơn"...) → `SOCIAL_CHAT`, `allowed_namespaces=frozenset()`.
- Có "project"/"dự án" + hỏi liệt kê ("nào", "những", "danh sách") → `PROJECT_DISCOVERY`, `allowed_namespaces={"strategy"}`.
- Có tên/id cụ thể + "kiểm tra" → `PROJECT_QUERY`, `allowed_namespaces={"strategy", "tasks"}`.
- Có domain keyword (sales/marketing/finance/legal) + "phân tích" → `PROJECT_ANALYSIS`, `allowed_namespaces={"strategy", <domain namespace>}`.
- Không khớp gì rõ → `GENERAL_QUESTION`, `allowed_namespaces=frozenset()`.
- Không xác định được → `AMBIGUOUS` — xử lý an toàn như `GENERAL_QUESTION` (không cấp tool, để model tự hỏi lại) chứ không mặc định cấp quyền.

Capability mapping dùng đúng `namespace` đã có trong `tool_registry` (`strategy`, `tasks`, `sales`, `finance`, `runtime`, `company`, `tech`, `approval`) — 1 dict hằng số trong `conversation_gate.py`, **không cần bảng DB mới ở P0**.

### Điểm nối vào `chat_execution_service.py`

Generalize `_dispatch_cycle_change_command` để gọi `conversation_gate.resolve()` thay vì gọi thẳng `WorkIntentClassifier.classify()`; giữ nguyên logic dispatch qua `WorkOrchestratorService` khi `route == "orchestrator"` (không đổi hành vi CYCLE_CHANGE hiện có).

Thay đổi hành vi thật ở dòng 308-310:

```python
# Trước:
tools = _tools_for(db, brain.workspace_id, provider_name, model_name, session.user_id)

# Sau:
gate_decision = conversation_gate.resolve(user_message.content)
tools = _tools_for(
    db, brain.workspace_id, provider_name, model_name, session.user_id,
    allowed_namespaces=gate_decision.allowed_namespaces,
)
```

`_tools_for` thêm filter cuối theo `namespace` khi `allowed_namespaces` được truyền (giữ tương thích ngược cho call site khác nếu có).

`NO_TOOL` là route hợp lệ (mục 5 spec): khi `allowed_namespaces == frozenset()` → `tools=[]` → dòng 318 hiện tại đã tự chọn `NO_TOOLS_PROMPT` khi `tools` rỗng — **hành vi này đã đúng sẵn**, chỉ cần đảm bảo `tools` thực sự rỗng cho `SOCIAL_CHAT`/`GENERAL_QUESTION`. Review lại nội dung `NO_TOOLS_PROMPT` — hiện viết cho case "model không hỗ trợ tool", có thể cần câu chữ khác cho case "gate quyết định không cần tool" để tránh model tự xin lỗi không cần thiết.

Cũng sửa cùng lúc: `_retrieve_context` (dòng 294) hiện chạy cho MỌI non-one-shot message không điều kiện — vi phạm nhẹ "No Job → No Heavy Priming" (mục 7.2). Chỉ gọi khi `gate_decision.needs_project` (hoặc tương đương) để tiết kiệm 1 embedding call cho "chào".

Feature flag mới: `FLAG_CONVERSATION_GATE_V13_2` trong `backend/app/core/feature_flags.py`.

### Regression tests (mục 24 spec)

Thêm `backend/app/tests/chat/test_conversation_gate.py` (unit test thuần cho `conversation_gate.resolve()`, không cần DB/router) + 2-3 test tích hợp trong `test_chat_execution_service.py` (đã có `_ScriptedRouter`/`_FakeRouter` fixtures) để khẳng định wiring đúng:

| Input | Assert |
|---|---|
| "chào" / "hello" / "bạn là ai?" | `tools == []`, không request nào tới `company_tools.execute_tool` |
| "funnel marketing là gì?" | `tools == []` (GENERAL_QUESTION) |
| "tôi đang có những project nào?" | `tools` chỉ chứa namespace `strategy` |
| "kiểm tra project mID" | `tools` chứa `strategy`+`tasks` |
| "phân tích sales mID" | `tools` chứa `sales`, không chứa tool write/action nào |

### Effort & rủi ro
**Vừa** — 1 file mới (~150-200 dòng), sửa 3 điểm trong `chat_execution_service.py`, ~8-10 test case. Rủi ro chính: false-negative của regex chặn nhầm câu hỏi cần tool → giảm bằng feature flag rollback + `AMBIGUOUS` an toàn (không cấp tool thay vì cấp rộng).

---

## 15A — OPC Admin Governance / Protected Resource RBAC (chi tiết đầy đủ, khoảng trống thật thứ 2)

### Gap đã xác nhận

Hoàn toàn không có `authorize(actor, action, resource)` tập trung. Role check rải rác, vocab không nhất quán ở ≥6 nơi: `vault_repo.py:8-16` (`ROLE_LEVELS`/`check_permission`, dùng lại ở `strategy/routers/template_router.py:43,53`), `platform/router.py:101`, `platform/domain_router.py:21`, `vault/brains_router.py:65,94,122`, `integrations/plugins_router.py:16`, `finance/routers/periods_router.py:48` — mỗi chỗ so sánh role trực tiếp, không qua hàm dùng chung.

Ví dụ gap rõ nhất, đã xác nhận đọc trực tiếp: `PATCH /agents/{agent_id}` (`backend/app/modules/tasks/agents_router.py:91-119`) — **không có bất kỳ permission check nào**, bất kỳ `WorkspaceMember` nào cũng sửa được `Agent.system_prompt` (dòng 112-113: `if agent_in.system_prompt is not None: agent.system_prompt = agent_in.system_prompt`), không versioning, không audit, không reset-to-default. Đây chính xác là 1 "Protected System Resource" theo mục 15A.1 đang bị bỏ ngỏ.

Điểm mấu chốt để không phải xây từ đầu: `WorkspaceTemplate` + `WorkspaceTemplateVersion` (`backend/app/modules/strategy/models.py:345-368`) đã là 1 implementation gần đúng pattern Default+Override — có `version_no`/`active_version_no`, `source_seed_key`, `status ACTIVE/ARCHIVED`, admin-gated reset (`template_router.py:39-53`). **Tổng quát hoá pattern này** thay vì phát minh lại.

### Thiết kế

**1. `authorize()` tập trung** — `backend/app/core/authz.py`:

```python
PERMISSION_LEVELS = {"owner": 4, "admin": 3, "editor": 2, "member": 2, "viewer": 1}
# Kế thừa trực tiếp ROLE_LEVELS của vault_repo.py — không tạo vocab role thứ 2.

PROTECTED_ACTIONS = {
    "spec.read", "spec.update", "spec.approve", "spec.reset",
    "prompt.read", "prompt.update", "prompt.reset",
    "skill.read", "skill.update", "skill.reset",
    "policy.read", "policy.update", "policy.reset",
    "agent.configure", "tool.configure", "approval_policy.configure",
    "employee.invite", "employee.role.assign", "employee.disable",
}

def authorize(member: WorkspaceMember, action: str, resource=None) -> None:
    """403 nếu action nằm trong PROTECTED_ACTIONS và role < admin. Không hard-code
    founder_id (mục 15A.2) — kiểm tra qua role, sẵn sàng mở rộng RBAC nhân viên sau này."""
    if action in PROTECTED_ACTIONS and PERMISSION_LEVELS.get(member.role, 0) < PERMISSION_LEVELS["admin"]:
        raise HTTPException(403, detail=f"Action '{action}' requires admin role")
```

Migrate dần các role-check rải rác sang gọi `authorize(member, "<action>")` (không đổi hành vi, chỉ tập trung hoá) — không cần làm hết cùng lúc với pilot, có thể theo sau.

**2. Protected Resource — generalize `WorkspaceTemplate`/`WorkspaceTemplateVersion`** — `backend/app/core/protected_resources/models.py` (SnowflakeIDMixin, đăng ký `db/base.py`):

```python
class ProtectedResource(SnowflakeIDMixin, Base):
    __tablename__ = "protected_resources"
    __table_args__ = (UniqueConstraint("workspace_id", "resource_type", "resource_key"),)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    resource_type: Mapped[str] = mapped_column(String(50))   # "agent_prompt", "spec", "skill", "policy", "priming"
    resource_key: Mapped[str] = mapped_column(String(255))   # vd "agent:{agent_id}:system_prompt"
    active_revision_no: Mapped[int] = mapped_column(Integer, default=0)   # 0 = đang dùng default
    editable_by: Mapped[list] = mapped_column(JSONB, default=lambda: ["admin"])
    resettable: Mapped[bool] = mapped_column(default=True)

class ProtectedResourceRevision(SnowflakeIDMixin, Base):
    __tablename__ = "protected_resource_revisions"
    __table_args__ = (UniqueConstraint("resource_id", "revision_no"),)
    resource_id: Mapped[int] = mapped_column(ForeignKey("protected_resources.id"), index=True)
    revision_no: Mapped[int] = mapped_column(Integer)
    content_jsonb: Mapped[dict] = mapped_column(JSONB)
    is_default: Mapped[bool] = mapped_column(default=False)   # revision 0 = bundled default, immutable
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE")
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    checksum: Mapped[Optional[str]] = mapped_column(String(128))
    created_at: ...
```

Service mới `backend/app/core/protected_resources/service.py`: `get_effective(resource_type, resource_key)`, `create_revision(...)`, `reset_to_default(...)` (archive current override, `active_revision_no=0`, ghi `AuditLog`) — đúng flow mục 15A.5.

**Audit** (mục 15A.9): tái dùng `AuditLog` có sẵn (`backend/app/modules/platform/models.py:56-66`, đã đủ field `actor_type/actor_id/action/target_type/target_id/metadata_jsonb`) — **không tạo bảng audit mới**. Convention: `action ∈ {CREATE_OVERRIDE, UPDATE, APPROVE, RESET_TO_DEFAULT, RESTORE_REVISION}`, `target_type="protected_resource"`.

**3. Pilot đầu tiên: `Agent.system_prompt`** (đã có DB row, scope workspace rõ, dễ quan sát tác động):
- `PATCH /agents/{agent_id}` (`agents_router.py:91-119`): thêm `authorize(member, "prompt.update")` đầu hàm; khi có `system_prompt` mới, gọi `create_revision(resource_key=f"agent:{agent_id}:system_prompt", ...)` thay vì ghi trực tiếp. `Agent.system_prompt` (cột hiện có) trở thành cache của effective revision — đọc lại sau `create_revision`, giữ tương thích ngược cho các nơi đang đọc trực tiếp.
- Endpoint mới `POST /agents/{agent_id}/system_prompt:reset` — `authorize(member, "prompt.reset")` + `reset_to_default(...)`.
- Endpoint mới `GET /agents/{agent_id}/system_prompt/revisions` — phục vụ Dashboard Admin Editor (History/Diff, mục 15A.7).

**4. Job binding theo revision** (acceptance test cuối mục 15A.12: Job chạy với revision N, Admin lưu N+1, Job đang chạy vẫn dùng N): nối vào P2 — khi Job Router tạo `AgentRun`, ghi `prompt_revision_no` đã dùng vào `AgentRun.metadata_jsonb` (field JSONB có sẵn) lúc khởi tạo; Job đang chạy đọc theo giá trị đã bind, không đọc lại `get_effective()` giữa chừng.

### Acceptance tests (mục 15A.12) → implementation mapping

| Test | Implementation |
|---|---|
| Admin edit Prompt → allowed, tạo revision mới | `create_revision()` sau `authorize()` pass |
| Admin Reset to Default → override archived, default effective, audit | `reset_to_default()` |
| Non-admin `prompt.update`/`spec.reset` → 403 | `authorize()` raise trước khi chạm DB |
| Coding agent mutate protected resource → denied trừ khi có delegated permission | Coding agent gọi qua API thường như mọi actor — không có bypass đặc biệt trong `authorize()`; cần xác nhận lúc implement rằng không tồn tại service-account nào skip `get_current_workspace_member` |
| Job bound revision N, Admin save N+1 → Job vẫn dùng N | `AgentRun.metadata_jsonb.prompt_revision_no` bind lúc tạo run (nối P2) |

### Effort
**Lớn** — 2 bảng mới + `authz.py` + service revision/reset + sửa 1 router pilot. Migrate các role-check rải rác còn lại có thể làm sau, không blocking pilot. Không thiết kế RBAC nhân viên đầy đủ (mục 15A.11) ở giai đoạn này — chỉ chuẩn bị `authorize()` đủ tổng quát để mở rộng sau mà không phải sửa lại endpoint đã dùng nó.

---

## P1 — Scope Resolver / Memory Resolver / Priming Registry (mới, chi tiết vừa phải)

**Gap thật** — không có Scope Resolver, Priming Registry, hay domain-knowledge Skill Library (`SKILL.md`) nào trong `backend/app/`. Lưu ý phân biệt: `agents/execution/skills/manifest.py` (`SkillManifest`) là **sandbox execution skill** (permissions/resources cho code execution) — khác hoàn toàn "domain knowledge skill" (copywriting, funnel design) của mục 9 spec. Không đặt trùng tên, không tái dùng module này.

- **Priming Registry**: không cần bảng DB riêng — coi mỗi entry là 1 loại **Protected Resource** (`resource_type="priming"`) dùng chung hạ tầng revision của 15A, tránh xây cơ chế cấu hình riêng rồi phải migrate sau. 3-5 `job_type` mẫu định nghĩa cứng làm default (bundled, immutable).
- **Scope Resolver** (`backend/app/agents/context/scope_resolver.py`): chạy sau Conversation Gate (P0), trước khi có Job. `ScopeSet.minimal_conversation()` cho chat thường. Sửa cùng lúc: `_retrieve_context` chỉ gọi khi `gate_decision.needs_project` — đang vi phạm "No Job → No Heavy Priming" (chạy vô điều kiện hiện tại).
- **Memory Resolver**: extend `agents/control_plane/context.py` có sẵn (`ContextEnvelope`/`resolve_context()`) — thêm tham số `job_type`, chỉ query `AgentMemoryItem` khi khớp domain, thay vì luôn lấy 10 bản ghi gần nhất bất kể ngữ cảnh.
- **Skill Library**: thư mục mới `backend/app/agents/skills_library/{marketing,sales}/SKILL.md` (2-3 mẫu, frontmatter YAML tối giản: `required_context`, `tool_permissions`), `SkillResolver.resolve(job_type)` — chỉ gọi từ Job Runtime (P2), không từ P0 gate.

Effort: **Vừa-Lớn**, phụ thuộc P0 (Scope Resolver) và schema P2 (Priming/Skill). Làm tuần tự: Scope Resolver trước, Priming/Skill sau khi P2 chốt.

---

## P2 — Job & Skill Runtime (extend, không tạo bảng job mới)

Map thẳng vào entity đã có thay vì tạo bảng `job` song song:

| Field trong `job` schema (mục 10.1/28) | Entity có sẵn |
|---|---|
| `job_id`, `status`, `agent`, scope | `AgentRun` (`agents/governance/models.py:12-42`) — đã có `workspace_id`, `company_id`, `agent_key`, `status`, `permission_profile`. Thêm 2 cột `job_type`, `project_id` qua migration. |
| Job có nhiều step/skill | `AgentPlan`+`AgentPlanStep` (`agents/control_plane/models.py:33-82`) đã có `domain`/`capability`/`policy_level`/`tool_id` — thêm `skills_jsonb`. |
| Execution thật | `ExecutionJob` (`agents/execution/models.py:16-41`, đã liên kết `agent_run_id`) — không cần Job Runtime song song. |
| `job_context` | Ghi vào `AgentEventRecord.payload_jsonb` có sẵn, không cần bảng riêng. |
| `job_outcome` | Thuộc P4, không phải P2. |

Việc cần làm: 2 migration nhỏ (cột mới trên `AgentRun`/`AgentPlan`) + 1 module mỏng `agents/jobs/job_router.py::route_to_job(gate_decision, scope)` gọi `PrimingResolver`/`SkillResolver` (P1) trước khi tạo `AgentRun`. Marketing/Sales/Finance/Legal (`agents/domains/*`) bọc qua Job Router thay vì gọi trực tiếp — không viết lại logic domain agent.

Effort: **Vừa**.

---

## P3 — Action Runtime (extend, cấu hình thuần)

Đã đủ cả chuỗi Agent → Action Request → Policy Engine → Risk Classification → Approval Engine → Executor → Audit:
- `PolicyEngine.evaluate()` (`agents/governance/policy_engine.py`) — map permission_profile L0-L3A + `risk_level` → ALLOW/DENY/REQUIRE_APPROVAL, khớp Tier 0-3 mục 12.
- `ToolSpec.risk_level` (`tool_registry.py`) đã per-tool.
- `ApprovalService` (`agents/governance/approval_service.py`) đủ field.
- `ExecutionJob` + sandbox adapters làm Executor.
- `AgentToolCall`/`AgentEventRecord` làm Audit.
- **Phát hiện cần lưu ý**: `CapabilityGateway.check()` (`agents/capabilities/service.py`, dùng `CapabilityGrant`) là 1 cơ chế capability-check KHÁC, song song tồn tại với `PolicyEngine`, đang dùng cho domain agents khác nhau. Việc có nên hợp nhất 2 cơ chế này là quyết định kiến trúc riêng, ngoài phạm vi P3 — ghi nhận như rủi ro kỹ thuật cần founder quyết định, không tự ý gộp khi implement.

Việc cần làm: đảm bảo Job Router (P2) set đúng `policy_level`/`risk_level` cho tool mới theo đúng tier (`landing_page.generate`=Tier1/low, `email.send`=Tier2/medium+`requires_approval`, `hostinger.deploy`=Tier3/critical) — thuần config, không code mới.

Effort: **Nhỏ**.

---

## P4 — Observe / Verify / Learn (storage có sẵn, pipeline mới)

**Gap thật nhưng không phải từ 0**: `AgentMemoryItem` (bảng `agent_business_memories`, `agents/control_plane/models.py:84-99`) đã tồn tại và đã được đọc vào context (`control_plane/context.py:143-160`), nhưng nơi duy nhất ghi là `POST /memories` thủ công của founder (`control_plane/router_api.py:398-423`, `provenance_jsonb.source="founder_manual_entry"`) — không có `job_outcome`, không có `verifier` nào (grep rỗng).

Thiết kế: bảng mới nhỏ `JobOutcome` (`agents/learning/models.py`, SnowflakeIDMixin) khớp schema mục 28 (`run_id`, `metric`, `expected_jsonb`, `actual_jsonb`, `verified`, `source_ref`) → `OutcomeObserver` hook vào cuối `AgentRun` lifecycle (status→`completed`) → `Verifier` rule-based đối chiếu actual/expected → `LearningWriter` **chỉ chạy khi `verified==True`** (mục 14.1/25 "Learning không được ghi bừa"), ghi vào `AgentMemoryItem` có sẵn với `provenance_jsonb={"source":"verified_job_outcome", "job_outcome_id":...}` — tái dùng nguyên bảng, không tạo `learning_memory` mới.

Effort: **Vừa** — 1 bảng mới + 3 hàm mỏng nối vào lifecycle `AgentRun` đã có.

---

## P5 — Hologram Hub Presence / Agent Event Bus (gap thật, đã trace cụ thể)

**Phát hiện quan trọng nhất trong các phase còn lại**: hạ tầng transport đã hoàn chỉnh nhưng không ai bơm agent event vào, và consumer không diễn giải theo granularity agent runtime.

Bằng chứng: `EventBroker`/`publish_event()`/`CrossProcessEventListener` (`backend/app/core/events.py:120-176`, LISTEN/NOTIFY qua Postgres, có test) → `GET /events/stream` SSE (`platform/events_router.py`, mount ở `main.py:147`) → `RealtimeService.connect()` (frontend) → `HologramHubController._onRealtimeEvent` (`hologram_hub_controller.dart:171-177`) đã subscribe nhưng **chỉ refetch REST cho mọi event_type, không đọc payload để cập nhật `runtimeState` (Visualizer state mục 17.3)**. `publish_event()` không có nơi gọi nào ngoài chính nó và test — trong khi `AgentEventRecord` được ghi (audit-only) ở 4 nơi (`agents/domains/sales/action.py`, `agents/execution/service.py`, `agents/control_plane/evaluator.py`, `agents/orchestration/chief_of_staff.py`) mà không publish realtime.

Thiết kế:
1. **Producer**: `backend/app/agents/events/agent_event_bus.py::publish_agent_event(...)` gọi `publish_event()` có sẵn, thêm ngay sau mỗi lần ghi `AgentEventRecord` ở 4 điểm trên — payload theo đúng mục 18.1 (`state`, `label`, `detail_safe`, `progress`, `risk`, `requires_approval`), **chỉ field an toàn, không chain-of-thought** (mục 18.2).
2. **Consumer**: sửa `_onRealtimeEvent` (dòng 171-177) — switch theo `eventType` bắt đầu `agent.*` để cập nhật `runtimeState` theo state machine mục 17.3/17.4, thay vì chỉ refetch REST.
3. Approval Card: dùng `needs_you_view.dart` làm tiền lệ UI (đang có diff dở dang không liên quan — **không động vào file này**), tạo widget mới trong `hologram_hub/presentation/widgets/` theo pattern `hud_card.dart` có sẵn.
4. Cần audit lúc implement: `HologramRuntimeState` enum hiện có (idle/listening/thinking/retrieving/acting/speaking/error/success/cancelled) có thể thiếu vài state tường minh của mục 25 (`understanding/routing/priming/tool_running/waiting_approval/completed/warning`) — xác nhận alias 1-1 hay cần bổ sung khi code.

Effort: **Vừa-Lớn** — backend nhỏ (1 hàm + 4 điểm gọi), frontend vừa (sửa handler + audit enum + card mới).

---

## P6 — Voice Hybrid (đã DONE phần lớn, chỉ polish)

Đã xác nhận triển khai đầy đủ, không phải gap: `RealtimeTransportResolver.resolve()` (`backend/app/modules/realtime/transport_resolver.py:15-60`) đúng 100% logic mục 16.4 (mobile luôn cloud; desktop auto/local/cloud với fallback + health check thật qua `is_local_livekit_healthy()`), wired vào `POST /realtime/sessions`, gated `FLAG_DESKTOP_LOCAL_TRANSPORT_V12_2`, có 8 test case (`test_realtime_transport_resolver.py`). Frontend đã truyền đúng `deviceType`.

Việc còn lại (nhỏ, audit khi implement): (1) UI Settings cho founder chọn `voice_transport` mode đã có chưa; (2) `realtime_health` endpoint có thể mở rộng để hiển thị runtime health thay vì chỉ config tĩnh; (3) xác nhận push-to-talk local (`VoiceService`/`onTalkPressed()`) đang dùng STT/TTS local thật hay cloud.

Effort: **Nhỏ**.

---

## Bảng tổng hợp

| Phase | Trạng thái | Effort | File mới chính | File sửa chính |
|---|---|---|---|---|
| P0 | Gap thật (bug xác nhận) | Vừa | `chat/conversation_gate.py` | `chat/chat_execution_service.py` |
| 15A | Gap thật (chi tiết đầy đủ) | Lớn | `core/authz.py`, `core/protected_resources/{models,service}.py` | `tasks/agents_router.py` |
| P1 | Gap thật (mới hoàn toàn) | Vừa-Lớn | `agents/context/scope_resolver.py`, `agents/skills_library/*/SKILL.md` | `agents/control_plane/context.py`, `chat_execution_service.py` |
| P2 | Extend | Vừa | `agents/jobs/job_router.py` | migration `AgentRun`+`AgentPlan` |
| P3 | Extend (config only) | Nhỏ | — | tool registration risk_level |
| P4 | Gap thật, storage tái dùng | Vừa | `agents/learning/models.py` (`JobOutcome`) | `agents/execution/service.py` |
| P5 | Gap thật (đã trace cụ thể) | Vừa-Lớn | `agents/events/agent_event_bus.py` | `hologram_hub_controller.dart` |
| P6 | Đã DONE phần lớn | Nhỏ | — | audit + polish |

**Thứ tự triển khai khuyến nghị**: P0 → 15A (song song được, độc lập nhau) → P1 → P2 → P3 → P4 → P5 → P6 (gần xong, làm cuối để polish).

---

## Verification

- **P0**: chạy `pytest backend/app/tests/chat/test_conversation_gate.py backend/app/tests/test_chat_execution_service.py` — xác nhận bảng regression mục 24 (input "chào"/"hello" → 0 tool call). Test thủ công qua chat UI: gõ "chào", quan sát log/DB không có `company_tools.execute_tool` nào được gọi.
- **15A**: `pytest` cho `authz.py` + `protected_resources/service.py` (revision/reset/audit flow) + test tích hợp `PATCH /agents/{id}` — xác nhận đúng 6 acceptance test mục 15A.12 (admin allowed, non-admin 403, reset-to-default, job-binding).
- **P1-P4**: test đơn vị cho từng module mới (`scope_resolver`, `job_router`, `JobOutcome`/`Verifier`/`LearningWriter`) theo acceptance checklist mục 25 tương ứng.
- **P5**: test thủ công — trigger 1 agent action thật (vd domain agent sales), quan sát Hologram Hub Card chuyển state đúng theo `agent.*` event, không phải chỉ refetch tĩnh; xác nhận "chào" không sinh event nào (hệ quả của P0, không cần thêm).
- **P6**: chạy `pytest backend/app/tests/test_realtime_transport_resolver.py` (đã có, xác nhận không hồi quy) + audit UI settings.
- Trước khi handoff mỗi phase: chạy backend pytest liên quan + `flutter analyze`/test liên quan cho phần frontend đã sửa, theo đúng CLAUDE.md ("Use test-first development... Run backend pytest and Flutter tests/analyze relevant to changed code before handoff").
