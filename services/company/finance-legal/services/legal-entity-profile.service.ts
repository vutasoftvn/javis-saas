import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { LEGAL_STATUS_CHANGED } from "../../shared/events";
import { randomUUID } from "node:crypto";

const { legalEntityProfiles, legalVerificationApprovals } = schema;

// M1 §6 — verification chỉ được confirm cho đúng transition này.
const VERIFICATION_EXPECTED_STATUS = "VERIFIED";
// Cửa sổ hiệu lực của một approval PENDING (spec: ~+72h).
const APPROVAL_TTL_MS = 72 * 60 * 60 * 1000;

export type LegalStatus =
  | "DRAFT"
  | "REGISTRATION_PREPARATION"
  | "REGISTERED_UNVERIFIED"
  | "VERIFIED"
  | "SUSPENDED"
  | "DISSOLVED";

export interface LegalEntityProfileView {
  id: string;
  workspaceId: string;
  entityType: string;
  status: LegalStatus;
  registrationNumber: string | null;
  taxId: string | null;
  verifiedAt: string | null;}

export async function listLegalEntityProfiles(
  workspaceId: bigint
): Promise<LegalEntityProfileView[]> {
  const rows = await db
    .select()
    .from(legalEntityProfiles)
    .where(eq(legalEntityProfiles.workspaceId, workspaceId));

  return rows.map((r) => ({
    id: String(r.id),
    workspaceId: String(r.workspaceId),
    entityType: r.entityType,
    status: r.status as LegalStatus,
    registrationNumber: r.registrationNumber,
    taxId: r.taxId,
    verifiedAt: r.verifiedAt ? r.verifiedAt.toISOString() : null,  }));
}

export async function createLegalEntityProfile(p: {
  workspaceId: bigint;
  entityType: string;
  registrationNumber?: string;
  taxId?: string;
}): Promise<LegalEntityProfileView> {
  const newId = generateSnowflake();
  const initialStatus: LegalStatus = p.registrationNumber
    ? "REGISTERED_UNVERIFIED"
    : "DRAFT";

  const [created] = await db
    .insert(legalEntityProfiles)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      entityType: p.entityType,
      status: initialStatus,
      registrationNumber: p.registrationNumber ?? null,
      taxId: p.taxId ?? null,
    })
    .returning();

  return {
    id: String(created.id),
    workspaceId: String(created.workspaceId),
    entityType: created.entityType,
    status: created.status as LegalStatus,
    registrationNumber: created.registrationNumber,
    taxId: created.taxId,
    verifiedAt: null,  };
}

export async function requestVerification(p: {
  profileId: bigint;
  workspaceId: bigint;
  actorMemberId: bigint;
  rationale?: string;
}): Promise<{ approvalId: string; status: "PENDING_APPROVAL"; expiresAt: string }> {
  return await db.transaction(async (tx) => {
    // Resolve profile TRONG workspace của ctx — không fetch-global-rồi-so-sánh.
    const [profile] = await tx
      .select()
      .from(legalEntityProfiles)
      .where(
        and(
          eq(legalEntityProfiles.id, p.profileId),
          eq(legalEntityProfiles.workspaceId, p.workspaceId)
        )
      );

    if (!profile) {
      throw APIError.notFound(`Legal entity profile '${p.profileId}' not found`);
    }

    // Request verification bắt buộc có định danh đăng ký (spec §4.5).
    if (!profile.registrationNumber) {
      throw APIError.failedPrecondition(
        "Legal entity must have a registration number before verification can be requested"
      );
    }
    if (profile.status === VERIFICATION_EXPECTED_STATUS) {
      throw APIError.failedPrecondition("Legal entity is already verified");
    }

    // Tái dùng approval PENDING còn hiệu lực nếu đã có (partial unique index bảo đảm tối đa 1).
    const [existing] = await tx
      .select()
      .from(legalVerificationApprovals)
      .where(
        and(
          eq(legalVerificationApprovals.workspaceId, p.workspaceId),
          eq(legalVerificationApprovals.legalEntityId, p.profileId),
          eq(legalVerificationApprovals.expectedStatus, VERIFICATION_EXPECTED_STATUS),
          eq(legalVerificationApprovals.status, "PENDING")
        )
      );
    if (existing) {
      if (existing.expiresAt.getTime() > Date.now()) {
        return {
          approvalId: String(existing.id),
          status: "PENDING_APPROVAL" as const,
          expiresAt: existing.expiresAt.toISOString(),
        };
      }
      // approval cũ đã hết hạn — đánh dấu EXPIRED rồi tạo cái mới.
      await tx
        .update(legalVerificationApprovals)
        .set({ status: "EXPIRED", decidedAt: new Date(), updatedAt: new Date() })
        .where(eq(legalVerificationApprovals.id, existing.id));
    }

    const now = new Date();
    const expiresAt = new Date(now.getTime() + APPROVAL_TTL_MS);
    const [created] = await tx
      .insert(legalVerificationApprovals)
      .values({
        id: generateSnowflake(),
        workspaceId: p.workspaceId,
        legalEntityId: p.profileId,
        expectedStatus: VERIFICATION_EXPECTED_STATUS,
        requestedBy: p.actorMemberId,
        status: "PENDING",
        requestedAt: now,
        expiresAt,
        rationale: p.rationale ?? null,
      })
      .returning();

    await tx
      .update(legalEntityProfiles)
      .set({
        status: "REGISTERED_UNVERIFIED",
        updatedAt: now,
      })
      .where(
        and(
          eq(legalEntityProfiles.id, p.profileId),
          eq(legalEntityProfiles.workspaceId, p.workspaceId)
        )
      );

    return {
      approvalId: String(created.id),
      status: "PENDING_APPROVAL" as const,
      expiresAt: expiresAt.toISOString(),
    };
  });
}

