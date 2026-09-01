import { APIError } from "encore.dev/api";
import { and, eq, inArray, isNull } from "drizzle-orm";
import { db } from "../../models/db";
import { projects } from "../../../shared/db/schema/operations";
import { pilotRuns, evidence } from "../../../shared/db/schema/strategy";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { assertLifecyclePrivileged } from "./lifecycle-authorization.service";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../../shared/events/envelope";
import { randomUUID } from "node:crypto";

export type PilotRunStatus = "DRAFT" | "APPROVED" | "ACTIVE" | "COMPLETED" | "CANCELLED";

export interface CreatePilotDraftParams {
  workspaceId: bigint;
  projectId: bigint;
  experimentId?: bigint;
  designPartnerEvidenceRefs: string[];
  metricContractArtifactRef: string;
  instrumentationArtifactRef: string;
  onboardingArtifactRef: string;
  supportEscalationArtifactRef?: string;
  rollbackArtifactRef: string;
  releaseOwnerMemberId: bigint;
  actorMemberId?: bigint;
}

export interface ApprovePilotParams {
  workspaceId: bigint;
  pilotId: bigint;
  approvalRef: string;
  actorMemberId?: bigint;
  actorRole?: string;
}

export interface ActivatePilotParams {
  workspaceId: bigint;
  pilotId: bigint;
  approvalRef: string;
  actorMemberId?: bigint;
  actorRole?: string;
}

export interface ClosePilotParams {
  workspaceId: bigint;
  pilotId: bigint;
  status: "COMPLETED" | "CANCELLED";
  cancellationReason?: string;
  actorMemberId?: bigint;
  actorRole?: string;
}

export async function createPilotDraft(p: CreatePilotDraftParams) {
  // 1. Verify project in workspace
  const [proj] = await db
    .select({ id: projects.id, lifecycleStage: projects.lifecycleStage })
    .from(projects)
    .where(and(eq(projects.id, p.projectId), eq(projects.workspaceId, p.workspaceId), isNull(projects.deletedAt)))
    .limit(1);

  if (!proj) {
    throw APIError.notFound("Project không tồn tại trong workspace này");
  }

  // 2. Validate required fields
  if (!p.releaseOwnerMemberId) {
    throw APIError.invalidArgument("releaseOwnerMemberId is required");
  }
  if (!p.metricContractArtifactRef || !p.metricContractArtifactRef.trim()) {
    throw APIError.invalidArgument("metricContractArtifactRef is required");
  }
  if (!p.instrumentationArtifactRef || !p.instrumentationArtifactRef.trim()) {
    throw APIError.invalidArgument("instrumentationArtifactRef is required");
  }
  if (!p.onboardingArtifactRef || !p.onboardingArtifactRef.trim()) {
    throw APIError.invalidArgument("onboardingArtifactRef is required");
  }
  if (!p.rollbackArtifactRef || !p.rollbackArtifactRef.trim()) {
    throw APIError.invalidArgument("rollbackArtifactRef is required");
  }
  if (!p.designPartnerEvidenceRefs || p.designPartnerEvidenceRefs.length === 0) {
    throw APIError.invalidArgument("designPartnerEvidenceRefs is required");
  }

  // 3. Verify design partner evidence exists and is reviewed ('approved') in workspace
  const evidenceBigIntIds = p.designPartnerEvidenceRefs.map((ref) => {
    try {
      return BigInt(ref);
    } catch {
      throw APIError.invalidArgument(`Invalid evidence ref ID: ${ref}`);
    }
  });

  const foundEvidence = await db
    .select({ id: evidence.id, status: evidence.status })
    .from(evidence)
    .where(
      and(
        eq(evidence.workspaceId, p.workspaceId),
        inArray(evidence.id, evidenceBigIntIds),
        isNull(evidence.deletedAt)
      )
    );

  if (foundEvidence.length !== evidenceBigIntIds.length) {
    throw APIError.invalidArgument("Một hoặc nhiều design partner evidence không tồn tại trong workspace này");
  }

  const unreviewed = foundEvidence.filter((e) => e.status !== "approved");
  if (unreviewed.length > 0) {
    throw APIError.failedPrecondition(
      `Evidence '${unreviewed.map((e) => e.id.toString()).join(", ")}' chưa được review/approved — yêu cầu bằng chứng đã được phê duyệt`
    );
  }

  const now = new Date();
  const id = generateSnowflake();

  const [created] = await db
    .insert(pilotRuns)
    .values({
      id,
      workspaceId: p.workspaceId,
      projectId: p.projectId,
      experimentId: p.experimentId ?? null,
      status: "DRAFT",
      designPartnerEvidenceRefs: p.designPartnerEvidenceRefs,
      metricContractArtifactRef: p.metricContractArtifactRef,
      instrumentationArtifactRef: p.instrumentationArtifactRef,
      onboardingArtifactRef: p.onboardingArtifactRef,
      supportEscalationArtifactRef: p.supportEscalationArtifactRef ?? null,
      rollbackArtifactRef: p.rollbackArtifactRef,
      releaseOwnerMemberId: p.releaseOwnerMemberId,
      version: 1,
      createdAt: now,
      updatedAt: now,
    })
    .returning();

  if (!created) {
    throw APIError.internal("Failed to create pilot draft");
  }

  return created;
}

