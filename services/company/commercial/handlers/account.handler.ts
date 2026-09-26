import { api, Header } from "encore.dev/api";
import {
  Account,
  CreateAccountParams as BaseCreateAccountParams,
  createAccountService,
  getAccountService,
  listAccountsService,
} from "../services/account.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

export { Account };

export interface CreateAccountParams extends BaseCreateAccountParams {
  authorization?: Header<"Authorization">;
}

export const createAccount = api(
  { method: "POST", path: "/commercial/accounts", expose: true },
  async (params: CreateAccountParams): Promise<Account> => {
    return createAccountService(params, params.authorization);
  }
);

export const getAccount = api(
  { method: "GET", path: "/commercial/accounts/:id", expose: true },
  async ({
    id,
    workspaceId,
    authorization,
  }: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<Account> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getAccountService(id, ctx);
  }
);

// Dashboard CRM — danh sách account của workspace (tenant guard trong service).
export const listAccounts = api(
  { method: "GET", path: "/commercial/workspaces/:workspaceId/accounts", expose: true },
  async (params: {
    workspaceId: string;
    authorization?: Header<"Authorization">;
  }): Promise<{ accounts: Account[] }> => {
    const accounts = await listAccountsService(params.workspaceId, params.authorization);
    return { accounts };
  }
);
