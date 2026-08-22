import { APIError } from "encore.dev/api";
import { eq, and, asc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { verifyPlatformToken } from "./token.service";
import { generateSnowflakeStr } from "./snowflake.service";

const { users, profiles, companies, companyRoles } = schema;

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

function slugify(name: string, userId: string): string {
  const base = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "company";
  return `${base}-${userId}`;
}

export async function listUserCompanies(userIdStr: string): Promise<ListMyCompaniesResponse> {
  const userId = BigInt(userIdStr);

  const rows = await db
    .select({
      companyId: companyRoles.companyId,
      name: companies.name,
      roleId: companyRoles.roleId,
    })
    .from(companyRoles)
    .innerJoin(companies, eq(companies.id, companyRoles.companyId))
    .where(and(eq(companyRoles.userId, userId), eq(companies.status, "active")))
    .orderBy(asc(companyRoles.createdAt));

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
  params: CreateCompanyParams
): Promise<CompanyActionResponse> {
  const userId = BigInt(userIdStr);
  const name = params.name.trim();
  if (!name) {
    throw APIError.invalidArgument("tên công ty không được để trống");
  }

  const slug = slugify(name, userId.toString());
  const newCompId = BigInt(generateSnowflakeStr());
  const roleId = BigInt(generateSnowflakeStr());

  const result = await db.transaction(async (tx) => {
    const [companyRow] = await tx
      .insert(companies)
      .values({
        id: newCompId,
        name,
        slug,
        createdBy: userId,
      })
      .returning({ id: companies.id, name: companies.name });

    if (!companyRow) throw APIError.internal("failed to create company");

    await tx.insert(companyRoles).values({
      id: roleId,
      companyId: companyRow.id,
      userId: userId,
      roleId: "founder",
    });

    return companyRow;
  });

  return {
    company_id: result.id.toString(),
    name: result.name,
    role_id: "founder",
  };
}

export async function joinExistingCompany(
  userIdStr: string,
  params: JoinCompanyParams
): Promise<CompanyActionResponse> {
  const userId = BigInt(userIdStr);
  const companyId = BigInt(params.company_id.toString());

  const [company] = await db
    .select({ id: companies.id, name: companies.name })
    .from(companies)
    .where(and(eq(companies.id, companyId), eq(companies.status, "active")))
    .limit(1);

  if (!company) {
    throw APIError.notFound("công ty muốn tham gia không tồn tại");
  }

  const [existing] = await db
    .select({ roleId: companyRoles.roleId })
    .from(companyRoles)
    .where(and(eq(companyRoles.companyId, company.id), eq(companyRoles.userId, userId)))
    .limit(1);

  let roleId = "user";
  if (existing) {
    roleId = existing.roleId;
  } else {
    const newRoleId = BigInt(generateSnowflakeStr());
    await db.insert(companyRoles).values({
      id: newRoleId,
      companyId: company.id,
      userId: userId,
      roleId: "user",
    });
  }

  return {
    company_id: company.id.toString(),
    name: company.name,
    role_id: roleId,
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
  const companyId = BigInt(params.companyId);

  const [userRow] = await db
    .select({
      id: users.id,
      email: users.email,
      phone: users.phone,
      fullName: profiles.fullName,
    })
    .from(users)
    .leftJoin(profiles, eq(profiles.userId, users.id))
    .where(eq(users.id, userId))
    .limit(1);

  if (!userRow) {
    throw APIError.notFound("platform user không tồn tại");
  }

  const [membershipRow] = await db
    .select({
      roleId: companyRoles.roleId,
      companyName: companies.name,
    })
    .from(companyRoles)
    .innerJoin(companies, eq(companies.id, companyRoles.companyId))
    .where(
      and(
        eq(companyRoles.userId, userId),
        eq(companyRoles.companyId, companyId),
        eq(companies.status, "active")
      )
    )
    .limit(1);

  if (!membershipRow) {
    throw APIError.permissionDenied("bạn không phải thành viên của company này");
  }

  return {
    valid: true,
    userId: userRow.id.toString(),
    email: userRow.email,
    phone: userRow.phone,
    displayName: userRow.fullName,
    companyId: companyId.toString(),
    companyName: membershipRow.companyName,
    roleId: membershipRow.roleId,
  };
}
