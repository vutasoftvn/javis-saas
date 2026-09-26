import { eq } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db } from "../../models/db";
import { ventureProfiles } from "../../../shared/db/schema/strategy";
import { generateSnowflake } from "../../../shared/services/snowflake.service";

// Hồ sơ khởi nghiệp cấp workspace (1 dòng/workspace, bootstrap rỗng khi sync
// membership). Agent đọc qua venture.profile.read để có ngữ cảnh ngành, khách
// hàng mục tiêu, runway khi tư vấn.
export interface VentureProfileView {
  workspaceId: string;
  problemStatement: string | null;
  targetCustomer: string | null;
  industry: string | null;
  geography: string | null;
  currency: string | null;
  timezone: string | null;
  founderGoal: string | null;
  initialRunwayMonths: number | null;
  updatedAt: string | null;
}

// undefined/null = giữ nguyên giá trị cũ; chuỗi rỗng = xoá trường text.
export interface VentureProfileUpdate {
  problemStatement?: string | null;
  targetCustomer?: string | null;
  industry?: string | null;
  geography?: string | null;
  currency?: string | null;
  timezone?: string | null;
  founderGoal?: string | null;
  initialRunwayMonths?: number | null;
}

const MAX_TEXT_LENGTH = 2000;
const FOUNDER_GOAL_MAX_LENGTH = 50;

type VentureProfileRow = typeof ventureProfiles.$inferSelect;

function toView(workspaceId: bigint, row: VentureProfileRow | undefined): VentureProfileView {
  return {
    workspaceId: String(workspaceId),
    problemStatement: row?.problemStatement ?? null,
    targetCustomer: row?.targetCustomer ?? null,
    industry: row?.industry ?? null,
    geography: row?.geography ?? null,
    currency: row?.currency ?? null,
    timezone: row?.timezone ?? null,
    founderGoal: row?.founderGoal ?? null,
    initialRunwayMonths: row?.initialRunwayMonths ?? null,
    updatedAt: row ? row.updatedAt.toISOString() : null,
  };
}

function normalizeText(
  value: string | null | undefined,
  field: string,
  maxLength: number
): string | null | undefined {
  if (value === undefined || value === null) return undefined;
  if (typeof value !== "string") {
    throw APIError.invalidArgument(`${field} must be a string`);
  }
  const trimmed = value.trim();
  if (trimmed.length > maxLength) {
    throw APIError.invalidArgument(`${field} must be at most ${maxLength} characters`);
  }
  return trimmed === "" ? null : trimmed;
}

export async function getVentureProfileService(workspaceId: bigint): Promise<VentureProfileView> {
  const [row] = await db
    .select()
    .from(ventureProfiles)
    .where(eq(ventureProfiles.workspaceId, workspaceId));
  return toView(workspaceId, row);
}

export async function updateVentureProfileService(
  workspaceId: bigint,
  input: VentureProfileUpdate
): Promise<VentureProfileView> {
  const changes: Partial<typeof ventureProfiles.$inferInsert> = {};
  const textFields = [
    "problemStatement",
    "targetCustomer",
    "industry",
    "geography",
    "currency",
    "timezone",
  ] as const;
  for (const field of textFields) {
    const value = normalizeText(input[field], field, MAX_TEXT_LENGTH);
    if (value !== undefined) changes[field] = value;
  }
  const founderGoal = normalizeText(input.founderGoal, "founderGoal", FOUNDER_GOAL_MAX_LENGTH);
  if (founderGoal !== undefined) changes.founderGoal = founderGoal;

  const runway = input.initialRunwayMonths;
  if (runway !== undefined && runway !== null) {
    if (!Number.isInteger(runway) || runway < 0 || runway > 600) {
      throw APIError.invalidArgument("initialRunwayMonths must be an integer between 0 and 600");
    }
    changes.initialRunwayMonths = runway;
  }

  if (Object.keys(changes).length === 0) {
    throw APIError.invalidArgument("no venture profile field to update");
  }

  const now = new Date();
  const [row] = await db
    .insert(ventureProfiles)
    .values({
      id: generateSnowflake(),
      workspaceId,
      stageEnteredAt: now,
      ...changes,
    })
    .onConflictDoUpdate({
      target: ventureProfiles.workspaceId,
      set: { ...changes, updatedAt: now },
    })
    .returning();
  return toView(workspaceId, row);
}
