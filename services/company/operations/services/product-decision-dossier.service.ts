import { APIError } from "encore.dev/api";
import { and, desc, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";

const { projects, productDecisionDossiers, productDecisionDossierRevisions } = schema;

export type ProductDecisionStatus = "DRAFT" | "CONFIRMED" | "SUPERSEDED";

/**
 * Evidence reference — chỉ lưu source ref + classification + excerpt đã
 * redact. KHÔNG BAO GIỜ chứa PII khách hàng hay raw research attachment
 * (những thứ đó nằm ngoài Agent context, xem task-1-brief §evidence).
 */
export interface EvidenceRef {
  sourceRef: string;
  classification: string;
  redactedExcerpt?: string;
}

export interface ProductDecisionSnapshot {
  dossierId: string;
  revision: number;
  evidenceRefs: EvidenceRef[];
  assumptions: unknown[];
  status: ProductDecisionStatus;
}

export interface CreateProductDecisionDossierInput {
  projectId: string;
  title: string;
  assumptions?: unknown[];
  evidenceRefs?: EvidenceRef[];
  reasonCode?: string;
  narrative?: string;
}

export interface AppendProductDecisionRevisionInput {
  assumptions?: unknown[];
  evidenceRefs?: EvidenceRef[];
  status?: "DRAFT" | "CONFIRMED";
  reasonCode: string;
  narrative?: string;
}

function normalizeEvidenceRefs(refs?: EvidenceRef[]): EvidenceRef[] {
  if (!refs) return [];
  return refs.map((r) => ({
    sourceRef: r.sourceRef,
    classification: r.classification,
    redactedExcerpt: r.redactedExcerpt,
  }));
}

/**
 * Guard bắt buộc: chỉ human context (không phải AI agent) mới được tạo/append
 * Product Decision Dossier — model có thể tư vấn nhưng KHÔNG BAO GIỜ tự xác
 * nhận quyết định sản phẩm (CLAUDE.md quy tắc 1 & 5). Project phải thuộc
 * đúng Workspace của ctx — chống truy cập chéo project/workspace.
 */
async function requireHumanProjectContext(
  ctx: TenantContext,
  projectId: string
): Promise<{ id: bigint }> {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }
  if (ctx.isAiAgent) {
    throw APIError.permissionDenied(
      "PRODUCT_DECISION_HUMAN_REQUIRED: Only a human Founder/member context can create or append a product decision"
    );
  }

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);

  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!project) {
    throw APIError.permissionDenied(
      "PROJECT_ACCESS_DENIED: project does not belong to this workspace"
    );
  }

  return project;
}

function toSnapshot(dossierId: bigint, revisionRow: {
  version: number;
  status: string;
  assumptions: unknown;
  evidenceRefs: unknown;
}): ProductDecisionSnapshot {
  return {
    dossierId: dossierId.toString(),
    revision: revisionRow.version,
    evidenceRefs: (revisionRow.evidenceRefs as EvidenceRef[]) ?? [],
    assumptions: (revisionRow.assumptions as unknown[]) ?? [],
    status: revisionRow.status as ProductDecisionStatus,
  };
}

/**
 * Founder/member tạo Product Decision Dossier mới cho Project (revision 1,
 * status DRAFT). Model context không bao giờ tới được nhánh này.
 */
export async function createProductDecisionDossier(
  ctx: TenantContext,
  input: CreateProductDecisionDossierInput
): Promise<ProductDecisionSnapshot> {
  if (!input.title?.trim()) {
    throw APIError.invalidArgument("title is required");
  }

  await requireHumanProjectContext(ctx, input.projectId);

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(input.projectId);
  const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  return db.transaction(async (tx) => {
    const dossierId = generateSnowflake();

    await tx.insert(productDecisionDossiers).values({
      id: dossierId,
      workspaceId: wsId,
      projectId: projId,
      title: input.title,
      status: "DRAFT",
      currentVersion: 1,
      createdByMemberId: actorMemberId,
    });

    const [revision] = await tx
      .insert(productDecisionDossierRevisions)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: projId,
        dossierId,
        version: 1,
        status: "DRAFT",
        assumptions: input.assumptions ?? [],
        evidenceRefs: normalizeEvidenceRefs(input.evidenceRefs),
        reasonCode: input.reasonCode ?? null,
        narrative: input.narrative ?? null,
        actorMemberId,
      })
      .returning();

    if (!revision) throw APIError.internal("failed to create product decision dossier");

    return toSnapshot(dossierId, revision);
  });
}

/**
 * Founder/member append một revision mới (CAS theo expectedVersion). Đặt
 * status "CONFIRMED" chỉ hợp lệ khi ctx là human founder/co-founder — đúng
 * tinh thần "Founder-reviewed" của dossier này. Model/agent context luôn bị
 * chặn ở `requireHumanProjectContext` trước khi chạm DB.
 */
