// Task 12 (plan founder-configurable-agent-skill-workflow) — read projections
// + composed commands cho Founder asset surface. File này KHÔNG được xâm phạm
// lãnh thổ Task 2/6: mọi ghi dữ liệu asset lifecycle (CREATE/CLONE/EDIT_DRAFT/
// EVALUATE/PUBLISH) vẫn đi qua founder-asset-authoring.service.ts; mọi bind/
// deploy/pause project vẫn đi qua founder-asset-deployment.service.ts. Hai
// việc mới thực sự thuộc về đây: (1) tổng hợp các bảng/sự kiện đã có thành
// view đọc cho Founder (library, project deployments, timeline), và (2) một
// command thực sự mới — startWorkflowRun — vì chưa nơi nào phát sinh event
// `operations.workflow_run.requested.v1` mà apps/cosa/events/router.py đã
// biết xử lý (Task 11, commit a367e80b).
import { APIError } from "encore.dev/api";
import { and, desc, eq, inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";
import type { TenantContext } from "../../shared/types/tenant_context";
import { mvpItem, mvpList, type MvpSuccess } from "../../shared/contracts/mvp-response";
import type { AssetKind, AssetOperation } from "./founder-asset-authoring.service";
import {
  deployAgentToProject,
  deployRoleToProject,
  bindWorkflowToProject,
  type ProjectAgentDeploymentDto,
  type ProjectRoleDeploymentDto,
  type ProjectWorkflowBindingDto,
} from "./founder-asset-deployment.service";

const {
  projects,
  founderAssetEvents,
  workspaceAgents,
  projectRoleDeployments,
  projectAgentDeployments,
  projectWorkflowBindings,
} = schema;

// Event type Task 11's apps/cosa/events/router.py đã biết dispatch thành một
// `governed_workflow_run` scheduler task (xem GOVERNED_WORKFLOW_RUN_REQUESTED_EVENT
// trong router.py) — 7 field snake_case này khớp chính xác
// _GOVERNED_WORKFLOW_ENVELOPE_FIELDS phía Python, không được đổi tên tuỳ ý.
const GOVERNED_WORKFLOW_RUN_REQUESTED_EVENT = "operations.workflow_run.requested.v1";

// Mirror của denylist trong founder-asset-authoring.service.ts (không export
// từ đó để tránh phụ thuộc chéo không cần thiết) — nhưng ở đây REDACT thay vì
// throw, vì đây là đường đọc: dữ liệu cũ có thể đã được ghi trước khi guard
// tồn tại, không được để lộ ra response dù nguồn gốc là gì.
const FORBIDDEN_METADATA_KEYS = new Set([
  "secret",
  "secrets",
  "credentials",
  "credential",
  "password",
  "token",
  "access_token",
  "private_key",
  "raw_prompt",
  "authorization",
  "cookie",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function redact(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(redact);
  }
  if (isRecord(value)) {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      out[k] = FORBIDDEN_METADATA_KEYS.has(k.toLowerCase()) ? "[redacted]" : redact(v);
    }
    return out;
  }
  return value;
}

async function validateProjectInWorkspace(workspaceId: bigint, projectId: bigint): Promise<void> {
  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projectId), eq(projects.workspaceId, workspaceId)))
    .limit(1);

  if (!project) {
    throw APIError.notFound("Project not found in workspace");
  }
}

function assertHumanFounder(ctx: TenantContext): void {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }
  if (ctx.isAiAgent) {
    throw APIError.permissionDenied("AI agent cannot start a governed workflow run");
  }
}

// ---------------------------------------------------------------------------
// GET /operations/founder-assets — thư viện asset Workspace (AGENT/SKILL/WORKFLOW)
// ---------------------------------------------------------------------------

export interface FounderAssetDeploymentCounts {
  readonly active: number;
  readonly paused: number;
  readonly retired: number;
}

export interface FounderAssetEvidenceRef {
  readonly kind: "company_db";
  readonly ref: string;
}

export interface FounderAssetLibraryItemDto {
  readonly assetId: string;
  readonly assetKind: AssetKind;
  readonly originAssetId?: string;
  readonly version?: string;
  readonly definitionHash?: string;
  readonly lifecycle: string;
  readonly lastOperation: AssetOperation;
  readonly evaluationSummary?: Record<string, unknown>;
  readonly safeReasonCode?: string;
  readonly deployments: FounderAssetDeploymentCounts;
  readonly evidenceRefs: readonly FounderAssetEvidenceRef[];
}

