import { api, APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";

const { accountingProfiles } = schema;

export interface AccountingProfile {
  id: number;
  workspaceId: number;
  mode: string;
  status: string;
  confirmedBy: number | null;
  confirmedAt: string | null;
  createdAt: string;
}

export interface CreateAccountingProfileParams {
  workspaceId: number;
  mode?: string;
}

export const createAccountingProfile = api(
  { method: "POST", path: "/finance-legal/accounting-profiles", expose: true },
  async (params: CreateAccountingProfileParams): Promise<AccountingProfile> => {
    await getWorkspace({ id: params.workspaceId });

    const [row] = await db
      .insert(accountingProfiles)
      .values({
        workspaceId: BigInt(params.workspaceId),
        mode: params.mode ?? "TT58_MODE_1",
      })
      .returning();

    if (!row) throw APIError.internal("failed to create accounting profile");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      mode: row.mode,
      status: row.status,
      confirmedBy: row.confirmedBy ? Number(row.confirmedBy) : null,
      confirmedAt: row.confirmedAt ? row.confirmedAt.toISOString() : null,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const getAccountingProfileByWorkspace = api(
  { method: "GET", path: "/finance-legal/accounting-profiles/by-workspace/:workspaceId", expose: true },
  async ({ workspaceId }: { workspaceId: number }): Promise<AccountingProfile> => {
    const [row] = await db
      .select()
      .from(accountingProfiles)
      .where(eq(accountingProfiles.workspaceId, BigInt(workspaceId)))
      .limit(1);

    if (!row) throw APIError.notFound(`no accounting profile for workspace ${workspaceId}`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      mode: row.mode,
      status: row.status,
      confirmedBy: row.confirmedBy ? Number(row.confirmedBy) : null,
      confirmedAt: row.confirmedAt ? row.confirmedAt.toISOString() : null,
      createdAt: row.createdAt.toISOString(),
    };
  }
);
