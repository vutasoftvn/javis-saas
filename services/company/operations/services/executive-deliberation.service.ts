import { randomUUID } from "node:crypto";
import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import {
  EXECUTIVE_DELIBERATION_FRAMED_V1,
  EXECUTIVE_ANALYSIS_COMPLETED_V1,
  EXECUTIVE_ANALYSIS_FAILED_V1,
} from "../../shared/events/event-types";
import {
  EXECUTIVE_ROLE_CATALOG,
  ExecutiveRoleKey,
  isExecutiveRoleKey,
} from "../../shared/contracts/executive-advisor-roles.generated";
import { requireExecutiveBoardFounderAuthority } from "./executive-role-activation.service";

const {
  projects,
  projectAgentAssignments,
  projectExecutiveRoleActivations,
  projectExecutiveDeliberations,
  projectExecutiveDeliberationFrames,
  projectExecutiveDeliberationDecisions,
  projectExecutiveDeliberationAnalyses,
} = schema;

export type DeliberationState =
  | "DRAFT"
  | "FRAMED"
  | "ANALYSIS_QUEUED"
  | "ANALYZING"
  | "SYNTHESIS_QUEUED"
  | "CRITIC_REVIEW"
  | "AWAITING_FOUNDER"
  | "DECIDED"
  | "CANCELLED"
  | "EXPIRED"
  | "FAILED_REQUIRES_ATTENTION";

export type ExecutiveDecisionType =
  | "APPROVE"
  | "MODIFY"
  | "REJECT"
  | "EXPIRE"
  | "CANCEL";

export interface SelectedRolePin {
  roleKey: string;
  assignmentId: string;
  specId: string;
  specVersion: string;
  specHash: string;
  skillPins: readonly string[];
}

export interface EvidenceSourceInput {
  sourceRef: string;
  sourceHash: string;
  classification: string;
}

export interface CreateDraftInput {
  title: string;
}

export interface FrameDeliberationInput {
  expectedVersion?: number;
  question: string;
  deliberationType?: string;
  deadline?: string;
  roleKeys: string[];
  evidenceSources?: EvidenceSourceInput[];
  criticRequired?: boolean;
  redactedContextRef?: string;
  idempotencyKey?: string;
}

export interface CancelDeliberationInput {
  expectedVersion?: number;
  reason?: string;
}

export interface AppendDecisionInput {
  decisionType: ExecutiveDecisionType;
  expectedVersion?: number;
  notes?: string;
  modifications?: Record<string, any>;
}

export interface DeliberationDetails {
  id: string;
  workspaceId: string;
  projectId: string;
  title: string;
  state: DeliberationState;
  activeFrameVersion: number;
  version: number;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  activeFrame?: {
    frameVersion: number;
    question: string;
    deliberationType: string;
    deadline?: string;
    decisionOwnerId: string;
    selectedRoles: SelectedRolePin[];
    evidenceSources: EvidenceSourceInput[];
    criticRequired: boolean;
    redactedContextRef?: string;
    framedAt: string;
  };
  decision?: {
    decisionType: ExecutiveDecisionType;
    decisionVersion: number;
    actorId: string;
    notes?: string;
    modifications?: Record<string, any>;
    decidedAt: string;
  };
  analyses?: Array<{
    id: string;
    frameVersion: number;
    roleKey: string;
    runId: string;
    status: string;
    descriptor: Record<string, any>;
    createdAt: string;
  }>;
}

/**
 * Tạo bản nháp Deliberation cho Project.
 */
export async function createDraftDeliberation(
  ctx: TenantContext,
  projectId: string,
  input: CreateDraftInput
): Promise<{ id: string; title: string; state: DeliberationState; version: number }> {
  await requireExecutiveBoardFounderAuthority(ctx, projectId);

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);
  const actorId = BigInt(ctx.userId);
  const id = generateSnowflake();

  await db.insert(projectExecutiveDeliberations).values({
    id,
    workspaceId: wsId,
    projectId: projId,
    title: input.title.trim(),
    state: "DRAFT",
    activeFrameVersion: 0,
    version: 1,
    createdBy: actorId,
  });

  return {
    id: id.toString(),
    title: input.title.trim(),
    state: "DRAFT",
    version: 1,
  };
}

/**
 * Frame Deliberation: xác nhận câu hỏi, phạm vi role, snapshot spec/skill/policy và outbox dispatch.
 */
