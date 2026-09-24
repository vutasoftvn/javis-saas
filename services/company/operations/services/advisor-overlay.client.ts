import jwt from "jsonwebtoken";
import { APIError } from "encore.dev/api";
import { isStagingOrProd } from "../../shared/env";
import { getPlatformUrl } from "../../identity/services/platform.client";
import {
  ADVISOR_OVERLAY_CATALOG,
  type AdvisorOverlayDefinition,
} from "../../shared/contracts/executive-advisor-overlays.generated";

const DEV_ADVISOR_OVERLAY_SERVICE_SECRET = "cosa-advisor-overlay-service-dev-secret-change-in-prod";
const REQUEST_TIMEOUT_MS = 5000;

/**
 * Cùng giá trị/tên biến với `services/cosa/services/advisor-overlay.service.ts`
 * (Company ký, COSA verify — một chiều, không tái dùng secret khác).
 */
function getAdvisorOverlayServiceSecret(): string {
  const secret = process.env.COSA_ADVISOR_OVERLAY_SERVICE_SECRET;
  if (isStagingOrProd()) {
    if (!secret || secret === DEV_ADVISOR_OVERLAY_SERVICE_SECRET || secret.length < 32) {
      throw APIError.internal(
        "COSA_ADVISOR_OVERLAY_SERVICE_SECRET must be explicitly set with >= 32 characters in staging/production"
      );
    }
    return secret;
  }
  return secret || DEV_ADVISOR_OVERLAY_SERVICE_SECRET;
}

function sameOverlay(a: AdvisorOverlayDefinition, b: AdvisorOverlayDefinition): boolean {
  // So từng trường (không so chuỗi JSON: thứ tự khóa không được ảnh hưởng kết quả).
  return (
    a.roleKey === b.roleKey &&
    a.overlaySpecId === b.overlaySpecId &&
    a.overlaySpecVersion === b.overlaySpecVersion &&
    a.overlayDefinitionHash === b.overlayDefinitionHash &&
    a.requiredProfileKey === b.requiredProfileKey &&
    a.advisoryOnly === b.advisoryOnly &&
    a.skillPins.length === b.skillPins.length &&
    a.skillPins.every(
      (pin, i) =>
        pin.skillId === b.skillPins[i].skillId &&
        pin.version === b.skillPins[i].version &&
        pin.definitionHash === b.skillPins[i].definitionHash
    )
  );
}

/**
 * Hỏi COSA Control Plane exact overlay identity đã publish cho 1 role. Fail-closed:
 * COSA không trả được, hoặc identity lệch contract Company đã generate → không frame.
 * Không bao giờ fallback sang AgentSpec profile, role string hay "latest".
 */
export async function fetchAdvisorOverlayIdentity(
  workspaceId: string,
  roleKey: string
): Promise<AdvisorOverlayDefinition> {
  const token = jwt.sign({ sub: workspaceId }, getAdvisorOverlayServiceSecret(), {
    audience: "cosa_advisor_overlay",
    issuer: "cosa_company",
    expiresIn: "60s",
  });

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(
      `${getPlatformUrl()}/platform/internal/executive-advisor-overlay?roleKey=${encodeURIComponent(roleKey)}`,
      { method: "GET", headers: { Authorization: `Bearer ${token}` }, signal: controller.signal }
    );
  } catch (err) {
    throw APIError.unavailable(
      `ADVISOR_OVERLAY_UNAVAILABLE: cannot resolve overlay for role '${roleKey}' from control-plane`,
      err instanceof Error ? err : undefined
    );
  } finally {
    clearTimeout(timeout);
  }

  if (!res.ok) {
    throw APIError.failedPrecondition(
      `ADVISOR_OVERLAY_UNAVAILABLE: control-plane returned HTTP ${res.status} for role '${roleKey}'`
    );
  }

  const body = (await res.json()) as { overlay?: AdvisorOverlayDefinition };
  const expected = ADVISOR_OVERLAY_CATALOG[roleKey];
  if (!body.overlay || !expected || !sameOverlay(body.overlay, expected)) {
    throw APIError.failedPrecondition(
      `ADVISOR_OVERLAY_MISMATCH: control-plane overlay for role '${roleKey}' does not match the executive contract`
    );
  }
  return body.overlay;
}
