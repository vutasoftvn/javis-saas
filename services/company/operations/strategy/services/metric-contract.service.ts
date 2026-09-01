import { APIError } from "encore.dev/api";
import { and, desc, eq, isNull } from "drizzle-orm";
import { db } from "../../models/db";
import { projects } from "../../../shared/db/schema/operations";
import { metricContracts } from "../../../shared/db/schema/strategy";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { assertLifecyclePrivileged } from "./lifecycle-authorization.service";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../../shared/events/envelope";
import { randomUUID } from "node:crypto";

export type MetricContractStatus = "DRAFT" | "ACTIVE" | "DEPRECATED";

export interface SourceMapping {
  system: string;
  identifier: string;
  aggregation: string;
  window: string;
}

export interface CreateMetricContractDraftParams {
  workspaceId: bigint;
  projectId: bigint;
  metricKey: string;
  displayName: string;
  unit: string;
  numeratorDefinition: string;
  denominatorDefinition: string;
  cohortDefinition: string;
  sourceMapping: SourceMapping;
  cadence: string;
  freshUntil?: Date;
  guardrail?: string;
  ownerMemberId?: bigint;
  decisionUse: string;
  changeRationale?: string;
  actorMemberId?: bigint;
  actorRole?: string;
}

export interface UpdateMetricContractDraftParams {
  workspaceId: bigint;
  id: bigint;
  displayName?: string;
  unit?: string;
  numeratorDefinition?: string;
  denominatorDefinition?: string;
  cohortDefinition?: string;
  sourceMapping?: SourceMapping;
  cadence?: string;
  freshUntil?: Date;
  guardrail?: string;
  ownerMemberId?: bigint;
  decisionUse?: string;
  changeRationale?: string;
  actorMemberId?: bigint;
  actorRole?: string;
}

export interface PublishMetricContractParams {
  workspaceId: bigint;
  id: bigint;
  approvalRef: string;
  actorMemberId?: bigint;
  actorRole?: string;
}

export interface ReviseMetricContractParams {
  workspaceId: bigint;
  id: bigint;
  displayName?: string;
  unit?: string;
  numeratorDefinition?: string;
  denominatorDefinition?: string;
  cohortDefinition?: string;
  sourceMapping?: SourceMapping;
  cadence?: string;
  freshUntil?: Date;
  guardrail?: string;
  ownerMemberId?: bigint;
  decisionUse?: string;
  changeRationale?: string;
  actorMemberId?: bigint;
  actorRole?: string;
}

function validateSourceMapping(mapping: unknown): asserts mapping is SourceMapping {
  if (!mapping || typeof mapping !== "object") {
    throw APIError.invalidArgument("sourceMapping must be an object with system, identifier, aggregation, window");
  }
  const m = mapping as Record<string, unknown>;
  const { system, identifier, aggregation, window } = m;
  if (!system || typeof system !== "string" || !system.trim()) {
    throw APIError.invalidArgument("sourceMapping.system is required");
  }
  if (!identifier || typeof identifier !== "string" || !identifier.trim()) {
    throw APIError.invalidArgument("sourceMapping.identifier is required");
  }
  if (!aggregation || typeof aggregation !== "string" || !aggregation.trim()) {
    throw APIError.invalidArgument("sourceMapping.aggregation is required");
  }
  if (!window || typeof window !== "string" || !window.trim()) {
    throw APIError.invalidArgument("sourceMapping.window is required");
  }

  // Reject credentials, passwords, tokens, raw SQL injection patterns
  const forbiddenPatterns = [
    /\b(select|insert|update|delete|drop|union|alter|exec|truncate|grant|revoke)\b/i,
    /--|;|\/\*|\*\//,
    /\b(password|secret|token|apikey|api_key|bearer|credentials)\b/i,
  ];

  const serialized = JSON.stringify(mapping);
  for (const pattern of forbiddenPatterns) {
    if (pattern.test(serialized)) {
      throw APIError.invalidArgument(
        `sourceMapping contains forbidden or insecure tokens/SQL patterns: ${pattern.toString()}`
      );
    }
  }
}

