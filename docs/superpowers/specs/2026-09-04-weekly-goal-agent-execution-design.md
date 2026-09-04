# Weekly Goal → Agent Execution (WGA) — Design

**Ngày:** 2026-09-04
**Trạng thái:** Approved (brainstorming), chờ writing-plans
**Liên quan:**
- `docs/superpowers/specs/2026-09-03-kickoff-materialize-weekly-tasks-design.md` — chuỗi `twelve_week_cycles → weekly_plans → weekly_commitments → tasks` mà spec này tái dùng, không dựng lại.
- `docs/superpowers/specs/2026-09-04-command-center-dashboard-redesign-design.md` — Command Center là nơi đặt UI mới.
- `ADR-COSA-DELEGATION-002`, `ADR-AGENT-REG-001`, `ADR-AI-COMPLIANCE-RUNTIME-001`.

## 1. Vấn đề

Founder đặt mục tiêu tuần (kèm hoặc không kèm task), nhưng AI agent hiện **chỉ phản ứng khi được hỏi trong chat** — không có đường để:

1. Khi founder đặt/sửa mục tiêu tuần (ở Command Center **hoặc** nêu trong chat), agent tự phân tích và **đề xuất kế hoạch triển khai** (phân rã thành công việc cụ thể).
2. Founder xác nhận kế hoạch một lần (theo lô), agent **tự thực thi** những việc thuộc quyền hạn của mình.
3. Việc có side-effect (gửi khách hàng, tài chính, đổi quyền…) đi qua **phê duyệt từng cái** rồi agent mới làm.
4. Việc agent không thể tự làm (phỏng vấn khách hàng trực tiếp, họp, quyết định chiến lược) được **tách riêng, gán cho founder**.

### Hiện trạng (đã verify bằng code)

| Mảnh | Hiện có | Vị trí |
|---|---|---|
| Goal tuần | `weekly_plans.focus/mission`, set 1 lần lúc kickoff | `project-kickoff-materialize.service.ts` |
| Phân rã goal → task nháp | Skill `operations-tasks` + capability `operations.task.create_draft` (`source='ai_agent_proposal'`, bắt buộc `decision_reason`+`evidence_refs`) — **nhưng không gì gọi tự động**, và agent **không có capability đổi `tasks.status`** | `apps/cosa/capabilities/operations_write.py`, `skillpacks/operations/tasks/SKILL.md` |
| Runtime run | `execute_run_task` → PolicySnapshot → AgentSpec exact-hash → compliance delegation → `kernel.run`; `approval.required {approval_id, checkpoint_ref}` khi `waiting_approval`; `execute_resume_task` → `kernel.resume` | `apps/cosa/worker/handlers.py` |
| Autopilot | `trigger_policy.py` (`mode ∈ artifact_only\|proposal\|write`, `required_capabilities`, `max_runs_per_aggregate_per_day`, kill-switch `enabled`) — **chỉ dùng cho `customer_support_autopilot`** | `apps/cosa/events/trigger_policy.py` |
| Tenant policy | Bảng `workspace_agent_policy`, `getTenantPolicyForTool` → `ALLOW\|REQUIRE_APPROVAL\|DENY`, match `exact > prefix.* > *` | `services/cosa/services/agent-policy.service.ts` |
| Task ↔ run link | Bảng `task_execution_records` (`run_id, tool_call_id, capability_id, triggered_by_kind, decision_record_id, status`) — **đã đủ cột** | `services/company/shared/db/schema/operations.ts` |
| Task assignee | `tasks.assignee_member_id` (nullable), `tasks.execution_mode` (text), AI member = `identity.workforce_members` (`member_type='ai'`, `agent_spec_id`) | `identity.ts:95`, `operations.ts:18` |
| Vòng duyệt FE | `WaitingForYouWidget` (`onApproveTask`/`onRejectTask` → resume), `founder_command_center_controller` (`approveTask`/`rejectTask`, `pendingApprovals`) | `frontend/lib/modules/hologram_hub/` |

### Khoảng trống

- **G1** Không có trigger "mục tiêu → run phân rã".
- **G2** Không có artifact "kế hoạch triển khai" xem-duyệt theo lô (task nháp hiện rơi rời rạc vào danh sách).
- **G3** Không có phân loại "capability ↔ task" → không tách được việc AI làm vs việc founder.
- **G4** Không có vòng "tự thực thi task trong quyền"; agent không có capability đổi status task.
- **G5** Không flow gán task cho AI member; không worker poll "task của tôi".
- **G6** "Goal từ chat" không được cấu trúc hoá — mục tiêu nói trong chat bị rơi.

## 2. Quyết định phạm vi (đã chốt với user)

| Câu hỏi | Chốt |
|---|---|
| Agent tự thực thi tới đâu | **Đầy đủ**: tự chạy cả việc side-effect, qua `approval.required` từng cái |
| Nguồn "mục tiêu tuần" | **Tái dùng `weekly_plans.focus`** (chuỗi 12WY spec 2026-09-03), không bảng goal mới |
| Goal từ chat kích hoạt | **Agent tự nhận diện** intent, có bước confirm chống nhầm |
| Agent profile trong phạm vi | **operations + finance + marketing** (3 profile đã deploy) |
| Màn duyệt kế hoạch | **Cả hai**: card ở Command Center (nơi sửa) + CTA link từ chat (chỉ báo) |

## 3. Nguyên tắc bất biến

