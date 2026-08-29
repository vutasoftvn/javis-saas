import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { bankConnections } = schema;

export interface BankConnectionView {
  id: string;
  workspaceId: string;
  provider: "cas" | "manual";
  consentState: "PENDING" | "GRANTED" | "REVOKED" | "EXPIRED";
  secretRef: string | null;
  scopes: string[];
  syncStatus: string;
  lastSyncedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export async function listBankConnectionsService(
  workspaceId: bigint
): Promise<BankConnectionView[]> {
  const rows = await db
    .select()
    .from(bankConnections)
    .where(eq(bankConnections.workspaceId, workspaceId));

  return rows.map((r) => ({
    id: String(r.id),
    workspaceId: String(r.workspaceId),
    provider: r.provider as any,
    consentState: r.consentState as any,
    secretRef: r.secretRef,
    scopes: (r.scopes || []) as string[],
    syncStatus: r.syncStatus,
    lastSyncedAt: r.lastSyncedAt ? r.lastSyncedAt.toISOString() : null,
    createdAt: r.createdAt.toISOString(),
    updatedAt: r.updatedAt.toISOString(),
  }));
}

export async function createBankConnectionService(p: {
  workspaceId: bigint;
  provider: "cas" | "manual";
  secretRef?: string;
  scopes?: string[];
}): Promise<BankConnectionView> {
  if (p.secretRef && !p.secretRef.startsWith("secret://cosa-connectors/")) {
    throw APIError.invalidArgument(
      "Raw tokens are strictly forbidden. secretRef must match 'secret://cosa-connectors/%'"
    );
  }

  const newId = generateSnowflake();
  const [created] = await db
    .insert(bankConnections)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      provider: p.provider,
      consentState: "PENDING",
      secretRef: p.secretRef ?? null,
      scopes: (p.scopes || []) as any,
    })
    .returning();

  return {
    id: String(created.id),
    workspaceId: String(created.workspaceId),
    provider: created.provider as any,
    consentState: created.consentState as any,
    secretRef: created.secretRef,
    scopes: (created.scopes || []) as string[],
    syncStatus: created.syncStatus,
    lastSyncedAt: null,
    createdAt: created.createdAt.toISOString(),
    updatedAt: created.updatedAt.toISOString(),
  };
}

export async function updateConsentStateService(p: {
  connectionId: bigint;
  consentState: "PENDING" | "GRANTED" | "REVOKED" | "EXPIRED";
}): Promise<BankConnectionView> {
  const [updated] = await db
    .update(bankConnections)
    .set({
      consentState: p.consentState,
      updatedAt: new Date(),
    })
    .where(eq(bankConnections.id, p.connectionId))
    .returning();

  if (!updated) {
    throw APIError.notFound(`Bank connection '${p.connectionId}' not found`);
  }

  return {
    id: String(updated.id),
    workspaceId: String(updated.workspaceId),
    provider: updated.provider as any,
    consentState: updated.consentState as any,
    secretRef: updated.secretRef,
    scopes: (updated.scopes || []) as string[],
    syncStatus: updated.syncStatus,
    lastSyncedAt: updated.lastSyncedAt ? updated.lastSyncedAt.toISOString() : null,
    createdAt: updated.createdAt.toISOString(),
    updatedAt: updated.updatedAt.toISOString(),
  };
}