interface LineageAcc {
  assetId: string;
  assetKind: AssetKind;
  originAssetId?: string;
  version?: string;
  definitionHash?: string;
  lifecycle: string;
  lastOperation: AssetOperation;
  evaluationSummary?: Record<string, unknown>;
  safeReasonCode?: string;
  evidenceRefs: FounderAssetEvidenceRef[];
}

export async function listFounderAssetLibrary(
  ctx: TenantContext
): Promise<MvpSuccess<readonly FounderAssetLibraryItemDto[]>> {
  const wsId = BigInt(ctx.workspaceId);

  const events = await db
    .select()
    .from(founderAssetEvents)
    .where(
      and(
        eq(founderAssetEvents.workspaceId, wsId),
        inArray(founderAssetEvents.targetKind, ["AGENT", "SKILL", "WORKFLOW"])
      )
    )
    .orderBy(founderAssetEvents.occurredAt);

  const lineageByKey = new Map<string, LineageAcc>();

  for (const event of events) {
    const targetRef = isRecord(event.targetRef) ? event.targetRef : {};
    const metadata = isRecord(event.metadata) ? event.metadata : {};
    const updatedAssetRef = isRecord(metadata.updatedAssetRef) ? metadata.updatedAssetRef : undefined;

    const resolvedAssetId =
      (updatedAssetRef?.assetId as string | undefined) ?? (targetRef.assetId as string | undefined);
    if (!resolvedAssetId) {
      // Sự kiện không mang assetId (vd. dữ liệu ROLE cũ trộn chung bảng) —
      // không thuộc thư viện AGENT/SKILL/WORKFLOW, bỏ qua.
      continue;
    }

    const key = `${event.targetKind}:${resolvedAssetId}`;
    const existing = lineageByKey.get(key);
    const sourceAssetId = targetRef.assetId as string | undefined;
    const originAssetId =
      existing?.originAssetId ??
      (event.command === "CLONE" && sourceAssetId && sourceAssetId !== resolvedAssetId
        ? sourceAssetId
        : undefined);

    const evaluationSummary = isRecord(metadata.evaluationSummary)
      ? (redact(metadata.evaluationSummary) as Record<string, unknown>)
      : existing?.evaluationSummary;

    lineageByKey.set(key, {
      assetId: resolvedAssetId,
      assetKind: event.targetKind as AssetKind,
      originAssetId,
      version:
        (updatedAssetRef?.version as string | undefined) ??
        (targetRef.version as string | undefined) ??
        existing?.version,
      definitionHash:
        event.afterHash ??
        (updatedAssetRef?.definitionHash as string | undefined) ??
        event.beforeHash ??
        existing?.definitionHash,
      lifecycle: typeof metadata.status === "string" ? metadata.status : existing?.lifecycle ?? "PENDING",
      lastOperation: event.command as AssetOperation,
      evaluationSummary,
      safeReasonCode:
        typeof metadata.safeReasonCode === "string" ? metadata.safeReasonCode : existing?.safeReasonCode,
      evidenceRefs: [
        ...(existing?.evidenceRefs ?? []),
        { kind: "company_db", ref: `founder_asset_events:${event.id.toString()}` },
      ],
    });
  }

  const agentDeploymentRows = await db
    .select({
      agentAssetId: workspaceAgents.agentAssetId,
      state: projectAgentDeployments.state,
    })
    .from(projectAgentDeployments)
    .innerJoin(
      workspaceAgents,
      and(eq(workspaceAgents.id, projectAgentDeployments.workspaceAgentId), eq(workspaceAgents.workspaceId, wsId))
    )
    .where(eq(projectAgentDeployments.workspaceId, wsId));

  const workflowBindingRows = await db
    .select({ workflowAssetId: projectWorkflowBindings.workflowAssetId, state: projectWorkflowBindings.state })
    .from(projectWorkflowBindings)
    .where(eq(projectWorkflowBindings.workspaceId, wsId));

  function countDeployments(kind: AssetKind, assetId: string): FounderAssetDeploymentCounts {
    const rows =
      kind === "AGENT"
        ? agentDeploymentRows.filter((r) => r.agentAssetId === assetId)
        : kind === "WORKFLOW"
        ? workflowBindingRows.filter((r) => r.workflowAssetId === assetId)
        : [];
    return {
      active: rows.filter((r) => r.state === "ACTIVE").length,
      paused: rows.filter((r) => r.state === "PAUSED").length,
      retired: rows.filter((r) => r.state === "RETIRED").length,
    };
  }

  const items: FounderAssetLibraryItemDto[] = Array.from(lineageByKey.values()).map((acc) => ({
    ...acc,
    deployments: countDeployments(acc.assetKind, acc.assetId),
  }));

  return mvpList(items, [{ kind: "company_db", ref: "operations.founder_asset_events" }]);
}

