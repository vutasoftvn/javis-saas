import { api, Header, Query } from "encore.dev/api";
import {
  resolveAdvisorOverlayIdentity,
  verifyAdvisorOverlayServiceToken,
} from "../services/advisor-overlay.service";
import type { AdvisorOverlayDefinition } from "../shared/contracts/executive-advisor-overlays.generated";

export interface GetAdvisorOverlayIdentityRequest {
  roleKey: Query<string>;
  authorization?: Header<"Authorization">;
}

export interface GetAdvisorOverlayIdentityResponse {
  overlay: AdvisorOverlayDefinition;
}

/**
 * Company (Encore app riêng) gọi qua HTTP thật nên không dùng `expose: false`;
 * `auth: false` ở Gateway vì token là service token ký bởi Company
 * (`COSA_ADVISOR_OVERLAY_SERVICE_SECRET`), verify thủ công trong service.
 * Trình duyệt không có secret này nên luôn bị từ chối `unauthenticated`.
 */
export const getAdvisorOverlayIdentity = api(
  { method: "GET", path: "/platform/internal/executive-advisor-overlay", expose: true, auth: false },
  async (params: GetAdvisorOverlayIdentityRequest): Promise<GetAdvisorOverlayIdentityResponse> => {
    verifyAdvisorOverlayServiceToken(params.authorization);
    return { overlay: resolveAdvisorOverlayIdentity(params.roleKey) };
  }
);
