# COSA Hybrid Data Architecture

## Local PostgreSQL + Supabase Self-Hosted Control Plane & Project Intelligence

**Mục tiêu:** Chuẩn hóa kiến trúc COSA theo mô hình hybrid: dữ liệu vận
hành chi tiết của từng doanh nghiệp được giữ tại PostgreSQL
local/private, trong khi Supabase self-hosted trên hạ tầng COSA quản lý
identity, company, license/tier, entitlement, project lifecycle,
program/cohort, public marketing data và dữ liệu intelligence cần thiết
để COSA phân tích sự phát triển của hệ sinh thái.

------------------------------------------------------------------------

# 1. Architecture Decision

COSA sử dụng **hai System of Record có trách nhiệm khác nhau**.

> **Supabase Central là System of Record cho COSA Platform Identity,
> License, Company Registry, Project Lifecycle và Platform
> Intelligence.**

> **PostgreSQL Local/Private là System of Record cho dữ liệu vận hành
> chi tiết, nội bộ và riêng tư của từng company.**

Không coi Local và Central là hai bản sao đầy đủ của cùng database.

``` text
                         COSA PLATFORM
                  Supabase Self-hosted
              ┌──────────────────────────┐
              │ Identity                 │
              │ Companies                │
              │ Memberships              │
              │ Plans / Licenses         │
              │ Entitlements             │
              │ Projects Registry        │
              │ Project Stage History    │
              │ Milestones / Outcomes    │
              │ Programs / Cohorts       │
              │ Product Analytics        │
              │ Landing / Public Intake  │
              │ Aggregate Intelligence   │
              └─────────────┬────────────┘
                            │
                     selective sync
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
      Company A         Company B         Company C
      COSA Local        COSA Local        COSA Server
      PostgreSQL        PostgreSQL        PostgreSQL

      Full private      Full private      Full private
      operational data operational data  operational data
```

------------------------------------------------------------------------

# 2. Deployment Model

## 2.1 COSA Platform / Shared VPS

Đề xuất stack:

``` text
Hostinger VPS
├── Reverse Proxy / HTTPS
├── COSA Platform API
├── Next.js
│   ├── Account Portal
│   ├── Landing Runtime
│   ├── Survey Runtime
│   └── Public pages
├── Supabase Self-hosted
│   ├── PostgreSQL
│   ├── Auth
│   ├── Storage
│   └── Realtime
├── Public Event Gateway
├── Deployment Service
└── optional n8n
```

## 2.2 Company Local

``` text
Founder Mac / Windows
├── COSA Desktop
├── COSA API / FastAPI
├── PostgreSQL Local
├── Agent Runtime
├── Knowledge
├── Attachments
└── Platform Sync Agent
```

## 2.3 Company Private Server

``` text
Company VPS / Server
├── COSA API
├── PostgreSQL
├── Agent Runtime
├── Scheduler
├── Knowledge
└── Platform Sync Agent
```

Local và Private Server dùng cùng business schema và domain logic.

------------------------------------------------------------------------

# 3. Centralized Identity Is Mandatory

COSA account không phải account hoàn toàn offline.

Mỗi COSA user tham gia một company phải có identity trung tâm:

``` text
Supabase Auth
     ↓
platform_user
     ↓
company_membership
     ↓
company
     ↓
plan / license / entitlement
```

Local giữ reference/cache:

``` text
local_user
├── platform_user_id
├── platform_company_id
├── local_role
├── department
└── local_permissions
```

Phân biệt:

``` text
PLATFORM ENTITLEMENT
Company được phép sử dụng gì?

LOCAL AUTHORIZATION
User trong company được phép làm gì?
```

Quyền cuối:

``` text
ALLOWED =
Platform Entitlement
AND
Local Authorization
```

------------------------------------------------------------------------

# 4. License, Tier và Entitlement

Không hard-code tier trong code nghiệp vụ.

Không:

``` python
if plan == "pro":
    max_projects = 10
```

Nên data-driven:

``` text
plans
features
plan_features
plan_limits
licenses
subscriptions
company_entitlements
company_overrides
```

Ví dụ entitlement:

``` json
{
  "plan": "pro",
  "limits": {
    "projects": 20,
    "users": 5,
    "scheduled_agents": 3
  },
  "features": {
    "marketing": true,
    "crm": true,
    "finance": false,
    "custom_domain": true
  }
}
```

Cho phép commercial override:

``` text
Company A
plan = pro

override
user.max = 10
scheduled_agents.max = 8
```

------------------------------------------------------------------------

# 5. Offline Entitlement Snapshot

Local không gọi Central cho mọi thao tác.

Central cấp signed entitlement snapshot:

``` text
company_id
plan
features
limits
issued_at
valid_until
signature
```

Local cache và verify.

``` text
Online
  ↓
Refresh entitlement
  ↓
Signed snapshot
  ↓
Local enforcement

Offline
  ↓
Cached signed snapshot
  ↓
Grace period
```

Nếu license/grace hết hạn, không khóa dữ liệu của khách hàng.

Recommended restricted mode:

``` text
Read existing data       YES
Backup / Export          YES
View existing projects   YES

Create premium objects   NO
Add seats                NO
Paid automation          NO
Premium agent execution  NO
```

------------------------------------------------------------------------

# 6. Project Registry phải nằm Central

Central không chỉ lưu `project_count`.

Mỗi project local phải có một platform identity:

``` text
platform_project_id
company_id
local_project_id
```

Central Project Registry nên lưu tối thiểu:

``` text
projects
--------
id
company_id
name
slug / public-safe identifier
category
industry
status
current_stage
created_at
updated_at
archived_at
deleted_at
last_stage_change_at
source_program_id
source_cohort_id
```

