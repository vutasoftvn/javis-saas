import { api, APIError, Header } from "encore.dev/api";
import { controlPlaneDB } from "./db";
import { verifyPlatformToken } from "./token";

export interface CompanyMembershipInfo {
  company_id: string;
  name: string | null;
  role_id: string;
}

export interface ListMyCompaniesResponse {
  companies: CompanyMembershipInfo[];
}

export interface CreateCompanyParams {
  name: string;
}

export interface JoinCompanyParams {
  company_id: number | string;
}

export interface CompanyActionResponse {
  company_id: string;
  name: string;
  role_id: string;
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
}

interface AuthHeader {
  authorization?: Header<"Authorization">;
}

function extractUserId(auth?: string): string {
  if (!auth || !auth.startsWith("Bearer ")) {
    throw APIError.unauthenticated("missing or invalid authorization header");
  }
  const token = auth.slice("Bearer ".length);
  try {
    const payload = verifyPlatformToken(token);
    return payload.sub;
  } catch {
    throw APIError.unauthenticated("invalid or expired platform token");
  }
}

function slugify(name: string, userId: number | string): string {
  const base = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "company";
  return `${base}-${userId}`;
}

export const listMyCompanies = api(
  { method: "GET", path: "/platform/auth/me/companies", expose: true },
  async (headers: AuthHeader): Promise<ListMyCompaniesResponse> => {
    const userId = Number(extractUserId(headers.authorization));

    const rows = await controlPlaneDB.query<{
      company_id: number;
      name: string | null;
      role_id: string;
    }>`
      SELECT cr.company_id, c.name, cr.role_id
      FROM control_plane.company_roles cr
      JOIN control_plane.companies c ON c.id = cr.company_id
      WHERE cr.user_id = ${userId} AND c.status = 'active'
      ORDER BY cr.created_at ASC
    `;

    const items: CompanyMembershipInfo[] = [];
    for await (const row of rows) {
      items.push({
        company_id: String(row.company_id),
        name: row.name,
        role_id: row.role_id,
      });
    }
    return { companies: items };
  }
);

export const createCompany = api(
  { method: "POST", path: "/platform/auth/companies/create", expose: true },
  async (params: CreateCompanyParams, headers: AuthHeader): Promise<CompanyActionResponse> => {
    const userId = Number(extractUserId(headers.authorization));
    const name = params.name.trim();
    if (!name) {
      throw APIError.invalidArgument("tên công ty không được để trống");
    }

    const tx = await controlPlaneDB.begin();
    try {
      const slug = slugify(name, userId);
      const companyRow = await tx.queryRow<{ id: number; name: string }>`
        INSERT INTO control_plane.companies (name, slug, created_by)
        VALUES (${name}, ${slug}, ${userId})
        RETURNING id, name
      `;
      if (!companyRow) throw APIError.internal("failed to create company");

      await tx.exec`
        INSERT INTO control_plane.company_roles (company_id, user_id, role_id)
        VALUES (${companyRow.id}, ${userId}, 'founder')
      `;

      await tx.commit();

      return {
        company_id: String(companyRow.id),
        name: companyRow.name,
        role_id: "founder",
      };
    } catch (err) {
      await tx.rollback();
      throw err;
    }
  }
);

export const joinCompany = api(
  { method: "POST", path: "/platform/auth/companies/join", expose: true },
  async (params: JoinCompanyParams, headers: AuthHeader): Promise<CompanyActionResponse> => {
    const userId = Number(extractUserId(headers.authorization));
    const companyId = Number(params.company_id);
    if (!companyId || isNaN(companyId)) {
      throw APIError.invalidArgument("mã công ty không hợp lệ");
    }

    const company = await controlPlaneDB.queryRow<{ id: number; name: string }>`
      SELECT id, name FROM control_plane.companies WHERE id = ${companyId} AND status = 'active'
    `;
    if (!company) {
      throw APIError.notFound("công ty muốn tham gia không tồn tại");
    }

    const existing = await controlPlaneDB.queryRow<{ role_id: string }>`
      SELECT role_id FROM control_plane.company_roles WHERE company_id = ${companyId} AND user_id = ${userId}
    `;

    let roleId = "user";
    if (existing) {
      roleId = existing.role_id;
    } else {
      await controlPlaneDB.exec`
        INSERT INTO control_plane.company_roles (company_id, user_id, role_id)
        VALUES (${companyId}, ${userId}, 'user')
      `;
    }

    return {
      company_id: String(company.id),
      name: company.name,
      role_id: roleId,
    };
  }
);

/**
 * Internal RPC: Used by `services/identity` to validate a membership and fetch user/company info during sync.
 */
export const validateMembership = api(
  { method: "POST", path: "/platform/internal/validate-membership", expose: false },
  async (params: ValidateMembershipParams): Promise<ValidateMembershipResult> => {
    let payload;
    try {
      payload = verifyPlatformToken(params.platformToken);
    } catch {
      throw APIError.unauthenticated("invalid or expired platform token");
    }

    const userId = Number(payload.sub);
    const companyId = Number(params.companyId);

    const userRow = await controlPlaneDB.queryRow<{
      id: number;
      email: string | null;
      phone: string | null;
      full_name: string | null;
    }>`
      SELECT u.id, u.email, u.phone, p.full_name
      FROM control_plane.users u
      LEFT JOIN control_plane.profiles p ON p.user_id = u.id
      WHERE u.id = ${userId}
    `;

    if (!userRow) {
      throw APIError.notFound("platform user không tồn tại");
    }

    const membershipRow = await controlPlaneDB.queryRow<{
      role_id: string;
      company_name: string;
    }>`
      SELECT cr.role_id, c.name as company_name
      FROM control_plane.company_roles cr
      JOIN control_plane.companies c ON c.id = cr.company_id
      WHERE cr.user_id = ${userId} AND cr.company_id = ${companyId} AND c.status = 'active'
    `;

    if (!membershipRow) {
      throw APIError.permissionDenied("bạn không phải thành viên của company này");
    }

    return {
      valid: true,
      userId: String(userRow.id),
      email: userRow.email,
      phone: userRow.phone,
      displayName: userRow.full_name,
      companyId: String(companyId),
      companyName: membershipRow.company_name,
      roleId: membershipRow.role_id,
    };
  }
);
