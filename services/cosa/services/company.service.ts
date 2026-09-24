import { APIError } from "encore.dev/api";
import { eq, and, asc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { authorizeAndProjectCoreAccess, resolveCallerIdentity } from "./core-access.service";
import { provisionVentureWorkspace } from "./venture-workspace.service";
import { createCoreOrganization, listCoreOrganizations } from "./core-organization.service";
import { mapCoreRoleToCosaRole } from "./core-projection.service";

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

// Role của core dùng cho miền giao thông (operator, driver) không có nghĩa ở COSA.
const CORE_ROLES_WITHOUT_COSA_ACCESS = new Set(["operator", "driver"]);

/** Danh sách organization của user lấy từ core (nguồn sự thật) khi đăng nhập bằng token của core. */
export async function listCoreCompanies(accessToken: string): Promise<ListMyCompaniesResponse> {
  const organizations = await listCoreOrganizations(accessToken);
  return {
    companies: organizations
      .filter((o) => !CORE_ROLES_WITHOUT_COSA_ACCESS.has(o.role))
      .map((o) => ({
        company_id: o.organizationId,
        name: o.name,
        role_id: mapCoreRoleToCosaRole(o.role),
      })),
  };
}

export interface CreateCompanyContext {
  /** Access token OIDC của core: organization được tạo ở core (nguồn sự thật). */
  accessToken: string;
}

export async function createNewCompany(
  userIdStr: string,
  params: CreateCompanyServiceParams,
  ctx: CreateCompanyContext
): Promise<CompanyActionResponse> {
  const userId = BigInt(userIdStr);
  const name = params.name.trim();
  if (!name) {
    throw APIError.invalidArgument("tên công ty không được để trống");
  }

  // Organization (id, tên, membership founder) được tạo ở core trước, COSA chỉ dựng dữ liệu vận hành
  // (license, entitlement, sync log) với đúng id đó.
  const coreOrg = await createCoreOrganization(ctx.accessToken, name);

  const result = await provisionVentureWorkspace({
    ownerUserId: userId,
    workspaceName: coreOrg.name,
    clientCreationId: `core-org-${coreOrg.organizationId}`,
    workspaceId: coreOrg.organizationId,
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

/**
 * ADR-WORKSPACE-INVITATION-001 — endpoint join-by-`company_id` trần đã bị
 * chốt là lỗ hổng authority (bất kỳ ai biết/đoán một `company_id` hợp lệ đều
 * tự cấp được membership). Giữ nguyên tên hàm + signature để không phải sửa
 * lại `company.handler.ts` và các caller khác, nhưng hành vi luôn từ chối —
 * membership giờ chỉ được cấp qua `workspace-invitation.service.ts::
 * acceptWorkspaceInvitation`. Tham số nhận vào không còn được dùng để tránh
 * "unused" lint nhưng vẫn khai báo để giữ chữ ký công khai ổn định.
 */
export async function joinExistingCompany(
  _userIdStr: string,
  _params: JoinCompanyServiceParams
): Promise<CompanyActionResponse> {
  throw APIError.permissionDenied("Workspace membership requires an invitation");
}

export async function validateUserMembership(
  params: ValidateMembershipParams
): Promise<ValidateMembershipResult> {
  // Access token OIDC của core: core quyết định thành viên (ném permission_denied nếu không phải) và bản
  // chiếu được cập nhật trước khi đọc bảng cục bộ.
  const caller = await resolveCallerIdentity(params.platformToken);
  await authorizeAndProjectCoreAccess(params.platformToken, params.companyId, "cosa.workspace.read");

  const userId = BigInt(caller.userId);
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