export async function frameDeliberation(
  ctx: TenantContext,
  projectId: string,
  deliberationId: string,
  input: FrameDeliberationInput
): Promise<{ id: string; state: DeliberationState; activeFrameVersion: number; version: number }> {
  await requireExecutiveBoardFounderAuthority(ctx, projectId);

  if (!input.roleKeys || input.roleKeys.length === 0) {
    throw APIError.invalidArgument("At least one role must be selected");
  }

  const uniqueRoleKeys = new Set(input.roleKeys);
  if (uniqueRoleKeys.size !== input.roleKeys.length) {
    throw APIError.invalidArgument("Duplicate role keys are not permitted");
  }

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);
  const delibId = BigInt(deliberationId);
  const actorId = BigInt(ctx.userId);

  // Validate evidence sources for cross-tenant / cross-project isolation
  if (input.evidenceSources) {
    for (const src of input.evidenceSources) {
      if (src.sourceRef && src.sourceRef.startsWith("project://")) {
        const parts = src.sourceRef.replace("project://", "").split("/");
        const refProjId = parts[0];
        if (refProjId && refProjId !== projectId) {
          throw APIError.permissionDenied(
            `CROSS_PROJECT_EVIDENCE_FORBIDDEN: Evidence reference '${src.sourceRef}' belongs to another project`
          );
        }
      }
      if (src.sourceRef && src.sourceRef.startsWith("workspace://")) {
        const parts = src.sourceRef.replace("workspace://", "").split("/");
        const refWsId = parts[0];
        if (refWsId && refWsId !== ctx.workspaceId) {
          throw APIError.permissionDenied(
            `CROSS_WORKSPACE_EVIDENCE_FORBIDDEN: Evidence reference '${src.sourceRef}' belongs to another workspace`
          );
        }
      }
    }
  }

  // 1. Verify every role is ACTIVE and fetch underlying pins
  const rolePins: SelectedRolePin[] = [];

  for (const roleKey of input.roleKeys) {
    if (!isExecutiveRoleKey(roleKey)) {
      throw APIError.invalidArgument(`Unknown role key '${roleKey}'`);
    }

    const roleDef = EXECUTIVE_ROLE_CATALOG[roleKey];
    if (roleDef.runtimeReadiness !== "READY") {
      throw APIError.failedPrecondition(
        `EXECUTIVE_ROLE_NOT_AVAILABLE: Role '${roleKey}' has readiness '${roleDef.runtimeReadiness}'`
      );
    }

    // Check activation in project
    const [act] = await db
      .select()
      .from(projectExecutiveRoleActivations)
      .where(
        and(
          eq(projectExecutiveRoleActivations.workspaceId, wsId),
          eq(projectExecutiveRoleActivations.projectId, projId),
          eq(projectExecutiveRoleActivations.roleKey, roleKey)
        )
      )
      .limit(1);

    if (!act || act.state !== "ACTIVE") {
      throw APIError.failedPrecondition(
        `EXECUTIVE_ROLE_NOT_ACTIVE: Role '${roleKey}' is not ACTIVE in project`
      );
    }

    // Check underlying assignment
    const [assignment] = await db
      .select({
        id: projectAgentAssignments.id,
        state: projectAgentAssignments.state,
        specId: projectAgentAssignments.specId,
        specVersion: projectAgentAssignments.specVersion,
        specHash: projectAgentAssignments.specHash,
      })
      .from(projectAgentAssignments)
      .where(
        and(
          eq(projectAgentAssignments.workspaceId, wsId),
          eq(projectAgentAssignments.projectId, projId),
          eq(projectAgentAssignments.profileKey, roleDef.requiredProfileKey)
        )
      )
      .limit(1);

    if (!assignment || assignment.state !== "ACTIVE" || !assignment.specHash) {
      throw APIError.failedPrecondition(
        `EXECUTIVE_ROLE_NOT_AVAILABLE: Required profile '${roleDef.requiredProfileKey}' assignment is not active`
      );
    }

    rolePins.push({
      roleKey,
      assignmentId: assignment.id.toString(),
      specId: assignment.specId ?? roleDef.requiredAgentSpec,
      specVersion: assignment.specVersion ?? "1.0.0",
      specHash: assignment.specHash,
      skillPins: roleDef.requiredSkillPins,
    });
  }

  // 2. Transaction: advance state, insert frame, and atomically write outbox
  return await db.transaction(async (tx) => {
    const [delib] = await tx
      .select()
      .from(projectExecutiveDeliberations)
      .where(
        and(
          eq(projectExecutiveDeliberations.id, delibId),
          eq(projectExecutiveDeliberations.workspaceId, wsId),
          eq(projectExecutiveDeliberations.projectId, projId)
        )
      )
      .limit(1);

    if (!delib) {
      throw APIError.notFound("Deliberation not found");
    }

    if (!["DRAFT", "FRAMED"].includes(delib.state)) {
      throw APIError.failedPrecondition(
        `INVALID_STATE: Cannot frame deliberation in state '${delib.state}'`
      );
    }

    if (
      input.expectedVersion !== undefined &&
      delib.version !== input.expectedVersion
    ) {
      throw APIError.aborted(
        `CAS_CONFLICT: Stale deliberation version (expected ${input.expectedVersion}, got ${delib.version})`
      );
    }

    const nextFrameVersion = delib.activeFrameVersion + 1;
    const nextVersion = delib.version + 1;
    const frameId = generateSnowflake();

    await tx.insert(projectExecutiveDeliberationFrames).values({
      id: frameId,
      workspaceId: wsId,
      projectId: projId,
      deliberationId: delibId,
      frameVersion: nextFrameVersion,
      question: input.question.trim(),
      deliberationType: input.deliberationType ?? "STRATEGY",
      deadline: input.deadline ? new Date(input.deadline) : null,
      decisionOwnerId: actorId,
      selectedRoles: rolePins,
      evidenceSources: input.evidenceSources ?? [],
      criticRequired: input.criticRequired ?? false,
      redactedContextRef: input.redactedContextRef ?? null,
      framedBy: actorId,
    });

    await tx
      .update(projectExecutiveDeliberations)
      .set({
        state: "ANALYSIS_QUEUED",
        activeFrameVersion: nextFrameVersion,
        version: nextVersion,
        updatedAt: new Date(),
      })
      .where(eq(projectExecutiveDeliberations.id, delibId));

    // Append to outbox
    const event = makeBusinessEvent({
      eventType: EXECUTIVE_DELIBERATION_FRAMED_V1,
      workspaceId: ctx.workspaceId,
      projectId,
      aggregateType: "deliberation",
      aggregateId: deliberationId,
      correlationId: input.idempotencyKey ?? randomUUID(),
      actor: { kind: "user", id: ctx.userId },
      classification: "internal",
      payload: {
        deliberationId,
        frameVersion: nextFrameVersion,
        question: input.question.trim(),
        deliberationType: input.deliberationType ?? "STRATEGY",
        selectedRoles: rolePins,
        evidenceSources: input.evidenceSources ?? [],
        criticRequired: input.criticRequired ?? false,
        redactedContextRef: input.redactedContextRef ?? null,
      },
    });

    await appendOutboxEvent(tx, event);

    return {
      id: deliberationId,
      state: "ANALYSIS_QUEUED" as DeliberationState,
      activeFrameVersion: nextFrameVersion,
      version: nextVersion,
    };
  });
}

