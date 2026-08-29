# COSA — Code-first audit và kiến trúc mục tiêu cho Workspace, lifecycle, local/cloud và AI workforce

Ngày rà soát: 2026-08-29  
Commit được rà soát: `d6fe04e1`  
Phạm vi: code chạy thực tế trong `services/cosa`, `services/company`, `apps/cosa`, `packages/agent_core`, `frontend`; không dùng các tài liệu `.md` hiện có làm nguồn sự thật. Phần kiến trúc mục tiêu ở nửa sau tài liệu đã được Founder xác nhận qua các vòng review ngày 2026-08-29.

## 0. Các quyết định đã thống nhất

| Mã | Quyết định | Trạng thái |
|---|---|---|
| D-01 | `Workspace` là aggregate root và tenant duy nhất; xóa Company khỏi ownership, tenancy, auth, membership, license, entitlement và policy | Đã chấp thuận |
| D-02 | Workspace lifecycle và Project lifecycle là hai state machine độc lập | Đã chấp thuận |
| D-03 | Workspace có thể tồn tại từ giai đoạn ý tưởng mà không có legal entity; legal entity là child aggregate `0..n` | Đã chấp thuận |
| D-04 | Local là business-data source of truth mặc định; hỗ trợ `REMOTE_ACCESS` và opt-in `CLOUD_CONTINUITY` | Đã chấp thuận |
| D-05 | Tách `local_session_token` và `platform_access_token` theo trust boundary | Đã chấp thuận |
| D-06 | ID persistent domain resource dùng Snowflake `BIGINT`; cùng một `workspace_id` được giữ nguyên xuyên local/cloud | Đã chấp thuận |
| D-07 | `workspace.slug` unique toàn cầu cho subdomain; `workspace.name` là tên hiển thị và không dùng trực tiếp làm DNS identity | Đã chấp thuận |
| D-08 | Một local installation được tạo và vận hành nhiều Workspace Vault độc lập | Đã chấp thuận |
| D-09 | Agent runtime là capability/function-first; CFO/CMO/COO là workforce role/persona hoặc supervisor theo stage, không phải identity kỹ thuật gốc | Đã chấp thuận |

Các quyết định trên thay thế mọi alias hoặc giả định cũ mâu thuẫn trong code/tài liệu trước đây. Chúng không tự động đồng nghĩa code hiện tại đã thực thi đúng; phần gap analysis dưới đây chỉ rõ các cutover còn thiếu.

## 1. Kết luận điều hành

COSA đi đúng hướng của mô hình “AI work environment” trong hình tham chiếu: đã có workspace-scoped tenancy ở Agent Core, execution plane local, control plane cloud, durable runs/checkpoints, policy/approval, outbox, evidence gates, weekly review, finance/legal có draft-confirm và citations.

Tuy nhiên, code hiện tại chưa tạo thành một sản phẩm end-to-end thống nhất. Vấn đề chính không phải thiếu thêm agent hay màn hình, mà là còn nhiều nguồn sự thật song song và hợp đồng giữa các lớp đang lệch nhau:

1. `Company` vẫn tồn tại như aggregate tenancy/auth/policy song song với `Workspace`.
2. Workspace lifecycle vẫn lưu ở cột `company_stage`.
3. Project lifecycle dùng enum và ý nghĩa khác nhau giữa backend và frontend.
4. Một local JWT duy nhất đang bị dùng cho cả local services, AgentOS và platform cloud dù ba nơi không cùng trust boundary.
5. Local/cloud mới thống nhất về hướng triển khai, chưa có mô hình đồng bộ dữ liệu tùy chọn và xử lý xung đột đầy đủ.
6. Một số API finance/legal mới bị frontend rewrite sang route cũ; entitlement backend/frontend trả/đọc khác key.
7. Có các lỗ hổng cross-workspace mutation, internal endpoint và webhook cần xử lý trước test hoàn thiện.
8. Snowflake generator đang dùng node ID ngẫu nhiên theo process, không an toàn cho nhiều local/cloud runtime cùng sinh ID.
9. Local storage mới được scope logic theo `workspace_id`; chưa có Workspace Vault hoàn chỉnh cho file, SOP, key, backup và sync state.
10. Backend agent platform đã capability-first nhưng UI đang hardcode tổ chức CFO/CMO/CTO và fallback khi API workforce không tồn tại.

Khuyến nghị: không sửa tiếp theo kiểu thêm alias. Chọn phương án **Workspace canonical + strangler cutover**, giữ compatibility adapter có thời hạn ở biên, sau đó xóa toàn bộ Company khỏi ownership/tenancy/auth/policy. Song song, xây một Workspace Runtime Fabric duy nhất có ba chế độ vận hành (`LOCAL_ONLY`, `REMOTE_ACCESS`, `CLOUD_CONTINUITY`) và một Workspace Vault độc lập cho từng workspace.

## 2. Đối chiếu hình chiến lược 2026–2030 với code

### 2026 — Hợp nhất hệ sinh thái AI

Hình mô tả một giao diện công việc thống nhất gồm model, dữ liệu doanh nghiệp, công cụ, quyền hạn và human approval.

COSA đã có phần lõi phù hợp:

- Agent Core dùng `workspace_id` làm tenant key duy nhất.
- Local execution plane và platform control plane đã được tách rõ.
- Có outbox, HMAC event intake, inbox idempotency, policy floor và approval.
- Có business modules strategy, operations, sales, marketing, finance và legal.

Khoảng trống: UI, auth, API route và identity model chưa cùng nói một ngôn ngữ Workspace. Vì vậy “hợp nhất” mới đúng ở kiến trúc thành phần, chưa đúng ở hành trình người dùng.

### 2027 — AI thấm vào quy trình lặp lại

COSA đã có stage gates, evidence, next-best-action, weekly review, task/OKR, durable workflow. Đây là nền tảng đúng.

Khoảng trống: lifecycle contract không thống nhất; policy thiếu có thể fail-open; stage override chưa giới hạn vai trò; UI gọi một số route không tồn tại. Chưa nên tăng tự động hóa trước khi ground truth này được khóa.

### 2028 — Quy trình AI-native

Hình yêu cầu dữ liệu → agent thực hiện/xác minh → phân loại rủi ro → tự động hoàn thành hoặc xin phê duyệt.

COSA đã có policy/approval/outbox và finance/legal draft-confirm. Khoảng trống là resource authorization chưa luôn bind vào workspace, approval legal chưa phải approval record thật, webhook có thể fail-open khi thiếu secret.

### 2029 — Tổ chức đa tác tử

Agent Core, durable runs, checkpoints và governance cho thấy COSA đã chuẩn bị đúng nền móng. Nhưng multi-agent chỉ đáng mở rộng sau khi Workspace, lifecycle, identity, policy và audit trail trở thành nguồn sự thật duy nhất.

### 2030 — Nền kinh tế siêu AI công việc

Đây là tầm nhìn dài hạn, chưa phải tiêu chí test hiện tại. Ưu tiên gần nhất nên là reliability, security, evidence và khả năng chạy local độc lập; outcome pricing hoặc autonomous organization nên để sau khi có số liệu vận hành thực.

## 3. Phát hiện code quan trọng

## 3.1 Company chưa bị loại bỏ khỏi lõi

`services/cosa/storage/schema.ts` vẫn có `companies`, `company_memberships`, `company_agent_policy`, license và entitlement theo `company_id`, đồng thời thêm các bảng `platform_workspaces`, `workspace_licenses`, `workspace_entitlements` song song.