export async function createMetricContractDraft(p: CreateMetricContractDraftParams) {
  // 1. Verify project in workspace
  const [proj] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, p.projectId), eq(projects.workspaceId, p.workspaceId), isNull(projects.deletedAt)))
    .limit(1);

  if (!proj) {
    throw APIError.notFound("Project không tồn tại trong workspace này");
  }

  // 2. Validate required fields
  if (!p.metricKey || !p.metricKey.trim()) {
    throw APIError.invalidArgument("metricKey is required");
  }
  if (!p.displayName || !p.displayName.trim()) {
    throw APIError.invalidArgument("displayName is required");
  }
  if (!p.unit || !p.unit.trim()) {
    throw APIError.invalidArgument("unit is required");
  }
  if (!p.numeratorDefinition || !p.numeratorDefinition.trim()) {
    throw APIError.invalidArgument("numeratorDefinition is required");
  }
  if (!p.denominatorDefinition || !p.denominatorDefinition.trim()) {
    throw APIError.invalidArgument("denominatorDefinition is required");
  }
  if (!p.cohortDefinition || !p.cohortDefinition.trim()) {
    throw APIError.invalidArgument("cohortDefinition is required");
  }
  if (!p.cadence || !p.cadence.trim()) {
    throw APIError.invalidArgument("cadence is required");
  }
  if (!p.ownerMemberId) {
    throw APIError.invalidArgument("ownerMemberId is required");
  }
  if (!p.decisionUse || !p.decisionUse.trim()) {
    throw APIError.invalidArgument("decisionUse is required");
  }

  validateSourceMapping(p.sourceMapping);

  // Check if active or draft version already exists for metricKey in project
  const existing = await db
    .select()
    .from(metricContracts)
    .where(
      and(
        eq(metricContracts.workspaceId, p.workspaceId),
        eq(metricContracts.projectId, p.projectId),
        eq(metricContracts.metricKey, p.metricKey),
        isNull(metricContracts.deletedAt)
      )
    )
    .orderBy(desc(metricContracts.version))
    .limit(1);

  const nextVersion = existing.length > 0 ? existing[0].version + 1 : 1;

  const now = new Date();
  const id = generateSnowflake();

  const [created] = await db
    .insert(metricContracts)
    .values({
      id,
      workspaceId: p.workspaceId,
      projectId: p.projectId,
      metricKey: p.metricKey,
      displayName: p.displayName,
      unit: p.unit,
      numeratorDefinition: p.numeratorDefinition,
      denominatorDefinition: p.denominatorDefinition,
      cohortDefinition: p.cohortDefinition,
      sourceMapping: p.sourceMapping,
      cadence: p.cadence,
      freshUntil: p.freshUntil ?? null,
      guardrail: p.guardrail ?? null,
      ownerMemberId: p.ownerMemberId,
      decisionUse: p.decisionUse,
      status: "DRAFT",
      version: nextVersion,
      changeRationale: p.changeRationale ?? "Initial draft",
      createdByMemberId: p.actorMemberId ?? null,
      createdAt: now,
      updatedAt: now,
    })
    .returning();

  if (!created) {
    throw APIError.internal("Failed to create metric contract draft");
  }

  return created;
}

export async function updateMetricContractDraft(p: UpdateMetricContractDraftParams) {
  const [contract] = await db
    .select()
    .from(metricContracts)
    .where(
      and(
        eq(metricContracts.id, p.id),
        eq(metricContracts.workspaceId, p.workspaceId),
        isNull(metricContracts.deletedAt)
      )
    )
    .limit(1);

  if (!contract) {
    throw APIError.notFound("Metric contract không tồn tại trong workspace này");
  }

  if (contract.status !== "DRAFT") {
    throw APIError.failedPrecondition(
      `Published metric contracts are immutable. Create a new revision instead (current status: ${contract.status})`
    );
  }

  if (p.sourceMapping) {
    validateSourceMapping(p.sourceMapping);
  }

  const now = new Date();

  const [updated] = await db
    .update(metricContracts)
    .set({
      displayName: p.displayName ?? contract.displayName,
      unit: p.unit ?? contract.unit,
      numeratorDefinition: p.numeratorDefinition ?? contract.numeratorDefinition,
      denominatorDefinition: p.denominatorDefinition ?? contract.denominatorDefinition,
      cohortDefinition: p.cohortDefinition ?? contract.cohortDefinition,
      sourceMapping: p.sourceMapping ?? contract.sourceMapping,
      cadence: p.cadence ?? contract.cadence,
      freshUntil: p.freshUntil !== undefined ? p.freshUntil : contract.freshUntil,
      guardrail: p.guardrail !== undefined ? p.guardrail : contract.guardrail,
      ownerMemberId: p.ownerMemberId ?? contract.ownerMemberId,
      decisionUse: p.decisionUse ?? contract.decisionUse,
      changeRationale: p.changeRationale ?? contract.changeRationale,
      updatedAt: now,
    })
    .where(and(eq(metricContracts.id, p.id), eq(metricContracts.workspaceId, p.workspaceId)))
    .returning();

  if (!updated) {
    throw APIError.internal("Failed to update metric contract draft");
  }

  return updated;
}

