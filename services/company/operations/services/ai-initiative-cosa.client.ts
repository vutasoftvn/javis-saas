import { APIError } from "encore.dev/api";
import { requireCosaInternalUrl, requireCosaServiceToken } from "../../shared/events/service-identity";
import { createHash } from "node:crypto";

export interface AiInitiativePromotionPins {
  agentSpecRef?: string | null;
  workflowRef?: string | null;
  modelRouteRef?: string | null;
  knowledgeSnapshotRef?: string | null;
}

export interface AiInitiativePromotionSnapshot {
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
  // Task 11 — carried alongside dataReadinessRevision so COSA's knowledge
  // readiness gate (apps/cosa/knowledge/initiative_readiness.py) can decide
  // NOT_READY/CONDITIONAL/READY + lexical/semantic without a cross-plane
  // lookup back into Company's strategy.ai_initiative_data_readiness_assessments.
  dataReadinessStatus?: "NOT_READY" | "CONDITIONAL" | "READY" | null;
  retrievalMode?: "none" | "lexical" | "semantic" | null;
  pins: AiInitiativePromotionPins;
}

export function computeDecisionHash(
  decisionId: string,
  revision: number,
  targetState: string,
  workspaceId: string,
  projectId: string
): string {
  // Binds workspace/project scope into the hash so COSA can independently
  // detect a resubmitted decision whose project/workspace was swapped, not
  // just a corrupted decisionId/revision/targetState — see plan Task 6.
  return createHash("sha256")
    .update(`${decisionId}:${revision}:${targetState}:${workspaceId}:${projectId}`)
    .digest("hex");
}

export type PromotionPublisher = (
  snapshot: AiInitiativePromotionSnapshot,
  options?: { cosaBaseUrl?: string; serviceToken?: string }
) => Promise<{ accepted: boolean; status: string; decisionId: string }>;

let customPublisher: PromotionPublisher | null = null;

export function setCustomPromotionPublisher(publisher: PromotionPublisher | null): void {
  customPublisher = publisher;
}

export async function publishPromotionSnapshotToCosa(
  snapshot: AiInitiativePromotionSnapshot,
  options?: { cosaBaseUrl?: string; serviceToken?: string }
): Promise<{ accepted: boolean; status: string; decisionId: string }> {
  if (customPublisher) {
    return customPublisher(snapshot, options);
  }

  const baseUrl = options?.cosaBaseUrl || requireCosaInternalUrl();
  const token = options?.serviceToken || requireCosaServiceToken();

  try {
    const res = await fetch(`${baseUrl}/internal/ai-initiatives/snapshots`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Cosa-Service-Token": token,
        "X-Workspace-Id": snapshot.workspaceId,
        "X-Project-Id": snapshot.projectId,
      },
      body: JSON.stringify({
        initiative_id: snapshot.initiativeId,
        initiative_revision: snapshot.initiativeRevision,
        workspace_id: snapshot.workspaceId,
        project_id: snapshot.projectId,
        lifecycle_state: snapshot.lifecycleState,
        risk_tier: snapshot.riskTier,
        autonomy_tier: snapshot.autonomyTier,
        decision_id: snapshot.decisionId,
        decision_hash: snapshot.decisionHash,
        value_contract_revision: snapshot.valueContractRevision ?? null,
        data_readiness_revision: snapshot.dataReadinessRevision ?? null,
        budget_policy_revision: snapshot.budgetPolicyRevision ?? null,
        evaluation_suite_revision: snapshot.evaluationSuiteRevision ?? null,
        data_readiness_status: snapshot.dataReadinessStatus ?? null,
        retrieval_mode: snapshot.retrievalMode ?? null,
        pins: snapshot.pins || {},
      }),
    });

    if (res.status === 403) {
      throw APIError.permissionDenied("COSA rejected snapshot: foreign project or hash drift");
    }

    if (!res.ok) {
      const text = await res.text();
      throw APIError.internal(`COSA snapshot failed with ${res.status}: ${text}`);
    }

    const data = (await res.json()) as { status: string; accepted?: boolean; decision_id?: string };
    return {
      accepted: data.accepted ?? true,
      status: data.status || "accepted",
      decisionId: data.decision_id || snapshot.decisionId,
    };
  } catch (err: any) {
    if (err instanceof APIError) throw err;
    throw APIError.internal(`publishPromotionSnapshotToCosa failed: ${err.message || String(err)}`);
  }
}
