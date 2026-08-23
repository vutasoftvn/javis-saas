import { api, Header } from "encore.dev/api";
import {
  FinanceException,
  RaiseFinanceExceptionParams as BaseRaiseFinanceExceptionParams,
  raiseFinanceExceptionService,
  getFinanceExceptionService,
  resolveFinanceExceptionService,
} from "../services/finance-exception.service";

export { FinanceException };

export interface RaiseFinanceExceptionParams extends BaseRaiseFinanceExceptionParams {
  authorization?: Header<"Authorization">;
}

export interface FinanceExceptionByIdParams {
  id: number;
  authorization?: Header<"Authorization">;
}

export const raiseFinanceException = api(
  { method: "POST", path: "/finance-legal/exceptions", expose: true },
  async (params: RaiseFinanceExceptionParams): Promise<FinanceException> => {
    return raiseFinanceExceptionService(params, params.authorization);
  }
);

export const getFinanceException = api(
  { method: "GET", path: "/finance-legal/exceptions/:id", expose: true },
  async ({ id, authorization }: FinanceExceptionByIdParams): Promise<FinanceException> => {
    return getFinanceExceptionService(id, authorization);
  }
);

export const resolveFinanceException = api(
  { method: "POST", path: "/finance-legal/exceptions/:id/resolve", expose: true },
  async ({ id, authorization }: FinanceExceptionByIdParams): Promise<FinanceException> => {
    return resolveFinanceExceptionService(id, authorization);
  }
);
