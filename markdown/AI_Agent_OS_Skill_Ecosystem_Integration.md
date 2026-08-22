# AI Agent OS — Skill Ecosystem, Registry & Supply Chain Integration

**Document type:** Architecture Addendum / Integration Specification  
**Status:** Proposed  
**Date:** 2026-08-22  
**Applies to:** AI Agent OS Core, Business Layer, Multi-Agent Runtime, Memory, Tool/MCP Layer, Self-Improvement Loop  
**Primary reference:** `vutasoftvn/awesome-agent-skills` / upstream `VoltAgent/awesome-agent-skills`

---

## 1. Executive Summary

This document extends the current AI Agent OS architecture with a first-class **Skill Ecosystem Layer**.

The main architectural conclusion is:

> `awesome-agent-skills` should not be embedded into AI Agent OS as runtime code.  
> It should be treated as an **external discovery source** for a governed Skill Registry and Skill Supply Chain.

AI Agent OS should therefore add the following core capabilities:

1. **Canonical Skill Model**
2. **Skill Registry**
3. **Skill Discovery**
4. **Skill Router**
5. **Skill Loader**
6. **Skill Runtime**
7. **Skill Trust & Permission Model**
8. **Skill Supply Chain**
9. **Skill Evaluation**
10. **Skill Observability**
11. **Skill Lifecycle Management**
12. **Capability Gap Detection**
13. **Self-Improvement with Human Approval**

The resulting system allows agents to:

- discover relevant capabilities,
- select only the skills needed for a task,
- load skill instructions progressively,
- execute through restricted tools,
- collect effectiveness metrics,
- detect capability gaps,
- propose new skills,
- evaluate them in a sandbox,
- request human approval,
- and evolve safely without modifying the Agent Core directly.

This architecture is aligned with the AI Agent OS design principle:

> **Core remains small and stable; intelligence and domain capability evolve through composable skills, tools, memory, policies, and business modules.**

---

# 2. Context

The Agent Skills ecosystem is converging around portable directory-based capability packages, commonly centered on a `SKILL.md` file and supporting resources.

The `awesome-agent-skills` repository is valuable because it provides:

- a broad catalog of real-world Agent Skills,
- official skills from major engineering teams,
- community skills,
- cross-platform compatibility signals,
- naming conventions,
- quality guidelines,
- security warnings,
- and a practical taxonomy of capabilities.

However, it is fundamentally a **curated index**, not a runtime.

The repository itself mainly contains:

- `README.md`
- `CONTRIBUTING.md`
- `LICENSE`
- `.gitignore`

The referenced skills live in external repositories.

Therefore, its correct place in AI Agent OS is:

```text
External Skill Catalogs
        ↓
Skill Discovery
        ↓
Skill Registry
        ↓
Security / Eval / Approval
        ↓
AI Agent OS Runtime
```

Not:

```text
awesome-agent-skills
        ↓
copy all skills
        ↓
Agent context
```

---

# 3. Architectural Decision

## ADR-SKILL-001 — Introduce a governed Skill Ecosystem Layer

### Decision

AI Agent OS will introduce a dedicated Skill Layer between the Agent Layer and Tool Layer.

```text
┌───────────────────────────────────────────────────────────┐
│                     BUSINESS OS                           │
│ OKR │ 12 Week Year │ Tasks │ CRM │ Marketing │ Finance  │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│                      AGENT LAYER                          │
│ Planner │ Executor │ Reviewer │ Critic │ Specialist      │
│ Sequential Flow │ Parallel Flow │ Delegation             │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│                      SKILL LAYER                          │
│ Skill Registry │ Router │ Loader │ Runtime │ Evaluator    │
│ Trust │ Permissions │ Supply Chain │ Lifecycle            │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│                       TOOL LAYER                          │
│ MCP │ APIs │ Connectors │ Browser │ Shell │ Code Runner  │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│ MEMORY │ KNOWLEDGE │ EVENTS │ AUDIT │ OBSERVABILITY      │
└───────────────────────────────────────────────────────────┘
```

### Consequences

Positive:

- smaller Agent Core,
- reusable skills,
- portable domain capability,
- easier testing,
- safer self-improvement,
- easier governance,
- multi-model compatibility,
- better observability,
- lower context usage,
- independent lifecycle for capability packages.

Trade-offs:

- adds registry complexity,
- needs security scanning,
- needs version pinning,
- needs evaluation infrastructure,
- needs permission enforcement,
- requires canonical metadata normalization.

---

# 4. Core Definitions

AI Agent OS should define the following objects separately.

## 4.1 Tool

A **Tool** is an atomic callable capability.

Examples:

```text
github.create_pull_request()
crm.update_contact()
calendar.create_event()
browser.open()
sql.query()
send_email()
```

A tool should be:

- narrow,
- typed,
- permission-scoped,
- auditable,
- deterministic where possible.

---

## 4.2 Skill

A **Skill** is a reusable capability package containing knowledge and procedure that may orchestrate one or more tools.

Recommended definition:

```text
Skill
=
Instructions
+ Domain Knowledge
+ Procedure
+ Tool Requirements
+ Policies
+ Validation Rules
+ Optional Resources
```