export async function publishMetricContract(p: PublishMetricContractParams) {
  assertLifecyclePrivileged(p.actorRole, "publish metric contract");
  if (!p.approvalRef || !p.approvalRef.trim()) {
    throw APIError.invalidArgument("approvalRef is required for publishing metric contract");
  }

  const [contract] = await db
    .select()
    .from(metricContracts)
    .where(
      and(
        eq(metricContracts.id, p.id),
        eq(metricContracts.workspaceId, p.workspaceId),
        isNull(metricContracts.deletedAt)
      )
    )
    .limit(1);

  if (!contract) {
    throw APIError.notFound("Metric contract không tồn tại trong workspace này");
  }

  if (contract.status === "ACTIVE") {
    return contract; // Idempotent
  }

  if (contract.status !== "DRAFT") {
    throw APIError.failedPrecondition(`Only DRAFT contract can be published (current status: ${contract.status})`);
  }

  const now = new Date();
  let updatedRecord: typeof metricContracts.$inferSelect;

  await db.transaction(async (tx) => {
    const [updated] = await tx
      .update(metricContracts)
      .set({
        status: "ACTIVE",
        approvalRef: p.approvalRef,
        publishedByMemberId: p.actorMemberId ?? null,
        publishedAt: now,
        updatedAt: now,
      })
      .where(and(eq(metricContracts.id, p.id), eq(metricContracts.workspaceId, p.workspaceId)))
      .returning();

    if (!updated) {
      throw APIError.aborted("Metric contract was updated concurrently");
    }
    updatedRecord = updated;

    const event = makeBusinessEvent({
      eventType: "strategy.metric_contract.published.v1",
      workspaceId: p.workspaceId.toString(),
      aggregateType: "metric_contract",
      aggregateId: p.id.toString(),
      correlationId: randomUUID(),
      actor: {
        kind: p.actorMemberId ? "user" : "system",
        id: p.actorMemberId ? p.actorMemberId.toString() : "strategy.metric_contract",
      },
      classification: "internal",
      payload: {
        contractId: p.id.toString(),
        workspaceId: p.workspaceId.toString(),
        projectId: contract.projectId.toString(),
        metricKey: contract.metricKey,
        version: contract.version,
        approvalRef: p.approvalRef,
        publishedAt: now.toISOString(),
      },
    });
    await appendOutboxEvent(tx, event);
  });

  return updatedRecord!;
}

