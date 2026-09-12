import { APIError } from "encore.dev/api";
import { and, desc, eq, inArray, isNull, sql } from "drizzle-orm";
import * as crypto from "crypto";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const {
  salesLeads,
  leadSources,
  leadFieldDefinitions,
  leadFieldValues,
  leadIdentityKeys,
  leadDedupCandidates,
  leadConsents,
} = schema;

export type LeadFieldDataType =
  | "SHORT_TEXT"
  | "LONG_TEXT"
  | "NUMBER"
  | "BOOLEAN"
  | "DATE"
  | "SINGLE_SELECT"
  | "MULTI_SELECT"
  | "URL";

export type DataClassification =
  | "PUBLIC"
  | "BUSINESS_CONFIDENTIAL"
  | "PERSONAL"
  | "SENSITIVE";

export type LeadFieldStatus = "ACTIVE" | "RETIRED";

export interface AllowedSelectValue {
  key: string;
  label: string;
}

export interface LeadFieldDefinitionModel {
  id: string;
  workspaceId: string;
  projectId: string;
  stableKey: string;
  version: number;
  label: string;
  dataType: LeadFieldDataType;
  validation: Record<string, unknown>;
  allowedValues?: AllowedSelectValue[];
  requiredAtStages: string[];
  classification: DataClassification;
  agentInputAllowed: boolean;
  searchable: boolean;
  status: LeadFieldStatus;
  createdAt: string;
  retiredAt?: string | null;
}

export interface CreateLeadFieldDefinitionParams {
  workspaceId: string;
  projectId: string;
  stableKey: string;
  label: string;
  dataType: LeadFieldDataType;
  validation?: Record<string, unknown>;
  allowedValues?: AllowedSelectValue[];
  requiredAtStages?: string[];
  classification?: DataClassification;
  agentInputAllowed?: boolean;
  searchable?: boolean;
  createdBy?: string;
}

export interface ProjectLeadInput {
  name: string;
  email?: string | null;
  phone?: string | null;
  company?: string | null;
  stage?: string;
  value?: number | null;
  source?: string | null;
  leadSourceId?: string | null;
  provenanceEventId?: string | null;
  ownerMemberId?: string | null;
  utmSource?: string | null;
  utmMedium?: string | null;
  utmCampaign?: string | null;
  utmContent?: string | null;
  utmTerm?: string | null;
  fitScore?: number | null;
  intentScore?: number | null;
  engagementScore?: number | null;
  qualificationStatus?: string | null;
  disqualificationReason?: string | null;
  fieldValues?: Record<string, unknown>; // keyed by stableKey
  consent?: {
    purpose: string;
    lawfulBasis: string;
    policyVersion: string;
    capturedAt?: string;
  };
}

export interface ProjectLeadView {
  id: string;
  workspaceId: string;
  projectId: string;
  name: string;
  email?: string | null;
  phone?: string | null;
  company?: string | null;
  stage: string;
  value?: number | null;
  source?: string | null;
  leadSourceId?: string | null;
  provenanceEventId?: string | null;
  ownerMemberId?: string | null;
  utmSource?: string | null;
  utmMedium?: string | null;
  utmCampaign?: string | null;
  utmContent?: string | null;
  utmTerm?: string | null;
  fitScore?: number | null;
  intentScore?: number | null;
  engagementScore?: number | null;
  qualificationStatus?: string | null;
  disqualificationReason?: string | null;
  fieldValues: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
  duplicateCandidate?: boolean;
  existingLeadId?: string;
}

const HMAC_SECRET = process.env.COSA_CRM_IDENTITY_HMAC_SECRET || "cosa-crm-default-identity-hmac-secret-v1";

export function computeIdentityHash(normalizedValue: string, version: number = 1): string {
  return crypto
    .createHmac("sha256", `${HMAC_SECRET}:v${version}`)
    .update(normalizedValue.trim().toLowerCase())
    .digest("hex");
}