`services/cosa/services/auth.service.ts` vẫn nhận `company_name`, `join_company_id`; UI đăng ký chính vẫn gửi các field này và gọi `/platform/auth/companies/create|join`. Workspace provisioning mới chỉ chạy khi không có các tham số company.

Đây là mô hình additive, chưa phải cutover. Việc xóa Company cần thực hiện ở aggregate tenancy/auth/policy; không nên blind-replace các từ “company” hợp lệ trong CRM, ví dụ tên công ty của một khách hàng/counterparty.

## 3.2 Workspace lifecycle vẫn là Company lifecycle đổi tên ở API

`services/company/shared/db/schema/identity.ts` lưu `company_stage` và `venture_stage_entered_at`. API có lúc trả cả `companyStage` lẫn alias `ventureStage`.

Backend lifecycle hiện dùng:

- `S0_GENESIS`
- `S1_PROBLEM_VALIDATION`
- `S2_SOLUTION_VALIDATION`
- `S3_MVP_BUILD`
- `S4_PRODUCT_MARKET_FIT`
- `S5_SCALE`

Các vấn đề cần sửa:

- Không có stage policy thì gate đang pass mặc định.
- Member có quyền write có thể gửi `override: true`; chưa bắt buộc founder/admin và approval/rationale bền vững.
- Chưa có row lock hoặc optimistic version, nên hai transition đồng thời có thể cùng xuất phát từ một stage.
- Chưa định nghĩa rõ same-stage là no-op hay một transition hợp lệ.
- `stageTransitions` cũ thực chất là cấu hình edge/policy nhưng tên giống history journal.

## 3.3 Project lifecycle chưa độc lập và không cùng contract

Backend lưu `projects.phase` dưới dạng varchar tự do, mặc định có nơi là `PLANNING`, nhưng gate evaluation lại coi phase là bộ S0–S5 của Workspace.

Frontend dùng bảy stage S0–S6 với nghĩa khác:

- `S0_EXPLORE`
- `S1_PROBLEM_VALIDATION`
- `S2_SOLUTION_VALIDATION`
- `S3_BUSINESS_VALIDATION`
- `S4_GO_TO_MARKET`
- `S5_OPERATE_GROWTH`
- `S6_SCALE_GOVERN`

Frontend còn gọi `/operations/strategy/stage-context` và `/operations/strategy/projects/:id/stage`, nhưng backend không có các route này; `StrategyService` lại gọi `/strategy/projects...` trong khi project handler hiện nằm dưới `/operations/...`.

Kết luận: Workspace và Project cần hai state machine độc lập, không chỉ hai field khác tên dùng chung mã S0–S5.

## 3.4 Local/cloud đúng hướng nhưng chưa có identity và sync contract thống nhất

Điểm tốt:

- `apps/cosa/config/planes.py` bắt execution plane chạy local trong production.
- `services/company/events/outbox-relay.service.ts` từ chối relay tới target không phải local.
- Agent Core migration 017 đã loại `company_id` và `tenant_id` khỏi tenant-owned records.

Điểm chưa hoàn thiện:

- Cloud workspace và local workspace có hai ID khác nhau; local tạo Snowflake mới rồi lưu `platformWorkspaceId` làm mapping.
- Chưa có một canonical Snowflake `workspace_id` được giữ nguyên xuyên device, local runtime, cloud runtime và event envelope.
- `sync.service.ts` nuốt lỗi khi gọi workspace membership cloud rồi fallback sang company membership; lỗi mạng/auth có thể bị hiểu nhầm thành “không có workspace”.
- Hiện mới là đồng bộ control-plane membership xuống local projection; chưa có optional business-data sync, cursor, revision, conflict hoặc recovery contract.
- Local-only workspace chưa có flow claim/link lên cloud rõ ràng.

## 3.5 Token đang đi sai trust boundary — blocker P0

Sau login platform, frontend gọi `/identity/sync-from-platform`, nhận local JWT rồi ghi đè vào một key `auth_token`. `ApiClient` sau đó dùng token này cho mọi endpoint.

Trong khi đó:

- Local identity verify bằng `JWT_SECRET`.
- AgentOS `apps/cosa/auth/dependency.py` verify bằng `PLATFORM_JWT_SECRET` và audience `cosa`.
- Platform control plane cũng yêu cầu platform token.

Thử nghiệm trực tiếp cho thấy local JWT bị AgentOS từ chối bằng `InvalidPlatformTokenError`. Vì vậy test service riêng lẻ xanh nhưng hành trình sau sync có thể 401 ở AgentOS/cloud.

Ngoài ra local token mặc định sống 8 giờ. Nếu offline lâu hơn mà không có local refresh/unlock/session renewal, lời hứa local-first sẽ bị gãy.

## 3.6 Legal entity đã tách đúng hướng, nhưng approval chưa đủ an toàn

Mô hình `0..n legal_entity_profiles` trên một workspace là đúng: workspace giai đoạn ý tưởng có thể tồn tại mà chưa có pháp nhân. Không nên tạo một “unregistered company” giả.

Cần điều chỉnh:

- Không gộp legal status của nhiều legal entities thành một workspace status bằng cách lấy trạng thái cao nhất.
- Xóa `platformCompanyId` khỏi legal entity.
- Có registration number nhưng đặt trạng thái `REGISTRATION_READINESS` là không rõ nghĩa; nên là `REGISTERED_UNVERIFIED` trước khi xác minh.
- Request verification chưa bắt buộc registration/tax identity.
- Approval ID chỉ là chuỗi random; confirm chỉ kiểm tra prefix `appr_legal_`, chưa có record, expiry, requester/approver separation hoặc binding vào profile/status.

## 3.7 Cross-workspace authorization và webhook — blocker P0

Nhiều handler xác minh người dùng thuộc workspace trong header, nhưng service mutation chỉ query resource theo `id`. Nếu biết ID của resource ở workspace B, thành viên workspace A có thể gửi header A để tác động resource B.

Các điểm đại diện:

- Legal request/apply verification.
- Accounting document confirmation.
- Reconciliation proposal acceptance.
- Workforce member lookup chỉ filter `humanUserId`, không filter workspace dù comment nói đã scoped.

Webhook CAS:

- Chỉ verify signature khi `CAS_WEBHOOK_SECRET` tồn tại; thiếu secret sẽ chấp nhận unsigned webhook.
- Reprocess endpoint public chưa có service/admin authorization rõ ràng.
- Payload tự khai `workspaceId` và `connectionId`; ingestion chưa chứng minh bank connection thuộc workspace đó.

## 3.8 Finance calculation và resource integrity

Financial snapshot hiện cộng toàn bộ IN/OUT lịch sử, lấy net flow làm current cash, lấy tổng burn không theo kỳ, rồi `runway = currentCash / netBurn`; cash-flow-positive trả hard-code 99. Đây không phải runway có thể dùng để ra quyết định.

Reconciliation accept chưa kiểm tra proposal đang pending, document/transaction cùng workspace, document status hợp lệ; `acceptedBy` chưa được ghi dùng. Các quan hệ mới nên có composite FK hoặc service guard theo `(workspace_id, id)`.

## 3.9 UI/API có vertical slices mới nhưng chưa nối kín

