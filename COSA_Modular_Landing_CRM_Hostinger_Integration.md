# COSA Modular Landing, CRM & Hostinger VPS Integration

**Status:** Proposed integration architecture  
**Target:** COSA local-first / self-hosted deployment model  
**Audience:** Claude Code / Antigravity CLI / Codex implementation agents  
**Date:** 2026-08-15

---

## 1. Executive Summary

COSA should **not** implement a drag-and-drop landing-page builder similar to LadiPage, Webflow, or a hosted website builder.

Instead, COSA should treat every landing page as a **generated software artifact**:

1. User asks COSA to analyze a project, feature, offer, campaign, or validation hypothesis.
2. COSA converts the request into an experiment and landing specification.
3. COSA delegates coding to an interchangeable local coding executor:
   - Claude Code CLI
   - Antigravity CLI
   - Codex
4. The coding executor generates a **modular Next.js application locally**.
5. The application connects to the central COSA API/CRM rather than owning a separate business database.
6. Email delivery is handled by a user-provided provider such as Resend through an adapter.
7. The founder previews and approves the result.
8. COSA packages and deploys the application to a Hostinger VPS.
9. Hostinger API MCP Server is used as programmable infrastructure for:
   - VPS operations
   - Docker Compose deployment/update
   - domain/DNS management
   - firewall
   - logs
   - snapshot/recovery
10. Leads, form submissions, events, campaign attribution, and customer feedback flow back into COSA CRM.
11. COSA analyzes the real market data and proposes the next experiment.

The key architectural rule is:

> **Landing pages must always be generated as reusable modules, never as a monolithic one-off page.**

A generated landing page can therefore evolve into a small product site, campaign site, feature microsite, documentation surface, demo site, or a navigation hub that links multiple COSA-managed subdomains.

---

# 2. Architecture Principles

## 2.1 COSA owns business logic

COSA remains the source of truth for:

- Projects
- Experiments
- Contacts
- Companies
- Leads
- CRM pipeline
- Form definitions
- Form submissions
- Consent
- Events
- Campaign attribution
- Email activities
- Notes
- Follow-ups
- AI insights
- Conversion metrics

Hostinger must **not** become COSA's backend.

Resend must **not** become COSA's CRM.

Claude Code, Antigravity, and Codex must **not** own COSA business logic.

They are replaceable executors/providers.

---

## 2.2 Hostinger is programmable infrastructure

Hostinger VPS is recommended as the primary deployment target because COSA may need to run:

- Next.js
- FastAPI
- PostgreSQL
- Redis
- background workers
- n8n
- MCP services
- monitoring
- reverse proxy
- multiple generated landing applications

The Hostinger API MCP Server currently exposes VPS Docker Compose operations including creating a project from Compose content/URL, updating projects by pulling new images and recreating containers, reading logs, restarting/stopping/starting projects, firewall operations, DNS record management, and VPS snapshots.

Therefore the correct abstraction is:

```text
COSA
  ↓
DeploymentProvider
  ↓
HostingerDeploymentProvider
  ↓
Hostinger API MCP Server
  ↓
Hostinger VPS / DNS / Firewall / Snapshot
```

Future providers can be added without changing COSA Growth or CRM logic:

```text
DeploymentProvider
├── Hostinger
├── Generic SSH VPS
├── Hetzner
├── AWS
├── Viettel Cloud
└── other providers
```

---

# 3. End-to-End User Experience

A founder should be able to say:

> "Phân tích chức năng COSA Finance và tạo landing page để kiểm chứng nhu cầu của doanh nghiệp siêu nhỏ."

COSA should perform:

```text
User request
    ↓
Project/Feature Analysis
    ↓
Customer / Offer / Hypothesis
    ↓
Experiment Specification
    ↓
Landing Specification
    ↓
Coding Agent
    ↓
Local Next.js Project
    ↓
Build + Tests
    ↓
Local Preview
    ↓
Founder Approval
    ↓
Docker Image
    ↓
Deployment Agent
    ↓
Hostinger VPS
    ↓
Domain/Subdomain + TLS
    ↓
Traffic
    ↓
Forms / Events
    ↓
COSA API
    ↓
PostgreSQL / CRM
    ↓
AI Analysis
    ↓
Next Experiment
```

The user should not need to understand:

- Next.js
- Docker
- DNS records
- reverse proxy
- PostgreSQL schemas
- webhooks

COSA owns this complexity.

---

# 4. Mandatory Modular Landing Architecture

## 4.1 Hard rule

Every generated landing project MUST satisfy:

```text
Page = Navigation
     + Reusable Sections
     + Reusable Forms
     + Shared Theme
     + Content Configuration
     + Tracking
     + Integration Adapters
```

Forbidden implementation:

```tsx
export default function Page() {
  return (
    <main>
      {/* 800–2000 lines containing the whole website */}
    </main>
  );
}
```

Required implementation:

```tsx
export default function Page() {
  return (
    <PageRenderer manifest={pageManifest} />
  );
}
```

or an equivalent modular composition.

---

## 4.2 Module categories

COSA should define a reusable module catalog.

### Navigation modules

```text
TopNav
TransparentTopNav
StickyNav
ProductNav
SubdomainNav
MobileNav
FooterNav
```

