import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { signAccessToken } from "./token.service";

const { identityUserProjections, identityWorkspaces, identityWorkspaceMemberships } = schema;

export interface CreateE2eSessionParams {
  email: string;
  displayName: string;
}

export interface E2eSession {
  accessToken: string;
  userId: string;
  workspaceId: string;
}

/**
 * Creates the minimal Company identity projection required by an isolated
 * HTTP E2E scenario. The handler that calls this service is disabled unless
 * an explicitly launched local/CI E2E process enables it.
 */
export async function createE2eSession(params: CreateE2eSessionParams): Promise<E2eSession> {
  const userId = generateSnowflake();
  const workspaceId = generateSnowflake();

  await db.transaction(async (tx) => {
    await tx.insert(identityUserProjections).values({
      id: userId,
      email: params.email,
      displayName: params.displayName,
    });
    await tx.insert(identityWorkspaces).values({
      id: workspaceId,
      name: `E2E workspace for ${params.displayName}`,
    });
    await tx.insert(identityWorkspaceMemberships).values({
      id: generateSnowflake(),
      workspaceId,
      userId,
      role: "founder",
    });
  });

  return {
    accessToken: signAccessToken(userId.toString()),
    userId: userId.toString(),
    workspaceId: workspaceId.toString(),
  };
}