- `VentureOnboardingScreen`, `EntitlementProvider`, `ReconciliationCard`, `CitationCard`, `ActionProposalCard` chỉ được tham chiếu trong file định nghĩa/test, chưa vào production flow.
- Onboarding mới gọi register với workspace fields nhưng không gửi email/password mặc định và bỏ `problemStatement`, `targetCustomer`, `goal` nếu không inject callback.
- `EntitlementProvider` đọc `features`/`limits`; backend trả `effectiveFeatures`/`effectiveLimits`.
- `ApiClient.normalizeEndpoint` rewrite `/finance/...` và `/legal/...` sang `/finance-legal/...`, nhưng các API TT58/legal entity mới thực sự được expose dưới `/finance/...` và `/legal/...`.
- Finance/Legal screen chính có route và controller; vấn đề là các vertical slice và endpoint mới chưa nối đúng vào các screen đó.

## 3.10 SnowflakeID chưa đủ an toàn cho multi-node local/cloud

`services/company/shared/services/snowflake.service.ts` và `services/cosa/services/snowflake.service.ts` cùng dùng layout Snowflake 64-bit, nhưng `NODE_ID` được chọn ngẫu nhiên khi process khởi động. Cách này giảm xác suất đụng trong một test/dev process, không tạo được bảo đảm uniqueness khi nhiều local node, cloud runtime hoặc worker cùng hoạt động.

Các hệ quả:

- Process restart có thể nhận node ID khác; hai process có thể nhận cùng node ID.
- Không có generator registration, lease hoặc fencing.
- Platform tạo một Snowflake workspace ID, local lại tạo Snowflake khác và lưu mapping `platformWorkspaceId`; điều này trái với quyết định một workspace identity xuyên hai plane.
- Agent Core vẫn dùng nhiều UUID/prefixed string cho document, chunk, run, conversation và artifact; chưa thống nhất persistent domain entity ID theo quyết định D-06.

Snowflake vẫn là lựa chọn đã chốt, nhưng generator phải trở thành hạ tầng được quản trị: node ID ổn định, được cấp phát, có clock-regression policy, restart test, collision test và JSON serialization dưới dạng string.

## 3.11 Workspace name, slug và subdomain chưa có contract mới

Legacy `companies.slug` có unique constraint, nhưng `platform_workspaces.workspace_name` chỉ là text không unique. Dùng trực tiếp display name làm subdomain không an toàn vì Unicode, khoảng trắng, reserved word, rename và trùng tên hợp lệ.

Contract cần tách:

- `name`: display name, Unicode, có thể đổi; không phải DNS identity.
- `slug`: lowercase ASCII, DNS-safe, unique toàn cầu, được platform giữ chỗ atomically.
- `custom_domain`: optional mapping sau này.
- `workspace_slug_history`: giữ alias/redirect khi đổi slug.

Tích hợp landing page/LadiPage sau này phải tham chiếu `workspace_id` và `slug`, không gắn ownership vào tên hiển thị hay vendor-specific ID.

## 3.12 Multi-workspace local đã có tenancy field nhưng chưa có Workspace Vault

Code hiện đã hỗ trợ một user có nhiều workspace ở identity sync và Workspace Picker. Memory, knowledge, artifacts, runs và conversations phần lớn có `workspace_id`; object ingestion tạo key dạng `quarantine/<workspace>/<ingestion>/...`. Đây là nền tảng tốt.

Những gap còn lại:

- Chưa có local filesystem object-store implementation; production path hiện thiên về S3/MinIO.
- File gốc mới ở quarantine; chưa có lifecycle rõ cho published document, SOP version, archive và trash theo workspace.
- `KnowledgeDocument`/`KnowledgeChunk` mặc định dùng UUID, không theo Snowflake decision.
- `PostgresKnowledgeStore.get_document(doc_id)` lookup chỉ theo document ID, chưa nhận workspace context.
- Vault frontend còn yêu cầu `brain_id`, trong khi backend đã drop các ghost brain fields và không có owner table tương ứng.
- Một số UI/service cache chỉ có một `workspace_id` active; chưa có centralized invalidation khi switch workspace.
- Chưa có per-workspace encryption key, quota, backup manifest, sync cursor và conflict area.

Vì vậy multi-workspace local là khả thi nhưng không thể được coi là hoàn thành chỉ vì các bảng đã có `workspace_id`.

## 3.13 Agent model đang bị chia đôi giữa backend và UI

Backend có cấu trúc phù hợp với function-first:

- `AgentSpec` pin `capability_refs`, skills, model/prompt policy và definition hash.
- `core.workforce_members` tách `agent_spec_id/version` khỏi `role_title`.
- `SupervisorCoordinator` điều phối specialist theo domain; write side-effect có durable supervisor/capability gateway.

Frontend lại hardcode `default12Agents` gồm Founder Copilot, CFO, CMO, CTO, Legal, HR... và hardcode org chart. Các API `/workforce/agents`, `/workforce/packs`, `/workforce/org-chart` được UI gọi nhưng chưa có backend implementation tương ứng; lỗi API bị che bằng fallback tĩnh.

Điều này làm UI trông như có một tổ chức số hoàn chỉnh nhưng không phản ánh AgentSpec đã publish, capability readiness, entitlement, workspace/project stage hoặc governance thật.

## 4. Domain model mục tiêu

## 4.1 Workspace là aggregate root và tenant duy nhất

```text
Workspace
  id                        BIGINT Snowflake, canonical local/cloud
  name                      display name, Unicode, mutable
  slug                      DNS-safe, globally unique khi đã link platform
  status                    ACTIVE | ARCHIVED | SUSPENDED
  lifecycle_stage           W0_IDEA | W1_PROBLEM_VALIDATION |
                            W2_SOLUTION_VALIDATION | W3_MVP_BUILD |
                            W4_PRODUCT_MARKET_FIT | W5_SCALE
  stage_entered_at
  stage_version             optimistic concurrency
  runtime_mode              LOCAL_ONLY | REMOTE_ACCESS | CLOUD_CONTINUITY
  sync_policy               CONTROL_METADATA_ONLY | SELECTIVE_ENCRYPTED |
                            FULL_ENCRYPTED
  sync_status               LOCAL_ONLY | PENDING | IN_SYNC | CONFLICT | ERROR
  primary_legal_entity_id   BIGINT Snowflake nullable
  created_at
  updated_at
  archived_at               nullable
```

Quy tắc bất biến:

- Workspace tồn tại từ lúc có ý tưởng; không phụ thuộc đăng ký kinh doanh.
- `status` là trạng thái vận hành; `lifecycle_stage` là độ trưởng thành. Hai field không suy diễn lẫn nhau.
- Không còn `company_id`, `platform_company_id`, `company_stage`, `workspace_uid` hoặc Company alias trong public/core contract.
- Cùng một Snowflake `workspace_id` được lưu nguyên giá trị ở platform, local runtime, AgentOS, event envelope, backup và sync record.
- Workspace local-only có thể chưa có public slug. Khi link platform, slug được reserve atomically; slug conflict không làm đổi workspace ID.
- `name` không phải DNS identity. Có thể cho phép trùng toàn cầu; UI có thể cảnh báo trùng trong danh sách của cùng user. `slug` mới là field unique phục vụ subdomain.

## 4.2 Workspace lifecycle

```text
W0_IDEA
W1_PROBLEM_VALIDATION
W2_SOLUTION_VALIDATION
W3_MVP_BUILD
W4_PRODUCT_MARKET_FIT
W5_SCALE
```