function validateCustomFieldValue(
  def: typeof leadFieldDefinitions.$inferSelect,
  val: unknown
): { isValid: boolean; error?: string } {
  if (val === null || val === undefined) return { isValid: true };

  switch (def.dataType as LeadFieldDataType) {
    case "SHORT_TEXT":
      if (typeof val !== "string") return { isValid: false, error: `${def.label} phải là chuỗi văn bản ngắn` };
      if (val.length > 255) return { isValid: false, error: `${def.label} không được vượt quá 255 ký tự` };
      return { isValid: true };
    case "LONG_TEXT":
      if (typeof val !== "string") return { isValid: false, error: `${def.label} phải là chuỗi văn bản` };
      if (val.length > 5000) return { isValid: false, error: `${def.label} không được vượt quá 5000 ký tự` };
      return { isValid: true };
    case "NUMBER":
      if (typeof val !== "number" || isNaN(val)) return { isValid: false, error: `${def.label} phải là chữ số` };
      return { isValid: true };
    case "BOOLEAN":
      if (typeof val !== "boolean") return { isValid: false, error: `${def.label} phải là giá trị đúng/sai` };
      return { isValid: true };
    case "DATE":
      if (typeof val !== "string" || isNaN(Date.parse(val))) return { isValid: false, error: `${def.label} phải là ngày hợp lệ (ISO)` };
      return { isValid: true };
    case "SINGLE_SELECT": {
      if (typeof val !== "string") return { isValid: false, error: `${def.label} phải là chuỗi` };
      const allowed = (def.allowedValuesJson as AllowedSelectValue[] | null) || [];
      if (!allowed.some((opt) => opt.key === val)) {
        return { isValid: false, error: `${def.label} nhận giá trị không có trong danh sách cho phép` };
      }
      return { isValid: true };
    }
    case "MULTI_SELECT": {
      if (!Array.isArray(val) || !val.every((item) => typeof item === "string")) {
        return { isValid: false, error: `${def.label} phải là mảng các chuỗi` };
      }
      const allowed = (def.allowedValuesJson as AllowedSelectValue[] | null) || [];
      const allowedKeys = new Set(allowed.map((opt) => opt.key));
      for (const item of val) {
        if (!allowedKeys.has(item)) {
          return { isValid: false, error: `${def.label} chứa giá trị '${item}' không hợp lệ` };
        }
      }
      return { isValid: true };
    }
    case "URL":
      if (typeof val !== "string") return { isValid: false, error: `${def.label} phải là URL hợp lệ` };
      try {
        new URL(val);
        return { isValid: true };
      } catch {
        return { isValid: false, error: `${def.label} không phải là định dạng URL hợp lệ` };
      }
    default:
      return { isValid: true };
  }
}

