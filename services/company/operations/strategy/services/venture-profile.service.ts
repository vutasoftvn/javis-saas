import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db } from "../../models/db";
import { ventureProfiles } from "../../../shared/db/schema/strategy";
import { generateSnowflake } from "../../../shared/services/snowflake.service";


export interface VentureProfileView {
  id: string;
  workspaceId: string;
  problemStatement: string | null;
  targetCustomer: string | null;
  industry: string | null;
  geography: string | null;
  currency: string;
  timezone: string;
  founderGoal: string | null;
  initialRunwayMonths: number | null;
  createdAt: string;
  updatedAt: string;
}

export async function getVentureProfileService(
  workspaceId: bigint
): Promise<VentureProfileView | null> {
  const [profile] = await db
    .select()
    .from(ventureProfiles)
    .where(eq(ventureProfiles.workspaceId, workspaceId))
    .limit(1);

  if (!profile) return null;

  return {
    id: String(profile.id),
    workspaceId: String(profile.workspaceId),
    problemStatement: profile.problemStatement,
    targetCustomer: profile.targetCustomer,
    industry: profile.industry,
    geography: profile.geography,
    currency: profile.currency || "VND",
    timezone: profile.timezone || "Asia/Ho_Chi_Minh",
    founderGoal: profile.founderGoal,
    initialRunwayMonths: profile.initialRunwayMonths,
    createdAt: profile.createdAt.toISOString(),
    updatedAt: profile.updatedAt.toISOString(),
  };
}

export async function upsertVentureProfileService(p: {
  workspaceId: bigint;
  problemStatement?: string;
  targetCustomer?: string;
  industry?: string;
  geography?: string;
  currency?: string;
  timezone?: string;
  founderGoal?: string;
  initialRunwayMonths?: number;
}): Promise<VentureProfileView> {
  const existing = await db
    .select()
    .from(ventureProfiles)
    .where(eq(ventureProfiles.workspaceId, p.workspaceId))
    .limit(1);

  if (existing.length > 0) {
    const [updated] = await db
      .update(ventureProfiles)
      .set({
        problemStatement:
          p.problemStatement !== undefined ? p.problemStatement : existing[0].problemStatement,
        targetCustomer:
          p.targetCustomer !== undefined ? p.targetCustomer : existing[0].targetCustomer,
        industry: p.industry !== undefined ? p.industry : existing[0].industry,
        geography: p.geography !== undefined ? p.geography : existing[0].geography,
        currency: p.currency !== undefined ? p.currency : existing[0].currency,
        timezone: p.timezone !== undefined ? p.timezone : existing[0].timezone,
        founderGoal: p.founderGoal !== undefined ? p.founderGoal : existing[0].founderGoal,
        initialRunwayMonths:
          p.initialRunwayMonths !== undefined
            ? p.initialRunwayMonths
            : existing[0].initialRunwayMonths,
        updatedAt: new Date(),
      })
      .where(eq(ventureProfiles.workspaceId, p.workspaceId))
      .returning();

    return {
      id: String(updated.id),
      workspaceId: String(updated.workspaceId),
      problemStatement: updated.problemStatement,
      targetCustomer: updated.targetCustomer,
      industry: updated.industry,
      geography: updated.geography,
      currency: updated.currency || "VND",
      timezone: updated.timezone || "Asia/Ho_Chi_Minh",
      founderGoal: updated.founderGoal,
      initialRunwayMonths: updated.initialRunwayMonths,
      createdAt: updated.createdAt.toISOString(),
      updatedAt: updated.updatedAt.toISOString(),
    };
  }

  const newId = generateSnowflake();
  const [created] = await db
    .insert(ventureProfiles)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      problemStatement: p.problemStatement || null,
      targetCustomer: p.targetCustomer || null,
      industry: p.industry || null,
      geography: p.geography || null,
      currency: p.currency || "VND",
      timezone: p.timezone || "Asia/Ho_Chi_Minh",
      founderGoal: p.founderGoal || null,
      initialRunwayMonths: p.initialRunwayMonths || null,
    })
    .returning();

  return {
    id: String(created.id),
    workspaceId: String(created.workspaceId),
    problemStatement: created.problemStatement,
    targetCustomer: created.targetCustomer,
    industry: created.industry,
    geography: created.geography,
    currency: created.currency || "VND",
    timezone: created.timezone || "Asia/Ho_Chi_Minh",
    founderGoal: created.founderGoal,
    initialRunwayMonths: created.initialRunwayMonths,
    createdAt: created.createdAt.toISOString(),
    updatedAt: created.updatedAt.toISOString(),
  };
}