Mỗi transition cần:

- versioned transition policy;
- evidence snapshot và evaluation result;
- optimistic compare-and-swap theo `stage_version` hoặc row lock;
- actor, rationale, timestamp, source và override approval;
- outbox event ghi cùng transaction;
- same-stage request trả no-op, không tạo history giả.

Missing policy phải fail-closed cho autonomous transition. Human override chỉ dành cho founder/admin hoặc approval workflow hợp lệ; override không xóa kết quả gate mà ghi một quyết định bổ sung có audit.

## 4.3 Project là aggregate con có lifecycle độc lập

```text
Project
  id                    BIGINT Snowflake
  workspace_id          BIGINT Snowflake
  name
  status                ACTIVE | PAUSED | COMPLETED | ARCHIVED
  lifecycle_stage       P0_DISCOVERY | P1_PROBLEM_VALIDATION |
                        P2_SOLUTION_VALIDATION | P3_BUILD_VALIDATE |
                        P4_GO_TO_MARKET | P5_OPERATE_GROWTH |
                        P6_SCALE_GOVERN
  stage_entered_at
  stage_version
```

Quy tắc:

- Dùng prefix `W` và `P` để không thể nhầm enum hoặc ý nghĩa.
- Project transition có policy, evidence và history riêng; không dùng Workspace transition journal.
- Workspace maturity có thể tổng hợp evidence từ portfolio projects, nhưng không tự động bằng stage cao nhất của một project.
- Một workspace W4 có thể chứa project P0; agent composition cho project đó phải dùng cả workspace stage lẫn project stage.

## 4.4 Legal entity là optional child aggregate, không phải tenant

```text
LegalEntityProfile
  id                        BIGINT Snowflake
  workspace_id              BIGINT Snowflake
  status                    DRAFT | REGISTRATION_PREPARATION |
                            REGISTERED_UNVERIFIED | VERIFIED |
                            SUSPENDED | DISSOLVED
  registration_number       nullable
  tax_id                     nullable
  verification_record_id    BIGINT Snowflake nullable
```

Workspace W0–W2 có thể có zero legal entity. Khi có nhiều entity, API trả danh sách và `primary_legal_entity_id`; không tổng hợp một `legalStatus` bằng cách lấy trạng thái cao nhất. Legal verification dùng approval record bền vững, có expiry, separation-of-duty và bind vào `(workspace_id, legal_entity_id, expected_status)`.

## 4.5 SnowflakeID contract

Persistent domain entity ID dùng `BIGINT Snowflake`. Các giá trị sau không bắt buộc Snowflake vì không phải domain entity identity: capability/spec ID có namespace, semantic version, content hash, idempotency key, external provider ID, object URI và encryption key reference.

Generator contract:

- epoch và bit layout được version hóa, không thay âm thầm;
- node/generator ID do registry cấp và lưu ổn định, không chọn random khi process start;
- production process không khởi động nếu thiếu hoặc trùng generator identity;
- có clock-regression handling, sequence exhaustion handling và restart fencing;
- platform workspace creation cấp một Snowflake ID; local reuse ID đó thay vì sinh mapping ID mới;
- node đã được kích hoạt có thể sinh ID khi offline; node chưa từng đăng ký không được hứa khả năng merge collision-free vào cloud;
- mọi Snowflake truyền qua JSON ở dạng decimal string, không dùng JavaScript `Number`.

Current 10-bit random node implementation chỉ phù hợp dev/test. Capacity của bit layout phải được đánh giá trước khi mở Cloud Continuity đại trà; không dùng xác suất random làm uniqueness guarantee.

## 4.6 Slug và subdomain contract

```text
WorkspaceSlug
  workspace_id
  slug                      lowercase ASCII DNS label
  status                    ACTIVE | REDIRECT | RELEASED
  redirect_to_slug          nullable
  reserved_at
  released_at               nullable
```

Quy tắc:

- unique index trên normalized `slug` ở platform;
- chặn reserved names như `admin`, `api`, `app`, `www`, `support`, `assets`;
- slug được derive như gợi ý từ `name`, nhưng user có thể chọn giá trị khác;
- rename tạo slug history/redirect trong retention window, không đổi workspace ID;
- custom domain và LadiPage connector chỉ tham chiếu `workspace_id` + active slug; vendor mapping là integration record, không phải tenant identity;
- local-only workspace có local display name và pending slug request; khi online nếu slug đã bị chiếm, user chọn slug khác.

## 5. Workspace Runtime Fabric: local, remote access và cloud continuity

## 5.1 Ownership của từng plane

Local Workspace Runtime Node sở hữu mặc định:

- business data và Workspace Vault;
- local business services và AgentOS execution;
- durable runs, checkpoints, approvals, artifacts, memory và knowledge index;
- local scheduler, capability gateway và transactional outbox;
- khả năng hoạt động khi cloud unavailable.

Platform cloud sở hữu:

- account identity và platform access session;
- workspace registry, slug reservation, membership projection;
- license, entitlement và connector policy/control metadata;
- runtime node registration/presence;
- secure relay routing;
- optional encrypted sync/backup và Cloud Workspace Runtime allocation.

Central control plane không trực tiếp trở thành shared business execution plane.

## 5.2 Hai token, hai trust boundary

- `local_session_token`: local identity, local business services, local AgentOS và local relay endpoint.
- `platform_access_token`: cloud identity, platform registry, entitlement, relay signaling và cloud runtime allocation.

API client chọn token theo resolved target/base URL, không chỉ theo path text. Hai token được lưu bằng key riêng. Local session cần refresh/desktop unlock độc lập để workspace vẫn dùng được offline sau TTL; platform token hết hạn không khóa local data đã được cấp quyền trước đó.

## 5.3 Ba user-facing runtime mode

| Mode | Local node | Execution | Business data |
|---|---|---|---|
| `LOCAL_ONLY` | Phải có | Local | Chỉ local; platform chỉ có metadata tối thiểu nếu workspace đã đăng ký |
| `REMOTE_ACCESS` | Phải online | Local qua secure relay | Vẫn ở local; cloud chỉ route encrypted traffic |
| `CLOUD_CONTINUITY` | Có thể tắt | Local preferred, cloud standby có điều kiện | Module được chọn sync mã hóa lên cloud runtime store |

`REMOTE_ACCESS` giải quyết truy cập từ xa khi máy local đang chạy. `CLOUD_CONTINUITY` giải quyết điều hành khi local node tắt. Không dùng một cờ `online=true` vì hai nhu cầu có data-residency và failure semantics khác nhau.

## 5.4 Request routing

```text
Web/Mobile/Desktop
        |
        v
Platform Gateway / Runtime Router
        |
        +--> Secure relay --> Local Workspace Runtime Node
        |
        +--> Isolated Cloud Workspace Runtime Node
```

Runtime Router resolve theo `workspace_id`, membership, runtime mode, node presence, execution lease và sync freshness. Cloud runtime là cùng runtime artifact/deployment contract với local nhưng chạy trong isolation scope của một workspace; không dùng shared global AgentOS state.

## 5.5 Single-writer execution lease và split-brain protection

```text
WorkspaceExecutionLease
  workspace_id
  active_runtime_node_id
  lease_epoch
  fencing_token
  lease_expires_at
  last_heartbeat_at
  last_sync_cursor
```

Quy tắc:

- một workspace chỉ có một write-authoritative runtime tại một thời điểm;
- mọi durable write/run completion kèm fencing token;
- cloud chỉ promote nếu local lease hết hạn và sync freshness đáp ứng policy;
- local quay lại phải acquire epoch mới, không tiếp tục ghi từ lease cũ;
- finance/legal có thể đặt `failover_policy=MANUAL` hoặc freshness threshold nghiêm ngặt;
- read-only stale view phải hiển thị rõ `as_of` và không giả vờ dữ liệu live.

## 5.6 Đồng bộ tùy chọn theo aggregate

Không replicate database row trực tiếp. Dùng sync envelope:

```text
workspace_id              Snowflake
entity_type
entity_id                 Snowflake với domain entity
revision
base_revision
source_runtime_node_id    Snowflake
occurred_at
idempotency_key
payload_hash
encryption_key_ref
encrypted_payload
```

Sync scopes:

- control metadata: sync khi workspace link platform;
- business modules: opt-in theo module và workspace;
- finance/legal: optimistic revision, conflict cần human resolve;
- credentials: không sync raw secret; chỉ sync connector grant handle hoặc cấp cloud secret riêng;
- runs/memory/artifacts: local mặc định, optional encrypted backup/sync riêng;
- quarantine/temp/cache: không sync.

Phải tách `agent_execution_outbox` khỏi `cloud_sync_outbox`; execution, sync và backup là ba pipeline khác nhau, có retry/dead-letter/retention riêng.

## 5.7 Failure semantics

- Platform unavailable: local mode tiếp tục; platform actions được queue hoặc báo unavailable, không fallback sang legacy Company.
- Local unavailable trong `REMOTE_ACCESS`: UI báo node offline/read-only; không âm thầm chạy cloud.
- Local unavailable trong `CLOUD_CONTINUITY`: chỉ promote cloud khi lease và freshness gate pass.
- Conflict: không dùng generic last-write-wins cho finance, legal, approval, lifecycle hoặc policy.
- Missing workspace key: fail-closed và hướng dẫn recovery; không tạo vault rỗng mới cùng ID.
- Connector chỉ có local credential: cloud runtime đánh dấu capability `MISSING_CREDENTIAL`, không giả lập thành công.

## 6. Multi-workspace local và Workspace Vault

## 6.1 Lựa chọn isolation

### A. Chỉ phân vùng logic bằng `workspace_id`

Nhẹ và gần code hiện tại, nhưng file, cache, key, backup và path traversal vẫn có thể tạo cross-workspace leak. Không đủ cho dữ liệu SOP/tài chính/pháp lý.

### B. Workspace Vault trên shared Runtime Host — khuyến nghị

File/object, encryption key, sync state, quota và backup tách theo workspace. PostgreSQL local dùng chung nhưng có `workspace_id`, composite FK và Row-Level Security. Cân bằng tốt nhất giữa isolation, tài nguyên và migration.

### C. Một full runtime stack cho mỗi workspace

Mỗi workspace có Postgres, object store, AgentOS và containers riêng. Isolation mạnh nhất nhưng tốn RAM/CPU, migration và vận hành. Chỉ nên là optional high-isolation/enterprise mode, không phải default.

## 6.2 Runtime Host và storage layout

```text
<COSA_DATA_ROOT>/
  host/
    catalog/
    runtime-node/
    logs/

  workspaces/
    <workspace_snowflake_id>/
      manifest.json

      vault/
        documents/
          <document_id>/versions/<version_id>/
            source
            normalized
            manifest.json
        sops/
          <sop_id>/versions/<version_id>/
        attachments/
        artifacts/

      knowledge/
        snapshots/
        indexes/

      quarantine/
      exports/
      temp/

      sync/
        outbox/
        inbox/
        conflicts/
        checkpoints/

      backup/
```

`manifest.json` chỉ chứa non-secret metadata tối thiểu, schema version, workspace ID, checksums và key reference. Không chứa plaintext workspace key/token.

## 6.3 WorkspaceObjectStore abstraction

Business code không ghép raw filesystem path. Interface nhận authenticated workspace context và opaque object ID:

```text
put(workspace_id, object_kind, object_id, version_id, stream)
get(workspace_id, object_ref)
archive(workspace_id, object_ref)
delete_after_retention(workspace_id, object_ref)
list_versions(workspace_id, object_id)
```

Implementations:

- `LocalFilesystemWorkspaceStore` cho managed local directory;
- `S3WorkspaceStore` cho local MinIO hoặc cloud S3-compatible store.

Object key chuẩn:

```text
workspaces/<workspace_id>/<kind>/<object_id>/versions/<version_id>/<blob>
```

Không deduplicate blob xuyên workspace mặc định vì hash/refcount dùng chung làm yếu isolation. Có thể deduplicate bên trong một workspace.

## 6.4 Relational metadata và vector index

Default không tạo một PostgreSQL instance cho mỗi workspace. Dùng một local Postgres cluster với:

- `workspace_id BIGINT NOT NULL` trên mọi tenant-owned row;
- lookup/mutation theo `(workspace_id, resource_id)`;
- composite unique/FK bảo đảm linked resources cùng workspace;
- Row-Level Security dùng transaction-local workspace context;
- connection pool reset context khi trả connection;
- indexes bắt đầu bằng `workspace_id` cho query tenant-scoped;
- pgvector search bắt buộc filter workspace trước khi trả result.

Ví dụ RLS policy:

```sql
USING (
  workspace_id = current_setting('cosa.workspace_id')::bigint
)
```

Per-workspace table partition/vector index chỉ mở khi đo được nhu cầu; không tạo động cho mọi workspace ngay từ đầu.

## 6.5 Document và SOP lifecycle

Document lifecycle:

```text
QUARANTINED -> SCANNED -> REVIEW_PENDING -> PUBLISHED -> ARCHIVED -> PURGED
```

Sau publish, file nguồn được chuyển/copy có kiểm chứng từ quarantine vào Workspace Vault; `source_uri` phải chứa workspace/object identity, không dùng URI thiếu workspace.

SOP là first-class resource, không chỉ là một knowledge file:

```text
SopDefinition
  id                    Snowflake
  workspace_id
  title
  owner_member_id
  status                DRAFT | REVIEW | ACTIVE | RETIRED
  current_version_id
  risk_class
  approval_policy

SopVersion
  id                    Snowflake
  workspace_id
  sop_id
  content_object_ref
  normalized_object_ref
  checksum
  effective_from
  approved_by
```

Chỉ SOP `ACTIVE` mới được đưa vào procedural instructions/capability context. Draft/review content không được agent coi là policy đang có hiệu lực.

## 6.6 Encryption và key isolation

- master device key lưu trong OS Keychain/Keystore/Secure Enclave khi có;
- mỗi workspace có Data Encryption Key riêng;
- workspace DEK được envelope-encrypt bởi device/user key;
- object, backup và sync payload dùng workspace-scoped key/version;
- switch workspace unload key, cache và realtime subscription của workspace cũ;
- key rotation có resumable re-encryption journal;
- xóa workspace chỉ destroy key sau retention/recovery window.

Local OS administrator vẫn là một threat model riêng; nếu cần chống cả host admin, phải dùng user-held passphrase/hardware key và chấp nhận giới hạn background automation.

## 6.7 Workspace switch và concurrent background work

