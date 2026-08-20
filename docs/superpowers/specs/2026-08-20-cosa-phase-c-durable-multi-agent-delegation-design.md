# COSA Phase C — Durable Multi-Agent Delegation Design

**Ngày:** 2026-08-20
**Trạng thái:** Đã được duyệt trong phiên thiết kế
**Nguồn:** docs/architecture/COSA_HARNESS_STABILITY_AND_MULTIAGENT_DELEGATION_ROADMAP.md, Phase C
**Phạm vi:** Durable background delegation, generalized long-running executors, governance, shared limits, và Chief of Staff continuation

## 1. Mục tiêu

Phase C cho phép COSA giao một RunStep cho một AgentProfile hoặc executor cụ thể, chạy bất đồng bộ qua agent-worker, theo dõi bền vững trong PostgreSQL, áp dụng policy/approval/budget/depth của mission gốc, và đưa kết quả trở lại ChiefOfStaffOrchestrator.

Thiết kế phải đạt các thuộc tính sau:

- không tạo AgentRuntime hoặc agent turn loop thứ hai;
- không bypass GovernanceKernel đối với tool calls bên trong agent;
- không dùng mock làm fallback khi runtime/provider được yêu cầu không tồn tại;
- phục hồi được sau worker crash hoặc process restart;
- external side effect effectively-once trên nền delivery at-least-once;
- budget và depth áp dụng trên toàn bộ cây AgentRun;
- giữ nguyên hành vi mặc định của bốn specialist sales, finance, legal và marketing;
- hỗ trợ Codex, Claude Code, n8n và OpenSandbox qua boundary đúng loại;
- có tenant isolation ở mọi lookup và state transition.

## 2. Hiện trạng và khoảng trống

ChiefOfStaffOrchestrator hiện đã tạo AgentRun con nhưng delegation chỉ gọi trực tiếp SpecialistSpec.fetch_snapshot. RunStep và RunEvent tồn tại trong Founder OS nhưng chưa tham gia vòng phân công của Chief of Staff. AgentRuntime.run là seam agent canonical, còn ExecutionProvider chỉ là sandbox command API.

Codebase đã có các primitive hữu ích:

- AgentRun.parent_run_id, permission_profile và budget_jsonb;
- AgentRuntimeManager với mock và deepseek_harness;
- agent-worker cùng PostgreSQL polling và FOR UPDATE SKIP LOCKED;
- ExecutionJob/OpenSandbox;
- DeveloperJob/Device/JobLease;
- AutomationProvider và N8nAdapter;
- PolicyAction, PolicyDecision, ApprovalService, BudgetTracker và StuckDetector;
- RunStep, RunEvent và mission_control_bus.

Các khoảng trống cần xử lý:

- AgentRuntimeManager hiện fallback im lặng sang mock;
- BudgetTracker chỉ đếm usage của một AgentRun;
- Chief of Staff không có continuation cho delegation bất đồng bộ;
- DeveloperJob claim/submit chưa đủ mạnh cho execution production;
- tài liệu mô tả Codex/Claude/n8n executor seam rộng hơn code thực tế;
- RunEvent chưa có sequence/idempotency cho concurrent writers;
- RunStep.risk_level đang dùng mặc định L0, trộn permission vocabulary L0–L3 với risk vocabulary R0–R4.

## 3. Quyết định kiến trúc

### 3.1 Durable coordination table

Tạo bảng delegation_jobs riêng. RunStep vẫn là business source of truth; delegation_jobs chỉ sở hữu queue, claim/lease, retry, provider handle và recovery.

Không chuẩn hóa mọi provider thành ExecutionJob vì agent reasoning, device CLI, remote automation và sandbox command có lifecycle và security boundary khác nhau.

### 3.2 Hai tầng provider

TaskBoardService chỉ phụ thuộc DelegationProvider.

DelegationProviderManager có hai loại implementation:

1. InProcessSubagentProvider gọi AgentRuntimeManager và AgentRuntime.run.
2. LongRunningExecutorBridge forward sang LongRunningWorkProviderManager.

LongRunningWorkProvider có các adapter:

- CodexDeviceExecutor dùng DeveloperJob/Device lease;
- ClaudeDeviceExecutor dùng DeveloperJob/Device lease;
- N8nExecutor bọc AutomationProvider;
- SandboxExecutor bọc ExecutionJob/OpenSandbox.

