import { APIError } from "encore.dev/api";
import { eq, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { hashPassword, verifyPassword } from "./password.service";
import { signAccessToken } from "./token.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { identityUserProjections, identityWorkspaces, identityWorkspaceMemberships } = schema;

export interface LoginParams {
  email: string;
  password: string;
}

export interface LoginResult {
  accessToken: string;
}

export interface RegisterParams {
  email: string;
  password: string;
  displayName?: string;
}

export interface RegisterResult {
  accessToken: string;
  userId: string;
  workspaceId: string;
}

export interface MeResponse {
  id: string;
  email: string | null;
  displayName: string | null;
  workspaceId: string | null;
  role: string | null;
}

export async function loginUser(params: LoginParams): Promise<LoginResult> {
  const email = params.email.trim().toLowerCase();
  const [user] = await db
    .select({
      id: identityUserProjections.id,
      passwordHash: identityUserProjections.passwordHash,
    })
    .from(identityUserProjections)
    .where(eq(sql`LOWER(${identityUserProjections.email})`, email))
    .limit(1);

  if (!user || !user.passwordHash) {
    throw APIError.unauthenticated("sai email hoặc mật khẩu");
  }
  const valid = await verifyPassword(params.password, user.passwordHash);
  if (!valid) {
    throw APIError.unauthenticated("sai email hoặc mật khẩu");
  }
  return { accessToken: signAccessToken(user.id.toString()) };
}

export async function registerUserService(params: RegisterParams): Promise<RegisterResult> {
  const email = params.email.trim().toLowerCase();

  const [existing] = await db
    .select({ id: identityUserProjections.id })
    .from(identityUserProjections)
    .where(eq(sql`LOWER(${identityUserProjections.email})`, email))
    .limit(1);

  if (existing) {
    throw APIError.alreadyExists("email đã được đăng ký");
  }

  const passwordHash = await hashPassword(params.password);

  const result = await db.transaction(async (tx) => {
    const [userRow] = await tx
      .insert(identityUserProjections)
      .values({
        id: generateSnowflake(),
        email,
        passwordHash,
        displayName: params.displayName || null,
      })
      .returning({ id: identityUserProjections.id });

    if (!userRow) throw APIError.internal("failed to create user");

    const [workspaceRow] = await tx
      .insert(identityWorkspaces)
      .values({
        id: generateSnowflake(),
        name: `Workspace của ${params.displayName ?? email}`,
      })
      .returning({ id: identityWorkspaces.id });

    if (!workspaceRow) throw APIError.internal("failed to create workspace");

    await tx.insert(identityWorkspaceMemberships).values({
      id: generateSnowflake(),
      workspaceId: workspaceRow.id,
      userId: userRow.id,
      role: "admin",
    });

    return {
      userId: userRow.id.toString(),
      workspaceId: workspaceRow.id.toString(),
    };
  });

  return {
    accessToken: signAccessToken(result.userId),
    userId: result.userId,
    workspaceId: result.workspaceId,
  };
}

export async function getMeProfile(userIdStr: string): Promise<MeResponse> {
  const userId = BigInt(userIdStr);
  const [userRow] = await db
    .select({
      id: identityUserProjections.id,
      email: identityUserProjections.email,
      displayName: identityUserProjections.displayName,
    })
    .from(identityUserProjections)
    .where(eq(identityUserProjections.id, userId))
    .limit(1);

  if (!userRow) throw APIError.notFound("user not found");

  const [membershipRow] = await db
    .select({
      workspaceId: identityWorkspaceMemberships.workspaceId,
      role: identityWorkspaceMemberships.role,
    })
    .from(identityWorkspaceMemberships)
    .where(eq(identityWorkspaceMemberships.userId, userId))
    .limit(1);

  return {
    id: userRow.id.toString(),
    email: userRow.email,
    displayName: userRow.displayName,
    workspaceId: membershipRow ? membershipRow.workspaceId.toString() : null,
    role: membershipRow?.role ?? null,
  };
}