`active_workspace_id` là UI context, không phải global backend state. Backend scheduler có thể tiếp tục chạy workspace B khi user đang xem workspace A.

Workspace switch phải:

1. chặn request mới của workspace cũ;
2. cancel/close realtime subscriptions và pending streams;
3. clear controllers, cached entitlement, knowledge results, role và project selection;
4. load membership, key và runtime status của workspace mới;
5. thiết lập local session context;
6. refetch dữ liệu thay vì tái sử dụng object cache không có workspace key.

Queue, compute budget, connector quota, agent concurrency và storage quota tách theo workspace để một workspace không làm đói tài nguyên của workspace khác.

## 6.8 Per-workspace backup, export, restore và sync

Backup package gồm:

- signed/encrypted manifest;
- schema version và workspace ID;
- relational snapshot đã filter workspace;
- encrypted object versions;
- knowledge/SOP version metadata;
- sync cursor/conflict state cần thiết;
- checksums và key-wrapping metadata.

Cho phép backup/export/restore một workspace mà không đọc hoặc khóa workspace khác. Restore cùng ID phải kiểm tra collision/ownership; clone workspace phải tạo Snowflake ID mới và rewrite internal references theo migration map.

Mỗi workspace chọn runtime/sync mode độc lập: trên cùng máy, workspace A có thể `LOCAL_ONLY`, B `REMOTE_ACCESS`, C `CLOUD_CONTINUITY`.

## 6.9 Workspace Vault security invariants

- không nhận raw absolute path từ client;
- canonicalize path, chặn `..`, symlink/hardlink escape và case-fold collision;
- mọi object metadata chứa workspace ID và checksum;
- delete/restore/version APIs bind `(workspace_id, object_id)`;
- knowledge, memory và artifact caches key theo workspace;
- temp/quarantine cleanup không đi ra ngoài workspace root;
- cross-workspace export, search, citation, backup và restore có negative tests bắt buộc.

## 7. AI workforce operating model

## 7.1 Ba phương án

### A. C-suite agent là canonical AgentSpec

UX dễ hiểu nhưng capability quá rộng, khó test/version, dễ tạo ảo giác thẩm quyền và không phù hợp workspace giai đoạn ý tưởng. Không khuyến nghị.

### B. Chỉ hiển thị functional specialist

Kỹ thuật sạch và governance rõ nhưng người dùng khó hình dung tổ chức ở giai đoạn trưởng thành.

### C. Function/capability-first + role/persona overlay — khuyến nghị

AgentSpec kỹ thuật đại diện một chức năng hoặc bounded job-to-be-done. Workforce assignment đặt role title như Finance Copilot, CFO, CMO, COO hoặc Chief of Staff tùy workspace stage và cấu hình; title không đổi capability set hay quyền phê duyệt.

## 7.2 Ba lớp identity

```text
Capability
  finance.transaction.read
  finance.cashflow.forecast
  finance.payment.propose
  marketing.campaign.plan
  legal.obligation.assess

Functional AgentSpec
  Cashflow Planner
  Accounting Document Specialist
  Market Research Specialist
  Campaign Planner
  Compliance Analyst

Workforce Assignment / Persona
  Finance Copilot
  CFO
  CMO
  COO
  Chief of Staff
```

`agent_spec_id + version + definition_hash` là execution identity. `role_title`, display name, department và manager là workspace-level presentation/organization metadata.

## 7.3 Composition theo Workspace và Project lifecycle

Gợi ý default packs:

| Workspace stage | Workforce trọng tâm |
|---|---|
| W0–W1 | Founder Office/Chief of Staff, Problem Research, Evidence Analyst, Finance Basics, Legal Readiness |
| W2 | Solution Validation, Experiment Designer, Pricing/Offer, Market Research |
| W3 | Product Delivery, Growth Experiment, Sales Pipeline, Accounting Operations, Customer Support |
| W4 | Revenue Operations, Marketing Operations, Customer Success, Finance Controller, Compliance |
| W5 | Domain supervisors có thể dùng persona CFO/CMO/COO; specialist hierarchy, budget/quorum và workforce governance |

Agent eligibility không chỉ theo stage:

```text
eligible = workspace_stage_policy
         + project_stage_policy
         + entitlement
         + capability_readiness
         + connector/data availability
         + risk/approval policy
```

Một project P0 trong workspace W4 vẫn nhận Discovery/Research composition cho project context đó.

## 7.4 Governance: title không cấp quyền

- CFO Agent không tự approve payment chỉ vì có title CFO.
- CMO Agent không tự publish/spend campaign nếu capability/policy yêu cầu human approval.
- High-risk approval phải resolve tới human principal/role hoặc quorum policy đã xác minh.
- Agent write luôn qua Capability Gateway, idempotency và durable approval.
- C-suite AI có thể tổng hợp, đề xuất, giám sát và phân công; accountability pháp lý cuối cùng vẫn thuộc con người được ủy quyền.
- Role/title change không được silent-widen AgentSpec capability; mọi capability change tạo spec/version/hash mới.

## 7.5 Workforce registry và UI contract

Backend cần source of truth gồm:

- published AgentSpec registry;
- workspace workforce assignments;
- role/persona/manager hierarchy;
- capability readiness;
- entitlement và stage eligibility;
- active runs, health, budget và approval queue.

Các API `/workforce/agents`, `/workforce/packs`, `/workforce/org-chart` phải được triển khai từ dữ liệu trên. Production UI không fallback sang `default12Agents`; nếu backend unavailable, hiển thị unavailable/stale state rõ ràng.

## 7.6 Đối chiếu tầm nhìn 2030

Hình 2030 mô tả AI coworker đáng tin cậy, công việc tự động theo mục tiêu, quyết định thời gian thực, con người tập trung chiến lược và governance tích hợp. Cấu trúc function-first phù hợp hơn việc dựng một “ban C-level giả” từ đầu: capability nhỏ tạo trust, domain supervisor tạo coordination, C-suite persona chỉ xuất hiện khi tổ chức đủ trưởng thành và có governance tương ứng.

## 8. Ba phương án cutover Company -> Workspace

### A. Giữ Company và thêm alias Workspace

Nhanh nhất nhưng tiếp tục tạo hai nguồn sự thật, tăng chi phí test và migration. Không khuyến nghị.

### B. Workspace canonical + strangler cutover — khuyến nghị

Định nghĩa schema/API Workspace canonical, thêm compatibility adapter chỉ ở biên, migrate dữ liệu có kiểm chứng, chuyển từng consumer, chặn write legacy, rồi drop Company. Cân bằng tốt nhất giữa an toàn và độ sạch.

### C. Big-bang rewrite

Schema sạch nhanh nhưng rủi ro downtime, rollback và mất hành vi ngầm lớn. Không phù hợp trước giai đoạn test hoàn thiện.

## 9. Lộ trình triển khai đề xuất

Không thực hiện như một big-bang feature. Mỗi phase có migration gate, contract tests, rollback và shadow comparison riêng.

## 9.0 Contract freeze trước khi sửa schema

1. Publish canonical vocabulary: Workspace, Workspace Member, Workspace Runtime Node, Workspace Vault, Workspace/Project lifecycle, Legal Entity, Functional Agent, Workforce Role.
2. Publish canonical JSON/API enums W0–W5, P0–P6 và runtime/sync modes.
3. Lập route inventory từ frontend tới backend; chặn tạo route alias mới.
4. Lập Company read/write inventory, phân biệt legacy tenancy với từ “company” hợp lệ trong CRM/counterparty.
5. Chốt Snowflake generator contract, node allocation và serialization.
6. Chốt workspace slug normalization/reserved-list contract.

