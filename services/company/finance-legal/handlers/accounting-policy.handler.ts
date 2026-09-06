import { api, Header, Query } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  getAccountingPolicyService,
  setAccountingPolicyService,
  AccountingPolicyView,
  SetAccountingPolicyInput,
} from "../services/accounting-policy.service";

export interface GetAccountingPolicyApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId: Query<string>;
}

export const getAccountingPolicy = api(
  { method: "GET", path: "/finance/accounting-policies", expose: true },
  async (req: GetAccountingPolicyApiRequest): Promise<{ policy: AccountingPolicyView | null }> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    const policy = await getAccountingPolicyService(ctx, req.legalEntityId);
    return { policy };
  }
);

export interface SetAccountingPolicyApiRequest extends SetAccountingPolicyInput {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const postAccountingPolicy = api(
  { method: "POST", path: "/finance/accounting-policies", expose: true },
  async (req: SetAccountingPolicyApiRequest): Promise<AccountingPolicyView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return setAccountingPolicyService(ctx, req);
  }
);