Tên project có thể được lưu central vì cần quản trị platform; nếu sau
này cần privacy mode đặc biệt có thể hỗ trợ pseudonymization.

------------------------------------------------------------------------

# 7. Startup Stage History

Không chỉ lưu trạng thái hiện tại.

``` text
project_stage_history
---------------------
id
project_id
from_stage
to_stage
changed_at
change_source
metadata
```

Ví dụ:

``` text
Idea
 ↓
Problem Discovery
 ↓
Validation
 ↓
MVP
 ↓
Traction
 ↓
Growth
```

Tên stage thực tế phải dùng taxonomy chuẩn của COSA tại thời điểm triển
khai, không hard-code từ tài liệu này nếu codebase đã có stage model mới
hơn.

Central có thể tính:

``` text
time_in_stage
median_stage_duration
stage conversion
stage abandonment
cohort progression
```

------------------------------------------------------------------------

# 8. Project Lifecycle Events

Mọi thay đổi lifecycle quan trọng gửi event lên Central:

``` text
project.created
project.updated
project.stage_changed
project.archived
project.restored
project.deleted

project.milestone_reached
project.first_customer
project.first_revenue
project.paused
project.closed
```

Event envelope:

``` json
{
  "event_id": "uuid",
  "company_id": "uuid",
  "project_id": "uuid",
  "event_type": "project.stage_changed",
  "occurred_at": "ISO-8601",
  "schema_version": 1,
  "payload": {}
}
```

Event phải idempotent.

------------------------------------------------------------------------

# 9. Project Deletion

Local cho phép user xóa project theo policy COSA.

Central không được giả vờ project chưa từng tồn tại nếu mục tiêu
platform cần lifecycle analytics.

Workflow:

``` text
Local project
    ↓ delete
project.deleted event
    ↓
Central
    ↓
deleted_at
last_known_stage
lifecycle summary
```

Nếu policy/consent yêu cầu xóa thông tin nhận dạng:

``` text
Detailed project metadata
        ↓
anonymize
        ↓
retain permitted aggregate lifecycle facts
```

Việc retention/anonymization phải được triển khai phù hợp privacy policy
và yêu cầu pháp lý, không dùng tài liệu kỹ thuật này để bỏ qua quyền xóa
dữ liệu.

------------------------------------------------------------------------

# 10. Project Outcomes

Tạo entity `project_outcomes`.

Gợi ý:

``` text
project_outcomes
----------------
project_id

first_interview_at
first_experiment_at
mvp_launched_at

first_lead_at
first_customer_at
first_revenue_at

has_revenue
revenue_band
revenue_verified

team_first_hire_at

fundraising_started_at
funding_received_at

paused_at
closed_at
outcome_updated_at
```

Không bắt buộc lưu doanh thu chính xác central.

Có thể dùng:

``` text
has_revenue = true/false
```

hoặc:

``` text
revenue_band
0
<1m
1m-10m
10m-50m
50m-100m
100m+
```

Taxonomy tiền tệ/band phải versioned nếu dùng cho analytics lâu dài.

------------------------------------------------------------------------

# 11. Evidence Metrics

Central có thể nhận **aggregate counters**, không cần toàn bộ nội dung
evidence.

Ví dụ:

``` text
project_metrics
---------------
customer_interview_count
experiment_count
validated_assumption_count
invalidated_assumption_count
lead_count
customer_count
active_campaign_count
mvp_release_count
```

Không mặc định sync:

``` text
interview transcript
customer PII
private documents
internal strategy notes
full accounting ledger
contracts
AI conversation history
API keys
credentials
```

------------------------------------------------------------------------

# 12. Program / Cohort Intelligence

Đây là domain quan trọng cho Free/Learning và chương trình như SIHUB.

Schema gợi ý:

``` text
programs
cohorts
program_participants
project_program_links
```

Ví dụ:

``` text
Program
SIHUB Startup Program

Cohort
2026-AUG

Participant
platform_user_id

Project
platform_project_id
```

Central có thể tạo funnel:

``` text
Participants
     ↓
Created account
     ↓
Created project
     ↓
Problem Discovery
     ↓
Validation
     ↓
MVP
     ↓
First Customer
     ↓
First Revenue
     ↓
Still Active 90d
     ↓
Still Active 180d
```

Đây là **outcome measurement**, không phải chỉ course completion.

------------------------------------------------------------------------

# 13. COSA Platform Intelligence

Central có thể phân tích:

``` text
Companies by stage
Projects by stage
Stage conversion
Median time per stage
Project survival
Project closure
First-customer rate
First-revenue rate
Cohort comparison
Industry comparison
Feature adoption
Plan conversion
Retention
```

Ví dụ AI có thể đưa insight dạng:

> Trong cohort tương tự, các project đạt X evidence có xu hướng tiến đến
> MVP với tỷ lệ cao hơn.

Không được biến correlation thành causal claim.

------------------------------------------------------------------------

# 14. Data Boundary

## Central Supabase --- nên lưu

``` text
Identity
Company Registry
Membership
Plan
License
Entitlement
Installation
Deployment metadata

Project Registry
Project stage
Stage history
Lifecycle
Milestones
Outcomes
Aggregate evidence metrics

Program
Cohort
Participation

Landing pages
Forms
Surveys
Public submissions
Campaign attribution
Public events

Product usage
Aggregate platform analytics
```

## Company PostgreSQL --- authoritative private data

``` text
Full project workspace
Tasks
OKRs / execution
Detailed CRM
Contacts
Customer profiles
Sales notes
Customer interviews
Interview transcripts
Experiment details
Internal marketing data
Finance/accounting details
Contracts
Documents
Knowledge base
Agent memory
AI conversation
Private prompts/configuration
Operational audit data
```

Một số entity có mặt cả hai phía nhưng **khác độ chi tiết và
authority**.

