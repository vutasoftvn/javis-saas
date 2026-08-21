# COSA — AI Marketing System Integration Specification

> **Mục tiêu:** Tích hợp mô hình **Research → Attract → Convert → Retain → Orchestrate (RACRO)** vào COSA hiện tại theo nguyên tắc **không tạo subsystem song song**, không biến COSA thành tập hợp 15 agent/tool rời rạc, và giữ **COSA Co-Founder** là điểm tương tác trung tâm của founder.

---

## 1. Quyết định kiến trúc

### 1.1. Không xây “15 tools = 15 agents”

Hình tham khảo có 15 capability chia thành 5 nhóm. COSA **không nên** triển khai thành 15 agent độc lập.

Cấu trúc chuẩn:

```text
Founder
  ↓
COSA Co-Founder
  ↓
Intent / Domain / Mission Routing
  ↓
Marketing Domain
  ↓
RACRO Move
  ↓
Capability
  ↓
Skill
  ↓
Workflow
  ↓
Tool / Connector
```

Nguyên tắc:

```text
Business Capability > Skill > Workflow > Tool
```

Tool có thể thay đổi; capability kinh doanh không được phụ thuộc vào một nhà cung cấp cụ thể.

Ví dụ:

```text
Demand Intelligence
  ├─ Google Search / Trends
  ├─ Web Search
  ├─ Social Listening
  ├─ CRM Signals
  └─ Competitor Sources
```

Google, Meta, TikTok, Zalo, n8n... chỉ là **adapter/tool**, không phải kiến trúc lõi.

---

## 2. Vị trí của RACRO trong COSA

COSA vẫn là hệ điều hành vận hành doanh nghiệp với **COSA Co-Founder** đồng hành xuyên suốt Research, Marketing, Sales, Operations, Finance, Legal, Projects...

RACRO được dùng như **Marketing Operating Model** bên trong Marketing Center.

```text
                         COSA CO-FOUNDER
                               │
                ┌──────────────┼───────────────┐
                │              │               │
             Projects       Marketing        Sales/CRM
                │              │               │
                │           RACRO Engine       │
                │              │               │
                └──────────────┼───────────────┘
                               │
                            Finance
                               │
                         Revenue / Cost
```

Không đổi kiến trúc runtime nền hiện tại. Runtime tiếp tục đi theo luồng:

```text
Chat / Voice
    ↓
Conversation Guard
    ↓
Intent + Verb + Domain + Specialist Router
    ↓
Mission Orchestrator
    ↓
Agent Kernel
    ↓
Governance Kernel
    ↓
Tool / MCP / n8n / Agent Host
    ↓
Reality Verifier
    ↓
Outcome Certificate
    ↓
Brain / Data / Hologram Hub
```

RACRO là **business-layer classification** nằm trên runtime này.

### Invariant bắt buộc

```text
NO INTENT = NO TOOL
```

Ví dụ founder chỉ nói:

```text
"Chào"
```

COSA trả lời hội thoại bình thường.

Không được:

- tự kiểm tra project;
- tự chạy market research;
- tự truy vấn CRM;
- tự gọi workflow;
- tự đọc mID;
- tự khởi chạy agent.

---

# 3. RACRO chuẩn cho COSA

## 3.1. RESEARCH — Know before you spend

### Capability 1 — Market Intelligence

Mục tiêu:

- quy mô/thay đổi thị trường;
- customer segment;
- ICP;
- Jobs-to-be-Done;
- pain/gain;
- xu hướng;
- search behavior;
- nhu cầu địa phương hoặc ngành;
- hypothesis liên quan đến project.

Output không chỉ là report. Kết quả phải có khả năng trở thành **Evidence** của project.

```text
Research
  ↓
Signal
  ↓
Evidence
  ↓
Linked Assumption / Hypothesis
  ↓
Founder Decision
```

### Capability 2 — Competitor Intelligence

Theo dõi:

- pricing;
- offer;
- landing page;
- content;
- campaign;
- product release;
- SEO;
- social;
- reviews;
- positioning;
- distribution channel.

Không tạo `Competitor Agent` riêng nếu chưa có lý do rõ ràng.

Nên triển khai dưới dạng:

```text
Marketing Specialist
  └─ skill: competitor_intelligence
```

### Capability 3 — Demand Intelligence

Đây là capability quan trọng nhất của Research.

Nguồn signal:

- search;
- social;
- website;
- landing pages;
- form;
- CRM;
- support conversation;
- reviews;
- competitor changes;
- advertising data;
- marketplace/OTA nếu phù hợp ngành;
- offline evidence do founder nhập.

Data contract tối thiểu:

```yaml
signal:
  project_id:
  company_id:
  type:
  source:
  observed_at:
  title:
  summary:
  evidence_url:
  confidence:
  related_segment:
  related_hypothesis:
  expires_at:
```

`confidence` là mức độ tin cậy của nguồn/kết quả AI, **không thay founder xác nhận business hypothesis**.

---

# 4. ATTRACT — Get found first

Không hard-code Local SEO/Google Business Profile/Social cho mọi company.

COSA dùng ba capability tổng quát:

## 4.1. Search & Discovery

Có thể chọn theo company:

- SEO;
- Local SEO;
- Google Business Profile;
- marketplace;
- OTA;
- app store;
- directories;
- community search.

## 4.2. Content & Creative

Bao gồm:

- content strategy;
- content pillar;
- post;
- article;
- video brief;
- image brief;
- landing-page copy;
- email content;
- case study;
- product story.

Content phải truy xuất ngược được về:

```text
Demand Signal
   ↓
Audience / ICP
   ↓
Offer
   ↓
Content
```

Không cho phép Content Agent sinh nội dung vô hạn mà không có campaign/goal/context.

## 4.3. Distribution

Channel là cấu hình động:

```text
Facebook
Instagram
TikTok
LinkedIn
Google
Email
Zalo
Telegram
Website
Community
OTA
Other
```

Mỗi company tự bật/tắt channel tùy ngành và entitlement.

---

# 5. CONVERT — Turn attention into revenue opportunity

Convert phải kết nối trực tiếp với **Sales/CRM**, không nằm riêng trong Marketing.

## 5.1. Campaign & Offer

Object chính:

```text
Campaign
  ├─ Goal
  ├─ Audience
  ├─ Offer
  ├─ Channel
  ├─ Content
  ├─ Landing Page
  ├─ Budget
  ├─ Leads
  └─ Attribution
```

Landing page do COSA sinh vẫn tuân theo kiến trúc deployment hiện tại:

```text
COSA
  ↓
Generate Next.js landing/app
  ↓
Company deployment
  ↓
Company subdomain / custom domain
  ↓
Lead form
  ↓
Local/private CRM
```

Landing page/template của từng company phải có khả năng company tự quản lý và di chuyển về VPS của họ.

## 5.2. Speed-to-Lead

Mục tiêu:

```text
Lead Created
   ↓
Normalize
   ↓
Deduplicate
   ↓
CRM
   ↓
Qualification
   ↓
Immediate Response
   ↓
Sales Owner / Automation
```

Connector có thể là:

- email;
- Zalo;
- Telegram;
- Messenger;
- WhatsApp nếu company có;
- n8n;
- webhook;
- internal notification.

Không gắn logic business trực tiếp vào n8n. n8n chỉ là execution/orchestration adapter.

## 5.3. Intake & Qualification

Lead profile tối thiểu:

```yaml
lead:
  lead_id:
  company_id:
  project_id:
  source:
  campaign_id:
  contact:
  need:
  segment:
  intent:
  urgency:
  budget_signal:
  qualification_score:
  status:
  owner:
  created_at:
```

AI có thể:

- tóm tắt;
- phân loại;
- scoring;
- đề xuất next action;
- route.

Nhưng Sales/CRM vẫn là source of truth của customer pipeline.

---

# 6. RETAIN — Keep them coming back

## 6.1. Follow-Up

Dùng CRM state để tạo workflow:

```text
New Lead
No Response
Qualified
Proposal Sent
Won
Customer
Inactive
Renewal Due
```

Mỗi trạng thái có playbook khác nhau.

Follow-up phải tránh spam và tuân theo:

- channel permission;
- consent;
- company policy;
- frequency limits;
- unsubscribe/opt-out.

## 6.2. Reputation / Reviews

Flow:

```text
Completed Outcome
   ↓
Request Feedback
   ↓
Positive ──────────→ Review / Testimonial
   ↓
Negative
   ↓
Service Recovery / Human Attention
```

Review tốt có thể quay lại:

```text
Review
  ↓
Evidence / Social Proof
  ↓
Landing Page / Content / Sales
```

## 6.3. Referral