Example:

```text
Skill: ship-feature
```

may perform:

```text
inspect changes
    ↓
run tests
    ↓
review code
    ↓
commit
    ↓
push
    ↓
create PR
    ↓
monitor CI
```

The skill itself is not the GitHub API.

The GitHub API is a tool dependency.

---

## 4.3 Workflow

A **Workflow** coordinates multiple steps, skills, agents, or approvals.

```text
Workflow
=
State Machine
+ Skills
+ Agents
+ Business Rules
+ Events
+ Approvals
```

---

## 4.4 Agent

An **Agent** is a reasoning actor.

Recommended abstraction:

```text
Agent
=
Model
+ Instructions
+ Memory
+ Skills
+ Tools
+ Policies
+ Runtime
```

---

## 4.5 Plugin

A **Plugin** is a deployable extension unit.

A plugin may contain:

- skills,
- tools,
- MCP adapters,
- UI components,
- event handlers,
- business integrations.

Therefore:

```text
Plugin != Skill
```

A plugin can provide many skills.

---

# 5. Design Principles

## 5.1 Stable Core, Extensible Capability

The Agent Core should contain only generic intelligence primitives:

- planning,
- reasoning,
- tool calling,
- memory usage,
- agent delegation,
- reflection,
- evaluation hooks,
- policy checks.

Domain knowledge should live outside the Core.

---

## 5.2 Progressive Disclosure

Do not load all skill content into the model context.

Recommended flow:

```text
User Request
    ↓
Intent Detection
    ↓
Skill Metadata Search
    ↓
Candidate Ranking
    ↓
Select 1–3 skills
    ↓
Load selected SKILL.md
    ↓
Load resources only when needed
```

Three context levels are recommended:

### Level 0 — Registry metadata

Very small metadata:

```yaml
id: marketing.seo.keyword-research
name: Keyword Research
description: Research and cluster commercial search keywords
domain: marketing
intents:
  - keyword research
  - seo planning
```

### Level 1 — Skill instructions

Load only after routing.

```text
SKILL.md
```

### Level 2 — Supporting resources

Load on demand:

```text
references/
schemas/
examples/
templates/
scripts/
```

---

## 5.3 Least Privilege

A skill must declare only the tools and permissions it actually needs.

Avoid:

```yaml
tools:
  - "*"
```

Prefer:

```yaml
tools:
  - web.search
  - analytics.read
  - docs.create
```

---

## 5.4 External Skills Are Untrusted by Default

External skill instructions are data until reviewed.

AI Agent OS must assume that external skills may contain:

- prompt injection,
- tool poisoning,
- malicious shell commands,
- secret exfiltration,
- destructive instructions,
- hidden network calls,
- unsafe data handling.

---

## 5.5 Never Execute Moving Git References in Production

Do not install production skills by:

```yaml
ref: main
```

Always resolve to:

```yaml
commit: 4bc9a82...
```

and optionally store:

```yaml
sha256: ...
```

---

## 5.6 Human Approval for Capability Promotion

Agents may:

- discover,
- compare,
- evaluate,
- propose,
- stage.

Agents should not silently promote high-risk external capabilities into production.

---

# 6. Skill Sources

AI Agent OS should support multiple skill sources.

```text
Skill Sources
│
├── Built-in
├── Internal Organization
├── Official Vendor
├── Curated Community
├── Git Repository
├── Marketplace
└── Generated Candidate Skill
```

---

## 6.1 Built-in Skills

Owned by AI Agent OS.

Examples:

```text
core/
business/
productivity/
memory/
planning/
evaluation/
```

These are the most trusted skills.

---

## 6.2 Business Domain Packs

Examples:

```text
okr/
12-week-year/
tasks/
marketing/
crm/
sales/
finance/
projects/
```

The previously analyzed `marketingskills` repository fits this category better than a generic external catalog.

It can become a curated **Marketing Skill Pack**.

---

## 6.3 Official Vendor Skills

Examples may include skills published by:

- OpenAI
- Anthropic
- Google
- Microsoft
- Cloudflare
- Vercel
- Stripe
- Notion
- Figma
- HashiCorp
- Trail of Bits

These should still be version-pinned and evaluated.

Official does not mean unrestricted.

---

## 6.4 Community Skills

Community skills must pass additional review.

Default behavior:

```text
discoverable
but
not automatically trusted
```

---

# 7. `awesome-agent-skills` Integration Model

The repository should be integrated as a **Discovery Provider**.

Recommended adapter:

```text
AwesomeAgentSkillsProvider
```

Responsibilities:

```text
fetch catalog
    ↓
parse entries
    ↓
normalize metadata
    ↓
resolve source repository
    ↓
store discovery records
```

It must not:

- execute skills,
- automatically install every skill,
- grant permissions,
- bypass security,
- treat README inclusion as audit approval.

---

# 8. Skill Registry

The Skill Registry is the authoritative inventory of known skills.

Recommended registry scopes:

```text
discovered
verified
installed
active
deprecated
quarantined
```

---

## 8.1 Canonical Skill Manifest

Recommended AI Agent OS manifest:

```yaml
apiVersion: agentos.ai/v1
kind: Skill

metadata:
  id: marketing.seo.keyword-research
  name: Keyword Research
  version: 1.4.2
  description: Research, cluster and prioritize search keywords
  tags:
    - marketing
    - seo
    - research

publisher:
  name: example-org
  type: community
  verified: false

source:
  type: git
  repository: https://github.com/example/skills
  path: skills/keyword-research
  commit: 4bc9a82c...
  license: MIT

capability:
  domain: marketing
  category: seo
  intents:
    - keyword research
    - keyword clustering
    - seo planning
  inputs:
    - website
    - target_market
  outputs:
    - keyword_clusters
    - opportunity_report

runtime:
  format: skill-md
  entrypoint: SKILL.md
  resources:
    - references/**
    - templates/**
  tools:
    - web.search
    - analytics.read
    - docs.create

permissions:
  network:
    mode: allowlist
    hosts:
      - "*.google.com"
      - "*.bing.com"
  filesystem:
    mode: workspace
  secrets: []
  business_actions:
    write: false

risk:
  level: low
  destructive_actions: false
  external_side_effects: false

trust:
  tier: T2
  human_reviewed: true
  security_scan: passed

quality:
  eval_score: 0.91
  success_rate: 0.88
  runs: 523

compatibility:
  agentos: ">=0.4"
  platforms:
    - claude-code
    - codex
    - cursor
    - gemini-cli
```

---

# 9. Canonical Skill Adapter Layer

Different ecosystems use different folder paths and metadata.

AI Agent OS should normalize them.

```text
Claude Skill
       │
Codex Skill
       │
Cursor Skill
       │
Gemini Skill
       │
OpenCode Skill
       │
Internal Skill
       ↓
Skill Normalizer
       ↓
Canonical Skill Manifest
```

Recommended interface:

```python
class SkillAdapter(Protocol):
    def detect(self, source: SkillSource) -> bool: ...
    def parse(self, source: SkillSource) -> CanonicalSkill: ...
    def validate(self, skill: CanonicalSkill) -> ValidationResult: ...
```

Possible implementations:

```text
ClaudeSkillAdapter
CodexSkillAdapter
GeminiSkillAdapter
CursorSkillAdapter
OpenCodeSkillAdapter
GenericSkillMdAdapter
AgentOSNativeSkillAdapter
```

---

# 10. Skill Trust Model

Recommended trust tiers:

| Tier | Source | Default Policy |
|---|---|---|
| T0 | AI Agent OS internal | trusted |
| T1 | approved official vendor | verified |
| T2 | reviewed community | sandbox / scoped |
| T3 | unknown external | disabled by default |
| T4 | rejected / malicious | quarantined |

---

## 10.1 Trust Is Not Binary

Trust score can combine:

```text
publisher reputation
source integrity
human review
security scan
evaluation score
usage history
incident history
permission scope
update stability
```

Example:

```text
TrustScore
=
0.20 Publisher
+ 0.15 Integrity
+ 0.20 Security
+ 0.20 Evaluation
+ 0.15 Runtime History
+ 0.10 Human Review
```

---

# 11. Skill Permission Model

A skill may request permissions.

Example capability classes:

```text
READ_LOCAL
WRITE_WORKSPACE
READ_NETWORK
EXTERNAL_WRITE
SEND_MESSAGE
MODIFY_BUSINESS_DATA
DEPLOY
EXECUTE_CODE
ACCESS_SECRET
DELETE_DATA
FINANCIAL_ACTION
```

Recommended policy:

```text
read-only                 → automatic when trusted
workspace write           → scoped
external write            → policy dependent
send email/message        → user/business policy
delete                    → approval
financial action          → approval
secret access             → explicit allowlist
production deploy         → approval or controlled workflow
```

---

# 12. Skill Lifecycle

Recommended states:

```text
DISCOVERED
    ↓
IMPORTED
    ↓
SCANNED
    ↓
VERIFIED
    ↓
STAGED
    ↓
ACTIVE
    ↓
DEPRECATED
```

Alternative states:

```text
QUARANTINED
REJECTED
DISABLED
REVOKED
```

---

## 12.1 Update Lifecycle

Never update an active skill in place.

```text
ACTIVE v1
    │
    └── upstream v2 detected
             ↓
          IMPORTED
             ↓
            DIFF
             ↓
            SCAN
             ↓
            EVAL
             ↓
          STAGED v2
          /       \
      PROMOTE    REJECT
```

---

# 13. Skill Supply Chain

This is a required production component.

Recommended pipeline:

```text
DISCOVER
    ↓
FETCH
    ↓
RESOLVE VERSION
    ↓
NORMALIZE
    ↓
STATIC INSPECTION
    ↓
SECURITY SCAN
    ↓
PERMISSION ANALYSIS
    ↓
EVALUATION
    ↓
HUMAN / POLICY APPROVAL
    ↓
PIN COMMIT
    ↓
STORE ARTIFACT
    ↓
INSTALL
    ↓
SANDBOX TEST
    ↓
PROMOTE
    ↓
OBSERVE
```

---

## 13.1 Artifact Store