/**
 * Founder huỷ bỏ Deliberation.
 */
export async function cancelDeliberation(
  ctx: TenantContext,
  projectId: string,
  deliberationId: string,
  input: CancelDeliberationInput
): Promise<{ id: string; state: DeliberationState; version: number }> {
  await requireExecutiveBoardFounderAuthority(ctx, projectId);

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);
  const delibId = BigInt(deliberationId);

  return await db.transaction(async (tx) => {
    const [delib] = await tx
      .select()
      .from(projectExecutiveDeliberations)
      .where(
        and(
          eq(projectExecutiveDeliberations.id, delibId),
          eq(projectExecutiveDeliberations.workspaceId, wsId),
          eq(projectExecutiveDeliberations.projectId, projId)
        )
      )
      .limit(1);

    if (!delib) {
      throw APIError.notFound("Deliberation not found");
    }

    if (["DECIDED", "CANCELLED", "EXPIRED"].includes(delib.state)) {
      throw APIError.failedPrecondition(
        `INVALID_STATE: Deliberation is already in terminal state '${delib.state}'`
      );
    }

    if (
      input.expectedVersion !== undefined &&
      delib.version !== input.expectedVersion
    ) {
      throw APIError.aborted(
        `CAS_CONFLICT: Stale deliberation version (expected ${input.expectedVersion}, got ${delib.version})`
      );
    }

    const nextVersion = delib.version + 1;
    await tx
      .update(projectExecutiveDeliberations)
      .set({
        state: "CANCELLED",
        version: nextVersion,
        updatedAt: new Date(),
      })
      .where(eq(projectExecutiveDeliberations.id, delibId));

    return {
      id: deliberationId,
      state: "CANCELLED" as DeliberationState,
      version: nextVersion,
    };
  });
}