Referral là một acquisition loop:

```text
Customer
  ↓
Referral Request
  ↓
Referral Lead
  ↓
CRM
  ↓
New Customer
```

Phải truy xuất `referred_by_customer_id` để attribution không bị mất.

---

# 7. ORCHESTRATE — One brain runs the marketing system

Không tạo một chatbot “Marketing Orchestrator” cạnh COSA Co-Founder.

**COSA Co-Founder / Mission Orchestrator hiện tại là orchestrator cấp cao nhất.**

Marketing chỉ cung cấp domain policy + RACRO capabilities.

## 7.1. Marketing Mission

Contract đề xuất:

```python
from enum import Enum
from pydantic import BaseModel
from typing import Optional, List

class MarketingMove(str, Enum):
    RESEARCH = "research"
    ATTRACT = "attract"
    CONVERT = "convert"
    RETAIN = "retain"
    ORCHESTRATE = "orchestrate"

class MarketingMission(BaseModel):
    company_id: str
    project_id: Optional[str] = None
    move: MarketingMove
    intent: str
    goal: str
    requested_by: str
    capabilities: List[str] = []
    approval_policy: Optional[str] = None
```

### Ví dụ routing

```text
"nghiên cứu đối thủ của mID"
→ Domain: Marketing
→ Move: Research
→ Skill: competitor_intelligence

"tạo chiến dịch thu lead cho khách sạn"
→ Domain: Marketing
→ Move: Attract + Convert
→ Mission: campaign_generation

"có lead nào chưa phản hồi không?"
→ Domain: Sales/CRM
→ Marketing relation: Convert
→ Skill: speed_to_lead_check

"chăm sóc lại khách cũ tháng trước"
→ Domain: CRM
→ Move: Retain
→ Skill: reactivation

"marketing hôm nay có gì cần tôi chú ý?"
→ Domain: Marketing
→ Move: Orchestrate
→ Skill: founder_daily_brief
```

---

# 8. Stage-aware Marketing

Marketing phải biết project đang ở giai đoạn nào.

Không dùng cùng một playbook cho startup mới khám phá vấn đề và company đã có doanh thu.

COSA sử dụng `project_stage` hiện có làm context đầu vào.

Ví dụ policy:

| Project state | RACRO ưu tiên | Hành vi |
|---|---|---|
| Early discovery | Research | thu signal/evidence, hạn chế chi tiền |
| Validation | Research + Attract + Convert | thử offer/channel nhỏ, đo phản hồi |
| Traction | Convert + Retain | tối ưu pipeline, response, repeat |
| Growth | Attract + Convert + Retain + Orchestrate | scale channel dựa trên attribution |

Tên stage thực tế phải lấy từ stage model hiện có; bảng trên là mapping logic, không tạo stage system mới.

---

# 9. Evidence-first Marketing

Mọi Research output quan trọng nên có khả năng liên kết với Evidence hiện tại của COSA.

Data graph:

```text
Project
  ↓
Stage
  ↓
Assumption / Hypothesis
  ↓
Evidence
  ↑
Marketing Signal
  ↑
Research / Campaign / CRM / Review
```

Một campaign thất bại cũng là evidence.

Ví dụ:

```yaml
evidence:
  statement: "ICP nhóm A phản hồi thấp với offer B"
  source_type: "campaign"
  source_id: "cmp_..."
  observed_at: "..."
  metrics:
    impressions: 10000
    leads: 18
    qualified_leads: 2
  interpretation: "Offer/ICP cần xem xét lại"
```

Không để AI tự biến interpretation thành fact.

---

# 10. Data Architecture: Local/Private vs COSA Control Plane

## 10.1. Local / company-owned PostgreSQL

Dữ liệu vận hành chi tiết phải nằm local/private theo company:

- leads;
- customers;
- CRM;
- campaign details;
- content;
- customer conversations;
- reviews có PII;
- referral relationships;
- marketing research nội bộ;
- private documents;
- detailed finance;
- company prompts/overrides;
- company knowledge.

Local/private DB là **Operational System of Record**.

## 10.2. COSA Control Plane — Supabase self-hosted

Control Plane lưu dữ liệu nền tảng cần để COSA quản lý sản phẩm:

- auth;
- companies;
- memberships;
- plan/license;
- entitlements;
- usage;
- project registry;
- project lifecycle/stage/status history;
- cohort/program;
- selected milestones/outcomes;
- deployment/domain registry;
- aggregate product analytics.

