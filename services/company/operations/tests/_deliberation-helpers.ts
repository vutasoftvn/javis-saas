import { TenantContext } from "../../shared/types/tenant_context";
import {
  getDeliberation,
  recordExecutiveAnalysisCallback,
  type SelectedAdvisorExecutionPin,
} from "../services/executive-deliberation.service";
import { computeDeploymentPinHash, computeOverlayPinHash } from "../services/executive-pin-hash";

/**
 * Giả lập worker gửi callback COMPLETED cho mọi role của active frame — đưa
 * deliberation tới AWAITING_FOUNDER đúng như đường chạy thật (quyết định Founder
 * chỉ hợp lệ sau khi có phân tích).
 */
export async function completeAllAnalyses(
  ctx: TenantContext,
  projectId: string,
  deliberationId: string
): Promise<void> {
  const details = await getDeliberation(ctx, projectId, deliberationId);
  const frameVersion = details.activeFrame!.frameVersion;
  const pins = details.activeFrame!.selectedRoles as SelectedAdvisorExecutionPin[];
  for (const pin of pins) {
    await recordExecutiveAnalysisCallback(ctx.workspaceId, projectId, deliberationId, {
      kind: "executive.analysis.completed.v1",
      deliberation_id: deliberationId,
      frame_version: frameVersion,
      role_key: pin.roleKey,
      deployment_pin_hash: computeDeploymentPinHash(pin.deployment),
      overlay_pin_hash: computeOverlayPinHash(pin.overlay),
      descriptor: { run_id: `run-${pin.roleKey}-${frameVersion}`, conclusion: "ok", evidence_claims: [] },
    });
  }
}
