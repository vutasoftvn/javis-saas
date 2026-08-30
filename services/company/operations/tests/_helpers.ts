// services/company/operations/tests/_helpers.ts
//
// Shared test fixtures: workspace + membership bootstrap cho operations tests.
// Tái dùng pattern từ identity/tests/helpers/test-session.ts.
import { db, schema } from "../../identity/models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { signAccessToken } from "../../identity/services/token.service";

const { identityUserProjections, identityWorkspaces, identityWorkspaceMemberships } = schema;

export interface TestWorkspaceWithMemberParams {
  role?: string;
}

export interface TestWorkspaceWithMember {
  workspaceId: string;
  userId: string;
  bearerToken: string;
}

export interface TestSecondWorkspace {
  workspaceId: string;
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
  });

  const token = signAccessToken(userId.toString());

  return {
    workspaceId: workspaceId.toString(),
    userId: userId.toString(),
    bearerToken: `Bearer ${token}`,
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
  });

  return {
    workspaceId: workspaceId.toString(),
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

