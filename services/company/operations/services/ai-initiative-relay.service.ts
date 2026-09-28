import {
  claimDueOutboxEvents,
  completeOutboxEvent,
  failOutboxEvent,
} from "../../shared/events/outbox.repository";
import { AI_INITIATIVE_PROMOTED_EVENT_TYPE } from "../../events/outbox-relay.service";
import { publishPromotionSnapshotToCosa, AiInitiativePromotionSnapshot } from "./ai-initiative-cosa.client";

/**
 * Dedicated relay for `ai.initiative.promoted.v1` outbox events (Task 6/13,
 * plan 2026-09-28-stage-adaptive-ai-operating-system).
 *
 * `transitionAiInitiative` (ai-initiative-transition.service.ts) only appends
 * the outbox event inside its own short DB transaction — it never calls COSA
 * directly (matches the plan's "delivery retries only the callback" design).
 * This relay is the actual callback: it claims due events of this specific
 * type only (never the generic automation events the existing
 * `outbox-relay.service.ts` handles) and calls
 * `publishPromotionSnapshotToCosa`, which POSTs to COSA's
 * `/internal/ai-initiatives/snapshots` (see ai-initiative-cosa.client.ts).
 *
 * `completeOutboxEvent` only on COSA's genuine 200 (accepted/already_consumed);
 * a 403 (scope/hash rejection) is also terminal — retrying an event COSA
 * rejected for cause will never succeed, and infinite-retrying it would just
 * burn the retry budget that a real transient failure needs.
 */
export interface AiInitiativeRelayDeps {
  batchLimit: number;
}

interface AiInitiativePromotedPayload {
  snapshot: {
    initiativeId: string;
    initiativeRevision: number;
    workspaceId: string;
    projectId: string;
    lifecycleState: string;
    riskTier: string;
    autonomyTier: string;
    decisionId: string;
    decisionHash: string;
    valueContractRevision?: number | null;
    dataReadinessRevision?: number | null;
    budgetPolicyRevision?: number | null;
    evaluationSuiteRevision?: number | null;
    dataReadinessStatus?: string | null;
    retrievalMode?: string | null;
    pins?: Record<string, unknown>;
  };
}

export async function runAiInitiativeRelayOnce(deps: AiInitiativeRelayDeps): Promise<void> {
  const rows = await claimDueOutboxEvents("ai-initiative-relay", deps.batchLimit, undefined, {
    eventType: AI_INITIATIVE_PROMOTED_EVENT_TYPE,
  });

  for (const row of rows) {
    try {
      const payload = row.envelope.payload as AiInitiativePromotedPayload;
      const s = payload.snapshot;
      const snapshot: AiInitiativePromotionSnapshot = {
        initiativeId: s.initiativeId,
        initiativeRevision: s.initiativeRevision,
        workspaceId: s.workspaceId,
        projectId: s.projectId,
        lifecycleState: s.lifecycleState,
        riskTier: s.riskTier,
        autonomyTier: s.autonomyTier,
        decisionId: s.decisionId,
        decisionHash: s.decisionHash,
        valueContractRevision: s.valueContractRevision ?? null,
        dataReadinessRevision: s.dataReadinessRevision ?? null,
        budgetPolicyRevision: s.budgetPolicyRevision ?? null,
        evaluationSuiteRevision: s.evaluationSuiteRevision ?? null,
        dataReadinessStatus: (s.dataReadinessStatus as any) ?? null,
        retrievalMode: (s.retrievalMode as any) ?? null,
        pins: s.pins ?? {},
      };

      const result = await publishPromotionSnapshotToCosa(snapshot);
      if (result.accepted) {
        await completeOutboxEvent(row.eventId, row.claimToken!);
      } else {
        await failOutboxEvent(row.eventId, row.claimToken!, `not accepted: ${result.status}`);
      }
    } catch (e: any) {
      // APIError.permissionDenied from publishPromotionSnapshotToCosa (COSA 403 —
      // scope/hash rejection) is terminal, not transient: retrying would never
      // succeed because the payload itself is what COSA rejected.
      const code = e?.code || e?.name;
      if (code === "permission_denied" || code === "PermissionDenied") {
        await completeOutboxEvent(row.eventId, row.claimToken!);
      } else {
        await failOutboxEvent(row.eventId, row.claimToken!, String(e?.message || e));
      }
    }
  }
}

export async function aiInitiativeRelayTick(): Promise<void> {
  await runAiInitiativeRelayOnce({
    batchLimit: Number(process.env.COSA_RELAY_BATCH_LIMIT || 50),
  });
}
