# Chat, Voice, N-Week Execution & Reporting Design

## Goal

Hoàn thiện COSA OS để Founder có thể vận hành dự án, OKR và chu kỳ thực thi N-tuần qua chat hoặc Live Voice; hệ thống tự động phân rã và điều phối công việc trong phạm vi đã duyệt, hiển thị tiến độ nhất quán, và báo cáo theo yêu cầu hoặc lịch tự động.

## Scope and Decisions

- `12WY` là chu kỳ N-tuần cấu hình được (1–52), mặc định 13 tuần; tuần cuối là tuần review/transition.
- Chat chỉ dùng `/api/v1/chat`; Flutter không gọi runtime legacy. Voice tiếp tục qua LiveKit và `services/realtime_agent`; backend FastAPI là control/data plane.
- Task, Outcome và OKR/KR là dữ liệu tiến độ chuẩn. Chỉ tổng hợp chỉ số Sales/Finance khi cycle/project/OKR liên quan và chỉ dùng số liệu đã xác thực.
- Tác vụ vận hành low-risk trong plan đã kích hoạt được thực thi tự động. Thay đổi chiến lược/cycle/OKR, tài chính, nội dung xuất bản và thao tác high/critical risk luôn cần Founder/Admin phê duyệt.
- Voice chỉ chủ động đọc báo cáo trong Live Voice session đang hoạt động. Ngoài phiên voice, report được gửi qua in-app chat/notification.

## Architecture

### Shared Work Orchestrator

Tạo lớp application service trong `backend/app` làm entry point chung cho chat và voice command:

1. Nhận transcript/message cùng authenticated `workspace_id`, `brain_id`, `user_id`, trạng thái UI hiện tại và optional project/cycle context.
2. Phân loại: inquiry, progress update, report request, plan/cycle command, work command, approval command.
3. Resolve mục tiêu trong workspace/brain ở server; không tin ID hay project hint từ client.
4. Với read/update low-risk, gọi strategy/task/outcome service hiện hữu rồi ghi audit/event.
5. Với large/risky action, tạo immutable execution proposal có diff, impact, evidence, policy decision và idempotency key; không ghi domain state trước khi được duyệt.
6. Sau phê duyệt, enqueue/replay exact command một lần; worker thực thi, lưu result/audit, cập nhật proposal thành executed/failed và phát event refresh.

`WorkIntentClassifier` là tín hiệu ban đầu, không phải authority. Nó cần được thay bởi typed command parsing/validation tại orchestrator để tránh keyword-only routing và để chat/voice có cùng hành vi.

### Approval execution gap

`ApprovalService` và `/api/v1/agent-approvals` hiện chỉ đổi trạng thái approval. Cần bổ sung proposal/execution record liên kết `AgentApproval` với command đã đóng băng. Endpoint approve chỉ được đánh dấu executed khi worker/domain action trả kết quả thành công; reject/expire không được thực thi command.

Policy Engine là lớp bắt buộc trước khi dispatch. Finance, publish-content, create/activate/replan project/cycle, OKR material change, pivot/stop và high/critical tool đều map sang `REQUIRE_APPROVAL`; rule không chỉ phụ thuộc prompt hay voice model.

## Project, OKR and N-week Flow

1. Founder đưa brief qua chat/voice.
2. AI tạo roadmap/stage plan draft, N-week focus, objective/KR và preview impact; Founder chỉnh/sửa trước khi activate.
3. Activation đã duyệt tạo `OkrCycle`, `TwelveWeekCycle(duration_weeks=N)`, `WeeklyPlan`, `WeeklyCommitment`, Task và Outcome theo existing runtime primitives.
4. Planner tạo dependencies, owner function/agent, acceptance criteria, evidence requirements, WIP/capacity checks và idempotency keys.
5. Dispatcher chỉ gửi task ready/dependency-satisfied cho agent phù hợp. Agent completion phải có Outcome/evidence; task blocked/failed tạo event cho report và Next Best Action.
6. Material replan/pivot giữ evidence cũ, supersede công việc chưa bắt đầu và đi qua approval. Không rewrite lịch sử hay tự thay đổi KR/cycle đang active.

## Progress Snapshot and Reports

### Snapshot

`ProgressSnapshotService` xây payload versioned, tenancy-scoped theo workspace/brain/project/cycle gồm:

- cycle: duration, current week from dates, phase, overall progress, late/blocker state;
- timeline: week, focus, status, commitment/task/outcome counts, owner functions, evidence links;
- OKR: objective/KR target/current/health; 
- selected business/finance metrics: only registered source data, unit, period, freshness and unavailable state;
- approvals and next action references; source timestamps and snapshot generation time.

Không để LLM tính số hoặc diễn giải dữ liệu thiếu là zero. LLM chỉ chuyển snapshot đã cấu trúc thành narrative có dẫn nguồn. Timeline service dùng cùng snapshot/aggregation rules; sửa logic `current_week` để suy ra theo `start_date` và clamp trong duration, thay vì cố định tuần 1.

### Delivery

- On-demand: chat/voice gọi snapshot của resource hiện tại hoặc resource đã resolve; chat trả narrative + structured card, voice đọc concise spoken summary và có thể mở UI command.
- Scheduled: Founder/Admin tạo automation flow theo workspace: timezone, schedule, scope, recipients, in-app channel/notification, detail level và triggers (`new week`, overdue blocker, KPI threshold). `worker_main.py` chạy due flows idempotently.
- Live voice: realtime agent nhận event/snapshot unread của participant khi session active; thông báo một câu ngắn rồi đọc full report chỉ khi Founder yêu cầu hoặc opt-in voice setting cho phép. Không thực hiện outgoing voice call.

Scheduler không được phép thay đổi strategy, financial state hay publish content; nó chỉ tạo/deliver report hoặc proposal.

## Hologram Hub UX

Desktop layout giữ ba vùng:

- **Left rail:** thay `SystemHealthPanel` bằng pinned `Executive Report Panel`: cycle/project title, snapshot freshness, compact metrics, N-week timeline, blockers/approval and activity log. Đây là overview luôn thấy.
- **Center:** contextual workspace, không chứa chat. Default là Hologram Hub với hologram. Khi user mở timeline detail, plan, task, document, report detail hoặc proposal, vùng này thay bởi internal page tương ứng; hologram thu nhỏ ở top chỉ khi cần Live Voice status.
- **Right rail:** persistent existing Chat & command input. Không copy chat history/input sang center.

Sau khi user completed view, approve, reject hoặc close internal page, center tự reset về Hologram default. User có thể pin page để giữ context qua refresh/navigation. UI event carries resource type/id, and backend re-authorizes on every fetch/action.

Mobile giữ chat/voice affordance hiện có nhưng opens contextual page full-screen; close returns to Hologram default.

## APIs and Events

All under versioned `/api/v1`, serializing Snowflake IDs as strings:

- command submit/status and proposal preview/approval execution;
- N-week plan draft/activate/replan with explicit `duration_weeks` validation;
- progress snapshot/report on-demand;
- report automation flow CRUD and delivery history;
- realtime report event/UI command envelopes.

Event types distinguish `progress.updated`, `report.generated`, `proposal.pending`, `proposal.executed`, `proposal.rejected`, `automation.delivery_failed`. Events contain no secrets or unscoped payloads.

## Error Handling and Safety

- Unknown intent, ambiguous project, unsupported metric or stale data asks a targeted question; it never fabricates or executes.
- Every resource lookup scopes `workspace_id` and where applicable `brain_id` server-side.
- Repeated command/delivery uses idempotency keys; retries are safe.
- Provider/worker/LiveKit failure makes status visible in chat/UI and preserves the source snapshot; no silent fallback.
- Agent autonomy is limited by policy, tool permission, dependency, WIP/capacity and acceptance/evidence gates.

## Testing

- Unit: intent-to-command parsing, policy mapping, proposal idempotency/execute-after-approval, N-week validation, current-week calculation, metric selection/freshness and report narrative facts.
- API: workspace/brain isolation, Snowflake string serialization, approval state machine, automation scheduling/delivery retry, chat structured report and SSE behavior.
- Realtime: LiveKit tool bridge receives scoped report, never announces in inactive session, and UI command opens correct contextual page.
- Flutter: left report panel, center state reset/pin behavior, right chat persistence, timeline N-week rendering, approval state and API failure states.

## Out of Scope

- Reconnecting Flutter to legacy Javis/backend-server/WebSocket services.
- New SQLite state, direct model-provider keys in brain-api, or proactive outbound voice calls.
- Autonomous financial transactions or content publication.