/**
 * Founder append quyết định cuối cùng (APPROVE, MODIFY, REJECT, EXPIRE, CANCEL).
 * Append-only, cấm trùng lặp.
 */
export async function appendFounderDecision(
  ctx: TenantContext,
  projectId: string,
  deliberationId: string,
  input: AppendDecisionInput
): Promise<{ id: string; deliberationId: string; decisionType: ExecutiveDecisionType; version: number }> {
  await requireExecutiveBoardFounderAuthority(ctx, projectId);

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);
  const delibId = BigInt(deliberationId);
  const actorId = BigInt(ctx.userId);

  return await db.transaction(async (tx) => {
    const [delib] = await tx
      .select()
      .from(projectExecutiveDeliberations)
      .where(
        and(
          eq(projectExecutiveDeliberations.id, delibId),
          eq(projectExecutiveDeliberations.workspaceId, wsId),
          eq(projectExecutiveDeliberations.projectId, projId)
        )
      )
      .limit(1);

    if (!delib) {
      throw APIError.notFound("Deliberation not found");
    }

    if (delib.state === "CANCELLED") {
      throw APIError.failedPrecondition(
        "CANNOT_DECIDE_CANCELLED: Deliberation was cancelled"
      );
    }

    if (delib.state === "DECIDED") {
      throw APIError.aborted(
        "EXECUTIVE_DECISION_ALREADY_RECORDED: Deliberation already has a final decision"
      );
    }

    if (
      input.expectedVersion !== undefined &&
      delib.version !== input.expectedVersion
    ) {
      throw APIError.aborted(
        `CAS_CONFLICT: Stale deliberation version (expected ${input.expectedVersion}, got ${delib.version})`
      );
    }

    // Ensure no prior decision exists
    const [existingDecision] = await tx
      .select({ id: projectExecutiveDeliberationDecisions.id })
      .from(projectExecutiveDeliberationDecisions)
      .where(eq(projectExecutiveDeliberationDecisions.deliberationId, delibId))
      .limit(1);

    if (existingDecision) {
      throw APIError.aborted(
        "EXECUTIVE_DECISION_ALREADY_RECORDED: Decision record already exists"
      );
    }

    const decisionId = generateSnowflake();
    await tx.insert(projectExecutiveDeliberationDecisions).values({
      id: decisionId,
      workspaceId: wsId,
      projectId: projId,
      deliberationId: delibId,
      decisionType: input.decisionType,
      decisionVersion: 1,
      actorId,
      notes: input.notes ?? null,
      modifications: input.modifications ?? {},
    });

    const nextVersion = delib.version + 1;
    await tx
      .update(projectExecutiveDeliberations)
      .set({
        state: "DECIDED",
        version: nextVersion,
        updatedAt: new Date(),
      })
      .where(eq(projectExecutiveDeliberations.id, delibId));

    return {
      id: decisionId.toString(),
      deliberationId,
      decisionType: input.decisionType,
      version: nextVersion,
    };
  });
}

/**
 * Lấy chi tiết Deliberation cùng active frame và decision (nếu có).
 */
