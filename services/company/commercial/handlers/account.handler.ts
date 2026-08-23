import { api, Header } from "encore.dev/api";
import { Account, CreateAccountParams as BaseCreateAccountParams, createAccountService, getAccountService } from "../services/account.service";

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
  async ({ id, authorization }: { id: string; authorization?: Header<"Authorization"> }): Promise<Account> => {
    return getAccountService(id, authorization);
  }
);
