import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { outcomeAnalysisRequests, outcomeAssessments, krContributionAssessments } = schema;

// Narrow capability duy nhất Outcome Analyst được phép ghi (spec §9.2).
export const CAP_OUTCOME_ASSESSMENT_RECORD = "operations.outcome-assessment.record";

/**
 * Ngữ cảnh delegation hẹp mà apps/cosa gửi kèm khi Outcome Analyst ghi
 * assessment. Server verify EXACT workspace + run + request + capability —
 * KHÔNG chấp nhận task ID tùy ý từ model text (spec §9.2).
 */
export interface DelegatedCapabilityContext {
  workspaceId: string;
  runId: string;
  requestId: string;
  capabilityIds: string[];
}

export interface RecordOutcomeAssessmentInput {
  requestId: string;
  taskResultId: string;
  contractId: string;
  agentInstanceId: string;
  assignmentId: string;
  skillId: string;
  skillVersion: string;
  definitionHash: string;
  rubricVersion?: string;
  evidenceUsedRefs: string[];
  missingEvidenceRefs: string[];
  expectedVsActual?: Record<string, unknown>;
  criterionScores: Record<string, number>;
  confidence: number;
  riskFlags?: string[];
  causalLimits?: string[];
  nextActionProposals?: string[];
  recommendation: "ACCEPT" | "REWORK" | "REJECT" | "NEEDS_HUMAN_DECISION";
  krContribution?: {
    krLinkId?: string;
    keyResultId?: string;
    claimedEffect?: Record<string, unknown>;
    evidenceRefs?: string[];
    causalConfidence?: number;
  };
}

export interface OutcomeAssessmentView {
  id: string;
  requestId: string;
  taskResultId: string;
  recommendation: string;
  status: string;
  confidence: number | null;
  createdAt: string;
}

/**
 * Ghi một Outcome Assessment. CHỈ chấp nhận request đã được router chọn:
 * delegation phải khớp workspace + run_id đã pin trên request và mang
 * capability `operations.outcome-assessment.record`. Không advance task, không
 * write KR — KR contribution chỉ ghi state PROPOSED.
 */
export async function recordOutcomeAssessment(
  input: RecordOutcomeAssessmentInput,
  delegated: DelegatedCapabilityContext
): Promise<OutcomeAssessmentView> {
  if (!delegated.capabilityIds.includes(CAP_OUTCOME_ASSESSMENT_RECORD)) {
    throw APIError.permissionDenied(
      `delegation missing capability ${CAP_OUTCOME_ASSESSMENT_RECORD}`
    );
  }
  if (delegated.requestId !== input.requestId) {
    throw APIError.permissionDenied("delegation request attribution mismatch");
  }

  const wsId = BigInt(delegated.workspaceId);
  const [req] = await db
    .select()
    .from(outcomeAnalysisRequests)
    .where(
      and(
        eq(outcomeAnalysisRequests.id, BigInt(input.requestId)),
        eq(outcomeAnalysisRequests.workspaceId, wsId)
      )
    )
    .limit(1);
  if (!req) throw APIError.notFound("outcome analysis request not found in workspace");

  // Run phải khớp run mà router đã pin lên request (nếu đã pin).
  if (req.selectedRunId && req.selectedRunId !== delegated.runId) {
    throw APIError.permissionDenied("delegation request attribution mismatch (run_id)");
  }
  if (req.taskResultId.toString() !== input.taskResultId) {
    throw APIError.invalidArgument("taskResultId does not match the analysis request");
  }

  return db.transaction(async (tx) => {
    const [row] = await tx
      .insert(outcomeAssessments)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        requestId: BigInt(input.requestId),
        taskResultId: BigInt(input.taskResultId),
        contractId: BigInt(input.contractId),
        agentInstanceId: input.agentInstanceId,
        assignmentId: input.assignmentId,
        runId: delegated.runId,
        skillId: input.skillId,
        skillVersion: input.skillVersion,
        definitionHash: input.definitionHash,
        rubricVersion: input.rubricVersion ?? null,
        evidenceUsedRefs: input.evidenceUsedRefs ?? [],
        missingEvidenceRefs: input.missingEvidenceRefs ?? [],
        expectedVsActual: input.expectedVsActual ?? {},
        criterionScores: input.criterionScores ?? {},
        confidence: input.confidence,
        riskFlags: input.riskFlags ?? [],
        causalLimits: input.causalLimits ?? [],
        nextActionProposals: input.nextActionProposals ?? [],
        recommendation: input.recommendation,
        status: "READY",
      })
      .returning();
    if (!row) throw APIError.internal("failed to record outcome assessment");

    if (input.krContribution) {
      await tx.insert(krContributionAssessments).values({
        id: generateSnowflake(),
        workspaceId: wsId,
        assessmentId: row.id,
        krLinkId: input.krContribution.krLinkId ? BigInt(input.krContribution.krLinkId) : null,
        keyResultId: input.krContribution.keyResultId
          ? BigInt(input.krContribution.keyResultId)
          : null,
        state: "PROPOSED", // KHÔNG BAO GIỜ tự VERIFIED (spec §8.3)
        claimedEffect: input.krContribution.claimedEffect ?? {},
        evidenceRefs: input.krContribution.evidenceRefs ?? [],
        causalConfidence: input.krContribution.causalConfidence ?? null,
      });
    }

    await tx
      .update(outcomeAnalysisRequests)
      .set({ status: "READY", selectedRunId: delegated.runId, updatedAt: new Date() })
      .where(eq(outcomeAnalysisRequests.id, BigInt(input.requestId)));

    return {
      id: row.id.toString(),
      requestId: input.requestId,
      taskResultId: input.taskResultId,
      recommendation: row.recommendation,
      status: row.status,
      confidence: row.confidence,
      createdAt: row.createdAt.toISOString(),
    };
  });
}

/** Test/router helper: pin employee/assignment/run/skill lên request trước khi analyst ghi. */
export async function pinAnalysisRequestSelection(
  requestId: string,
  workspaceId: string,
  selection: {
    agentInstanceId: string;
    assignmentId: string;
    runId: string;
    skillId: string;
    skillVersion: string;
    definitionHash: string;
  }
): Promise<void> {
  await db
    .update(outcomeAnalysisRequests)
    .set({
      status: "RUNNING",
      selectedAgentInstanceId: selection.agentInstanceId,
      selectedAssignmentId: selection.assignmentId,
      selectedRunId: selection.runId,
      skillId: selection.skillId,
      skillVersion: selection.skillVersion,
      definitionHash: selection.definitionHash,
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(outcomeAnalysisRequests.id, BigInt(requestId)),
        eq(outcomeAnalysisRequests.workspaceId, BigInt(workspaceId))
      )
    );
}

export async function loadAssessmentForResult(
  taskResultId: string,
  workspaceId: string
): Promise<{ id: string; status: string } | null> {
  const [row] = await db
    .select({ id: outcomeAssessments.id, status: outcomeAssessments.status })
    .from(outcomeAssessments)
    .where(
      and(
        eq(outcomeAssessments.taskResultId, BigInt(taskResultId)),
        eq(outcomeAssessments.workspaceId, BigInt(workspaceId))
      )
    )
    .limit(1);
  return row ? { id: row.id.toString(), status: row.status } : null;
}
