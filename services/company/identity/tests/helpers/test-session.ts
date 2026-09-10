// services/company/identity/tests/helpers/test-session.ts
//
// Test-only bootstrap: chèn thẳng user_projection + workspace +
// workspace_membership vào DB, bỏ qua sync-from-platform HTTP thật (vì test
// ở services/company không muốn phụ thuộc services/cosa đang chạy). Thay
// thế cho registerUserService cũ (đã xoá cùng local password auth).
import { sql } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { signAccessToken } from "../../services/token.service";

const { identityUserProjections, identityWorkspaces, identityWorkspaceMemberships } = schema;

export interface CreateTestSessionParams {
  email?: string;
  displayName?: string;
  role?: string;
}

export interface TestSession {
  accessToken: string;
  userId: string;
  workspaceId: string;
  /**
   * Startup Core: seed sẵn một project (id === workspaceId) để thoả composite
   * FK (project_id, workspace_id) trên tasks / okr_objectives /
   * twelve_week_cycles mà nhiều operations test chèn trực tiếp.
   */
  projectId: string;
}

export async function createTestSession(params: CreateTestSessionParams = {}): Promise<TestSession> {
  const displayName = params.displayName || "Test User";
  const email =
    params.email ||
    `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
  const role = params.role || "admin";

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

    await tx.execute(sql`
      INSERT INTO strategy.projects (id, workspace_id, title, status, lifecycle_stage)
      VALUES (${workspaceId}, ${workspaceId}, 'Default Test Project', 'ACTIVE', 'P0_DISCOVERY')
    `);
  });

  return {
    accessToken: signAccessToken(userId.toString()),
    userId: userId.toString(),
    workspaceId: workspaceId.toString(),
    projectId: workspaceId.toString(),
  };
}
