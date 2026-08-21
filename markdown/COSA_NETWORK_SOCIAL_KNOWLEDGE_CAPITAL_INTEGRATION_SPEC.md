# COSA Network — Social, Knowledge & Capital Integration Specification

**Status:** Draft v1.0  
**Date:** 2026-08-21  
**Codebase baseline:** `vutasoftvn/javis-saas` `main` (reviewed against latest visible commit `49289b9633abfadfc5c19083f8c8970e4118bdb9`)  
**Recommended repository path:** `docs/architecture/COSA_NETWORK_SOCIAL_KNOWLEDGE_CAPITAL_INTEGRATION.md`  
**Related design documents:**
- `docs/architecture/COSA_STARTUP_COFOUNDER_METHODOLOGY.md` — startup operating methodology.
- `docs/architecture/COSA_CAPITAL_NETWORK_INVESTOR_INTELLIGENCE.md` — detailed capital/investor sub-domain.

---

## 1. Executive Summary

COSA should not build a generic “LinkedIn for startups”. The recommended product is **COSA Network**: a professional network in which people, companies, projects, operating evidence, knowledge and capital relationships are connected to the same underlying COSA operating graph.

The product hierarchy should be treated as:

```text
COSA OS
= where founders operate the company

COSA Network
= shared professional/network layer

COSA Knowledge
= publishing, expertise and premium knowledge layer

COSA Capital
= investor discovery, fundraising and capital relationship layer

COSA Investor
= investor-facing mobile/web experience over COSA Network + COSA Capital
```

The strategic differentiator is not social posting. It is the ability to connect public professional identity and content to **live company/project intelligence** produced by COSA while preserving a strict publication boundary.

```text
Founder operates company in COSA
        ↓
Local PostgreSQL holds private operating truth
        ↓
COSA derives safe, founder-approved projections
        ↓
Platform Outbox / policy-controlled sync
        ↓
Central PostgreSQL
        ↓
┌──────────────────────────────────────────────────┐
│                 COSA NETWORK                     │
│                                                  │
│ Person Graph                                     │
│ Company / Project Graph                          │
│ Content / Knowledge Graph                        │
│ Capital Graph                                    │
│ Reputation / Trust Graph                         │
└──────────────────────────────────────────────────┘
        ↓                         ↓
Professional Feed          Investor / Knowledge UX
        ↓                         ↓
Comments, follows, saves, investor interest, reads
        ↓
Central signals / summarized events
        ↓
Local COSA AI Co-founder
        ↓
Founder insight / next best action
```

The implementation must preserve COSA’s current architecture rules:

1. **Business Core remains independent from model providers and social/payment vendors.**
2. **Company operational data is private/local by default.**
3. **One authority per aggregate; no active-active ownership.**
4. **Do not duplicate Company, Project, Task, Workforce or Agent architecture.**
5. **Use the existing PlatformOutbox/PlatformInbox for Local ↔ Central events.**
6. **Data classification and audience authorization are separate concerns.**
7. **Never expose raw local business aggregates as social/public records.**
8. **Investor/social engagement is a signal, not automatically business evidence.**
9. **Paid membership should precede creator payout complexity.**
10. **Moderation, identity trust, conflict disclosure and publication safety are P0 capabilities, not later polish.**

---

## 2. Basis in the Current COSA Codebase

This specification is based on the current repository architecture rather than a greenfield redesign.

### 2.1 Canonical architecture rules already exist

`CLAUDE.md` defines COSA as a Founder / Company Operating System with a composable agent harness and requires architecture-first reuse. It explicitly separates Business Core from Google ADK, DeepSeek Harness and model-provider internals. It also defines the local-first principle and deterministic permission requirements.

Relevant current paths:

```text
CLAUDE.md

docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md

backend/core
backend/app/workforce/agents/runtime
backend/app/workforce/agents/governance
backend/app/core/tool_registry.py
backend/app/platform
backend/app/platform/sync
frontend/lib
```

### 2.2 Business domain ownership must not be duplicated

`COSA_CANONICAL_OWNERSHIP_MAP.md` establishes:

```text
Workspace = Company / tenant
OperatingUnit + Offering = Business Core entities
Initiative = existing operational record
Task = WorkItem engine
Project = linked strategy record
```

Therefore COSA Network must **not** introduce:

```text
CompanyV2
StartupCompany
SocialCompany
InvestorProject
NetworkProject
```

as replacement aggregates for existing Company/Workspace or Project.

Central network records are **projections/network identities**, not a second operating authority.

### 2.3 Existing Project model is already network-addressable

Current `backend/core/strategy/project.py` contains:

```text
Project.workspace_id
Project.title
Project.description
Project.status
Project.project_type
Project.strategic_priority
Project.project_stage
Project.stage_goal
Project.critical_constraints
Project.exit_criteria_jsonb
Project.stage_metadata
Project.platform_project_id
Project.sync_status
Project.last_synced_at
```

Current canonical stage vocabulary is:

```text
S0_EXPLORE
S1_PROBLEM_VALIDATION
S2_SOLUTION_VALIDATION
S3_BUSINESS_VALIDATION
S4_GO_TO_MARKET
S5_OPERATE_GROWTH
S6_SCALE_GOVERN
```

COSA Network must reuse this lifecycle vocabulary for company/project intelligence. It must not create another `IDEA/MVP/GROWTH/...` social stage taxonomy.

### 2.4 Existing validation/evidence chain is a major differentiator

`backend/core/validation/evidence_chain.py` already defines:

```text
ValidationAssumption
        ↓
ValidationHypothesis
        ↓
ValidationExperiment
        ↓
ValidationEvidence
        ↓
ValidationReview
        ↓
ValidationDecision
```

This enables COSA to publish **evidence-linked summaries** instead of allowing every company claim to remain an unqualified marketing assertion.

COSA Network must never expose raw evidence attachments automatically. It should derive an explicitly publishable projection.

### 2.5 Existing Local ↔ Central synchronization must be reused

`backend/app/platform/sync/models.py` provides:

```text
PlatformOutbox
PlatformInbox
LocalEntitlementSnapshot
```

`PlatformOutbox` already carries:

```text
event_id
event_type
aggregate_type
aggregate_id
company_id
classification
payload
status
retry_count
acknowledgement timestamps
```