------------------------------------------------------------------------

# 15. Data Classification

Mỗi sync field/event nên có classification:

``` text
PLATFORM_REQUIRED
ANALYTICS_REQUIRED
PUBLIC
COMPANY_PRIVATE
SENSITIVE
SECRET
```

Ví dụ:

``` text
project.stage
→ PLATFORM_REQUIRED

project.first_revenue_at
→ ANALYTICS_REQUIRED

landing_page.title
→ PUBLIC

interview.transcript
→ COMPANY_PRIVATE

customer.phone
→ SENSITIVE

api_key
→ SECRET
```

`SECRET` không được sync qua Project Intelligence pipeline.

------------------------------------------------------------------------

# 16. Local → Central Sync Agent

``` text
COSA Company Core
├── PostgreSQL
└── Platform Sync Agent
      ├── authenticate
      ├── entitlement refresh
      ├── lifecycle outbox
      ├── usage summary
      ├── project metadata sync
      ├── retry
      └── acknowledgement
```

Dùng local outbox:

``` text
platform_outbox
---------------
event_id
event_type
aggregate_type
aggregate_id
payload
created_at
sent_at
acknowledged_at
retry_count
```

Business transaction:

``` text
BEGIN

UPDATE local project

INSERT platform_outbox

COMMIT
```

Tránh trường hợp local thay đổi thành công nhưng Central không bao giờ
biết.

------------------------------------------------------------------------

# 17. Central → Local Sync

Central gửi:

``` text
license changes
entitlement changes
membership/seat status
platform configuration
approved updates
```

Có thể dùng:

``` text
Realtime/WebSocket
= notification

HTTPS REST
= authoritative fetch/ack
```

Mất Realtime không được làm mất state.

------------------------------------------------------------------------

# 18. Conflict Ownership

Không xây generic bidirectional database sync.

Mỗi field/domain phải có owner.

Ví dụ:

``` text
plan
owner = Central

license
owner = Central

max_users
owner = Central

project detailed content
owner = Local

project current_stage
owner = Local
mirror = Central

project outcome
owner = Local
mirror = Central

central cohort assignment
owner = Central
mirror = Local when needed
```

Nếu conflict, authority quyết định.

------------------------------------------------------------------------

# 19. Supabase Multi-company Security

Mọi shared table phải có `company_id` khi applicable.

Không tin `company_id` tùy ý từ client.

Identity/token được resolve server-side:

``` text
token
 ↓
platform user
 ↓
membership
 ↓
company
 ↓
allowed resources
```

RLS phải được thiết kế cho các table exposed qua Supabase API.

Các thao tác nhạy cảm phải qua COSA Platform API:

``` text
license activation
plan/tier change
entitlement change
company ownership
seat allocation
custom domain
deployment
billing-related state
```

Service-role credential không được đưa vào Next.js browser bundle hoặc
COSA client.

------------------------------------------------------------------------

# 20. Marketing / Landing Architecture

## Default Free / Learning

``` text
COSA Marketing Agent
       ↓
Landing definition / reusable modules
       ↓
COSA Landing Runtime
       ↓
company-or-campaign.cosa-domain
```

## Paid / Upgraded

``` text
same landing
    ↓
custom domain mapping
    ↓
landing.company.vn
```

Custom domain là entitlement:

``` text
custom_domain.enabled
```

Không cần build lại landing chỉ để đổi domain.

------------------------------------------------------------------------

# 21. Shared Landing Runtime

Không tạo một Next.js app/process riêng cho mọi landing page thông
thường.

Ưu tiên:

``` text
Next.js COSA Landing Runtime
        ↓
hostname resolution
        ↓
company
        ↓
landing definition
        ↓
reusable module renderer
```

Schema:

``` text
landing_pages
landing_versions
landing_sections
domains
forms
form_fields
campaigns
```

`sections` có thể dùng JSONB nếu phù hợp với implementation hiện tại.

Agent tạo landing theo module reusable.

Chỉ generate/deploy Next.js app riêng cho use case custom thực sự.

------------------------------------------------------------------------

# 22. Automatic Deployment

Flow:

``` text
Founder request
    ↓
Marketing Agent
    ↓
Generate landing/modules
    ↓
Preview
    ↓
Founder publish approval
    ↓
Deployment Service
    ↓
Hostinger VPS
    ↓
subdomain/default domain
    ↓
LIVE
```

Không để AI tự ý publish production nếu UX hiện tại yêu cầu founder
approval.

Deployment record:

``` text
deployments
-----------
id
company_id
asset_id
environment
status
version
hostname
created_at
deployed_at
```

------------------------------------------------------------------------

# 23. Public Lead / Survey Intake

``` text
Visitor
  ↓
Landing / Survey
  ↓
Public Intake API
  ↓
Supabase PostgreSQL
  ↓
form_submission
  ↓
public_event
  ↓
Company Sync
  ↓
Local PostgreSQL
  ↓
CRM / Research
```

Central có thể giữ dữ liệu cần thiết theo retention policy.

PII không nên mặc định trở thành dữ liệu analytics vĩnh viễn.

------------------------------------------------------------------------

# 24. COSA Customer Intelligence

Phân biệt:

## COSA Customer

Company/user mua hoặc dùng COSA.

Central cần hiểu:

``` text
acquisition
plan
cohort
company lifecycle
feature adoption
projects
stages
outcomes
retention
upgrade
```

## Customer of a COSA Company

Khách hàng/lead của Company A.

Detailed profile mặc định thuộc Company A Local/Private.

Central chỉ giữ public-intake/analytics fields cần thiết theo policy.

------------------------------------------------------------------------

# 25. Free User Is Strategically Important

Free/Learning không chỉ là trial.

Ví dụ:

``` text
SIHUB participant
    ↓
Free COSA
    ↓
creates company
    ↓
creates project
    ↓
Validation
    ↓
MVP
    ↓
First customer
    ↓
First revenue
```

COSA có thể đo real outcome nếu project lifecycle được sync Central.

Do đó không xóa project registry khỏi Central chỉ vì user đang Free.

------------------------------------------------------------------------

# 26. Suggested Central Schema Domains

``` text
platform_identity/
  users
  companies
  company_memberships

commercial/
  software_products
  plans
  features
  plan_features
  plan_limits
  licenses
  subscriptions
  company_entitlements
  company_overrides

installations/
  installations
  devices
  deployment_targets

projects/
  projects
  project_stage_history
  project_milestones
  project_outcomes
  project_metrics
  project_events

programs/
  programs
  cohorts
  program_participants
  project_program_links

marketing/
  campaigns
  landing_pages
  landing_versions
  domains
  forms
  form_submissions
  public_events

analytics/
  usage_events
  company_usage_summary
  project_analytics
  cohort_metrics

distribution/
  releases
  templates
  knowledge_pack_versions
```

Tên bảng cuối cùng phải phù hợp convention codebase hiện tại.

------------------------------------------------------------------------

# 27. IDs

Ưu tiên UUID/ULID phù hợp stack hiện hữu.

Mọi aggregate sync quan trọng cần stable platform ID:

``` text
platform_user_id
platform_company_id
platform_project_id
event_id
installation_id
```

Không dùng auto-increment local ID làm global identity.

------------------------------------------------------------------------

# 28. Privacy & Consent

Vì COSA muốn dùng dữ liệu project để platform intelligence, đây phải là
thiết kế sản phẩm minh bạch.

UI/Terms/Privacy cần phân biệt: - dữ liệu bắt buộc để vận hành
license/platform; - project lifecycle metadata; - aggregate analytics; -
optional detailed analytics; - private local data không upload.

Không âm thầm upload transcript, tài liệu nội bộ hoặc dữ liệu khách hàng
chi tiết chỉ vì chúng hữu ích cho AI.

Cần hỗ trợ policy/version:

``` text
consent_version
privacy_policy_version
analytics_preferences
accepted_at
```

Các yêu cầu pháp lý cụ thể phải được rà soát riêng trước production.

------------------------------------------------------------------------

# 29. Deletion & Retention

Cần policy riêng cho:

``` text
account deletion
company deletion
project deletion
lead deletion
analytics retention
backup retention
```

Không equate `soft_delete` với quyền lưu vĩnh viễn.

Central analytics có thể dùng anonymized aggregates nếu được phép.

------------------------------------------------------------------------

# 30. Backup Strategy

## Supabase Central

Backup production định kỳ: - PostgreSQL. - Storage metadata/files cần
thiết. - configuration. - encryption/secrets theo quy trình riêng. -
restore drill.

## Company Local

``` text
company.cosa-backup
├── database.dump
├── knowledge/
├── attachments/
├── configs/
└── manifest.json
```

Central Project Registry không thay thế local backup.

------------------------------------------------------------------------

# 31. Failure Modes

## Central unavailable

Local: - tiếp tục đọc/ghi private operational data; - dùng cached
entitlement trong grace period; - queue platform events; - sync lại khi
online.

## Local offline

Central: - landing vẫn hoạt động; - lead/survey vẫn được nhận; - project
intelligence cũ vẫn tồn tại; - public events chờ local nhận.

## Sync duplicate

Dùng `event_id` + idempotency.

## Event out of order

Dùng: - occurred_at; - aggregate version/revision khi cần; - server
reconciliation rule.

------------------------------------------------------------------------

# 32. Hologram Hub

Có thể thêm card:

``` text
Platform Sync
─────────────
Account        Connected
License        Pro
Entitlement    Current
Project Sync   Healthy
Last Sync      2 min ago
Pending Events 0
```

Project cards có thể hiển thị stage/lifecycle từ local data.

Không hiển thị Central analytics nhạy cảm cho company khác.

------------------------------------------------------------------------

# 33. COSA Internal Analytics Dashboard

Admin COSA có thể có:

``` text
Companies
Active Companies
Free → Paid Conversion

Projects Created
Projects Active
Projects Deleted
Projects by Stage

Idea → Validation
Validation → MVP
MVP → First Customer
First Customer → Revenue

Median Time per Stage

Programs / Cohorts
SIHUB Cohort A
SIHUB Cohort B

First Revenue Rate
90-day Survival
180-day Survival
```

Phải hỗ trợ filtering:

``` text
program
cohort
industry
region (nếu hợp lệ/được thu thập)
plan
created period
stage
```

------------------------------------------------------------------------

# 34. AI Intelligence Layer

AI không đọc trực tiếp raw production tables tùy tiện.

Nên có analytics views/materialized views hoặc warehouse layer sau này:

``` text
Supabase Operational Tables
          ↓
Analytics Views
          ↓
Aggregated / de-identified dataset
          ↓
COSA Intelligence
```

AI insight phải phân biệt: - descriptive; - correlational; -
predictive; - recommendation.

Không gọi correlation là nguyên nhân.

------------------------------------------------------------------------

# 35. Implementation Rules for Claude Code

1.  Inspect toàn bộ codebase trước.
2.  Không tạo architecture song song nếu COSA đã có entity tương đương.
3.  PostgreSQL local/private vẫn là authoritative detailed operational
    DB.
