import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { requireCommandAuthority } from "../../../identity/services/command-authority.service";
import {
  createPestelSignal,
  listPestelSignals,
  updatePestelSignal,
  createResourceCapabilityAssessment,
  listResourceCapabilityAssessments,
  updateResourceCapabilityAssessment,
  createSwotItem,
  listSwotItems,
  updateSwotItem,
  deriveSwotDrafts,
  PestelSignal,
  PestelDimension,
  PestelImpact,
  PestelCertainty,
  ResourceCapabilityAssessment,
  ResourceCapabilityCategory,
  StrengthLevel,
  SwotItem,
  SwotKind,
  SwotSourceType,
  AnalysisStatus,
} from "../services/strategy-analysis.service";
import { BscPerspective } from "../services/workspace-strategy-settings.service";

// PESTEL Params
export interface CreatePestelSignalParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  objectiveId: string;
  dimension: PestelDimension;
  statement: string;
  impact: PestelImpact;
  certainty: PestelCertainty;
  evidenceRefs?: string[];
  bscPerspectives?: BscPerspective[];
  status?: AnalysisStatus;
}

export interface ListPestelSignalsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  objectiveId: string;
  status?: AnalysisStatus;
}

export interface UpdatePestelSignalParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  objectiveId: string;
  id: string;
  dimension?: PestelDimension;
  statement?: string;
  impact?: PestelImpact;
  certainty?: PestelCertainty;
  evidenceRefs?: string[];
  bscPerspectives?: BscPerspective[];
  status?: AnalysisStatus;
}

// Resource Params
export interface CreateResourceAssessmentParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  objectiveId: string;
  category: ResourceCapabilityCategory;
  statement: string;
  strengthLevel: StrengthLevel;
  evidenceRefs?: string[];
  bscPerspectives?: BscPerspective[];
  status?: AnalysisStatus;
}

export interface ListResourceAssessmentsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  objectiveId: string;
  status?: AnalysisStatus;
}

export interface UpdateResourceAssessmentParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  objectiveId: string;
  id: string;
  category?: ResourceCapabilityCategory;
  statement?: string;
  strengthLevel?: StrengthLevel;
  evidenceRefs?: string[];
  bscPerspectives?: BscPerspective[];
  status?: AnalysisStatus;
}

// SWOT Params
export interface CreateSwotItemParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  objectiveId: string;
  kind: SwotKind;
  statement: string;
  sourceType: SwotSourceType;
  sourceId?: string | null;
  evidenceRefs?: string[];
  bscPerspectives?: BscPerspective[];
  status?: AnalysisStatus;
}

export interface ListSwotItemsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  objectiveId: string;
  status?: AnalysisStatus;
}

export interface UpdateSwotItemParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  objectiveId: string;
  id: string;
  kind?: SwotKind;
  statement?: string;
  status?: AnalysisStatus;
  evidenceRefs?: string[];
  bscPerspectives?: BscPerspective[];
}

export interface DeriveSwotDraftsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  objectiveId: string;
}

// -------------------------------------------------------------
// PESTEL Endpoints
// -------------------------------------------------------------

export const createPestelSignalApi = api(
  { method: "POST", path: "/operations/strategy/objectives/:objectiveId/analysis/pestel", expose: true },
  async (params: CreatePestelSignalParams): Promise<PestelSignal> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.analysis.write", {
      workspaceId: String(ctx.workspaceId),
    });
    return createPestelSignal(ctx, {
      strategicObjectiveId: params.objectiveId,
      dimension: params.dimension,
      statement: params.statement,
      impact: params.impact,
      certainty: params.certainty,
      evidenceRefs: params.evidenceRefs,
      bscPerspectives: params.bscPerspectives,
      status: params.status,
    });
  }
);

export const listPestelSignalsApi = api(
  { method: "GET", path: "/operations/strategy/objectives/:objectiveId/analysis/pestel", expose: true },
  async (params: ListPestelSignalsParams): Promise<{ items: PestelSignal[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.read", {
      workspaceId: String(ctx.workspaceId),
    });
    return listPestelSignals(ctx, params.objectiveId, params.status);
  }
);