This is the correct delivery seam for publishable operating updates and selected Central → Local network signals. Do not build a second social sync engine.

### 2.6 Existing platform taxonomy already supports data classification

`backend/app/platform/sync/schemas.py` defines:

```text
PLATFORM_REQUIRED
ANALYTICS_REQUIRED
PUBLIC
COMPANY_PRIVATE
SENSITIVE
SECRET
```

It also already defines platform user/company/membership sync contracts and a standard platform event envelope.

Important architectural rule:

> `DataClassificationEnum` describes what class of data a payload belongs to. It must not be overloaded to represent who is allowed to read a social item.

For example, a premium article can be safe for the platform (`PUBLIC` classification from a data-sensitivity standpoint) but accessible only to entitled members. Therefore COSA Network needs an orthogonal `AudienceScope`/access policy.

### 2.7 Entitlement infrastructure exists, payment infrastructure is not established

Current entitlement contracts include:

```text
SignedEntitlementSnapshot
EntitlementLimits
EntitlementFeatures
```

and `backend/app/platform/sync/entitlement_guard.py` enforces feature access through verified workspace context.

This makes **paid platform membership** technically aligned with the existing codebase.

This does **not** mean COSA currently has a creator marketplace settlement system. Paid article purchase, platform fees, refunds, creator balances, payout, KYC and tax/reconciliation must be treated as new capabilities.

### 2.8 Existing platform audit primitive can be reused selectively

`backend/app/platform/core/models.py` contains `AuditLog` with actor/action/target/metadata/timestamp semantics. It is useful as an audit pattern for moderation and sensitive administrative actions.

Before direct reuse for all Central network operations, ID compatibility and tenancy semantics must be audited because network identities may use platform UUIDs while current audit IDs are BigInteger fields.

### 2.9 Flutter has mobile platform scaffolding

The current `frontend` is Flutter and includes:

```text
frontend/android
frontend/ios
frontend/web
frontend/macos
frontend/windows
frontend/linux
```

The existence of mobile platform folders means COSA can reuse Flutter as a delivery technology. It does **not** prove the current desktop-oriented UX and service layer are already mobile-ready. Network UX should be built responsively and validated on iOS/Android from the first Network phase.

---

## 3. Product Definition

### 3.1 COSA Network

COSA Network is a professional network connecting:

```text
Person
Founder
Investor
Expert
Operator
Company
Project
Knowledge
Content
Evidence-backed public claims
Capital opportunities
Investor thesis
Professional relationships
```

It is not a generic consumer social network.

### 3.2 Core Jobs to Be Done

**Founder**

```text
Build a credible professional identity
Make the company/project discoverable
Publish progress without manually rewriting operating data
Learn from investors and experts
Build long-term investor relationships
Receive qualified feedback
Raise capital when appropriate
```

**Investor**

```text
Discover companies/projects matching investment thesis
Follow execution over time
Read structured operating/evidence summaries
Build public professional reputation
Publish thesis and knowledge
Save/watch opportunities
Request introduction / data-room access
```

**Expert / Creator**

```text
Build domain reputation
Publish high-signal knowledge
Attract founders/investors
Offer premium research/knowledge later
Potentially monetize expertise after payment/payout infrastructure matures
```

**Paid professional member**

```text
Access advanced discovery, premium knowledge and AI intelligence
without requiring creator payouts in the first commercial phase
```

---

## 4. Product Boundary

### 4.1 V1 should include

```text
Professional profile
Company network profile
Project network profile
Follow graph
Post / article publishing
Comments / replies
Reactions
Save / bookmark
Topic / expertise tagging
Role-aware feed
Company/project update drafts generated from COSA operating events
Founder-controlled publication
Evidence provenance labels
Investor profile / thesis integration
Investor watch/follow
Intro request integration
Notification center
Basic moderation/report/block
Feature entitlement gates
```

### 4.2 V1 should not include

```text
Open marketplace for anyone to sell anything
Native securities transactions
Invest Now button
Escrow
SPV / syndication
Automated investment recommendations
Creator cash wallet
Creator payout
Complex revenue sharing
Tips/donations
Paid boosting that changes organic ranking without explicit sponsorship labeling
Anonymous fundraising
Unmoderated direct messaging at scale
```

### 4.3 Commercial expansion sequence

Recommended sequence:

```text
1. Free network + Founder/Investor professional value
2. Paid COSA membership / premium network entitlements
3. Premium knowledge access bundled with membership
4. Paid individual content / creator subscription
5. Creator earnings ledger
6. KYC + payout + refund/chargeback/reconciliation
7. Tips / consultation marketplace only after trust and compliance maturity
```

---

## 5. Unified Graph Model

COSA Network should be designed around five connected graphs rather than around a single feed table.

```text
PERSON GRAPH
Person ─ role ─ Company ─ Project
  │                    │
  └ follow / expertise ┘

CONTENT GRAPH
Author ─ ContentItem ─ Topic
            │
            ├ Company
            ├ Project
            ├ InvestorThesis
            └ ClaimProvenance

COMPANY GRAPH
Company ─ Project ─ Stage ─ Milestone ─ Public Projection

CAPITAL GRAPH
Investor ─ Thesis ─ Opportunity ─ Interest ─ IntroRequest ─ DataRoomAccess

TRUST GRAPH
IdentityVerification
Expertise
Disclosures
ModerationHistory
ContentQualitySignals
OutcomeHistory
```

The feed is a read model over these graphs; it is not the core domain model.

---

## 6. Identity Model

### 6.1 PersonProfile must be separate from operating FounderProfile

Do not turn an internal founder operating profile into a public professional identity.

Proposed Central entity:

```text
PersonProfile
- platform_user_id
- handle
- display_name
- headline
- bio
- avatar_url
- location
- country_code
- website_url
- profile_visibility
- verification_state
- created_at
- updated_at
```

### 6.2 A person may have multiple professional roles

Do not create separate user accounts for Founder, Investor, Advisor or Creator.

```text
ProfessionalRole
- person_id
- role_type
- organization_ref
- title
- start_date
- end_date
- is_current
- verification_state
```

Example role vocabulary:

```text
FOUNDER
COFOUNDER
INVESTOR
FUND_MANAGER
EXPERT
ADVISOR
OPERATOR
RESEARCHER
MENTOR
CREATOR
```

### 6.3 Company membership must reuse existing company identity

Network membership should resolve against existing platform user/company identity instead of inventing a social Company owner concept.

Proposed Central projection:

```text
CompanyNetworkMembership
- platform_company_id
- platform_user_id
- professional_role
- public_title
- public_since
- visibility
- verification_state
```

This is a network projection of the relationship, not a replacement for local Workspace membership or `WorkforceMember`.

---

## 7. Company and Project Network Profiles

### 7.1 CompanyNetworkProfile

Central network representation should be a projection keyed by existing `platform_company_id`.

```text
CompanyNetworkProfile
- platform_company_id
- slug
- display_name
- logo
- headline
- public_summary
- industry
- geography
- website
- startup_stage_summary
- publication_state
- latest_snapshot_version
- published_at
- updated_at
```

Do not store private accounting, CRM or raw validation data in this profile.

### 7.2 ProjectNetworkProfile

```text
ProjectNetworkProfile
- platform_project_id
- platform_company_id
- slug
- title
- short_summary
- project_type
- project_stage
- problem_summary
- solution_summary
- business_model_summary
- traction_summary
- evidence_summary
- fundraising_summary
- publication_state
- latest_snapshot_version
```

### 7.3 Publication snapshots are mandatory

Never make the Central social profile a direct serialization of the Local Project model.

Use:

```text
Local Project / Company
        ↓
Publication Policy Engine
        ↓
Publication Snapshot
        ↓
Founder approval / configured policy
        ↓
Central Network Profile
```

A snapshot should contain only fields explicitly allowed for its audience.

---

## 8. Data Classification vs Audience Scope

Two orthogonal dimensions are required.

### 8.1 Existing DataClassification

Reuse the current sync classification:

```text
PLATFORM_REQUIRED
ANALYTICS_REQUIRED
PUBLIC
COMPANY_PRIVATE
SENSITIVE
SECRET
```

### 8.2 Proposed AudienceScope

```text
PRIVATE
COMPANY
NETWORK
PUBLIC
INVESTOR
ENTITLED
DATA_ROOM
```

Interpretation:

| Audience | Meaning |
|---|---|
| PRIVATE | author/founder only |
| COMPANY | company members only |
| NETWORK | authenticated COSA Network users |
| PUBLIC | publicly accessible surface |
| INVESTOR | verified/authorized investor audience |
| ENTITLED | requires a product entitlement/subscription |
| DATA_ROOM | explicit grant required |

### 8.3 Why these must stay separate

Examples:

```text
Premium article:
classification = PUBLIC
access = ENTITLED

Private operating KPI:
classification = COMPANY_PRIVATE
access = PRIVATE or COMPANY

Public company milestone:
classification = PUBLIC
access = PUBLIC

Investor-only raise detail:
classification = PUBLIC or PLATFORM_REQUIRED depending payload
access = INVESTOR
```

No permission decision should be delegated to an LLM.

---

## 9. Content Model

Do not create a one-table design where every object is just `Post`.

### 9.1 ContentItem

Proposed Central aggregate:

```text
ContentItem
- id
- author_person_id
- author_company_id nullable
- content_type
- title nullable
- body
- summary nullable
- audience_scope
- monetization_mode
- status
- language
- canonical_url nullable
- published_at
- edited_at
- created_at
```

### 9.2 Content types

```text
SHORT_POST
ARTICLE
INVESTOR_MEMO
COMPANY_UPDATE
PROJECT_UPDATE
CASE_STUDY
KNOWLEDGE_NOTE
QUESTION
ANALYSIS
RESEARCH
FUNDRAISING_UPDATE
EVENT_NOTE
```

### 9.3 Content associations

```text
ContentAssociation
- content_id
- entity_type
- entity_id
- association_type
```

Entities can include:

```text
PERSON
COMPANY
PROJECT
TOPIC
INVESTOR_THESIS
OPPORTUNITY
EVIDENCE_PROJECTION
```

This association layer is critical for semantic feed ranking and knowledge graph construction.

### 9.4 Revision/version history

Professional and paid content should be auditable.

```text
ContentRevision
- content_id
- revision_no
- body_snapshot
- changed_by
- change_reason nullable
- created_at
```

Do not overwrite paid research without a history trail.

---

## 10. Social Graph and Interaction Model

### 10.1 Follow graph

```text
NetworkFollow
- follower_person_id
- target_type
- target_id
- created_at
```

Targets:

```text
PERSON
COMPANY
PROJECT
TOPIC
```

### 10.2 Reactions

Keep reaction semantics small initially.

```text
LIKE
INSIGHTFUL
SUPPORT
```

Avoid a large consumer-social reaction taxonomy.

### 10.3 Comments and replies

```text
Comment
- id
- content_id
- parent_comment_id nullable
- author_person_id
- body
- status
- created_at
- edited_at
```

Investor comments may additionally carry verified investor identity and disclosure metadata, but a comment remains a social signal rather than validation evidence.

### 10.4 Saves/bookmarks

Save is a high-value intent signal and should be first-class:

```text
SavedItem
- person_id
- target_type
- target_id
- collection_id nullable
- created_at
```

Investor saves of companies/projects may feed Capital watchlists, subject to policy.

---

## 11. Knowledge Graph

### 11.1 Topics

```text
Topic
- id
- slug
- name
- parent_topic_id nullable
- taxonomy_version
```

Examples:

```text
ClimateTech
Industrial Energy Efficiency
B2B SaaS
Seed Investing
Pricing
Customer Discovery
Project Finance
Vietnam
SEA
```

### 11.2 Expertise signals

Do not assign expertise solely from self-declared profile text.

Potential inputs:

```text
Declared expertise
Published content
High-quality saves
Citations
Professional roles
Investments / company roles when verified
Repeated topic engagement
Paid subscriber retention later
```

Do not compress this into a single opaque “expert score” in V1.

### 11.3 AI-derived knowledge extraction

COSA AI may propose:

```text
content topics
entity associations
summary
key claims
opinion vs factual claim classification
potential disclosures
```

Human author remains responsible for publication.

---

## 12. Claim Provenance and Evidence Projection

This is a central differentiator of COSA Network.

