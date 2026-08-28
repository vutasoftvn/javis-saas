import { APIError } from "encore.dev/api";

export interface OnboardChannelConnectorParams {
  workspaceId: string;
  connectorKey: string;
  secretRef: string;
  grantedScopes?: string[];
  expiresAt?: string;
}

export interface OnboardChannelConnectorResult {
  installationId: string;
  authorizationId: string;
}

export type OnboardingRunner = (action: "install" | "authorize" | "grant", payload: any) => Promise<any>;

let customOnboardingRunner: OnboardingRunner | null = null;

export function setCustomOnboardingRunner(runner: OnboardingRunner | null) {
  customOnboardingRunner = runner;
}

export async function onboardChannelConnector(
  params: OnboardChannelConnectorParams,
  authorization: string
): Promise<OnboardChannelConnectorResult> {
  const cosaBaseUrl = process.env.COSA_CONTROL_PLANE_URL || "http://127.0.0.1:4000";
  const authHeader = authorization.startsWith("Bearer ") ? authorization : `Bearer ${authorization}`;

  if (customOnboardingRunner) {
    const inst = await customOnboardingRunner("install", {
      workspaceId: params.workspaceId,
      connectorKey: params.connectorKey,
    });
    const auth = await customOnboardingRunner("authorize", {
      workspaceId: params.workspaceId,
      installationId: inst.id,
      secretRef: params.secretRef,
      grantedScopes: params.grantedScopes || ["send", "read"],
      expiresAt: params.expiresAt || new Date(Date.now() + 365 * 86400000).toISOString(),
    });
    await customOnboardingRunner("grant", {
      workspaceId: params.workspaceId,
      conversationId: "system",
      authorizationId: auth.id,
      allowedActions: ["send"],
    });

    return {
      installationId: inst.id,
      authorizationId: auth.id,
    };
  }

  // 1. Install connector in Control Plane
  const installResp = await fetch(`${cosaBaseUrl}/cosa/connectors/install`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: authHeader,
    },
    body: JSON.stringify({
      workspaceId: params.workspaceId,
      connectorKey: params.connectorKey,
    }),
  });

  if (!installResp.ok) {
    const err = await installResp.json().catch(() => ({}));
    throw APIError.failedPrecondition(`Failed to install connector: ${err.message || installResp.statusText}`);
  }

  const installData = await installResp.json();
  const installationId = installData.id;

  // 2. Authorize connector with secretRef
  const authorizeResp = await fetch(`${cosaBaseUrl}/cosa/connectors/authorize`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: authHeader,
    },
    body: JSON.stringify({
      workspaceId: params.workspaceId,
      installationId,
      secretRef: params.secretRef,
      grantedScopes: params.grantedScopes || ["send", "read"],
      expiresAt: params.expiresAt || new Date(Date.now() + 365 * 86400000).toISOString(),
    }),
  });

  if (!authorizeResp.ok) {
    const err = await authorizeResp.json().catch(() => ({}));
    throw APIError.failedPrecondition(`Failed to authorize connector: ${err.message || authorizeResp.statusText}`);
  }

  const authData = await authorizeResp.json();
  const authorizationId = authData.id;

  // 3. Grant system-level permission for channel sending
  await fetch(`${cosaBaseUrl}/cosa/connectors/grant`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: authHeader,
    },
    body: JSON.stringify({
      workspaceId: params.workspaceId,
      conversationId: "system",
      authorizationId,
      allowedActions: ["send"],
    }),
  }).catch(() => {});

  return {
    installationId,
    authorizationId,
  };
}
