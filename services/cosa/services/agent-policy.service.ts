import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { createHash } from "crypto";
import { db, schema } from "../models/db";
import { generateSnowflake } from "./snowflake.service";
import { verifyWorkspaceMembership } from "./workspace-connector.service";

const { companyAgentPolicy, companies, companyMemberships, users } = schema;

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

export interface TenantPolicyRule {
  toolPattern: string;
  decision: TenantPolicyDecision;
  reason: string | null;
}

export interface TenantPolicySnapshotResult {
  workspaceId: string;
  workspaceStatus: string;
  principalStatus: string;
  rules: TenantPolicyRule[];
  snapshotHash: string;
}

/**
 * Trả toàn bộ `cosa.company_agent_policy` rows của 1 company + trạng thái
 * workspace/user hiện tại — 1 lần resolve tại boundary (run-start/trước
 * resume) thay vì gọi lại `getTenantPolicyForTool` mỗi tool call. Bắt buộc
 * verify caller thực sự là thành viên của workspace (qua services/company
 * endpoint) trước khi trả policy của underlying company (nếu tồn tại).
 * Workspace không có platform company => trả rules: [] (local-only workspace).
 */
export async function getTenantPolicySnapshotForCaller(
  userIdStr: string,
  workspaceId: string,
  authorizationHeader?: string
): Promise<TenantPolicySnapshotResult> {
  const userId = BigInt(userIdStr);

  const [userRow] = await db.select({ status: users.status }).from(users).where(eq(users.id, userId)).limit(1);
  if (!userRow) {
    throw APIError.notFound("platform user không tồn tại");
  }

  // Resolve workspace → platform_company_id via services/company endpoint
  // This also verifies workspace membership (throws if not a member)
  const membershipInfo = await verifyWorkspaceMembership(workspaceId, authorizationHeader);
  const platformCompanyId = membershipInfo.platformCompanyId;

  // Local-only workspace (no platform company): return empty rules
  if (!platformCompanyId) {
    const snapshotHash = createHash("sha256")
      .update(JSON.stringify({ workspaceStatus: "active", principalStatus: userRow.status, rules: [] }))
      .digest("hex");

    return {
      workspaceId,
      workspaceStatus: "active",
      principalStatus: userRow.status,
      rules: [],
      snapshotHash,
    };
  }

  // Workspace linked to platform company: lookup policy rules
  const companyIdBig = BigInt(platformCompanyId);
  const policyRows = await db
    .select({
      toolPattern: companyAgentPolicy.toolPattern,
      decision: companyAgentPolicy.decision,
      reason: companyAgentPolicy.reason,
    })
    .from(companyAgentPolicy)
    .where(eq(companyAgentPolicy.companyId, companyIdBig));

  const rules: TenantPolicyRule[] = policyRows.map((r) => ({
    toolPattern: r.toolPattern,
    decision: r.decision as TenantPolicyDecision,
    reason: r.reason,
  }));

  const snapshotHash = createHash("sha256")
    .update(JSON.stringify({ workspaceStatus: "active", principalStatus: userRow.status, rules }))
    .digest("hex");

  return {
    workspaceId,
    workspaceStatus: "active",
    principalStatus: userRow.status,
    rules,
    snapshotHash,
  };
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
