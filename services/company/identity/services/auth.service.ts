import { APIError } from "encore.dev/api";
import { eq, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { hashPassword, verifyPassword } from "./password.service";
import { signAccessToken } from "./token.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { identityUsers, identityWorkspaces, identityWorkspaceMembers } = schema;

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
      id: identityUsers.id,
      passwordHash: identityUsers.passwordHash,
    })
    .from(identityUsers)
    .where(eq(sql`LOWER(${identityUsers.email})`, email))
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
    .select({ id: identityUsers.id })
    .from(identityUsers)
    .where(eq(sql`LOWER(${identityUsers.email})`, email))
    .limit(1);

  if (existing) {
    throw APIError.alreadyExists("email đã được đăng ký");
  }

  const passwordHash = await hashPassword(params.password);

  const result = await db.transaction(async (tx) => {
    const [userRow] = await tx
      .insert(identityUsers)
      .values({
        id: generateSnowflake(),
        email,
        passwordHash,
        displayName: params.displayName || null,
      })
      .returning({ id: identityUsers.id });

    if (!userRow) throw APIError.internal("failed to create user");

    const [workspaceRow] = await tx
      .insert(identityWorkspaces)
      .values({
        id: generateSnowflake(),
        name: `Workspace của ${params.displayName ?? email}`,
      })
      .returning({ id: identityWorkspaces.id });

    if (!workspaceRow) throw APIError.internal("failed to create workspace");

    await tx.insert(identityWorkspaceMembers).values({
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
      id: identityUsers.id,
      email: identityUsers.email,
      displayName: identityUsers.displayName,
    })
    .from(identityUsers)
    .where(eq(identityUsers.id, userId))
    .limit(1);

  if (!userRow) throw APIError.notFound("user not found");

  const [membershipRow] = await db
    .select({
      workspaceId: identityWorkspaceMembers.workspaceId,
      role: identityWorkspaceMembers.role,
    })
    .from(identityWorkspaceMembers)
    .where(eq(identityWorkspaceMembers.userId, userId))
    .limit(1);

  return {
    id: userRow.id.toString(),
    email: userRow.email,
    displayName: userRow.displayName,
    workspaceId: membershipRow ? membershipRow.workspaceId.toString() : null,
    role: membershipRow?.role ?? null,
  };
}