### Hero modules

```text
HeroCentered
HeroSplit
HeroWithDemo
HeroWithVideo
HeroWithForm
HeroWithSocialProof
```

### Problem / value modules

```text
ProblemGrid
PainPoints
BeforeAfter
ValueProposition
UseCases
FeatureGrid
FeatureComparison
```

### Proof modules

```text
LogoCloud
MetricProof
Testimonials
CaseStudies
CustomerQuotes
TrustBadges
```

### Conversion modules

```text
CTA
WaitlistCTA
DemoCTA
PricingCTA
LeadForm
SurveyForm
NewsletterForm
BookingCTA
```

### Product modules

```text
ProductDemo
Screenshots
FeatureTabs
Workflow
Architecture
IntegrationGrid
FAQ
Pricing
```

### Legal / trust modules

```text
PrivacyNotice
Consent
TermsLinks
CompanyIdentity
SecuritySummary
```

---

# 5. Module Contract

Each reusable module should have a predictable contract.

Example:

```ts
export interface LandingModule<TProps = unknown> {
  id: string;
  type: string;
  version: string;
  props: TProps;
  analytics?: {
    impressionEvent?: string;
    clickEvent?: string;
  };
}
```

Example Hero props:

```ts
export interface HeroSplitProps {
  eyebrow?: string;
  title: string;
  description: string;
  primaryCta: CTA;
  secondaryCta?: CTA;
  media?: MediaAsset;
}
```

The purpose is to let AI modify **content/configuration** before it modifies implementation code.

---

# 6. Module Registry

COSA landing projects should contain a registry.

```ts
export const moduleRegistry = {
  hero_centered: HeroCentered,
  hero_split: HeroSplit,
  problem_grid: ProblemGrid,
  feature_grid: FeatureGrid,
  testimonials: Testimonials,
  pricing: Pricing,
  lead_form: LeadForm,
  faq: FAQ,
  cta: CTA,
};
```

The page manifest can then be:

```ts
export const pageManifest = {
  id: "cosa-finance-validation",
  theme: "cosa-default",
  modules: [
    {
      id: "hero",
      type: "hero_split",
      props: {}
    },
    {
      id: "problem",
      type: "problem_grid",
      props: {}
    },
    {
      id: "features",
      type: "feature_grid",
      props: {}
    },
    {
      id: "validation-form",
      type: "lead_form",
      props: {}
    },
    {
      id: "faq",
      type: "faq",
      props: {}
    }
  ]
};
```

This architecture allows COSA to say:

> "Đổi hero sang dạng có demo nhưng giữ nguyên phần còn lại."

The coding agent only needs to modify:

```text
pageManifest
```

instead of rewriting an entire page.

---

# 7. Shared Module Library

For maximum reuse, generated projects should not duplicate all UI code indefinitely.

Recommended evolution:

## Phase A — local project modules

```text
landing-project/
└── src/
    ├── modules/
    ├── components/
    └── config/
```

Best for initial implementation.

## Phase B — COSA shared packages

```text
cosa-web-kit/
├── packages/
│   ├── landing-core/
│   ├── landing-modules/
│   ├── forms/
│   ├── analytics/
│   ├── crm-client/
│   ├── email-client/
│   ├── theme/
│   └── navigation/
```

A generated application depends on these packages.

Example:

```json
{
  "dependencies": {
    "@cosa/landing-core": "...",
    "@cosa/landing-modules": "...",
    "@cosa/forms": "...",
    "@cosa/crm-client": "...",
    "@cosa/navigation": "..."
  }
}
```

Do not start by over-engineering a large public package ecosystem. Build reusable local packages first and extract only modules that have proven reuse across several experiments.

---

# 8. Content Must Be Separated From Layout

Coding agents MUST separate:

```text
content
layout
design tokens
integration configuration
```

Recommended:

```text
src/
├── app/
├── modules/
├── components/
├── content/
│   ├── vi.ts
│   └── en.ts
├── config/
│   ├── site.ts
│   ├── navigation.ts
│   ├── experiment.ts
│   └── integrations.ts
└── styles/
```

Example:

```ts
export const content = {
  hero: {
    title: "Kế toán cho doanh nghiệp siêu nhỏ",
    description: "...",
    cta: "Đăng ký trải nghiệm"
  }
};
```

This lets COSA modify copy through an AI task without touching component implementation.

---

# 9. Navigation & Subdomain Architecture

This is a core requirement.

Landing pages must be capable of becoming part of a broader COSA-managed web surface.

Example deployment:

```text
www.company.vn
finance.company.vn
crm.company.vn
demo.company.vn
learn.company.vn
survey.company.vn
```

A landing app can expose a menu that navigates between these subdomains.

---

## 9.1 Navigation Manifest

Navigation MUST NOT be hard-coded directly into JSX.

Use a manifest:

```ts
export interface NavItem {
  id: string;
  label: string;
  type: "route" | "anchor" | "subdomain" | "external";
  href?: string;
  subdomain?: string;
  anchor?: string;
  target?: "_self" | "_blank";
  visible?: boolean;
}
```

Example:

