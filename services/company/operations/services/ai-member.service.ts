import { and, asc, eq } from "drizzle-orm";
import { identityWorkforceMembers } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";

export type OwnerAgentProfile = "operations" | "finance" | "marketing";

// AgentSpec id theo apps/cosa/agents/specs.py (COSA_*_AGENT_SPEC.id).
export const AGENT_PROFILE_SPEC_ID: Record<OwnerAgentProfile, string> = {
  operations: "cosa.agents.operations",
  finance: "cosa.agents.finance",
  marketing: "cosa.agents.marketing",
};

// Metadata mô tả (constraint workforce_members yêu cầu agent_spec_version NOT NULL
// cho AI_AGENT). Runtime dispatch KHÔNG dùng giá trị này — worker resolve exact
// hash qua registry theo ADR-AGENT-REG-001; đây chỉ là nhãn cho UI/audit.
export const AGENT_PROFILE_SPEC_VERSION: Record<OwnerAgentProfile, string> = {
  operations: "1.2.0",
  finance: "1.1.0",
  marketing: "1.1.0",
};

// Drizzle transaction type — cùng cách project-kickoff-materialize.service.ts đặt tên.
type Tx = Parameters<Parameters<typeof import("../models/db").db.transaction>[0]>[0];

/**
 * Đảm bảo workspace có đúng 1 workforce member kiểu AI_AGENT cho agent profile.
 * Trả về member id (string). Seed lười khi materialize execution plan lần đầu.
 */
export async function ensureAiWorkforceMember(
  tx: Tx,
  workspaceId: string,
  agentProfile: OwnerAgentProfile
): Promise<string> {
  const wsId = BigInt(workspaceId);
  const specId = AGENT_PROFILE_SPEC_ID[agentProfile];

  const [existing] = await tx
    .select({ id: identityWorkforceMembers.id })
    .from(identityWorkforceMembers)
    .where(
      and(
        eq(identityWorkforceMembers.workspaceId, wsId),
        eq(identityWorkforceMembers.memberType, "AI_AGENT"),
        eq(identityWorkforceMembers.agentSpecId, specId)
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
      agentSpecVersion: AGENT_PROFILE_SPEC_VERSION[agentProfile],
      roleTitle: `AI ${agentProfile}`,
      status: "active",
    })
    .returning({ id: identityWorkforceMembers.id });
  return row!.id.toString();
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
