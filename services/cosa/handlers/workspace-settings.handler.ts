import { api, Header } from "encore.dev/api";
import {
  ConnectorStatusView,
  installWorkspaceConnectorService,
  listWorkspaceAuditEventsService,
  listWorkspaceConnectorsService,
  listWorkspaceMembersService,
  listWorkspaceRuntimeNodesService,
  MvpSuccess,
  revokeWorkspaceConnectorService,
  revokeWorkspaceRuntimeNodeService,
  RuntimeNodeView,
  WorkspaceAuditEventDTO,
  WorkspaceMemberDTO,
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