```ts
export const navigation = [
  {
    id: "home",
    label: "Trang chủ",
    type: "route",
    href: "/"
  },
  {
    id: "features",
    label: "Tính năng",
    type: "anchor",
    anchor: "features"
  },
  {
    id: "finance",
    label: "Finance",
    type: "subdomain",
    subdomain: "finance"
  },
  {
    id: "crm",
    label: "CRM",
    type: "subdomain",
    subdomain: "crm"
  },
  {
    id: "demo",
    label: "Demo",
    type: "subdomain",
    subdomain: "demo"
  }
];
```

---

## 9.2 Domain Resolver

Do not hard-code production domains.

```ts
resolveSubdomain("finance")
```

should use environment/config:

```env
NEXT_PUBLIC_ROOT_DOMAIN=company.vn
```

Result:

```text
finance.company.vn
```

Development:

```env
NEXT_PUBLIC_ROOT_DOMAIN=localhost
```

can resolve to development URLs or configured preview ports.

---

## 9.3 Site Registry

COSA should maintain a server-side registry:

```text
sites
- id
- workspace_id
- project_id
- name
- slug
- site_type
- domain
- subdomain
- environment
- deployment_id
- status
- navigation_group_id
```

A shared navigation group:

```text
navigation_groups
navigation_items
```

allows several generated applications to render a consistent menu.

Example:

```text
Miva Corp Web Group

├── Home       → www.mivacorp.vn
├── COSA       → cosa.mivacorp.vn
├── Finance    → finance.mivacorp.vn
├── CRM        → crm.mivacorp.vn
└── Demo       → demo.mivacorp.vn
```

---

# 10. Two Navigation Modes

COSA should support both.

## Static navigation

Navigation is generated at build time.

Advantages:

- simple
- fast
- resilient

Use for stable production sites.

## Dynamic navigation

Application retrieves its navigation manifest from COSA API.

```text
GET /public/sites/{site_key}/navigation
```

Advantages:

- founder changes menu once
- multiple subdomains update consistently
- no need to rebuild every site for every navigation change

Recommended hybrid:

1. cache navigation locally
2. retrieve dynamic config
3. fall back to bundled navigation if COSA API is temporarily unavailable

---

# 11. Recommended Next.js Standard

As of 2026-08-15, Next.js 16.3 is the current major release published by the official Next.js project.

However, COSA prompts SHOULD NOT permanently hard-code a fixed version such as `16.3`.

Required behavior:

```text
At project-generation time:
1. Resolve the latest approved stable Next.js version.
2. Prefer the latest stable/security-patched release permitted by COSA policy.
3. Generate the project.
4. Lock the exact version in package-lock/pnpm-lock.
5. Record it in experiment/deployment metadata.
```

COSA should maintain a platform policy:

```yaml
web_runtime:
  framework: nextjs
  version_policy: latest-approved-stable
  package_manager: pnpm
  typescript: required
  app_router: required
```

This avoids an old prompt silently generating obsolete projects months later.

---

# 12. Generated Project Template

Recommended initial structure:

```text
project/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── privacy/
│   │   └── api/
│   ├── modules/
│   │   ├── navigation/
│   │   ├── hero/
│   │   ├── problem/
│   │   ├── proof/
│   │   ├── features/
│   │   ├── pricing/
│   │   ├── forms/
│   │   ├── faq/
│   │   └── footer/
│   ├── components/
│   ├── config/
│   │   ├── site.ts
│   │   ├── navigation.ts
│   │   ├── experiment.ts
│   │   └── integrations.ts
│   ├── content/
│   ├── lib/
│   │   ├── cosa/
│   │   ├── analytics/
│   │   └── validation/
│   └── styles/
├── public/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── AGENTS.md
├── README.md
├── package.json
└── pnpm-lock.yaml
```

---

# 13. COSA Experiment Model

Landing page creation should be linked to an experiment instead of being an isolated utility.

```text
Project
  ↓
Experiment
  ├── hypothesis
  ├── target audience
  ├── offer
  ├── success metrics
  ├── landing
  ├── forms
  ├── traffic
  ├── events
  ├── leads
  ├── insights
  └── decision
```

Suggested fields:

```text
experiments
- id
- workspace_id
- project_id
- name
- hypothesis
- target_customer
- offer
- status
- start_at
- end_at
- success_definition
- created_by
```

```text
landing_pages
- id
- experiment_id
- site_id
- variant
- repository_path
- image_tag
- deployment_id
- published_url
- status
```

---

# 14. Central COSA CRM

Landing applications MUST NOT own a separate CRM.

Flow:

```text
Landing A ─┐
Landing B ─┼─→ COSA Public API → COSA CRM → PostgreSQL
Landing C ─┘
```

Core CRM objects:

```text
contacts
companies
leads
opportunities
pipelines
pipeline_stages
crm_activities
crm_notes
tags
contact_tags
sources
campaigns
experiments
forms
form_submissions
consents
events
email_messages
email_events
```

---

# 15. Public Form API

Generated websites should submit through COSA.

Example:

```text
POST /public/forms/{form_key}/submissions
```

Payload:

```json
{
  "experiment_id": "exp_001",
  "landing_id": "landing_a",
  "visitor_id": "...",
  "utm": {
    "source": "facebook",
    "medium": "paid",
    "campaign": "finance_validation"
  },
  "fields": {
    "name": "...",
    "email": "...",
    "company": "...",
    "pain_point": "..."
  },
  "consent": {
    "marketing": true,
    "privacy": true
  }
}
```

Server-side processing:

```text
Validate
  ↓
Anti-spam / rate limit
  ↓
Store submission
  ↓
Upsert contact
  ↓
Create/update lead
  ↓
Record attribution
  ↓
Record CRM activity
  ↓
Trigger allowed workflow
```

---

# 16. Forms Must Also Be Modular

Forms are reusable modules.

```text
LeadForm
WaitlistForm
SurveyForm
DemoRequestForm
NewsletterForm
ContactForm
QualificationForm
```

Form schema should preferably be configuration-driven:

```ts
const form = {
  key: "finance-validation",
  fields: [
    {
      name: "email",
      type: "email",
      required: true
    },
    {
      name: "pain_point",
      type: "textarea",
      required: true
    }
  ]
};
```

The coding agent should not create a new form handler for every landing page.

---

# 17. Email Provider Architecture

Email is provider-based.

```text
COSA Email Service
  ↓
EmailProvider interface
  ├── ResendProvider
  ├── SMTPProvider
  ├── SESProvider
  └── future providers
```

Recommended provider interface:

```ts
interface EmailProvider {
  send(input: SendEmailInput): Promise<SendResult>;
  sendTemplate(input: SendTemplateInput): Promise<SendResult>;
  verifyConfiguration(): Promise<ProviderHealth>;
}
```

---

# 18. Resend Integration

Resend is a practical default because it provides:

- API-based sending
- custom domain support
- webhooks
- delivery events
- open/click-related email events
- receiving capabilities if COSA needs them later

But the user owns the account/API key.

COSA stores provider credentials securely and only sends through the selected workspace provider.

Recommended event flow:

```text
COSA
 ↓
Resend API
 ↓
Email
 ↓
Resend webhook
 ↓
COSA webhook endpoint
 ↓
email_events
 ↓
CRM activity timeline
```

Example webhook endpoint:

```text
POST /webhooks/email/resend
```

Do not treat email-open data as a perfectly reliable indicator of human intent. Use it as a supporting signal only.

---

# 19. Tracking & Attribution

Every generated landing page should include a consistent COSA event client.

Minimum events:

```text
page_view
session_start
cta_clicked
form_started
form_submitted
form_failed
demo_requested
pricing_viewed
external_link_clicked
```

Recommended dimensions:

```text
workspace_id
project_id
experiment_id
landing_id
variant
visitor_id
session_id
utm_source
utm_medium
utm_campaign
utm_content
referrer
device
timestamp
```

Do not collect unnecessary personal data.

---

# 20. Reusable Analytics Module

Generated apps should use:

```text
@cosa/analytics
```

conceptually:

```ts
track("cta_clicked", {
  experimentId,
  variant,
  cta: "hero_primary"
});
```

The page module itself should not directly implement database writes.

---

# 21. Coding Agent Abstraction

COSA must not depend permanently on one coding CLI.

```text
CodingAgentProvider
├── ClaudeCodeProvider
├── AntigravityProvider
└── CodexProvider
```

Common operations:

```text
createProject(spec)
modifyProject(task)
runTests()
build()
fixBuild()
review()
```

The provider receives the same structured `LandingGenerationSpec`.

---

# 22. LandingGenerationSpec

Recommended structured contract:

```yaml
schema_version: 1

project:
  id: cosa-finance
  name: COSA Finance

experiment:
  id: exp-finance-001
  hypothesis: >
    Micro-enterprises are interested in a simplified finance workflow.
  audience: >
    Vietnamese founders and micro-enterprises.

site:
  type: landing
  locale: vi-VN
  root_domain: example.vn
  requested_subdomain: finance

navigation:
  mode: dynamic-with-fallback
  group: main-product-network
  items:
    - label: Trang chủ
      type: subdomain
      subdomain: www
    - label: COSA
      type: subdomain
      subdomain: cosa
    - label: CRM
      type: subdomain
      subdomain: crm

modules:
  - navigation
  - hero_split
  - pain_points
  - feature_grid
  - workflow
  - lead_form
  - faq
  - final_cta
  - footer

form:
  key: finance-validation
  destination: cosa-crm

email:
  provider: workspace-configured

deployment:
  provider: hostinger
  mode: docker

quality:
  modular_required: true
  typescript_required: true
  mobile_required: true
  accessibility_required: true
  tests_required: true
```

---

# 23. Mandatory Coding-Agent Prompt

The following rule should be automatically prepended by COSA whenever it asks a coding agent to generate or modify a landing site.

## SYSTEM / PROJECT INSTRUCTION

