import { api, APIError } from "encore.dev/api";
import { financeLegalDB as db } from "./db";

export interface ValidationHypothesis {
  id: number;
  workspaceId: number;
  projectId?: number | null;
  title: string;
  statement: string;
  confidenceScore: number;
  status: string;
  createdAt: string;
}

export interface CreateHypothesisRequest {
  workspaceId: number;
  projectId?: number | null;
  title: string;
  statement: string;
  confidenceScore?: number;
}

export interface ValidationExperiment {
  id: number;
  workspaceId: number;
  hypothesisId: number;
  experimentType: string;
  title: string;
  status: string;
  startDate?: string | null;
  endDate?: string | null;
  createdAt: string;
}

export interface CreateExperimentRequest {
  workspaceId: number;
  hypothesisId: number;
  experimentType?: string;
  title: string;
  startDate?: string | null;
  endDate?: string | null;
}

export interface EvidenceItem {
  id: number;
  workspaceId: number;
  experimentId: number;
  evidenceType: string;
  title: string;
  content: string;
  strengthScore: number;
  createdAt: string;
}

export interface CreateEvidenceItemRequest {
  workspaceId: number;
  experimentId: number;
  evidenceType?: string;
  title: string;
  content: string;
  strengthScore?: number;
}

// ─── Hypotheses Endpoints ───

export const createHypothesis = api(
  { expose: true, method: "POST", path: "/finance-legal/hypotheses" },
  async (req: CreateHypothesisRequest): Promise<ValidationHypothesis> => {
    if (!req.workspaceId || !req.title || !req.statement) {
      throw APIError.invalidArgument("workspaceId, title, and statement are required");
    }

    const row = await db.queryRow<ValidationHypothesis>`
      INSERT INTO validation.validation_hypotheses (
        workspace_id, project_id, title, statement, confidence_score
      ) VALUES (
        ${req.workspaceId}, ${req.projectId ?? null},
        ${req.title}, ${req.statement}, ${req.confidenceScore ?? 0.5}
      )
      RETURNING
        id, workspace_id as "workspaceId", project_id as "projectId",
        title, statement, confidence_score as "confidenceScore",
        status, created_at as "createdAt"
    `;
    if (!row) throw APIError.internal("Failed to create validation hypothesis");
    return row;
  }
);

export const listHypotheses = api(
  { expose: true, method: "GET", path: "/finance-legal/workspaces/:workspaceId/hypotheses" },
  async (params: { workspaceId: number }): Promise<{ hypotheses: ValidationHypothesis[] }> => {
    const rows = db.query<ValidationHypothesis>`
      SELECT
        id, workspace_id as "workspaceId", project_id as "projectId",
        title, statement, confidence_score as "confidenceScore",
        status, created_at as "createdAt"
      FROM validation.validation_hypotheses
      WHERE workspace_id = ${params.workspaceId}
      ORDER BY id DESC
    `;
    const hypotheses: ValidationHypothesis[] = [];
    for await (const row of rows) hypotheses.push(row);
    return { hypotheses };
  }
);

// ─── Experiments Endpoints ───

export const createExperiment = api(
  { expose: true, method: "POST", path: "/finance-legal/experiments" },
  async (req: CreateExperimentRequest): Promise<ValidationExperiment> => {
    if (!req.workspaceId || !req.hypothesisId || !req.title) {
      throw APIError.invalidArgument("workspaceId, hypothesisId, and title are required");
    }

    const row = await db.queryRow<ValidationExperiment>`
      INSERT INTO validation.validation_experiments (
        workspace_id, hypothesis_id, experiment_type, title,
        start_date, end_date
      ) VALUES (
        ${req.workspaceId}, ${req.hypothesisId},
        ${req.experimentType ?? "INTERVIEW"}, ${req.title},
        ${req.startDate ?? null}, ${req.endDate ?? null}
      )
      RETURNING
        id, workspace_id as "workspaceId", hypothesis_id as "hypothesisId",
        experiment_type as "experimentType", title, status,
        start_date as "startDate", end_date as "endDate", created_at as "createdAt"
    `;
    if (!row) throw APIError.internal("Failed to create validation experiment");
    return row;
  }
);

// ─── Evidence Items Endpoints ───

export const createEvidence = api(
  { expose: true, method: "POST", path: "/finance-legal/evidence" },
  async (req: CreateEvidenceItemRequest): Promise<EvidenceItem> => {
    if (!req.workspaceId || !req.experimentId || !req.title || !req.content) {
      throw APIError.invalidArgument("workspaceId, experimentId, title, and content are required");
    }

    const row = await db.queryRow<EvidenceItem>`
      INSERT INTO validation.evidence_items (
        workspace_id, experiment_id, evidence_type, title, content, strength_score
      ) VALUES (
        ${req.workspaceId}, ${req.experimentId},
        ${req.evidenceType ?? "QUOTE"}, ${req.title},
        ${req.content}, ${req.strengthScore ?? 1.0}
      )
      RETURNING
        id, workspace_id as "workspaceId", experiment_id as "experimentId",
        evidence_type as "evidenceType", title, content,
        strength_score as "strengthScore", created_at as "createdAt"
    `;
    if (!row) throw APIError.internal("Failed to create evidence item");
    return row;
  }
);
