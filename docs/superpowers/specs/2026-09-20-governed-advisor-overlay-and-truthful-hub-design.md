# Governed Advisor Overlay and Truthful Hub Design

## Goal

Make an Executive Advisor a versioned, immutable overlay that can advise only
through an active Project agent deployment, and make every Hub action either
perform a real API operation or present an unavailable state. A development
stack must be able to prove the complete path from UI or Company command to a
durable run, worker result, and read-back state.

## Scope

This change covers:

- Executive Board role framing, dispatch, worker execution, callback, and
  audit identity.
- Built-in advisor assets and their relationship to Project agent deployments.
- Agent workflow AGENT steps, whose kernel invocation must conform to the
  `ExecutionKernel` contract.
- Hub direct specialist chat, task creation from a response, and test-run UI.
- Contract, integration, process E2E, and Flutter tests for these paths.

It does not add arbitrary founder-authored agents or an open workflow canvas.
It does not change Company ownership of Workspace, Project, authority,
business records, or approval decisions.

## Source-backed current state

Company already evaluates a role against three independent facts for a Project:
the Workspace office state, the Project agent deployment state, and lifecycle
stage eligibility. It pins the deployment AgentSpec in `SelectedRolePin`.

The worker then forwards that pin to `ExecutiveBoardRunner`. The runner ignores
the pinned AgentSpec and constructs `executive.board.<role>` in memory. The
contract has fifteen `requiredAgentSpec` entries, while the runtime catalog
seeds only ten executive AgentSpecs and has no spec for Chief of Staff, CFO,
CMO, COO, or CCO. This prevents an audit from answering which immutable
advisor definition actually produced an analysis.

Hub direct specialist chat calls a test-run API and fabricates a local answer
when it cannot obtain one. Its task conversion callback only shows a success
toast. The test-run drawer also only shows a success toast. These are not
valid production actions.

`AgentWorkflowStep` verifies deployment and manifest pins but calls the kernel
with one argument, contrary to the two-argument `ExecutionKernel` contract.

## Terminology and ownership

| Term | Owner | Meaning |
|---|---|---|
| Project deployment | Company | A live binding from a Project to a Workspace agent profile. It is the authority to use that profile in that Project. |
| Advisor overlay | Agent registry | A built-in immutable AgentSpec for a role such as CFO. It supplies advisor instructions, output schema, model policy, and skill pins. It has no independent Project authority. |
| Advisor execution pin | Deliberation frame | The exact advisor overlay identity plus the exact Project deployment identity used for one role in one frame. |
| Execution composition | Worker | A run that uses the pinned advisor overlay as its root executable while carrying the pinned Project deployment as mandatory authority metadata. |

The agent deployment is never inferred from a role key. The advisor overlay is
never inferred from the latest registry version. Both identities are persisted
with the frame and reused on retry or callback replay.

## Advisor overlay contract

### Built-in overlay catalog

Every role in `EXECUTIVE_ROLE_CATALOG` has one published built-in overlay.
The catalog contains, for each role:

- `roleKey`
- `overlaySpecId`
- `overlaySpecVersion`
- `overlayDefinitionHash`
- `requiredProfileKey`
- exact skill identities
- `advisoryOnly: true`

The existing executive AgentSpecs become overlays. The five missing overlays
are added: `chief_of_staff`, `cfo`, `cmo`, `coo`, and `cco`. CEO remains a
valid overlay only when it is seeded and published; declared-only is not a
valid framed state.

An overlay's `capability_refs` must be a subset of its required profile's
deployed AgentSpec `capability_refs`. An overlay cannot add a write capability,
model-input capability, connector grant, or higher autonomy level. All overlays
use L1 advisory autonomy.

### Frame record

Replace the ambiguous `SelectedRolePin` shape with:

```ts
interface ProjectDeploymentPin {
  projectAgentDeploymentId: string;
  profileKey: string;
  specId: string;
  specVersion: string;
  specHash: string;
}

interface AdvisorOverlayPin {
  roleKey: string;
  overlaySpecId: string;
  overlaySpecVersion: string;
  overlaySpecHash: string;
  skillPins: readonly PinnedSkillIdentity[];
}

interface SelectedAdvisorExecutionPin {
  deployment: ProjectDeploymentPin;
  overlay: AdvisorOverlayPin;
}
```

`PinnedSkillIdentity` includes id, version, and definition hash. The old
`skillpack:name@version` string is not sufficient in persisted execution
state.

### Cross-plane resolution

`services/cosa` exposes a service-authenticated, read-only endpoint that
returns an exact published overlay identity by role key. It reads only the
published built-in overlay catalog; it does not expose registry mutation.

During `frameDeliberation`, Company:

1. verifies founder authority, Workspace office, stage, and the exact Project
   deployment as it does today;
2. asks COSA Control Plane for the exact overlay identity;
3. persists both pins and emits them in the transactional outbox event.