```text
You are implementing a COSA-managed landing application.

NON-NEGOTIABLE ARCHITECTURE RULES:

1. Build the application using the latest COSA-approved stable Next.js release at generation time.
2. Use TypeScript and the App Router.
3. DO NOT build the landing page as one monolithic page/component.
4. The UI MUST be designed as reusable modules.
5. Separate:
   - navigation
   - page modules/sections
   - forms
   - content
   - theme/design tokens
   - analytics
   - COSA API integration
   - deployment configuration
6. Every page section must be reusable and receive typed props/configuration.
7. Use a module registry and page manifest, or an equivalent composition mechanism.
8. Navigation MUST be configuration-driven.
9. Navigation MUST support:
   - internal routes
   - page anchors
   - external URLs
   - COSA-managed subdomains
10. Never hard-code the production root domain inside components.
11. Resolve subdomains from environment/site configuration.
12. Forms MUST use reusable schema-driven form components.
13. Forms MUST submit to the COSA Public API. Do not create a separate CRM/database for the landing application unless the specification explicitly requires isolation.
14. Do not expose database credentials to the browser.
15. Email MUST be handled through COSA's Email Provider interface; do not hard-code Resend credentials inside the generated site.
16. Analytics MUST use the COSA event adapter.
17. Keep content separate from reusable component implementation whenever practical.
18. Reuse existing COSA modules before creating new ones.
19. If a new reusable module is required:
    - define typed props
    - make it content-agnostic
    - document it
    - register it
20. Generate:
    - Dockerfile
    - docker-compose.yml or deployment fragment
    - .env.example
    - README.md
    - tests
21. Run lint/typecheck/tests/build before declaring completion.
22. Do not deploy production automatically.
23. Return:
    - architecture summary
    - modules created/reused
    - files changed
    - test/build status
    - local preview command
    - deployment readiness
```

This prompt should be treated as a platform invariant.

---

# 24. Agent Prompt for Modification

When the founder says:

> "Đổi headline, thêm bảng giá và đưa CRM vào menu."

COSA should NOT regenerate the site.

Use:

```text
Modify the existing COSA landing project.

Requirements:
- Preserve the existing modular architecture.
- Modify content/config before component implementation where possible.
- Reuse the Pricing module if available.
- Update the navigation manifest to add the CRM subdomain.
- Do not duplicate an existing module.
- Do not rewrite unrelated sections.
- Run tests and build after changes.
```

---

# 25. Module Reuse Decision Rule

Coding agent should follow:

```text
Need UI capability
    ↓
Does module already exist?
 ┌──Yes─────────────┐
 ↓                  │
Reuse + configure   │
                    │
No                  │
 ↓                  │
Can generic module  │
be extended safely? │
 ┌──Yes─────────────┘
 ↓
Extend module
 ↓
No
 ↓
Create reusable module
 ↓
Register
 ↓
Document
```

Never create:

```text
FinanceHero
CRMSpecialHero
MarketingHero2026
```

if all three are merely content variants of:

```text
HeroSplit
```

---

# 26. Design System

A reusable landing architecture also requires shared design tokens.

```text
theme
├── colors
├── typography
├── spacing
├── radius
├── shadows
├── containers
├── breakpoints
└── motion
```

Generated modules should consume theme variables rather than embed arbitrary style constants throughout the codebase.

This enables:

```text
same module
+
different theme
=
different brand/site
```

---

# 27. Deployment Architecture

Recommended production architecture:

```text
Internet
   ↓
DNS
   ↓
Hostinger VPS
   ↓
Reverse Proxy
   ├── www.example.vn      → web-main
   ├── finance.example.vn  → landing-finance
   ├── crm.example.vn      → landing-crm
   ├── demo.example.vn     → landing-demo
   └── api.example.vn      → cosa-api
                                  ↓
                            PostgreSQL
```

---

# 28. Reverse Proxy

Use one supported reverse proxy implementation such as:

- Caddy
- Traefik
- Nginx

Recommended initial preference:

```text
Caddy
```

because of relatively simple configuration and automatic TLS workflows.

However, keep the reverse proxy behind an infrastructure adapter/configuration rather than embedding assumptions into landing modules.

---

# 29. PostgreSQL Placement

Do not deploy one PostgreSQL instance per landing page.

Preferred:

```text
Landing containers
      ↓
COSA API
      ↓
PostgreSQL
```

Never:

```text
Browser
  ↓
PostgreSQL:5432
```

Production PostgreSQL should stay on a private Docker/network boundary or an equivalent protected network.

---

# 30. Docker Deployment Contract

Generated app:

```text
Source
  ↓
Build
  ↓
Docker Image
  ↓
Registry
  ↓
Hostinger VPS Docker Compose
```

Recommended:

```text
Git repository = source history
Container registry = deployable artifact
Hostinger VPS = runtime
```

The deployment agent can update the Docker Compose project by using a new image tag and invoking the Hostinger VPS project update flow.

---

# 31. Image Versioning

Never deploy only:

```text
:latest
```

Recommended:

```text
ghcr.io/org/cosa-finance:git-abc123
```

Deployment metadata should store:

```text
image
image_digest
git_commit
build_time
nextjs_version
deployment_time
deployment_status
```

This makes rollback and audit possible.

---

# 32. Hostinger MCP Integration

Create:

```text
HostingerInfrastructureAdapter
```

Capabilities:

```text
listVps()
deployComposeProject()
updateComposeProject()
restartProject()
stopProject()
getProjectLogs()

getDnsRecords()
validateDnsRecords()
updateDnsRecords()

createFirewall()
activateFirewall()

createSnapshot()
restoreSnapshot()
```