export async function getDeliberation(
  ctx: TenantContext,
  projectId: string,
  deliberationId: string
): Promise<DeliberationDetails> {
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);
  const delibId = BigInt(deliberationId);

  const [delib] = await db
    .select()
    .from(projectExecutiveDeliberations)
    .where(
      and(
        eq(projectExecutiveDeliberations.id, delibId),
        eq(projectExecutiveDeliberations.workspaceId, wsId),
        eq(projectExecutiveDeliberations.projectId, projId)
      )
    )
    .limit(1);

  if (!delib) {
    throw APIError.notFound("Deliberation not found");
  }

  let activeFrame: DeliberationDetails["activeFrame"];
  if (delib.activeFrameVersion > 0) {
    const [frame] = await db
      .select()
      .from(projectExecutiveDeliberationFrames)
      .where(
        and(
          eq(projectExecutiveDeliberationFrames.deliberationId, delibId),
          eq(projectExecutiveDeliberationFrames.frameVersion, delib.activeFrameVersion)
        )
      )
      .limit(1);

    if (frame) {
      activeFrame = {
        frameVersion: frame.frameVersion,
        question: frame.question,
        deliberationType: frame.deliberationType,
        deadline: frame.deadline?.toISOString(),
        decisionOwnerId: frame.decisionOwnerId.toString(),
        selectedRoles: frame.selectedRoles as SelectedRolePin[],
        evidenceSources: frame.evidenceSources as EvidenceSourceInput[],
        criticRequired: frame.criticRequired,
        redactedContextRef: frame.redactedContextRef ?? undefined,
        framedAt: frame.framedAt.toISOString(),
      };
    }
  }

  const [decisionRow] = await db
    .select()
    .from(projectExecutiveDeliberationDecisions)
    .where(eq(projectExecutiveDeliberationDecisions.deliberationId, delibId))
    .limit(1);

  let decision: DeliberationDetails["decision"];
  if (decisionRow) {
    decision = {
      decisionType: decisionRow.decisionType as ExecutiveDecisionType,
      decisionVersion: decisionRow.decisionVersion,
      actorId: decisionRow.actorId.toString(),
      notes: decisionRow.notes ?? undefined,
      modifications: decisionRow.modifications as Record<string, any> | undefined,
      decidedAt: decisionRow.decidedAt.toISOString(),
    };
  }

  const analysisRows = await db
    .select()
    .from(projectExecutiveDeliberationAnalyses)
    .where(
      and(
        eq(projectExecutiveDeliberationAnalyses.deliberationId, delibId),
        eq(projectExecutiveDeliberationAnalyses.frameVersion, delib.activeFrameVersion)
      )
    );

  const analyses = analysisRows.map((r) => ({
    id: r.id.toString(),
    frameVersion: r.frameVersion,
    roleKey: r.roleKey,
    runId: r.runId,
    status: r.status,
    descriptor: (r.descriptor as Record<string, any>) ?? {},
    createdAt: r.createdAt.toISOString(),
  }));

  return {
    id: delib.id.toString(),
    workspaceId: delib.workspaceId.toString(),
    projectId: delib.projectId.toString(),
    title: delib.title,
    state: delib.state as DeliberationState,
    activeFrameVersion: delib.activeFrameVersion,
    version: delib.version,
    createdBy: delib.createdBy.toString(),
    createdAt: delib.createdAt.toISOString(),
    updatedAt: delib.updatedAt.toISOString(),
    activeFrame,
    decision,
    analyses,
  };
}

export interface ExecutiveAnalysisCallbackInput {
  kind: "executive.analysis.completed.v1" | "executive.analysis.failed.v1" | string;
  deliberation_id: string;
  frame_version: number;
  role_key: string;
  descriptor?: Record<string, any>;
  error_detail?: string;
}

export interface AnalysisRecordResult {
  id: string;
  deliberationId: string;
  roleKey: string;
  status: string;
  state: DeliberationState;
}

/**
 * Ghi nhận callback từ Agent Platform cho 1 role analysis (Idempotent, append-only, state transition).
 */
