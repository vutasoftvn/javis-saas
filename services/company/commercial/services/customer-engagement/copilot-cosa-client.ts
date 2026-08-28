import { APIError } from "encore.dev/api";

export interface DispatchCopilotRunPayload {
  workspaceId: string;
  threadRef: {
    threadId: string;
    contactId: string | null;
  };
  intent: string;
  knowledgeScope: Record<string, unknown>;
  identityVerified: boolean;
  correlationId: string;
}

export interface DispatchCopilotRunResult {
  runId: string;
}

export type DispatchCopilotRunner = (payload: DispatchCopilotRunPayload) => Promise<DispatchCopilotRunResult>;

let customRunner: DispatchCopilotRunner | null = null;

export function setCustomCopilotRunner(runner: DispatchCopilotRunner | null): void {
  customRunner = runner;
}

export async function dispatchCopilotRun(payload: DispatchCopilotRunPayload): Promise<DispatchCopilotRunResult> {
  if (customRunner) {
    return customRunner(payload);
  }

  const cosaBaseUrl = process.env.COSA_INTERNAL_URL || "http://127.0.0.1:8000";
  const serviceToken = process.env.COSA_SERVICE_TOKEN || "local-dev-service-token";

  try {
    const response = await fetch(`${cosaBaseUrl}/agent/copilot/customer-support`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Cosa-Service-Token": serviceToken,
        "X-Workspace-Id": payload.workspaceId,
      },
      body: JSON.stringify({
        workspace_id: payload.workspaceId,
        thread_ref: {
          thread_id: payload.threadRef.threadId,
          contact_id: payload.threadRef.contactId,
        },
        intent: payload.intent,
        knowledge_scope: payload.knowledgeScope,
        identity_verified: payload.identityVerified,
        correlation_id: payload.correlationId,
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`COSA returned ${response.status}: ${errText}`);
    }

    const data = (await response.json()) as { run_id: string };
    return { runId: data.run_id };
  } catch (err: any) {
    throw APIError.internal(`copilot dispatch failed: ${err.message || String(err)}`);
  }
}