The exact Hostinger MCP tools may change over time, so the adapter should isolate COSA from the vendor-specific tool names.

---

# 33. Current Hostinger MCP Capabilities Relevant to COSA

As verified from the current `hostinger/api-mcp-server` repository on 2026-08-15:

### Docker Compose

`VPS_createNewProjectV1`

- deploys a project from `docker-compose.yaml` contents or a URL
- can resolve a GitHub repository URL to a Compose file
- replaces a project if the same project name already exists

`VPS_updateProjectV1`

- pulls the latest image versions
- recreates containers
- preserves data volumes

`VPS_getProjectLogsV1`

- provides recent aggregated project logs

Also available:

- start
- stop
- restart
- list projects

### DNS

Relevant tools include:

- get DNS records
- validate DNS records
- update DNS records
- DNS snapshots/restore

### Firewall

Relevant capabilities include:

- create firewall
- update rules
- activate/deactivate firewall

### VPS snapshots

Relevant capabilities include:

- create snapshot
- retrieve snapshot
- restore snapshot
- delete snapshot

These capabilities are sufficient for a first Hostinger deployment adapter.

---

# 34. Deployment Approval Policy

COSA must distinguish operations by risk.

## Safe / low-risk

Can be automated after user policy permits:

```text
build
lint
test
preview
read logs
read metrics
health check
```

## Production-changing

Require approval by default:

```text
publish
change DNS
replace compose project
update production image
restart production project
```

## Destructive

Require explicit confirmation every time:

```text
delete project
delete DNS records
restore snapshot
destroy volume
delete database
```

---

# 35. Deployment Workflow

```text
1. User approves publish
2. COSA verifies build status
3. COSA records current deployment
4. Optional: snapshot before high-risk update
5. Build Docker image
6. Push image to registry
7. Prepare/update Docker Compose
8. Update Hostinger project
9. Configure/validate DNS
10. Verify health endpoint
11. Verify public HTTPS URL
12. Record deployment
13. Surface logs if unhealthy
14. Roll back if policy allows and health check fails
```

---

# 36. Site Deployment Record

Suggested:

```text
deployments
- id
- workspace_id
- site_id
- environment
- provider
- provider_project_id
- image
- image_digest
- git_commit
- compose_hash
- domain
- deployed_at
- status
- health_status
- previous_deployment_id
```

---

# 37. Health Check Standard

Every generated landing app must expose:

```text
GET /api/health
```

Response:

```json
{
  "status": "ok",
  "service": "landing-finance",
  "version": "abc123"
}
```

Deployment agent should consider deployment incomplete until:

```text
container healthy
+
HTTPS reachable
+
health endpoint OK
```

---

# 38. Security Requirements

Minimum:

1. Never expose PostgreSQL port publicly.
2. Keep secrets out of Git.
3. Use `.env.example`, never commit `.env`.
4. Browser receives only public configuration.
5. Resend/API keys remain server-side/COSA-side.
6. Validate all public form input.
7. Rate-limit form endpoints.
8. Add anti-bot/anti-spam controls where necessary.
9. Store marketing consent with timestamp and source.
10. Validate DNS change before applying it.
11. Restrict destructive infrastructure operations.
12. Keep deployment/audit logs.
13. Use HTTPS.
14. Use secure webhook verification.
15. Use least-privilege credentials where supported.

---

# 39. CRM Workflow Example

```text
Visitor
  ↓
finance.example.vn
  ↓
LeadForm
  ↓
COSA Public API
  ↓
form_submission
  ↓
contact upsert
  ↓
lead create/update
  ↓
tags:
- finance
- founder
- experiment-001
  ↓
CRM activity
  ↓
Email workflow
  ↓
Sales follow-up
```

---

# 40. Email Workflow Example

```text
Form submitted
  ↓
COSA Workflow Engine
  ↓
Check consent / workflow rule
  ↓
EmailProvider
  ↓
Resend
  ↓
Delivery webhook
  ↓
COSA
  ↓
CRM timeline
```

COSA owns workflow state. Resend performs delivery.

---

# 41. Linking Landing Experiments to Execution

Landing creation should be usable as an execution tactic.

Example:

```text
Project
  ↓
Goal / execution target
  ↓
Cycle
  ↓
Weekly tactic:
"Validate COSA CRM demand"
  ↓
Experiment
  ↓
Landing
  ↓
CRM leads
  ↓
Measured result
  ↓
Review
```

The landing feature should therefore not live as an isolated "Website Builder" screen.

Recommended placement:

```text
Growth / Experiments
```

with links back to:

```text
Projects
CRM
Tasks
Reviews
```

---

# 42. COSA Growth Module

Recommended structure:

```text
Growth
├── Experiments
├── Sites
├── Forms
├── Traffic Sources
├── Analytics
└── Insights
```

---

# 43. COSA Sites Screen

Suggested list:

```text
COSA Sites

Name            Domain                  Type        Status
---------------------------------------------------------
Main            www.example.vn          website     live
Finance         finance.example.vn      landing     live
CRM             crm.example.vn          landing     draft
Demo            demo.example.vn         demo        live
Survey          survey.example.vn       survey      paused
```