export async function recordExecutiveAnalysisCallback(
  workspaceId: string,
  projectId: string,
  deliberationId: string,
  callback: ExecutiveAnalysisCallbackInput
): Promise<AnalysisRecordResult> {
  const wsId = BigInt(workspaceId);
  const projId = BigInt(projectId);
  const delibId = BigInt(deliberationId);

  return await db.transaction(async (tx) => {
    const [delib] = await tx
      .select()
      .from(projectExecutiveDeliberations)
      .where(
        and(
          eq(projectExecutiveDeliberations.id, delibId),
          eq(projectExecutiveDeliberations.workspaceId, wsId),
          eq(projectExecutiveDeliberations.projectId, projId)
        )
      )
      .limit(1);

    if (!delib) {
      throw APIError.notFound("Deliberation not found or project mismatch");
    }

    // Terminal states check
    if (["CANCELLED", "EXPIRED", "DECIDED"].includes(delib.state)) {
      throw APIError.failedPrecondition(
        `Deliberation is in terminal state '${delib.state}', ignoring callback`
      );
    }

    if (delib.activeFrameVersion !== callback.frame_version) {
      throw APIError.failedPrecondition(
        `Frame version mismatch: active is ${delib.activeFrameVersion}, callback is ${callback.frame_version}`
      );
    }

    // Check if role is in active frame
    const [frame] = await tx
      .select()
      .from(projectExecutiveDeliberationFrames)
      .where(
        and(
          eq(projectExecutiveDeliberationFrames.deliberationId, delibId),
          eq(projectExecutiveDeliberationFrames.frameVersion, delib.activeFrameVersion)
        )
      )
      .limit(1);

    if (!frame) {
      throw APIError.notFound("Deliberation frame not found");
    }

    const selectedRoles = (frame.selectedRoles as SelectedRolePin[]) || [];
    const isRolePinned = selectedRoles.some((r) => r.roleKey === callback.role_key);
    if (!isRolePinned) {
      throw APIError.failedPrecondition(
        `Role '${callback.role_key}' was not selected in frame version ${callback.frame_version}`
      );
    }

    // Check idempotency: already exists?
    const [existing] = await tx
      .select()
      .from(projectExecutiveDeliberationAnalyses)
      .where(
        and(
          eq(projectExecutiveDeliberationAnalyses.deliberationId, delibId),
          eq(projectExecutiveDeliberationAnalyses.frameVersion, callback.frame_version),
          eq(projectExecutiveDeliberationAnalyses.roleKey, callback.role_key)
        )
      )
      .limit(1);

    if (existing) {
      return {
        id: existing.id.toString(),
        deliberationId,
        roleKey: existing.roleKey,
        status: existing.status,
        state: delib.state as DeliberationState,
      };
    }

    // Verify role is still active in project
    const [roleAct] = await tx
      .select({ state: projectExecutiveRoleActivations.state })
      .from(projectExecutiveRoleActivations)
      .where(
        and(
          eq(projectExecutiveRoleActivations.workspaceId, wsId),
          eq(projectExecutiveRoleActivations.projectId, projId),
          eq(projectExecutiveRoleActivations.roleKey, callback.role_key)
        )
      )
      .limit(1);

    if (!roleAct || roleAct.state !== "ACTIVE") {
      throw APIError.failedPrecondition(
        `Role '${callback.role_key}' has been disabled or revoked`
      );
    }

    // Insert analysis record
    const analysisId = generateSnowflake();
    const isSuccess = callback.kind === "executive.analysis.completed.v1";
    const status = isSuccess ? "COMPLETED" : "FAILED";
    const runId =
      callback.descriptor?.run_id ?? `run_${callback.role_key}_${deliberationId}`;
    const descriptor = callback.descriptor ?? { error: callback.error_detail };

    await tx.insert(projectExecutiveDeliberationAnalyses).values({
      id: analysisId,
      workspaceId: wsId,
      projectId: projId,
      deliberationId: delibId,
      frameVersion: callback.frame_version,
      roleKey: callback.role_key,
      runId,
      status,
      descriptor,
    });

    // Outbox event (compact summary, no raw prompt or raw CoT)
    const eventType = isSuccess
      ? EXECUTIVE_ANALYSIS_COMPLETED_V1
      : EXECUTIVE_ANALYSIS_FAILED_V1;

    const event = makeBusinessEvent({
      workspaceId,
      projectId,
      eventType,
      aggregateType: "deliberation",
      aggregateId: deliberationId,
      correlationId: runId,
      actor: { kind: "agent", id: `agent_exec_${callback.role_key}` },
      classification: "internal",
      payload: {
        workspaceId,
        projectId,
        deliberationId,
        frameVersion: callback.frame_version,
        roleKey: callback.role_key,
        status,
        summary: descriptor.conclusion || callback.error_detail || "",
        confidence: descriptor.confidence || "UNKNOWN",
      },
    });
    await appendOutboxEvent(tx, event);

    // Count all analyses for this frame
    const allAnalyses = await tx
      .select()
      .from(projectExecutiveDeliberationAnalyses)
      .where(
        and(
          eq(projectExecutiveDeliberationAnalyses.deliberationId, delibId),
          eq(projectExecutiveDeliberationAnalyses.frameVersion, callback.frame_version)
        )
      );

    let nextState: DeliberationState = delib.state as DeliberationState;
    if (delib.state === "ANALYSIS_QUEUED" || delib.state === "FRAMED") {
      nextState = "ANALYZING";
    }
    if (allAnalyses.length >= selectedRoles.length) {
      // All roles completed analysis!
      nextState = frame.criticRequired ? "CRITIC_REVIEW" : "AWAITING_FOUNDER";
    }

    if (nextState !== delib.state) {
      await tx
        .update(projectExecutiveDeliberations)
        .set({
          state: nextState,
          version: delib.version + 1,
          updatedAt: new Date(),
        })
        .where(eq(projectExecutiveDeliberations.id, delibId));
    }

    return {
      id: analysisId.toString(),
      deliberationId,
      roleKey: callback.role_key,
      status,
      state: nextState,
    };
  });
}

