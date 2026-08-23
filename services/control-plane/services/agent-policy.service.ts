import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "./snowflake.service";

const { companyAgentPolicy } = schema;

export type TenantPolicyDecision = "ALLOW" | "REQUIRE_APPROVAL" | "DENY";

export interface GetTenantPolicyParams {
  companyId: string;
  toolName: string;
}

export interface GetTenantPolicyResult {
  decision: TenantPolicyDecision | null;
  matchedPattern: string | null;
  reason: string | null;
}

export interface UpsertTenantPolicyParams {
  companyId: string;
  toolPattern: string;
  decision: TenantPolicyDecision;
  reason?: string;
}

/**
 * Khớp `tool_pattern` theo thứ tự ưu tiên: exact match tên tool trước, sau đó
 * wildcard prefix (ví dụ `commercial.*` khớp `commercial.lead.create`), cuối
 * cùng `*` (áp dụng cho mọi tool). Company chưa cấu hình policy nào -> trả
 * `decision: null` (agentos coi là "không có tenant policy", không phải DENY).
 */
export async function getTenantPolicyForTool(params: GetTenantPolicyParams): Promise<GetTenantPolicyResult> {
  const companyIdBig = BigInt(params.companyId);
  const rows = await db
    .select()
    .from(companyAgentPolicy)
    .where(eq(companyAgentPolicy.companyId, companyIdBig));

  if (rows.length === 0) {
    return { decision: null, matchedPattern: null, reason: null };
  }

  const exact = rows.find((r) => r.toolPattern === params.toolName);
  if (exact) {
    return { decision: exact.decision as TenantPolicyDecision, matchedPattern: exact.toolPattern, reason: exact.reason };
  }

  const prefixMatches = rows
    .filter((r) => r.toolPattern.endsWith(".*") && params.toolName.startsWith(r.toolPattern.slice(0, -1)))
    .sort((a, b) => b.toolPattern.length - a.toolPattern.length);
  if (prefixMatches.length > 0) {
    const match = prefixMatches[0];
    return { decision: match.decision as TenantPolicyDecision, matchedPattern: match.toolPattern, reason: match.reason };
  }

  const wildcard = rows.find((r) => r.toolPattern === "*");
  if (wildcard) {
    return { decision: wildcard.decision as TenantPolicyDecision, matchedPattern: "*", reason: wildcard.reason };
  }

  return { decision: null, matchedPattern: null, reason: null };
}

export async function upsertTenantPolicy(params: UpsertTenantPolicyParams): Promise<void> {
  const companyIdBig = BigInt(params.companyId);
  const existing = await db
    .select()
    .from(companyAgentPolicy)
    .where(and(eq(companyAgentPolicy.companyId, companyIdBig), eq(companyAgentPolicy.toolPattern, params.toolPattern)));

  if (existing.length > 0) {
    await db
      .update(companyAgentPolicy)
      .set({ decision: params.decision, reason: params.reason ?? null, updatedAt: new Date() })
      .where(eq(companyAgentPolicy.id, existing[0].id));
    return;
  }

  await db.insert(companyAgentPolicy).values({
    id: generateSnowflake(),
    companyId: companyIdBig,
    toolPattern: params.toolPattern,
    decision: params.decision,
    reason: params.reason ?? null,
  });
}
