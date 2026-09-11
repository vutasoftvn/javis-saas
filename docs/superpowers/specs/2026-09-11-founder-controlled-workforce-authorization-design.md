# Founder-Controlled Workforce Authorization & Delegation — Design

Ngày: 2026-09-11  
Trạng thái: Implemented — hoàn thành và kiểm chứng qua S9 E2E cross-plane smoke tests và quality gates

## 1. Mục tiêu

Thiết lập một đường quyền duy nhất để founder quản lý role của member và AI
agent trong workspace, trong khi agent vẫn thực thi được phần việc đã ủy quyền.
Business state chỉ đổi tại Company Business Plane; agent không tự cấp quyền,
không tự phê duyệt, không ghi trực tiếp business database.

Kết quả bắt buộc:

1. Founder là chủ thể `HUMAN` duy nhất quản lý role, agent capability grant,
   approval policy, policy overlay và kill switch.
2. Member và agent dùng chung identity workforce, tenant scope và audit model,
   nhưng agent không thể nhận đặc quyền human-only.
3. Agent chỉ thực hiện action là giao của role, exact grant, delegation theo
   run, policy hiện hành và approval khi cần.
4. Flutter hiển thị dữ liệu/quyết định thật của backend. GraphQL chỉ đọc và
   tổng hợp cho UI; command quản trị dùng typed Company API.

## 2. Bối cảnh đã xác minh

Đã có một spine chung: `core.workforce_members` có `member_type` là `HUMAN`
hoặc `AI_AGENT`; `core.workspace_roles`, `core.role_permissions` và
`core.member_role_assignments` dùng `workforce_member_id`. Spec này mở rộng
spine đó, không tạo thêm bảng principal, member hoặc AI identity song song.

Company đã có policy version, scope project/legal entity và permission evaluator.
Agent Platform đã có Capability Gateway, delegation scope
`workspace_id + run_id + capability_ids`, TTL tối đa 600 giây, replay protection,
approval binding và audit run. Các lớp này chưa khép kín vì:

- `requireFounderCommand` hiện chấp nhận `founder` và `co-founder`;
- role assignment chưa chặn `AI_AGENT` nhận role human-only;
- business policy hiểu `permissionKey`, còn runtime gọi `capabilityId`;
- Control Plane có `workspace_agent_policy`, nhưng không được là nguồn sự thật
  quyền nghiệp vụ;
- `require_workspace_operator` cục bộ ở Agent Platform còn cho operator mutate
  cấu hình mà chưa chứng minh founder authority tại Company;
- GraphQL hiện là persisted read boundary, chưa là founder authority read model.

## 3. Quyết định kiến trúc

### 3.1 Subject, membership và role

`WorkforceMember` là authorization subject canonical. `workspace_memberships`
chỉ chứng minh human user thuộc tenant; sau cutover nó không còn tự cấp quyền
founder command. Mọi authority resolve từ active role assignment theo workspace,
project/legal entity và hiệu lực thời gian.

`workspace_roles` có metadata `allowed_member_types`:

| Role class | Subject hợp lệ | Quy tắc |
|---|---|---|
| `founder` system role | `HUMAN` | chỉ role này quản lý authority surface |
| human business role | `HUMAN` | scope/time-bound role nghiệp vụ |
| agent execution role | `AI_AGENT` | trần quyền nghiệp vụ, không là quyền quản trị |
| shared read role | `HUMAN`, `AI_AGENT` | chỉ khi capability catalog cho phép |

Không có role agent tương đương founder, co-founder, admin, approver hay role
manager. Database và Company service phải reject gán `founder` hoặc bất kỳ
human-only role nào cho `AI_AGENT`, không dựa vào UI. Founder cuối cùng không
thể bị revoke, suspend hay đổi thành AI subject.

Founder có thể tạo role custom nhưng không thể đưa các permission authority sau
vào custom role:

```text
authorization.roles.manage
authorization.agent-policy.manage
authorization.capability-grant.manage
authorization.approval-policy.manage
authorization.kill-switch.manage
```

Các permission trên chỉ có system founder role. Co-founder/admin/manager có thể
giữ permission nghiệp vụ trong scope của họ nhưng không mutate authority surface.
Đây không tự thay đổi các command tài chính/vận hành ngoài scope spec này.

### 3.2 Capability bridge và grant agent

Role là điều kiện cần nhưng agent phải có thêm `AgentCapabilityGrant` explicit:

```text
grant_id, workspace_id, agent_workforce_member_id
capability_id, business_permission_key, project_id?, legal_entity_id?
constraints_json, valid_from, valid_until, status
granted_by_founder_member_id, revoked_at, revoke_reason
```