4.  Supabase Central là authoritative platform DB.
5.  Central account là bắt buộc.
6.  Project Registry và lifecycle phải Central.
7.  Không chỉ sync project count.
8.  Stage history phải lưu lịch sử.
9.  Project deletion phải phát lifecycle event.
10. Không sync secret/private data ngoài allowlist.
11. Dùng outbox pattern cho Local → Central.
12. Dùng idempotency cho mọi event.
13. Không xây generic bidirectional DB sync.
14. Xác định field/domain authority rõ ràng.
15. License/entitlement data-driven.
16. Hỗ trợ signed offline entitlement snapshot.
17. Supabase RLS cho shared exposed data.
18. Privileged actions qua Platform API.
19. Không expose service-role secret cho client.
20. Landing thông thường dùng shared runtime/module library.
21. Custom app mới dùng dedicated generation/deployment.
22. Central analytics phải có privacy/retention model.
23. Không xóa/migrate code hiện tại trước khi lập mapping và migration
    plan.

------------------------------------------------------------------------

# 36. Prompt triển khai cho Claude Code

``` text
Bạn đang triển khai COSA Hybrid Data Architecture.

Hãy inspect codebase hiện tại trước khi sửa code.

Mục tiêu kiến trúc:

A. SUPABASE SELF-HOSTED CENTRAL
Là System of Record cho:
- platform identity;
- companies;
- memberships;
- plans/licenses/entitlements;
- installations;
- project registry;
- project stage history;
- project lifecycle;
- project milestones/outcomes;
- programs/cohorts;
- landing/public intake;
- product/platform intelligence.

B. COMPANY POSTGRESQL LOCAL/PRIVATE
Là System of Record cho:
- detailed project workspace;
- tasks/execution;
- detailed CRM;
- interviews;
- experiments;
- finance;
- private documents;
- knowledge;
- agent memory;
- private operational data.

C. SYNC
- Không generic DB replication.
- Local → Central dùng outbox/event pattern.
- Central → Local dùng API + cached signed entitlement.
- Event idempotent.
- Domain ownership rõ ràng.
- Offline phải queue và recover.

D. PROJECT
Central phải lưu project-level metadata và lifecycle, không chỉ project_count.
Phải hỗ trợ:
- created;
- updated;
- stage_changed;
- archived;
- restored;
- deleted;
- milestone;
- first_customer;
- first_revenue;
- paused;
- closed.

E. FREE / PROGRAM COHORT
Phải có khả năng liên kết user/company/project với program/cohort để COSA đo:
- project creation;
- stage progression;
- MVP;
- first customer;
- first revenue;
- survival/closure.

F. PRIVACY
Chỉ sync allowlisted platform/project intelligence fields.
Không upload mặc định:
- transcript;
- private document;
- customer detailed PII;
- accounting ledger;
- credentials;
- secrets;
- full AI conversations.

G. MARKETING
- Next.js shared Landing Runtime cho landing/survey thông thường.
- default COSA subdomain.
- custom domain theo entitlement.
- Public Intake → Supabase → event → Local CRM.
- dedicated Next.js deployment chỉ khi use case thực sự custom.

Trước khi code, xuất báo cáo:
1. Existing architecture map.
2. Existing local DB models.
3. Existing auth/account/license implementation.
4. Existing project/stage model.
5. Existing marketing/landing implementation.
6. Existing deployment workflow.
7. Mapping existing → target architecture.
8. Gaps.
9. Database migration plan.
10. Phased implementation plan.

Sau khi tôi/maintainer duyệt plan mới bắt đầu refactor lớn.
Ưu tiên incremental changes và backward compatibility.
```

------------------------------------------------------------------------

# 37. Implementation Phases

## Phase 1 --- Architecture Audit

-   Codebase mapping.
-   Existing schema inventory.
-   Current auth/license analysis.
-   Current project/stage analysis.
-   Marketing/deployment analysis.

## Phase 2 --- Central Platform Core

-   Supabase schema.
-   Company.
-   Membership.
-   Plan/license.
-   Entitlement.
-   Installation.
-   RLS.
-   Platform API.

## Phase 3 --- Identity & Entitlement

-   Supabase Auth.
-   Company membership.
-   Local identity mapping.
-   Signed entitlement snapshot.
-   Offline grace.
-   Tier enforcement.

## Phase 4 --- Project Intelligence

-   Central Project Registry.
-   Stable platform project ID.
-   Stage history.
-   Lifecycle events.
-   Milestones.
-   Outcomes.
-   Metrics.

## Phase 5 --- Reliable Sync

-   Local outbox.
-   Central ingestion.
-   ACK.
-   Retry.
-   Idempotency.
-   Offline recovery.
-   Conflict/authority rules.

## Phase 6 --- Programs & Cohorts

-   Program/cohort schema.
-   Participant attribution.
-   Project attribution.
-   Outcome funnel.
-   SIHUB-style cohort dashboard.

## Phase 7 --- Marketing Public Edge

-   Landing Runtime.
-   Form/survey.
-   Supabase intake.
-   Public events.
-   Local CRM sync.
-   Default subdomain.
-   Custom domain entitlement.

## Phase 8 --- Platform Intelligence

-   Analytics views.
-   Cohort metrics.
-   Stage conversion.
-   Revenue outcome.
-   Retention/survival.
-   Admin dashboard.

## Phase 9 --- Privacy & Hardening

-   Data classification.
-   Consent/versioning.
-   Retention.
-   Delete/anonymize flows.
-   Security review.
-   Backup/restore.
-   Disaster recovery.

------------------------------------------------------------------------

# 38. Acceptance Criteria

-   [ ] COSA user identity được liên kết Central.
-   [ ] Company tier/entitlement do Central quyết định.
-   [ ] Local hoạt động được trong offline grace period.
-   [ ] Company private operational data không bị bắt buộc upload toàn
    bộ.
-   [ ] Mỗi project có stable Central identity.
-   [ ] Central biết project hiện ở stage nào.
-   [ ] Central giữ stage history.
-   [ ] Central nhận create/update/archive/delete lifecycle.
-   [ ] Central đo được first customer/first revenue khi project ghi
    nhận outcome.