Không upload mặc định:

- lead PII;
- CRM conversation;
- customer phone/email;
- full content repository;
- private finance;
- private business documents.

### Aggregate sync đề xuất

Có thể sync:

```yaml
marketing_usage:
  company_id:
  project_id:
  date:
  research_runs:
  campaigns_created:
  leads_count:
  qualified_leads_count:
  customers_count:
  capability_usage:
  project_stage:
```

Revenue milestone chỉ sync theo policy/consent đã được COSA định nghĩa; không mặc định đồng bộ ledger chi tiết.

---

# 11. Knowledge Pack / Skill Pack

RACRO phải tích hợp vào Business Knowledge Pack hiện tại.

## 11.1. Factory Pack

Read-only:

```text
Marketing
├── Research
│   ├── market_intelligence
│   ├── competitor_intelligence
│   └── demand_intelligence
├── Attract
│   ├── search_discovery
│   ├── content_creative
│   └── distribution
├── Convert
│   ├── campaign_offer
│   ├── speed_to_lead
│   └── intake_qualification
├── Retain
│   ├── follow_up
│   ├── reputation
│   └── referral
└── Orchestrate
    ├── marketing_planner
    ├── attribution
    └── founder_brief
```

Mỗi capability có thể chứa:

```text
skill.md
sop.md
prompt.md
templates/
examples/
schemas/
tests/
```

## 11.2. Company Pack

Company có thể override:

- tone;
- brand;
- ICP;
- channel;
- template;
- offer rules;
- qualification rules;
- local SOP;
- response templates.

Precedence:

```text
Company Override > Factory Default
```

Factory update không ghi đè company content.

Chỉ Admin được:

- sửa spec;
- sửa system prompt;
- sửa core workflow;
- reset factory defaults;
- thay đổi security-sensitive connector settings.

---

# 12. Agent Architecture

Không triển khai:

```text
Market Research Agent
Competitor Agent
Demand Agent
SEO Agent
Content Agent
Ads Agent
Lead Agent
Review Agent
...
```

Cấu trúc đề xuất:

```text
COSA Co-Founder
   ↓
Mission Orchestrator
   ↓
Marketing Specialist
   ├─ RACRO capability skills
   ├─ domain context
   └─ tool adapters
```

Có thể spawn worker/agent tạm thời khi mission thật sự cần concurrency, nhưng worker là runtime implementation, không phải 15 “nhân viên AI” cố định trong UI.

Founder chỉ cần biết:

```text
COSA đang làm gì?
Tại sao?
Kết quả?
Evidence?
Điều gì cần quyết định?
```

---

# 13. Hologram Hub

Hologram Hub là CEO Command Center, không phải tool launcher.

## 13.1. Marketing Pulse Card

Đề xuất card:

```text
MARKETING PULSE

Stage
Validation

Demand
↑ 3 signals mạnh trong 7 ngày

Attract
12 content assets
2 active channels

Convert
31 leads
8 qualified
Median response: 6m

Retain
4 follow-ups due
2 reviews received
1 referral lead

Revenue/Pipeline
Pipeline: ...
Attributed revenue: ...

Attention
⚠ 5 leads chưa được phản hồi

COSA Recommendation
Test offer B với ICP A trước khi tăng ngân sách.
```

## 13.2. Marketing Center

Founder view:

```text
Overview
Research
Attract
Convert
Retain
Analytics
```

UI có thể hiển thị RACRO flow ngang/dọc:

```text
Research → Attract → Convert → Retain
                   ↘
                  Orchestrate
```

`Orchestrate` chủ yếu được thể hiện bằng:

- recommendation;
- health;
- alerts;
- attribution;
- daily brief.

Không cần biến thành một màn hình kỹ thuật.

## 13.3. Admin / Inspector

Chỉ Admin cần thấy:

- Agents;
- Prompts;
- Skills;
- Workflows;
- Automations;
- Tools;
- Channels;
- Permissions;
- Connector health;
- Mission trace.

---

# 14. Analytics & Attribution

MVP không cần hệ thống attribution quá phức tạp.

Cần tối thiểu event chain:

```text
Signal
  ↓
Campaign
  ↓
Content / Ad
  ↓
Landing Page
  ↓
Lead
  ↓
Qualified Lead
  ↓
Opportunity
  ↓
Customer
  ↓
Revenue
```