Không adapter nào tự sở hữu polling loop. agent-worker là durable loop duy nhất.

### 3.3 State ownership

| Thành phần | Trách nhiệm |
|---|---|
| RunStep | Ý nghĩa nghiệp vụ, dependencies, assignee, trạng thái và kết quả cuối |
| DelegationJob | Queue, attempt, lease, retry, provider correlation và recovery |
| Child AgentRun | Governance context, permission, cost/budget và runtime trace |
| DeveloperJob/ExecutionJob/automation run | Provider-native execution state |
| RunEvent | Business timeline và mailbox của OutcomeRun |
| AgentEventRecord | Runtime trace; không quyết định RunStep state |

## 4. Component layout

Package mới:

    backend/app/workforce/agents/delegation/
      __init__.py
      types.py
      models.py
      provider.py
      manager.py
      policy.py
      limits.py
      events.py
      task_board.py
      worker.py
      providers/
        __init__.py
        in_process.py
        executor_bridge.py

    backend/app/workforce/agents/execution/long_running/
      __init__.py
      base.py
      types.py
      manager.py
      providers/
        __init__.py
        codex_device.py
        claude_device.py
        n8n.py
        sandbox.py

ChiefOfStaffOrchestrator chỉ gọi TaskBoardService và continuation service; nó không import provider adapter.

Commit đầu tiên giới thiệu DelegationProviderManager hoặc TaskBoardService phải đồng thời cập nhật
docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md, xác lập chúng là canonical owners của durable
delegation coordination và provider routing.

## 5. Schema

### 5.1 RunStep

Thêm:

- assigned_agent_profile_id: nullable string;
- assigned_runtime: nullable string;
- delegated_run_id: nullable FK tới agent_runs.id;
- result_jsonb: nullable JSONB.

RunStep.risk_level dùng R0–R4. Migration chuyển dữ liệu L0…L4 cũ sang R0…R4 và đổi default thành R0.

RunStep status canonical trong Phase C:

- pending;
- waiting_approval;
- running;
- completed;
- failed;
- cancelled;
- skipped.

### 5.2 AgentProfile

Thêm default backward-compatible:

- permission_profile = read_only;
- preferred_runtime = null;
- delegation_provider = agent_runtime.

preferred_runtime chỉ chọn AgentRuntime. delegation_provider phân biệt agent_runtime, codex_device, claude_device, n8n và sandbox.

### 5.3 DelegationJob

Các cột:

- id: Snowflake bigint primary key;
- workspace_id: FK workspaces.id, indexed;
- run_step_id: FK run_steps.id, indexed;
- root_agent_run_id: FK agent_runs.id, indexed;
- parent_agent_run_id: FK agent_runs.id, indexed;
- child_agent_run_id: nullable FK agent_runs.id, indexed;
- attempt_no: integer;
- provider_kind, provider_name, profile_id, runtime_name;
- status;
- provider_handle_jsonb;
- idempotency_key;
- available_at, next_poll_at;
- attempt_count, max_attempts;
- claimed_by, lease_token, lease_expires_at, heartbeat_at;
- cancel_requested_at;
- reserved_cost_usd, reserved_tool_calls, reserved_steps;
- result_jsonb, error_code, error_message;
- created_at, started_at, completed_at, updated_at.

Ràng buộc:

- unique run_step_id + attempt_no;
- unique workspace_id + idempotency_key;
- provider handle không chứa credentials hoặc provider secrets;
- mỗi lần reassign tạo attempt mới;
- tất cả service lookup phải scope theo workspace_id.

### 5.4 RunEvent

Thêm:

- sequence: integer, unique trong một OutcomeRun;
- event_key: string, unique trong một OutcomeRun.

Sequence được cấp dưới row lock của OutcomeRun. State transition và RunEvent tương ứng được commit trong cùng transaction.

Event types:

- step.assigned;
- step.delegation_queued;
- step.delegated;
- step.waiting_approval;
- step.retry_scheduled;
- step.delegation_denied;
- step.cancel_requested;
- step.cancelled;
- step.completed;
- step.failed.

## 6. State machine