export async function approvePilot(p: ApprovePilotParams) {
  assertLifecyclePrivileged(p.actorRole, "approve pilot");
  if (!p.approvalRef || !p.approvalRef.trim()) {
    throw APIError.invalidArgument("approvalRef is required for approving pilot");
  }

  const [pilot] = await db
    .select()
    .from(pilotRuns)
    .where(and(eq(pilotRuns.id, p.pilotId), eq(pilotRuns.workspaceId, p.workspaceId), isNull(pilotRuns.deletedAt)))
    .limit(1);

  if (!pilot) {
    throw APIError.notFound("Pilot run không tồn tại trong workspace này");
  }

  if (pilot.status !== "DRAFT") {
    throw APIError.failedPrecondition(`Only DRAFT pilot can be approved, current status is ${pilot.status}`);
  }

  const now = new Date();
  let updatedRecord: typeof pilotRuns.$inferSelect;

  await db.transaction(async (tx) => {
    const [updated] = await tx
      .update(pilotRuns)
      .set({
        status: "APPROVED",
        approvedByMemberId: p.actorMemberId ?? null,
        approvalRef: p.approvalRef,
        approvedAt: now,
        version: pilot.version + 1,
        updatedAt: now,
      })
      .where(and(eq(pilotRuns.id, p.pilotId), eq(pilotRuns.version, pilot.version)))
      .returning();

    if (!updated) {
      throw APIError.aborted("Pilot run was updated concurrently — please reload");
    }
    updatedRecord = updated;

    const event = makeBusinessEvent({
      eventType: "strategy.pilot.approved.v1",
      workspaceId: p.workspaceId.toString(),
      aggregateType: "pilot_run",
      aggregateId: p.pilotId.toString(),
      correlationId: randomUUID(),
      actor: {
        kind: p.actorMemberId ? "user" : "system",
        id: p.actorMemberId ? p.actorMemberId.toString() : "strategy.pilot",
      },
      classification: "internal",
      payload: {
        pilotId: p.pilotId.toString(),
        workspaceId: p.workspaceId.toString(),
        projectId: pilot.projectId.toString(),
        approvalRef: p.approvalRef,
        approvedAt: now.toISOString(),
      },
    });
    await appendOutboxEvent(tx, event);
  });

  return updatedRecord!;
}