export async function appendProductDecisionRevision(
  ctx: TenantContext,
  dossierId: string,
  expectedVersion: number,
  input: AppendProductDecisionRevisionInput
): Promise<ProductDecisionSnapshot> {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }
  if (ctx.isAiAgent) {
    throw APIError.permissionDenied(
      "PRODUCT_DECISION_HUMAN_REQUIRED: Only a human Founder/member context can append a product decision revision"
    );
  }
  if (!input.reasonCode?.trim()) {
    throw APIError.invalidArgument("reasonCode is required");
  }

  const wsId = BigInt(ctx.workspaceId);
  const dossierBigId = BigInt(dossierId);

  const [dossier] = await db
    .select()
    .from(productDecisionDossiers)
    .where(and(eq(productDecisionDossiers.id, dossierBigId), eq(productDecisionDossiers.workspaceId, wsId)))
    .limit(1);
  if (!dossier) throw APIError.notFound("product decision dossier not found in workspace");

  if (dossier.currentVersion !== expectedVersion) {
    throw APIError.aborted(
      `CAS_CONFLICT: stale dossier version (expected ${expectedVersion}, got ${dossier.currentVersion})`
    );
  }

  const nextStatus = input.status ?? (dossier.status as ProductDecisionStatus) ?? "DRAFT";
  if (nextStatus === "CONFIRMED") {
    const role = (ctx.membershipRole || "").toLowerCase();
    if (!["founder", "co-founder"].includes(role)) {
      throw APIError.permissionDenied(
        "FOUNDER_CONFIRMATION_REQUIRED: Only a human founder can confirm a product decision"
      );
    }
  }

  const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;
  const nextVersion = dossier.currentVersion + 1;

  return db.transaction(async (tx) => {
    const [prior] = await tx
      .select({ id: productDecisionDossierRevisions.id })
      .from(productDecisionDossierRevisions)
      .where(eq(productDecisionDossierRevisions.dossierId, dossierBigId))
      .orderBy(desc(productDecisionDossierRevisions.version))
      .limit(1);

    const [revision] = await tx
      .insert(productDecisionDossierRevisions)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: dossier.projectId,
        dossierId: dossierBigId,
        version: nextVersion,
        status: nextStatus,
        assumptions: input.assumptions ?? [],
        evidenceRefs: normalizeEvidenceRefs(input.evidenceRefs),
        reasonCode: input.reasonCode,
        narrative: input.narrative ?? null,
        actorMemberId,
        confirmedByMemberId: nextStatus === "CONFIRMED" ? actorMemberId : null,
        confirmedAt: nextStatus === "CONFIRMED" ? new Date() : null,
        supersedesRevisionId: prior?.id ?? null,
      })
      .returning();
    if (!revision) throw APIError.internal("failed to append product decision revision");

    const [updatedDossier] = await tx
      .update(productDecisionDossiers)
      .set({
        currentVersion: nextVersion,
        status: nextStatus,
        updatedAt: new Date(),
      })
      .where(
        and(
          eq(productDecisionDossiers.id, dossierBigId),
          eq(productDecisionDossiers.currentVersion, expectedVersion)
        )
      )
      .returning();
    if (!updatedDossier) {
      throw APIError.aborted("CAS_CONFLICT: dossier changed concurrently");
    }

    return toSnapshot(dossierBigId, revision);
  });
}

/**
 * Đọc snapshot mới nhất (đã redact tại nguồn — evidence_refs chỉ chứa
 * source ref/classification/excerpt) của Product Decision Dossier theo
 * Project. Model/agent context ĐƯỢC PHÉP đọc (chỉ không được ghi). Project ở
 * workspace khác luôn bị từ chối bằng permission_denied — không lộ thông tin
 * tồn tại/không tồn tại của project chéo tenant.
 */
export async function readProductDecisionSnapshot(
  ctx: TenantContext,
  projectId: string
): Promise<ProductDecisionSnapshot> {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);

  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);
  if (!project) {
    throw APIError.permissionDenied(
      "PROJECT_ACCESS_DENIED: project does not belong to this workspace"
    );
  }

  const [dossier] = await db
    .select()
    .from(productDecisionDossiers)
    .where(and(eq(productDecisionDossiers.workspaceId, wsId), eq(productDecisionDossiers.projectId, projId)))
    .orderBy(desc(productDecisionDossiers.updatedAt))
    .limit(1);
  if (!dossier) {
    throw APIError.notFound("no product decision dossier found for this project");
  }

  const [revision] = await db
    .select()
    .from(productDecisionDossierRevisions)
    .where(eq(productDecisionDossierRevisions.dossierId, dossier.id))
    .orderBy(desc(productDecisionDossierRevisions.version))
    .limit(1);
  if (!revision) {
    throw APIError.internal("product decision dossier has no revisions");
  }

  return toSnapshot(dossier.id, revision);
}