-   [ ] Program/cohort có thể liên kết tới project.
-   [ ] Có thể tính funnel cohort.
-   [ ] Local → Central sync có outbox/retry/idempotency.
-   [ ] Không có generic bidirectional DB replication.
-   [ ] Landing Free có thể dùng default COSA subdomain.
-   [ ] Custom domain được điều khiển bằng entitlement.
-   [ ] Public lead/survey không phụ thuộc laptop founder đang bật.
-   [ ] Lead có thể sync về PostgreSQL local/private.
-   [ ] Central analytics không cần transcript/private docs.
-   [ ] Secrets không được sync.
-   [ ] Project deletion/retention có policy rõ ràng.
-   [ ] Admin COSA có platform analytics mà không lộ private company
    workspace.

------------------------------------------------------------------------

# 39. Final Architecture

``` text
                           COSA
                            │
             ┌──────────────┴──────────────┐
             │                             │
     COSA CONTROL PLANE            COMPANY DATA PLANE
     Supabase Self-hosted          PostgreSQL Local/Private
             │                             │
     Identity                              Projects Detail
     Companies                             Tasks
     Membership                            CRM
     License/Tier                          Interviews
     Entitlement                           Experiments
     Project Registry                      Finance
     Stage History                         Documents
     Outcomes                              Knowledge
     Programs/Cohorts                      Agent Memory
     Public Marketing                      Internal Operations
     Platform Intelligence
             │                             │
             └──────── reliable sync ──────┘
```

**Nguyên tắc cuối cùng:**

> COSA tập trung dữ liệu cần thiết để vận hành platform và hiểu
> lifecycle/outcome của company/project; COSA phân tán dữ liệu vận hành
> chi tiết và riêng tư về hạ tầng do từng company kiểm soát.

Nhờ đó COSA có thể đồng thời: - cung cấp Local/Private deployment; -
kiểm soát license/tier; - biết chính xác hệ sinh thái có bao nhiêu
company/project; - hiểu project đang ở stage nào; - theo dõi lifecycle
kể cả archive/delete; - đo outcome của Free/program cohorts; - biết bao
nhiêu project tiến tới khách hàng/doanh thu; - cải thiện sản phẩm bằng
dữ liệu nền tảng; - nhưng không cần biến toàn bộ dữ liệu nội bộ của
khách hàng thành SaaS tập trung.

------------------------------------------------------------------------

# 40. CẬP NHẬT KIẾN TRÚC LANDING PAGE --- COMPANY-OWNED LANDING APP

## 40.1. Quyết định thay đổi

Thay thế định hướng **Shared Landing Runtime là application dùng chung
cho mọi company** bằng:

> **Shared Module Library + Company-Owned Landing App**

COSA cung cấp framework, SDK, module, template, AI generation và
deployment automation dùng chung; nhưng mỗi company sở hữu một
landing/marketing application riêng.

``` text
COSA Marketing Platform
├── Landing SDK
├── Module Library
├── Form SDK
├── Analytics SDK
├── Templates
└── Deployment Agent
        │
        ├── Company A Marketing App
        ├── Company B Marketing App
        └── Company C Marketing App
```

Mục tiêu: - Company có source code riêng. - Có thể tự quản lý về sau. -
Có thể export/transfer. - Có thể chuyển từ COSA VPS sang VPS riêng. -
Không khóa website/landing asset vào hạ tầng COSA. - Vẫn tái sử dụng
module và template COSA. - Vẫn tích hợp Supabase Central/Public Intake
khi cần.

------------------------------------------------------------------------

# 41. Một Company = Một Marketing/Landing Application mặc định

Không thiết kế:

``` text
1 landing page = 1 Next.js project
```

Mặc định:

``` text
1 company = 1 marketing web application
```

Một application có thể chứa nhiều:

``` text
/
├── /
├── /ai-agent
├── /survey
├── /product-a
├── /event-2026
├── /campaign/summer
└── /lead-magnet/guide
```

Nhờ vậy company không phải vận hành hàng chục Next.js applications chỉ
vì có nhiều campaign.

Custom application riêng chỉ tạo khi use case thực sự yêu cầu
isolation/runtime riêng.

------------------------------------------------------------------------

# 42. Cấu trúc Company-Owned App

Ví dụ:

``` text
company-marketing-app/
├── app/
│   ├── page.tsx
│   ├── ai-agent/
│   ├── survey/
│   └── campaign/
├── components/
│   ├── cosa/
│   │   ├── hero/
│   │   ├── features/
│   │   ├── pricing/
│   │   ├── testimonials/
│   │   ├── faq/
│   │   ├── lead-form/
│   │   └── survey/
│   └── company/
├── lib/
│   ├── cosa-intake/
│   ├── analytics/
│   └── company-config/
├── public/
├── campaigns/
├── cosa.manifest.yaml
└── deployment/
```

Cấu trúc thực tế phải map vào convention/codebase hiện tại, không tạo
duplicate architecture nếu đã có.

------------------------------------------------------------------------

# 43. Shared Modules, Not Shared Application

COSA duy trì:

``` text
@cosa/landing-sdk
@cosa/form-sdk
@cosa/analytics-sdk
@cosa/ui-marketing
@cosa/templates
```

Tên package chỉ là minh họa.

Module có thể gồm:

``` text
Hero
Problem
Solution
Features
Benefits
Social Proof
Testimonials
Pricing
Comparison
FAQ
CTA
Lead Form
Survey
Booking
Product Offer
Checkout Integration
Footer
```

Marketing Agent ưu tiên compose/reuse module thay vì generate toàn bộ
code mới.

Flow:

``` text
Founder Request
      ↓
Marketing Agent
      ↓
Analyze campaign objective
      ↓
Select reusable modules
      ↓
Generate/update company page
      ↓
Preview
      ↓
Founder approval
      ↓
Build
      ↓
Deploy
```

------------------------------------------------------------------------

# 44. Source Code Ownership

Landing/marketing application là **digital asset của company**.

Nguyên tắc:

> COSA tạo và quản lý tài sản số cho company nhưng không khóa source
> code vào COSA.

Company phải có khả năng: - export source; - clone source; - backup; -
tự chỉnh sửa; - chuyển repository; - chuyển deployment target; - chạy
độc lập trên hạ tầng riêng nếu entitlement/chính sách cho phép.

Không lưu source code duy nhất dưới dạng JSON trong Supabase.

Supabase lưu registry/metadata; source phải có source-control hoặc
exportable project representation.

------------------------------------------------------------------------

# 45. Repository Model

Đề xuất:

``` text
Company
└── Marketing App
    └── Git Repository
```

Central registry:

``` text
company_web_apps
----------------
id
company_id
app_type
repository_ref
framework
deployment_mode
current_version
created_at
updated_at
```

Không nhất thiết repository phải nằm trên GitHub; abstraction cần cho
phép thay provider về sau.

COSA có thể quản lý repository ban đầu và hỗ trợ transfer/export khi
company cần.

------------------------------------------------------------------------

# 46. COSA App Manifest

Mỗi app cần manifest portable.

Ví dụ:

``` yaml
schema_version: 1

app:
  type: marketing
  framework: nextjs

company:
  platform_company_id: cmp_xxx

cosa:
  project_id: prj_xxx
  public_intake_enabled: true

features:
  lead_forms: true
  surveys: true
  checkout: false

deployment:
  mode: cosa_managed
```

Không lưu secret trong manifest.

Secret được inject bằng environment/secret store tại deployment target.

Manifest giúp Deployment Agent: - nhận diện app; - kiểm tra
compatibility; - build; - migrate; - transfer; - deploy lại trên VPS
khác.

------------------------------------------------------------------------

# 47. Ba mức Deployment Ownership

## Level 1 --- COSA Managed

``` text
Company App
    ↓
COSA Shared VPS
    ↓
company-slug.cosa-domain
```

COSA quản lý: - build; - deployment; - HTTPS; - default subdomain; -
runtime; - monitoring cơ bản.

Phù hợp Free/Learning và user không muốn quản trị server.

## Level 2 --- Company VPS + COSA Services

``` text
Company VPS
└── Company Marketing App
          │
          ▼
COSA Public Intake / Platform API
          │
          ▼
Supabase Central
```

Company sở hữu hosting, COSA vẫn cung cấp platform/public services.

## Level 3 --- Fully Private

``` text
Company VPS
├── Marketing App
├── COSA Company API
├── PostgreSQL
└── Private Intake
        │
        └── selective platform sync
```

COSA Central chỉ nhận platform/project intelligence được phép.

------------------------------------------------------------------------

# 48. Default Subdomain và Custom Domain

Mặc định COSA-managed:

``` text
company-slug.<cosa-domain>
```

Có thể mở rộng campaign routing:

``` text
company-slug.<cosa-domain>/campaign-a
company-slug.<cosa-domain>/survey
```

Custom domain là entitlement:

``` text
custom_domain.enabled = true
```

Ví dụ:

``` text
marketing.company.vn
www.company.vn
campaign.company.vn
```

Đổi domain không yêu cầu viết lại app.

Central:

``` text
domains
-------
id
company_id
app_id
hostname
type
verification_status
ssl_status
created_at
```

------------------------------------------------------------------------

# 49. Deployment Registry

Supabase Central quản lý metadata deployment:

``` text
deployments
-----------
id
company_id
app_id
version
target_type
target_ref
hostname
build_status
deployment_status
created_at
deployed_at
```

`target_type` ví dụ:

``` text
cosa_shared_vps
company_vps
custom_server
```

Không lưu private server credentials plaintext trong database.

------------------------------------------------------------------------

# 50. Landing Runtime Strategy trên COSA VPS

Company-owned app không đồng nghĩa mỗi app phải chạy một Node process
24/7.

COSA Deployment Service phân loại:

## Static Landing

``` text
Next.js build
    ↓
static output
    ↓
Nginx/CDN/static hosting
```

Phù hợp landing/campaign phổ biến.

## Dynamic Marketing App

``` text
Next.js runtime
    ↓
managed container/process
```

Chỉ khi cần server-side dynamic behavior.

## Custom Web App

``` text
Dedicated build/container
```

Cho workflow/application đặc biệt.

Nguyên tắc:

> Ưu tiên static generation cho landing pages; form/public data gửi về
> API riêng.

Điều này giúp một VPS chung phục vụ nhiều company hiệu quả hơn.

------------------------------------------------------------------------

# 51. Lead Intake không phụ thuộc Hosting Location

COSA-managed app:

``` text
Landing
  ↓
COSA Public Intake
  ↓
Supabase
  ↓
Company Sync
  ↓
Local CRM
```

Company-hosted app vẫn có thể:

``` text
Company VPS Landing
        ↓
COSA Public Intake
        ↓
Supabase
        ↓
Company Sync
```

Do đó việc chuyển website khỏi COSA VPS không làm mất integration.

------------------------------------------------------------------------

# 52. Fully Private Intake

Gói/deployment phù hợp có thể cho phép:

``` text
Company Landing
     ↓
Company COSA API
     ↓
Company PostgreSQL
```

Sau đó chỉ gửi aggregate/platform event:

``` text
campaign.created
landing.published
lead_count.updated
conversion.updated
```

Central không nhất thiết nhận customer PII.