export async function activatePilot(p: ActivatePilotParams) {
  assertLifecyclePrivileged(p.actorRole, "activate pilot");
  if (!p.approvalRef || !p.approvalRef.trim()) {
    throw APIError.invalidArgument("approvalRef is required for activating pilot");
  }

  const [pilot] = await db
    .select()
    .from(pilotRuns)
    .where(and(eq(pilotRuns.id, p.pilotId), eq(pilotRuns.workspaceId, p.workspaceId), isNull(pilotRuns.deletedAt)))
    .limit(1);

  if (!pilot) {
    throw APIError.notFound("Pilot run không tồn tại trong workspace này");
  }

  // Idempotency: if already ACTIVE, return directly without re-emitting events
  if (pilot.status === "ACTIVE") {
    return pilot;
  }

  if (pilot.status !== "APPROVED") {
    throw APIError.failedPrecondition(
      `Pilot must be in APPROVED status before activation (current status: ${pilot.status})`
    );
  }

  const now = new Date();
  let updatedRecord: typeof pilotRuns.$inferSelect;

  await db.transaction(async (tx) => {
    const [updated] = await tx
      .update(pilotRuns)
      .set({
        status: "ACTIVE",
        activatedByMemberId: p.actorMemberId ?? null,
        activatedAt: now,
        version: pilot.version + 1,
        updatedAt: now,
      })
      .where(and(eq(pilotRuns.id, p.pilotId), eq(pilotRuns.version, pilot.version)))
      .returning();

    if (!updated) {
      throw APIError.aborted("Pilot run was updated concurrently — please reload");
    }
    updatedRecord = updated;

    const event = makeBusinessEvent({
      eventType: "strategy.pilot.activated.v1",
      workspaceId: p.workspaceId.toString(),
      aggregateType: "pilot_run",
      aggregateId: p.pilotId.toString(),
      correlationId: randomUUID(),
      actor: {
        kind: p.actorMemberId ? "user" : "system",
        id: p.actorMemberId ? p.actorMemberId.toString() : "strategy.pilot",
      },
      classification: "internal",
      payload: {
        pilotId: p.pilotId.toString(),
        workspaceId: p.workspaceId.toString(),
        projectId: pilot.projectId.toString(),
        activatedAt: now.toISOString(),
      },
    });
    await appendOutboxEvent(tx, event);
  });

  return updatedRecord!;
}

export async function closePilot(p: ClosePilotParams) {
  assertLifecyclePrivileged(p.actorRole, "close pilot");

  const [pilot] = await db
    .select()
    .from(pilotRuns)
    .where(and(eq(pilotRuns.id, p.pilotId), eq(pilotRuns.workspaceId, p.workspaceId), isNull(pilotRuns.deletedAt)))
    .limit(1);

  if (!pilot) {
    throw APIError.notFound("Pilot run không tồn tại trong workspace này");
  }

  if (pilot.status === "COMPLETED" || pilot.status === "CANCELLED") {
    throw APIError.failedPrecondition(`Pilot run is already in terminal status ${pilot.status}`);
  }

  const now = new Date();
  let updatedRecord: typeof pilotRuns.$inferSelect;

  if (p.status === "CANCELLED") {
    if (!p.cancellationReason || !p.cancellationReason.trim()) {
      throw APIError.invalidArgument("cancellationReason is required when cancelling a pilot run");
    }

    await db.transaction(async (tx) => {
      const [updated] = await tx
        .update(pilotRuns)
        .set({
          status: "CANCELLED",
          cancelledAt: now,
          cancellationReason: p.cancellationReason,
          version: pilot.version + 1,
          updatedAt: now,
        })
        .where(and(eq(pilotRuns.id, p.pilotId), eq(pilotRuns.version, pilot.version)))
        .returning();

      if (!updated) throw APIError.aborted("Concurrent update conflict");
      updatedRecord = updated;

      const event = makeBusinessEvent({
        eventType: "strategy.pilot.closed.v1",
        workspaceId: p.workspaceId.toString(),
        aggregateType: "pilot_run",
        aggregateId: p.pilotId.toString(),
        correlationId: randomUUID(),
        actor: {
          kind: p.actorMemberId ? "user" : "system",
          id: p.actorMemberId ? p.actorMemberId.toString() : "strategy.pilot",
        },
        classification: "internal",
        payload: {
          pilotId: p.pilotId.toString(),
          workspaceId: p.workspaceId.toString(),
          projectId: pilot.projectId.toString(),
          status: "CANCELLED",
          cancellationReason: p.cancellationReason,
          closedAt: now.toISOString(),
        },
      });
      await appendOutboxEvent(tx, event);
    });
  } else if (p.status === "COMPLETED") {
    if (pilot.status !== "ACTIVE") {
      throw APIError.failedPrecondition(`Only ACTIVE pilot can be COMPLETED, current status is ${pilot.status}`);
    }

    await db.transaction(async (tx) => {
      const [updated] = await tx
        .update(pilotRuns)
        .set({
          status: "COMPLETED",
          completedAt: now,
          version: pilot.version + 1,
          updatedAt: now,
        })
        .where(and(eq(pilotRuns.id, p.pilotId), eq(pilotRuns.version, pilot.version)))
        .returning();

      if (!updated) throw APIError.aborted("Concurrent update conflict");
      updatedRecord = updated;

      const event = makeBusinessEvent({
        eventType: "strategy.pilot.closed.v1",
        workspaceId: p.workspaceId.toString(),
        aggregateType: "pilot_run",
        aggregateId: p.pilotId.toString(),
        correlationId: randomUUID(),
        actor: {
          kind: p.actorMemberId ? "user" : "system",
          id: p.actorMemberId ? p.actorMemberId.toString() : "strategy.pilot",
        },
        classification: "internal",
        payload: {
          pilotId: p.pilotId.toString(),
          workspaceId: p.workspaceId.toString(),
          projectId: pilot.projectId.toString(),
          status: "COMPLETED",
          closedAt: now.toISOString(),
        },
      });
      await appendOutboxEvent(tx, event);
    });
  } else {
    throw APIError.invalidArgument(`Invalid status: ${p.status}`);
  }

  return updatedRecord!;
}