For reproducibility, store a local immutable copy or content-addressed package:

```text
skills-cache/
  sha256/
    ab/
      abcd1234...
```

Metadata should record:

```yaml
source_commit: ...
content_hash: ...
scan_result: ...
eval_version: ...
approval_id: ...
installed_at: ...
```

---

# 14. Skill Security Pipeline

Minimum checks:

## Static

- suspicious shell commands,
- environment variable access,
- secret references,
- arbitrary network access,
- file deletion,
- recursive writes,
- prompt injection markers,
- hidden encoded payloads,
- dependency downloads,
- executable scripts.

## Semantic

Use an evaluator model to inspect:

- whether the instructions try to override system policy,
- whether the skill asks the model to reveal secrets,
- whether it instructs unauthorized side effects,
- whether its declared permissions match actual behavior.

## Runtime

Run in sandbox:

```text
no production secrets
no production network
test dataset
restricted filesystem
synthetic tools
```

---

# 15. Skill Router

The Skill Router determines which skills should be loaded.

Recommended pipeline:

```text
User Goal
   ↓
Intent Extraction
   ↓
Required Capabilities
   ↓
Metadata Retrieval
   ↓
Policy Filter
   ↓
Trust Filter
   ↓
Compatibility Filter
   ↓
Semantic Ranking
   ↓
Cost / Latency Ranking
   ↓
Select Skill Set
```

---

## 15.1 Routing Score

A possible score:

```text
Score(skill)
=
w1 * Relevance
+ w2 * Trust
+ w3 * EvalQuality
+ w4 * HistoricalEffectiveness
+ w5 * BusinessFit
- w6 * Cost
- w7 * Risk
- w8 * Latency
```

---

## 15.2 Skill Composition

The router should support:

```text
single skill
skill chain
parallel skills
fallback skill
review skill
```

Example:

```text
marketing campaign
   ↓
market-research
   ↓
positioning
   ↓
copywriting
   ↓
seo
   ↓
review
```

or:

```text
                   ┌─ competitor research
campaign planner ──┼─ seo research
                   └─ customer research
                           ↓
                        synthesis
```

---

# 16. Skill Runtime

The Skill Runtime is responsible for executing skill instructions safely.

Responsibilities:

- load skill context,
- bind allowed tools,
- enforce permissions,
- track token budget,
- track tool calls,
- record traces,
- enforce timeout,
- isolate files,
- apply business policies,
- capture outputs,
- emit evaluation signals.

Suggested object:

```python
class SkillRuntime:
    async def execute(
        self,
        skill: SkillVersion,
        task: TaskContext,
        agent: AgentContext,
        permissions: PermissionGrant,
    ) -> SkillExecutionResult:
        ...
```

---

# 17. Skill Context Budget

To prevent context explosion:

```yaml
context:
  metadata_tokens: 100
  instruction_tokens_max: 6000
  resource_tokens_max: 12000
  total_tokens_max: 18000
```

Resources should be fetched on demand.

---

# 18. Skill Evaluation

Every production-grade skill should have evals.

Recommended dimensions:

```text
task success
accuracy
hallucination rate
tool correctness
policy compliance
cost
latency
human acceptance
output quality
side-effect correctness
```

---

## 18.1 Eval Types

### Unit Eval

One skill, fixed input.

### Scenario Eval

Skill inside a realistic task.

### Regression Eval

Run after upstream changes.

### Adversarial Eval

Prompt injection / malformed input.

### Permission Eval

Ensure unauthorized actions are blocked.

### Business Eval

Measure whether the output improves the target KPI.

---

# 19. Skill Observability

Record:

```text
skill_id
skill_version
agent_id
task_id
model
input intent
selected tools
tool success/failure
duration
token usage
cost
final result
evaluation score
human feedback
exceptions
```

---

## 19.1 Skill Performance Store

Example schema:

```sql
skill_run (
  id,
  skill_id,
  skill_version,
  agent_id,
  task_id,
  status,
  started_at,
  finished_at,
  tokens_in,
  tokens_out,
  tool_calls,
  cost,
  eval_score,
  user_feedback
)
```

This enables learning from experience.

---

# 20. Self-Improvement Through Skills

AI Agent OS should favor **capability evolution through skills** before modifying Agent Core prompts or source code.

Recommended loop:

```text
Observe
   ↓
Detect repeated failures
   ↓
Classify capability gap
   ↓
Search Skill Registry
   ↓
Search External Sources
   ↓
Evaluate candidates
   ↓
Generate recommendation
   ↓
Human Approval
   ↓
Stage new skill
   ↓
A/B or canary
   ↓
Promote
```

This is a safer form of self-improvement.

---

## 20.1 Capability Gap Object

Example:

```yaml
gap:
  id: gap_123
  domain: marketing
  capability: keyword clustering

evidence:
  failed_tasks: 8
  period: 14d
  average_eval_score: 0.54

recommendation:
  type: install_skill
  candidates:
    - skill_a
    - skill_b
```

---

# 21. Human Governance

AI Agent OS should allow agents to make proposals, but preserve human control.

Agent may propose:

```text
install new skill
upgrade skill
change trust level
grant additional permission
deprecate underperforming skill
replace skill
promote staged skill
```