### 12.1 Provenance types

Proposed display semantics:

```text
FOUNDER_STATEMENT
AUTHOR_OPINION
COSA_OPERATING_DATA
EVIDENCE_LINKED
EXTERNAL_SOURCE
SPONSORED_CLAIM
```

Do not display “COSA Verified Startup” as a generic badge implying investment endorsement.

### 12.2 Evidence-linked company claims

Example:

```text
Claim:
"5 paid industrial pilots completed"

Provenance:
COSA operating data

Evidence status:
Supported by publishable operating records
```

The Central record should store a safe provenance pointer / projection version, not raw private evidence files.

### 12.3 Opinion remains opinion

Example investor statement:

```text
"I believe industrial cooling AI will become a major category."
```

should be labeled/treated as opinion. COSA must not imply factual verification.

### 12.4 Social engagement is not validation evidence

Never infer:

```text
100 likes = problem validated
20 comments = market validated
10 investor saves = investment readiness proven
```

Network activity should enter an `ExternalSignal`/network-signal layer and may cause the AI Co-founder to recommend a new experiment.

---

## 13. Operating Event → Social Update Pipeline

The most defensible social feature is automatic **drafting**, not automatic publication.

### 13.1 Candidate operating events

Examples already compatible with current Project/sync intelligence:

```text
project.stage_changed
project.milestone_reached
project.first_customer
project.first_revenue
project.paused
project.closed
```

Additional internal milestones can be transformed into publication candidates if the source data is allowed.

### 13.2 Safe publishing workflow

```text
Operating event
     ↓
PublicationCandidateService
     ↓
Safety / data policy filter
     ↓
AI draft generation
     ↓
Founder review
     ↓
Audience selection
     ↓
Publish
     ↓
PlatformOutbox event
     ↓
Central ContentItem + profile update
```

### 13.3 Default policy

Default must be:

```text
AUTO_DRAFT = allowed
AUTO_PUBLISH = disabled
```

Auto-publish may be introduced only as an explicit company-level policy for low-risk fields/events.

### 13.4 AI must not infer undisclosed numbers

If local state only contains a revenue band, the draft may say a band or “revenue milestone reached” according to publication policy; it must not manufacture a precise value.

---

## 14. Feed Architecture

### 14.1 Feed is a Central read model

Do not sync an entire feed into Local PostgreSQL.

Central owns:

```text
following graph
content inventory
reactions
comments
saves
ranking signals
```

Clients query feed APIs directly.

### 14.2 V1 ranking

Start deterministic and explainable:

```text
FeedScore
= relationship relevance
+ professional/topic relevance
+ recency
+ company/project relevance
+ investment thesis relevance when investor
+ quality/trust signals
- spam/risk penalties
```

Do not begin with an opaque deep-learning recommender.

### 14.3 Role-aware feed

Founder feed:

```text
company/project updates from network
investor/expert knowledge
relevant questions
fundraising/market content
```

Investor feed:

```text
followed company/project updates
thesis-fit discoveries
founder insights
sector research
material milestones
```

Expert feed:

```text
domain questions
high-signal founder/project updates
research and discussions
```

### 14.4 Semantic ranking later

PostgreSQL full-text search and vector capabilities may later support semantic discovery, but implementation should first audit the Central database extensions and existing search infrastructure. Do not assume local `pgvector` use automatically means Central feed vector search is already provisioned.

---

## 15. Capital Network Integration

COSA Network must not build a separate investor social silo.

The detailed Capital Network model remains a specialized sub-domain, sharing the same identities and company/project graph.

```text
PersonProfile
   │
   ├ ProfessionalRole(INVESTOR)
   │
   └ InvestorProfile
          ↓
    InvestmentThesis
          ↓
       Watchlist
          ↓
Company / Project
          ↓
 InvestmentInterest
          ↓
    IntroRequest
          ↓
   DataRoomAccess
```

### 15.1 Shared entities

Reuse across Social and Capital:

```text
PersonProfile
CompanyNetworkProfile
ProjectNetworkProfile
Topic
Follow
SavedItem
Notification
ContentItem
Disclosure
Verification
```

### 15.2 Capital-specific entities

Remain under Capital domain:

```text
InvestorProfile
InvestmentThesis
FundraisingRound
InvestmentOpportunity
InvestmentInterest
IntroRequest
InvestorPipelineState
DataRoomAccessGrant
StrategicInvestorProposal
```

### 15.3 Social behavior improves capital intelligence

Examples of allowed signals:

```text
Investor follows Project A
Investor saves Project A
Investor repeatedly reads Project A updates
Investor comments on Project A
Investor requests introduction
```

These may influence relationship prioritization, but COSA must not convert passive behavior into a claim such as “Investor will invest”.

---

## 16. AI Co-founder Integration

The AI Co-founder should use COSA Network as a new signal source and publishing assistant, not as an autonomous social-media agent.

### 16.1 Publish assistant

```text
Detect material milestone
→ suggest whether it is worth sharing
→ generate safe draft from allowed projection
→ explain source/provenance
→ founder edits/approves
```

### 16.2 Network signal analysis

```text
Central network signals
      ↓
selected/summarized PlatformInbox event
      ↓
Local signal processor
      ↓
AI Co-founder
      ↓
"9 qualified investors asked about installation time"
      ↓
recommend a validation / product experiment
```

### 16.3 Creator assistant

For investors/experts:

```text
research organization
outline
summary
topic extraction
citation assistance
translation
claim/disclosure checks
```

The author remains the author. AI-generated text must not silently imply that COSA endorses the investment opinion.

### 16.4 Content-to-thesis intelligence

With consent and appropriate policy, repeated investor content can improve a structured thesis model:

```text
explicit thesis settings
+
content topics
+
portfolio/public roles
+
follow/save behavior
```

Implicit inference must remain distinguishable from explicit investor preferences.

---

## 17. Event Integration

### 17.1 Local → Central events

Extend the current platform event mechanism instead of creating a network-specific transport.

Proposed events:

```text
network.company_profile_published
network.company_profile_unpublished
network.project_profile_published
network.project_profile_unpublished
network.content_published
network.content_updated
network.content_unpublished
network.publication_snapshot_updated
capital.fundraising_projection_published
```

Payload rules:

```text
must use platform UUID identity
must carry classification
must be idempotent
must contain snapshot version
must not contain SECRET data
must not contain raw private attachments
```

### 17.2 Central → Local events

Do not mirror every like/comment locally. Only push operationally relevant signals.

Proposed:

```text
network.signal_summary.updated
network.material_comment.flagged
capital.investor_interest.created
capital.intro_request.created
capital.data_room_request.created
capital.strategic_proposal.created
network.moderation_action.applied
```

### 17.3 Batch low-value engagement

For example, instead of 500 inbox events for reactions:

```text
network.signal_summary.updated
{
  "content_id": "...",
  "period": "24h",
  "qualified_investor_saves": 7,
  "founder_saves": 12,
  "comments": 9,
  "recurring_questions": [...]
}
```

This keeps local operating systems focused on actionable information.

---

## 18. Proposed Backend Ownership

This section is a proposal and must be finalized by ADR before implementation.

### 18.1 Central Network authority

Recommended new platform bounded context:

```text
backend/app/platform/network/
├── models.py
├── schemas.py
├── services/
│   ├── identity_service.py
│   ├── profile_service.py
│   ├── content_service.py
│   ├── social_graph_service.py
│   ├── feed_service.py
│   ├── search_service.py
│   ├── moderation_service.py
│   ├── disclosure_service.py
│   └── notification_service.py
├── routers/
│   ├── profiles.py
│   ├── content.py
│   ├── feed.py
│   ├── graph.py
│   ├── search.py
│   └── moderation.py
└── policies/
    ├── audience.py
    ├── publication.py
    └── ranking.py
```

Why `backend/app/platform/network` rather than `backend/core/marketing`:

- Social identity is platform-wide, not a company marketing aggregate.
- Investor/expert users may not belong to the startup whose content they consume.
- Feed, follow, comment and creator access are Central network authority.
- Marketing remains the company’s operating marketing domain.

### 18.2 Local publication support

Do not create a second network database locally.

Add only the minimum local business-side pieces required to make safe projections and founder decisions. Candidate locations should be selected after import/ownership audit. Logical capabilities are:

```text
PublicationPolicy
PublicationCandidate
PublicationSnapshotBuilder
NetworkSignalIngestion
```

If persistence is required for business-owned publication decisions, models should follow the canonical Business Core ownership rules rather than being hidden inside an AI runtime package.

### 18.3 Capital domain

Capital-specific Central network models may either live under:

```text
backend/app/platform/network/capital/
```

or a sibling:

```text
backend/app/platform/capital/
```

The key rule is **one capital authority**, shared by social/investor clients. Do not keep one Capital model for Investor App and another in Founder Finance.

### 18.4 Payment integration later

Recommended external integration seam:

```text
backend/app/integrations/payments/
```

Provider-specific SDKs belong here, not in Business Core.

Platform commerce state may live in a Central bounded context such as:

```text
backend/app/platform/commerce/
```

with deterministic order/access/ledger models.

---

## 19. Proposed Central Logical Data Model

This is a logical design, not a final Alembic schema.

```text
platform_users (existing platform identity / authority to audit)
    │
    └── person_profiles
           │
           ├── professional_roles
           ├── expertise_declarations
           ├── identity_verifications
           ├── network_follows
           ├── saved_items
           └── creator_profiles

platform_companies / company identity
    │
    ├── company_network_profiles
    ├── company_network_memberships
    └── company_publication_snapshots

platform_projects / platform project identity
    │
    ├── project_network_profiles
    └── project_publication_snapshots

content_items
    │
    ├── content_revisions
    ├── content_associations
    ├── content_topics
    ├── content_claims
    ├── reactions
    ├── comments
    ├── saved_items
    └── content_disclosures

topics
    └── topic_relations

network_notifications
moderation_reports
moderation_actions
blocks

capital...
    ├── investor_profiles
    ├── investment_theses
    ├── fundraising_rounds
    ├── investment_opportunities
    ├── investment_interests
    ├── intro_requests
    └── data_room_access_grants
```

Do not build all tables in one migration. Introduce by phase and only after ownership review.

---

## 20. API Surface — Proposed

### 20.1 Identity and profiles

```text
GET    /network/me
PATCH  /network/me/profile
GET    /network/people/{handle}
GET    /network/companies/{slug}
GET    /network/projects/{id-or-slug}
POST   /network/{target}/follow
DELETE /network/{target}/follow
```

### 20.2 Content

```text
POST   /network/content
GET    /network/content/{id}
PATCH  /network/content/{id}
POST   /network/content/{id}/publish
POST   /network/content/{id}/unpublish
POST   /network/content/{id}/reaction
POST   /network/content/{id}/comments
GET    /network/content/{id}/comments
POST   /network/content/{id}/save
```

### 20.3 Feed/search

```text
GET /network/feed
GET /network/search
GET /network/topics/{slug}/feed
GET /network/discover/people
GET /network/discover/companies
GET /network/discover/projects
```

### 20.4 Company-side publication

```text
GET  /projects/{project_id}/network/publication-preview
POST /projects/{project_id}/network/publish
POST /projects/{project_id}/network/unpublish
GET  /projects/{project_id}/network/update-candidates
POST /projects/{project_id}/network/update-candidates/{id}/publish
```

### 20.5 Capital integration

Capital endpoints should follow the dedicated Capital spec, but must reuse `/network` identities and shared content/profile objects.

---

## 21. Frontend Architecture

### 21.1 One shared Flutter domain module first

Recommended:

```text
frontend/lib/modules/network/
├── models/
├── services/
├── controllers/
├── views/
│   ├── feed/
│   ├── people/
│   ├── companies/
│   ├── projects/
│   ├── knowledge/
│   └── notifications/
└── widgets/
```

Capital-specific screens can be nested or composed with the existing strategy/funding UI as appropriate.

### 21.2 Avoid immediate code duplication for COSA Investor

Do not create an entirely separate Flutter codebase on day one.

Prefer:

```text
shared services/models/widgets
+ role-aware navigation
+ responsive/mobile views
```

A separate `COSA Investor` app shell can be extracted later if store positioning or release cadence requires it.

### 21.3 Founder navigation

Suggested mobile navigation:

```text
Home
Network
Create
Company
COSA AI
```