Exit gate: contract tests tồn tại cho enum, ID, slug và target routing trước migration dữ liệu.

## 9.1 P0 security và trust-boundary closure

1. Tách platform/local token storage; route token theo resolved target.
2. Cho local AgentOS verify local session hoặc introspect local identity; platform chỉ nhận platform token.
3. Bind mọi resource mutation bằng `(workspace_id, resource_id)` và composite resource validation.
4. Scope workforce member lookup theo workspace.
5. Bảo vệ internal workspace endpoints bằng service identity/token hoặc mTLS.
6. CAS webhook secret fail-closed ở staging/prod; bind bank connection vào workspace; bảo vệ reprocess.
7. Legal approval thành durable approval record thật.
8. Missing agent/stage policy fail-closed theo risk class.

Exit gate: cross-tenant negative suite và trust-boundary E2E pass; không còn public unauthenticated internal mutation.

## 9.2 Workspace canonical, Snowflake và slug cutover

1. Thêm canonical fields: `id`, `name`, `slug`, `status`, `lifecycle_stage`, `stage_version`, `runtime_mode`, `sync_policy`, `sync_status`.
2. Tạo generator registry; loại random production `NODE_ID`.
3. Tạo `workspace_id_map(old_local_id, canonical_workspace_id)` cho workspace đã sync theo mô hình hai ID.
4. Chọn platform Snowflake workspace ID làm canonical cho workspace đã đăng ký; update toàn bộ local FK theo migration transaction/batch có validation.
5. Workspace local-only giữ Snowflake ID gốc; khi link platform, platform adopt ID sau proof/generator validation.
6. Chuyển auth/register/join/membership/license/entitlement/policy sang Workspace.
7. Reserve slug atomically; tạo reserved list và slug history.
8. Chặn Company write, chạy shadow read comparison, rồi drop Company tenancy tables/fields/routes.
9. Chỉ đổi tên physical folder/service/env `company` sau domain cutover để diff cơ học không che logic lỗi.

Exit gate: một user tạo/chọn nhiều workspace; cùng workspace ID xuất hiện xuyên platform/local/AgentOS; zero mismatch ở membership/license/policy reconciliation.

## 9.3 Workspace Vault multi-workspace local

1. Tạo Runtime Host Catalog và Workspace Vault manifest.
2. Bổ sung `WorkspaceObjectStore` với local filesystem và S3-compatible implementations.
3. Migrate object key sang `workspaces/<workspace_id>/...`.
4. Chuyển document lifecycle từ quarantine sang versioned published storage.
5. Tạo first-class SOP Definition/Version/approval lifecycle.
6. Bổ sung per-workspace DEK, key rotation journal, quota và cleanup.
7. Bật RLS/composite FK cho tenant-owned relational tables; sửa knowledge lookup nhận workspace context.
8. Xóa `brain_id` khỏi frontend auth, Vault, chat và marketing compatibility paths; Workspace là knowledge/vault scope duy nhất.
9. Xây runtime workspace switcher và centralized cache/subscription invalidation.
10. Tạo per-workspace backup/export/restore.

Exit gate: hai workspace trên cùng local host không thể đọc/search/export/restore dữ liệu của nhau; background run vẫn đúng workspace khi UI switch.

## 9.4 Workspace và Project lifecycle

1. Rename/drop physical `company_stage`; backfill `workspace_lifecycle_stage`.
2. Workspace W0–W5 transition dùng CAS/lock, immutable journal và versioned policy.
3. Project P0–P6 fields, transition journal và gate policy độc lập.
4. Sửa toàn bộ frontend/backend route và enum contract.
5. Legal entity status và durable verification approval tách khỏi Workspace stage.
6. Agent eligibility đọc cả workspace/project stage nhưng không tự transition stage.

Exit gate: concurrent transition tests, round-trip enum tests và independence tests pass.

## 9.5 Remote Access

1. Runtime node registration, device key và heartbeat.
2. Secure outbound tunnel/relay; không mở raw local port ra internet.
3. Runtime Router resolve workspace membership và active local node.
4. End-to-end authenticated command envelope, replay protection và audit.
5. Offline/stale UI semantics; không cloud fallback nếu mode chỉ `REMOTE_ACCESS`.

Exit gate: truy cập web/mobile từ xa chạy task trên local node; tắt local node tạo trạng thái offline rõ ràng và không chạy nơi khác.

## 9.6 Cloud Continuity

1. Cloud Workspace Runtime deployment profile tách khỏi central control plane.
2. Encrypted selective sync, cursor, conflict queue và recovery.
3. Workspace execution lease, epoch và fencing token.
4. Local-preferred routing, cloud promotion/demotion và split-brain recovery.
5. Per-module failover/freshness policy; finance/legal manual gate mặc định.
6. Cloud connector grants riêng; không copy raw local credential.

Exit gate: local-off continuation pass, stale-write rejection pass, split-brain chaos test pass và no-plaintext-sync verification pass.

## 9.7 AI workforce và UI integration

1. Chuẩn hóa functional AgentSpec catalog và capability boundaries.
2. Tạo workspace workforce assignment/persona/manager model từ registry thật.
3. Triển khai `/workforce/agents`, `/workforce/packs`, `/workforce/org-chart`, readiness và budget endpoints.
4. Bỏ `default12Agents` khỏi production fallback.
5. Stage-aware composition, entitlement và connector readiness.
6. Founder Office/Chief of Staff orchestration; C-suite persona chỉ là role overlay theo stage.
7. Nối onboarding, entitlement, reconciliation, citation và action proposal vào production flows.
8. Sinh client hoặc contract-test API để ngăn route drift.

Exit gate: org chart phản ánh registry/workforce thật; title change không đổi capability; high-risk action vẫn cần human approval.

## 10. Test matrix trước khi gọi là “hoàn thiện”

## 10.1 Snowflake và slug

- Generator restart giữ node identity và không collision.
- Hai node/process không thể đăng ký cùng generator ID.
- Clock regression không tạo duplicate hoặc ID đi ngược contract.
- Sequence exhaustion được block/retry đúng.
- JSON round-trip không mất precision trên Dart, TypeScript và Python.
- Platform/local/AgentOS/event/backup dùng cùng workspace ID.
- Slug normalization, reserved word, case-fold và concurrent reservation tests.
- Rename slug giữ workspace ID và redirect history đúng.

## 10.2 Domain và Company migration

- Tạo workspace W0 khi chưa có legal entity.
- Migrate Company → Workspace giữ membership, role, policy, license và entitlement.
- Hai-ID workspace cũ được remap toàn bộ FK không orphan.
- Legacy Company write bị chặn; reconciliation report zero mismatch trước drop.
- CRM counterparty/company name hợp lệ không bị xóa nhầm.

## 10.3 Multi-workspace Workspace Vault

- Một local installation tạo, mở, archive và restore nhiều workspace.
- Workspace A không đọc/list/search/cite/export object, SOP, knowledge, memory hoặc artifact của B.
- Path traversal, symlink, hardlink, Unicode/case-fold escape bị chặn.
- Knowledge lookup bắt buộc workspace ID; vector search không leak result.
- Workspace switch clear cache, role, entitlement, project và realtime subscriptions.
- Background agent của B tiếp tục đúng context khi UI đang ở A.
- Storage/compute/connector quota của A không làm nghẽn B ngoài host-level policy.
- Backup A không chứa metadata/hash/key của B; restore A không khóa hoặc mutate B.
- Key rotation/resume và retention/key-destruction tests.
- Chỉ SOP ACTIVE được dùng làm procedural instruction.

