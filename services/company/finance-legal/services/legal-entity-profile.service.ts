import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { LEGAL_STATUS_CHANGED } from "../../shared/events";
import { randomUUID } from "node:crypto";

const { legalEntityProfiles } = schema;

export type LegalStatus =
  | "NOT_DECLARED"
  | "UNREGISTERED"
  | "REGISTRATION_READINESS"
  | "REGISTERED_PENDING_VERIFICATION"
  | "REGISTERED_VERIFIED";

export interface LegalEntityProfileView {
  id: string;
  workspaceId: string;
  entityType: string;
  status: LegalStatus;
  registrationNumber: string | null;
  taxId: string | null;
  verifiedAt: string | null;
  platformCompanyId: string | null;
}

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
    verifiedAt: r.verifiedAt ? r.verifiedAt.toISOString() : null,
    platformCompanyId: r.platformCompanyId,
  }));
}

export async function createLegalEntityProfile(p: {
  workspaceId: bigint;
  entityType: string;
  registrationNumber?: string;
  taxId?: string;
}): Promise<LegalEntityProfileView> {
  const newId = generateSnowflake();
  const initialStatus: LegalStatus = p.registrationNumber
    ? "REGISTRATION_READINESS"
    : "UNREGISTERED";

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
    verifiedAt: null,
    platformCompanyId: created.platformCompanyId,
  };
}

export async function requestVerification(p: {
  profileId: bigint;
  actorMemberId: bigint;
}): Promise<{ approvalId: string; status: "PENDING_APPROVAL" }> {
  const [profile] = await db
    .select()
    .from(legalEntityProfiles)
    .where(eq(legalEntityProfiles.id, p.profileId));

  if (!profile) {
    throw APIError.notFound(`Legal entity profile '${p.profileId}' not found`);
  }

  await db
    .update(legalEntityProfiles)
    .set({
      status: "REGISTERED_PENDING_VERIFICATION",
      updatedAt: new Date(),
    })
    .where(eq(legalEntityProfiles.id, p.profileId));

  const approvalId = `appr_legal_${randomUUID().replace(/-/g, "").slice(0, 16)}`;
  return {
    approvalId,
    status: "PENDING_APPROVAL",
  };
}

export async function applyVerification(p: {
  profileId: bigint;
  approvalId: string;
  approverMemberId: bigint;
}): Promise<LegalEntityProfileView> {
  if (!p.approvalId || !p.approvalId.startsWith("appr_legal_")) {
    throw APIError.permissionDenied("Invalid or unbound approval ID for legal verification");
  }

  return await db.transaction(async (tx) => {
    const [profile] = await tx
      .select()
      .from(legalEntityProfiles)
      .where(eq(legalEntityProfiles.id, p.profileId));

    if (!profile) {
      throw APIError.notFound(`Legal entity profile '${p.profileId}' not found`);
    }

    const verifiedAt = new Date();
    const [updated] = await tx
      .update(legalEntityProfiles)
      .set({
        status: "REGISTERED_VERIFIED",
        verifiedByMemberId: p.approverMemberId,
        verifiedAt,
        updatedAt: verifiedAt,
      })
      .where(eq(legalEntityProfiles.id, p.profileId))
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
        toStatus: "REGISTERED_VERIFIED",
        verifiedAt: verifiedAt.toISOString(),
      },
    });

    await appendOutboxEvent(tx, event);

    return {
      id: String(updated.id),
      workspaceId: String(updated.workspaceId),
      entityType: updated.entityType,
      status: "REGISTERED_VERIFIED",
      registrationNumber: updated.registrationNumber,
      taxId: updated.taxId,
      verifiedAt: verifiedAt.toISOString(),
      platformCompanyId: updated.platformCompanyId,
    };
  });
}