// ---------------------------------------------------------------------------
// GET /operations/projects/:projectId/founder-deployments
// ---------------------------------------------------------------------------

export interface ProjectFounderDeploymentsView {
  readonly roles: readonly ProjectRoleDeploymentDto[];
  readonly agents: readonly ProjectAgentDeploymentDto[];
  readonly workflows: readonly ProjectWorkflowBindingDto[];
}

export async function getProjectFounderDeployments(
  ctx: TenantContext,
  projectId: string
): Promise<MvpSuccess<ProjectFounderDeploymentsView>> {
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);
  await validateProjectInWorkspace(wsId, projId);

  const [roleRows, agentRows, workflowRows] = await Promise.all([
    db
      .select()
      .from(projectRoleDeployments)
      .where(and(eq(projectRoleDeployments.workspaceId, wsId), eq(projectRoleDeployments.projectId, projId))),
    db
      .select()
      .from(projectAgentDeployments)
      .where(and(eq(projectAgentDeployments.workspaceId, wsId), eq(projectAgentDeployments.projectId, projId))),
    db
      .select()
      .from(projectWorkflowBindings)
      .where(and(eq(projectWorkflowBindings.workspaceId, wsId), eq(projectWorkflowBindings.projectId, projId))),
  ]);

  const roles: ProjectRoleDeploymentDto[] = roleRows.map((r) => ({
    id: r.id.toString(),
    workspaceId: r.workspaceId.toString(),
    projectId: r.projectId.toString(),
    roleId: r.roleId.toString(),
    state: r.state,
    policyOverride: r.policyOverride as Record<string, any>,
    budgetLimit: r.budgetLimit as Record<string, any> | null,
    version: r.version,
  }));

  const agents: ProjectAgentDeploymentDto[] = agentRows.map((r) => ({
    id: r.id.toString(),
    workspaceId: r.workspaceId.toString(),
    projectId: r.projectId.toString(),
    workspaceAgentId: r.workspaceAgentId.toString(),
    projectRoleDeploymentId: r.projectRoleDeploymentId ? r.projectRoleDeploymentId.toString() : null,
    state: r.state,
    capabilityOverrides: r.capabilityOverrides as any[],
    version: r.version,
  }));

  const workflows: ProjectWorkflowBindingDto[] = workflowRows.map((r) => ({
    id: r.id.toString(),
    workspaceId: r.workspaceId.toString(),
    projectId: r.projectId.toString(),
    workflowAssetId: r.workflowAssetId,
    workflowAssetVersion: r.workflowAssetVersion,
    workflowDefinitionHash: r.workflowDefinitionHash,
    state: r.state,
    executionPolicy: r.executionPolicy as Record<string, any>,
    version: r.version,
  }));

  return mvpItem(
    { roles, agents, workflows },
    [
      { kind: "company_db", ref: `operations.project_role_deployments:${projectId}` },
      { kind: "company_db", ref: `operations.project_agent_deployments:${projectId}` },
      { kind: "company_db", ref: `operations.project_workflow_bindings:${projectId}` },
    ]
  );
}

// ---------------------------------------------------------------------------
// POST /operations/projects/:projectId/founder-deployments — dispatch theo kind
// tới đúng command Task 2 đã có sẵn (không ghi DB trực tiếp ở đây).
// ---------------------------------------------------------------------------

export interface DeployFounderAssetToProjectInput {
  kind: "ROLE" | "AGENT" | "WORKFLOW";
  roleId?: string;
  workspaceAgentId?: string;
  projectRoleDeploymentId?: string;
  capabilityOverrides?: any[];
  policyOverride?: Record<string, any>;
  budgetLimit?: Record<string, any>;
  workflowAssetId?: string;
  workflowAssetVersion?: string;
  workflowDefinitionHash?: string;
  executionPolicy?: Record<string, any>;
  expectedVersion?: number;
  reason: string;
  idempotencyKey?: string;
}