`capability_id` được đăng ký trong capability-permission catalog versioned thuộc
Company contract. Mỗi binding ánh xạ exact `capability_id` sang một
`business_permission_key` và risk class:

```text
READ | INTERNAL_WRITE | EXTERNAL_WRITE | FINANCIAL | LEGAL | AUTHORITY
```

Không client, prompt, AgentSpec hay worker nào tự gửi string capability/
permission tùy ý. Gateway nhận snapshot mapping phiên bản hóa để evaluate đúng
business permission; Company vẫn verify exact capability trong delegation trước
khi side effect. Đây là cầu nối bắt buộc giữa vocabulary `permissionKey` hiện có
và `capabilityId` hiện có.

### 3.3 Công thức effective authority

Mặc định là deny.

```text
Human authority
  = active tenant membership
  ∩ active role assignment in resource scope
  ∩ Company business-policy decision

AI agent authority
  = active AI WorkforceMember + executor assignment
  ∩ active role assignment in resource scope
  ∩ active AgentCapabilityGrant for exact capability
  ∩ capability-permission catalog binding
  ∩ Company business-policy decision
  ∩ Control Plane overlay
  ∩ per-run delegation scope
  ∩ approval state when required
```

`DENY` thắng mọi rule. `REQUIRE_APPROVAL` không thể bị nới thành `ALLOW` bởi
agent, Control Plane hoặc UI. Control Plane overlay chỉ được deny hoặc tăng mức
kiểm soát, không thể cấp business permission mà Company không cấp.

`constraints_json` dùng schema đã đăng ký theo capability: project, legal entity,
amount/currency, connector hoặc recipient allowlist. Thiếu fact cần cho
constraint là deny, không suy luận từ nội dung model.

## 4. Founder command authority

### 4.1 Transaction và audit

Mọi founder command bắt buộc chứa `expectedVersion`, `reason`, `correlationId`
và actor human WorkforceMember. Một transaction phải:

1. xác minh actor là active `HUMAN` founder trong đúng workspace;
2. validate target member type, role/capability, scope, expiry và invariant
   founder cuối cùng;
3. áp dụng mutation cùng append-only authorization event;
4. tăng policy version/authorization epoch atomically;
5. phát outbox invalidation sau commit.

Không partial-commit batch. Conflict trả `VERSION_CONFLICT`; Flutter reload
overview và buộc founder xác nhận lại, không retry mù.

`PUT /identity/permissions` được giữ cho compatibility nhưng phải harden thành
founder-human-only với subject-type guard. Agent grant, approval policy, suspend,
revoke và kill switch dùng typed Company commands; không đi qua raw generic JSON.
Endpoint authority trong `apps/cosa` không được chỉ dựa vào
`require_workspace_operator`: chúng phải delegate đến Company command-authority
boundary hoặc được chuyển về Company.

### 4.2 Audit lifecycle

Thêm append-only `authorization_events` gồm command, actor, target, before/after
hash, reason, policy version/epoch, correlation ID và optional run/tool-call/
evidence reference. Revoke/suspend/retire không hard-delete grant, role history,
run, approval, task hay evidence.

## 5. Luồng AI thực thi, con người kiểm soát

1. Founder cấp agent role và exact `AgentCapabilityGrant` có scope/expiry. Agent
   executor assignment liên kết rõ với WorkforceMember đó.
2. Human manager/founder xác nhận Outcome Contract và work package. AI proposal
   chỉ là `DRAFT`; chỉ contract `CONFIRMED` mới được queue.
3. Worker resolve agent member, assignment/spec/skill pin và policy snapshot ở
   run-start hoặc resume. Thiếu snapshot hợp lệ thì fail closed trước kernel.
4. Gateway kiểm catalog binding, grant, Company rule, Control Plane overlay,
   delegation scope, tenancy, input constraint, readiness và idempotency.
5. Với `EXTERNAL_WRITE`, `FINANCIAL`, `LEGAL`, `AUTHORITY` hoặc rule
   `REQUIRE_APPROVAL`, worker cần authorization ticket một-lần, TTL ngắn, mang
   `run_id + tool_call_id + checkpoint_ref + capability_id + authorizationEpoch`.
6. Approval bind đúng `run_id + tool_call_id + checkpoint_ref`. Approver phải là
   human đủ quyền và không thể là agent/principal đã đề xuất hoặc gọi action.
7. Company capability endpoint verify delegation, ticket, replay/idempotency rồi
   mới thực hiện business mutation trong service transaction.
8. Run audit policy version/epoch, grant IDs, decision, approval, tool call và
   evidence. Founder revoke/suspend/kill; high-risk action chưa có ticket mới
   bị chặn dù run còn snapshot cũ.