Actions:

```text
Preview
Edit with AI
Navigation
Forms
Analytics
Deployments
Domain
Logs
Pause
Archive
```

---

# 44. COSA Site Detail

Tabs:

```text
Overview
Modules
Content
Navigation
Forms
Analytics
CRM
Deployments
Settings
```

This UI reinforces modularity for users without exposing code complexity.

---

# 45. Edit With AI

Example:

User:

> "Thêm menu Finance và CRM. Đưa form đăng ký lên ngay dưới hero."

COSA converts this to a structured task:

```yaml
changes:
  navigation:
    add:
      - type: subdomain
        label: Finance
        subdomain: finance
      - type: subdomain
        label: CRM
        subdomain: crm

  modules:
    move:
      module: lead_form
      after: hero
```

Coding agent receives only the required project context and modifies configuration/modules.

---

# 46. Future: Visual Module Editor

A visual editor can be added later without changing the underlying architecture.

Because pages already use:

```text
module registry
+
page manifest
+
content configuration
```

COSA can later provide:

```text
[Hero]
  ↓
[Problem]
  ↓
[Features]
  ↓
[Form]
```

with reorder controls.

The editor changes the manifest rather than rewriting HTML.

This gives COSA many benefits of a LadiPage-like UI later without making drag-and-drop the foundation today.

---

# 47. Future: Module Marketplace / Skill Library

Once modules become stable:

```text
COSA Module Library
├── SaaS Launch
├── Waitlist
├── Product Validation
├── Webinar
├── Service Lead Generation
├── Pricing Test
├── Survey
└── Event
```

Each template should be:

```text
template
=
module composition
+
content schema
+
experiment defaults
```

not duplicated code.

---

# 48. AI Learning From Module Performance

COSA can eventually analyze:

```text
HeroSplit
vs
HeroCentered

LeadForm 3 fields
vs
LeadForm 8 fields

CTA "Đăng ký"
vs
CTA "Dùng thử"
```

Because modules are standardized, COSA can compare experiment performance across sites.

This is another reason modularity is strategically important: it turns UI elements into measurable experiment units.

---

# 49. Module Performance Data

Possible model:

```text
module_impressions
module_interactions
module_conversions
```

Dimensions:

```text
module_type
module_version
experiment_id
variant
position
traffic_source
```

Then AI can answer:

> "Module nào đang chuyển đổi tốt hơn cho nhóm founder OPC?"

without scraping page structure after the fact.

---

# 50. Recommended MVP Scope

Implement first:

## COSA Core

- Experiment entity
- Site entity
- Form entity
- CRM contact/lead
- Public form API
- basic event ingestion

## Modular web kit

- Navigation
- Hero
- Problem
- Feature Grid
- Workflow
- Proof
- Lead Form
- FAQ
- CTA
- Footer

## Coding execution

- `CodingAgentProvider`
- Claude Code first
- adapters for Antigravity/Codex next

## Deployment

- `DeploymentProvider`
- Hostinger first
- Docker
- DNS/subdomain
- logs
- health checks

## Email

- `EmailProvider`
- Resend first
- webhooks to CRM timeline

---

# 51. Explicitly Defer

Do not build initially:

- full drag-and-drop editor
- complex website CMS
- independent PostgreSQL for every site
- custom email infrastructure
- Hostinger-specific business logic inside COSA domain models
- auto-deploy without approval
- complex multi-provider deployment orchestration
- premature module marketplace

---

# 52. Implementation Sequence

## Stage 1 — contracts

Create:

```text
LandingGenerationSpec
LandingModule
PageManifest
NavigationManifest
FormSchema
CodingAgentProvider
EmailProvider
DeploymentProvider
```

## Stage 2 — reusable kit

Implement initial module library and sample landing.

## Stage 3 — COSA API

Implement:

```text
sites
experiments
forms
submissions
events
contacts
leads
```

## Stage 4 — coding agent

Implement local workspace generation and edit loop.

## Stage 5 — preview

Local build + local preview + COSA UI approval.

## Stage 6 — container

Docker build + registry.

## Stage 7 — Hostinger adapter

Docker Compose + DNS + logs + health.

## Stage 8 — CRM/email

Resend adapter + webhooks + CRM timeline.

## Stage 9 — experiment insights

Conversion metrics + AI review + next-experiment suggestions.

---

# 53. Acceptance Criteria

The integration is complete when the following scenario works end-to-end:

1. User creates or selects a COSA project.
2. User asks:
   > "Phân tích chức năng này và tạo landing page."
3. COSA creates an experiment specification.
4. Coding agent generates a local Next.js project.
5. The generated site:
   - is modular
   - uses a page/module manifest
   - has config-driven navigation
   - supports subdomain menu links
   - uses reusable forms
   - connects to COSA CRM/API
6. Local lint/typecheck/tests/build pass.
7. User previews locally.
8. User modifies content with natural language without page regeneration.
9. User approves publish.
10. Deployment agent builds/pushes a versioned Docker image.
11. Hostinger VPS runs the Compose project.
12. Hostinger DNS exposes the requested subdomain.
13. HTTPS health check passes.
14. Visitor submits the form.
15. COSA CRM creates/updates the contact and lead.
16. Resend can send an approved email workflow.
17. Resend webhook updates CRM activity.
18. COSA shows experiment conversion data.
19. AI can propose a next variant.
20. Existing reusable modules are reused rather than duplicated.