export async function getPilotInWorkspace(workspaceId: bigint, pilotId: bigint) {
  const [pilot] = await db
    .select()
    .from(pilotRuns)
    .where(and(eq(pilotRuns.id, pilotId), eq(pilotRuns.workspaceId, workspaceId), isNull(pilotRuns.deletedAt)))
    .limit(1);

  if (!pilot) {
    throw APIError.notFound("Pilot run không tồn tại trong workspace này");
  }
  return pilot;
}

export async function listPilotsInWorkspace(workspaceId: bigint, projectId?: bigint) {
  if (projectId) {
    return db
      .select()
      .from(pilotRuns)
      .where(and(eq(pilotRuns.workspaceId, workspaceId), eq(pilotRuns.projectId, projectId), isNull(pilotRuns.deletedAt)))
      .orderBy(pilotRuns.createdAt);
  }
  return db
    .select()
    .from(pilotRuns)
    .where(and(eq(pilotRuns.workspaceId, workspaceId), isNull(pilotRuns.deletedAt)))
    .orderBy(pilotRuns.createdAt);
}

export interface PilotRunDto {
  id: string;
  workspaceId: string;
  projectId: string;
  experimentId: string | null;
  status: PilotRunStatus;
  designPartnerEvidenceRefs: string[];
  metricContractArtifactRef: string | null;
  instrumentationArtifactRef: string | null;
  onboardingArtifactRef: string | null;
  supportEscalationArtifactRef: string | null;
  rollbackArtifactRef: string | null;
  releaseOwnerMemberId: string;
  approvedByMemberId: string | null;
  approvalRef: string | null;
  approvedAt: string | null;
  activatedByMemberId: string | null;
  activatedAt: string | null;
  completedAt: string | null;
  cancelledAt: string | null;
  cancellationReason: string | null;
  version: number;
  createdAt: string;
  updatedAt: string;
}

export function toPilotRunDto(row: typeof pilotRuns.$inferSelect): PilotRunDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    experimentId: row.experimentId ? row.experimentId.toString() : null,
    status: row.status as PilotRunStatus,
    designPartnerEvidenceRefs: (row.designPartnerEvidenceRefs as string[]) || [],
    metricContractArtifactRef: row.metricContractArtifactRef ?? null,
    instrumentationArtifactRef: row.instrumentationArtifactRef ?? null,
    onboardingArtifactRef: row.onboardingArtifactRef ?? null,
    supportEscalationArtifactRef: row.supportEscalationArtifactRef ?? null,
    rollbackArtifactRef: row.rollbackArtifactRef ?? null,
    releaseOwnerMemberId: row.releaseOwnerMemberId.toString(),
    approvedByMemberId: row.approvedByMemberId ? row.approvedByMemberId.toString() : null,
    approvalRef: row.approvalRef ?? null,
    approvedAt: row.approvedAt ? row.approvedAt.toISOString() : null,
    activatedByMemberId: row.activatedByMemberId ? row.activatedByMemberId.toString() : null,
    activatedAt: row.activatedAt ? row.activatedAt.toISOString() : null,
    completedAt: row.completedAt ? row.completedAt.toISOString() : null,
    cancelledAt: row.cancelledAt ? row.cancelledAt.toISOString() : null,
    cancellationReason: row.cancellationReason ?? null,
    version: row.version,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}