export async function reviseMetricContract(p: ReviseMetricContractParams) {
  assertLifecyclePrivileged(p.actorRole, "revise metric contract");

  const [existing] = await db
    .select()
    .from(metricContracts)
    .where(
      and(
        eq(metricContracts.id, p.id),
        eq(metricContracts.workspaceId, p.workspaceId),
        isNull(metricContracts.deletedAt)
      )
    )
    .limit(1);

  if (!existing) {
    throw APIError.notFound("Metric contract không tồn tại trong workspace này");
  }

  if (p.sourceMapping) {
    validateSourceMapping(p.sourceMapping);
  }

  // Find max version for this workspace + project + metricKey
  const [maxVerRecord] = await db
    .select({ version: metricContracts.version })
    .from(metricContracts)
    .where(
      and(
        eq(metricContracts.workspaceId, p.workspaceId),
        eq(metricContracts.projectId, existing.projectId),
        eq(metricContracts.metricKey, existing.metricKey),
        isNull(metricContracts.deletedAt)
      )
    )
    .orderBy(desc(metricContracts.version))
    .limit(1);

  const nextVersion = (maxVerRecord?.version ?? existing.version) + 1;
  const now = new Date();
  const id = generateSnowflake();

  const [revised] = await db
    .insert(metricContracts)
    .values({
      id,
      workspaceId: p.workspaceId,
      projectId: existing.projectId,
      metricKey: existing.metricKey,
      displayName: p.displayName ?? existing.displayName,
      unit: p.unit ?? existing.unit,
      numeratorDefinition: p.numeratorDefinition ?? existing.numeratorDefinition,
      denominatorDefinition: p.denominatorDefinition ?? existing.denominatorDefinition,
      cohortDefinition: p.cohortDefinition ?? existing.cohortDefinition,
      sourceMapping: p.sourceMapping ?? existing.sourceMapping,
      cadence: p.cadence ?? existing.cadence,
      freshUntil: p.freshUntil !== undefined ? p.freshUntil : existing.freshUntil,
      guardrail: p.guardrail !== undefined ? p.guardrail : existing.guardrail,
      ownerMemberId: p.ownerMemberId ?? existing.ownerMemberId,
      decisionUse: p.decisionUse ?? existing.decisionUse,
      status: "DRAFT",
      version: nextVersion,
      changeRationale: p.changeRationale ?? `Revised from v${existing.version}`,
      createdByMemberId: p.actorMemberId ?? null,
      createdAt: now,
      updatedAt: now,
    })
    .returning();

  if (!revised) {
    throw APIError.internal("Failed to create revised metric contract version");
  }

  return revised;
}

export async function getMetricContractInWorkspace(workspaceId: bigint, contractId: bigint) {
  const [contract] = await db
    .select()
    .from(metricContracts)
    .where(
      and(
        eq(metricContracts.id, contractId),
        eq(metricContracts.workspaceId, workspaceId),
        isNull(metricContracts.deletedAt)
      )
    )
    .limit(1);

  if (!contract) {
    throw APIError.notFound("Metric contract không tồn tại trong workspace này");
  }

  return contract;
}

export async function listMetricContractsInWorkspace(workspaceId: bigint, projectId?: bigint) {
  if (projectId) {
    return db
      .select()
      .from(metricContracts)
      .where(
        and(
          eq(metricContracts.workspaceId, workspaceId),
          eq(metricContracts.projectId, projectId),
          isNull(metricContracts.deletedAt)
        )
      )
      .orderBy(desc(metricContracts.version));
  }

  return db
    .select()
    .from(metricContracts)
    .where(and(eq(metricContracts.workspaceId, workspaceId), isNull(metricContracts.deletedAt)))
    .orderBy(desc(metricContracts.version));
}

export interface MetricContractDto {
  id: string;
  workspaceId: string;
  projectId: string;
  metricKey: string;
  displayName: string;
  unit: string;
  numeratorDefinition: string;
  denominatorDefinition: string;
  cohortDefinition: string;
  sourceMapping: SourceMapping;
  cadence: string;
  freshUntil: string | null;
  guardrail: string | null;
  ownerMemberId: string | null;
  decisionUse: string;
  status: MetricContractStatus;
  version: number;
  approvalRef: string | null;
  changeRationale: string | null;
  createdByMemberId: string | null;
  publishedByMemberId: string | null;
  publishedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export function toMetricContractDto(row: typeof metricContracts.$inferSelect): MetricContractDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    metricKey: row.metricKey,
    displayName: row.displayName,
    unit: row.unit,
    numeratorDefinition: row.numeratorDefinition,
    denominatorDefinition: row.denominatorDefinition,
    cohortDefinition: row.cohortDefinition,
    sourceMapping: row.sourceMapping as SourceMapping,
    cadence: row.cadence,
    freshUntil: row.freshUntil ? row.freshUntil.toISOString() : null,
    guardrail: row.guardrail ?? null,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    decisionUse: row.decisionUse,
    status: row.status as MetricContractStatus,
    version: row.version,
    approvalRef: row.approvalRef ?? null,
    changeRationale: row.changeRationale ?? null,
    createdByMemberId: row.createdByMemberId ? row.createdByMemberId.toString() : null,
    publishedByMemberId: row.publishedByMemberId ? row.publishedByMemberId.toString() : null,
    publishedAt: row.publishedAt ? row.publishedAt.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}
