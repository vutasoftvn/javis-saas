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
  listCoreCompanies,
  createNewCompany,
  joinExistingCompany,
  validateUserMembership,
} from "../services/company.service";
import {
  CreateWorkspaceInvitationParams,
  CreateWorkspaceInvitationResponse,
  AcceptWorkspaceInvitationParams,
  createWorkspaceInvitation,
  acceptWorkspaceInvitation,
} from "../services/workspace-invitation.service";

export {
  CompanyMembershipInfo,
  ListMyCompaniesResponse,
  CompanyActionResponse,
  ValidateMembershipParams,
  ValidateMembershipResult,
  CreateWorkspaceInvitationParams,
  CreateWorkspaceInvitationResponse,
  AcceptWorkspaceInvitationParams,
};

export async function listMyCompaniesFor(authData: AuthData): Promise<ListMyCompaniesResponse> {
  return listCoreCompanies(authData.accessToken);
}

export async function createCompanyFor(
  authData: AuthData,
  params: BaseCreateCompanyParams
): Promise<CompanyActionResponse> {
  return createNewCompany(authData.userID, params, { accessToken: authData.accessToken });
}

export async function joinCompanyFor(
  authData: AuthData,
  params: BaseJoinCompanyParams
): Promise<CompanyActionResponse> {
  return joinExistingCompany(authData.userID, params);
}

/**
 * ADR-WORKSPACE-INVITATION-001. Chỉ founder/co-founder/admin của workspace
 * mới issue được — kiểm tra role thực hiện ở service layer, không tin input
 * client.
 */
export async function createWorkspaceInvitationFor(
  authData: AuthData,
  params: CreateWorkspaceInvitationParams
): Promise<CreateWorkspaceInvitationResponse> {
  return createWorkspaceInvitation(authData.userID, params);
}

/**
 * ADR-WORKSPACE-INVITATION-001. Email của invitation phải khớp principal
 * đang gọi accept; transaction-safe cho accept song song cùng token.
 */
export async function acceptWorkspaceInvitationFor(
  authData: AuthData,
  params: AcceptWorkspaceInvitationParams
): Promise<CompanyActionResponse> {
  return acceptWorkspaceInvitation(authData.userID, params);
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

// ADR-WORKSPACE-INVITATION-001 (Task 6): route `/platform/auth/companies/join`
// đã bị gỡ hẳn — frontend không còn gọi (auth_service.dart giờ chỉ chấp nhận
// invitation token qua acceptWorkspaceInvitation). `joinCompanyFor`
// (`joinExistingCompany` bên dưới) vẫn giữ lại làm regression test: chứng
// minh gọi thẳng function với `company_id` trần luôn bị từ chối
// `permission_denied` (xem tests/control-plane.test.ts và
// tests/workspace-invitation.test.ts) — không expose lại qua HTTP.
export const createWorkspaceInvitationEndpoint = api(
  { method: "POST", path: "/platform/auth/companies/invitations", expose: true, auth: true },
  async (params: CreateWorkspaceInvitationParams): Promise<CreateWorkspaceInvitationResponse> => {
    return createWorkspaceInvitationFor(await resolveAuthData(), params);
  }
);

export const acceptWorkspaceInvitationEndpoint = api(
  { method: "POST", path: "/platform/auth/companies/invitations/accept", expose: true, auth: true },
  async (params: AcceptWorkspaceInvitationParams): Promise<CompanyActionResponse> => {
    return acceptWorkspaceInvitationFor(await resolveAuthData(), params);
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