ID cần giữ xuyên suốt:

```text
project_id
campaign_id
content_id
utm_*
landing_page_id
lead_id
opportunity_id
customer_id
revenue_event_id
```

MVP attribution:

- source;
- medium;
- campaign;
- first touch;
- last touch;
- conversion;
- revenue linkage.

Multi-touch attribution triển khai sau khi event data đủ tốt.

Nguyên tắc:

```text
Track the money, not vanity metrics.
```

Không chỉ báo:

- views;
- likes;
- impressions.

Phải liên kết dần tới:

- lead;
- qualified lead;
- opportunity;
- customer;
- revenue;
- retention/referral.

---

# 15. Cross-domain Integration

## Research ↔ Projects

Research signal → Evidence → Stage decision.

## Marketing ↔ Sales/CRM

```text
Campaign → Lead → Qualification → Opportunity → Sale
```

Không duplicate `Lead` giữa hai domain.

Marketing tạo/đẩy lead; CRM sở hữu pipeline.

## Sales/CRM ↔ Retain

Customer state là đầu vào cho:

- follow-up;
- reactivation;
- renewal;
- referral.

## Finance ↔ Attribution

Finance cung cấp:

- recognized revenue;
- campaign cost nếu có;
- CAC inputs;
- margin context.

Marketing không tự tạo “doanh thu giả định”.

## Legal / Governance ↔ Marketing

Marketing workflow phải đọc policy phù hợp trước các hành động như:

- outbound;
- personal data;
- claims;
- regulated content;
- automated publishing.

---

# 16. Tool Adapter Layer

Capability không được gọi vendor trực tiếp trong business logic.

Ví dụ interface logic:

```python
class SearchProvider:
    async def search(self, query: str): ...

class SocialPublisher:
    async def publish(self, channel: str, content: dict): ...

class LeadChannel:
    async def send(self, lead_id: str, message: str): ...

class AdsProvider:
    async def get_campaign_metrics(self, campaign_id: str): ...
```

Adapter có thể là:

```text
Google
Meta
TikTok
Zalo
Telegram
Email
n8n
Hostinger
Web Search
Other MCP
```

COSA có thể đổi provider mà không sửa RACRO business model.

---

# 17. Chat + Voice

Desktop và mobile dùng chung business contract.

```text
Desktop Chat / LiveKit Local
                │
                ├── Shared Session
                ├── Intent
                ├── Domain
                ├── Mission
                ├── Memory
                └── Event Stream
                │
Mobile Chat / LiveKit Cloud
```

Không tạo riêng “voice marketing agent”.

Voice chỉ là interface vào cùng COSA Co-Founder.

---

# 18. Daily Founder Brief

Daily Report trong hình tham khảo nên được chuyển thành **Founder Brief**, không giới hạn ở marketing.

Marketing section:

```yaml
marketing_brief:
  demand_changes:
  campaign_changes:
  new_leads:
  qualified_leads:
  response_risk:
  retention_actions:
  attributed_pipeline:
  attributed_revenue:
  anomalies:
  recommendations:
```

Hologram Hub chỉ hiển thị những gì cần founder chú ý.

Không ép founder mở 10 dashboard.

---

# 19. Event Model đề xuất

Không bắt buộc tạo event-sourcing toàn hệ thống ngay lập tức. Nhưng RACRO nên chuẩn hóa business events.

Ví dụ:

```text
marketing.signal.detected
marketing.campaign.created
marketing.content.published
marketing.lead.created
marketing.lead.qualified
marketing.lead.responded
marketing.customer.converted
marketing.followup.due
marketing.review.received
marketing.referral.created
marketing.attribution.updated
```

Event giúp:

- Hologram Hub realtime;
- automation;
- audit;
- analytics;
- attribution;
- daily brief.

---

# 20. Minimal Data Model

Ưu tiên reuse bảng hiện có.

Chỉ tạo entity mới khi chưa có canonical model.

Logical entities:

```text
MarketingSignal
CompetitorObservation
AudienceSegment / ICP
Offer
Campaign
CampaignAsset
ChannelBinding
AttributionEvent
MarketingRecommendation
```

Reuse:

```text
Project
Evidence
Lead
Customer
Opportunity
Task
Document
Conversation
Revenue
User
Company
```

Quy tắc chống duplication:

```text
Nếu COSA đã có canonical entity → thêm relation/metadata.
Không tạo bảng domain-local thứ hai có cùng ý nghĩa.
```