export async function applyVerification(p: {
  profileId: bigint;
  workspaceId: bigint;
  approvalId: string;
  approverMemberId: bigint;
}): Promise<LegalEntityProfileView> {
  let approvalId: bigint;
  try {
    approvalId = BigInt(p.approvalId);
  } catch {
    throw APIError.permissionDenied("Invalid approval reference for legal verification");
  }

  // Validate approval NGOÀI write-transaction: nếu throw ở trong tx thì việc đánh dấu
  // EXPIRED cũng bị rollback. Đọc + kiểm tra + đánh dấu EXPIRED bằng statement autocommit.
  const [approval] = await db
    .select()
    .from(legalVerificationApprovals)
    .where(eq(legalVerificationApprovals.id, approvalId));

  // Không tiết lộ khác biệt "không tồn tại" vs "workspace khác".
  if (!approval || approval.workspaceId !== p.workspaceId) {
    throw APIError.permissionDenied("Approval not found or not bound to this workspace");
  }
  if (approval.legalEntityId !== p.profileId) {
    throw APIError.permissionDenied("Approval is not bound to this legal entity");
  }
  if (approval.expectedStatus !== VERIFICATION_EXPECTED_STATUS) {
    throw APIError.permissionDenied("Approval does not authorize this transition");
  }
  if (approval.status !== "PENDING") {
    throw APIError.failedPrecondition(`Approval is ${approval.status}, not PENDING`);
  }
  if (approval.expiresAt.getTime() <= Date.now()) {
    await db
      .update(legalVerificationApprovals)
      .set({ status: "EXPIRED", decidedAt: new Date(), updatedAt: new Date() })
      .where(eq(legalVerificationApprovals.id, approval.id));
    throw APIError.failedPrecondition("Approval has expired");
  }
  // Separation of duty: người duyệt ≠ người xin.
  if (approval.requestedBy === p.approverMemberId) {
    throw APIError.permissionDenied(
      "Approver must be different from the requester (separation of duty)"
    );
  }

  return await db.transaction(async (tx) => {
    // Re-check PENDING trong transaction để chống race (double confirm đồng thời).
    const upd = await tx
      .update(legalVerificationApprovals)
      .set({
        status: "APPROVED",
        approvedBy: p.approverMemberId,
        decidedAt: new Date(),
        updatedAt: new Date(),
      })
      .where(
        and(
          eq(legalVerificationApprovals.id, approval.id),
          eq(legalVerificationApprovals.status, "PENDING")
        )
      )
      .returning();
    if (upd.length === 0) {
      throw APIError.failedPrecondition("Approval is no longer PENDING");
    }

    const [profile] = await tx
      .select()
      .from(legalEntityProfiles)
      .where(
        and(
          eq(legalEntityProfiles.id, p.profileId),
          eq(legalEntityProfiles.workspaceId, p.workspaceId)
        )
      );

    if (!profile) {
      throw APIError.notFound(`Legal entity profile '${p.profileId}' not found`);
    }

    const verifiedAt = new Date();

    const [updated] = await tx
      .update(legalEntityProfiles)
      .set({
        status: "VERIFIED",
        verifiedByMemberId: p.approverMemberId,
        verifiedAt,
        updatedAt: verifiedAt,
      })
      .where(
        and(
          eq(legalEntityProfiles.id, p.profileId),
          eq(legalEntityProfiles.workspaceId, p.workspaceId)
        )
      )
      .returning();

    const event = makeBusinessEvent({
      eventType: LEGAL_STATUS_CHANGED,
      workspaceId: String(updated.workspaceId),
      aggregateType: "legal_entity_profile",
      aggregateId: String(updated.id),
      correlationId: randomUUID(),
      actor: {
        kind: "user",
        id: String(p.approverMemberId),
      },
      classification: "internal",
      payload: {
        workspaceId: String(updated.workspaceId),
        profileId: String(updated.id),
        fromStatus: profile.status,
        toStatus: "VERIFIED",
        verifiedAt: verifiedAt.toISOString(),
      },
    });

    await appendOutboxEvent(tx, event);

    return {
      id: String(updated.id),
      workspaceId: String(updated.workspaceId),
      entityType: updated.entityType,
      status: "VERIFIED",
      registrationNumber: updated.registrationNumber,
      taxId: updated.taxId,
      verifiedAt: verifiedAt.toISOString(),    };
  });
}
