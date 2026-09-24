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
  listWorkspaceModuleVisibilityService,
  setWorkspaceModuleEnabledService,
  setUserModulePreferenceService,
  WorkspaceModuleVisibilityDTO,
  getWorkspaceCapabilityManifestService,
  setWorkspaceSurfaceOverrideService,
  WorkspaceCapabilityManifest,
} from "../services/workspace-settings.service";

export interface WorkspaceSettingsHeaderRequest {
  organizationId: string;
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
  { expose: true, method: "GET", path: "/platform/organizations/:organizationId/members" },
  async ({ organizationId, authorization }: WorkspaceSettingsHeaderRequest): Promise<MvpSuccess<readonly WorkspaceMemberDTO[]>> => {
    return listWorkspaceMembersService(organizationId, authorization);
  }
);

// 2. Connectors
export const listWorkspaceConnectors = api(
  { expose: true, method: "GET", path: "/platform/organizations/:organizationId/connectors" },
  async ({ organizationId, authorization }: WorkspaceSettingsHeaderRequest): Promise<MvpSuccess<readonly ConnectorStatusView[]>> => {
    return listWorkspaceConnectorsService(organizationId, authorization);
  }
);

export const installWorkspaceConnector = api(
  { expose: true, method: "POST", path: "/platform/organizations/:organizationId/connectors/:connectorKey/install" },
  async ({ organizationId, connectorKey, authorization }: ConnectorActionRequest): Promise<MvpSuccess<ConnectorStatusView>> => {
    return installWorkspaceConnectorService(organizationId, connectorKey, authorization);
  }
);

export const revokeWorkspaceConnector = api(
  { expose: true, method: "POST", path: "/platform/organizations/:organizationId/connectors/:connectorKey/revoke" },
  async ({ organizationId, connectorKey, authorization }: ConnectorActionRequest): Promise<MvpSuccess<ConnectorStatusView>> => {
    return revokeWorkspaceConnectorService(organizationId, connectorKey, authorization);
  }
);

// 3. Runtime Nodes
export const listWorkspaceRuntimeNodes = api(
  { expose: true, method: "GET", path: "/platform/organizations/:organizationId/runtime-nodes" },
  async ({ organizationId, authorization }: WorkspaceSettingsHeaderRequest): Promise<MvpSuccess<readonly RuntimeNodeView[]>> => {
    return listWorkspaceRuntimeNodesService(organizationId, authorization);
  }
);

export const revokeWorkspaceRuntimeNode = api(
  { expose: true, method: "POST", path: "/platform/organizations/:organizationId/runtime-nodes/:nodeId/revoke" },
  async ({ organizationId, nodeId, authorization }: RuntimeNodeActionRequest): Promise<MvpSuccess<{ revoked: boolean }>> => {
    return revokeWorkspaceRuntimeNodeService(organizationId, nodeId, authorization);
  }
);

// 4. Audit Events
export const listWorkspaceAuditEvents = api(
  { expose: true, method: "GET", path: "/platform/organizations/:organizationId/audit-events" },
  async ({ organizationId, authorization }: WorkspaceSettingsHeaderRequest): Promise<MvpSuccess<readonly WorkspaceAuditEventDTO[]>> => {
    return listWorkspaceAuditEventsService(organizationId, authorization);
  }
);

// 5. Skill Policies (Task 4 — Truthful MVP Hardening)
export const listWorkspaceSkillPolicies = api(
  { expose: true, method: "GET", path: "/platform/organizations/:organizationId/skill-policies" },
  async ({ organizationId, authorization }: WorkspaceSettingsHeaderRequest): Promise<MvpSuccess<readonly WorkspaceSkillPolicyView[]>> => {
    return listWorkspaceSkillPoliciesService(organizationId, authorization);
  }
);

// 6. Session Context (Task 3 — Frontend Trust and UX Hardening)
//
// Đặt cạnh runtime-nodes/settings — cùng nhóm endpoint platform đọc trạng
// thái workspace hiện tại, cùng dùng chung membership resolver ở service.
export const getWorkspaceSessionContext = api(
  { expose: true, method: "GET", path: "/platform/organizations/:organizationId/session-context" },
  async ({ organizationId, authorization }: WorkspaceSettingsHeaderRequest): Promise<WorkspaceSessionContextView> => {
    return getWorkspaceSessionContextService(organizationId, authorization);
  }
);

export const putWorkspaceSkillPolicy = api(
  { expose: true, method: "PUT", path: "/platform/organizations/:organizationId/skill-policies/:skillKey" },
  async ({ organizationId, skillKey, enabled, config, authorization }: SkillPolicyPutRequest): Promise<MvpSuccess<WorkspaceSkillPolicyView>> => {
    return putWorkspaceSkillPolicyService(organizationId, skillKey, enabled, config ?? {}, authorization);
  }
);

// 7. Module Visibility (2026-09-07 Localization & Shell Customization)
export interface SetWorkspaceModuleRequest extends WorkspaceSettingsHeaderRequest {
  moduleKey: string;
  enabled: boolean;
}

export interface SetUserModulePreferenceRequest extends WorkspaceSettingsHeaderRequest {
  moduleKey: string;
  visible: boolean;
}

export const listWorkspaceModuleVisibility = api(
  { expose: true, method: "GET", path: "/platform/organizations/:organizationId/module-visibility" },
  async ({ organizationId, authorization }: WorkspaceSettingsHeaderRequest): Promise<MvpSuccess<WorkspaceModuleVisibilityDTO>> => {
    return listWorkspaceModuleVisibilityService(organizationId, authorization);
  }
);

export const setWorkspaceModuleEnabled = api(
  { expose: true, method: "PUT", path: "/platform/organizations/:organizationId/module-visibility/:moduleKey" },
  async ({ organizationId, moduleKey, enabled, authorization }: SetWorkspaceModuleRequest): Promise<MvpSuccess<WorkspaceModuleVisibilityDTO>> => {
    return setWorkspaceModuleEnabledService(organizationId, moduleKey, enabled, authorization);
  }
);

export const setUserModulePreference = api(
  { expose: true, method: "PUT", path: "/platform/organizations/:organizationId/module-visibility/:moduleKey/preference" },
  async ({ organizationId, moduleKey, visible, authorization }: SetUserModulePreferenceRequest): Promise<MvpSuccess<WorkspaceModuleVisibilityDTO>> => {
    return setUserModulePreferenceService(organizationId, moduleKey, visible, authorization);
  }
);

// 8. Workspace Capability Manifest (Founder Trial R1 — spec §7.1)
export interface SetSurfaceOverrideRequest extends WorkspaceSettingsHeaderRequest {
  surfaceKey: string;
  statusOverride: string;
  reason?: string;
}

export const getWorkspaceCapabilityManifest = api(
  { expose: true, method: "GET", path: "/platform/organizations/:organizationId/capability-manifest" },
  async ({ organizationId, authorization }: WorkspaceSettingsHeaderRequest): Promise<MvpSuccess<WorkspaceCapabilityManifest>> => {
    return getWorkspaceCapabilityManifestService(organizationId, authorization);
  }
);

export const setWorkspaceSurfaceOverride = api(
  { expose: true, method: "PUT", path: "/platform/organizations/:organizationId/capability-manifest/:surfaceKey" },
  async ({ organizationId, surfaceKey, statusOverride, reason, authorization }: SetSurfaceOverrideRequest): Promise<MvpSuccess<WorkspaceCapabilityManifest>> => {
    return setWorkspaceSurfaceOverrideService(organizationId, surfaceKey, statusOverride, reason, authorization);
  }
);