---

# 54. Architecture Decision Record

## Decision 1

**Do not build a LadiPage clone.**

Use AI-generated modular Next.js applications.

## Decision 2

**Modularity is mandatory.**

Every landing is composed from reusable sections and configuration.

## Decision 3

**Navigation is a first-class module.**

It must support route, anchor, external URL, and subdomain navigation.

## Decision 4

**COSA owns CRM and experiment data.**

Landing apps send data to COSA API.

## Decision 5

**Email providers are adapters.**

Resend is the initial recommended provider, not a hard dependency.

## Decision 6

**Coding agents are interchangeable executors.**

Claude Code first; Antigravity/Codex use the same contract.

## Decision 7

**Hostinger is infrastructure.**

Use Hostinger VPS + Docker + DNS + firewall + logs + snapshots.

## Decision 8

**Deployment is artifact-based.**

Prefer versioned Docker images and Git source history.

## Decision 9

**Founder approval is required before production deployment by default.**

## Decision 10

**Do not create one database per landing page by default.**

Use the central COSA CRM/API/PostgreSQL architecture.

---

# 55. Final Reference Architecture

```text
                         USER
                          │
                    Chat / Voice
                          │
                          ▼
                         COSA
                          │
              ┌───────────┼────────────┐
              ▼           ▼            ▼
          Analysis      Growth        CRM
                          │            │
                          ▼            ▼
                      Experiment    Contact/Lead
                          │
                          ▼
                  LandingGenerationSpec
                          │
                          ▼
                 CodingAgentProvider
             ┌────────────┼────────────┐
             ▼            ▼            ▼
        Claude Code   Antigravity     Codex
             │
             ▼
       LOCAL NEXT.JS APP
             │
      ┌──────┼───────────────┐
      ▼      ▼               ▼
   Modules  Forms        Navigation
      │      │               │
      │      │           Subdomains
      │      │
      │      └─────────────→ COSA API
      │                         │
      │                    PostgreSQL
      │                         │
      │                        CRM
      │                         │
      │                  EmailProvider
      │                         │
      │                       Resend
      │
      ▼
 Test / Build / Preview
      │
 Founder Approval
      │
      ▼
 Versioned Docker Image
      │
      ▼
 DeploymentProvider
      │
      ▼
 Hostinger MCP Adapter
      │
 ┌────┼────────┬─────────┬──────────┐
 ▼    ▼        ▼         ▼          ▼
VPS  Docker    DNS    Firewall   Snapshot/Logs
 │
 ▼
Reverse Proxy
 ├── www.domain.vn
 ├── finance.domain.vn
 ├── crm.domain.vn
 └── demo.domain.vn
```

---

# 56. Key Implementation Rule for Claude Code

If only one instruction from this document is retained, it should be:

> **Never ask the coding agent to "make a landing page" without the COSA modular-generation contract. Every site must be generated as reusable modules + manifest + configurable navigation + reusable forms + COSA integration.**

This rule prevents COSA from accumulating hundreds of one-off AI-generated codebases and makes future reuse, A/B experiments, visual editing, cross-subdomain navigation, maintenance, and automated learning feasible.

---

# 57. Sources Verified for This Architecture

Verified on **2026-08-15**:

- Hostinger API MCP Server repository: `https://github.com/hostinger/api-mcp-server`
- Hostinger Agent Skills repository: `https://github.com/hostinger/hostinger-agent-skills`
- Next.js official release blog: `https://nextjs.org/blog`
- Next.js 16.3 release: `https://nextjs.org/blog/next-16-3`
- Resend webhook documentation: `https://resend.com/docs/webhooks/introduction`
- Resend API documentation: `https://resend.com/docs/api-reference/introduction`

When implementing, re-check provider APIs and latest stable/security-patched framework versions rather than assuming this document's observed versions remain current.

---

# 58. Implementation Priority

**P0**

- Modular landing contract
- Navigation/subdomain manifest
- Page manifest
- reusable form schema
- COSA public form API
- COSA CRM contact/lead integration
- local coding-agent workflow
- local preview/build

**P1**

- Docker image pipeline
- Hostinger VPS adapter
- DNS/subdomain management
- health checks/logs
- Resend provider + webhooks

**P2**

- dynamic navigation registry
- module performance tracking
- experiment variants
- AI-assisted experiment analysis

**P3**

- visual module editor
- module/template library
- cross-experiment module intelligence
- additional deployment providers

---

## Final Recommendation

Proceed with the integration.

The recommended product boundary is:

```text
COSA = intelligence + experiment + CRM + orchestration
Coding Agent = reusable Next.js implementation
COSA Web Kit = reusable landing modules
PostgreSQL = central business/CRM data
Resend = replaceable email delivery provider
Hostinger VPS = production runtime
Hostinger MCP = infrastructure control plane
```

This creates a practical startup workflow while preserving COSA's local-first, self-hostable, provider-independent architecture.
