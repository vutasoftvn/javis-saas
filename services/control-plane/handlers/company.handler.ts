import { api, Header } from "encore.dev/api";
import { extractUserId } from "../services/auth.service";
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

export interface ListMyCompaniesParams {
  authorization?: Header<"Authorization">;
}

export interface CreateCompanyParams extends BaseCreateCompanyParams {
  authorization?: Header<"Authorization">;
}

export interface JoinCompanyParams extends BaseJoinCompanyParams {
  authorization?: Header<"Authorization">;
}

export const listMyCompanies = api(
  { method: "GET", path: "/platform/auth/me/companies", expose: true, auth: false },
  async (params: ListMyCompaniesParams): Promise<ListMyCompaniesResponse> => {
    const userId = extractUserId(params.authorization);
    return listUserCompanies(userId);
  }
);

export const createCompany = api(
  { method: "POST", path: "/platform/auth/companies/create", expose: true, auth: false },
  async (params: CreateCompanyParams): Promise<CompanyActionResponse> => {
    const userId = extractUserId(params.authorization);
    return createNewCompany(userId, params);
  }
);

export const joinCompany = api(
  { method: "POST", path: "/platform/auth/companies/join", expose: true, auth: false },
  async (params: JoinCompanyParams): Promise<CompanyActionResponse> => {
    const userId = extractUserId(params.authorization);
    return joinExistingCompany(userId, params);
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