1. Business truth ở `services/*`. Agent không tự ghi business DB — mọi side-effect qua Capability + Governance + Audit.
2. Không capability side-effect nào chạy mà không có **`tenant_policy=ALLOW`** (do founder đặt) **hoặc** một approval bound đúng `run_id + tool_call_id + checkpoint_ref`.
3. **Outbound / finance / deploy / delete / workspace-settings: vĩnh viễn không AUTO** — không nới được kể cả founder ép.
4. `autonomy_class` quyết định ở **backend** khi materialize, ghi cứng, không tính lại lúc execute; execute-time vẫn re-check freshness tenant-policy (§10.5) — policy siết lại giữa chừng thì hạ xuống approval tại chỗ.
5. Agent đổi `tasks.status` **chỉ** qua capability mới `operations.task.advance`, **chỉ** với task nó đảm nhận.
6. Trạng thái structured — không `if "blocked" in model_text`. Plan agent xuất ra theo JSON schema cố định; sai schema → run fail, không tạo plan nửa vời.
7. Test durability qua process/lease thật (không 2 instance cùng process).

## 4. Kiến trúc — luồng 4 chặng

```
CHẶNG 1  GOAL INTAKE
  (A) Command Center: sửa "Mục tiêu tuần" + nút "Nhờ AI lập kế hoạch"
  (B) Chat: agent nhận diện intent=set_weekly_goal → confirm card → founder bấm "Đặt & lập kế hoạch"
                                   │
        POST /operations/strategy/projects/:id/weekly-goal { focus, mission?, triggerDecomposition, origin, originRef }
                                   │  upsert weekly_plans (week 1, helper materialize sẵn có)
                                   ▼
                      emit  operating.weekly_goal.set.v1

CHẶNG 2  DECOMPOSITION RUN  (worker, kind=goal_decomposition)
  event → task worker → execute_goal_decomposition_task
  agent operations chủ trì; skill operations-tasks / twelve-week-year / lifecycle-next-best-action
  gọi operations.task.list để chống trùng
  → agent xuất STRUCTURED PLAN (JSON schema): items[]{ title, decision_reason, evidence_refs,
       suggested_domain, expected_capability, depends_on_titles, priority }
  → backend ROUTER + CLASSIFIER (§6) gắn: owner_agent_profile, autonomy_class, autonomy_class_source
  → POST /operations/execution-plans  → execution_plans(draft) + execution_plan_items(proposed)
  → emit operating.execution_plan.created.v1  (origin=chat → agent đăng message CTA)

CHẶNG 3  PLAN REVIEW & ACCEPT
  Card "Kế hoạch đề xuất" (Command Center): sửa title / đổi class / đổi owner / bỏ item
  founder "Chấp nhận cả lô" → POST /operations/execution-plans/:id/accept  (1 transaction):
    mỗi item != dropped → weekly_commitments + operating.tasks
      (source='ai_agent_proposal', weekly_commitment_id, execution_mode, assignee) + task_projects
    AUTO / NEEDS_APPROVAL → assignee = AI member của owner_agent_profile
    FOUNDER_ONLY          → assignee = founder member
    task_dependencies từ depends_on_item_ids
  → emit operating.execution_plan.accepted.v1

CHẶNG 4  EXECUTION LOOP  (worker task-executor, poll ~30s)
  claim: tasks status='todo' AND source='ai_agent_proposal' AND execution_mode IN ('agent_auto','agent_approval')
         AND assignee ∈ AI members AND deps done AND workspace không kill-switch AND runs_today < max
  lease durable per task (idempotency_key = task_id); set status='in_progress'
    execution_mode='agent_auto'      → dispatch run kind=task_execution (agent=owner_agent_profile)
       capability call: gateway check getTenantPolicyForTool
         ALLOW → chạy + task_execution_records; REQUIRE_APPROVAL / FORBIDDEN_RE → approval.required, task='waiting_approval'
       run xong OK → agent gọi operations.task.advance{ to_status:'done', run_id }
       run lỗi/timeout → task='blocked' + reason
    execution_mode='agent_approval'  → agent chạy tới checkpoint rồi LUÔN approval.required trước side-effect
       founder duyệt ở WaitingForYouWidget → execute_resume_task → kernel.resume → capability chạy → advance(done)
       founder từ chối → task='blocked' + reason
    execution_mode='founder'         → executor bỏ qua; hiện ở card "Việc của bạn"
```

## 5. Data model (Expand-only)

### 5.1 Bảng mới `operating.execution_plans`

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | bigint PK (snowflake) | |
| `workspace_id` | bigint not null | |
| `project_id` | bigint not null → `strategy.projects.id` on delete cascade | |
| `weekly_plan_id` | bigint → `operating.weekly_plans.id` on delete set null | goal nguồn |
| `goal_text` | text not null | snapshot `focus` lúc phân rã |
| `status` | text not null default `draft` | `draft` → `accepted` \| `superseded` \| `rejected` |
| `origin` | text not null | `command_center` \| `chat` |
| `origin_ref` | text | `conversation_id` nếu từ chat |
| `run_id` | text | run phân rã đã sinh plan |
| `accepted_by_member_id` | bigint | |
| `accepted_at` | timestamptz | |
| `created_at` / `updated_at` | timestamptz default now | |

Partial unique index: **1 plan `draft` / `weekly_plan_id`** (`WHERE status='draft' AND deleted_at IS NULL`). Phân rã lại → plan `draft` cũ → `superseded`.

### 5.2 Bảng mới `operating.execution_plan_items`

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | bigint PK | |
| `plan_id` | bigint not null → `execution_plans.id` on delete cascade | |
| `workspace_id` | bigint not null | tenancy guard |
| `title` | text not null | bắt đầu bằng động từ hành động |
| `decision_reason` | text not null | cho `operations.task.create_draft` contract |
| `evidence_refs` | jsonb not null default `[]` | ≥1 khi accept (trừ `FOUNDER_ONLY`) |
| `owner_agent_profile` | text | `operations` \| `finance` \| `marketing` \| null (=founder) |
| `expected_capability` | text | capability agent dự kiến gọi, hoặc null |
| `autonomy_class` | text not null | `AUTO` \| `NEEDS_APPROVAL` \| `FOUNDER_ONLY` |
| `autonomy_class_source` | text not null | `classifier_default` \| `tenant_policy` \| `founder_override` |
| `priority` | text default `medium` | |
| `depends_on_item_ids` | jsonb default `[]` | dependency trong cùng plan |
| `sort_key` | double precision | |
| `materialized_task_id` | bigint → `operating.tasks.id` on delete set null | null tới khi accept |
| `status` | text not null default `proposed` | `proposed` → `accepted` \| `dropped` |
| `created_at` / `updated_at` | timestamptz default now | |

