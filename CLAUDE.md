# CLAUDE.md

# COSA Core Coding Rules

COSA is a **Founder / Company Operating System with a composable Agent Harness**.

Do not treat COSA as a collection of independent AI agents.

---

## 1. Architecture First

Before coding:

1. Inspect the existing code.
2. Reuse existing components when possible.
3. Identify the correct architecture layer.
4. Make the smallest safe change.
5. Preserve existing working behavior.

Do not perform large rewrites unless explicitly required.

---

## 2. COSA Architecture

Use this mental model:

```text
COSA
├── Business Core
├── Co-founder Orchestrator
├── Agent Runtime
├── Agent Profiles
├── Skills
├── Tools
├── Workflows
├── Knowledge
├── Memory / Sessions
└── Executors
```

Current concrete instantiation (update when it changes, not fixed forever): Co-founder Orchestrator = Google ADK; executing Agent Runtime = DeepSeek Harness via the `AgentRuntime` adapter. Check `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` for the current canonical owner of each component before adding code.

Business Core must remain independent from LLM vendors.

---

## 3. Agent Rule

Do not create a new Agent by default.

First decide whether the requested capability is actually a:

```text
Skill
Tool
Workflow
Knowledge
Executor
Integration
```

Create a new Agent Profile only when there is a real new business role.

Marketing, Sales, Finance, Legal, Research, etc. are profiles using the same Agent Runtime.

---

## 4. Agent Composition

Use:

```text
Agent
=
Profile
+
Model
+
Context
+
Skills
+
Tools
+
Workflows
+
Permissions
+
Runtime
```

Avoid duplicated prompts, tools, skills, or runtimes between agents.

---

## 5. Business Core

Business entities such as:

```text
Company
Project
OKR
Task
CRM
Marketing
Sales
Finance
Legal
```

must not depend directly on:

```text
DeepSeek
Claude
OpenAI
DeepSeek Harness
```

Use stable COSA interfaces/adapters.

Workforce (human or AI) must resolve through one unified identity (`WorkforceMember`) — do not create separate personnel concepts/tables for AI versus humans.

---

## 6. DeepSeek Harness

DeepSeek Harness is an optional runtime implementation.

Use:

```text
COSA AgentRuntime
        ↓
DeepSeekHarnessAdapter
```

Never couple COSA Business Core directly to DeepSeek Harness internals.

Do not fork DeepSeek Harness into COSA core.

---

## 6a. Google ADK Orchestrator

Google ADK is the orchestration runtime for the Co-founder Orchestrator layer.

Use:

```text
COSA Co-founder Orchestrator
        ↓
AdkCofounderOrchestrator
```

ADK never calls a model provider or tool/domain logic directly — always through the existing ModelGateway and GovernanceKernel/TaskBoardService.

Do not fork governance logic into ADK.

---

## 7. Claude Code / Codex

Claude Code and Codex are **coding executors**, not the COSA Agent Runtime.

Correct flow:

```text
COSA
→ Coding Workflow
→ Executor
→ Claude Code / Codex
```

---

## 8. Skills, Tools and Workflows

Use:

* **Skill** = how to perform something.
* **Tool** = executable capability.
* **Workflow** = repeatable multi-step process.

Do not hide deterministic business workflows inside long prompts.

Prefer reusable Skills + Tools + Workflows.

---

## 9. Intent and Context

Never trigger project analysis from a greeting or unrelated conversation.

Example:

```text
"chào"
```

must not automatically:

```text
load project
search project database
run project workflow
```

Load project context only when the user, UI, session, or workflow explicitly requires it.

---

## 10. Local First

Company operational data is local/private by default.

Prefer:

```text
PostgreSQL
→ business data

SQLite
→ sessions, traces, cache

Markdown / Files
→ knowledge, prompts, skills, specs, templates

COSA Server
→ license, tier, entitlement, update metadata
```

Do not introduce automatic cloud synchronization without explicit requirements.

A business data aggregate has exactly one authority at a time (Personal Mode: local; Team Mode: cloud, switched via an explicit action) — do not design active-active.

---

## 11. Permissions

Permissions must be enforced by deterministic code, not by the LLM.

High-risk actions such as:

```text
production deployment
destructive database changes
sending external messages
credential changes
financial actions
```

must require appropriate permission/approval.

---

## 12. Sessions and Trace

Meaningful Agent executions should be traceable.

Track operational events such as:

```text
intent
context
skill
workflow
tool
result
artifact
error
status
```

Do not store or expose private chain-of-thought.

---

## 13. Structured State

Application state must be structured.

Do not make UI logic depend on parsing natural-language AI responses.

Prefer:

```json
{
  "status": "completed"
}
```

over detecting words such as `"done"` or `"completed"` in chat text.

---

## 14. No Duplicate Architecture

Before adding a:

```text
prompt
skill
tool
workflow
agent
service
```

search the repository first.

Prefer composition and reuse over duplication.

Before adding a new Agent/personnel identity model, read `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` — see the `Agent`/`AgentDefinition`/`AgentProfile`/`WorkforceMember` fragmentation history (4 duplicate models found 2026-08-20) as a concrete example of what happens without checking first.

---

## 15. External Projects

When integrating an external repository or framework, classify what COSA actually needs:

```text
Runtime
Skill
Tool
Workflow
Memory
Knowledge
Executor
Integration
UI
```

Do not copy entire projects by default.

---

## 16. Coding Safety

Before significant changes:

```bash
git status
```

Do not destroy or overwrite existing user changes.

Avoid destructive commands unless explicitly required.

Database schema changes must use migrations.

Never hardcode or commit API keys/secrets.

---

## 17. Testing

Add or update tests for changed behavior.

Important regression rule:

```text
"chào"
```

must never trigger automatic project lookup.

Do not claim completion without validating the affected functionality.

---

## 18. COSA North Star

When choosing between:

```text
more agents
vs
better composition
```

choose **better composition**.

When choosing between:

```text
more prompt logic
vs
deterministic application logic
```

choose **deterministic application logic**.

When choosing between:

```text
vendor coupling
vs
COSA abstraction
```

choose **COSA abstraction**.

A new capability should normally be implemented as:

```text
Skill
+
Tool
+
Workflow
+
Agent Profile assignment
```

not as another independent AI system.

## Planning Before Execution For non-trivial changes: 1. Inspect the existing codebase first. 2. Understand current architecture and conventions. 3. Create an implementation plan before editing files. 4. Identify affected files, dependencies and risks. 5. Define acceptance criteria. 6. Execute incrementally by task or milestone. 7. Test after meaningful changes. 8. Observe errors and update the plan when assumptions fail. 9. Do not continue blindly after a failed dependency. 10. Verify acceptance criteria before declaring completion. Rule: NO PLAN → NO EXECUTION Do not rewrite working architecture unless the plan explicitly requires it. Do not create duplicate modules when equivalent functionality already exists. Prefer extending COSA's existing architecture over introducing parallel systems.
