// services/company/operations/tests/_helpers.ts
//
// Shared test fixtures: workspace + membership bootstrap cho operations tests.
// Tái dùng pattern từ identity/tests/helpers/test-session.ts.
import { sql } from "drizzle-orm";
import { db, schema } from "../../identity/models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { signAccessToken } from "../../identity/services/token.service";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  AGENT_PROFILE_SPEC_ID,
  AGENT_PROFILE_SPEC_VERSION,
  AGENT_PROFILE_SPEC_HASH,
  OwnerAgentProfile,
} from "../services/ai-member.service";
import {
  createWorkspaceAgent,
  deployAgentToProject,
} from "../services/founder-asset-deployment.service";

const { identityUserProjections, identityWorkspaces, identityWorkspaceMemberships } = schema;

export interface TestWorkspaceWithMemberParams {
  role?: string;
}

export interface TestWorkspaceWithMember {
  workspaceId: string;
  userId: string;
  bearerToken: string;
  /**
   * Startup Core: mọi Objective/Task/Cycle sống bên trong một project và
   * `001` có composite FK (project_id, workspace_id) → strategy.projects.
   * Helper seed sẵn một project có `id === workspaceId` để các test cũ chèn
   * `projectId: BigInt(ws.workspaceId)` vẫn thoả FK; test mới nên dùng
   * `ws.projectId` cho rõ nghĩa.
   */
  projectId: string;
}

export interface TestSecondWorkspace {
  workspaceId: string;
  projectId: string;
}

/**
 * Tạo workspace với một member đã được signup.
 * Returns workspaceId, userId, và signed bearer token cho auth.
 */
export async function createTestWorkspaceWithMember(
  opts: TestWorkspaceWithMemberParams = {}
): Promise<TestWorkspaceWithMember> {
  const role = opts.role || "admin";
  const displayName = "Test User";
  const email = `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;

  const userId = generateSnowflake();
  const workspaceId = generateSnowflake();
  const membershipId = generateSnowflake();

  await db.transaction(async (tx) => {
    await tx.insert(identityUserProjections).values({
      id: userId,
      email,
      displayName,
    });

    await tx.insert(identityWorkspaces).values({
      id: workspaceId,
      name: `Workspace của ${displayName}`,
    });

    await tx.insert(identityWorkspaceMemberships).values({
      id: membershipId,
      workspaceId,
      userId,
      role,
    });

    // Seed project mặc định (id === workspaceId) để thoả composite FK
    // (project_id, workspace_id) trên tasks / okr_objectives / twelve_week_cycles.
    await tx.execute(sql`
      INSERT INTO strategy.projects (id, workspace_id, title, status, lifecycle_stage)
      VALUES (${workspaceId}, ${workspaceId}, 'Default Test Project', 'ACTIVE', 'P0_DISCOVERY')
    `);
  });

  const token = signAccessToken(userId.toString());

  return {
    workspaceId: workspaceId.toString(),
    userId: userId.toString(),
    bearerToken: `Bearer ${token}`,
    projectId: workspaceId.toString(),
  };
}

/**
 * Tạo workspace thứ hai mà primary test user không phải member.
 * Dùng để test permission checks.
 */
export async function createSecondWorkspace(): Promise<TestSecondWorkspace> {
  const workspaceId = generateSnowflake();

  await db.transaction(async (tx) => {
    await tx.insert(identityWorkspaces).values({
      id: workspaceId,
      name: `Second Workspace (${Date.now()})`,
    });

    await tx.execute(sql`
      INSERT INTO strategy.projects (id, workspace_id, title, status, lifecycle_stage)
      VALUES (${workspaceId}, ${workspaceId}, 'Default Test Project', 'ACTIVE', 'P0_DISCOVERY')
    `);
  });

  return {
    workspaceId: workspaceId.toString(),
    projectId: workspaceId.toString(),
  };
}

/**
 * Thêm một user với role chỉ định vào workspace có sẵn.
 */
export async function addMemberToWorkspace(
  workspaceId: string,
  role: string = "member"
): Promise<{ userId: string; bearerToken: string }> {
  await new Promise((r) => setTimeout(r, 2));
  const userId = generateSnowflake();
  const membershipId = generateSnowflake();
  const displayName = `Member User ${role}`;
  const email = `member-${role}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;

  await db.transaction(async (tx) => {
    await tx.insert(identityUserProjections).values({
      id: userId,
      email,
      displayName,
    });
    await tx.insert(identityWorkspaceMemberships).values({
      id: membershipId,
      workspaceId: BigInt(workspaceId),
      userId,
      role,
    });
  });

  const token = signAccessToken(userId.toString());
  return {
    userId: userId.toString(),
    bearerToken: `Bearer ${token}`,
  };
}


