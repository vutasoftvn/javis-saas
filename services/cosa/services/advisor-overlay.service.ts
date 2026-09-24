import jwt from "jsonwebtoken";
import { APIError } from "encore.dev/api";
import { isStagingOrProd } from "../shared/env";
import {
  ADVISOR_OVERLAY_CATALOG,
  type AdvisorOverlayDefinition,
} from "../shared/contracts/executive-advisor-overlays.generated";

const DEV_ADVISOR_OVERLAY_SERVICE_SECRET = "cosa-advisor-overlay-service-dev-secret-change-in-prod";
const HEX64 = /^[0-9a-f]{64}$/;

export const ADVISOR_OVERLAY_TOKEN_AUDIENCE = "cosa_advisor_overlay";
export const ADVISOR_OVERLAY_TOKEN_ISSUER = "cosa_company";

/**
 * Secret một chiều: `services/company` ký, `services/cosa` verify. Không tái dùng
 * JWT_SECRET / *_DELEGATION_SECRET (CLAUDE.md: mỗi secret đúng 1 chiều).
 */
export function getAdvisorOverlayServiceSecret(): string {
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

export function verifyAdvisorOverlayServiceToken(authorization: string | undefined): void {
  const token = authorization?.startsWith("Bearer ") ? authorization.slice(7).trim() : "";
  if (!token) {
    throw APIError.unauthenticated("missing advisor overlay service token");
  }
  try {
    jwt.verify(token, getAdvisorOverlayServiceSecret(), {
      audience: ADVISOR_OVERLAY_TOKEN_AUDIENCE,
      issuer: ADVISOR_OVERLAY_TOKEN_ISSUER,
    });
  } catch {
    throw APIError.unauthenticated("invalid or expired advisor overlay service token");
  }
}

function assertOverlayIntegrity(roleKey: string, overlay: AdvisorOverlayDefinition): void {
  const valid =
    overlay.roleKey === roleKey &&
    overlay.advisoryOnly === true &&
    overlay.overlaySpecId.length > 0 &&
    overlay.overlaySpecVersion.length > 0 &&
    HEX64.test(overlay.overlayDefinitionHash) &&
    overlay.skillPins.length > 0 &&
    overlay.skillPins.every((p) => HEX64.test(p.definitionHash));
  if (!valid) {
    throw APIError.failedPrecondition(
      `ADVISOR_OVERLAY_CONTRACT_MISMATCH: overlay for role '${roleKey}' is not an exact published identity`
    );
  }
}

/**
 * Read-only: chỉ đọc catalog overlay built-in đã publish; không có đường mutate registry.
 * `catalog` chỉ để test tiêm dữ liệu sai lệch — runtime luôn dùng catalog generated.
 */
export function resolveAdvisorOverlayIdentity(
  roleKey: string,
  catalog: Readonly<Record<string, AdvisorOverlayDefinition>> = ADVISOR_OVERLAY_CATALOG
): AdvisorOverlayDefinition {
  const overlay = Object.prototype.hasOwnProperty.call(catalog, roleKey) ? catalog[roleKey] : undefined;
  if (!overlay) {
    throw APIError.notFound(`ADVISOR_OVERLAY_NOT_FOUND: no published overlay for role '${roleKey}'`);
  }
  assertOverlayIntegrity(roleKey, overlay);
  return overlay;
}
