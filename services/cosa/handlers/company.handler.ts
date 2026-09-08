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

// ADR-WORKSPACE-INVITATION-001: join bằng company_id trần đã bị chốt là lỗ
// hổng authority. Endpoint vẫn đăng ký (frontend Flutter hiện tại —
// frontend/lib/modules/auth/services/auth_service.dart — còn gọi route này,
// và route chưa nằm trong shared/contracts/mvp-surface.json nên
// frontend-api-contract-check không chặn được việc xoá) nhưng
// `joinExistingCompany` giờ luôn từ chối `permission_denied`. Việc gỡ hẳn
// route này khỏi frontend/contract thuộc Task 6 của chuỗi hardening.
export const joinCompany = api(
  { method: "POST", path: "/platform/auth/companies/join", expose: true, auth: true },
  async (params: BaseJoinCompanyParams): Promise<CompanyActionResponse> => {
    return joinCompanyFor(await resolveAuthData(), params);
  }
);

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
