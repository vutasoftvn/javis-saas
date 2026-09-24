import { createHash } from "node:crypto";
import type { AdvisorOverlayPin, ProjectDeploymentPin } from "./executive-deliberation.service";

/**
 * Hash định danh pin dùng để đối chiếu callback với frame đã persist. Định dạng
 * (các trường nối bằng "\n", đúng thứ tự) phải khớp `apps/cosa/company/executive_pin_hash.py`.
 */
function sha256(parts: readonly string[]): string {
  return createHash("sha256").update(parts.join("\n"), "utf8").digest("hex");
}

export function computeDeploymentPinHash(pin: ProjectDeploymentPin): string {
  return sha256([
    pin.projectAgentDeploymentId,
    pin.profileKey,
    pin.specId,
    pin.specVersion,
    pin.specHash,
  ]);
}

export function computeOverlayPinHash(pin: AdvisorOverlayPin): string {
  return sha256([
    pin.roleKey,
    pin.overlaySpecId,
    pin.overlaySpecVersion,
    pin.overlaySpecHash,
    ...pin.skillPins.map((s) => `${s.skillId}@${s.version}#${s.definitionHash}`),
  ]);
}
