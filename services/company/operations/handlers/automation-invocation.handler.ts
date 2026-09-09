// COSA Automation MVP — invocation endpoints (Task 3).

import { api, Header } from "encore.dev/api";
import type { MvpSuccess } from "../../shared/contracts/mvp-response";
import {
  createAutomationInvocation,
  getAutomationInvocation,
  cancelAutomationInvocation,
  type AutomationInvocationView,
  type CreateAutomationInvocationCommand,
} from "../services/automation-invocation.service";

export type { AutomationInvocationView, CreateAutomationInvocationCommand };

interface WsHeaders {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const createAutomationInvocationEndpoint = api(
  { method: "POST", path: "/operations/automation/definitions/:definitionId/invocations", expose: true },
  async (
    params: WsHeaders & { definitionId: string; command: CreateAutomationInvocationCommand }
  ): Promise<MvpSuccess<AutomationInvocationView>> => {
    return createAutomationInvocation({
      workspaceId: params.workspaceId,
      authorization: params.authorization,
      definitionId: params.definitionId,
      command: params.command,
    });
  }
);

export const getAutomationInvocationEndpoint = api(
  { method: "GET", path: "/operations/automation/invocations/:invocationId", expose: true },
  async (
    params: WsHeaders & { invocationId: string }
  ): Promise<MvpSuccess<AutomationInvocationView>> => {
    return getAutomationInvocation({
      workspaceId: params.workspaceId,
      authorization: params.authorization,
      invocationId: params.invocationId,
    });
  }
);

export const cancelAutomationInvocationEndpoint = api(
  { method: "POST", path: "/operations/automation/invocations/:invocationId/cancellation", expose: true },
  async (
    params: WsHeaders & { invocationId: string; expectedVersion: number }
  ): Promise<MvpSuccess<AutomationInvocationView>> => {
    return cancelAutomationInvocation({
      workspaceId: params.workspaceId,
      authorization: params.authorization,
      invocationId: params.invocationId,
      expectedVersion: params.expectedVersion,
    });
  }
);
