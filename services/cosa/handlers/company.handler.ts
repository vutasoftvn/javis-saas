import { api } from "encore.dev/api";
import { AuthData, resolveAuthData } from "./auth.handler";
import {
  CompanyMembershipInfo,
  ListMyCompaniesResponse,
  CreateCompanyServiceParams as BaseCreateCompanyParams,
  JoinCompanyServiceParams as BaseJoinCompanyParams,
  CompanyActionResponse,
  ValidateMembershipParams,
  ValidateMembershipResult,
  listUserCompanies,
  createNewCompany,
  joinExistingCompany,
  validateUserMembership,
} from "../services/company.service";

export {
  CompanyMembershipInfo,
  ListMyCompaniesResponse,
  CompanyActionResponse,
  ValidateMembershipParams,
  ValidateMembershipResult,
};

export async function listMyCompaniesFor(authData: AuthData): Promise<ListMyCompaniesResponse> {
  return listUserCompanies(authData.userID);
}

export async function createCompanyFor(
  authData: AuthData,
  params: BaseCreateCompanyParams
): Promise<CompanyActionResponse> {
  return createNewCompany(authData.userID, params);
}

export async function joinCompanyFor(
  authData: AuthData,
  params: BaseJoinCompanyParams
): Promise<CompanyActionResponse> {
  return joinExistingCompany(authData.userID, params);
}

export const listMyCompanies = api(
  { method: "GET", path: "/platform/auth/me/companies", expose: true, auth: true },
  async (): Promise<ListMyCompaniesResponse> => {
    return listMyCompaniesFor(await resolveAuthData());
  }
);

export const createCompany = api(
  { method: "POST", path: "/platform/auth/companies/create", expose: true, auth: true },
  async (params: BaseCreateCompanyParams): Promise<CompanyActionResponse> => {
    return createCompanyFor(await resolveAuthData(), params);
  }
);

export const joinCompany = api(
  { method: "POST", path: "/platform/auth/companies/join", expose: true, auth: true },
  async (params: BaseJoinCompanyParams): Promise<CompanyActionResponse> => {
    return joinCompanyFor(await resolveAuthData(), params);
  }
);

/**
 * Internal RPC: Used by `services/identity` to validate a membership and fetch user/company info during sync.
 */
export const validateMembership = api(
  { method: "POST", path: "/platform/internal/validate-membership", expose: false },
  async (params: ValidateMembershipParams): Promise<ValidateMembershipResult> => {
    return validateUserMembership(params);
  }
);
