export type AiInitiativeGateStatus =
  | "APPROVAL_STATUS_REQUIRED"
  | "PROJECT_CONTEXT_REQUIRED"
  | "OWNER_REQUIRED"
  | "PROBLEM_STATEMENT_REQUIRED"
  | "INTENDED_OUTCOME_REQUIRED"
  | "BASELINE_AND_METRIC_REQUIRED"
  | "DATA_READINESS_ASSESSMENT_REQUIRED"
  | "DATA_READINESS_BLOCKS_PROMOTION"
  | "DATA_READINESS_NOT_READY"
  | "EVALUATION_SUITE_REQUIRED"
  | "BUDGET_POLICY_REQUIRED"
  | "HUMAN_ESCALATION_ROUTE_REQUIRED"
  | "ROLLBACK_PROCEDURE_REQUIRED"
  | "UNSUPPORTED_AUTONOMY_TIER"
  | "INVALID_LIFECYCLE_TRANSITION";

export interface AiInitiativeGateInput {
  fromState: string;
  toState: string;
  projectStage?: string;
  riskTier: string;
  autonomyTier: string;
  approvalStatus: string;
  legacyRemediationState?: string;
  hasProblemStatement?: boolean;
  hasIntendedOutcome?: boolean;
  hasOwner?: boolean;
  hasValueContract?: boolean;
  hasBaseline?: boolean;
  hasDataAssessment?: boolean;
  dataAssessmentStatus?: string;
  hasEvaluationSuite?: boolean;
  hasBudgetPolicy?: boolean;
  hasHumanEscalationRoute?: boolean;
  hasRollbackPauseProcedure?: boolean;
}

export function evaluateAiInitiativePromotionGates(
  input: AiInitiativeGateInput
): readonly AiInitiativeGateStatus[] {
  const gates: AiInitiativeGateStatus[] = [];

  if (input.legacyRemediationState === "NEEDS_REBIND") {
    gates.push("PROJECT_CONTEXT_REQUIRED");
  }

  if (input.autonomyTier === "A3") {
    gates.push("UNSUPPORTED_AUTONOMY_TIER");
  }

  if (input.fromState === "RETIRED") {
    gates.push("INVALID_LIFECYCLE_TRANSITION");
    return gates;
  }

  if (input.toState === "PAUSED" || input.toState === "RETIRED") {
    return gates;
  }

  const edge = `${input.fromState}->${input.toState}`;

  switch (edge) {
    case "DISCOVER->PILOT": {
      if (input.approvalStatus !== "APPROVED") {
        gates.push("APPROVAL_STATUS_REQUIRED");
      }
      if (!input.hasOwner) {
        gates.push("OWNER_REQUIRED");
      }
      if (!input.hasProblemStatement) {
        gates.push("PROBLEM_STATEMENT_REQUIRED");
      }
      if (!input.hasIntendedOutcome) {
        gates.push("INTENDED_OUTCOME_REQUIRED");
      }
      break;
    }

    case "PILOT->VALIDATE": {
      if (!input.hasValueContract || !input.hasBaseline) {
        gates.push("BASELINE_AND_METRIC_REQUIRED");
      }
      if (!input.hasOwner) {
        gates.push("OWNER_REQUIRED");
      }
      if (!input.hasDataAssessment) {
        gates.push("DATA_READINESS_ASSESSMENT_REQUIRED");
      }
      if (input.dataAssessmentStatus === "NOT_READY") {
        gates.push("DATA_READINESS_BLOCKS_PROMOTION");
      }
      break;
    }

    case "VALIDATE->SCALE_CANDIDATE": {
      if (!input.hasEvaluationSuite) {
        gates.push("EVALUATION_SUITE_REQUIRED");
      }
      if (!input.hasBudgetPolicy) {
        gates.push("BUDGET_POLICY_REQUIRED");
      }
      if (input.dataAssessmentStatus !== "READY") {
        gates.push("DATA_READINESS_NOT_READY");
      }
      break;
    }

    case "SCALE_CANDIDATE->SCALED": {
      if (!input.hasHumanEscalationRoute) {
        gates.push("HUMAN_ESCALATION_ROUTE_REQUIRED");
      }
      if (!input.hasRollbackPauseProcedure) {
        gates.push("ROLLBACK_PROCEDURE_REQUIRED");
      }
      break;
    }

    case "PAUSED->PILOT":
    case "PAUSED->VALIDATE":
    case "PAUSED->SCALE_CANDIDATE": {
      // Remediation resume edge
      break;
    }

    default: {
      gates.push("INVALID_LIFECYCLE_TRANSITION");
      break;
    }
  }

  return gates;
}
