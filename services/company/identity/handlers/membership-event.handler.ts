import { api, Header } from "encore.dev/api";
import { requireWorkerServiceAuth } from "../../shared/auth/worker-service-auth";
import {
  applyMembershipProjection,
  type ApplyMembershipProjectionResult,
  type MembershipProjectionEvent,
} from "../services/membership-projection.service";

export interface IngestMembershipEventRequest {
  event: MembershipProjectionEvent;
  serviceToken?: Header<"X-Service-Token">;
  authorization?: Header<"Authorization">;
}

// Consumer của `organization.membership.changed.v1` (spec 2026-09-25 §6):
// relay nội bộ ký JWT worker, Company áp projection forward-only theo
// membershipVersion và tombstone membership bị thu hồi.
export const ingestMembershipEvent = api(
  { method: "POST", path: "/internal/identity/membership-events", expose: true },
  async (req: IngestMembershipEventRequest): Promise<ApplyMembershipProjectionResult> => {
    await requireWorkerServiceAuth({
      serviceToken: req.serviceToken,
      authorization: req.authorization,
    });
    return applyMembershipProjection(req.event);
  }
);
