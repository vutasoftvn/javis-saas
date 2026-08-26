# Điều chỉnh sản phẩm lấy cảm hứng từ QwenWork cho giai đoạn test

**Ngày:** 2026-08-26
**Trạng thái:** Sẵn sàng triển khai sau khi hoàn thành các cổng P0 trong [tái kiểm tra test readiness](/Volumes/SSD/javis-saas/docs/architecture/TEST_READINESS_REAUDIT_2026-08-26.md).
**Phạm vi:** COSA web/Flutter, `apps/cosa`, `packages/agent_core` và `services/cosa`.

## 1. Kết luận điều chỉnh

QwenWork tổ chức trải nghiệm quanh một **agent session trong workspace**: người dùng mô tả công việc, theo dõi tiến trình thực thi, nhận deliverable; skills/connectors được cài ở workspace, account được ủy quyền và chỉ được bật cho session; scheduled task chạy thành một session độc lập. Đây là một mẫu sản phẩm phù hợp với COSA, nhưng không nên sao chép toàn bộ phạm vi nền tảng của họ trong đợt test.

Với code base hiện tại, lựa chọn đúng là:

1. Giữ `ConversationRecord` làm **Agent Session v1**. Một session có đúng một `conversation_id`; không tạo bảng hay ID session thứ hai.
2. Biến run stream hiện có thành timeline người dùng đọc được, có trạng thái, approval và artifact/deliverable.
3. Thêm Connector theo ba bước tách biệt: **install trong workspace → account authorization → grant cho session**. Không lưu access token thô trong PostgreSQL.
4. Thêm lịch chạy nghiệp vụ durable, nhưng chỉ hỗ trợ `one_time`, `daily` và `weekdays` ở v1; mỗi lần chạy tạo run/session execution riêng, không phụ thuộc máy người dùng mở.
5. Mở tính năng bằng feature/capability gate theo workspace; các bề mặt legacy không nằm trong test path phải bị ẩn hoặc từ chối điều hướng.

Điều này mang lại trải nghiệm “giao việc → xem hệ thống làm → duyệt khi cần → nhận kết quả → lặp lại theo lịch”, đồng thời tận dụng được Conversation, durable scheduler, SSE event log và approval engine đã có.

## 2. Bằng chứng tham chiếu và cách áp dụng có chọn lọc

