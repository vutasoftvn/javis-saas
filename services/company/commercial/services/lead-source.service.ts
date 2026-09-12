import { APIError } from "encore.dev/api";
import { and, desc, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { assertCommercialProjectInWorkspace } from "./project-record-link.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { leadSources } = schema;

export type LeadSourceType =
  | "landing_form"
  | "manual"
  | "csv_import"
  | "referral_partner"
  | "campaign_event"
  | "inbound_conversation";

export const ALLOWED_SOURCE_TYPES: readonly LeadSourceType[] = [
  "landing_form",
  "manual",
  "csv_import",
  "referral_partner",
  "campaign_event",
  "inbound_conversation",
];

export interface LeadSourceModel {
  id: string;
  workspaceId: string;
  projectId: string;
  sourceType: LeadSourceType;
  label: string;
  status: string;
  configurationRevision: number;
  createdBy?: string | null;
  createdAt: string;
  updatedAt: string;
}

export function assertCrmSchemaAuthority(ctx: TenantContext): void {
  const role = ctx.membershipRole?.toLowerCase();
  if (role !== "founder" && role !== "admin" && role !== "owner") {
    throw APIError.permissionDenied("Chỉ Founder hoặc Admin mới có quyền cấu hình CRM schema và lead sources");
  }
}

export async function createLeadSourceService(
  ctx: TenantContext,
  projectId: string,
  params: { sourceType: string; label: string }
): Promise<LeadSourceModel> {
  assertCrmSchemaAuthority(ctx);
  await assertCommercialProjectInWorkspace(ctx, projectId);

  if (!ALLOWED_SOURCE_TYPES.includes(params.sourceType as LeadSourceType)) {
    throw APIError.invalidArgument(
      `sourceType không hợp lệ. Cho phép: ${ALLOWED_SOURCE_TYPES.join(", ")}`
    );
  }

  if (!params.label || !params.label.trim()) {
    throw APIError.invalidArgument("Label cho lead source là bắt buộc");
  }

  const id = generateSnowflake();
  const [row] = await db
    .insert(leadSources)
    .values({
      id: BigInt(id),
      workspaceId: BigInt(ctx.workspaceId),
      projectId: BigInt(projectId),
      sourceType: params.sourceType,
      label: params.label.trim(),
      status: "ACTIVE",
      configurationRevision: 1,
      createdBy: ctx.userId ? BigInt(ctx.userId) : null,
    })
    .returning();

  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    projectId: String(row.projectId),
    sourceType: row.sourceType as LeadSourceType,
    label: row.label,
    status: row.status,
    configurationRevision: row.configurationRevision,
    createdBy: row.createdBy ? String(row.createdBy) : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function listLeadSourcesService(
  ctx: TenantContext,
  projectId: string
): Promise<LeadSourceModel[]> {
  await assertCommercialProjectInWorkspace(ctx, projectId);

  const rows = await db
    .select()
    .from(leadSources)
    .where(
      and(
        eq(leadSources.workspaceId, BigInt(ctx.workspaceId)),
        eq(leadSources.projectId, BigInt(projectId))
      )
    )
    .orderBy(desc(leadSources.createdAt));

  return rows.map((row) => ({
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    projectId: String(row.projectId),
    sourceType: row.sourceType as LeadSourceType,
    label: row.label,
    status: row.status,
    configurationRevision: row.configurationRevision,
    createdBy: row.createdBy ? String(row.createdBy) : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  }));
}
