import { and, asc, eq } from "drizzle-orm";
import { identityWorkforceMembers } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";

export type OwnerAgentProfile =
  | "operations"
  | "finance"
  | "marketing"
  | "research_intelligence"
  | "strategy"
  | "customer_support"
  | "sales"
  | "coding"
  | "product"
  | "people"
  | "security"
  | "legal"
  | "data"
  | "ai_governance";

// AgentSpec id theo apps/cosa/agents/specs.py (COSA_*_AGENT_SPEC.id).
export const AGENT_PROFILE_SPEC_ID: Record<OwnerAgentProfile, string> = {
  operations: "cosa.agents.operations",
  finance: "cosa.agents.finance",
  marketing: "cosa.agents.marketing",
  research_intelligence: "cosa.agents.research_intelligence",
  strategy: "cosa.agents.strategy",
  customer_support: "cosa.agents.customer_support",
  sales: "cosa.agents.sales",
  coding: "cosa.agents.coding",
  product: "cosa.agents.product",
  people: "cosa.agents.people",
  security: "cosa.agents.security",
  legal: "cosa.agents.legal",
  data: "cosa.agents.data",
  ai_governance: "cosa.agents.ai_governance",
};

// Metadata mô tả (constraint workforce_members yêu cầu agent_spec_version NOT NULL
// cho AI_AGENT).
export const AGENT_PROFILE_SPEC_VERSION: Record<OwnerAgentProfile, string> = {
  operations: "1.4.0",
  finance: "1.2.0",
  marketing: "1.2.0",
  research_intelligence: "1.1.0",
  strategy: "1.1.0",
  customer_support: "1.2.0",
  sales: "1.1.0",
  coding: "1.1.0",
  product: "1.2.0",
  people: "1.1.0",
  security: "1.1.0",
  legal: "1.1.0",
  data: "1.1.0",
  ai_governance: "1.0.0",
};

// Pinned definition_hash theo specs.py AgentSpec.compute_hash().
export const AGENT_PROFILE_SPEC_HASH: Record<OwnerAgentProfile, string> = {
  operations: "45ea0896d4de7301e4aff6c5e6182a29f23cfbb02379e0d3d4f46c1485f71ab3",
  finance: "7c8bab30f70b75e856a5a3a4c83687047bda08988f58e8c498c455e362a4fc78",
  marketing: "f4d95277b345b7e172d878bc83961955ae6c364dafb9d3a033a39c20ee5908c5",
  research_intelligence: "fc98ddd07d96fb31e7feee056554ee0015b7103b707f1a205fb54d86531ab4b6",
  strategy: "37b4f3b506d2eeb6b81e619f91428f0c30a72a68fe32c81691b98f68939c0d69",
  customer_support: "71fbf6cfccd3299367ad88e68866e53fd488d406c7d74bd0fbaef472731e15aa",
  sales: "3604eb24d4ddd9f45c55253c4a72e37ca271e4128833ac9be1d23abba11633d2",
  coding: "f9159d1d697d3a1483c388c6b8dc36c451d820d784230e0559be0cf364dec5b6",
  product: "820f0a5a020da30f322a120aec8106d327a8f7ebeb4edeae3115eab6a586a303",
  people: "c8f2e66c267071113ce309becf3c93d0162e1f4e751dcb667b49e4898454146f",
  security: "74e66e486eca6fddcfa5dba081334a6073a3033b77b207daca04eaaff076cb2d",
  legal: "7b5800e439d40f635de343c0b0ad934d17eb833c3fcccb5a6e1aaed6749c447d",
  data: "a6dc3b9771e8b394898ed656593e1d1b8b819c61432cc8eed9263e04c0f8edd7",
  ai_governance: "5cea97aae46c8c872708356cd7b52195760b9dfc62969b40b96bd2ba77f15f99",
};

// Drizzle transaction type — cùng cách project-kickoff-materialize.service.ts đặt tên.
type Tx = Parameters<Parameters<typeof import("../models/db").db.transaction>[0]>[0];

