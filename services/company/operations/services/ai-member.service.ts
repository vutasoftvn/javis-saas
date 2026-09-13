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
  | "data";

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
};

// Metadata mô tả (constraint workforce_members yêu cầu agent_spec_version NOT NULL
// cho AI_AGENT).
export const AGENT_PROFILE_SPEC_VERSION: Record<OwnerAgentProfile, string> = {
  operations: "1.3.0",
  finance: "1.1.0",
  marketing: "1.1.0",
  research_intelligence: "1.0.0",
  strategy: "1.0.0",
  customer_support: "1.2.0",
  sales: "1.0.0",
  coding: "1.0.0",
  product: "1.0.0",
  people: "1.0.0",
  security: "1.0.0",
  legal: "1.0.0",
  data: "1.0.0",
};

// Pinned definition_hash theo specs.py AgentSpec.compute_hash().
export const AGENT_PROFILE_SPEC_HASH: Record<OwnerAgentProfile, string> = {
  operations: "0c838f93ddc700984b9acdfead50ce45eb7f6ad867453edaf7c6793562dc33b2",
  finance: "21bacc10efd681f204e62e827111853a468436fa2413857bdc1b1e7e0c38be96",
  marketing: "4666a8f2958a656edbcb17f520826da84db8d871797baca18b22bd1438d9838a",
  research_intelligence: "2a3e445f343954dbad137100816be11226b9651a39ba91088adcbbbce1a9e705",
  strategy: "9e73d25f9399303e78556c7f3b881f2fe1ef738b9e95c978f7106f5e55343dd0",
  customer_support: "71fbf6cfccd3299367ad88e68866e53fd488d406c7d74bd0fbaef472731e15aa",
  sales: "089a67c81dc22041835b0ed05df7a441305c6abe416f293f609cc5262d31f332",
  coding: "d388ea7491ff1bad0863444b9bb764fe15804ee7eb74a4aad25e402a0af573e2",
  product: "f91ce512b333d3dff17672164206bc958fab042435fd420a926a715a1ac889be",
  people: "a03fcb1d3050bf4f364ca7c9e7581b443c08d3dac781199162626a5329dc0b05",
  security: "54232cdc8454ebda917991b48eb38f639dae3e6d8db3081070b859561670d966",
  legal: "b3f8435557658d3882da386db95c41f087c173acfe39f43e688c122263f46baf",
  data: "71535c32bc5d48e79e8b92887e5f9fd549d6142c0a2582690e6a5e6ca65fb21f",
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