### 21.4 Investor navigation

```text
Feed
Discover
Watchlist
Knowledge
Profile
```

### 21.5 Company/project page

Tabs can include:

```text
Overview
Projects
Updates
Evidence / Traction
Capital
Team
```

Only tabs allowed by audience policy are rendered.

---

## 22. Notifications

Central owns network notifications.

Initial notification types:

```text
NEW_FOLLOWER
CONTENT_COMMENT
COMMENT_REPLY
CONTENT_SAVE_MILESTONE
COMPANY_UPDATE
PROJECT_UPDATE
INVESTOR_INTEREST
INTRO_REQUEST
DATA_ROOM_REQUEST
MODERATION_NOTICE
ENTITLEMENT_CHANGE
```

Avoid notifying founders for every low-value reaction. Aggregate where possible.

---

## 23. Moderation, Trust and Safety

Professional network trust is a product capability, not only an abuse queue.

### 23.1 P0 risks

```text
fake investor
fake founder
impersonation
fundraising fraud
spam
harassment
defamation
fake operating claims
undisclosed sponsorship
portfolio conflict of interest
content theft
payment fraud later
```

### 23.2 Required trust primitives

```text
identity verification state
company-role verification
investor-role verification
report content/user
block user
content status / takedown
moderation reason codes
appeal state later
immutable/auditable moderation action record
relationship disclosures
sponsored content labels
```

### 23.3 Conflict disclosure

Examples:

```text
AUTHOR_IS_INVESTOR
PORTFOLIO_COMPANY
PAID_SPONSORSHIP
ADVISORY_RELATIONSHIP
EMPLOYEE_RELATIONSHIP
AFFILIATE_RELATIONSHIP
```

Investor analysis of a portfolio company should display that relationship.

### 23.4 Financial claims and investment content

COSA should provide clear product disclaimers and avoid language that turns AI matching into regulated investment advice. “Thesis fit” and evidence summaries are safer concepts than an opaque “investment score” or “buy recommendation”.

---

## 24. Monetization Architecture

### 24.1 Phase 1 — Platform membership

Reuse entitlement patterns first.

Potential features to add to entitlement schema after backward-compatibility review:

```text
network_pro
investor_pro
premium_knowledge
creator_tools
advanced_search
advanced_company_intelligence
```

Plan names remain commercial configuration and should not be hardcoded into domain behavior.

### 24.2 Phase 2 — Premium knowledge bundle

COSA can sell a membership that unlocks a premium content pool without immediately calculating per-author payouts.

This validates:

```text
Will users pay for startup/investor knowledge?
Which content creates retention?
Who are the high-value creators?
```

before payment-marketplace complexity.

### 24.3 Phase 3 — Paid content / creator subscription

Logical models:

```text
Offer
Order
PaymentAttempt
AccessGrant
CreatorSubscription
Refund
```

### 24.4 Phase 4 — Creator earnings and payout

Only after product/legal validation:

```text
LedgerAccount
LedgerEntry
CreatorEarning
PlatformFee
PayoutAccount
Payout
RefundAllocation
Chargeback
Tax/KYC status
ReconciliationRun
```

### 24.5 Money movement boundary

```text
COSA
  ├ order state
  ├ access entitlement
  ├ ledger/business records
  └ payout instructions
        ↓
Payment Service Provider
        ↓
authorization / settlement / payout rail
```

Do not store raw card/bank credentials in COSA.

---

## 25. Reputation Model

Do not launch a universal “COSA Score”.

Expose interpretable dimensions instead:

```text
Verified identity
Verified professional role
Company/project outcome history
Expertise topics
Published content history
Saved/cited content
Subscriber retention later
Founder endorsements later
Investor relationship disclosures
Moderation standing
```

A single score creates gaming, explainability and liability problems before the network has enough trustworthy data.

---

## 26. Search and Discovery

Search should operate across:

```text
people
companies
projects
content
topics
investor theses
```

Initial filters:

```text
role
industry
location
startup stage
project stage
project type
topic
fundraising state
investor thesis attributes
```

Search ranking should use explicit fields first. Semantic search can be layered after high-quality structured data and Central indexing are in place.

---

## 27. COSA Methodology Integration

COSA Network itself is a startup hypothesis and should follow COSA’s evidence-first methodology.

Do not move directly from architecture document to a large build.

### 27.1 Core hypotheses

```text
H1
Founders want a professional profile tied to actual company/project progress,
not another profile they must maintain manually.

H2
Investors value structured, evidence-provenance company/project updates more
than self-reported pitch-style feeds.

H3
Investors and experts are willing to publish knowledge where their professional
reputation and investment/company graph are visible.

H4
Founder-approved operating-event drafts reduce the effort needed to keep a
company profile active.

H5
A meaningful subset of users will pay for advanced network intelligence or
premium knowledge before creator payouts exist.

H6
High-quality network feedback can generate useful new validation/strategy
experiments for the AI Co-founder without treating engagement as evidence.
```

### 27.2 Recommended validation experiments before full build

```text
10–15 founder interviews
10–15 investor interviews
5–10 expert/creator interviews
clickable professional/company/project feed prototype
manual concierge feed using 10–20 curated startups
manual investor knowledge newsletter / premium research test
measure save, follow, return, intro-request and willingness-to-pay behavior
```

Interview counts are planning guidelines, not universal deterministic stage gates.

### 27.3 Strong early validation signal

The most useful early signal is not signup volume. It is repeated professional intent:

```text
Founder publishes more than once
Investor follows/saves companies and returns for updates
Investor requests qualified intro
Expert publishes again
Users pay or strongly commit to premium intelligence
```

---

## 28. North Star and Product Metrics

### 28.1 Recommended North Star

**Qualified professional relationships that reach a substantive action per month.**

Examples of substantive action:

```text
qualified investor follows + later requests intro
a founder and expert enter a meaningful discussion
a network signal produces a founder experiment
a premium article produces repeat subscriber/read behavior
```

### 28.2 Supporting metrics

```text
published active company profiles
published project profiles
weekly active founders
weekly active investors
high-intent saves
qualified follow rate
company/project update open rate
return rate after followed company update
intro request rate
founder acceptance rate
content completion rate
save-to-read ratio
repeat creator publication rate
moderation incident rate
stale company profile rate
paid conversion later
premium retention later
```