export class ProjectLeadRepository {
  /** Tạo custom field definition cho project. */
  static async createFieldDefinition(
    params: CreateLeadFieldDefinitionParams
  ): Promise<LeadFieldDefinitionModel> {
    const classification = params.classification || "BUSINESS_CONFIDENTIAL";
    const agentInputAllowed =
      classification === "PERSONAL" || classification === "SENSITIVE"
        ? false
        : params.agentInputAllowed ?? true;
    const searchable =
      classification === "PERSONAL" || classification === "SENSITIVE"
        ? false
        : params.searchable ?? true;

    // Tìm version tiếp theo nếu stableKey đã tồn tại
    const existing = await db
      .select({ version: leadFieldDefinitions.version })
      .from(leadFieldDefinitions)
      .where(
        and(
          eq(leadFieldDefinitions.workspaceId, BigInt(params.workspaceId)),
          eq(leadFieldDefinitions.projectId, BigInt(params.projectId)),
          eq(leadFieldDefinitions.stableKey, params.stableKey)
        )
      )
      .orderBy(desc(leadFieldDefinitions.version))
      .limit(1);

    const nextVersion = existing.length > 0 ? existing[0].version + 1 : 1;
    const id = generateSnowflake();

    const [row] = await db
      .insert(leadFieldDefinitions)
      .values({
        id: BigInt(id),
        workspaceId: BigInt(params.workspaceId),
        projectId: BigInt(params.projectId),
        stableKey: params.stableKey,
        version: nextVersion,
        label: params.label,
        dataType: params.dataType,
        validationJson: params.validation || {},
        allowedValuesJson: params.allowedValues || null,
        requiredAtStagesJson: params.requiredAtStages || [],
        classification,
        agentInputAllowed,
        searchable,
        status: "ACTIVE",
        createdBy: params.createdBy ? BigInt(params.createdBy) : null,
      })
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
      status: row.status as LeadFieldStatus,
      createdAt: row.createdAt.toISOString(),
      retiredAt: row.retiredAt?.toISOString() || null,
    };
  }

  /** Lấy danh sách active field definitions cho project. */
  static async getActiveFieldDefinitions(
    workspaceId: string,
    projectId: string
  ): Promise<Array<typeof leadFieldDefinitions.$inferSelect>> {
    return db
      .select()
      .from(leadFieldDefinitions)
      .where(
        and(
          eq(leadFieldDefinitions.workspaceId, BigInt(workspaceId)),
          eq(leadFieldDefinitions.projectId, BigInt(projectId)),
          eq(leadFieldDefinitions.status, "ACTIVE")
        )
      );
  }

  /** Tạo Project Lead với transaction an toàn: lead, custom values, identity keys, consent, dedup check. */
  static async createLead(
    workspaceId: string,
    projectId: string,
    input: ProjectLeadInput,
    existingTx?: any
  ): Promise<ProjectLeadView> {
    const wsId = BigInt(workspaceId);
    const projId = BigInt(projectId);

    // 1. Tải active field definitions của Project này
    const activeDefs = await this.getActiveFieldDefinitions(workspaceId, projectId);
    const defMap = new Map<string, typeof leadFieldDefinitions.$inferSelect>();
    for (const def of activeDefs) {
      defMap.set(def.stableKey, def);
    }

    // 2. Validate custom field values
    const customValuesToInsert: Array<{
      defId: bigint;
      valJson: unknown;
      normSearch?: string | null;
    }> = [];

    if (input.fieldValues) {
      for (const [key, val] of Object.entries(input.fieldValues)) {
        const def = defMap.get(key);
        if (!def) {
          throw APIError.invalidArgument(
            `Field definition '${key}' không tồn tại hoặc đã bị retired trong project này`
          );
        }
        const validation = validateCustomFieldValue(def, val);
        if (!validation.isValid) {
          throw APIError.invalidArgument(validation.error || `Giá trị không hợp lệ cho field ${key}`);
        }
        const normSearch =
          def.searchable && typeof val === "string" ? val.toLowerCase().trim() : null;
        customValuesToInsert.push({
          defId: def.id,
          valJson: val,
          normSearch,
        });
      }
    }

    // Check requiredAtStages
    const currentStage = input.stage || "NEW";
    for (const def of activeDefs) {
      const requiredStages = (def.requiredAtStagesJson as string[]) || [];
      if (requiredStages.includes(currentStage)) {
        const provided = input.fieldValues && input.fieldValues[def.stableKey] !== undefined;
        if (!provided) {
          throw APIError.invalidArgument(`Trường '${def.label}' là bắt buộc tại giai đoạn ${currentStage}`);
        }
      }
    }

    // 3. Chuẩn bị Identity Keys (email, phone)
    const identityHashes: Array<{ keyType: string; hash: string }> = [];
    if (input.email && input.email.trim()) {
      identityHashes.push({ keyType: "email", hash: computeIdentityHash(input.email) });
    }
    if (input.phone && input.phone.trim()) {
      identityHashes.push({ keyType: "phone", hash: computeIdentityHash(input.phone) });
    }

    const executeInTransaction = async (tx: any) => {
      // 4. Kiểm tra duplicate candidate
      let isDuplicate = false;
      let existingLeadId: string | undefined;

      if (identityHashes.length > 0) {
        for (const idKey of identityHashes) {
          const [found] = await tx
            .select({ leadId: leadIdentityKeys.leadId })
            .from(leadIdentityKeys)
            .where(
              and(
                eq(leadIdentityKeys.workspaceId, wsId),
                eq(leadIdentityKeys.keyType, idKey.keyType),
                eq(leadIdentityKeys.keyHash, idKey.hash)
              )
            )
            .limit(1);

          if (found) {
            isDuplicate = true;
            existingLeadId = String(found.leadId);
            break;
          }
        }
      }

      // 5. Tạo row sales_leads
      const leadId = generateSnowflake();
      const [newLead] = await tx
        .insert(salesLeads)
        .values({
          id: BigInt(leadId),
          workspaceId: wsId,
          projectId: projId,
          name: input.name,
          company: input.company || null,
          stage: currentStage,
          value: input.value || null,
          source: input.source || null,
          leadSourceId: input.leadSourceId ? BigInt(input.leadSourceId) : null,
          provenanceEventId: input.provenanceEventId ? BigInt(input.provenanceEventId) : null,
          ownerMemberId: input.ownerMemberId ? BigInt(input.ownerMemberId) : null,
          utmSource: input.utmSource || null,
          utmMedium: input.utmMedium || null,
          utmCampaign: input.utmCampaign || null,
          utmContent: input.utmContent || null,
          utmTerm: input.utmTerm || null,
          fitScore: input.fitScore || null,
          intentScore: input.intentScore || null,
          engagementScore: input.engagementScore || null,
          qualificationStatus: input.qualificationStatus || null,
          disqualificationReason: input.disqualificationReason || null,
        })
        .returning();

      // 6. Lưu custom field values
      for (const item of customValuesToInsert) {
        const valId = generateSnowflake();
        await tx.insert(leadFieldValues).values({
          id: BigInt(valId),
          workspaceId: wsId,
          projectId: projId,
          leadId: BigInt(leadId),
          fieldDefinitionId: item.defId,
          valueJson: item.valJson,
          normalizedSearchValue: item.normSearch || null,
          sourceKind: "manual",
        });
      }

      // 7. Lưu Identity Keys
      for (const idKey of identityHashes) {
        const keyId = generateSnowflake();
        await tx
          .insert(leadIdentityKeys)
          .values({
            id: BigInt(keyId),
            workspaceId: wsId,
            projectId: projId,
            leadId: BigInt(leadId),
            keyType: idKey.keyType,
            keyHash: idKey.hash,
            keyVersion: 1,
          })
          .onConflictDoNothing();
      }

      // 8. Nếu duplicate -> tạo record lead_dedup_candidates
      if (isDuplicate && existingLeadId) {
        const dedupId = generateSnowflake();
        await tx.insert(leadDedupCandidates).values({
          id: BigInt(dedupId),
          workspaceId: wsId,
          projectId: projId,
          incomingLeadId: BigInt(leadId),
          existingLeadId: BigInt(existingLeadId),
          reasonCodesJson: ["EXACT_IDENTITY_KEY_MATCH"],
          state: "NEEDS_REVIEW",
        });
      }

      // 9. Lưu Consent nếu có
      if (input.consent) {
        const consentId = generateSnowflake();
        await tx.insert(leadConsents).values({
          id: BigInt(consentId),
          workspaceId: wsId,
          projectId: projId,
          leadId: BigInt(leadId),
          purpose: input.consent.purpose,
          lawfulBasis: input.consent.lawfulBasis,
          consentState: "GRANTED",
          policyVersion: input.consent.policyVersion,
          capturedAt: input.consent.capturedAt ? new Date(input.consent.capturedAt) : new Date(),
          provenanceEventId: input.provenanceEventId ? BigInt(input.provenanceEventId) : null,
        });
      }

      return {
        id: String(newLead.id),
        workspaceId: String(newLead.workspaceId),
        projectId: String(newLead.projectId),
        name: newLead.name,
        email: input.email || null,
        phone: input.phone || null,
        company: newLead.company,
        stage: newLead.stage,
        value: newLead.value,
        source: newLead.source,
        leadSourceId: newLead.leadSourceId ? String(newLead.leadSourceId) : null,
        provenanceEventId: newLead.provenanceEventId ? String(newLead.provenanceEventId) : null,
        ownerMemberId: newLead.ownerMemberId ? String(newLead.ownerMemberId) : null,
        utmSource: newLead.utmSource,
        utmMedium: newLead.utmMedium,
        utmCampaign: newLead.utmCampaign,
        utmContent: newLead.utmContent,
        utmTerm: newLead.utmTerm,
        fitScore: newLead.fitScore,
        intentScore: newLead.intentScore,
        engagementScore: newLead.engagementScore,
        qualificationStatus: newLead.qualificationStatus,
        disqualificationReason: newLead.disqualificationReason,
        fieldValues: input.fieldValues || {},
        createdAt: newLead.createdAt.toISOString(),
        updatedAt: newLead.updatedAt.toISOString(),
        duplicateCandidate: isDuplicate,
        existingLeadId,
      };
    };

    if (existingTx) {
      return await executeInTransaction(existingTx);
    }
    return await db.transaction(executeInTransaction);
  }

  /** Lấy danh sách leads thuộc project với pagination. */
  static async listLeads(
    workspaceId: string,
    projectId: string,
    options?: { limit?: number; offset?: number }
  ): Promise<ProjectLeadView[]> {
    const wsId = BigInt(workspaceId);
    const projId = BigInt(projectId);
    const limit = options?.limit || 50;
    const offset = options?.offset || 0;

    const leads = await db
      .select()
      .from(salesLeads)
      .where(and(eq(salesLeads.workspaceId, wsId), eq(salesLeads.projectId, projId)))
      .orderBy(desc(salesLeads.createdAt))
      .limit(limit)
      .offset(offset);

    if (leads.length === 0) return [];

    const leadIds = leads.map((l) => l.id);

    // Tải custom field values tương ứng
    const values = await db
      .select({
        leadId: leadFieldValues.leadId,
        stableKey: leadFieldDefinitions.stableKey,
        val: leadFieldValues.valueJson,
      })
      .from(leadFieldValues)
      .innerJoin(
        leadFieldDefinitions,
        eq(leadFieldValues.fieldDefinitionId, leadFieldDefinitions.id)
      )
      .where(inArray(leadFieldValues.leadId, leadIds));

    const valuesByLeadId = new Map<string, Record<string, unknown>>();
    for (const v of values) {
      const lid = String(v.leadId);
      if (!valuesByLeadId.has(lid)) {
        valuesByLeadId.set(lid, {});
      }
      valuesByLeadId.get(lid)![v.stableKey] = v.val;
    }

    return leads.map((l) => ({
      id: String(l.id),
      workspaceId: String(l.workspaceId),
      projectId: String(l.projectId),
      name: l.name,
      company: l.company,
      stage: l.stage,
      value: l.value,
      source: l.source,
      leadSourceId: l.leadSourceId ? String(l.leadSourceId) : null,
      provenanceEventId: l.provenanceEventId ? String(l.provenanceEventId) : null,
      ownerMemberId: l.ownerMemberId ? String(l.ownerMemberId) : null,
      utmSource: l.utmSource,
      utmMedium: l.utmMedium,
      utmCampaign: l.utmCampaign,
      utmContent: l.utmContent,
      utmTerm: l.utmTerm,
      fitScore: l.fitScore,
      intentScore: l.intentScore,
      engagementScore: l.engagementScore,
      qualificationStatus: l.qualificationStatus,
      disqualificationReason: l.disqualificationReason,
      fieldValues: valuesByLeadId.get(String(l.id)) || {},
      createdAt: l.createdAt.toISOString(),
      updatedAt: l.updatedAt.toISOString(),
    }));
  }
}