If COSA cannot return a published overlay matching the catalog, framing fails
before a frame or outbox record is written. There is no fallback to a profile
AgentSpec, role string, or latest version.

### Worker execution

The worker resolves both pins before a model call:

1. resolve the deployment AgentSpec from registry by id, version, and hash;
2. resolve the overlay AgentSpec by id, version, and hash;
3. validate overlay scope is contained in the deployment scope;
4. use the overlay AgentSpec as the execution root;
5. put both identities, project id, deployment id, deliberation id, and frame
   version in the `RunRequest` metadata and durable run record;
6. use the common COSA run preparation path for compliance delegation and
   model routing before calling the kernel;
7. reject callback data whose frame, role, overlay pin, or deployment pin does
   not equal the persisted frame.

The generic `packages/agent` runner remains unaware of Company APIs. Company
resolution and model routing stay in `apps/cosa`.

## Workflow AGENT-step contract

An AGENT step resolves a full AgentSpec from `SpecRegistryRepository` using
the live authority's exact identity, verifies it against the manifest pin, and
calls:

```python
await kernel.run(request, resolved_spec)
```

The step cannot synthesize a spec from `PinnedSpecIdentity`, cannot use a
floating registry version, and cannot call a kernel with a nonconforming
one-argument test double. The workflow engine receives an explicit spec
resolver dependency at composition time.

## Truthful Hub behavior

### Specialist direct chat

`AgentDirectChatSheet` accepts the active Project id and profile key. It uses
`AgentChatService` to create or reuse a Project-scoped conversation and posts
a message with explicit `project_id` and data-access declaration. It displays
queued/running/failure/completion from the real run stream. It never creates a
local generated answer as a fallback.

If the active Project is missing, authorization fails, or a profile is not
eligible, the sheet shows a recoverable error and sends no message.

### Convert response to task

The action calls `TaskService.createTypedTask` with active `projectId`, title,
and source metadata. Success is shown only after Company returns a task id.
Failure leaves the response intact and shows the API error. The user can retry
without duplicating a task by using an idempotency key derived from the
conversation message and Project.

### Test run

The existing test-run drawer is not a production execution surface. Until a
separate sandbox-run API has a durable policy, audit trail, and result model,
the button is removed from Hub. It must not show an execution-success toast.

### Navigation

Workflow, approval, agent, vault, and other non-live routes remain labelled
unavailable and are excluded from actionable Hub navigation. When an actual
workflow surface is implemented, it must list bindings, start a real run,
show the durable run state, and show approvals from their canonical API.

## Skillpack closure

Built-in skillpacks are parsed and validated as a complete batch before any
published status becomes visible. A batch uses staging records or one database
transaction and exposes records only after every manifest, hash, capability,
and dependency check passes.

Validation rejects:

- an AgentSpec pin whose skill is absent;
- a skill tool absent from the capability registry;
- a skill tool outside its owning AgentSpec's `capability_refs`;
- an advisor overlay whose capabilities exceed its base profile;
- any role whose declared overlay is absent from the seeded registry.

## Acceptance criteria

1. A frame persists exact deployment and overlay pins for every selected role.
2. A worker run records both pin identities and cannot execute after either
   deployment or overlay hash drift.
3. All fifteen roles have a seeded, published overlay or are explicitly
   unavailable and cannot be framed. There is no silently missing role spec.
4. A governed workflow AGENT step calls a real-conforming kernel with a full
   resolved AgentSpec and survives an approval/restart path.
5. Hub specialist chat creates a Project-scoped conversation and durable run;
   no local response is presented as an agent result.
6. Hub task conversion creates a Company task with the active Project id or
   visibly fails without claiming success.
7. No actionable navigation or CTA leads to a planned route or fake success.
8. A disposable PostgreSQL process E2E proves the primary paths and their
   tenant, Project, pin-drift, retry, and callback-replay negative cases.

## Verification strategy

| Layer | Evidence |
|---|---|
| Contract | Generated overlay catalog matches all Company roles, Python AgentSpecs, skillpack identities, and capability closure. |
| Unit | Exact pin resolver, scope-subset validator, AGENT-step kernel invocation, and UI controllers' success/failure state. |
| Service integration | Company frame stores both pins and rejects missing/incorrect overlay identity. |
| Process E2E | Company outbox, COSA worker, registry, model fake, callback, PostgreSQL persistence, and restart/resume use the same pins. |
| Flutter integration | API-backed direct chat and task creation issue the required Project-scoped requests; unavailable actions do not claim completion. |

## Non-negotiable constraints

- `workspace_id` and `project_id` are required for every business run.
- Company remains the sole authority for Project deployment and business writes.
- No floating `latest` asset resolution at run time.
- A retry, restart, duplicate outbox event, and callback replay use the same
  pins and are idempotent.
- Overlay execution is advisory L1 and cannot increase profile authority.
- UI copy reports only state returned by a real API or local explicit
  unavailable state.
