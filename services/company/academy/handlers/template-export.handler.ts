/**
 * Academy template export handler.
 *
 * ISOLATION RULE: This file MUST NOT import any module from:
 * - `operations/strategy` handlers or services
 * - `operations/handlers` (project, task, etc.)
 * - `commercial` or `finance-legal` handlers
 *
 * A template export is the ONLY sanctioned one-way path from Academy to a
 * live workspace. It never produces Evidence, a source-ingestion record, a
 * gate input, a metric snapshot, or a task — only a labelled draft artifact
 * that a human must independently re-source before it can enter the live
 * evidence ledger (see `assertNotAcademyTemplateDraft`).
 */

import { ACADEMY_ARTIFACT_SCHEME, ACADEMY_TEMPLATE_DRAFT_KIND } from "../contracts";

export interface AcademyTemplateExport {
  id: string;
  workspaceId: string;
  accountId: string;
  templateKind: string;
  body: Record<string, unknown>;
  academySourceRef: string;
  disclaimer: string;
  /** Live artifact kind is always 'academy_template_draft' — never eligible for Evidence. */
  liveArtifactKind: typeof ACADEMY_TEMPLATE_DRAFT_KIND;
  exportedAt: string;
  confirmedByAccountId: string;
}

export interface ExportTemplateParams {
  workspaceId: string;
  accountId: string;
  academyAttemptId: string;
  templateKind: string;
  body: Record<string, unknown>;
  /** Must be the explicit, human-confirming account — no background export. */
  confirmedByAccountId: string;
}

const ACADEMY_DISCLAIMER =
  "Template học tập từ Academy — không phải evidence sản xuất. " +
  "Cần con người thay thế bằng nguồn thực tế độc lập trước khi dùng làm evidence.";

const FORBIDDEN_BODY_FIELDS = ["score", "synthetic", "modelFeedback", "feedback"];

/** Strips simulation score/synthetic/model-feedback fields from an export body. */
function stripSimulationArtifacts(body: Record<string, unknown>): Record<string, unknown> {
  const cleaned: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(body)) {
    if (FORBIDDEN_BODY_FIELDS.includes(key)) continue;
    cleaned[key] = value;
  }
  return cleaned;
}

const _exports: Map<string, AcademyTemplateExport> = new Map();

/**
 * Exports a labelled template draft into a workspace.
 * Requires explicit human confirmation (`confirmedByAccountId`); no background
 * export runs on lesson/simulation completion.
 */
export function exportTemplate(params: ExportTemplateParams): AcademyTemplateExport {
  if (!params.confirmedByAccountId) {
    throw new Error("Template export requires an explicit human confirmation (confirmedByAccountId)");
  }
  if (!params.academyAttemptId) {
    throw new Error("Template export requires academyAttemptId");
  }

  const id = `academy_export_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  const academySourceRef = `${ACADEMY_ARTIFACT_SCHEME}attempt/${params.academyAttemptId}`;

  const record: AcademyTemplateExport = {
    id,
    workspaceId: params.workspaceId,
    accountId: params.accountId,
    templateKind: params.templateKind,
    body: stripSimulationArtifacts(params.body),
    academySourceRef,
    disclaimer: ACADEMY_DISCLAIMER,
    liveArtifactKind: ACADEMY_TEMPLATE_DRAFT_KIND,
    exportedAt: new Date().toISOString(),
    confirmedByAccountId: params.confirmedByAccountId,
  };

  _exports.set(id, record);
  return record;
}

export function getTemplateExport(id: string): AcademyTemplateExport | undefined {
  return _exports.get(id);
}

// ─── Reset for testing ───────────────────────────────────────────────────────
export function _resetTemplateExportStore(): void {
  _exports.clear();
}