DelegationJob:

    queued
      -> waiting_approval -> queued
      -> denied
      -> claimed -> dispatching -> running
                                  -> succeeded
                                  -> retry_scheduled -> queued
                                  -> failed
                                  -> cancel_requested -> cancelled

Mapping sang RunStep:

| DelegationJob | RunStep |
|---|---|
| queued, claimed | pending |
| waiting_approval | waiting_approval |
| dispatching, running, retry_scheduled | running |
| succeeded | completed |
| denied, failed | failed |
| cancelled | cancelled |

Mọi transition đi qua một state transition helper, dùng compare-and-swap hoặc row lock. Terminal state không được chuyển về non-terminal; operator retry tạo attempt mới.

## 7. Provider contracts

DelegationProvider:

    delegate(scope, step, profile, request, idempotency_key) -> DelegationHandle
    poll(handle) -> DelegationStatus
    cancel(handle) -> CancelResult
    health() -> ProviderHealth

LongRunningWorkProvider:

    start(context, request, idempotency_key) -> WorkHandle
    poll(context, handle) -> WorkStatus
    cancel(context, handle) -> CancelResult
    health() -> ProviderHealth
    capabilities() -> ProviderCapabilities

WorkStatus chuẩn hóa queued, running, waiting_approval, succeeded, failed và cancelled; đồng thời chứa progress, structured result, usage metrics, retryability, normalized error và next poll delay.

start phải idempotent. Adapter phải tạo hoặc tìm provider-native job theo idempotency key trước external side effect. Provider không hỗ trợ retry an toàn phải trả capability tương ứng và dispatch-unknown trở thành permanent failure.

## 8. Worker và recovery

agent-worker được mở rộng bằng delegation_loop và delegation_reconciler.

Một iteration:

1. Claim due job bằng FOR UPDATE SKIP LOCKED.
2. Ghi claimed_by, random lease_token và lease expiry.
3. Commit trước khi gọi model, CLI, sandbox hoặc HTTP.
4. Resolve profile/provider và kiểm tra tenant, dependency, depth, budget, policy.
5. Trong transaction ngắn, tạo child AgentRun, reserve budget, update state và ghi RunEvent.
6. Gọi provider ngoài transaction.
7. Persist handle bằng CAS theo job id và lease token.
8. Đặt next_poll_at và giải phóng lease giữa các poll.
9. Khi terminal, persist result, settle budget, update child run/step/event atomically.
10. Đánh thức dependent step hoặc Chief of Staff continuation.

InProcessSubagentProvider chạy AgentRuntime.run trong worker và renew lease bằng heartbeat coroutine. cancel_requested dẫn tới AgentRuntime.cancel.

Recovery rules:

- lease hết hạn trước handle: claim lại và idempotent start;
- có handle: chỉ poll;
- handle tồn tại nhưng native job mất: DELEGATION_PROVIDER_STATE_LOST;
- callback/poll trùng: event_key và terminal CAS chống double completion;
- result đến sau cancel: lưu audit nhưng không thay terminal state;
- hết max attempts: permanent failure và operator-visible dead letter;
- restart dựng toàn bộ state từ PostgreSQL, không dựa vào in-memory singleton.

## 9. Governance và approval

DelegationPolicyEngine trả về PolicyDecision và PolicyAction hiện có. Không tạo ToolSpec giả.

Input gồm actor, workspace, parent run, step, profile, provider, effective permission, depth và budget snapshot.

Quy tắc:

- profile/provider/runtime phải tồn tại, healthy và được enable;
- effective permission là quyền thấp hơn giữa parent và profile;
- R0/R1 có thể auto-assign nếu permission cho phép;
- R2 theo workspace/provider policy;
- R3/R4, coding executor, deployment và external automation mặc định REQUIRE_APPROVAL;
- unknown/unhealthy provider DENY và không fallback mock;
- n8n intent được govern trước webhook;
- AgentRuntime tool calls tiếp tục qua GovernanceKernel.

Approval dùng ApprovalService:

- action_type = delegation.assign;
- capability = agent.delegate;
- resource_type = run_step;
- resource_id = step id;
- tool_name = delegation.<provider_name>;
- idempotency key gắn delegation job.

Chỉ approval khớp capability/resource/idempotency mới resume job. Reject hoặc expire ghi step.delegation_denied và không dispatch provider.

