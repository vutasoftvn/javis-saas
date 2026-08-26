// services/company/identity/handlers/workforce.handler.ts
import { api, Header } from "encore.dev/api";
import {
  WorkforceMember,
  HireWorkforceMemberServiceParams,
  hireWorkforceMemberRecord,
  getWorkforceMemberRecord,
} from "../services/workforce.service";

export { WorkforceMember };

export interface HireWorkforceMemberParams extends Omit<HireWorkforceMemberServiceParams, "authorization"> {
  authorization?: Header<"Authorization">;
}

export const hireWorkforceMember = api(
  { method: "POST", path: "/identity/workforce-members", expose: true },
  async (params: HireWorkforceMemberParams): Promise<WorkforceMember> => {
    return hireWorkforceMemberRecord(params);
  }
);

export const getWorkforceMember = api(
  { method: "GET", path: "/identity/workforce-members/:id", expose: true },
  async ({
    id,
    authorization,
  }: {
    id: string;
    authorization?: Header<"Authorization">;
  }): Promise<WorkforceMember> => {
    return getWorkforceMemberRecord({ id, authorization });
  }
);
