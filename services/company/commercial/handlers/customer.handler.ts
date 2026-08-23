import { api, Header } from "encore.dev/api";
import { Customer, CreateCustomerParams as BaseCreateCustomerParams, createCustomerService, getCustomerService } from "../services/customer.service";

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
  async ({ id, authorization }: { id: number; authorization?: Header<"Authorization"> }): Promise<Customer> => {
    return getCustomerService(id, authorization);
  }
);
