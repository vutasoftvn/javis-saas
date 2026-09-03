import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { ACADEMY_ARTIFACT_SCHEME, ACADEMY_TEMPLATE_DRAFT_KIND } from "../contracts";

const { academyTemplateExports } = schema;

export interface AcademyTemplateExport {
  id: string;
  workspaceId: string;
  accountId: string;
  templateKind: string;
  body: Record<string, unknown>;
  academySourceRef: string;
  disclaimer: string;
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
  /** Phải là tài khoản người xác nhận rõ ràng — không export nền tự động. */
  confirmedByAccountId: string;
}

const ACADEMY_DISCLAIMER =
  "Template học tập từ Academy — không phải evidence sản xuất. " +
  "Cần con người thay thế bằng nguồn thực tế độc lập trước khi dùng làm evidence.";

const FORBIDDEN_BODY_FIELDS = ["score", "synthetic", "modelFeedback", "feedback"];

function stripSimulationArtifacts(body: Record<string, unknown>): Record<string, unknown> {
  const cleaned: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(body)) {
    if (FORBIDDEN_BODY_FIELDS.includes(key)) continue;
    cleaned[key] = value;
  }
  return cleaned;
}

function mapRow(row: typeof academyTemplateExports.$inferSelect): AcademyTemplateExport {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    accountId: row.accountId.toString(),
    templateKind: row.templateKind,
    body: row.body as Record<string, unknown>,
    academySourceRef: row.academySourceRef,
    disclaimer: row.disclaimer,
    liveArtifactKind: row.liveArtifactKind as typeof ACADEMY_TEMPLATE_DRAFT_KIND,
    exportedAt: row.exportedAt.toISOString(),
    confirmedByAccountId: row.confirmedByAccountId.toString(),
  };
}

/**
 * Exports a labelled template draft into a workspace.
 * Requires explicit human confirmation (`confirmedByAccountId`); no background
 * export runs on lesson/simulation completion.
 */
export async function exportTemplate(params: ExportTemplateParams): Promise<AcademyTemplateExport> {
  if (!params.confirmedByAccountId) {
    throw APIError.invalidArgument(
      "Template export requires an explicit human confirmation (confirmedByAccountId)"
    );
  }
  if (!params.academyAttemptId) {
    throw APIError.invalidArgument("Template export requires academyAttemptId");
  }

  const academySourceRef = `${ACADEMY_ARTIFACT_SCHEME}attempt/${params.academyAttemptId}`;

  const [row] = await db
    .insert(academyTemplateExports)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      accountId: BigInt(params.accountId),
      templateKind: params.templateKind,
      body: stripSimulationArtifacts(params.body),
      academySourceRef,
      disclaimer: ACADEMY_DISCLAIMER,
      liveArtifactKind: ACADEMY_TEMPLATE_DRAFT_KIND,
      confirmedByAccountId: BigInt(params.confirmedByAccountId),
    })
    .returning();

  if (!row) throw APIError.internal("failed to create academy template export");
  return mapRow(row);
}

export async function getTemplateExport(id: string): Promise<AcademyTemplateExport> {
  const [row] = await db
    .select()
    .from(academyTemplateExports)
    .where(eq(academyTemplateExports.id, BigInt(id)))
    .limit(1);
  if (!row) throw APIError.notFound(`academy template export ${id} not found`);
  return mapRow(row);
}