/**
 * Lấy authority context cho deliberation role analysis (worker verify).
 */
export async function getDeliberationAuthority(
  workspaceId: string,
  projectId: string,
  deliberationId: string,
  roleKey: string,
  expectedFrameVersion?: number
): Promise<{
  deliberationId: string;
  frameVersion: number;
  roleKey: string;
  state: DeliberationState;
  rolePin: SelectedRolePin;
  question: string;
  evidenceSources: EvidenceSourceInput[];
}> {
  const wsId = BigInt(workspaceId);
  const projId = BigInt(projectId);
  const delibId = BigInt(deliberationId);

  const [delib] = await db
    .select()
    .from(projectExecutiveDeliberations)
    .where(
      and(
        eq(projectExecutiveDeliberations.id, delibId),
        eq(projectExecutiveDeliberations.workspaceId, wsId),
        eq(projectExecutiveDeliberations.projectId, projId)
      )
    )
    .limit(1);

  if (!delib) {
    throw APIError.notFound("Deliberation not found");
  }

  if (["CANCELLED", "EXPIRED", "DECIDED"].includes(delib.state)) {
    throw APIError.failedPrecondition(`Deliberation is in state '${delib.state}'`);
  }

  if (expectedFrameVersion !== undefined && delib.activeFrameVersion !== expectedFrameVersion) {
    throw APIError.failedPrecondition(
      `Frame version mismatch: active is ${delib.activeFrameVersion}, expected ${expectedFrameVersion}`
    );
  }

  const [frame] = await db
    .select()
    .from(projectExecutiveDeliberationFrames)
    .where(
      and(
        eq(projectExecutiveDeliberationFrames.deliberationId, delibId),
        eq(projectExecutiveDeliberationFrames.frameVersion, delib.activeFrameVersion)
      )
    )
    .limit(1);

  if (!frame) {
    throw APIError.notFound("Frame not found");
  }

  const selectedRoles = (frame.selectedRoles as SelectedRolePin[]) || [];
  const rolePin = selectedRoles.find((r) => r.roleKey === roleKey);
  if (!rolePin) {
    throw APIError.failedPrecondition(
      `Role '${roleKey}' is not pinned in deliberation active frame`
    );
  }

  // Verify role is still active in project
  const [roleAct] = await db
    .select({ state: projectExecutiveRoleActivations.state })
    .from(projectExecutiveRoleActivations)
    .where(
      and(
        eq(projectExecutiveRoleActivations.workspaceId, wsId),
        eq(projectExecutiveRoleActivations.projectId, projId),
        eq(projectExecutiveRoleActivations.roleKey, roleKey)
      )
    )
    .limit(1);

  if (!roleAct || roleAct.state !== "ACTIVE") {
    throw APIError.failedPrecondition(
      `Role '${roleKey}' is no longer ACTIVE or has been disabled`
    );
  }

  // Verify underlying startup team assignment is still active
  if (isExecutiveRoleKey(roleKey)) {
    const roleDef = EXECUTIVE_ROLE_CATALOG[roleKey];
    if (roleDef) {
      const [assignment] = await db
        .select({ state: projectAgentAssignments.state })
        .from(projectAgentAssignments)
        .where(
          and(
            eq(projectAgentAssignments.workspaceId, wsId),
            eq(projectAgentAssignments.projectId, projId),
            eq(projectAgentAssignments.profileKey, roleDef.requiredProfileKey)
          )
        )
        .limit(1);

      if (!assignment || assignment.state !== "ACTIVE") {
        throw APIError.failedPrecondition(
          `Underlying assignment for role '${roleKey}' is no longer ACTIVE`
        );
      }
    }
  }

  return {
    deliberationId,
    frameVersion: frame.frameVersion,
    roleKey,
    state: delib.state as DeliberationState,
    rolePin,
    question: frame.question,
    evidenceSources: (frame.evidenceSources as EvidenceSourceInput[]) || [],
  };
}