/**
 * Startup Core: một Initiative thuộc đúng một Key Result (design §131). Nhiều
 * test tạo Initiative mà không dựng OKR trước — helper này seed nhanh một
 * Objective + Key Result trực tiếp vào project mặc định của workspace.
 */
export async function seedObjectiveWithKeyResult(
  workspaceId: string,
  projectId: string = workspaceId
): Promise<{ objectiveId: string; keyResultId: string }> {
  const objectiveId = generateSnowflake();
  const keyResultId = generateSnowflake();
  await db.transaction(async (tx) => {
    await tx.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, project_id, title, status)
      VALUES (${objectiveId}, ${BigInt(workspaceId)}, ${BigInt(projectId)}, 'Seed Objective', 'draft')
    `);
    await tx.execute(sql`
      INSERT INTO strategy.key_results (id, workspace_id, objective_id, title)
      VALUES (${keyResultId}, ${BigInt(workspaceId)}, ${objectiveId}, 'Seed KR')
    `);
  });
  return { objectiveId: objectiveId.toString(), keyResultId: keyResultId.toString() };
}

export function makeTestTenantContext(params: {
  workspaceId: string;
  userId: string;
  workforceMemberId?: string;
  membershipRole?: string;
  isAiAgent?: boolean;
}): TenantContext {
  return {
    workspaceId: params.workspaceId,
    userId: params.userId,
    workforceMemberId: params.workforceMemberId,
    membershipRole: params.membershipRole ?? "founder",
    permissions: [],
    correlationId: "test-corr-" + generateSnowflake().toString(),
    isAiAgent: params.isAiAgent ?? false,
  };
}

/**
 * Seed một Workspace Agent (V2) cho profile — CHƯA deploy vào Project nào.
 * Dùng profileKey như "finance", "operations"… để map sang exact AgentSpec pin
 * (`cosa.agents.*`) của catalog.
 */
export async function createWorkspaceAgentForProfile(
  ctx: TenantContext,
  profileKey: string
): Promise<{ workspaceAgentId: string }> {
  const specId = AGENT_PROFILE_SPEC_ID[profileKey as OwnerAgentProfile];
  const specVersion = AGENT_PROFILE_SPEC_VERSION[profileKey as OwnerAgentProfile];
  const specHash = AGENT_PROFILE_SPEC_HASH[profileKey as OwnerAgentProfile];

  const memberId = generateSnowflake();
  await db.execute(sql`
    INSERT INTO core.workforce_members (id, workspace_id, member_type, role_title, agent_spec_id, agent_spec_version, status)
    VALUES (${memberId}, ${BigInt(ctx.workspaceId)}, 'AI_AGENT', ${`AI ${profileKey}`}, ${specId}, ${specVersion}, 'active')
  `);

  const agent = await createWorkspaceAgent(ctx, {
    agentAssetId: specId,
    agentAssetVersion: specVersion,
    agentDefinitionHash: specHash,
    workforceMemberId: memberId.toString(),
    originKind: "BUILTIN",
    reason: "Test V2 deployment",
    idempotencyKey: `test-agent-${profileKey}`,
  });

  return { workspaceAgentId: agent.id };
}

/**
 * Seed một Workspace Agent (V2) + deploy vào Project — đường authority chính
 * thức của Executive Board (2026-09-14). Tái sử dụng cho test hai-Project
 * isolation và deliberation frame.
 */
export async function deployWorkspaceAgentForProfile(
  ctx: TenantContext,
  projectId: string,
  profileKey: string
): Promise<{ workspaceAgentId: string; deploymentId: string }> {
  const { workspaceAgentId } = await createWorkspaceAgentForProfile(ctx, profileKey);
  const deployment = await deployAgentToProject(ctx, {
    projectId,
    workspaceAgentId,
    reason: "Test V2 deployment",
    idempotencyKey: `test-deploy-${profileKey}`,
  });

  return { workspaceAgentId, deploymentId: deployment.id };
}