------------------------------------------------------------------------

# 53. Marketing Asset Registry

Supabase Central có thể giữ:

``` text
marketing_apps
landing_pages
campaigns
forms
surveys
domains
deployments
versions
aggregate_metrics
```

Local/private giữ detailed operational marketing data theo data-boundary
chung.

------------------------------------------------------------------------

# 54. App Portability

Bắt buộc kiểm thử scenario:

``` text
COSA Shared VPS
      ↓
Export / Transfer
      ↓
Company VPS
      ↓
Configure environment
      ↓
Build
      ↓
Deploy
      ↓
Verify
      ↓
Switch domain
```

Không yêu cầu rewrite application.

Portable package/repository cần chứa: - source; - manifest; - dependency
lockfile; - public assets; - migration instructions nếu app có private
schema; - environment template không có secret; - deployment
instructions.

------------------------------------------------------------------------

# 55. Migration from COSA Managed to Company VPS

Flow đề xuất:

``` text
Founder/Admin chooses Transfer Hosting
        ↓
Entitlement check
        ↓
Prepare repository/package
        ↓
Select target VPS
        ↓
Configure environment/secrets
        ↓
Build target
        ↓
Health check
        ↓
Preview target
        ↓
Domain switch
        ↓
Verify public intake
        ↓
Mark deployment active
```

Old deployment chỉ xóa sau rollback window phù hợp.

------------------------------------------------------------------------

# 56. AI Code Generation Rules

Marketing Agent / Claude Code không được generate app tùy tiện từ blank
project nếu có template/module tương ứng.

Thứ tự:

``` text
1. Inspect company marketing app
2. Inspect COSA module catalog
3. Reuse existing component
4. Extend component nếu cần
5. Create company-specific component
6. Generate dedicated app chỉ khi thật sự cần
```

Mục tiêu: - giảm duplicated code; - dễ update; - giữ design
consistency; - dễ transfer; - tránh AI-generated technical debt.

------------------------------------------------------------------------

# 57. Module Versioning

Shared SDK/module cần version:

``` text
COSA Landing SDK v1.x
Company A app → v1.4
Company B app → v1.6
```

Không force-update production app.

COSA có thể:

``` text
detect update
   ↓
generate compatibility report
   ↓
test
   ↓
founder/admin approve
   ↓
upgrade
```

------------------------------------------------------------------------

# 58. Security

Public app không chứa: - Supabase service-role key; - platform admin
credential; - company database password; - local COSA API secret; -
deployment master token.

Browser chỉ dùng public-safe credentials/API.

Sensitive operations qua: - Public Intake API; - Platform API; - company
backend.

------------------------------------------------------------------------

# 59. Updated Marketing Architecture

``` text
                         COSA PLATFORM
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
   Module/SDK Registry   Deployment Service   Supabase Central
          │                    │                    │
          └──────────────┬─────┴──────────────┬─────┘
                         │                    │
                Company-Owned Apps      Public Intake
                         │                    │
             ┌───────────┼───────────┐        │
             ▼           ▼           ▼        │
          Company A   Company B   Company C   │
          Web App     Web App     Web App     │
             │           │           │        │
             └───────────┴───────────┴────────┘
                         │
              COSA VPS or Company VPS
```

------------------------------------------------------------------------

# 60. Updated Acceptance Criteria --- Marketing/Landing

-   [ ] Mỗi company có marketing app riêng hoặc portable logical app
    riêng.
-   [ ] Một company app hỗ trợ nhiều landing/campaign/survey.
-   [ ] Source code có thể export/transfer.
-   [ ] Không phụ thuộc COSA VPS để chạy vĩnh viễn.
-   [ ] Default deployment có thể dùng COSA subdomain.
-   [ ] Paid entitlement có thể bật custom domain.
-   [ ] Company có thể chuyển app sang VPS riêng.
-   [ ] Transfer không yêu cầu rewrite landing pages.
-   [ ] Form vẫn hoạt động qua COSA Public Intake sau transfer.
-   [ ] Fully Private deployment có thể dùng company intake.
-   [ ] Shared modules/SDK được version.
-   [ ] Marketing Agent ưu tiên reuse module.
-   [ ] Static landing không bắt buộc Node process riêng.
-   [ ] Dynamic/custom app mới dùng runtime/container khi cần.
-   [ ] Source code không tồn tại duy nhất trong Supabase.
-   [ ] Supabase lưu registry/deployment metadata.
-   [ ] Secrets không nằm trong repository/manifest/public bundle.

------------------------------------------------------------------------

# 61. Superseded Guidance

Các phần trước trong tài liệu đề xuất **Shared Landing Runtime** phải
được hiểu theo quyết định mới sau:

``` text
OLD:
One shared application renders landing pages for all companies.

NEW:
Shared SDK / Module Library / Templates
+
Company-Owned Marketing Application
+
Portable Deployment
```

Nếu có xung đột giữa phần cũ và mục 40--61, **mục 40--61 có ưu tiên cao
hơn**.

------------------------------------------------------------------------

# 62. Updated Architecture Principle

> **COSA owns the platform; each company owns its generated digital
> assets.**

Với landing/marketing:

``` text
COSA owns/manages:
├── platform
├── module ecosystem
├── templates
├── deployment automation
├── public intake services
└── platform intelligence

Company owns:
├── marketing app source
├── landing pages
├── brand assets
├── campaign configuration
└── right to move deployment
```

Thiết kế này giúp COSA cung cấp trải nghiệm managed ngay từ
Free/Learning nhưng không tạo vendor lock-in về source code hoặc
hosting. Company có thể trưởng thành từ COSA-managed subdomain sang
custom domain, VPS riêng hoặc fully-private deployment mà vẫn giữ cùng
tài sản số và workflow.