Approval records should be auditable.

Example:

```yaml
approval:
  id: apr_456
  action: promote_skill
  skill: marketing.seo.keyword-research@1.5.0
  reviewer: user
  created_at: ...
  reason: ...
```

---

# 22. Integration with Multi-Agent Architecture

Skills and agents should remain separate.

Example:

```text
Planner Agent
    ↓
selects skills
    ↓
delegates
 ┌──────────────┬──────────────┐
 │              │              │
SEO Agent   Research Agent   Copy Agent
 │              │              │
skills         skills         skills
```

A specialist agent is a persistent reasoning role.

A skill is a portable capability.

---

# 23. Integration with Google ADK / Python Agent Core

The Python Agent Core remains the orchestration layer.

Recommended modules:

```text
agentos/
├── core/
│   ├── agent.py
│   ├── planner.py
│   ├── runtime.py
│   └── policies.py
│
├── skills/
│   ├── registry.py
│   ├── router.py
│   ├── loader.py
│   ├── runtime.py
│   ├── evaluator.py
│   ├── trust.py
│   ├── permissions.py
│   ├── lifecycle.py
│   └── supply_chain.py
│
├── adapters/
│   ├── claude_skill.py
│   ├── codex_skill.py
│   ├── gemini_skill.py
│   └── generic_skill.py
│
├── tools/
├── memory/
├── agents/
├── improvement/
└── observability/
```

Google ADK can be used for agent orchestration while the Skill Layer remains an AI Agent OS abstraction.

Do not couple the canonical skill registry directly to one agent framework.

---

# 24. Integration with DeepSeek Harness Philosophy

The architecture should preserve the simple plugin/harness philosophy:

```text
small core
+ explicit extension points
+ filesystem-friendly packages
+ simple conventions
+ on-demand loading
```

Recommended:

```text
plugin
 ├── manifest.yaml
 ├── skills/
 ├── tools/
 ├── resources/
 └── ui/
```

A business plugin may provide:

```text
okr-plugin
 ├── skills/
 │   ├── create-objective/
 │   ├── weekly-review/
 │   └── score-key-results/
 │
 ├── tools/
 │   └── okr_api.py
 │
 └── ui/
```

---

# 25. Integration with Encore Business Layer

Encore should remain responsible for typed business services and domain state.

Example services:

```text
identity
organizations
okr
tasks
projects
crm
marketing
billing
events
workflow
```

The Agent Core should interact with them through tools/APIs.

```text
Agent
  ↓
Skill
  ↓
Tool Adapter
  ↓
Encore Business API
  ↓
Database
```

Encore does not need to parse `SKILL.md`.

---

# 26. Example — OKR

Business service:

```text
OKR Service
```

Tools:

```text
okr.get_objectives
okr.create_objective
okr.update_key_result
okr.get_progress
```

Skills:

```text
okr.objective-design
okr.weekly-checkin
okr.score-key-results
okr.identify-at-risk-krs
okr.quarterly-review
```

Workflow:

```text
Quarterly OKR Planning
    ↓
strategy context
    ↓
objective-design skill
    ↓
KR quality review
    ↓
human approval
    ↓
persist via OKR service
```

---

# 27. Example — 12 Week Year

Skills:

```text
12wy.define-vision
12wy.build-12-week-plan
12wy.weekly-plan
12wy.score-execution
12wy.weekly-accountability
12wy.review-cycle
```

Tools:

```text
tasks.*
calendar.*
metrics.*
notes.*
```

The 12 Week Year implementation therefore becomes a domain skill pack layered over business APIs.

---

# 28. Example — Tasks

Tools:

```text
task.create
task.update
task.complete
task.assign
task.query
```

Skills:

```text
tasks.prioritize
tasks.breakdown
tasks.daily-plan
tasks.detect-blockers
tasks.weekly-review
```

The task database remains business state.

The skills contain planning behavior.

---

# 29. Example — Marketing

Recommended integration:

```text
Marketing Skill Pack
│
├── research
├── positioning
├── seo
├── content
├── copywriting
├── lifecycle
├── analytics
└── growth
```

External skills from the broader ecosystem can complement internal marketing skills.

Preferred priority:

```text
internal approved
    ↓
official verified
    ↓
reviewed community
    ↓
unknown external
```

---

# 30. Skill Registry Storage Model

Recommended core tables:

```text
skills
skill_versions
skill_sources
skill_permissions
skill_dependencies
skill_evaluations
skill_runs
skill_reviews
skill_approvals
skill_incidents
skill_tags
capability_embeddings
```

---

## 30.1 `skills`

```sql
skills (
  id,
  canonical_name,
  display_name,
  domain,
  category,
  description,
  publisher_id,
  trust_tier,
  status,
  created_at,
  updated_at
)
```

---

## 30.2 `skill_versions`

```sql
skill_versions (
  id,
  skill_id,
  version,
  source_repo,
  source_path,
  source_commit,
  content_hash,
  manifest_json,
  status,
  created_at
)
```

---

## 30.3 `skill_evaluations`