## 10.4 Auth và trust boundary

- Platform token chỉ đi platform; local token chỉ đi local/AgentOS.
- Token không được gửi nhầm khi endpoint normalize/redirect.
- Local app hoạt động khi platform unavailable.
- Offline local session renewal hoạt động sau TTL hiện tại.
- Cloud membership timeout không fallback thành Company membership.
- Link/claim/retry idempotent; `clientCreationId` không rò workspace user khác.

## 10.5 Remote Access và Cloud Continuity

- Remote browser → relay → local runtime giữ đúng workspace/principal.
- Local offline trong `REMOTE_ACCESS` không tự cloud execute.
- `CLOUD_CONTINUITY` chỉ promote khi lease hết và sync freshness pass.
- Local/cloud concurrent write chỉ active fencing token thắng.
- Local reconnect với stale epoch bị reject.
- Finance/legal stale cloud state chuyển manual/read-only theo policy.
- Encrypted sync không để plaintext business payload/control-plane logs.
- Conflict recovery giữ đủ audit và không generic last-write-wins dữ liệu critical.
- Mỗi workspace trên cùng host có runtime/sync policy độc lập.

## 10.6 Security

- Với mỗi finance/legal/operations/commercial/knowledge resource, user workspace A không thể read/write ID workspace B.
- Legal approval đúng workspace, profile, expected state, approver và expiry.
- Unsigned webhook bị reject trong staging/prod.
- Bank connection/workspace mismatch bị reject.
- Internal sync endpoint không nhận public/user token.
- Workspace keys/tokens không xuất hiện trong manifest, log, event hoặc backup plaintext.

## 10.7 Lifecycle và legal

- Missing policy không cho autonomous transition.
- Hai transition đồng thời chỉ một transition thắng.
- Same-stage là no-op rõ ràng.
- Override chỉ founder/admin hoặc approval workflow hợp lệ.
- Frontend/backend round-trip mọi enum W0–W5 và P0–P6.
- Workspace stage không tự đổi khi legal entity đăng ký/xác minh.
- Project stage không tự đổi Workspace stage và ngược lại.

## 10.8 AI workforce

- Agent selection dùng workspace stage + project stage + entitlement + readiness + risk.
- Role/title change không làm capability widen.
- CFO/CMO AI không tự approve high-risk action.
- Org chart và packs lấy từ backend source of truth, không hardcoded fallback.
- AgentSpec/version/hash pin trong run manifest và resolve lại được lịch sử.
- Cloud/local runtime resolve cùng AgentSpec/policy version cho cùng mission.

## 10.9 API/UI

- Contract test cho toàn bộ route production UI sử dụng.
- Entitlement đọc đúng `effectiveFeatures/effectiveLimits`.
- Onboarding tạo account + workspace + venture profile + evidence seed.
- Workspace picker/switcher hiển thị runtime mode, sync status và last sync.
- Vault không còn `brain_id`; document/SOP flows workspace-native.
- Reconciliation/citation/action proposal test từ screen → controller → API → DB/outbox.
- UI không biến network/backend failure thành fallback “thành công” hoặc fake workforce.

## 10.10 Recovery, performance và operability

- Crash/restart giữa upload, ingest, publish, sync, key rotation và failover có resume/idempotency.
- Nhiều workspace không tạo connection pool/container không giới hạn.
- Lazy-load Workspace Vault và per-workspace resource budget.
- Backup/restore compatibility theo schema version.
- Metrics/log/traces có workspace ID nhưng không chứa sensitive payload.
- Runbook xử lý node lost, key recovery, slug takeover dispute, sync conflict và failed Company migration.

## 11. Bằng chứng kiểm thử tại thời điểm audit

- `services/cosa`: typecheck và 91/91 tests pass.
- `services/company`: typecheck và 415/415 tests pass.
- AgentOS/COSA targeted Python: 29/29 tests pass.
- Flutter targeted widgets: 7/7 tests pass.
- `flutter analyze --no-pub`: exit 1 với 7 lint infos (2 null-aware suggestions, 5 `withOpacity` deprecated).
- Direct trust-boundary probe: local JWT bị AgentOS từ chối bằng `InvalidPlatformTokenError` như verifier hiện tại.

Các kết quả xanh trên chứng minh component behavior tương ứng, không chứng minh hành trình end-to-end hoặc kiến trúc mục tiêu đã được triển khai. Readiness gate phải dựa vào mục 10.

## 12. Implementation guardrails và phạm vi chưa làm

Các quyết định kiến trúc đã được khóa ở mục 0. Trước khi viết implementation plan, cần giữ các guardrail:

1. Không tạo thêm Company alias, `brain_id`, `workspace_uid` hoặc parallel tenancy source.
2. Không đổi toàn bộ từ “company” máy móc; giữ thuật ngữ hợp lệ cho customer/counterparty, nhưng xóa Company aggregate khỏi core.
3. Không biến central platform control plane thành shared business execution database/runtime.
4. Không gọi row-prefix là physical isolation; Workspace Vault phải bao gồm file, key, cache, backup và sync state.
5. Không dùng C-suite title làm authorization hoặc approval principal cho AI.
6. Không dùng random node ID cho production Snowflake.
7. Không cloud-failover khi user chỉ bật Remote Access.
8. Không sync raw credentials hoặc dùng generic last-write-wins cho dữ liệu critical.
9. Không drop legacy trước khi có shadow comparison, reconciliation report và rollback checkpoint.
10. Không tuyên bố “test hoàn thiện” chỉ dựa vào component tests đang xanh.

Ngoài phạm vi gần:

- outcome-based pricing hoặc “AI company tự trị hoàn toàn” của tầm nhìn 2030;
- full runtime stack mặc định cho từng workspace;
- generic cross-workspace blob deduplication;
- tự động cấp quyền pháp lý cho AI C-suite;
- public custom-domain/LadiPage implementation trước khi slug/ownership contract hoàn tất.

## 13. Definition of Ready và Definition of Done

### Ready để bắt đầu integrated test hoàn thiện

- P0 security/trust boundary đã đóng.
- Canonical Workspace/Project enums, Snowflake và route contracts đã publish.
- Company migration inventory và rollback map có đủ.
- Multi-workspace isolation test harness có ít nhất hai workspace thật.
- UI không còn route/fallback che lỗi ở luồng đang test.

### Done cho Workspace foundation

- Workspace là tenant key duy nhất trong auth, policy, license, entitlement và AgentOS.
- Cùng Snowflake workspace ID xuyên local/cloud.
- Một local host vận hành nhiều Workspace Vault không leak dữ liệu.
- Workspace và Project lifecycle độc lập, concurrency-safe và audit được.
- Workspace W0 tồn tại không cần legal entity.
- Local-only vẫn chạy; Remote Access không đổi data residency; Cloud Continuity failover có fencing và encrypted sync.
- Workforce UI phản ánh functional AgentSpec/capability thật; CFO/CMO chỉ là governed role overlay.
- Test matrix mục 10 pass ở phạm vi release đã công bố.
