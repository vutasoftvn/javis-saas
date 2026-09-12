import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  getCrmSchemaService,
  createFieldDefinitionService,
  patchFieldDefinitionService,
  retireFieldDefinitionService,
  CrmSchemaView,
} from "../services/lead-field-definition.service";
import {
  createLeadSourceService,
  listLeadSourcesService,
  LeadSourceModel,
} from "../services/lead-source.service";
import {
  createProjectLeadService,
  listProjectLeadsService,
} from "../services/project-lead.service";
import {
  LeadFieldDefinitionModel,
  LeadFieldDataType,
  DataClassification,
  AllowedSelectValue,
  ProjectLeadView,
  ProjectLeadInput,
} from "../services/project-lead-repository";

export interface CreateFieldDefinitionRequest {
  projectId: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  stableKey: string;
  label: string;
  dataType: LeadFieldDataType;
  validation?: Record<string, unknown>;
  allowedValues?: AllowedSelectValue[];
  requiredAtStages?: string[];
  classification?: DataClassification;
  agentInputAllowed?: boolean;
  searchable?: boolean;
}

export interface PatchFieldDefinitionRequest {
  projectId: string;
  fieldId: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  label?: string;
  allowedValues?: AllowedSelectValue[];
  requiredAtStages?: string[];
}

export interface RetireFieldDefinitionRequest {
  projectId: string;
  fieldId: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  expectedVersion?: number;
}

export interface CreateLeadSourceRequest {
  projectId: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  sourceType: string;
  label: string;
}

export interface CreateProjectLeadRequest extends ProjectLeadInput {
  projectId: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export const getProjectCrmSchema = api(
  { method: "GET", path: "/commercial/projects/:projectId/crm/schema", expose: true },
  async ({
    projectId,
    workspaceId,
    authorization,
  }: {
    projectId: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<CrmSchemaView> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getCrmSchemaService(ctx, projectId);
  }
);

export const createProjectLeadFieldDefinition = api(
  { method: "POST", path: "/commercial/projects/:projectId/crm/field-definitions", expose: true },
  async (req: CreateFieldDefinitionRequest): Promise<LeadFieldDefinitionModel> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return createFieldDefinitionService(ctx, req.projectId, {
      stableKey: req.stableKey,
      label: req.label,
      dataType: req.dataType,
      validation: req.validation,
      allowedValues: req.allowedValues,
      requiredAtStages: req.requiredAtStages,
      classification: req.classification,
      agentInputAllowed: req.agentInputAllowed,
      searchable: req.searchable,
    });
  }
);

export const patchProjectLeadFieldDefinition = api(
  { method: "PATCH", path: "/commercial/projects/:projectId/crm/field-definitions/:fieldId", expose: true },
  async (req: PatchFieldDefinitionRequest): Promise<LeadFieldDefinitionModel> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return patchFieldDefinitionService(ctx, req.projectId, req.fieldId, {
      label: req.label,
      allowedValues: req.allowedValues,
      requiredAtStages: req.requiredAtStages,
    });
  }
);

export const retireProjectLeadFieldDefinition = api(
  { method: "POST", path: "/commercial/projects/:projectId/crm/field-definitions/:fieldId/retire", expose: true },
  async (req: RetireFieldDefinitionRequest): Promise<LeadFieldDefinitionModel> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return retireFieldDefinitionService(ctx, req.projectId, req.fieldId, req.expectedVersion);
  }
);

export const listProjectLeadSources = api(
  { method: "GET", path: "/commercial/projects/:projectId/crm/lead-sources", expose: true },
  async ({
    projectId,
    workspaceId,
    authorization,
  }: {
    projectId: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<{ sources: LeadSourceModel[] }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const sources = await listLeadSourcesService(ctx, projectId);
    return { sources };
  }
);

export const createProjectLeadSource = api(
  { method: "POST", path: "/commercial/projects/:projectId/crm/lead-sources", expose: true },
  async (req: CreateLeadSourceRequest): Promise<LeadSourceModel> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return createLeadSourceService(ctx, req.projectId, {
      sourceType: req.sourceType,
      label: req.label,
    });
  }
);

export const listProjectLeads = api(
  { method: "GET", path: "/commercial/projects/:projectId/crm/leads", expose: true },
  async ({
    projectId,
    workspaceId,
    authorization,
    limit,
    offset,
  }: {
    projectId: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    limit?: number;
    offset?: number;
  }): Promise<{ leads: ProjectLeadView[] }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const leads = await listProjectLeadsService(ctx, projectId, { limit, offset });
    return { leads };
  }
);

export const createProjectLead = api(
  { method: "POST", path: "/commercial/projects/:projectId/crm/leads", expose: true },
  async (req: CreateProjectLeadRequest): Promise<ProjectLeadView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return createProjectLeadService(ctx, req.projectId, req);
  }
);