```sql
skill_evaluations (
  id,
  skill_version_id,
  eval_suite,
  score,
  security_score,
  policy_score,
  latency_ms,
  cost,
  report_json,
  created_at
)
```

---

# 31. Registry APIs

Suggested API surface:

```text
GET    /skills
GET    /skills/:id
GET    /skills/:id/versions
POST   /skills/discover
POST   /skills/import
POST   /skills/:id/evaluate
POST   /skills/:id/stage
POST   /skills/:id/promote
POST   /skills/:id/disable
POST   /skills/:id/upgrade
GET    /capabilities/search
GET    /skill-runs
```

---

# 32. Domain Events

Recommended events:

```text
skill.discovered
skill.imported
skill.scan_completed
skill.evaluation_completed
skill.approval_requested
skill.approved
skill.rejected
skill.staged
skill.activated
skill.execution_started
skill.execution_completed
skill.execution_failed
skill.incident_detected
skill.update_available
skill.deprecated
capability.gap_detected
```

These events can feed the Event Bus and Improvement Engine.

---

# 33. Skill Search Architecture

Use hybrid retrieval.

```text
Metadata Filtering
+
Keyword Search
+
Semantic Embedding Search
+
Historical Performance Ranking
```

Search fields:

```text
name
description
domain
category
intents
tool dependencies
business capabilities
platform compatibility
trust tier
eval score
```

---

# 34. Skill Conflict Resolution

Multiple skills may serve the same capability.

Resolver should compare:

```text
relevance
trust
business fit
tool compatibility
model compatibility
eval score
cost
latency
recent success rate
permission risk
```

A default skill may be assigned per capability.

Example:

```yaml
capability: marketing.seo.keyword-research

default:
  skill: internal.keyword-research

fallback:
  - openai-compatible.skill-x
  - community.skill-y
```

---

# 35. Dependency Management

Skills may depend on:

```text
tools
other skills
runtime packages
MCP servers
business services
secrets
models
```

Manifest:

```yaml
dependencies:
  skills:
    - research.web@^2
  tools:
    - browser.search
  services:
    - marketing-analytics
  models:
    minimum_context: 32000
```

The installer must resolve dependencies before activation.

---

# 36. Compatibility Matrix

A skill version should declare:

```yaml
compatibility:
  agentos: ">=0.4,<1.0"
  python: ">=3.12"
  platforms:
    - agentos
    - codex
  models:
    capabilities:
      - tool_calling
      - structured_output
```

---

# 37. Built-in vs External Skills

Recommended hierarchy:

```text
Layer A — Core Skills
Layer B — Business Skills
Layer C — Organization Skills
Layer D — Verified External
Layer E — Community
```

Routing preference should generally follow this hierarchy unless evaluation data indicates otherwise.

---

# 38. Skill Marketplace — Future Direction

The Registry can later evolve into a marketplace.

Potential features:

```text
search
install
version history
trust badges
permissions
eval score
usage metrics
reviews
publisher verification
signed packages
enterprise allowlists
private skill catalogs
```

Important:

Marketplace is a product layer.

The underlying Registry, Trust, Supply Chain, and Runtime should exist first.

---

# 39. Signed Skill Packages

Future production hardening:

```text
skill package
    ↓
publisher signature
    ↓
registry verification
    ↓
content hash
    ↓
organization allowlist
```

This provides stronger supply-chain integrity.

---

# 40. Self-Generated Skills

AI Agent OS may eventually generate candidate skills.

However, generated skills must not become active automatically.

Recommended lifecycle:

```text
Agent detects repeated procedure
        ↓
draft skill
        ↓
generate tests
        ↓
sandbox eval
        ↓
human review
        ↓
publish internal skill
```

This turns successful repeated behavior into reusable organizational capability.

---

# 41. Skill Distillation

A useful long-term capability:

```text
successful task traces
       ↓
pattern mining
       ↓
repeatable procedure
       ↓
skill draft
       ↓
eval
       ↓
human approval
       ↓
internal skill
```

This is a practical mechanism for organizational learning.

---

# 42. Memory Integration

Skill runtime should interact with memory carefully.

Recommended scopes:

```text
task memory
agent memory
user memory
organization memory
skill execution memory
```

Skill instructions should not receive all memory by default.

Use policy-based retrieval.

---

# 43. Skill Learning from Execution History

Historical metrics may influence routing.

Example:

```text
Skill A
success: 92%
cost: $0.04
latency: 8s

Skill B
success: 89%
cost: $0.01
latency: 3s
```

For low-risk tasks:

```text
choose B
```

For high-value tasks:

```text
choose A
```

This creates adaptive skill selection without changing the core model.

---

# 44. Failure Handling

Skill execution should support:

```text
retry
fallback
alternate skill
alternate tool
human escalation
rollback
```

Example:

```text
skill A fails
    ↓
classify error
    ↓
tool issue? → retry
skill issue? → fallback skill B
policy issue? → stop
high risk? → human escalation
```

---

# 45. Skill Review Agent

Introduce an optional internal specialist:

```text
Skill Review Agent
```

Responsibilities:

- inspect new skill manifests,
- compare permission requests,
- identify suspicious instructions,
- review updates,
- generate human-readable risk reports.

