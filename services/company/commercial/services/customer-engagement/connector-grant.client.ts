export interface AssertConnectorGrantParams {
  workspaceId: string;
  conversationId: string;
  connectorKey: string;
  action: string;
  requiredScope?: string;
}

export type ConnectorGrantRunner = (
  params: AssertConnectorGrantParams
) => Promise<{ ok: boolean; secretRef: string | null }>;

let customConnectorGrantRunner: ConnectorGrantRunner | null = null;

export function setCustomConnectorGrantRunner(runner: ConnectorGrantRunner | null) {
  customConnectorGrantRunner = runner;
}

export async function assertConnectorGrant(
  params: AssertConnectorGrantParams
): Promise<{ ok: boolean; secretRef: string | null }> {
  if (customConnectorGrantRunner) {
    try {
      return await customConnectorGrantRunner(params);
    } catch {
      return { ok: false, secretRef: null };
    }
  }

  const cosaBaseUrl = process.env.COSA_CONTROL_PLANE_URL || "http://127.0.0.1:4000";
  const workerServiceToken = process.env.COSA_WORKER_SERVICE_TOKEN || process.env.COSA_SERVICE_TOKEN || "local-dev-service-token";

  try {
    const resp = await fetch(`${cosaBaseUrl}/cosa/connectors/assert`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${workerServiceToken}`,
      },
      body: JSON.stringify({
        workspaceId: params.workspaceId,
        conversationId: params.conversationId,
        connectorKey: params.connectorKey,
        action: params.action,
        requiredScope: params.requiredScope,
      }),
    });

    if (!resp.ok) {
      return { ok: false, secretRef: null };
    }

    const data = await resp.json().catch(() => ({}));
    if (data.ok && data.secretRef) {
      return { ok: true, secretRef: data.secretRef };
    }
    return { ok: Boolean(data.ok), secretRef: data.secretRef || null };
  } catch {
    // Network errors fail-closed
    return { ok: false, secretRef: null };
  }
}
