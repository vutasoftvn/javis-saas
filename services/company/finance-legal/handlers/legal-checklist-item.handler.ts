import { api, Header } from "encore.dev/api";
import {
  LegalChecklistItem,
  CreateChecklistItemParams as BaseCreateChecklistItemParams,
  createChecklistItemService,
  getChecklistItemService,
  completeChecklistItemService,
} from "../services/legal-checklist-item.service";

export { LegalChecklistItem };

export interface CreateChecklistItemParams extends BaseCreateChecklistItemParams {
  authorization?: Header<"Authorization">;
}

export interface ChecklistItemByIdParams {
  id: string;
  authorization?: Header<"Authorization">;
}

export const createChecklistItem = api(
  { method: "POST", path: "/finance-legal/checklist-items", expose: true },
  async (params: CreateChecklistItemParams): Promise<LegalChecklistItem> => {
    return createChecklistItemService(params, params.authorization);
  }
);

export const getChecklistItem = api(
  { method: "GET", path: "/finance-legal/checklist-items/:id", expose: true },
  async ({ id, authorization }: ChecklistItemByIdParams): Promise<LegalChecklistItem> => {
    return getChecklistItemService(id, authorization);
  }
);

export const completeChecklistItem = api(
  { method: "POST", path: "/finance-legal/checklist-items/:id/complete", expose: true },
  async ({ id, authorization }: ChecklistItemByIdParams): Promise<LegalChecklistItem> => {
    return completeChecklistItemService(id, authorization);
  }
);