This agent does not have authority to approve by itself.

---

# 46. Skill Curator Agent

Optional internal specialist:

```text
Skill Curator Agent
```

Responsibilities:

```text
monitor sources
deduplicate
classify
tag
compare
score relevance
recommend adoption
```

Useful with `awesome-agent-skills`.

---

# 47. Skill Eval Agent

Optional internal specialist:

```text
Skill Eval Agent
```

Responsibilities:

```text
generate test cases
run benchmark
compare skill versions
detect regressions
produce scorecard
```

---

# 48. Reference Implementation Flow

User asks:

```text
"Create an SEO launch plan for product X"
```

System:

```text
1. Planner identifies:
   - market research
   - keyword research
   - content planning
   - SEO review

2. Skill Router searches registry.

3. Policy prefers:
   internal skills > verified vendor > reviewed community.

4. Selected skills:
   marketing.market-research@2.1
   marketing.keyword-research@1.4
   marketing.content-plan@3.0
   web.seo-review@1.2

5. Runtime loads only selected SKILL.md files.

6. Each skill receives scoped tools.

7. Outputs are passed between skills.

8. Reviewer Agent evaluates final result.

9. Skill run metrics are recorded.

10. If repeated failures occur in keyword clustering:
    capability.gap_detected event is emitted.
```

---

# 49. Proposed Repository Layout for AI Agent OS

```text
ai-agent-os/
│
├── apps/
├── services/
├── agentos/
│   ├── core/
│   ├── agents/
│   ├── skills/
│   ├── tools/
│   ├── memory/
│   ├── policies/
│   ├── improvement/
│   └── observability/
│
├── skillpacks/
│   ├── core/
│   ├── okr/
│   ├── 12-week-year/
│   ├── tasks/
│   ├── marketing/
│   └── engineering/
│
├── registry/
│   ├── sources.yaml
│   ├── approved.yaml
│   ├── blocked.yaml
│   └── policies/
│
├── evals/
│   ├── skills/
│   ├── agents/
│   └── workflows/
│
└── docs/
```

---

# 50. Proposed Fork Role for `vutasoftvn/awesome-agent-skills`

The fork should not merely mirror upstream forever.

Recommended role:

> **AI Agent OS Curated Skill Intelligence Feed**

Potential additions:

```text
registry/
  sources.yaml

catalog/
  official.yaml
  community.yaml
  recommended.yaml

policies/
  trust-policy.yaml
  permission-policy.yaml

evals/
  skill-scorecards/

approved/
  ai-agent-os.yaml

blocked/
  skills.yaml
```

This repository can remain lightweight while becoming useful to the Agent OS ecosystem.

---

# 51. Recommended Adoption Policy

## Automatically discover

- official sources,
- curated community catalogs,
- approved private repositories.

## Automatically import metadata

Allowed.

## Automatically download source for inspection

Allowed in isolated environment.

## Automatically execute

Not allowed for unknown external skills.

## Automatically stage

Allowed for low-risk candidates after successful scans/evals.

## Automatically promote to production

Only for explicitly allowed trust/policy classes.

For most external skills:

```text
human approval required
```

---

# 52. Phase Plan

## Phase 1 — Foundation

Build:

- Canonical Skill Manifest
- local Skill Registry
- Skill Loader
- Skill Router
- built-in skills
- trust tiers
- basic tool permission model

Target:

```text
AI Agent OS can execute internal skills cleanly.
```

---

## Phase 2 — External Import

Build:

- Git source importer
- `awesome-agent-skills` discovery adapter
- skill format adapters
- version pinning
- content hashing
- basic static scanner

Target:

```text
AI Agent OS can discover and safely stage external skills.
```

---

## Phase 3 — Eval & Governance

Build:

- eval harness,
- skill scorecards,
- approval workflow,
- update diff,
- canary promotion,
- rollback.

Target:

```text
external skills can enter production through governance.
```

---

## Phase 4 — Adaptive Routing

Build:

- semantic capability search,
- historical performance ranking,
- fallback selection,
- cost/risk-aware routing.

Target:

```text
agents choose skills dynamically.
```

---

## Phase 5 — Self-Improvement

Build:

- capability gap detector,
- skill recommendation engine,
- candidate evaluator,
- generated skill proposals,
- human approval UI.

Target:

```text
AI Agent OS can safely propose its own capability upgrades.
```

---

# 53. MVP Scope

For the first implementation, avoid overbuilding.

MVP:

```text
1. skills stored in filesystem
2. manifest.yaml
3. SKILL.md
4. registry in PostgreSQL
5. Python SkillLoader
6. semantic search
7. scoped tools
8. commit pinning
9. manual approval
10. basic evaluation
```

Do not start with a full marketplace.

---

# 54. MVP Skill Folder

```text
skills/
  marketing/
    keyword-research/
      manifest.yaml
      SKILL.md
      references/
      tests/
```

---

# 55. MVP Router Pseudocode

