import { APIError } from "encore.dev/api";
import { and, desc, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { assertCommercialProjectInWorkspace } from "./project-record-link.service";
import { assertCrmSchemaAuthority } from "./lead-source.service";
import {
  ProjectLeadRepository,
  LeadFieldDefinitionModel,
  LeadFieldDataType,
  DataClassification,
  AllowedSelectValue,
} from "./project-lead-repository";

const { leadFieldDefinitions } = schema;

export const STANDARD_LEAD_FIELDS = [
  { key: "name", label: "Full Name", dataType: "SHORT_TEXT", required: true, isStandard: true },
  { key: "email", label: "Email", dataType: "SHORT_TEXT", required: false, isStandard: true },
  { key: "phone", label: "Phone Number", dataType: "SHORT_TEXT", required: false, isStandard: true },
  { key: "company", label: "Company Name", dataType: "SHORT_TEXT", required: false, isStandard: true },
  { key: "stage", label: "Pipeline Stage", dataType: "SHORT_TEXT", required: true, isStandard: true },
  { key: "value", label: "Opportunity Value", dataType: "NUMBER", required: false, isStandard: true },
  { key: "source", label: "Lead Source", dataType: "SHORT_TEXT", required: false, isStandard: true },
];

export interface CrmSchemaView {
  projectId: string;
  standardFields: typeof STANDARD_LEAD_FIELDS;
  customFields: LeadFieldDefinitionModel[];
}

export async function getCrmSchemaService(
  ctx: TenantContext,
  projectId: string
): Promise<CrmSchemaView> {
  await assertCommercialProjectInWorkspace(ctx, projectId);

  const customRows = await db
    .select()
    .from(leadFieldDefinitions)
    .where(
      and(
        eq(leadFieldDefinitions.workspaceId, BigInt(ctx.workspaceId)),
        eq(leadFieldDefinitions.projectId, BigInt(projectId))
      )
    )
    .orderBy(desc(leadFieldDefinitions.createdAt));

  const customFields: LeadFieldDefinitionModel[] = customRows.map((row) => ({
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    projectId: String(row.projectId),
    stableKey: row.stableKey,
    version: row.version,
    label: row.label,
    dataType: row.dataType as LeadFieldDataType,
    validation: (row.validationJson as Record<string, unknown>) || {},
    allowedValues: (row.allowedValuesJson as AllowedSelectValue[] | null) || undefined,
    requiredAtStages: (row.requiredAtStagesJson as string[]) || [],
    classification: row.classification as DataClassification,
    agentInputAllowed: row.agentInputAllowed,
    searchable: row.searchable,
    status: row.status as any,
    createdAt: row.createdAt.toISOString(),
    retiredAt: row.retiredAt?.toISOString() || null,
  }));

  return {
    projectId,
    standardFields: STANDARD_LEAD_FIELDS,
    customFields,
  };
}

export async function createFieldDefinitionService(
  ctx: TenantContext,
  projectId: string,
  input: {
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
): Promise<LeadFieldDefinitionModel> {
  assertCrmSchemaAuthority(ctx);
  await assertCommercialProjectInWorkspace(ctx, projectId);

  if (!input.stableKey || !/^[a-z0-9_]+$/.test(input.stableKey)) {
    throw APIError.invalidArgument(
      "stableKey bắt buộc và chỉ chứa chữ thường, số, dấu gạch dưới (lower_snake_case)"
    );
  }

  // Cấm trùng với standard fields
  if (STANDARD_LEAD_FIELDS.some((sf) => sf.key === input.stableKey)) {
    throw APIError.invalidArgument(
      `stableKey '${input.stableKey}' trùng với trường tiêu chuẩn của hệ thống`
    );
  }

  return ProjectLeadRepository.createFieldDefinition({
    workspaceId: ctx.workspaceId,
    projectId,
    stableKey: input.stableKey,
    label: input.label,
    dataType: input.dataType,
    validation: input.validation,
    allowedValues: input.allowedValues,
    requiredAtStages: input.requiredAtStages,
    classification: input.classification,
    agentInputAllowed: input.agentInputAllowed,
    searchable: input.searchable,
    createdBy: ctx.userId,
  });
}

export async function patchFieldDefinitionService(
  ctx: TenantContext,
  projectId: string,
  fieldId: string,
  updates: {
    label?: string;
    allowedValues?: AllowedSelectValue[];
    requiredAtStages?: string[];
  }
): Promise<LeadFieldDefinitionModel> {
  assertCrmSchemaAuthority(ctx);
  await assertCommercialProjectInWorkspace(ctx, projectId);

  const [existing] = await db
    .select()
    .from(leadFieldDefinitions)
    .where(
      and(
        eq(leadFieldDefinitions.id, BigInt(fieldId)),
        eq(leadFieldDefinitions.workspaceId, BigInt(ctx.workspaceId)),
        eq(leadFieldDefinitions.projectId, BigInt(projectId))
      )
    )
    .limit(1);

  if (!existing) {
    throw APIError.notFound("Không tìm thấy field definition");
  }

  if (existing.status === "RETIRED") {
    throw APIError.failedPrecondition("Không thể sửa field definition đã bị retired");
  }

  const [row] = await db
    .update(leadFieldDefinitions)
    .set({
      label: updates.label !== undefined ? updates.label : existing.label,
      allowedValuesJson:
        updates.allowedValues !== undefined ? updates.allowedValues : existing.allowedValuesJson,
      requiredAtStagesJson:
        updates.requiredAtStages !== undefined
          ? updates.requiredAtStages
          : existing.requiredAtStagesJson,
    })
    .where(eq(leadFieldDefinitions.id, BigInt(fieldId)))
    .returning();

  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    projectId: String(row.projectId),
    stableKey: row.stableKey,
    version: row.version,
    label: row.label,
    dataType: row.dataType as LeadFieldDataType,
    validation: (row.validationJson as Record<string, unknown>) || {},
    allowedValues: (row.allowedValuesJson as AllowedSelectValue[] | null) || undefined,
    requiredAtStages: (row.requiredAtStagesJson as string[]) || [],
    classification: row.classification as DataClassification,
    agentInputAllowed: row.agentInputAllowed,
    searchable: row.searchable,
    status: row.status as any,
    createdAt: row.createdAt.toISOString(),
    retiredAt: row.retiredAt?.toISOString() || null,
  };
}

export async function retireFieldDefinitionService(
  ctx: TenantContext,
  projectId: string,
  fieldId: string,
  expectedVersion?: number
): Promise<LeadFieldDefinitionModel> {
  assertCrmSchemaAuthority(ctx);
  await assertCommercialProjectInWorkspace(ctx, projectId);

  const [existing] = await db
    .select()
    .from(leadFieldDefinitions)
    .where(
      and(
        eq(leadFieldDefinitions.id, BigInt(fieldId)),
        eq(leadFieldDefinitions.workspaceId, BigInt(ctx.workspaceId)),
        eq(leadFieldDefinitions.projectId, BigInt(projectId))
      )
    )
    .limit(1);

  if (!existing) {
    throw APIError.notFound("Không tìm thấy field definition");
  }

  if (expectedVersion !== undefined && existing.version !== expectedVersion) {
    throw APIError.aborted(
      `Version conflict: expected version ${expectedVersion}, but found ${existing.version}`
    );
  }

  const [row] = await db
    .update(leadFieldDefinitions)
    .set({
      status: "RETIRED",
      retiredAt: new Date(),
    })
    .where(eq(leadFieldDefinitions.id, BigInt(fieldId)))
    .returning();

  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    projectId: String(row.projectId),
    stableKey: row.stableKey,
    version: row.version,
    label: row.label,
    dataType: row.dataType as LeadFieldDataType,
    validation: (row.validationJson as Record<string, unknown>) || {},
    allowedValues: (row.allowedValuesJson as AllowedSelectValue[] | null) || undefined,
    requiredAtStages: (row.requiredAtStagesJson as string[]) || [],
    classification: row.classification as DataClassification,
    agentInputAllowed: row.agentInputAllowed,
    searchable: row.searchable,
    status: "RETIRED",
    createdAt: row.createdAt.toISOString(),
    retiredAt: row.retiredAt?.toISOString() || null,
  };
}
