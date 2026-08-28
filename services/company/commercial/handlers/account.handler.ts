import { api, Header } from "encore.dev/api";
import { Account, CreateAccountParams as BaseCreateAccountParams, createAccountService, getAccountService } from "../services/account.service";
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

