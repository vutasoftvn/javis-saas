import { APIError } from "encore.dev/api";
import { eq, and, inArray, desc, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspaceRecord } from "../../identity/services/workspace.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { requireCommandAuthority } from "../../identity/services/command-authority.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";

const { legalObligations } = schema;

export interface LegalObligation {
  id: string;
  workspaceId: string;
  title: string;
  description: string | null;
  dueAt: string | null;
  status: string;
  createdAt: string;
}

export interface CreateObligationParams {
  workspaceId: string;
  title: string;
  description?: string;
  dueAt?: string;
}

function toObligation(row: typeof legalObligations.$inferSelect): LegalObligation {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    title: row.title,
    description: row.description,
    dueAt: row.dueAt ? row.dueAt.toISOString() : null,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function createObligationService(
  params: CreateObligationParams,
  authorization: string | undefined
): Promise<LegalObligation> {
  await requireWorkspaceAccess(authorization, params.workspaceId);
  await getWorkspaceRecord(String(params.workspaceId));

  const [row] = await db
    .insert(legalObligations)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      title: params.title,
      description: params.description || null,
      dueAt: params.dueAt ? new Date(params.dueAt) : null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create obligation");
  return toObligation(row);
}

export async function getObligationService(
  id: string,
  ctx: TenantContext
): Promise<LegalObligation> {
  const [row] = await db
    .select()
    .from(legalObligations)
    .where(and(eq(legalObligations.id, BigInt(id)), eq(legalObligations.workspaceId, BigInt(ctx.workspaceId))))
    .limit(1);

  if (!row) throw APIError.notFound(`obligation ${id} not found`);
  return toObligation(row);
}

export async function fulfillObligationService(
  id: string,
  ctx: TenantContext
): Promise<LegalObligation> {
  const [row] = await db
    .update(legalObligations)
    .set({ status: "FULFILLED" })
    .where(and(eq(legalObligations.id, BigInt(id)), eq(legalObligations.workspaceId, BigInt(ctx.workspaceId))))
    .returning();

  if (!row) throw APIError.notFound(`obligation ${id} not found`);
  return toObligation(row);
}

const { legalObligationInstances, obligationTransitions } = schema;

export interface LegalObligationInstanceView {
  id: string;
  workspaceId: string;
  legalEntityProfileId: string | null;
  templateId: string | null;
  regulationVersionId: string | null;
  source: "REGULATION_TEMPLATE" | "USER_CREATED" | "AI_PROPOSAL";
  title: string;
  dueDate: string | null;
  status: string;
  periodKey: string | null;
  evidenceRefs: string[];
  evidenceArtifactId: string | null;
  reviewStatus: string;
  createdAt: string;
  updatedAt: string;
}

function toInstanceView(r: typeof legalObligationInstances.$inferSelect): LegalObligationInstanceView {
  return {
    id: String(r.id),
    workspaceId: String(r.workspaceId),
    legalEntityProfileId: r.legalEntityProfileId ? String(r.legalEntityProfileId) : null,
    templateId: r.templateId ? String(r.templateId) : null,
    regulationVersionId: r.regulationVersionId ? String(r.regulationVersionId) : null,
    source: r.source as any,
    title: r.title,
    dueDate: r.dueDate ? String(r.dueDate) : null,
    status: r.status === "PENDING" ? "OPEN" : r.status,
    periodKey: r.periodKey ?? null,
    evidenceRefs: (r.evidenceRefs as string[]) || [],
    evidenceArtifactId: r.evidenceArtifactId ? String(r.evidenceArtifactId) : null,
    reviewStatus: r.reviewStatus,
    createdAt: r.createdAt.toISOString(),
    updatedAt: r.updatedAt.toISOString(),
  };
}

export async function listObligationInstancesService(
  workspaceId: bigint,
  status?: string
): Promise<LegalObligationInstanceView[]> {
  const rows = await db
    .select()
    .from(legalObligationInstances)
    .where(eq(legalObligationInstances.workspaceId, workspaceId));

  let filtered = rows;
  if (status) {
    filtered = rows.filter((r) => r.status.toLowerCase() === status.toLowerCase());
  }

  return filtered.map(toInstanceView);
}

export interface OpenObligationView extends LegalObligationInstanceView {
  isOverdue: boolean;
  overdueDays: number;
}

export async function listOpenObligations(
  ctx: { workspaceId: string },
  params?: {
    projectId?: bigint;
    legalEntityId?: bigint;
    at?: string;
  }
): Promise<OpenObligationView[]> {
  const wsId = BigInt(ctx.workspaceId);
  const atDate = params?.at ? new Date(params.at) : new Date();

  const conditions = [
    eq(legalObligationInstances.workspaceId, wsId),
    inArray(legalObligationInstances.status, ["OPEN", "IN_PROGRESS", "PENDING"]),
  ];

  if (params?.legalEntityId) {
    conditions.push(eq(legalObligationInstances.legalEntityProfileId, params.legalEntityId));
  }

  const rows = await db
    .select()
    .from(legalObligationInstances)
    .where(and(...conditions));

  return rows.map((r) => {
    let isOverdue = false;
    let overdueDays = 0;
    if (r.dueDate) {
      const dueTime = new Date(r.dueDate).getTime();
      const diffMs = atDate.getTime() - dueTime;
      if (diffMs > 0) {
        isOverdue = true;
        overdueDays = Math.floor(diffMs / (24 * 60 * 60 * 1000));
      }
    }

    const base = toInstanceView(r);
    return {
      ...base,
      isOverdue,
      overdueDays,
    };
  });
}

export async function createObligationInstanceService(p: {
  workspaceId: bigint;
  templateId?: bigint;
  regulationVersionId?: bigint;
  legalEntityProfileId?: bigint;
  source: "REGULATION_TEMPLATE" | "USER_CREATED" | "AI_PROPOSAL";
  title: string;
  dueDate?: string;
  periodKey?: string;
  evidenceRefs?: string[];
  evidenceArtifactId?: bigint;
  ownerMemberId?: bigint;
}): Promise<LegalObligationInstanceView> {
  // Idempotency check: if templateId and periodKey exist, prevent duplicate instance
  if (p.templateId && p.periodKey) {
    const existing = await db
      .select()
      .from(legalObligationInstances)
      .where(
        and(
          eq(legalObligationInstances.workspaceId, p.workspaceId),
          eq(legalObligationInstances.templateId, p.templateId),
          eq(legalObligationInstances.periodKey, p.periodKey),
          p.legalEntityProfileId
            ? eq(legalObligationInstances.legalEntityProfileId, p.legalEntityProfileId)
            : isNull(legalObligationInstances.legalEntityProfileId)
        )
      )
      .limit(1);

    if (existing.length > 0) {
      return toInstanceView(existing[0]);
    }
  }

  const newId = generateSnowflake();
  const [created] = await db
    .insert(legalObligationInstances)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      legalEntityProfileId: p.legalEntityProfileId ?? null,
      templateId: p.templateId ?? null,
      regulationVersionId: p.regulationVersionId ?? null,
      source: p.source,
      title: p.title,
      dueDate: p.dueDate ? (p.dueDate as any) : null,
      periodKey: p.periodKey ?? null,
      evidenceRefs: p.evidenceRefs ?? [],
      evidenceArtifactId: p.evidenceArtifactId ?? null,
      ownerMemberId: p.ownerMemberId ?? null,
      status: "OPEN",
      reviewStatus: p.source === "AI_PROPOSAL" ? "PENDING_REVIEW" : "ACCEPTED",
    })
    .returning();

  return toInstanceView(created);
}