export async function deployFounderAssetToProject(
  ctx: TenantContext,
  projectId: string,
  input: DeployFounderAssetToProjectInput
): Promise<ProjectRoleDeploymentDto | ProjectAgentDeploymentDto | ProjectWorkflowBindingDto> {
  switch (input.kind) {
    case "ROLE": {
      if (!input.roleId) {
        throw APIError.invalidArgument("roleId is required to deploy a role");
      }
      return deployRoleToProject(ctx, {
        projectId,
        roleId: input.roleId,
        expectedVersion: input.expectedVersion,
        policyOverride: input.policyOverride,
        budgetLimit: input.budgetLimit,
        reason: input.reason,
        idempotencyKey: input.idempotencyKey,
      });
    }
    case "AGENT": {
      if (!input.workspaceAgentId) {
        throw APIError.invalidArgument("workspaceAgentId is required to deploy an agent");
      }
      return deployAgentToProject(ctx, {
        projectId,
        workspaceAgentId: input.workspaceAgentId,
        projectRoleDeploymentId: input.projectRoleDeploymentId,
        capabilityOverrides: input.capabilityOverrides,
        expectedVersion: input.expectedVersion,
        reason: input.reason,
        idempotencyKey: input.idempotencyKey,
      });
    }
    case "WORKFLOW": {
      if (!input.workflowAssetId || !input.workflowAssetVersion || !input.workflowDefinitionHash) {
        throw APIError.invalidArgument(
          "workflowAssetId, workflowAssetVersion and workflowDefinitionHash are required to bind a workflow"
        );
      }
      return bindWorkflowToProject(ctx, {
        projectId,
        workflowAssetId: input.workflowAssetId,
        workflowAssetVersion: input.workflowAssetVersion,
        workflowDefinitionHash: input.workflowDefinitionHash,
        executionPolicy: input.executionPolicy,
        expectedVersion: input.expectedVersion,
        reason: input.reason,
        idempotencyKey: input.idempotencyKey,
      });
    }
    default:
      throw APIError.invalidArgument(`Unknown founder deployment kind: ${String((input as { kind: string }).kind)}`);
  }
}

// ---------------------------------------------------------------------------
// POST /operations/projects/:projectId/workflow-bindings/:bindingId/runs
// ---------------------------------------------------------------------------

export interface StartWorkflowRunInput {
  projectId?: string;
  bindingId?: string;
  reason: string;
  idempotencyKey: string;
}

export interface FounderWorkflowRunResult {
  readonly commandId: string;
  readonly workspaceId: string;
  readonly projectId: string;
  readonly bindingId: string;
  readonly workflowAssetId: string;
  readonly workflowAssetVersion: string;
  readonly workflowDefinitionHash: string;
  readonly status: "REQUESTED";
  readonly idempotencyKey: string;
}