Avoid optimizing primarily for total posts, likes or time spent.

---

## 29. Cold-Start Strategy

A generic network dies if it starts with an empty feed. COSA can reduce this risk by turning operating progress into founder-approved content.

### 29.1 Initial content supply

```text
Company/project milestones
Founder learnings
COSA-generated update drafts
Curated investor theses
Expert playbooks
Case studies
Structured questions from founders
```

### 29.2 Initial community boundary

Recommended first community:

```text
Founders using COSA
Verified investors
Verified domain experts
Selected accelerator/ecosystem partners
```

Do not optimize V1 for broad job-seeker or generic creator acquisition.

### 29.3 Vertical beachhead

ClimateTech / Energy Efficiency in Vietnam/SEA remains a strong candidate because COSA already has methodology/evidence work suitable for standardized pilot, savings, impact, payback and technical-commercial proof. This should remain a go-to-market choice, not a hard-coded architecture constraint.

---

## 30. Existing / Gap / Proposal / No-Change Matrix

| Capability | Status | Integration decision |
|---|---|---|
| Workspace as Company | EXISTS | Reuse; do not create parallel Company aggregate |
| Project strategy record | EXISTS | Reuse; expose only through network projection |
| S0–S6 project stage | EXISTS | Canonical lifecycle vocabulary |
| Validation evidence chain | EXISTS | Reuse for safe provenance summaries |
| PlatformOutbox/Inbox | EXISTS | Reuse for Local ↔ Central events |
| Data classification | EXISTS | Reuse; do not overload as audience policy |
| Platform user/company/project IDs | EXISTS/PARTIAL | Reuse after identity ownership audit |
| Entitlement snapshot/guard | EXISTS | Extend for paid network features |
| AuditLog pattern | EXISTS | Reuse pattern; verify Central ID compatibility |
| Flutter mobile scaffolding | EXISTS | Reuse technology; mobile UX still needs implementation |
| Person professional profile | GAP | Add Central PersonProfile |
| Multiple professional roles | GAP | Add ProfessionalRole projection |
| Company network profile | GAP | Add versioned Central projection |
| Project network profile | GAP | Add versioned Central projection |
| Social graph | GAP | Add Central follow/save/block relationships |
| Content/article domain | GAP | Add Central ContentItem model |
| Feed | GAP | Add deterministic Central read model/ranking |
| Moderation | GAP | Add platform network moderation domain |
| Claim provenance UI | GAP | Add projection + display semantics |
| Investor profile/thesis | GAP/PROPOSAL | Implement through shared Capital domain |
| Fundraising pipeline | GAP/PROPOSAL | Implement through Capital domain, not generic Finance-only model |
| Payment checkout | GAP | External PSP integration later |
| Creator revenue share | GAP | Defer until premium knowledge validated |
| Creator payout | GAP | Defer; requires compliance/ledger/KYC/reconciliation |
| Business Core LLM independence | NO CHANGE | Preserve |
| WorkforceMember identity for company workforce | NO CHANGE | Preserve; do not replace with social role tables |
| Canonical task/workflow architecture | NO CHANGE | Network workflows must integrate, not duplicate |

---

## 31. Implementation Phases

### Phase 0 — Validation and ADRs

Before schema work:

```text
validate founder/investor/expert demand
confirm Central PostgreSQL identity ownership
confirm platform user/company/project UUID authority
write publication-boundary ADR
write network-domain ownership ADR
write PersonProfile/ProfessionalRole ADR
write moderation/trust ADR
```

Exit criteria:

```text
product hypotheses have qualitative evidence
core authority decisions are explicit
no duplicate Company/Project/User architecture
```

### Phase 1 — Network Identity + Public Projection

Build:

```text
PersonProfile
ProfessionalRole
CompanyNetworkProfile
ProjectNetworkProfile
PublicationSnapshot
PublicationPolicy
basic public/network profile APIs
founder-controlled publish/unpublish
```

Exit criteria:

```text
one founder can publish a safe company/project profile
private source data cannot leak through API tests
unpublish is deterministic
snapshot is versioned/auditable
```

### Phase 2 — Social Core

Build:

```text
ContentItem
follow
save
reaction
comment
notifications
basic feed
report/block
```

Exit criteria:

```text
role-aware feed works
spam/rate controls exist
moderation action is auditable
```

### Phase 3 — Operating Update Intelligence

Build:

```text
operating event → publication candidate
AI draft generation
claim provenance
founder review
publish event
network-signal summary back to Local
```

Exit criteria:

```text
AI cannot publish without deterministic policy/approval
private fields fail closed
social engagement is stored separately from validation evidence
```

### Phase 4 — Knowledge Network

Build:

```text
long-form article
Topic
ContentAssociation
expertise views
semantic tagging
knowledge feed/search
```

Exit criteria:

```text
investor/expert can build visible expertise history
content is searchable by structured topic/company/project associations
```

### Phase 5 — Capital Integration

Implement the detailed Capital Network spec using shared identities and graph:

```text
InvestorProfile
InvestmentThesis
Opportunity
Watchlist
Interest
IntroRequest
DataRoomAccess
Founder capital pipeline
```

Exit criteria:

```text
no second person/company/project identity system
investor activity uses shared network profile/content primitives
```

### Phase 6 — Paid Membership

Extend entitlement schema and Central billing integration for:

```text
Investor Pro
Founder Network Pro
Premium Knowledge access
advanced discovery/intelligence
```

Exit criteria:

```text
entitlements are deterministic
local offline behavior remains correct where required
plan access does not depend on LLM decisions
```

### Phase 7 — Creator Commerce

Only after evidence of paid knowledge demand:

```text
paid article
creator subscription
order/payment/access models
refund handling
```

### Phase 8 — Creator Payout

Only after legal/compliance/provider review:

```text
creator KYC
ledger
creator earnings
platform fees
payout
reconciliation
chargeback allocation
tax/reporting support
```

---

## 32. Security and Privacy Acceptance Criteria

No phase is complete unless all relevant criteria pass.