---

# 21. Migration từ Marketing Center hiện tại

Không rewrite toàn bộ.

## Step 1 — Inventory

Claude Code phải scan:

- current Marketing screens;
- existing agent definitions;
- skills;
- prompts;
- workflows;
- n8n hooks;
- CRM models;
- project/evidence models;
- analytics;
- Hologram cards.

## Step 2 — Mapping

Tạo mapping:

```yaml
existing_component:
  current_name:
  current_path:
  current_type:
  racro_move:
  capability:
  canonical_entity:
  action:
    - keep
    - refactor
    - merge
    - hide_from_founder
    - deprecate
```

## Step 3 — Không tạo parallel subsystem

Nếu đã có:

```text
market_research
```

thì map nó vào:

```text
Research / Market Intelligence
```

Không tạo:

```text
racro_market_research_v2
```

## Step 4 — Add metadata

Skill/workflow hiện có chỉ cần thêm:

```yaml
domain: marketing
move: research
capability: competitor_intelligence
```

## Step 5 — UI consolidation

Founder UI chuyển từ:

```text
Tools / Agents / Automations
```

sang:

```text
Business outcomes / RACRO state
```

---

# 22. Implementation Phases

## Phase A — Architecture Mapping

Deliverables:

- inventory;
- canonical entity map;
- RACRO mapping;
- duplication report;
- migration plan.

Không code feature lớn trước khi hoàn thành phase này.

## Phase B — RACRO Domain Contract

Implement:

- enums;
- capability registry;
- mission contract;
- routing metadata;
- event names;
- permissions.

## Phase C — Research + Evidence

Implement trước:

```text
Market Intelligence
Competitor Intelligence
Demand Intelligence
```

Output có structured signals và link Evidence.

## Phase D — Attract + Convert

Tích hợp:

- content;
- campaign;
- landing;
- lead capture;
- CRM;
- speed-to-lead;
- qualification.

## Phase E — Retain

Tích hợp:

- follow-up;
- review/reputation;
- referral;
- reactivation.

## Phase F — Attribution + Hologram

Xây:

- event chain;
- marketing metrics;
- Marketing Pulse;
- Founder Brief.

## Phase G — Control Plane Aggregation

Chỉ sync aggregate/sanitized product intelligence cần thiết về Supabase Control Plane.

---

# 23. Tests bắt buộc

## Intent Guard

```text
Input: "chào"
Expected:
- no marketing mission
- no project query
- no CRM query
- no tool call
```

## Research Route

```text
Input: "nghiên cứu 5 đối thủ của dự án mID"
Expected:
domain = marketing
move = research
capability = competitor_intelligence
```

## Convert Route

```text
Input: "kiểm tra lead mới chưa được phản hồi"
Expected:
domain = sales/crm
related_move = convert
skill = speed_to_lead_check
```

## Data Locality

Lead có email/phone:

```text
Expected:
stored = company private database
central_supabase_contains_pii = false
```

## Company Override

```text
Factory prompt = A
Company override = B
Expected effective prompt = B
```

Factory update không được ghi đè B.

## Permission

Non-admin:

```text
edit core prompt → denied
reset factory pack → denied
```

## Attribution

```text
Campaign → Lead → Opportunity → Customer → Revenue
```

Phải truy xuất được campaign/source của revenue event nếu dữ liệu có đủ.

---

# 24. Definition of Done

Tích hợp chỉ được coi là hoàn thành khi:

- [ ] Founder chỉ tương tác với COSA Co-Founder; không phải chọn 15 agent.
- [ ] Marketing Center tổ chức theo RACRO/business outcomes.
- [ ] Existing skills/workflows được map, không duplicate.
- [ ] `NO INTENT = NO TOOL` được test.
- [ ] Greeting không kích hoạt project/marketing/CRM.
- [ ] Research signal có thể trở thành Evidence.
- [ ] Project stage ảnh hưởng marketing recommendation.
- [ ] Convert nối chung canonical Lead/CRM.
- [ ] Retain dùng canonical Customer/CRM.
- [ ] Campaign → Lead → Revenue có attribution chain tối thiểu.
- [ ] Hologram Hub có Marketing Pulse/Founder Brief.
- [ ] Tool/vendor nằm sau adapter.
- [ ] Company data/private PII nằm local/private.
- [ ] Supabase Control Plane chỉ nhận dữ liệu platform/aggregate đã quy định.
- [ ] Factory Pack và Company Override hoạt động đúng precedence.
- [ ] Chỉ Admin sửa/reset prompt/spec/core workflow.
- [ ] Desktop LiveKit Local và Mobile LiveKit Cloud dùng chung session/mission runtime.

