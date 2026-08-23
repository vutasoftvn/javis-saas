import { api, Header } from "encore.dev/api";
import {
  AccountingProfile,
  CreateAccountingProfileParams as BaseCreateAccountingProfileParams,
  createAccountingProfileService,
  getAccountingProfileByWorkspaceService,
} from "../services/accounting-profile.service";

export { AccountingProfile };

export interface CreateAccountingProfileParams extends BaseCreateAccountingProfileParams {
  authorization?: Header<"Authorization">;
}

export const createAccountingProfile = api(
  { method: "POST", path: "/finance-legal/accounting-profiles", expose: true },
  async (params: CreateAccountingProfileParams): Promise<AccountingProfile> => {
    return createAccountingProfileService(params, params.authorization);
  }
);

export const getAccountingProfileByWorkspace = api(
  { method: "GET", path: "/finance-legal/accounting-profiles/by-workspace/:workspaceId", expose: true },
  async ({
    workspaceId,
    authorization,
  }: {
    workspaceId: number;
    authorization?: Header<"Authorization">;
  }): Promise<AccountingProfile> => {
    return getAccountingProfileByWorkspaceService(workspaceId, authorization);
  }
);
