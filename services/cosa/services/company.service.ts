import { APIError } from "encore.dev/api";
import { eq, and, asc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { verifyPlatformToken } from "./token.service";
import { generateSnowflakeStr } from "./snowflake.service";
import { provisionVentureWorkspace } from "./venture-workspace.service";

const {
  users,
  profiles,
  workspaces,
  workspaceMemberships,
} = schema;

export interface CompanyMembershipInfo {
  company_id: string;
  name: string | null;
  role_id: string;
}

export interface ListMyCompaniesResponse {
  companies: CompanyMembershipInfo[];
}

export interface CreateCompanyServiceParams {
  name: string;
}

export interface JoinCompanyServiceParams {
  company_id: number | string;
}

export interface CompanyActionResponse {
  company_id: string;
  name: string;
  role_id: string;
  workspace?: {
    workspace_id: string;
    workspace_name: string;
    role_id: string;
    status: string;
  };
}

export interface ValidateMembershipParams {
  platformToken: string;
  companyId: string;
}

export interface ValidateMembershipResult {
  valid: boolean;
  userId: string;
  email: string | null;
  phone: string | null;
  displayName: string | null;
  companyId: string;
  companyName: string;
  roleId: string;
  membershipId: string;
  membershipUpdatedAt: string;
}

export async function listUserCompanies(userIdStr: string): Promise<ListMyCompaniesResponse> {
  const userId = BigInt(userIdStr);

  const rows = await db
    .select({
      companyId: workspaceMemberships.workspaceId,
      name: workspaces.workspaceName,
      roleId: workspaceMemberships.roleId,
    })
    .from(workspaceMemberships)
    .innerJoin(workspaces, eq(workspaces.id, workspaceMemberships.workspaceId))
    .where(and(eq(workspaceMemberships.userId, userId), eq(workspaces.status, "active")))
    .orderBy(asc(workspaceMemberships.createdAt));

  return {
    companies: rows.map((r) => ({
      company_id: r.companyId.toString(),
      name: r.name,
      role_id: r.roleId,
    })),
  };
}

export async function createNewCompany(
  userIdStr: string,
  params: CreateCompanyServiceParams
): Promise<CompanyActionResponse> {
  const userId = BigInt(userIdStr);
  const name = params.name.trim();
  if (!name) {
    throw APIError.invalidArgument("tên công ty không được để trống");
  }

  const result = await provisionVentureWorkspace({
    ownerUserId: userId,
    workspaceName: name,
    clientCreationId: `legacy-comp-create-${Date.now()}-${userIdStr}`,
  });

  // Tự động nâng profile role của người tạo lên founder nếu đang là member
  await db
    .update(profiles)
    .set({ roleId: "founder", updatedAt: new Date() })
    .where(and(eq(profiles.id, userId), eq(profiles.roleId, "member")));

  return {
    company_id: result.platformWorkspaceId,
    name: name,
    role_id: "founder",
    workspace: {
      workspace_id: result.platformWorkspaceId,
      workspace_name: name,
      role_id: "founder",
      status: "active",
    },
  };
}

export async function joinExistingCompany(
  userIdStr: string,
  params: JoinCompanyServiceParams
): Promise<CompanyActionResponse> {
  const userId = BigInt(userIdStr);
  const workspaceId = BigInt(params.company_id.toString());

  const [ws] = await db
    .select({ id: workspaces.id, name: workspaces.workspaceName })
    .from(workspaces)
    .where(and(eq(workspaces.id, workspaceId), eq(workspaces.status, "active")))
    .limit(1);

  if (!ws) {
    throw APIError.notFound("công ty không tồn tại hoặc đã bị vô hiệu hóa");
  }

  const [existing] = await db
    .select({ id: workspaceMemberships.id })
    .from(workspaceMemberships)
    .where(and(eq(workspaceMemberships.workspaceId, workspaceId), eq(workspaceMemberships.userId, userId)))
    .limit(1);

  if (existing) {
    return {
      company_id: workspaceId.toString(),
      name: ws.name,
      role_id: "member",
      workspace: {
        workspace_id: workspaceId.toString(),
        workspace_name: ws.name,
        role_id: "member",
        status: "active",
      },
    };
  }

  const newMembershipId = BigInt(generateSnowflakeStr());
  await db.insert(workspaceMemberships).values({
    id: newMembershipId,
    workspaceId: workspaceId,
    userId: userId,
    roleId: "member",
  });

  return {
    company_id: workspaceId.toString(),
    name: ws.name,
    role_id: "member",
    workspace: {
      workspace_id: workspaceId.toString(),
      workspace_name: ws.name,
      role_id: "member",
      status: "active",
    },
  };
}

export async function validateUserMembership(
  params: ValidateMembershipParams
): Promise<ValidateMembershipResult> {
  let payload;
  try {
    payload = verifyPlatformToken(params.platformToken);
  } catch {
    throw APIError.unauthenticated("invalid or expired platform token");
  }

  const userId = BigInt(payload.sub);
  const workspaceId = BigInt(params.companyId);

  const [userRow] = await db
    .select({
      id: users.id,
      email: users.email,
      phone: users.phone,
      fullName: profiles.fullName,
    })
    .from(users)
    .leftJoin(profiles, eq(profiles.id, users.id))
    .where(eq(users.id, userId))
    .limit(1);

  if (!userRow) {
    throw APIError.notFound("platform user không tồn tại");
  }

  const [membershipRow] = await db
    .select({
      id: workspaceMemberships.id,
      roleId: workspaceMemberships.roleId,
      workspaceName: workspaces.workspaceName,
      updatedAt: workspaceMemberships.updatedAt,
    })
    .from(workspaceMemberships)
    .innerJoin(workspaces, eq(workspaces.id, workspaceMemberships.workspaceId))
    .where(
      and(
        eq(workspaceMemberships.userId, userId),
        eq(workspaceMemberships.workspaceId, workspaceId),
        eq(workspaces.status, "active")
      )
    )
    .limit(1);

  if (!membershipRow) {
    throw APIError.permissionDenied("bạn không phải thành viên của workspace này");
  }

  return {
    valid: true,
    userId: userRow.id.toString(),
    email: userRow.email,
    phone: userRow.phone,
    displayName: userRow.fullName,
    companyId: workspaceId.toString(),
    companyName: membershipRow.workspaceName,
    roleId: membershipRow.roleId,
    membershipId: membershipRow.id.toString(),
    membershipUpdatedAt: membershipRow.updatedAt.toISOString(),
  };
}