---

# 25. Prompt triển khai cho Claude Code

```text
Bạn đang làm việc trên codebase COSA hiện tại.

MỤC TIÊU
Tích hợp RACRO Marketing Operating Model:
Research → Attract → Convert → Retain → Orchestrate
vào kiến trúc hiện hữu, KHÔNG tạo một subsystem marketing mới chạy song song.

CÁC INVARIANT
1. COSA Co-Founder là điểm tương tác trung tâm.
2. Reuse Mission Orchestrator, Agent Kernel, Governance Kernel, Tool/MCP/n8n layer.
3. NO INTENT = NO TOOL.
4. Không tạo 15 permanent agents.
5. Capability > Skill > Workflow > Tool.
6. Reuse canonical Project, Evidence, Lead, Customer, Opportunity, Task, Revenue nếu đã tồn tại.
7. Local/private company DB là operational system of record cho CRM, customer, content, private research, finance detail.
8. Supabase Control Plane chỉ lưu auth/company/license/entitlements/project registry/lifecycle/aggregate product intelligence theo policy.
9. Factory Pack read-only; Company Override có precedence cao hơn; factory update không overwrite company content.
10. Core prompt/spec/workflow chỉ Admin được sửa/reset.
11. Founder UI không expose technical agent/tool complexity.
12. Desktop voice LiveKit Local và mobile LiveKit Cloud dùng chung session/intent/mission runtime.

PHASE 1 — INSPECT FIRST
Không sửa code ngay.
Hãy scan repo và xuất:
- architecture inventory;
- Marketing Center components;
- existing agents;
- prompts;
- skills;
- workflows;
- tools/connectors;
- CRM entities;
- Project/Stage/Evidence entities;
- Hologram Hub cards;
- analytics/event model;
- Supabase/local DB boundaries.

PHASE 2 — MAP
Lập bảng:
current component → RACRO move → capability → canonical entity → action.
Action chỉ được là:
KEEP / REFACTOR / MERGE / HIDE_FROM_FOUNDER / DEPRECATE.

Phát hiện mọi duplication có nguy cơ tạo parallel subsystem.

PHASE 3 — PLAN
Đề xuất minimal-diff implementation plan theo dependency order.
Chưa code nếu có xung đột source of truth.

PHASE 4 — IMPLEMENT
Tạo RACRO metadata/contracts trước.
Sau đó lần lượt:
Research/Evidence
→ Attract
→ Convert/CRM
→ Retain
→ Attribution
→ Hologram/Founder Brief.

PHASE 5 — TEST
Bắt buộc test:
- "chào" => zero tool calls;
- research routing;
- speed-to-lead routing;
- local PII boundary;
- admin permission;
- company override precedence;
- campaign-to-revenue attribution;
- desktop/mobile shared mission contract.

OUTPUT MỖI PHASE
1. Files inspected/changed
2. Architecture decision
3. Why
4. Risks
5. Tests
6. Migration impact
7. Next smallest step

KHÔNG:
- tạo racro_v2;
- tạo 15 agents;
- duplicate Lead/Customer/Project/Evidence;
- hard-code Google/Meta/n8n vào domain logic;
- đưa CRM PII về central Supabase mặc định;
- tự trigger tool khi không có intent rõ ràng.
```

---

# 26. Kết luận kiến trúc

Giá trị lớn nhất của mô hình trong hình không phải là “15 AI tools”.

Đối với COSA, mô hình đúng là:

```text
COSA Co-Founder
      ↓
Business Intent
      ↓
Domain
      ↓
RACRO Move
      ↓
Capability
      ↓
Skill / Workflow
      ↓
Tool
      ↓
Evidence / CRM / Revenue
      ↓
Hologram Hub
      ↓
Founder Decision
```

Ba nguyên tắc cần giữ:

1. **Founder nhìn business system; COSA xử lý technical system phía sau.**
2. **Marketing phải nối Research → Evidence → Acquisition → CRM → Revenue → Retention.**
3. **Không xây thêm tool; xây một operating engine trên đúng kiến trúc COSA hiện tại.**
