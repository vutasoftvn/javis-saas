// services/company/identity/handlers/workforce.handler.ts
import { api } from "encore.dev/api";
import {
  WorkforceMember,
  HireWorkforceMemberParams,
  hireWorkforceMemberRecord,
  getWorkforceMemberRecord,
} from "../services/workforce.service";

export { WorkforceMember, HireWorkforceMemberParams };

export const hireWorkforceMember = api(
  { method: "POST", path: "/identity/workforce-members", expose: true },
  async (params: HireWorkforceMemberParams): Promise<WorkforceMember> => {
    return hireWorkforceMemberRecord(params);
  }
);

export const getWorkforceMember = api(
  { method: "GET", path: "/identity/workforce-members/:id", expose: true },
  async ({ id }: { id: string }): Promise<WorkforceMember> => {
    return getWorkforceMemberRecord(id);
  }
);
