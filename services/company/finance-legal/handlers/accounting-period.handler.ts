import { api, Header } from "encore.dev/api";
import {
  AccountingPeriod,
  OpenAccountingPeriodParams as BaseOpenAccountingPeriodParams,
  openAccountingPeriodService,
  getAccountingPeriodService,
  closeAccountingPeriodService,
} from "../services/accounting-period.service";

export { AccountingPeriod };

export interface OpenAccountingPeriodParams extends BaseOpenAccountingPeriodParams {
  authorization?: Header<"Authorization">;
}

export interface AccountingPeriodByIdParams {
  id: number;
  authorization?: Header<"Authorization">;
}

export const openAccountingPeriod = api(
  { method: "POST", path: "/finance-legal/accounting-periods", expose: true },
  async (params: OpenAccountingPeriodParams): Promise<AccountingPeriod> => {
    return openAccountingPeriodService(params, params.authorization);
  }
);

export const getAccountingPeriod = api(
  { method: "GET", path: "/finance-legal/accounting-periods/:id", expose: true },
  async ({ id, authorization }: AccountingPeriodByIdParams): Promise<AccountingPeriod> => {
    return getAccountingPeriodService(id, authorization);
  }
);

export const closeAccountingPeriod = api(
  { method: "POST", path: "/finance-legal/accounting-periods/:id/close", expose: true },
  async ({ id, authorization }: AccountingPeriodByIdParams): Promise<AccountingPeriod> => {
    return closeAccountingPeriodService(id, authorization);
  }
);