```python
async def select_skills(task, registry, policy):
    intent = await extract_intent(task)

    candidates = await registry.search(
        query=intent.summary,
        capabilities=intent.capabilities,
    )

    candidates = [
        skill
        for skill in candidates
        if policy.is_allowed(skill)
    ]

    ranked = rank(
        candidates,
        relevance=True,
        trust=True,
        eval_score=True,
        historical_success=True,
        risk=True,
    )

    return ranked[:3]
```

---

# 56. MVP Loader Pseudocode

```python
async def load_skill(skill_version):
    verify_hash(skill_version)

    manifest = read_manifest(skill_version)
    instructions = read_skill_md(skill_version)

    return LoadedSkill(
        manifest=manifest,
        instructions=instructions,
        resources=LazyResourceLoader(skill_version),
    )
```

---

# 57. MVP Runtime Pseudocode

```python
async def run_skill(skill, task, agent):
    allowed_tools = permission_engine.bind(
        skill.manifest.runtime.tools,
        skill.manifest.permissions,
    )

    with sandbox(skill):
        result = await agent.execute(
            task=task,
            instructions=skill.instructions,
            tools=allowed_tools,
        )

    record_skill_run(skill, task, result)

    return result
```

---

# 58. Acceptance Criteria

The Skill Layer is considered production-ready when:

- no external skill executes from a moving branch,
- every active skill has a pinned version,
- every skill has explicit tool dependencies,
- every external skill has a trust tier,
- every side-effecting skill has permission declarations,
- every active external skill has an evaluation report,
- skill execution is traceable,
- skill rollback is supported,
- external updates never silently replace active versions,
- agents can discover but cannot self-promote high-risk skills,
- a human approval path exists,
- capability gaps can generate recommendations.

---

# 59. Non-Goals

This architecture does not require:

- copying every skill from public catalogs,
- loading thousands of skills into context,
- tying AI Agent OS to one LLM provider,
- tying AI Agent OS to one coding assistant,
- making every tool a skill,
- making every workflow a skill,
- allowing arbitrary shell execution,
- allowing autonomous production upgrades.

---

# 60. Final Architecture

The revised AI Agent OS architecture becomes:

```text
AI Agent OS
│
├── Agent Core
│   ├── reasoning
│   ├── planning
│   ├── delegation
│   └── policy hooks
│
├── Multi-Agent Runtime
│
├── Skill Ecosystem
│   ├── Registry
│   ├── Discovery
│   ├── Router
│   ├── Loader
│   ├── Runtime
│   ├── Trust
│   ├── Permissions
│   ├── Supply Chain
│   ├── Evaluation
│   └── Lifecycle
│
├── Tools & MCP
│
├── Memory & Knowledge
│
├── Business OS
│   ├── OKR
│   ├── 12 Week Year
│   ├── Tasks
│   ├── CRM
│   ├── Marketing
│   └── other domains
│
├── Improvement Engine
│   ├── capability gap detection
│   ├── skill recommendation
│   ├── skill distillation
│   └── upgrade proposals
│
├── Governance
│   ├── approvals
│   ├── audit
│   ├── risk policy
│   └── trust policy
│
└── Observability & Evaluation
```

---

# 61. Final Recommendation

`awesome-agent-skills` should be integrated into AI Agent OS as:

```text
External Discovery Source
```

not as:

```text
Runtime Dependency
```

The correct architectural value is to use it to bootstrap:

```text
Skill Registry
+
Skill Discovery
+
Trust & Permission Model
+
Skill Supply Chain
+
Evaluation
+
Self-Improvement
```

The long-term design goal is:

> AI Agent OS should not need to know every capability in advance.

Instead, it should be able to:

```text
understand the goal
    ↓
identify required capabilities
    ↓
discover available skills
    ↓
select trusted skills
    ↓
execute with scoped permissions
    ↓
measure effectiveness
    ↓
detect capability gaps
    ↓
propose improvements
    ↓
obtain human approval
    ↓
evolve safely
```

This makes the Skill Layer one of the core pillars of AI Agent OS, alongside:

```text
Agent Core
Memory
Tools
Business Services
Evaluation
Governance
```

and creates a practical path toward a **self-improving but human-governed Agent Operating System**.

---

# 62. Related Sources

- `https://github.com/vutasoftvn/awesome-agent-skills`
- `https://github.com/VoltAgent/awesome-agent-skills`
- `https://github.com/vutasoftvn/marketingskills`
- Google ADK
- DeepSeek Harness
- TencentDB Agent Memory

---

# 63. Decision Summary

**Adopt**

- portable skill concept,
- progressive disclosure,
- scoped tools,
- external discovery,
- cross-platform skill compatibility,
- curated official/community sources.

**Extend**

- canonical manifest,
- trust tiers,
- version pinning,
- integrity hashes,
- permission model,
- eval score,
- observability,
- lifecycle,
- approval workflow,
- supply-chain security.

**Do not adopt directly**

- README as production registry,
- mutable Git branch execution,
- automatic trust based on catalog inclusion,
- bulk context loading,
- unrestricted tool access.

**AI Agent OS principle**

> Skills are replaceable capabilities.  
> Tools are atomic actions.  
> Agents are reasoning actors.  
> Workflows coordinate execution.  
> Business services own domain state.  
> Governance controls change.  
> Evaluation determines what should be trusted.
