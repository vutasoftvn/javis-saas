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
    workspaceId: string;
    authorization?: Header<"Authorization">;
  }): Promise<{ profiles: AccountingFiscalProfile[] }> => {
    const profiles = await listFiscalProfilesService(params.workspaceId, params.authorization);
    return { profiles };
  }
);

// ─── COA Mapping Endpoints ───
// Bảng tra cứu quy đổi tài khoản dùng chung giữa các chế độ kế toán — global
// reference data, không gắn workspace. M1 §4: đây là WRITE vào bảng dùng chung,
// KHÔNG được public/không-auth (bất kỳ ai cũng làm bẩn được). expose:false —
// chỉ service/admin nội bộ; dữ liệu seed qua migration.
export const createCoaMapping = api(
  { expose: false, method: "POST", path: "/finance-legal/coa-mappings" },
  async (req: CreateCoaMappingRequest): Promise<AccountingCoaMapping> => {
    return createCoaMappingService(req);
  }
);
