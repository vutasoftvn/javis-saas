import { api, APIError } from "encore.dev/api";
import { isStagingOrProd } from "../../shared/env";
import { seedE2eComplianceScenario, type E2eSeedScenario } from "../services/ai-compliance-e2e-seed.service";

export interface SeedE2eComplianceRequest {
  scenario: E2eSeedScenario;
  /**
   * Task 7 (2026-08-30) — ép `system_key` khớp đúng `AgentSpec.id` sản xuất
   * thật (vd. `cosa.agents.operations`), để test round-trip qua route HTTP
   * thật `POST /agent/conversations/{id}/messages` → worker → SpecResolver
   * (dùng spec cố định, không random) → ComplianceResolver không bị 404
   * "system không tồn tại". Xem `E2eSeedOptions.systemKey`.
   */
  systemKey?: string;
  /** Capability bổ sung AgentSpec thật yêu cầu ngoài 2 capability mặc định. */
  additionalBoundCapabilityIds?: string[];
}

// Khai báo tường minh (không suy diễn qua re-export type từ service module
// khác) — Encore phân tích tĩnh AST để sinh response schema, khai báo rời
// rạc qua barrel import đã từng khiến body trả về rỗng dù `code=ok`.
export interface SeedE2eComplianceResponse {
  workspaceId: string;
  founderId: string;
  systemKey: string;
  deploymentId: string;
  assessmentId: string;
  providerProfileId: string;
  dataProfileId: string;
  subjectReference?: string;
  authorizationId?: string;
}

/**
 * CHỈ dùng cho `tests/e2e/test_ai_compliance_company_http.py` (Task 10) —
 * seed dữ liệu AI compliance THẬT (qua đúng service function governance
 * thật, không phải mock) vào Company service đang chạy thật
 * (`encore run`), để Python E2E test gọi HTTP thật vào route runtime
 * production mà không phải tự dựng lại toàn bộ chuỗi governance qua HTTP
 * public (chưa có route public cho từng bước approve/suspend).
 *
 * Fail-closed 2 lớp — không có đường nào bật được ngoài ý muốn:
 *   1. isStagingOrProd() luôn chặn cứng, bất kể cờ bật.
 *   2. Thiếu `E2E_TEST_SEED_ENABLED=1` (không set trong dev/CI thường) thì
 *      vẫn từ chối — chỉ Makefile target `ai-compliance-production-gate`
 *      /workflow CI tương ứng mới set cờ này khi khởi Company service riêng
 *      cho gate, không phải khi chạy `make dev`.
 */
export const seedE2eComplianceApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/_e2e/seed", expose: false },
  async (req: SeedE2eComplianceRequest): Promise<SeedE2eComplianceResponse> => {
    if (isStagingOrProd()) {
      throw APIError.permissionDenied("E2E seed endpoint is never available in staging/production");
    }
    if (process.env.E2E_TEST_SEED_ENABLED !== "1") {
      throw APIError.permissionDenied(
        "E2E seed endpoint disabled — set E2E_TEST_SEED_ENABLED=1 only for the ai-compliance-production-gate test run"
      );
    }

    const result = await seedE2eComplianceScenario(req.scenario, {
      systemKey: req.systemKey,
      additionalBoundCapabilityIds: req.additionalBoundCapabilityIds,
    });
    return {
      workspaceId: result.workspaceId,
      founderId: result.founderId,
      systemKey: result.systemKey,
      deploymentId: result.deploymentId,
      assessmentId: result.assessmentId,
      providerProfileId: result.providerProfileId,
      dataProfileId: result.dataProfileId,
      subjectReference: result.subjectReference,
      authorizationId: result.authorizationId,
    };
  }
);
