import { api } from "encore.dev/api";
import {
  Organization,
  CreateOrganizationParams,
  WorkforceMember,
  HireWorkforceMemberParams,
  createOrganizationRecord,
  hireWorkforceMemberRecord,
  getWorkforceMemberRecord,
} from "../services/organization.service";

export { Organization, CreateOrganizationParams, WorkforceMember, HireWorkforceMemberParams };

export const createOrganization = api(
  { method: "POST", path: "/identity/organizations", expose: true },
  async (params: CreateOrganizationParams): Promise<Organization> => {
    return createOrganizationRecord(params);
  }
);

export const hireWorkforceMember = api(
  { method: "POST", path: "/identity/workforce-members", expose: true },
  async (params: HireWorkforceMemberParams): Promise<WorkforceMember> => {
    return hireWorkforceMemberRecord(params);
  }
);

export const getWorkforceMember = api(
  { method: "GET", path: "/identity/workforce-members/:id", expose: true },
  async ({ id }: { id: number }): Promise<WorkforceMember> => {
    return getWorkforceMemberRecord(id);
  }
);
