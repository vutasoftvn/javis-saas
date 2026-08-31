import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { createHash } from "crypto";
import { db, schema } from "../models/db";
import { generateSnowflake } from "./snowflake.service";
import { verifyWorkspaceMembership } from "./workspace-connector.service";

const { workspaceAgentPolicy, users } = schema;

export type TenantPolicyDecision = "ALLOW" | "REQUIRE_APPROVAL" | "DENY";

export interface GetTenantPolicyParams {
  workspaceId?: string;
  companyId?: string;
  toolName: string;
}

export interface GetTenantPolicyResult {
  decision: TenantPolicyDecision | null;
  matchedPattern: string | null;
  reason: string | null;
}

export interface UpsertTenantPolicyParams {
  workspaceId?: string;
  companyId?: string;
  toolPattern: string;
  decision: TenantPolicyDecision;
  reason?: string;
}

/**
 * Khớp `tool_pattern` theo thứ tự ưu tiên: exact match tên tool trước, sau đó
 * wildcard prefix (ví dụ `commercial.*` khớp `commercial.lead.create`), cuối
 * cùng `*` (áp dụng cho mọi tool). Workspace chưa cấu hình policy nào -> trả
 * `decision: null` (agentos coi là "không có tenant policy", không phải DENY).
 */
export async function getTenantPolicyForTool(params: GetTenantPolicyParams): Promise<GetTenantPolicyResult> {
  const rawId = params.workspaceId || params.companyId;
  if (!rawId) {
    return { decision: null, matchedPattern: null, reason: null };
  }
  const workspaceIdBig = BigInt(rawId);
  const rows = await db
    .select()
    .from(workspaceAgentPolicy)
    .where(eq(workspaceAgentPolicy.workspaceId, workspaceIdBig));

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
 * Trả toàn bộ `cosa.workspace_agent_policy` rows của 1 workspace + trạng thái
 * workspace/user hiện tại — 1 lần resolve tại boundary (run-start/trước
 * resume) thay vì gọi lại `getTenantPolicyForTool` mỗi tool call.
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

  // Verify workspace membership (throws if not a member)
  await verifyWorkspaceMembership(workspaceId, authorizationHeader);

  const workspaceIdBig = BigInt(workspaceId);
  const policyRows = await db
    .select({
      toolPattern: workspaceAgentPolicy.toolPattern,
      decision: workspaceAgentPolicy.decision,
      reason: workspaceAgentPolicy.reason,
    })
    .from(workspaceAgentPolicy)
    .where(eq(workspaceAgentPolicy.workspaceId, workspaceIdBig));

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
  const rawId = params.workspaceId || params.companyId;
  if (!rawId) {
    throw APIError.invalidArgument("workspaceId hoặc companyId là bắt buộc");
  }
  const workspaceIdBig = BigInt(rawId);
  const existing = await db
    .select()
    .from(workspaceAgentPolicy)
    .where(and(eq(workspaceAgentPolicy.workspaceId, workspaceIdBig), eq(workspaceAgentPolicy.toolPattern, params.toolPattern)));

  if (existing.length > 0) {
    await db
      .update(workspaceAgentPolicy)
      .set({ decision: params.decision, reason: params.reason ?? null, updatedAt: new Date() })
      .where(eq(workspaceAgentPolicy.id, existing[0].id));
    return;
  }

  await db.insert(workspaceAgentPolicy).values({
    id: generateSnowflake(),
    workspaceId: workspaceIdBig,
    toolPattern: params.toolPattern,
    decision: params.decision,
    reason: params.reason ?? null,
  });
}