export async function startWorkflowRun(
  ctx: TenantContext,
  input: StartWorkflowRunInput
): Promise<FounderWorkflowRunResult> {
  assertHumanFounder(ctx);
  if (!input.projectId) {
    throw APIError.invalidArgument("projectId is required to run a workflow");
  }
  if (!input.bindingId) {
    throw APIError.invalidArgument("bindingId is required to run a workflow");
  }

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(input.projectId);
  const bindingId = BigInt(input.bindingId);
  const actorId = BigInt(ctx.userId);

  await validateProjectInWorkspace(wsId, projId);

  const [binding] = await db
    .select()
    .from(projectWorkflowBindings)
    .where(
      and(
        eq(projectWorkflowBindings.id, bindingId),
        eq(projectWorkflowBindings.workspaceId, wsId),
        eq(projectWorkflowBindings.projectId, projId)
      )
    )
    .limit(1);

  if (!binding || binding.state !== "ACTIVE") {
    throw APIError.invalidArgument("Active project workflow binding required to start a run");
  }

  const existingRuns = await db
    .select()
    .from(founderAssetEvents)
    .where(
      and(
        eq(founderAssetEvents.workspaceId, wsId),
        eq(founderAssetEvents.projectId, projId),
        eq(founderAssetEvents.command, "RUN"),
        eq(founderAssetEvents.targetKind, "WORKFLOW")
      )
    );
  const existing = existingRuns.find(
    (row) => isRecord(row.metadata) && row.metadata.idempotencyKey === input.idempotencyKey
  );
  if (existing) {
    return {
      commandId: existing.id.toString(),
      workspaceId: ctx.workspaceId,
      projectId: input.projectId,
      bindingId: input.bindingId,
      workflowAssetId: binding.workflowAssetId,
      workflowAssetVersion: binding.workflowAssetVersion,
      workflowDefinitionHash: binding.workflowDefinitionHash,
      status: "REQUESTED",
      idempotencyKey: input.idempotencyKey,
    };
  }

  const commandId = generateSnowflake();
  const envelope = makeBusinessEvent({
    eventType: GOVERNED_WORKFLOW_RUN_REQUESTED_EVENT,
    workspaceId: ctx.workspaceId,
    projectId: input.projectId,
    aggregateType: "project_workflow_binding",
    aggregateId: input.bindingId,
    correlationId: ctx.correlationId || commandId.toString(),
    actor: { kind: "user", id: ctx.userId },
    classification: "internal",
    payload: {
      workspace_id: ctx.workspaceId,
      project_id: input.projectId,
      workflow_binding_id: input.bindingId,
      workflow_asset_id: binding.workflowAssetId,
      workflow_version: binding.workflowAssetVersion,
      workflow_definition_hash: binding.workflowDefinitionHash,
      idempotency_key: input.idempotencyKey,
    },
  });

  await db.transaction(async (tx) => {
    await tx.insert(founderAssetEvents).values({
      id: commandId,
      workspaceId: wsId,
      projectId: projId,
      actorId,
      command: "RUN",
      targetKind: "WORKFLOW",
      targetRef: { bindingId: input.bindingId, workflowAssetId: binding.workflowAssetId },
      afterHash: binding.workflowDefinitionHash,
      reason: input.reason,
      correlationId: ctx.correlationId || commandId.toString(),
      metadata: { idempotencyKey: input.idempotencyKey, status: "PENDING" },
    });

    await appendOutboxEvent(tx, envelope);
  });

  return {
    commandId: commandId.toString(),
    workspaceId: ctx.workspaceId,
    projectId: input.projectId,
    bindingId: input.bindingId,
    workflowAssetId: binding.workflowAssetId,
    workflowAssetVersion: binding.workflowAssetVersion,
    workflowDefinitionHash: binding.workflowDefinitionHash,
    status: "REQUESTED",
    idempotencyKey: input.idempotencyKey,
  };
}

// ---------------------------------------------------------------------------
// GET /operations/projects/:projectId/agent-timeline
// ---------------------------------------------------------------------------

export interface FounderTimelineEntryDto {
  readonly commandId: string;
  readonly occurredAt: string;
  readonly command: string;
  readonly targetKind: string;
  readonly targetRef: Record<string, unknown>;
  readonly status?: string;
  readonly safeReasonCode?: string;
  readonly evaluationSummary?: Record<string, unknown>;
  readonly evidenceRef: FounderAssetEvidenceRef;
}

export async function getProjectAgentTimeline(
  ctx: TenantContext,
  projectId: string
): Promise<MvpSuccess<readonly FounderTimelineEntryDto[]>> {
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);
  await validateProjectInWorkspace(wsId, projId);

  const rows = await db
    .select()
    .from(founderAssetEvents)
    .where(and(eq(founderAssetEvents.workspaceId, wsId), eq(founderAssetEvents.projectId, projId)))
    .orderBy(desc(founderAssetEvents.occurredAt))
    .limit(200);

  const items: FounderTimelineEntryDto[] = rows.map((row) => {
    const metadata = isRecord(row.metadata) ? row.metadata : {};
    return {
      commandId: row.id.toString(),
      occurredAt: row.occurredAt.toISOString(),
      command: row.command,
      targetKind: row.targetKind,
      targetRef: redact(isRecord(row.targetRef) ? row.targetRef : {}) as Record<string, unknown>,
      status: typeof metadata.status === "string" ? metadata.status : undefined,
      safeReasonCode: typeof metadata.safeReasonCode === "string" ? metadata.safeReasonCode : undefined,
      evaluationSummary: isRecord(metadata.evaluationSummary)
        ? (redact(metadata.evaluationSummary) as Record<string, unknown>)
        : undefined,
      evidenceRef: { kind: "company_db", ref: `founder_asset_events:${row.id.toString()}` },
    };
  });

  return mvpList(items, [{ kind: "company_db", ref: `operations.founder_asset_events:${projectId}` }]);
}
