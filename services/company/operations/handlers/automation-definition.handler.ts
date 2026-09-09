// COSA Automation MVP — automation definition endpoints (Task 2).
// Thin: declare route, thread the Authorization/X-Workspace-Id headers, call the
// service (which owns tenancy + role authorization) and return the mvp envelope.

import { api, Header } from "encore.dev/api";
import type { MvpSuccess } from "../../shared/contracts/mvp-response";
import {
  listAutomationDefinitions,
  getAutomationDefinition,
  configureAutomationDefinition,
  publishAutomationRevision,
  suspendAutomationDefinition,
  type AutomationDefinitionView,
  type AutomationTriggerContract,
} from "../services/automation-definition.service";

export type { AutomationDefinitionView, AutomationTriggerContract };

interface WsHeaders {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const listAutomationDefinitionsEndpoint = api(
  { method: "GET", path: "/operations/automation/definitions", expose: true },
  async (
    params: WsHeaders
  ): Promise<MvpSuccess<readonly AutomationDefinitionView[]>> => {
    return listAutomationDefinitions({
      workspaceId: params.workspaceId,
      authorization: params.authorization,
    });
  }
);

export const getAutomationDefinitionEndpoint = api(
  { method: "GET", path: "/operations/automation/definitions/:definitionId", expose: true },
  async (
    params: WsHeaders & { definitionId: string }
  ): Promise<MvpSuccess<AutomationDefinitionView>> => {
    return getAutomationDefinition({
      workspaceId: params.workspaceId,
      authorization: params.authorization,
      definitionId: params.definitionId,
    });
  }
);

export const configureAutomationDefinitionEndpoint = api(
  { method: "PATCH", path: "/operations/automation/definitions/:definitionId/configuration", expose: true },
  async (
    params: WsHeaders & {
      definitionId: string;
      automationKey: string;
      configuration: Record<string, unknown>;
      triggerContract: AutomationTriggerContract;
    }
  ): Promise<MvpSuccess<AutomationDefinitionView>> => {
    return configureAutomationDefinition({
      workspaceId: params.workspaceId,
      authorization: params.authorization,
      automationKey: params.automationKey,
      configuration: params.configuration,
      triggerContract: params.triggerContract,
    });
  }
);

export const publishAutomationRevisionEndpoint = api(
  { method: "POST", path: "/operations/automation/definitions/:definitionId/revisions", expose: true },
  async (
    params: WsHeaders & { definitionId: string }
  ): Promise<MvpSuccess<AutomationDefinitionView>> => {
    return publishAutomationRevision({
      workspaceId: params.workspaceId,
      authorization: params.authorization,
      definitionId: params.definitionId,
    });
  }
);

export const suspendAutomationDefinitionEndpoint = api(
  { method: "POST", path: "/operations/automation/definitions/:definitionId/suspension", expose: true },
  async (
    params: WsHeaders & { definitionId: string }
  ): Promise<MvpSuccess<AutomationDefinitionView>> => {
    return suspendAutomationDefinition({
      workspaceId: params.workspaceId,
      authorization: params.authorization,
      definitionId: params.definitionId,
    });
  }
);