Read và low-risk draft dùng snapshot ngắn hạn. Mọi side effect dùng live ticket,
do đó revoke/suspend không phải chờ snapshot hết TTL.

## 6. GraphQL và Founder UI

### 6.1 GraphQL

GraphQL tại `apps/cosa` chỉ thêm persisted read operation
`workspaceAuthorityOverview` khi backend authority đã có. Operation trả role,
member/agent grant, policy version, active run, pending approval và audit summary
trong tenant scope; resolver cũng xác minh founder authority.

GraphQL không có mutation để gán/thu hồi role, đổi grant/policy/approval/budget,
kill agent, queue/cancel/approve run; không nhận raw document hay resolver name
từ client. Các thao tác đó gọi typed Company command API với version/reason/audit.
GraphQL không evaluate policy và không là nguồn sự thật.

### 6.2 Flutter

Founder Authority surface chỉ được đưa vào navigation khi read/command contract
thực thi được. Nó có năm khu vực:

| Khu vực | Nội dung |
|---|---|
| Members | role, scope, hiệu lực của human member; founder gán/thu hồi |
| AI workforce | executor, role, grant, constraint, expiry; founder suspend/revoke |
| Policies | risk class, Company decision, overlay và approval rule |
| Live control | active run/pending approval; revoke, suspend, kill có reason |
| Audit | actor, target, hashes, version, correlation/run/tool/evidence refs |

UI gọi simulation cho subject + capability + scope + facts trước khi commit để
hiển thị `ALLOW`, `DENY` hoặc `REQUIRE_APPROVAL`; server vẫn evaluate lại khi
thực thi. Flutter dùng typed `MvpEndpoint` client cho command và persisted
GraphQL client cho overview. Không thêm literal URL vào allowlist hoặc màn hình
`unavailable` để giả vờ capability đã live.

## 7. Dữ liệu và cutover

Migrations chỉ additive trong release này:

1. `allowed_member_types` cho workspace role;
2. capability-permission catalog/binding versioned;
3. `agent_capability_grants` có scope, expiry, revoke và founder actor;
4. `authorization_events` append-only;
5. authorization epoch/invalidation state để phát ticket live.

Cutover bắt đầu bằng inventory/backfill: mỗi founder hiện hữu phải có active
`HUMAN` WorkforceMember và founder role assignment. Dual-read ghi sai khác giữa
legacy membership-based result và authority resolver mới. Chỉ sau khi không còn
mapping thiếu, role-management command mới switch. Khi đó membership role chỉ
phục vụ tenant compatibility, không cấp founder authority.

## 8. Acceptance evidence

Không coi lint/mock/widget test đơn lẻ là đủ. Trước rollout phải chứng minh:

1. Founder human cấp/thu hồi role đúng scope; co-founder/admin/agent bị từ chối
   mọi authority mutation.
2. Agent không thể nhận founder/human-only role qua API, race hay backfill; không
   thể thu hồi founder cuối cùng.
3. Agent thiếu role, exact grant, catalog binding, business permission hoặc
   delegation đều không chạy capability.
4. Cross-tenant, project/legal scope, expiry và amount/currency constraints fail
   closed.
5. Revoke/suspend sau dispatch nhưng trước high-risk tool call chặn side effect.
6. Approval concurrent, mismatched, stale hoặc self-approval bị từ chối.
7. Duplicate delivery không double side effect; audit ghi chính xác decision.
8. GraphQL overview founder-gated, tenant-isolated, persisted/read-only; raw doc
   và authority mutation bị từ chối.
9. Flutter hiển thị server error/version conflict, không gọi route unavailable.
10. Disposable Postgres/process E2E chứng minh đường thật: founder grant →
    confirmed work package → scheduler/worker → approval hoặc Company mutation
    → outcome/audit, gồm revoke và cross-tenant negative case.

Gate tối thiểu: Company typecheck/tests và boundary checks, Agent Platform tests,
GraphQL tests, Flutter analyze/test, `make frontend-api-contract-check`,
`make contract-freeze-check` và `make e2e-cross-plane-smoke` có credential
Postgres hợp lệ. E2E bị skip hoặc bị môi trường chặn là evidence chưa có.

## 9. Ngoài phạm vi

- Thay toàn bộ role/finance authorization hiện hữu trong một release.
- Agent tự cấp grant, tự promote prompt/model/skill hoặc tự phê duyệt.
- Generic GraphQL write API hoặc policy evaluation ở client.
- Xóa lịch sử role/run/audit/evidence, đổi Workspace/Project lifecycle hoặc tự
  động chuyển stage.
- Mở UI cho capability chưa có backend contract, approval và E2E evidence.
