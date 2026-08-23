import { api, Header } from "encore.dev/api";
import {
  ValidationHypothesis,
  CreateHypothesisRequest as BaseCreateHypothesisRequest,
  ValidationExperiment,
  CreateExperimentRequest as BaseCreateExperimentRequest,
  EvidenceItem,
  CreateEvidenceItemRequest as BaseCreateEvidenceItemRequest,
  createHypothesisService,
  listHypothesesService,
  createExperimentService,
  createEvidenceService,
} from "../services/validation.service";

export { ValidationHypothesis, ValidationExperiment, EvidenceItem };

export interface CreateHypothesisRequest extends BaseCreateHypothesisRequest {
  authorization?: Header<"Authorization">;
}
export interface CreateExperimentRequest extends BaseCreateExperimentRequest {
  authorization?: Header<"Authorization">;
}
export interface CreateEvidenceItemRequest extends BaseCreateEvidenceItemRequest {
  authorization?: Header<"Authorization">;
}

// ─── Hypotheses Endpoints ───

export const createHypothesis = api(
  { expose: true, method: "POST", path: "/finance-legal/hypotheses" },
  async (req: CreateHypothesisRequest): Promise<ValidationHypothesis> => {
    return createHypothesisService(req, req.authorization);
  }
);

export const listHypotheses = api(
  { expose: true, method: "GET", path: "/finance-legal/workspaces/:workspaceId/hypotheses" },
  async (params: { workspaceId: number; authorization?: Header<"Authorization"> }): Promise<{ hypotheses: ValidationHypothesis[] }> => {
    const hypotheses = await listHypothesesService(params.workspaceId, params.authorization);
    return { hypotheses };
  }
);

// ─── Experiments Endpoints ───

export const createExperiment = api(
  { expose: true, method: "POST", path: "/finance-legal/experiments" },
  async (req: CreateExperimentRequest): Promise<ValidationExperiment> => {
    return createExperimentService(req, req.authorization);
  }
);

// ─── Evidence Items Endpoints ───

export const createEvidence = api(
  { expose: true, method: "POST", path: "/finance-legal/evidence" },
  async (req: CreateEvidenceItemRequest): Promise<EvidenceItem> => {
    return createEvidenceService(req, req.authorization);
  }
);
