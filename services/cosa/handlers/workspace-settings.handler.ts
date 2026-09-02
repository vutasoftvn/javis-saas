import { api, Header } from "encore.dev/api";
import {
  ConnectorStatusView,
  installWorkspaceConnectorService,
  listWorkspaceAuditEventsService,
  listWorkspaceConnectorsService,
  listWorkspaceMembersService,
  listWorkspaceRuntimeNodesService,
  listWorkspaceSkillPoliciesService,
  MvpSuccess,
  putWorkspaceSkillPolicyService,
  revokeWorkspaceConnectorService,
  revokeWorkspaceRuntimeNodeService,
  RuntimeNodeView,
  WorkspaceAuditEventDTO,
  WorkspaceMemberDTO,
  WorkspaceSessionContextView,
  WorkspaceSkillPolicyView,
  getWorkspaceSessionContextService,
} from "../services/workspace-settings.service";

export interface WorkspaceSettingsHeaderRequest {
  workspaceId: string;
  authorization?: Header<"Authorization">;
}

export interface ConnectorActionRequest extends WorkspaceSettingsHeaderRequest {
  connectorKey: string;
}

export interface RuntimeNodeActionRequest extends WorkspaceSettingsHeaderRequest {
  nodeId: string;
}

export interface SkillPolicyPutRequest extends WorkspaceSettingsHeaderRequest {
  skillKey: string;
  enabled: boolean;
  config: Record<string, unknown>;
}

// 1. Members
export const listWorkspaceMembers = api(
  { expose: true, method: "GET", path: "/platform/workspaces/:workspaceId/members" },
  async ({ workspaceId, authorization }: WorkspaceSettingsHeaderRequest): Promise<MvpSuccess<readonly WorkspaceMemberDTO[]>> => {
    return listWorkspaceMembersService(workspaceId, authorization);
  }
);

// 2. Connectors
export const listWorkspaceConnectors = api(
  { expose: true, method: "GET", path: "/platform/workspaces/:workspaceId/connectors" },
  async ({ workspaceId, authorization }: WorkspaceSettingsHeaderRequest): Promise<MvpSuccess<readonly ConnectorStatusView[]>> => {
    return listWorkspaceConnectorsService(workspaceId, authorization);
  }
);

export const installWorkspaceConnector = api(
  { expose: true, method: "POST", path: "/platform/workspaces/:workspaceId/connectors/:connectorKey/install" },
  async ({ workspaceId, connectorKey, authorization }: ConnectorActionRequest): Promise<MvpSuccess<ConnectorStatusView>> => {
    return installWorkspaceConnectorService(workspaceId, connectorKey, authorization);
  }
);

export const revokeWorkspaceConnector = api(
  { expose: true, method: "POST", path: "/platform/workspaces/:workspaceId/connectors/:connectorKey/revoke" },
  async ({ workspaceId, connectorKey, authorization }: ConnectorActionRequest): Promise<MvpSuccess<ConnectorStatusView>> => {
    return revokeWorkspaceConnectorService(workspaceId, connectorKey, authorization);
  }
);

// 3. Runtime Nodes
export const listWorkspaceRuntimeNodes = api(
  { expose: true, method: "GET", path: "/platform/workspaces/:workspaceId/runtime-nodes" },
  async ({ workspaceId, authorization }: WorkspaceSettingsHeaderRequest): Promise<MvpSuccess<readonly RuntimeNodeView[]>> => {
    return listWorkspaceRuntimeNodesService(workspaceId, authorization);
  }
);

export const revokeWorkspaceRuntimeNode = api(
  { expose: true, method: "POST", path: "/platform/workspaces/:workspaceId/runtime-nodes/:nodeId/revoke" },
  async ({ workspaceId, nodeId, authorization }: RuntimeNodeActionRequest): Promise<MvpSuccess<{ revoked: boolean }>> => {
    return revokeWorkspaceRuntimeNodeService(workspaceId, nodeId, authorization);
  }
);

// 4. Audit Events
export const listWorkspaceAuditEvents = api(
  { expose: true, method: "GET", path: "/platform/workspaces/:workspaceId/audit-events" },
  async ({ workspaceId, authorization }: WorkspaceSettingsHeaderRequest): Promise<MvpSuccess<readonly WorkspaceAuditEventDTO[]>> => {
    return listWorkspaceAuditEventsService(workspaceId, authorization);
  }
);

// 5. Skill Policies (Task 4 — Truthful MVP Hardening)
export const listWorkspaceSkillPolicies = api(
  { expose: true, method: "GET", path: "/platform/workspaces/:workspaceId/skill-policies" },
  async ({ workspaceId, authorization }: WorkspaceSettingsHeaderRequest): Promise<MvpSuccess<readonly WorkspaceSkillPolicyView[]>> => {
    return listWorkspaceSkillPoliciesService(workspaceId, authorization);
  }
);

// 6. Session Context (Task 3 — Frontend Trust and UX Hardening)
//
// Đặt cạnh runtime-nodes/settings — cùng nhóm endpoint platform đọc trạng
// thái workspace hiện tại, cùng dùng chung membership resolver ở service.
export const getWorkspaceSessionContext = api(
  { expose: true, method: "GET", path: "/platform/workspaces/:workspaceId/session-context" },
  async ({ workspaceId, authorization }: WorkspaceSettingsHeaderRequest): Promise<WorkspaceSessionContextView> => {
    return getWorkspaceSessionContextService(workspaceId, authorization);
  }
);

export const putWorkspaceSkillPolicy = api(
  { expose: true, method: "PUT", path: "/platform/workspaces/:workspaceId/skill-policies/:skillKey" },
  async ({ workspaceId, skillKey, enabled, config, authorization }: SkillPolicyPutRequest): Promise<MvpSuccess<WorkspaceSkillPolicyView>> => {
    return putWorkspaceSkillPolicyService(workspaceId, skillKey, enabled, config ?? {}, authorization);
  }
);