### 5.3 Thay đổi schema có sẵn

- `operating.tasks`: **không đổi cấu trúc**. Dùng cột sẵn có:
  - `source = 'ai_agent_proposal'`
  - `execution_mode` — TS layer (`task.service.ts`) đã cố định enum `'HUMAN' | 'AGENT' | 'HYBRID' | null`. Đặt `'AGENT'` cho item `AUTO`/`NEEDS_APPROVAL`, `'HUMAN'` cho `FOUNDER_ONLY`. **Không overload cột này với `autonomy_class`.**
  - `assignee_member_id`, `weekly_commitment_id`
- **`autonomy_class` là single source of truth trên `execution_plan_items`**, không copy sang `tasks`. Worker `task-executor` JOIN `execution_plan_items ON materialized_task_id = tasks.id` để đọc class + `owner_agent_profile` + `expected_capability`.
- FK duy nhất thêm hướng tasks: `execution_plan_items.materialized_task_id`.
- Migration: 2 `CREATE TABLE` + index, không `ALTER` phá huỷ (Encore Guardrail #4).

### 5.4 Không tạo mới (xác nhận)

- Không bảng "goal" — `weekly_plans.focus`.
- Không bảng `capability_autonomy_map` — default classifier là **hằng số trong code `apps/cosa`** (giống `FORBIDDEN_AUTOPILOT_CAP_RE`); override per-workspace qua `workspace_agent_policy` sẵn có.
- Không bảng AI member riêng — `identity.workforce_members` (`member_type='ai'`, `agent_spec_id`).
- Kill-switch per-workspace: pattern quy ước `execution.autopilot` = `DENY` trong `workspace_agent_policy`, không bảng mới.

## 6. Autonomy classifier & router (phần rủi ro cao nhất)

### 6.1 Router: item → `owner_agent_profile`

Agent phân rã tự đề xuất `suggested_domain`. Backend **không tin text** — chuẩn hoá qua bảng ánh xạ tường minh (giống `_AGENT_PROFILE_SPECS` trong `handlers.py`):

```
_EXPECTED_CAP_PREFIX_TO_PROFILE = {
  "operations.": "operations", "engagement.": "operations",
  "finance.": "finance", "billing.": "finance",
  "marketing.": "marketing", "strategy.positioning": "marketing", "research.": "marketing",
}
```

- Có `expected_capability` → route theo prefix capability (nguồn chắc chắn nhất).
- Không có capability → route theo `suggested_domain` + kiểm tra chéo keyword; lệch → `owner_agent_profile = null` → `FOUNDER_ONLY`.

### 6.2 Classifier: item → `autonomy_class` (dừng ở match đầu tiên)

1. **Không có `expected_capability`** → `FOUNDER_ONLY`, `source=classifier_default`.
   *Việc không map được vào capability nào = việc tay (phỏng vấn KH, họp, quyết định chiến lược).*
2. **`expected_capability` khớp `FORBIDDEN_RE`**
   `= (billing\.|finance\.write|\.opportunity\.|\.lead\.write|\.message\.send|legal\.write|\.deploy|\.delete|workspace\.settings)`
   → `NEEDS_APPROVAL`, `source=classifier_default`. **Không bao giờ AUTO, không nới được.**
3. **`workspace_agent_policy` cho capability**: `DENY` → `FOUNDER_ONLY`; `REQUIRE_APPROVAL` → `NEEDS_APPROVAL`; `ALLOW` → `AUTO`. `source=tenant_policy`.
4. **Classifier default theo `CapabilityRisk` của `CapabilitySpec`:**
   - `LOW` + action chỉ đọc/tạo-artifact (`*.read`, `*.list`, `*.draft`, `*.create_draft`, research, SOP) → `AUTO`.
   - `MEDIUM` → `NEEDS_APPROVAL`.
   - `HIGH` / không xác định → `NEEDS_APPROVAL`.
5. Fallback → `NEEDS_APPROVAL`.

### 6.3 Founder override khi duyệt

Dropdown class trên mỗi item trong card:
- Hạ cấp (`AUTO → NEEDS_APPROVAL → FOUNDER_ONLY`): luôn được, `source=founder_override`.
- Nâng `FOUNDER_ONLY → NEEDS_APPROVAL`: được.
- Nâng lên `AUTO`: **chặn** (FE + backend) nếu capability khớp `FORBIDDEN_RE` **hoặc** `tenant_policy ≠ ALLOW`. Hiện lý do inline. `source` không thể là `founder_override` cho nhóm `FORBIDDEN_RE`.

### 6.4 Bất biến classifier

- Chạy ở backend khi tạo plan + khi PATCH item; ghi cứng vào `execution_plan_items.autonomy_class` và (khi accept) `tasks.execution_mode`.
- Execute-time: gateway re-check `getTenantPolicyForTool` mỗi capability call — `AUTO` bị hạ xuống `approval.required` tại chỗ nếu policy đã siết, không chạy lén.

## 7. Goal intake

### 7.1 Từ Command Center (đường A)

- Cạnh field "Mục tiêu tuần" (trong `top3_focus_widget.dart` / khu vực goal): nút **"Nhờ AI lập kế hoạch"**.
- Sửa goal + bấm → `POST /operations/strategy/projects/:id/weekly-goal { focus, mission?, triggerDecomposition: true, origin: "command_center" }`.
- Service (`services/company/operations/strategy/services/weekly-goal.service.ts`):
  - upsert `weekly_plans` week 1 (tái dùng helper lazy-create cycle+plan từ `project-kickoff-materialize.service.ts`).
  - `triggerDecomposition` → emit `operating.weekly_goal.set.v1 { workspaceId, projectId, weeklyPlanId, focus, origin, originRef }`.
  - Idempotent theo (`weeklyPlanId`, `focus` hash) — bấm 2 lần không tạo 2 run.

### 7.2 Từ chat (đường B) — agent tự nhận diện

- Trong `execute_run_task` của agent operations: sau khi agent trả lời, chạy **1 bước phân loại phụ** (structured output, không so chuỗi):
  `{ is_weekly_goal_statement: bool, normalized_goal: str, confidence: float }`.
- `confidence ≥ ngưỡng` (cấu hình, default 0.75) → agent chèn message structured `goal_confirm` vào conversation:
  *"Đặt đây làm mục tiêu tuần này và để tôi lập kế hoạch? [Đặt & lập kế hoạch] [Không]"*.
- Founder bấm "Đặt & lập kế hoạch" → FE gọi endpoint 7.1 với `origin:"chat"`, `originRef=conversationId`.
- **Không tự ghi goal khi chưa confirm** (chống nhận nhầm; structural, không dựa prompt).

### 7.3 Decomposition run

- `operating.weekly_goal.set.v1` → `apps/cosa` event intake → task worker `kind=goal_decomposition`, payload `{ workspace_id, project_id, weekly_plan_id, goal_text, origin, origin_ref }`.
- `execute_goal_decomposition_task` (handler mới, `apps/cosa/worker/handlers.py`):
  1. Resolve PolicySnapshot + AgentSpec operations exact-hash (như run thường).
  2. `kernel.run` — prompt dựng từ goal + context: lifecycle stage, next-best-actions (`GET .../next-best-actions`), task hiện có (`operations.task.list`) để chống trùng.
  3. Agent xuất **structured plan** đúng JSON schema cố định (`items[]`).
  4. Backend: router + classifier (§6) → `POST /operations/execution-plans`.
  5. Emit `operating.execution_plan.created.v1`. Nếu `origin=chat` → agent đăng message `execution_plan_ready` kèm deep-link tab Command Center.
- Fail (kernel lỗi / plan sai schema) → run `failed`, **không** tạo plan; chat báo lỗi mã ổn định; founder retry bằng nút.

## 8. Plan review & accept → materialize

### 8.1 Card "Kế hoạch đề xuất" (Command Center)

- Nguồn: `GET /operations/execution-plans?projectId=&status=draft`.
- Hiển thị: `goal_text`; danh sách item — title (sửa inline), dropdown `autonomy_class`, dropdown `owner_agent_profile`, toggle "Bỏ", badge `expected_capability` + lý do class, dependency.
- **"Chấp nhận cả lô"** — disabled nếu item `AUTO`/`NEEDS_APPROVAL` nào thiếu `evidence_refs`.
- **"Từ chối"** → `execution_plans.status='rejected'`.
- Item `FOUNDER_ONLY` không yêu cầu evidence.

### 8.2 `POST /operations/execution-plans/:id/accept` (1 transaction)

Bọc `db.transaction()` (như `activateProjectOperatingSetup`):

1. `execution_plans.status='accepted'`, ghi `accepted_by_member_id` / `accepted_at`.
2. Mỗi item `status != 'dropped'`:
   - `weekly_commitments` (title, `weekly_plan_id`, `initiative_id=null`, `commitment_owner_type` theo class, `execution_mode`) — tái dùng helper materialize.
   - `operating.tasks`: `source='ai_agent_proposal'`, `weekly_commitment_id`, `priority`, `status='todo'`,
     `execution_mode = { AUTO:'AGENT', NEEDS_APPROVAL:'AGENT', FOUNDER_ONLY:'HUMAN' }` (class chính xác đọc từ `execution_plan_items.autonomy_class`),
     `assignee_member_id = FOUNDER_ONLY ? founderMemberId : aiMemberFor(owner_agent_profile)`.
   - `task_projects(task_id, project_id)`.
   - `execution_plan_items.materialized_task_id`, `status='accepted'`.
3. `task_dependencies` từ `depends_on_item_ids` (map qua `materialized_task_id`). Circular → **422** trước khi ghi.
4. Emit `operating.execution_plan.accepted.v1`.

- Accept khi plan đã `superseded`/`rejected` → **409**, FE reload.
- Sửa item trước accept → `PATCH /operations/execution-plans/:id/items/:itemId` (re-run classifier guard §6.3).

### 8.3 Re-decompose

Founder sửa goal lần nữa → plan `draft` cũ → `superseded`; task đã materialize từ plan `accepted` trước **giữ nguyên** (không xoá việc đang chạy); plan mới chỉ bổ sung việc.

### 8.4 AI WorkforceMember seed

- Mỗi workspace: đảm bảo tồn tại 1 `workforce_members` (`member_type='ai'`, `agent_spec_id` = spec id của profile, `role_title`) cho mỗi profile trong {operations, finance, marketing}. Seed lười lúc accept đầu tiên hoặc lúc kickoff.
- `aiMemberFor(profile)` tra theo (`workspace_id`, `member_type='ai'`, `agent_spec_id`).
- `founderMemberId` = `workforce_members` (`member_type='human'`) có `human_user_id` trỏ tới owner/founder của workspace (role `OWNER`/`FOUNDER` trong `identity`); nếu workspace có nhiều human member, dùng member của người tạo project (`projects.created_by`). Resolve 1 lần khi accept.

## 9. Execution loop

### 9.1 Worker `task-executor` (process riêng, poll)

- Chu kỳ default 30s (env `WGA_EXECUTOR_POLL_SECONDS`).
- Claim query:
  ```
  SELECT t.*, i.autonomy_class, i.owner_agent_profile, i.expected_capability, i.id AS plan_item_id
  FROM operating.tasks t
  JOIN operating.execution_plan_items i ON i.materialized_task_id = t.id AND i.status = 'accepted'
  JOIN operating.execution_plans p ON p.id = i.plan_id AND p.status = 'accepted'
  WHERE t.deleted_at IS NULL
    AND t.status = 'todo'
    AND t.source = 'ai_agent_proposal'
    AND i.autonomy_class IN ('AUTO','NEEDS_APPROVAL')
    AND t.assignee_member_id IN (SELECT id FROM core.workforce_members WHERE member_type='ai' AND workspace_id = t.workspace_id)
    AND NOT EXISTS (SELECT 1 FROM operating.task_dependencies d
                    JOIN operating.tasks dep ON dep.id = d.depends_on_task_id
                    WHERE d.task_id = t.id AND dep.status <> 'done' AND dep.deleted_at IS NULL)
    AND NOT EXISTS (SELECT 1 FROM cosa.workspace_agent_policy wap    -- kill-switch (services/cosa DB, tra qua RPC agent-policy)
                    WHERE wap.workspace_id = t.workspace_id AND wap.tool_pattern = 'execution.autopilot' AND wap.decision = 'DENY')
    AND runs_today(t.workspace_id) < WGA_MAX_RUNS_PER_WORKSPACE_PER_DAY   -- default 50; đếm run kind=task_execution trong 24h qua, không tính goal_decomposition
  ORDER BY t.priority, t.sort_key
  LIMIT WGA_EXECUTOR_BATCH   -- default 5
  ```
  *(kill-switch check thực tế gọi `getTenantPolicyForTool({workspaceId, toolName:'execution.autopilot'})` qua RPC sang `services/cosa` — `workspace_agent_policy` không nằm trong DB `services/company`. Executor cache kết quả theo workspace trong 1 chu kỳ poll.)*
- Lease durable per task (`idempotency_key = task_id`) — chống 2 worker cùng chạy (CLAUDE.md #6).
- Set `status='in_progress'` bằng optimistic lock trên `updated_at` trước khi dispatch.

### 9.2 Dispatch theo `execution_mode`

**`agent_auto`:**
1. Dispatch run `kind=task_execution`, agent = `owner_agent_profile`, prompt = title + `decision_reason` + `evidence_refs` + chỉ thị *"hoàn thành bằng capability được phép; nếu cần side-effect ngoài quyền, dừng và tạo handoff"*. `metadata.execution_plan_item_id` để truy vết.
2. Mỗi capability call → gateway `getTenantPolicyForTool`:
   - `ALLOW` → chạy, ghi `task_execution_records(run_id, tool_call_id, capability_id, triggered_by_kind='agent', status)`.
   - `REQUIRE_APPROVAL` / khớp `FORBIDDEN_RE` → `approval.required`, task `status='waiting_approval'` (de-facto chuyển nhánh approval).
3. Run OK → agent gọi `operations.task.advance { task_id, to_status:'done', run_id }`.
4. Run lỗi/timeout → `status='blocked'` + reason; hiện ở "Việc của bạn".

**`agent_approval`:**
- Như trên nhưng chỉ thị agent chạy tới checkpoint rồi **luôn** `approval.required` trước mọi side-effect. Task `waiting_approval`.
- Founder duyệt ở `WaitingForYouWidget` (đã có) → `execute_resume_task(checkpoint_ref, {approved:true})` → `kernel.resume` → capability chạy → agent `advance('done')`.
- Founder từ chối → task `blocked` + reason.

**`founder`:** executor không đụng tới.

### 9.3 Capability mới `operations.task.advance`

```
id: operations.task.advance
risk: MEDIUM   metadata.action_class: "B"
input: { task_id, to_status ∈ {in_progress, done, blocked}, run_id, note? }
```

Company endpoint `POST /operations/tasks/:id/advance` (handler → service, không query DB trong handler):
- `task.assignee_member_id` phải là AI member của workspace hiện tại — sai → **403**, ghi audit.
- `to_status='done'` chỉ khi task đang `in_progress` hoặc `waiting_approval` — sai → **422**.
- Không cho `cancelled` (huỷ là việc người).
- Ghi `task_execution_records` + emit `task.completed` (`buildTaskCompletedEvent` đã có).

Đây là capability **duy nhất** cho agent đổi status task. `skillpacks/operations/tasks/SKILL.md` cập nhật phần "Fallback & Handoff" (hiện ghi "agent không có capability này").

### 9.4 Guardrails

- `WGA_MAX_RUNS_PER_WORKSPACE_PER_DAY` (default 50) — chống loop.
- Kill-switch per-workspace: `workspace_agent_policy` pattern `execution.autopilot` = `DENY`.
- Mọi run executor gắn `metadata.execution_plan_item_id` → audit truy ngược `item → weekly_plan → goal`.

## 10. Frontend

| Surface | File | Thay đổi |
|---|---|---|
| Nút "Nhờ AI lập kế hoạch" | cạnh field mục tiêu tuần (`top3_focus_widget.dart` hoặc banner "Vòng hiện tại") | gọi `weekly-goal` endpoint |
| Card "Kế hoạch đề xuất" | mới `frontend/lib/modules/hologram_hub/widgets/execution_plan_card_widget.dart` | list item + edit class/owner + accept/reject |
| Confirm card goal trong chat | `hub_chat_panel.dart` / message renderer | render structured `goal_confirm` (2 nút) |
| CTA từ chat → card | message `execution_plan_ready` deep-link tab Command Center | |
| "Việc của bạn" | mở rộng `WaitingForYouWidget` hoặc card cạnh nó | list task `execution_mode='founder'` **hoặc** `status='blocked'` |
| Controller | `founder_command_center_controller.dart` | `RxList<ExecutionPlan> draftPlans`; `requestDecomposition()`, `acceptPlan()`, `rejectPlan()`, `updatePlanItem()`; subscribe `execution_plan.created` / `.accepted` SSE |
| Models | mới `frontend/lib/data/models/execution_plan_model.dart` | `ExecutionPlan`, `ExecutionPlanItem` |
| Contract | `shared/contracts/mvp-surface.json` + `route-auth-allowlist` | thêm route mới; chạy `make frontend-api-contract-check` |

## 11. Xử lý lỗi

| Tình huống | Xử lý |
|---|---|
| Decomposition run fail | không tạo plan; chat báo mã lỗi ổn định; retry bằng nút |
| Agent xuất plan sai schema | backend reject; run `failed`; không plan nửa vời |
| Accept plan đã `superseded`/`rejected` | 409, FE reload |
| 2 worker cùng claim 1 task | lease + optimistic lock `updated_at` → kẻ thua bỏ |
| Policy siết giữa lúc AUTO chạy | gateway re-check → hạ xuống `approval.required` tại chỗ |
| `operations.task.advance` cho task không phải của AI | 403 + audit; run `failed` |
| Founder ép AUTO capability `FORBIDDEN_RE` | FE + backend đều chặn |
| Founder xoá/sửa goal | plan `draft` → `superseded`; task đang chạy giữ nguyên |
| Circular dependency trong plan | 422 khi accept, chỉ ra vòng lặp |
| Goal-intent nhận nhầm | luôn có confirm card; dưới ngưỡng confidence → không hỏi |

## 12. Testing

**Backend (`services/company`):**
- `weekly-goal.service`: upsert focus, emit event, idempotent theo (weeklyPlanId, focus hash).
- `execution-plans.service`: tạo / list / patch / accept; accept materialize đúng số task + dependency + assignee theo class; reject; superseded; circular dep → 422; accept superseded → 409.
- `operations.task.advance` endpoint: AI member → OK; human/non-AI task → 403; `done` từ `todo` → 422; emit `task.completed`.
- Classifier unit test: bảng case capability → class (FORBIDDEN_RE; tenant policy DENY/REQUIRE_APPROVAL/ALLOW; risk LOW/MEDIUM/HIGH; no-capability → FOUNDER_ONLY).

**`apps/cosa`:**
- Router: `expected_capability` prefix → profile; `suggested_domain` lệch keyword → FOUNDER_ONLY.
- `execute_goal_decomposition_task`: mock kernel trả plan hợp lệ → POST execution-plans; plan sai schema → run failed, không POST.
- `task-executor`: claim query đúng filter; lease chống double-claim (qua lease/process thật — CLAUDE.md #6); `agent_auto` happy path → `advance('done')`; policy `REQUIRE_APPROVAL` giữa chừng → `waiting_approval`; `agent_approval` → `approval.required` → resume → `done`; run fail → `blocked`.
- Goal-intent detection: structured output parse; dưới ngưỡng confidence → không confirm card.

**Frontend (`flutter test`):**
- `founder_command_center_controller`: `requestDecomposition`; `acceptPlan` optimistic + reload; `updatePlanItem` chặn nâng AUTO trái phép.
- Widget: `execution_plan_card_widget` render class dropdown, disable "Chấp nhận" khi thiếu evidence; chat `goal_confirm` 2 nút.

**Gate:** `make services-test-company`, `make apps-cosa-test`, `cd frontend && flutter test`, `make frontend-analyze`, `make frontend-api-contract-check`, `make company-boundary-check`, `make encore-handler-boundary-check`, `make ts-suppression-check`, migration gates.

## 13. Ngoài phạm vi

- **Phase sau** — tự nới `NEEDS_APPROVAL → AUTO` theo lịch sử tin cậy (N lần duyệt tay liên tiếp); không áp cho `FORBIDDEN_RE`. Thiết kế riêng.
- Tạo tuần 2, 3… / weekly review cadence — spec khác.
- Sub-task đệ quy nhiều tầng — item chỉ 1 tầng ở slice này.
- UI chấm điểm 12WY (`executionScore`/`outcomeScore`) — không đụng.
- Agent tự phỏng vấn khách hàng / gọi điện — luôn `FOUNDER_ONLY`.
- Không backfill `weekly_plans`/task cũ.

## 14. Câu hỏi mở

Không còn — user đã chốt 5 quyết định phạm vi ở §2. Đây là bản tổng hợp để review trước khi viết implementation plan.

## 15. Addendum 2026-09-04 — quyết định wiring + phát hiện khi triển khai

### 15.1 Trigger wiring: hướng A (event-intake production) — đã chốt

Spec §7.3 giả định sai. Thực tế phát hiện khi code:

1. **Không có kênh `services/company` → `apps/cosa` đồng bộ.** Delegation chỉ 1 chiều (cosa ký → company verify). Company chỉ gọi RPC sang `services/cosa` (control plane TS).
2. **Đường event-intake CÓ wire trong lifespan** (`apps/cosa/api/app.py` gọi `build_event_intake_deps` khi `AGENT_DATABASE_URL` set) — docstring "P0 để None" đã lỗi thời. Outbox relay ở company (`events/outbox-relay.service.ts`) cũng có sẵn.
3. **Nhưng `handle_event` bắt buộc `EventTriggerRule` per-workspace** (cơ chế autopilot, operator provision, mặc định `enabled=false`).

**Giải pháp (đã implement, commit `9cffb11b`):** `apps/cosa/events/router.py` thêm `_PLATFORM_SELF_TRIGGER` — event founder chủ động phát tự schedule task, KHÔNG cần `EventTriggerRule`:
- `operating.weekly_goal.set.v1` → task `goal_decomposition` (spec `cosa.agents.operations`)
- `operating.execution_plan.accepted.v1` → task `workspace_task_sweep`

`LocalExecutionPlaneScheduleClient.schedule_platform_task()` schedule task với `task_type` tùy ý (không phải reference-task autopilot). `coalescing_key = wga:<ws>:<event_type>:<aggregate_id>` chống trùng.

**Task execution KHÔNG dùng poll loop toàn cục** (khác spec §9.1). Thay bằng: `execution_plan.accepted.v1` → 1 task `workspace_task_sweep` cho workspace đó. Handler sweep gọi `GET /operations/tasks/agent-claimable` (đã có, Task 1.8), chạy từng task, tự re-schedule (delay ~15s) nếu còn task `todo` (dependency chưa xong), tự dừng khi hết. Backpressure tự nhiên, không cần endpoint global "workspaces-with-claimable".

### 15.2 Điểm tích hợp CÒN LẠI (chưa code) — cần cho `execute_goal_decomposition_task` + `execute_workspace_task_sweep_task`

1. **Auth cho background-task → company.** Task self-trigger không có user session → không có delegation token. Phải mint qua `plane.compliance_resolver.resolve_for_run(req, spec)` (đường autopilot đang dùng) → `_company_delegation_token` scoped `{workspace_id, run_id, capability_ids}`.
   - **Chặn:** endpoint `POST /operations/execution-plans` + `POST /operations/tasks/:id/advance` hiện verify qua `requireWorkspaceAccess` (local-session / platform token). Phải cho verify thêm **cosa company-delegation token** (`cosa-delegation.service.ts::verifyCosaDelegationToken`, đã có cho capability-scoped call). `execution-plans`/`advance` không phải "capability" theo nghĩa scoped — cần quyết định: (a) thêm capability id giả cho 2 route này vào `capability_ids` scope, hoặc (b) 1 đường verify riêng "workspace-scoped cosa task token".
2. **Reuse run core.** `_execute_run_task_inner` (~370 dòng) coupling chặt với conversation. Cần tách helper `run_agent_and_get_text(plane, *, agent_profile, prompt, workspace_id, principal) -> (status, text, company_delegation_token)` để 2 handler mới + chat path dùng chung — refactor có test risk cho chat path (nhiều test hiện có).
3. **`workspace_task_sweep` kill-switch + rate limit.** Gọi `plane.tenant_policy_client` (RPC services/cosa) check `execution.autopilot=DENY` + đếm `task_execution` run 24h. Cần xác nhận `tenant_policy_client` có sẵn method phù hợp hay phải thêm.
4. **`execute_resume_task` mở rộng.** Sau resume completed, nếu payload có `execution_plan_item_id` → gọi `operations.task.advance(done)`.
5. **Dispatch branches** trong `apps/cosa/worker/main.py::dispatch_one_task` cho `task_type ∈ {goal_decomposition, workspace_task_sweep}` (giống nhánh `run`/`resume`, có lease theo `run_id` sinh nội bộ).

### 15.2b Integration point #1 — ĐÃ XONG (commit sau `9cffb11b`)

`services/company/shared/auth/cosa-task-delegation.ts` — `resolveCosaTaskContext()`:
- `POST /operations/execution-plans` — khi request có `runId` → verify cosa company-delegation token (cap `operations.execution_plan.create`, khớp `run_id`); không có `runId` → session (test/founder).
- `POST /operations/tasks/:id/advance` — delegation-only (cap `operations.task.advance`, khớp `run_id`).
- `GET /operations/tasks/agent-claimable` — chuyển `expose:true`, delegation (cap `operations.task.list`, chỉ workspace + cap).
- KHÔNG `consumeCosaDelegation` (1 sweep advance nhiều task / 1 token) — dựa TTL 600s + guard state-machine. 6 test; company suite 1116 pass.

`apps/cosa` mint token bằng `apps/cosa/auth/jwt.py::mint_company_delegation(sub, workspace_id, run_id, capability_ids=[...])` — gọi trực tiếp, KHÔNG qua `compliance_resolver` (vì cap-list WGA khai tường minh, không suy từ spec).

### 15.2c Integration point #3 (MỚI phát hiện) — AgentSpec `capability_refs`

`COSA_OPERATIONS_AGENT_SPEC.capability_refs` hiện chỉ `["operations.task.list", "operations.task.read"]`. Gateway chặn kernel gọi capability ngoài danh sách này. Nên:
- `execute_goal_decomposition_task`: OK — chỉ cần kernel reasoning ra JSON, KHÔNG gọi capability (pre-fetch context vào prompt, POST plan từ worker qua HTTP delegation).
- `execute_workspace_task_sweep_task`: agent chỉ "làm" được task có `expected_capability ∈ {operations.task.list, operations.task.read}` (read-only). Task cần capability khác (SOP draft, automation-design, ...) → phải **mở rộng `capability_refs` của operations spec + re-seed registry** (ADR-AGENT-REG-001: đổi = sửa code + redeploy). `operations.task.advance` gọi TRỰC TIẾP từ worker (không qua kernel) nên không cần trong refs.

→ Sweep executor v1 thực chất chỉ chạy được subset nhỏ; muốn đủ phải làm thêm bước mở rộng spec (chưa scope).

### 15.3 Trạng thái triển khai (2026-09-04, cập nhật cuối)

| Phase | Trạng thái | Test |
|---|---|---|
| **1 — company backend** | ✅ HOÀN TẤT | 53 |
| **2 — apps/cosa** | ✅ HOÀN TẤT (v1) | ~55 |
| **2 — int. point #1** delegation auth | ✅ `cosa-task-delegation.ts` + 3 route | 6 |
| **2 — int. point #2** run-core | ✅ `apps/cosa/worker/run_core.py` (`resolve_spec`/`prepare_request`/`run_kernel`), chat path refactor giữ nguyên hành vi | 7 |
| **2 — int. point #3** spec caps | ✅ operations AgentSpec `1.2.0` + `operations.task.create_draft` ref | — |
| **2 — decomposition + sweep** | ✅ `execute_goal_decomposition_task`, `execute_workspace_task_sweep_task`, self-trigger router (`_PLATFORM_SELF_TRIGGER`), dispatch branch `_dispatch_wga_task` | 24 |
| **3 — goal-intent + Flutter** | ✅ HOÀN TẤT (v1) | ~40 |
| **3 — goal-intent** | `goal_intent.py` pre-filter đa tín hiệu → `_execute_run_task_inner` chèn `{kind:"goal_confirm"}` message | 15 |
| **3 — Flutter** | `ExecutionPlan`/`ExecutionPlanItem` model, `ExecutionPlanService`, controller (`activeProjectId`/`draftPlans`/`requestDecomposition`/`acceptPlan`/`rejectPlan`/`updatePlanItem`/`loadDraftPlans`), `ExecutionPlanCardWidget` wired vào Command Center, nút "Nhờ AI lập kế hoạch", `goal_confirm` chat card, 5 allowlist entry | ~25 |

**Luồng end-to-end đã nối (v1):**
`weekly-goal` endpoint (`triggerDecomposition`) → outbox `operating.weekly_goal.set.v1` → relay → `handle_event` self-trigger → schedule `goal_decomposition` → worker → agent run → `parse_plan_output` → POST `/operations/execution-plans` (delegation, cap `operations.execution_plan.create`) → plan `draft`.
Founder accept (Phase 3 UI, hoặc gọi API trực tiếp) → outbox `operating.execution_plan.accepted.v1` → self-trigger → `workspace_task_sweep` → `GET agent-claimable` → mỗi task AUTO: advance `in_progress` → agent run → advance `done`/`blocked` → re-schedule nếu batch đầy.

### 15.4 Addendum 2026-09-04 (chiều) — đóng toàn bộ giới hạn v1 (Tier 1-3)

| # | Giới hạn v1 | Đã đóng — cách làm |
|---|---|---|
| **#1** | Task `NEEDS_APPROVAL` bị `blocked` oan, không có approval-resume cho headless | `operations.task.advance` nhận `waiting_approval`; sweep set task `waiting_approval` (bản ghi approval do kernel tạo, hiện ở `WaitingForYouWidget`); sweep run_id mã hoá task_id (`wga_task_<id>_<hex>`); `execute_resume_task` sau COMPLETED gọi `advance_wga_task_after_resume(done)`. |
| **#2** | Kill-switch chỉ env toàn cục | `operating.workspace_execution_settings` (migration 38) + `GET/POST /operations/execution-settings {sweepEnabled}`. `agent-claimable` trả `[]` khi tắt. (Company-side vì task nền không mint được control-plane delegation cho services/cosa.) |
| **#3** | Không tôn trọng ALLOW override per-workspace | `operating.workspace_capability_policy` (migration 39) + `GET/POST /operations/capability-policy {capabilityId, decision}`. `createExecutionPlanService` đọc bảng làm `tenant_policy_decision` lúc classify (ALLOW→AUTO, REQUIRE_APPROVAL/DENY hạ cấp; `FORBIDDEN_RE` vẫn thắng ALLOW; `null` xoá override). |
| **#4** | Chống loop chỉ `sweep_depth` | `agent-claimable` trả `[]` khi số distinct agent run_id trong `task_execution_records` / 24h ≥ `WGA_MAX_TASK_RUNS_PER_WORKSPACE_PER_DAY` (default 50). |
| **#5** | goal-intent chỉ heuristic | `classify_weekly_goal_llm` — 1 lượt Agents-SDK turn (không tool) trả `{is_weekly_goal_statement, normalized_goal, confidence}`. Pre-filter rẻ gate việc gọi LLM; verdict LLM (≥ `WGA_GOAL_INTENT_CONFIDENCE`, default 0.75) là quyết định; thiếu model / parse lỗi → fallback heuristic. |
| **#6a** | Không có widget "Việc của bạn" | `GET /operations/tasks/founder-inbox` (FOUNDER_ONLY + blocked ai_agent_proposal) → `YourTasksWidget` trong Command Center. |
| **#6b** | `draftPlans` chỉ reload khi mở lại tab | Controller poll `loadDraftPlans` + `loadFounderInbox` mỗi 20s khi ở tab Command Center (bỏ qua trong `Get.testMode`). |

Còn lại (không chặn, để sau): SSE push real-time thay poll 20s; UI toggle cho `execution-settings`/`capability-policy` (hiện chỉ API-level); circular-dep giữa item của 2 plan khác nhau.

Gate xanh: `make services-test-company` 1116 pass · `make apps-cosa-test` 774 pass (coverage 85% / gate 78%) · `make lint` · `cd frontend && flutter test` 1421 pass · `make frontend-api-contract-check` · company typecheck · boundary checks.
Lỗi có sẵn KHÔNG liên quan (fail trên `main` trước WGA): `route-auth-allowlist-check` (`cosa /platform/auth/me/agent-policy-snapshot`), `typecheck-py` (`apps/cosa/api/workforce_routes.py:508`), `make frontend-analyze` 1 info trong `project_kickoff_controller_test.dart:36` (file đang dở dang từ trước session, không thuộc WGA).