export const updatePestelSignalApi = api(
  { method: "PUT", path: "/operations/strategy/objectives/:objectiveId/analysis/pestel/:id", expose: true },
  async (params: UpdatePestelSignalParams): Promise<PestelSignal> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.analysis.write", {
      workspaceId: String(ctx.workspaceId),
    });
    return updatePestelSignal(ctx, {
      id: params.id,
      dimension: params.dimension,
      statement: params.statement,
      impact: params.impact,
      certainty: params.certainty,
      evidenceRefs: params.evidenceRefs,
      bscPerspectives: params.bscPerspectives,
      status: params.status,
    });
  }
);

// -------------------------------------------------------------
// Resource & Capability Endpoints
// -------------------------------------------------------------

export const createResourceAssessmentApi = api(
  { method: "POST", path: "/operations/strategy/objectives/:objectiveId/analysis/resources", expose: true },
  async (params: CreateResourceAssessmentParams): Promise<ResourceCapabilityAssessment> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.analysis.write", {
      workspaceId: String(ctx.workspaceId),
    });
    return createResourceCapabilityAssessment(ctx, {
      strategicObjectiveId: params.objectiveId,
      category: params.category,
      statement: params.statement,
      strengthLevel: params.strengthLevel,
      evidenceRefs: params.evidenceRefs,
      bscPerspectives: params.bscPerspectives,
      status: params.status,
    });
  }
);

export const listResourceAssessmentsApi = api(
  { method: "GET", path: "/operations/strategy/objectives/:objectiveId/analysis/resources", expose: true },
  async (params: ListResourceAssessmentsParams): Promise<{ items: ResourceCapabilityAssessment[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.read", {
      workspaceId: String(ctx.workspaceId),
    });
    return listResourceCapabilityAssessments(ctx, params.objectiveId, params.status);
  }
);

export const updateResourceAssessmentApi = api(
  { method: "PUT", path: "/operations/strategy/objectives/:objectiveId/analysis/resources/:id", expose: true },
  async (params: UpdateResourceAssessmentParams): Promise<ResourceCapabilityAssessment> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.analysis.write", {
      workspaceId: String(ctx.workspaceId),
    });
    return updateResourceCapabilityAssessment(ctx, {
      id: params.id,
      category: params.category,
      statement: params.statement,
      strengthLevel: params.strengthLevel,
      evidenceRefs: params.evidenceRefs,
      bscPerspectives: params.bscPerspectives,
      status: params.status,
    });
  }
);

// -------------------------------------------------------------
// SWOT Endpoints
// -------------------------------------------------------------

export const createSwotItemApi = api(
  { method: "POST", path: "/operations/strategy/objectives/:objectiveId/analysis/swot", expose: true },
  async (params: CreateSwotItemParams): Promise<SwotItem> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.analysis.write", {
      workspaceId: String(ctx.workspaceId),
    });
    return createSwotItem(ctx, {
      strategicObjectiveId: params.objectiveId,
      kind: params.kind,
      statement: params.statement,
      sourceType: params.sourceType,
      sourceId: params.sourceId,
      evidenceRefs: params.evidenceRefs,
      bscPerspectives: params.bscPerspectives,
      status: params.status,
    });
  }
);

export const listSwotItemsApi = api(
  { method: "GET", path: "/operations/strategy/objectives/:objectiveId/analysis/swot", expose: true },
  async (params: ListSwotItemsParams): Promise<{ items: SwotItem[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.read", {
      workspaceId: String(ctx.workspaceId),
    });
    return listSwotItems(ctx, params.objectiveId, params.status);
  }
);

export const updateSwotItemApi = api(
  { method: "PUT", path: "/operations/strategy/objectives/:objectiveId/analysis/swot/:id", expose: true },
  async (params: UpdateSwotItemParams): Promise<SwotItem> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.analysis.write", {
      workspaceId: String(ctx.workspaceId),
    });
    return updateSwotItem(ctx, {
      id: params.id,
      kind: params.kind,
      statement: params.statement,
      status: params.status,
      evidenceRefs: params.evidenceRefs,
      bscPerspectives: params.bscPerspectives,
    });
  }
);

export const deriveSwotDraftsApi = api(
  { method: "POST", path: "/operations/strategy/objectives/:objectiveId/analysis/swot/derive-drafts", expose: true },
  async (params: DeriveSwotDraftsParams): Promise<{ items: SwotItem[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.analysis.write", {
      workspaceId: String(ctx.workspaceId),
    });
    return deriveSwotDrafts(ctx, params.objectiveId);
  }
);
