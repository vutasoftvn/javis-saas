import { api, Header } from "encore.dev/api";
import { Customer, CreateCustomerParams as BaseCreateCustomerParams, createCustomerService, getCustomerService } from "../services/customer.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

export { Customer };

export interface CreateCustomerParams extends BaseCreateCustomerParams {
  authorization?: Header<"Authorization">;
}

export const createCustomer = api(
  { method: "POST", path: "/commercial/customers", expose: true },
  async (params: CreateCustomerParams): Promise<Customer> => {
    return createCustomerService(params, params.authorization);
  }
);

export const getCustomer = api(
  { method: "GET", path: "/commercial/customers/:id", expose: true },
  async ({
    id,
    workspaceId,
    authorization,
  }: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<Customer> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getCustomerService(id, ctx);
  }
);