export interface TransitionObligationInput {
  workspaceId: bigint;
  instanceId: bigint;
  expectedFromStatus?: string;
  toStatus: "OPEN" | "IN_PROGRESS" | "FULFILLED" | "EXEMPT" | "CANCELLED";
  evidenceArtifactId?: bigint;
  evidenceRefs?: string[];
  actorMemberId?: bigint;
  rationale?: string;
}

export interface ObligationTransitionView {
  id: string;
  obligationInstanceId: string;
  fromStatus: string;
  toStatus: string;
  evidenceArtifactId: string | null;
  evidenceRefs: string[];
  actorMemberId: string | null;
  rationale: string | null;
  createdAt: string;
}

const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  OPEN: ["IN_PROGRESS", "FULFILLED", "EXEMPT", "CANCELLED"],
  IN_PROGRESS: ["FULFILLED", "EXEMPT", "CANCELLED", "OPEN"],
  FULFILLED: [],
  EXEMPT: ["OPEN"],
  CANCELLED: ["OPEN"],
  PENDING: ["OPEN", "IN_PROGRESS", "FULFILLED", "EXEMPT", "CANCELLED"],
};

export async function transitionObligationStatus(
  input: TransitionObligationInput,
  ctx?: TenantContext
): Promise<LegalObligationInstanceView> {
  const wsId = input.workspaceId;
  const instId = input.instanceId;

  // IA18: bắt buộc quyền legal.obligation.manage khi có ctx (request HTTP thật
  // luôn có ctx qua requireWorkspaceAccess); giữ ctx optional để không phá các
  // caller nội bộ/test không qua HTTP — theo đúng pattern resumeAiDeployment.
  if (ctx) {
    await requireCommandAuthority(ctx, "legal.obligation.manage", { workspaceId: String(wsId) });
  }

  // 1. Transition sang FULFILLED bắt buộc kèm evidence có nội dung thật
  // (IA18: trước đây [""] cũng qua vì chỉ kiểm length > 0, không kiểm nội dung).
  if (input.toStatus === "FULFILLED") {
    const hasEvidence =
      Boolean(input.evidenceArtifactId) ||
      (Array.isArray(input.evidenceRefs) &&
        input.evidenceRefs.some((ref) => typeof ref === "string" && ref.trim().length > 0));
    if (!hasEvidence) {
      const err = APIError.invalidArgument(
        "Fulfillment requires verified evidence (evidenceArtifactId or non-empty evidenceRefs)"
      );
      (err as any).code = "EVIDENCE_REQUIRED";
      throw err;
    }
  }

  // IA18: EXEMPT bắt buộc rationale làm căn cứ miễn trừ — trước đây có thể
  // miễn trừ nghĩa vụ mà không cần giải trình gì.
  if (input.toStatus === "EXEMPT") {
    if (!input.rationale || !input.rationale.trim()) {
      const err = APIError.invalidArgument(
        "Exemption requires a rationale documenting the legal basis"
      );
      (err as any).code = "RATIONALE_REQUIRED";
      throw err;
    }
  }

  return await db.transaction(async (tx) => {
    // 2. Fetch current record
    const [current] = await tx
      .select()
      .from(legalObligationInstances)
      .where(
        and(
          eq(legalObligationInstances.id, instId),
          eq(legalObligationInstances.workspaceId, wsId)
        )
      )
      .limit(1);

    if (!current) {
      throw APIError.notFound(`Legal obligation instance ${instId} not found`);
    }

    const currentCanonical = current.status === "PENDING" ? "OPEN" : current.status;

    // Idempotent: return existing if already transitioned
    if (currentCanonical === input.toStatus) {
      return toInstanceView(current);
    }

    // Expected from status check
    if (input.expectedFromStatus && currentCanonical !== input.expectedFromStatus) {
      const err = APIError.aborted(
        `CAS mismatch: expected status ${input.expectedFromStatus} but current status is ${currentCanonical}`
      );
      (err as any).code = "CONCURRENT_MODIFICATION";
      throw err;
    }

    // Allowed transition check
    const allowed = ALLOWED_TRANSITIONS[currentCanonical] || [];
    if (!allowed.includes(input.toStatus)) {
      const err = APIError.invalidArgument(
        `Invalid obligation transition from ${currentCanonical} to ${input.toStatus}`
      );
      (err as any).code = "INVALID_TRANSITION";
      throw err;
    }

    const now = new Date();
    const updatedEvidenceRefs = input.evidenceRefs || (current.evidenceRefs as string[]) || [];
    const updatedArtifactId = input.evidenceArtifactId ?? current.evidenceArtifactId;

    // 3. CAS Update
    const [updated] = await tx
      .update(legalObligationInstances)
      .set({
        status: input.toStatus,
        evidenceArtifactId: updatedArtifactId,
        evidenceRefs: updatedEvidenceRefs,
        updatedAt: now,
      })
      .where(
        and(
          eq(legalObligationInstances.id, instId),
          eq(legalObligationInstances.workspaceId, wsId),
          eq(legalObligationInstances.status, current.status)
        )
      )
      .returning();

    if (!updated) {
      const err = APIError.aborted("Concurrent modification during obligation transition");
      (err as any).code = "CONCURRENT_MODIFICATION";
      throw err;
    }

    // 4. Log to obligation_transitions
    const transitionId = generateSnowflake();
    const actorId = ctx ? (ctx.workforceMemberId || ctx.userId) : input.actorMemberId;
    await tx.insert(obligationTransitions).values({
      id: transitionId,
      workspaceId: wsId,
      obligationInstanceId: instId,
      fromStatus: currentCanonical,
      toStatus: input.toStatus,
      evidenceArtifactId: input.evidenceArtifactId ?? null,
      evidenceRefs: input.evidenceRefs || [],
      actorMemberId: actorId ? BigInt(actorId) : null,
      rationale: input.rationale ?? null,
      createdAt: now,
    });

    return toInstanceView(updated);
  });
}

export async function listObligationTransitions(
  workspaceId: bigint,
  obligationInstanceId: bigint
): Promise<ObligationTransitionView[]> {
  const rows = await db
    .select()
    .from(obligationTransitions)
    .where(
      and(
        eq(obligationTransitions.workspaceId, workspaceId),
        eq(obligationTransitions.obligationInstanceId, obligationInstanceId)
      )
    )
    .orderBy(desc(obligationTransitions.createdAt));

  return rows.map((r) => ({
    id: String(r.id),
    obligationInstanceId: String(r.obligationInstanceId),
    fromStatus: r.fromStatus,
    toStatus: r.toStatus,
    evidenceArtifactId: r.evidenceArtifactId ? String(r.evidenceArtifactId) : null,
    evidenceRefs: (r.evidenceRefs as string[]) || [],
    actorMemberId: r.actorMemberId ? String(r.actorMemberId) : null,
    rationale: r.rationale,
    createdAt: r.createdAt.toISOString(),
  }));
}