| Quan sát từ QwenWork | Áp dụng trong COSA test | Quyết định phạm vi |
|---|---|---|
| Session là bề mặt thực thi chính, hiển thị event và kết quả. [Workspace agent sessions](https://docs.qwenwork.ai/web/workspace-agent-sessions) | Thêm `SessionView` aggregate từ conversation + run + SSE + artifact. | Làm ngay. |
| Skill dùng trong workspace/session. [Skills](https://docs.qwenwork.ai/features/skills) | Giữ registry/manifest hiện hữu; hiển thị capability đã được cho phép trong SessionView. | Không xây skill marketplace. |
| Connector có install, account authorization và enable cho session. [Connectors](https://docs.qwenwork.ai/features/connectors) | Dùng ba lớp grant và reference tới secret manager. | Chỉ thử một connector sandbox/đọc dữ liệu. |
| Scheduled task chạy trong session độc lập và có lịch sử. [Scheduled tasks](https://docs.qwenwork.ai/web/scheduled-tasks) | Tạo `schedule_execution` bất biến, enqueue vào durable `scheduled_tasks`, ghi kết quả/link run. | Làm v1 với 3 kiểu lịch cố định. |
| File, Drive và Deliverables có lineage. [Files, Drive & Deliverables](https://docs.qwenwork.ai/web/files-drive-deliverables) | Thêm `WorkspaceArtifact` metadata: input attachment, run, output object ref. | Chỉ metadata/object reference, không thay storage provider. |
| Consent, data scope và admin controls là một phần security model. [Privacy & Security](https://docs.qwenwork.ai/getting-started/privacy-security) | Scope connector theo company/workspace/principal/session và kiểm tra expiry ở mọi execution. | Bắt buộc trước connector thật. |

QwenWork có computer control trên desktop, yêu cầu quyền hệ điều hành cao và xác nhận ở nhiều điểm. [Computer Control](https://docs.qwenwork.ai/desktop/computer-use) COSA **không** đưa năng lực này vào đợt test: nó tạo thêm rủi ro permission, audit và blast radius trước khi các cổng P0 hiện tại đã đóng.

## 3. Đích sản phẩm và luồng chuẩn

```text
Người dùng trong Workspace
  → tạo/mở Agent Session (ConversationRecord)
  → gửi nhiệm vụ + attachment
  → durable task / worker tạo Run
  → timeline SSE: started → thinking → tool/approval → completed|failed
  → WorkspaceArtifact gắn vào run/message
  → người dùng mở, tải hoặc dùng artifact cho lượt sau

Connector (nếu có)
  install workspace → account authorization (secret reference) → session grant
  → mỗi tool call kiểm tra scope, expiry, policy và approval

Schedule (nếu có)
  definition enabled → cron dispatcher claim → schedule execution
  → scheduled_tasks → worker → run/session execution → history/artifact
```

### Golden path để nghiệm thu

1. Admin tạo workspace và bật `canonical_sessions`.
2. Người dùng tạo conversation; UI gọi nó là “Agent Session”.
3. Người dùng đính kèm file, gửi nhiệm vụ Operations, thấy timeline realtime và trạng thái terminal.
4. Worker tạo một `WorkspaceArtifact` từ output; artifact hiển thị nguồn run và attachment đầu vào.
5. Người dùng cài connector sandbox, ủy quyền account, bật connector đúng session và thực hiện một action read-only.
6. Người dùng tạo lịch `daily` theo `Asia/Ho_Chi_Minh`, bấm “Run now”, xem execution và run liên kết.
7. Hết hạn credential hoặc bị thu hồi grant: run chuyển `blocked_reauth`, không retry side effect và không lộ secret.

## 4. Ranh giới kiến trúc và ownership

| Thành phần | Owner | Giữ/Thêm | Lý do |
|---|---|---|---|
| Session identity, messages, attachments, UX event stream | `apps/cosa` + `agent_conversation` | Giữ `conversation_id`; thêm SessionView | Conversation substrate đã durable và tenant-scoped. |
| Run, tool ledger, approval, artifacts | `packages/agent_core` | Thêm artifact contract/repository | Đó là state sinh từ runtime, không phải business domain. |
| Connector installation, authorization refs, session grants, schedule definition/execution | `services/cosa` + `control_plane` | Thêm bảng/schema/service/handler | Đây là tenant control và scheduling durable. |
| Công việc business thật | `services/company` | Không thêm dependency mới vào agent core | Giữ rule: `agent_core` không import company. |
| Màn hình session, schedules, settings/gate | `frontend` | Điều chỉnh UI trên canonical routes | Không khôi phục trang legacy như đường test chính. |

### Invariants không được phá

- Một `conversation_id` là định danh duy nhất của Agent Session v1. `RunRecord.session_ref`, nếu dùng, phải bằng chính `conversation_id`.
- Mọi đọc/ghi SessionView, artifact, connector grant và schedule đều lọc đồng thời `company_id` và `workspace_id`; principal chỉ thao tác dữ liệu tenant đã xác thực.
- Event trả ra UI dùng vocabulary `agent_conversation.run_stream_events`; không gộp thẳng với `agent_core.run_events`, vì hai bảng có payload contract khác nhau.
- `object_ref` chỉ là opaque reference. API tuyệt đối không trả secret, provider token, refresh token hoặc presigned URL dài hạn.
- Scheduler chỉ thực thi payload tạo server-side. Client không truyền `target_spec_id`, `company_id`, `principal` hay connector secret reference tùy ý.
- Side effect của connector phải qua policy, approval và idempotency ledger đang có.

## 5. Hợp đồng v1 đề xuất

### 5.1 Session View

`GET /agent/sessions/{conversation_id}` trả aggregate read-only, không tạo persistence table mới.

```json
{
  "id": "conv_abc123",
  "company_id": "company_01",
  "workspace_id": "ws_01",
  "title": "Đối chiếu giao dịch hôm nay",
  "agent_profile": "operations",
  "status": "running",
  "latest_run": {"run_id": "run_01", "status": "RUNNING"},
  "messages": [],
  "timeline": [],
  "artifacts": [],
  "enabled_connector_keys": ["sandbox-read"]
}
```

`GET /agent/sessions/{conversation_id}/timeline?after_sequence=42` only returns allowlisted UX events: `run.started`, `reasoning.status`, `message.started`, `message.delta`, `approval.required`, `approval.resolved`, `run.completed`, `run.failed`. Payload is redacted before serialization; unrecognized event types are omitted and logged server-side.

### 5.2 Artifact lineage

`WorkspaceArtifact` is metadata, not a second object store. Minimum fields:

```text
artifact_id, company_id, workspace_id, conversation_id, run_id,
source_message_id, artifact_kind, display_name, media_type, object_ref,
checksum, size_bytes, status, input_artifact_ids, created_at, archived_at
```

Artifact kinds in v1: `assistant_output`, `report`, `table`, `file_export`. Statuses: `available`, `failed`, `archived`. `source_message_id` and `run_id` make lineage visible. Use `input_artifact_ids JSONB` only for artifact-to-artifact relationships; an attachment remains in the existing `message_attachments` table.

### 5.3 Connector consent

The database separates three entities:

| Entity | Unique scope | Required state |
|---|---|---|
| `workspace_connector_installation` | company + workspace + connector key | `enabled` or `disabled` |
| `connector_authorization` | installation + principal | `active`, `expired`, `revoked` |
| `session_connector_grant` | conversation + authorization | `enabled`, `revoked`, `expired` |

`connector_authorization.secret_ref` points to a selected secret-manager key. It never contains credential material. On each tool call, the capability gateway verifies installation enabled, authorization active/non-expired, session grant enabled/non-expired, required scope in `granted_scopes`, tenant match, then policy/approval. Failure returns a safe `connector_reauth_required` error and records an audit event with IDs only.

### 5.4 Business schedule

Supported `schedule_kind` is deliberately finite:

| Kind | Fields | Example |
|---|---|---|
| `one_time` | `run_at` UTC | Generate a report at 08:00 tomorrow. |
| `daily` | IANA `timezone`, `hour`, `minute` | Every day at 08:30 Asia/Ho_Chi_Minh. |
| `weekdays` | `timezone`, `hour`, `minute`, `weekdays` (1–7) | Mon/Fri at 09:00. |

Each due occurrence creates exactly one `workspace_schedule_execution` with idempotency key `schedule:{definition_id}:{scheduled_for_utc}`. The control plane then creates a low-level `scheduled_tasks` row whose target is fixed to `cosa.schedule-execution`; the worker resolves definition data server-side and creates a new Run. Do not accept free-form cron in v1, and do not reuse a prior interactive conversation as a mutable prompt source. Store an immutable `prompt_template`, `agent_profile`, and connector grant IDs snapshot on the execution.

Execution states: `queued → running → succeeded|failed|blocked_reauth|cancelled`. Schedule definition states: `enabled|paused|archived`.

## 6. Cấu hình test đề xuất

Các key dưới đây là contract cấu hình sẽ được implement; values production dùng secret/config manager, values test là biến môi trường riêng.

| Key | Test value | Mục đích |
|---|---|---|
| `COSA_TEST_CAPABILITY_SET` | `canonical_sessions,artifact_lineage,connector_consent,schedules` | Allowlist UI/API product features theo môi trường. |
| `COSA_CONNECTOR_SECRET_PROVIDER` | `test-vault` | Resolver `secret_ref`; không cho phép inline credential. |
| `COSA_CONNECTOR_ALLOWED_KEYS` | `sandbox-read` | Chỉ bật connector đã review trong test. |
| `COSA_SCHEDULE_MAX_ACTIVE_PER_WORKSPACE` | `10` | Giới hạn schedule enable cùng lúc. |
| `COSA_SCHEDULE_MAX_EXECUTIONS_24H` | `50` | Giới hạn tổng execution để chặn abuse/cost spike. |
| `COSA_SCHEDULE_DISPATCH_BATCH_SIZE` | `25` | Bounded polling mỗi phút. |
| `COSA_SESSION_TIMELINE_PAGE_SIZE` | `100` | Giới hạn replay event từ API. |
| `COSA_ARTIFACT_MAX_SIZE_BYTES` | `26214400` | Chặn metadata liên kết tới object quá lớn ở test. |

Mọi cấu hình trên phải fail closed: thiếu key required ở test/prod thì startup báo lỗi rõ ràng; không tự bật connector hoặc scheduler.

## 7. Thứ tự triển khai và cổng quyết định

| Wave | Nội dung | Điều kiện vào | Cổng ra |
|---|---|---|---|
| 0 | P0 từ tái kiểm tra: strict config, control-plane worker ingress, Postgres test DB | Không có | CI chạy test TS + Python thật, endpoint nội bộ không public. |
| 1 | SessionView + timeline read model | Wave 0 pass | Tenant isolation và redaction test pass. |
| 2 | Artifact lineage | Wave 1 pass | Artifact links đúng run/message, object ref không cross-tenant. |
| 3 | Connector consent sandbox | Wave 0–2 pass | Expiry/revoke chặn tool call, secret không xuất hiện log/API. |
| 4 | Schedule `one_time/daily/weekdays` | Wave 0–3 pass | Crash/retry/idempotency, timezone và reauth blocking pass. |
| 5 | Flutter gate, observability, staged rollout | Wave 1–4 pass | Golden path E2E pass trong workspace pilot. |

Nếu Wave 0 chưa qua, chỉ có thể chuẩn bị schema/test unit cho Wave 1–4; không bật UI route hay API mutation mới trên môi trường test chung.

## 8. Những gì không làm trong đợt này

- Computer/desktop control, browser automation có quyền hệ điều hành.
- Marketplace cài skill/connector từ bên thứ ba, OAuth provider production hoặc token exchange đa nhà cung cấp.
- Arbitrary cron expression, multi-step schedule workflow editor và delivery qua email/slack.
- Billing/credit marketplace; chỉ ghi usage/cost ledger hiện có để quan sát.
- Thay Conversation bằng thực thể Session khác hoặc di chuyển business ownership vào `agent_core`.
- Mở lại frontend legacy direct-call như đường chạy mặc định.

## 9. Chỉ số theo dõi và tiêu chí phát hành pilot

Theo workspace và release flag, ghi dashboard cho: số session tạo/chạy/thất bại, p50/p95 queue delay, time-to-first-event, completion rate, approval wait time, artifact creation rate, connector reauth block rate, schedule lag, duplicate execution count và cross-tenant denial count. Không log raw prompt có dữ liệu nhạy cảm hay credential.

Pilot chỉ mở rộng khi trong 7 ngày: không có cross-tenant access, không có schedule duplicate chưa được idempotency chặn, không có secret leak, >= 95% session có event terminal trong SLO đã chốt, và mọi `blocked_reauth` nhìn thấy được trong UI/history.

## 10. Tài liệu triển khai đi kèm

Kế hoạch file-level, TDD và lệnh verification nằm tại [QwenWork-inspired workspace execution implementation plan](/Volumes/SSD/javis-saas/docs/superpowers/plans/2026-08-26-qwenwork-inspired-workspace-execution.md). Kế hoạch này bổ sung, không thay thế, [test readiness adjustment plan](/Volumes/SSD/javis-saas/docs/architecture/TEST_READINESS_ADJUSTMENT_PLAN_2026-08-26.md) và [re-audit](/Volumes/SSD/javis-saas/docs/architecture/TEST_READINESS_REAUDIT_2026-08-26.md).