## 10. Depth và shared mission budget

MAX_SUBRUN_DEPTH chuyển vào một module limits dùng chung.

Depth traversal đi toàn bộ parent_run_id chain và fail-closed khi cycle, orphan, cross-workspace chain hoặc vượt trần. Trước self-FK migration phải chạy preflight audit; migration dừng nếu dữ liệu chưa hợp lệ.

Root AgentRun là budget owner. BudgetTracker có aggregate mode dùng recursive CTE để cộng usage của root và descendants.

Để ngăn concurrent children cùng vượt trần:

- worker khóa root AgentRun khi reserve;
- committed usage + active reservations không vượt limit;
- reservation được settle theo usage thực;
- fail/cancel trước dispatch giải phóng reservation;
- wall time tính từ root started_at;
- tool bridge kiểm tra aggregate budget trước mỗi tool call;
- executor bridge kiểm tra trước dispatch và sau provider metric update.

StuckDetector tiếp tục phát hiện tool loops trên child run. Lease/heartbeat/provider deadline xử lý inactivity. Budget hoặc root wall-time hết sẽ yêu cầu cancel descendants.

## 11. Provider-specific design

### 11.1 Codex và Claude Code

CodexDeviceExecutor và ClaudeDeviceExecutor dùng DeveloperJob. DeveloperJob được bổ sung agent_run_id, run_step_id, executor_kind, request_jsonb, result_jsonb và cancel_requested_at.

Device protocol phải:

- claim atomic;
- kiểm tra workspace, required capabilities, allowed projects và trust level;
- có lease renewal;
- submit bằng active, unexpired lease token;
- reclaim lease hết hạn theo retry policy;
- acknowledge cancel;
- trả diff, artifacts, test results và redacted logs;
- chạy trong isolated workspace/worktree, không sửa main trực tiếp.

Scaffold backend/executors không được phục hồi làm production seam.

Backend Phase C cung cấp contract đầy đủ, nhưng adapter chỉ được đánh dấu production khi reference device worker hoặc test worker thực sự chạy CLI tương ứng qua contract.

### 11.2 n8n

N8nExecutor bọc AutomationProvider:

- request đã qua governance;
- signed correlation và idempotency key;
- external run id trong handle;
- poll hoặc signed callback;
- callback chống replay và kiểm tra workspace/provider/correlation;
- callback không trực tiếp mutate business state;
- cancel capability được khai báo trung thực.

### 11.3 OpenSandbox

SandboxExecutor tạo ExecutionJob với provider explicit. Execution loop hiện tại tiếp tục sở hữu sandbox lifecycle; delegation worker chỉ poll. Result dùng artifact references thay vì nhúng file lớn.

## 12. Chief of Staff continuation

SpecialistSpec thêm delegate_via_profile_id nullable.

Khi field không set, code tiếp tục fetch_snapshot đồng bộ.

Khi field set và feature gate đạt:

1. orchestrate tạo RunStep và DelegationJob;
2. trả mission status delegating;
3. worker chạy specialist;
4. khi required steps terminal, resume_after_delegation khóa OutcomeRun;
5. TaskBoardService.report_result tạo đúng specialist_reports shape;
6. chạy governance/budget check;
7. gọi synthesis path hiện tại;
8. ghi completion idempotently.

Required step failure có thể fail-fast. Optional failure giữ structured error report và tiếp tục synthesis, tương thích hành vi hiện tại.

Không fallback từ delegated path đã bắt đầu sang legacy fetch_snapshot vì có thể lặp side effect.

Canary bắt đầu bằng marketing read-only trong internal workspace, sau đó sales và finance. Legal chỉ bật sau khi quality-gate output shape được giải quyết.

## 13. Security invariants

- mọi lookup scope theo workspace;
- callback verify signature, replay window và correlation;
- provider handle/event/result được redact;
- secrets không persist trong delegation_jobs hoặc RunEvent;
- runtime/provider unknown fail-closed;
- child permission không vượt parent permission;
- device submit cần active lease token;
- external write không chạy trước approval;
- n8n không có quyền trực tiếp với business database;
- terminal transition idempotent;
- Phase B critical governance findings phải đóng trước production enablement.

## 14. Verification

Contract suite chung cho từng provider:

