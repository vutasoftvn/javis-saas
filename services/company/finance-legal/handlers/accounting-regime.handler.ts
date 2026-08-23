import { api, Header } from "encore.dev/api";
import {
  AccountingFiscalProfile,
  CreateFiscalProfileRequest,
  AccountingCoaMapping,
  CreateCoaMappingRequest,
  createFiscalProfileService,
  listFiscalProfilesService,
  createCoaMappingService,
} from "../services/accounting-regime.service";

export { AccountingFiscalProfile, CreateFiscalProfileRequest, AccountingCoaMapping, CreateCoaMappingRequest };

// ─── Fiscal Profiles Endpoints ───

export const createFiscalProfile = api(
  { expose: true, method: "POST", path: "/finance-legal/fiscal-profiles" },
  async (req: CreateFiscalProfileRequest & { authorization?: Header<"Authorization"> }): Promise<AccountingFiscalProfile> => {
    return createFiscalProfileService(req, req.authorization);
  }
);

export const listFiscalProfiles = api(
  { expose: true, method: "GET", path: "/finance-legal/workspaces/:workspaceId/fiscal-profiles" },
  async (params: {
    workspaceId: number;
    authorization?: Header<"Authorization">;
  }): Promise<{ profiles: AccountingFiscalProfile[] }> => {
    const profiles = await listFiscalProfilesService(params.workspaceId, params.authorization);
    return { profiles };
  }
);

// ─── COA Mapping Endpoints (bảng tra cứu quy đổi tài khoản dùng chung giữa
// các chế độ kế toán, không gắn workspace cụ thể — không cần workspace check) ───

export const createCoaMapping = api(
  { expose: true, method: "POST", path: "/finance-legal/coa-mappings" },
  async (req: CreateCoaMappingRequest): Promise<AccountingCoaMapping> => {
    return createCoaMappingService(req);
  }
);