export interface AssetIdentityInput {
  specId: string;
  specVersion: string;
  definitionHash?: string;
  title?: string;
}

/**
 * Đảm bảo workspace có đúng 1 workforce member kiểu AI_AGENT cho asset spec & version.
 * Idempotent: tìm theo (workspaceId, memberType='AI_AGENT', agentSpecId, agentSpecVersion).
 */
export async function ensureAiWorkforceMemberForAsset(
  tx: Tx,
  workspaceId: string,
  asset: AssetIdentityInput
): Promise<string> {
  const wsId = BigInt(workspaceId);
  const specId = asset.specId;
  const specVersion = asset.specVersion;

  const [existing] = await tx
    .select({ id: identityWorkforceMembers.id })
    .from(identityWorkforceMembers)
    .where(
      and(
        eq(identityWorkforceMembers.workspaceId, wsId),
        eq(identityWorkforceMembers.memberType, "AI_AGENT"),
        eq(identityWorkforceMembers.agentSpecId, specId),
        eq(identityWorkforceMembers.agentSpecVersion, specVersion)
      )
    )
    .limit(1);
  if (existing) return existing.id.toString();

  const [row] = await tx
    .insert(identityWorkforceMembers)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      memberType: "AI_AGENT",
      agentSpecId: specId,
      agentSpecVersion: specVersion,
      roleTitle: asset.title || `AI ${specId}`,
      status: "active",
    })
    .returning({ id: identityWorkforceMembers.id });
  return row!.id.toString();
}

/**
 * Đảm bảo workspace có đúng 1 workforce member kiểu AI_AGENT cho agent profile.
 * Trả về member id (string). Seed lười khi materialize execution plan lần đầu.
 */
export async function ensureAiWorkforceMember(
  tx: Tx,
  workspaceId: string,
  agentProfile: OwnerAgentProfile
): Promise<string> {
  return ensureAiWorkforceMemberForAsset(tx, workspaceId, {
    specId: AGENT_PROFILE_SPEC_ID[agentProfile],
    specVersion: AGENT_PROFILE_SPEC_VERSION[agentProfile],
    definitionHash: AGENT_PROFILE_SPEC_HASH[agentProfile],
    title: `AI ${agentProfile}`,
  });
}

/**
 * Resolve member id để gán cho task FOUNDER_ONLY. Ưu tiên member của người đang
 * duyệt (preferredMemberId, thường là ctx.workforceMemberId); nếu không có thì
 * lấy HUMAN member cũ nhất của workspace; nếu workspace chưa có HUMAN member nào
 * thì trả null (task vẫn hiện ở "Việc của bạn" nhờ execution_mode='HUMAN').
 */
export async function resolveFounderMemberId(
  tx: Tx,
  workspaceId: string,
  preferredMemberId?: string | null
): Promise<string | null> {
  const wsId = BigInt(workspaceId);

  if (preferredMemberId) {
    const [pref] = await tx
      .select({ id: identityWorkforceMembers.id })
      .from(identityWorkforceMembers)
      .where(
        and(
          eq(identityWorkforceMembers.id, BigInt(preferredMemberId)),
          eq(identityWorkforceMembers.workspaceId, wsId),
          eq(identityWorkforceMembers.memberType, "HUMAN")
        )
      )
      .limit(1);
    if (pref) return pref.id.toString();
  }

  const [oldest] = await tx
    .select({ id: identityWorkforceMembers.id })
    .from(identityWorkforceMembers)
    .where(
      and(
        eq(identityWorkforceMembers.workspaceId, wsId),
        eq(identityWorkforceMembers.memberType, "HUMAN")
      )
    )
    .orderBy(asc(identityWorkforceMembers.createdAt), asc(identityWorkforceMembers.id))
    .limit(1);
  return oldest ? oldest.id.toString() : null;
}