- idempotent start;
- poll normalization;
- cancel semantics;
- unavailable/unknown provider;
- malformed handle/result;
- timeout và transient/permanent errors;
- tenant isolation;
- không mock fallback.

PostgreSQL integration tests:

- SKIP LOCKED và lease CAS;
- unique idempotency;
- event sequence;
- recursive depth/budget;
- concurrent reservations;
- FK và tenant constraints.

Crash matrix:

| Crash point | Expected recovery |
|---|---|
| Sau claim, trước policy | Lease expiry và requeue |
| Sau approval creation | Không tạo approval thứ hai |
| Sau child run creation | Không tạo child run thứ hai |
| Sau dispatch, trước save handle | Idempotent provider recovery |
| Sau save handle | Chỉ poll |
| Sau provider terminal, trước step completion | Reconcile một lần |
| Trong cancel | Không dispatch/retry side effect |
| Sau event insert | event_key chặn event trùng |

End-to-end scenarios bao gồm legacy regression, async in-process, approval, concurrent budget, depth/cycle/orphan, device claim/renew/cancel/result, n8n signed callback/replay, sandbox artifacts, worker restart, optional/required specialist failure và kill switch.

## 15. Observability

Metrics:

- queue depth và oldest age;
- claim latency và lease expiry;
- retries/dead letters;
- provider start/poll/cancel latency;
- approval wait time;
- root budget usage/reservation;
- child depth;
- continuation lag;
- terminal jobs thiếu terminal RunEvent.

Log correlation fields:

- workspace_id;
- outcome_run_id;
- run_step_id;
- delegation_job_id;
- child_agent_run_id;
- provider correlation id.

## 16. Feature flags và rollout

Flags:

- agent_delegation;
- agent_delegation_chief_of_staff;
- agent_delegation_device_executors;
- agent_delegation_n8n;
- agent_delegation_sandbox;
- workspace/provider allowlist;
- global kill switch.

Tranches:

1. C0 — đóng Phase B gate, data audit, provider readiness matrix;
2. C1 — schema và canonical state/event helpers;
3. C2 — TaskBoard, policy, depth, aggregate budget, queue/lease/recovery;
4. C3 — async InProcessSubagentProvider và worker integration;
5. C4 — LongRunningWorkProvider, device hardening, Codex/Claude/n8n/sandbox adapters;
6. C5 — Chief of Staff continuation và legacy regressions;
7. C6 — internal canary;
8. C7 — chaos tests, operational APIs, dashboards, alerts và runbook.

Không retire legacy specialist path trong Phase C.

## 17. Exit criteria

- không governance bypass hoặc silent mock fallback;
- một durable job tạo tối đa một provider-native side effect;
- worker restart không mất hoặc nhân đôi job;
- budget/depth áp dụng toàn cây run;
- cross-tenant tests fail-closed;
- legacy Chief of Staff behavior giữ nguyên khi flag off;
- provider production chạy đủ contract suite;
- migration upgrade, downgrade và fresh install đạt;
- ownership map cập nhật trong commit giới thiệu seam;
- runbook mô tả inspect, cancel, retry và dead-letter recovery.

## 18. Phương án đã loại

### TaskBoard switch trực tiếp theo provider

Ít abstraction hơn lúc đầu nhưng TaskBoardService sẽ thành god-object và business layer phải đổi khi thêm provider.

### Chuẩn hóa mọi thứ thành ExecutionJob

Tận dụng worker hiện tại nhưng trộn agent reasoning, sandbox, device CLI và remote automation vào một model, phá ownership boundary.

### Không tạo delegation_jobs

Dùng RunStep làm cả business state và operational queue làm schema step phình lớn, khó giữ attempt history và lease/recovery semantics rõ ràng. Thiết kế được duyệt chọn coordination table riêng.

## 19. Non-goals

- không retire bốn legacy specialist;
- không xây UI task-board hoàn chỉnh;
- không cho n8n ghi trực tiếp PostgreSQL;
- không phục hồi root executor scaffold thành canonical runtime;
- không tạo agent planner/team protocol mới ngoài RunStep dependencies;
- không tăng MAX_SUBRUN_DEPTH trong Phase C;
- không cho provider tự cấp thêm permission hoặc budget;
- không coi mock contract test là bằng chứng production readiness.
