import { requireCosaInternalUrl, requireCosaServiceToken } from "../../../shared/events/service-identity";

export interface DispatchKickoffSuggestionPayload {
  workspaceId: string;
  projectId: string;
  runId: string;
  targetCustomer: string;
  problemStatement: string;
  evidenceLevel: string;
  selectedStage: string;
  stageDurationWeeks: number;
}

export type DispatchKickoffSuggestionRunner = (
  payload: DispatchKickoffSuggestionPayload
) => Promise<void>;

let customRunner: DispatchKickoffSuggestionRunner | null = null;

export function setCustomKickoffSuggestionRunner(runner: DispatchKickoffSuggestionRunner | null): void {
  customRunner = runner;
}

export async function dispatchKickoffSuggestionRun(
  payload: DispatchKickoffSuggestionPayload
): Promise<void> {
  if (customRunner) {
    await customRunner(payload);
    return;
  }

  const cosaBaseUrl = requireCosaInternalUrl();
  const serviceToken = requireCosaServiceToken();

  const response = await fetch(`${cosaBaseUrl}/agent/kickoff/first-week-suggestion`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Cosa-Service-Token": serviceToken,
    },
    body: JSON.stringify({
      workspace_id: payload.workspaceId,
      project_id: payload.projectId,
      run_id: payload.runId,
      target_customer: payload.targetCustomer,
      problem_statement: payload.problemStatement,
      evidence_level: payload.evidenceLevel,
      selected_stage: payload.selectedStage,
      stage_duration_weeks: payload.stageDurationWeeks,
    }),
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`COSA returned ${response.status}: ${errText}`);
  }
}