```text
[ ] Company operational data is private by default.
[ ] Publication uses explicit safe snapshots, not direct ORM serialization.
[ ] SECRET data can never be emitted as a network publication event.
[ ] SENSITIVE data requires explicit policy and must fail closed.
[ ] Founder can preview exactly what investor/public users will see.
[ ] Publish/unpublish is deterministic and auditable.
[ ] AudienceScope is enforced in code, not by model prompt.
[ ] Entitlement access is enforced through verified identity/workspace context.
[ ] Network API never trusts a raw company ID header as authorization.
[ ] Moderation admin actions are audited.
[ ] AI draft generation cannot call a publish side effect directly.
[ ] Raw evidence attachments are never automatically public.
[ ] Investor-only/data-room fields require explicit authorization.
[ ] External payment provider tokens/secrets are never exposed to content/AI layers.
```

---

## 33. Product Acceptance Criteria

### Professional Network V1

```text
[ ] User has one professional identity with multiple roles.
[ ] Founder can link verified company/project relationships.
[ ] Company/project profile can be published from safe COSA projections.
[ ] Founder can generate a draft update from a real operating milestone.
[ ] User can follow a person/company/project.
[ ] User can publish post/article and attach structured entity/topic associations.
[ ] User can comment, save and react.
[ ] Feed ranking is deterministic enough to explain/debug.
[ ] Investor can discover relevant company/project content.
[ ] Founder can receive summarized high-value network signals in COSA.
[ ] Social engagement never silently mutates validation state.
[ ] Report/block/moderation workflow exists.
```

### Paid Network V1

```text
[ ] Premium access is an entitlement, not a hardcoded UI condition.
[ ] Paywall behavior is enforced server-side.
[ ] Subscription expiry/grace behavior is tested.
[ ] Free users retain enough network functionality for network effects.
```

---

## 34. Architecture Decisions That Must Be Explicitly Avoided

Do not:

```text
create SocialCompany beside Workspace/Company
create SocialProject beside Project
use FounderProfile as public PersonProfile
store raw local Project JSON in public profile
sync the entire social feed into each company database
put network graph under Marketing domain
put investor social data under Finance simply because money is involved
create a second event bus for Network
create a new Agent just to run social posting
allow LLM to decide authorization or publish permissions
interpret likes as validation evidence
launch a universal opaque investment/reputation score
add Invest Now / securities transaction to social MVP
start creator payouts before paid-content demand is validated
hardcode a specific payment provider into Business Core
```

---

## 35. Required ADRs Before Production Coding

Recommended ADR set:

```text
ADR-NET-001 — Central Network Aggregate Ownership
ADR-NET-002 — PersonProfile and Multi-role Identity
ADR-NET-003 — Publication Snapshot and Audience Policy
ADR-NET-004 — Content / Social Graph Model
ADR-NET-005 — Network Event Boundary Local ↔ Central
ADR-NET-006 — Trust, Moderation and Disclosure
ADR-NET-007 — Feed Ranking v1
ADR-NET-008 — Capital Domain Relationship to COSA Network
ADR-NET-009 — Entitlement and Premium Knowledge Model
ADR-NET-010 — Payment / Creator Commerce Boundary (later phase)
```

Each ADR should include:

```text
current owner
new owner
source of truth
data lifecycle
privacy classification
authorization
events
failure mode
migration impact
rollback strategy
```

---

## 36. Recommended Repository Changes — Planning Only

No code should be added solely from this document without completing Phase 0 audit/ADRs.

Likely new documentation:

```text
docs/architecture/COSA_NETWORK_SOCIAL_KNOWLEDGE_CAPITAL_INTEGRATION.md

docs/architecture/adr/
  ADR-NET-001-...
  ...
```

Likely new Central capability after ADR approval:

```text
backend/app/platform/network/
```

Likely Flutter owner:

```text
frontend/lib/modules/network/
```

Existing modules to extend/reuse:

```text
backend/app/platform/sync
backend/app/platform/core
backend/core/strategy
backend/core/validation
backend/app/workforce/agents/governance
frontend/lib/modules/strategy
```

Do not modify canonical/frozen runtime owners merely to host network code.

---

## 37. Recommended First Implementation Slice

The best first vertical slice is intentionally small:

```text
Founder operates Project
      ↓
Project reaches a milestone
      ↓
COSA creates a safe update candidate
      ↓
Founder previews the exact public/network data
      ↓
Founder publishes
      ↓
Company/Project Network page updates
      ↓
Verified investor follows/saves/comments
      ↓
COSA sends a summarized material signal back to Local
      ↓
AI Co-founder explains whether this creates a useful next experiment
```

This slice validates the unique COSA thesis. It is more important than implementing generic social features such as reposts, stories, trending hashtags or complex recommendation algorithms.

---

## 38. Strategic Positioning

Avoid positioning:

> “LinkedIn for startup founders.”

Prefer a positioning direction such as:

> **COSA Network — the professional network where companies are alive.**

The meaning of “alive” is concrete:

```text
Company
has Projects
has progress
has evidence provenance
has founders
has knowledge
has capital relationships
has outcome history
```

COSA’s long-term defensibility comes from the integration of:

```text
Professional identity
+
Real company operations
+
Project portfolio
+
Evidence
+
Knowledge history
+
Capital interactions
+
Outcome history
```

—not from the number of posts or social reactions.

---

## 39. Final Architecture Principle

COSA Network should extend the Company Operating System rather than turn COSA into a conventional social-media product.

The invariant is:

```text
PRIVATE OPERATING TRUTH
        ↓ controlled projection
PUBLIC / NETWORK PROFESSIONAL TRUTH
        ↓ social + capital interaction
NETWORK SIGNALS
        ↓ controlled ingestion
AI CO-FOUNDER REASONING
        ↓
FOUNDER DECISION / EXPERIMENT / ACTION
```

If this boundary remains intact, Social, Knowledge and Capital can reinforce the core COSA product and produce a compounding data/network advantage.

If this boundary is broken, COSA risks becoming a generic feed product with privacy, moderation and regulatory liabilities while weakening the operating-system architecture.

The recommended implementation strategy is therefore:

```text
Validate → ADR → Identity/Projection → Social Core → Operating Update Intelligence
→ Knowledge → Capital → Paid Membership → Creator Commerce → Payout
```

This order maximizes strategic learning while minimizing architecture, trust and financial-compliance risk.
