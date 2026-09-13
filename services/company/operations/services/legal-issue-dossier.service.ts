import { APIError } from "encore.dev/api";
import { and, desc, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import { getObligationService } from "../../finance-legal/services/legal-obligation.service";

const { projects, legalIssueDossiers, legalIssueDossierRevisions } = schema;

export type LegalIssueDossierStatus = "DRAFT" | "CONFIRMED" | "SUPERSEDED";

/**
 * Allowlist cố định phân loại vấn đề pháp lý — mirror pattern các dossier
 * khác (RiskSignalCategory/SecurityFindingCategory): KHÔNG phải gợi ý, mà là
 * toàn bộ tập hợp giá trị hợp lệ, chống nhét free-text vào field category.
 */
export type LegalIssueCategory =
  | "CONTRACT_QUESTION"
  | "REGULATORY_QUESTION"
  | "IP_QUESTION"
  | "EMPLOYMENT_QUESTION"
  | "DATA_PRIVACY_QUESTION"
  | "ENTITY_STRUCTURE_QUESTION"
  | "DISPUTE_QUESTION"
  | "OTHER";

const LEGAL_ISSUE_CATEGORIES: ReadonlySet<string> = new Set<LegalIssueCategory>([
  "CONTRACT_QUESTION",
  "REGULATORY_QUESTION",
  "IP_QUESTION",
  "EMPLOYMENT_QUESTION",
  "DATA_PRIVACY_QUESTION",
  "ENTITY_STRUCTURE_QUESTION",
  "DISPUTE_QUESTION",
  "OTHER",
]);

/**
 * Fixed enum bắt buộc (task-1-brief §Global Constraints: "missing
 * applicability is an explicit unknown/escalation") — KHÔNG BAO GIỜ null/
 * undefined khi applicability chưa xác định được qua finance-legal. Dossier
 * này KHÔNG tự đặt legal applicability (đó là thẩm quyền riêng của
 * `legal-applicability.service.ts`) — field này chỉ ghi lại trạng thái
 * applicability ĐÃ ĐƯỢC người dùng/quy trình khác xác định hoặc escalate,
 * chưa bao giờ tự suy luận.
 */
export type LegalApplicabilityStatus = "APPLICABLE" | "NOT_APPLICABLE" | "UNKNOWN" | "ESCALATED";

const LEGAL_APPLICABILITY_STATUSES: ReadonlySet<string> = new Set<LegalApplicabilityStatus>([
  "APPLICABLE",
  "NOT_APPLICABLE",
  "UNKNOWN",
  "ESCALATED",
]);

export type LegalIssueReasonCode =
  | "ISSUE_RAISED"
  | "REFERENCE_UPDATED"
  | "APPLICABILITY_UPDATED"
  | "ESCALATED"
  | "FOUNDER_REVIEW";

const LEGAL_ISSUE_REASON_CODES: ReadonlySet<string> = new Set<LegalIssueReasonCode>([
  "ISSUE_RAISED",
  "REFERENCE_UPDATED",
  "APPLICABILITY_UPDATED",
  "ESCALATED",
  "FOUNDER_REVIEW",
]);

/**
 * `recordType` cố định — hiện chỉ hỗ trợ tham chiếu tới
 * `legal.legal_obligations` (qua `getObligationService`). Thêm loại bản ghi
 * legal mới (vd. entity profile, applicability assessment) PHẢI thêm giá trị
 * vào đây VÀ thêm nhánh validate tương ứng trong `assertLegalRecordRefsResolve`
 * — không tự suy diễn recordType nào cũng "resolve được".
 */
export type LegalRecordType = "OBLIGATION";

const LEGAL_RECORD_TYPES: ReadonlySet<string> = new Set<LegalRecordType>(["OBLIGATION"]);

/**
 * Tham chiếu tới một bản ghi legal THẬT đã tồn tại trong finance-legal —
 * KHÔNG BAO GIỜ sao chép nội dung bản ghi đó vào dossier này (task-1-brief:
 * "referencing (not duplicating) real legal records"). `recordId` bắt buộc
 * phải resolve được qua Finance-Legal read service tại thời điểm ghi
 * (xem `assertLegalRecordRefsResolve`) — một id không tồn tại/thuộc workspace
 * khác bị reject bằng `invalid_argument`, không âm thầm chấp nhận.
 */
export interface LegalRecordRef {
  recordType: LegalRecordType;
  recordId: string;
  classification?: string;
}

export interface LegalIssueSnapshot {
  dossierId: string;
  revision: number;
  issueCategory: LegalIssueCategory;
  legalRecordRefs: LegalRecordRef[];
  applicabilityStatus: LegalApplicabilityStatus;
  jurisdiction?: string;
  redactedQuestion: string;
  status: LegalIssueDossierStatus;
}

export interface CreateLegalIssueDossierInput {
  projectId: string;
  issueCategory: LegalIssueCategory;
  legalRecordRefs?: LegalRecordRef[];
  applicabilityStatus?: LegalApplicabilityStatus;
  jurisdiction?: string;
  redactedQuestion: string;
  reasonCode: LegalIssueReasonCode;
}

/**
 * Append LUÔN yêu cầu lại đầy đủ `issueCategory`/`redactedQuestion` (không
 * ngầm giữ nguyên giá trị revision trước) — mirror full-replace semantics đã
 * thiết lập ở các dossier khác (controls/findings/evidenceRefs của Security
 * Posture Dossier), mở rộng sang cả 2 field scalar cốt lõi này để mỗi
 * revision luôn là một bản ghi TƯỜNG MINH, tự chứa toàn bộ nội dung đã ghi
 * nhận tại thời điểm đó — không có state ẩn nào carry-over từ revision cũ mà
 * người đọc audit log không nhìn thấy trực tiếp trong chính revision đó.
 */
export interface AppendLegalIssueRevisionInput {
  issueCategory: LegalIssueCategory;
  legalRecordRefs?: LegalRecordRef[];
  applicabilityStatus?: LegalApplicabilityStatus;
  jurisdiction?: string;
  redactedQuestion: string;
  status?: "DRAFT" | "CONFIRMED";
  reasonCode: LegalIssueReasonCode;
}

// ---------------------------------------------------------------------------
// Validation — allowlist nghiêm ngặt + deep-scan chặn contract-body/PII/
// privileged-advice-shaped string ở BẤT KỲ field nào (kể cả field hợp lệ),
// mirror pattern `deepAssertNoSecret`/`deepAssertNoPii` của Security Posture/
// People Risk Dossier. Đây là headline "never project contract bodies,
// personal data or privileged advice" property của dossier này (task-1-brief
// §Global Constraints) — reject chủ động bằng `invalid_argument`, không chỉ
// "không có chỗ để lưu".
// ---------------------------------------------------------------------------

const ALLOWED_CREATE_KEYS = new Set([
  "projectId",
  "issueCategory",
  "legalRecordRefs",
  "applicabilityStatus",
  "jurisdiction",
  "redactedQuestion",
  "reasonCode",
]);

const ALLOWED_APPEND_KEYS = new Set([
  "issueCategory",
  "legalRecordRefs",
  "applicabilityStatus",
  "jurisdiction",
  "redactedQuestion",
  "status",
  "reasonCode",
]);

const ALLOWED_LEGAL_RECORD_REF_KEYS = new Set(["recordType", "recordId", "classification"]);

// PII — mirror EMAIL_PATTERN/PHONE_PATTERN của people-risk-dossier.service.ts.
const EMAIL_PATTERN = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i;
const PHONE_PATTERN = /(\+\d[\d\-.\s()]{6,14}\d)|(\(\d{3}\)[\s.-]?\d{3}[\s.-]\d{4})|(\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b)/;

// Contract-body boilerplate — dấu hiệu của toàn văn hợp đồng bị dán nhầm vào
// thay vì một câu hỏi đã redact. Không cố phát hiện MỌI hợp đồng, chỉ các
// marker phổ biến, thực dụng và có thể test.
const CONTRACT_BOILERPLATE_PATTERNS: ReadonlyArray<{ name: string; re: RegExp }> = [
  { name: "whereas_clause", re: /\bWHEREAS\b/i },
  { name: "witness_clause", re: /\bIN WITNESS WHEREOF\b/i },
  { name: "now_therefore_clause", re: /\bNOW,?\s+THEREFORE\b/i },
  { name: "this_agreement_clause", re: /\bTHIS AGREEMENT\b/i },
  { name: "hereinafter_clause", re: /\bHEREINAFTER REFERRED TO AS\b/i },
  { name: "entire_agreement_clause", re: /\bENTIRE AGREEMENT\b/i },
  { name: "governing_law_clause", re: /\bGOVERNING LAW\b/i },
];

// Privileged-advice language — dấu hiệu tư vấn privileged bị dán nhầm vào
// thay vì một câu hỏi đã redact.
const PRIVILEGED_ADVICE_PATTERNS: ReadonlyArray<{ name: string; re: RegExp }> = [
  { name: "attorney_client_privilege", re: /\bATTORNEY[\s-]CLIENT PRIVILEGE(D)?\b/i },
  { name: "privileged_and_confidential", re: /\bPRIVILEGED\s+(AND|&)\s+CONFIDENTIAL\b/i },
  { name: "counsel_opinion", re: /\bCOUNSEL'?S?\s+(OPINION|ADVICE)\b/i },
  { name: "outside_counsel_advises", re: /\bOUTSIDE COUNSEL\s+(ADVISES|RECOMMENDS|OPINES)\b/i },
  { name: "work_product_doctrine", re: /\bWORK PRODUCT DOCTRINE\b/i },
];

// Câu hỏi đã redact không có lý do gì cần dài hơn ngưỡng này — một chuỗi dài
// hơn được coi là "trông giống" toàn văn hợp đồng/tài liệu dán nhầm vào, kể
// cả khi không khớp marker cụ thể nào (mirror "at minimum length caps" của
// task-1-brief).
const MAX_FREE_TEXT_LENGTH = 800;

function assertNoContractBodyOrPrivilegedOrPii(value: string, path: string): void {
  if (EMAIL_PATTERN.test(value)) {
    throw APIError.invalidArgument(
      `LEGAL_DOSSIER_PII_REJECTED: "${path}" looks like an email address — personal data is never allowed in this dossier`
    );
  }
  if (PHONE_PATTERN.test(value)) {
    throw APIError.invalidArgument(
      `LEGAL_DOSSIER_PII_REJECTED: "${path}" looks like a phone number — personal data is never allowed in this dossier`
    );
  }
  for (const { name, re } of CONTRACT_BOILERPLATE_PATTERNS) {
    if (re.test(value)) {
      throw APIError.invalidArgument(
        `LEGAL_DOSSIER_CONTRACT_BODY_REJECTED: "${path}" looks like ${name} contract boilerplate — full contract bodies are never allowed in this dossier`
      );
    }
  }
  for (const { name, re } of PRIVILEGED_ADVICE_PATTERNS) {
    if (re.test(value)) {
      throw APIError.invalidArgument(
        `LEGAL_DOSSIER_PRIVILEGED_ADVICE_REJECTED: "${path}" looks like ${name} — privileged advice is never allowed in this dossier`
      );
    }
  }
  if (value.length > MAX_FREE_TEXT_LENGTH) {
    throw APIError.invalidArgument(
      `LEGAL_DOSSIER_CONTRACT_BODY_REJECTED: "${path}" exceeds ${MAX_FREE_TEXT_LENGTH} characters — a redacted question should never be this long, this looks like a pasted document`
    );
  }
}

/**
 * Quét đệ quy TOÀN BỘ input tìm chuỗi giống contract-body/PII/privileged-
 * advice — kể cả field đã nằm trong allowlist key (mirror
 * `deepAssertNoSecret`/`deepAssertNoPii` của Security Posture/People Risk
 * Dossier).
 */
function deepAssertSafeShape(value: unknown, path: string): void {
  if (typeof value === "string") {
    assertNoContractBodyOrPrivilegedOrPii(value, path);
  } else if (Array.isArray(value)) {
    value.forEach((v, i) => deepAssertSafeShape(v, `${path}[${i}]`));
  } else if (value && typeof value === "object") {
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      deepAssertSafeShape(v, `${path}.${k}`);
    }
  }
}

function assertPlainObject(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw APIError.invalidArgument(`LEGAL_DOSSIER_SHAPE_INVALID: "${path}" must be an object`);
  }
  return value as Record<string, unknown>;
}

function assertOnlyAllowedKeys(obj: Record<string, unknown>, allowed: ReadonlySet<string>, path: string): void {
  for (const key of Object.keys(obj)) {
    if (!allowed.has(key)) {
      throw APIError.invalidArgument(
        `LEGAL_DOSSIER_FIELD_REJECTED: "${key}" is not an allowed field on ${path} — this dossier only accepts classified issue metadata and record references`
      );
    }
  }
}

function assertValidReasonCode(value: unknown, path: string): LegalIssueReasonCode {
  if (typeof value !== "string" || !LEGAL_ISSUE_REASON_CODES.has(value)) {
    throw APIError.invalidArgument(
      `LEGAL_DOSSIER_SHAPE_INVALID: "${path}" must be one of the fixed allowed reason codes — free text is not accepted`
    );
  }
  return value as LegalIssueReasonCode;
}

function assertValidIssueCategory(value: unknown, path: string): LegalIssueCategory {
  if (typeof value !== "string" || !LEGAL_ISSUE_CATEGORIES.has(value)) {
    throw APIError.invalidArgument(
      `LEGAL_DOSSIER_SHAPE_INVALID: "${path}" must be one of the fixed allowed issue categories`
    );
  }
  return value as LegalIssueCategory;
}

/**
 * Trả về UNKNOWN theo mặc định — không bao giờ null/undefined (task-1-brief
 * §Global Constraints).
 */
function normalizeApplicabilityStatus(raw: unknown, path: string): LegalApplicabilityStatus {
  if (raw === undefined) return "UNKNOWN";
  if (typeof raw !== "string" || !LEGAL_APPLICABILITY_STATUSES.has(raw)) {
    throw APIError.invalidArgument(
      `LEGAL_DOSSIER_SHAPE_INVALID: "${path}" must be one of APPLICABLE|NOT_APPLICABLE|UNKNOWN|ESCALATED`
    );
  }
  return raw as LegalApplicabilityStatus;
}

function normalizeJurisdiction(raw: unknown, path: string): string | undefined {
  if (raw === undefined) return undefined;
  if (typeof raw !== "string" || !raw.trim()) {
    throw APIError.invalidArgument(`LEGAL_DOSSIER_SHAPE_INVALID: "${path}" must be a non-empty string`);
  }
  if (raw.length > 64) {
    throw APIError.invalidArgument(`LEGAL_DOSSIER_SHAPE_INVALID: "${path}" must be at most 64 characters`);
  }
  return raw;
}

function assertValidRedactedQuestion(raw: unknown, path: string): string {
  if (typeof raw !== "string" || !raw.trim()) {
    throw APIError.invalidArgument(`LEGAL_DOSSIER_SHAPE_INVALID: "${path}" is required`);
  }
  return raw;
}

function normalizeLegalRecordRefs(raw: unknown): LegalRecordRef[] {
  if (raw === undefined) return [];
  if (!Array.isArray(raw)) {
    throw APIError.invalidArgument("LEGAL_DOSSIER_SHAPE_INVALID: legalRecordRefs must be an array");
  }
  return raw.map((item, i) => {
    const obj = assertPlainObject(item, `legalRecordRefs[${i}]`);
    assertOnlyAllowedKeys(obj, ALLOWED_LEGAL_RECORD_REF_KEYS, `legalRecordRefs[${i}]`);
    const { recordType, recordId, classification } = obj;
    if (typeof recordType !== "string" || !LEGAL_RECORD_TYPES.has(recordType)) {
      throw APIError.invalidArgument(
        `LEGAL_DOSSIER_SHAPE_INVALID: legalRecordRefs[${i}].recordType must be one of the fixed allowed record types`
      );
    }
    if (typeof recordId !== "string" || !recordId.trim()) {
      throw APIError.invalidArgument(`LEGAL_DOSSIER_SHAPE_INVALID: legalRecordRefs[${i}].recordId is required`);
    }
    if (classification !== undefined && typeof classification !== "string") {
      throw APIError.invalidArgument(
        `LEGAL_DOSSIER_SHAPE_INVALID: legalRecordRefs[${i}].classification must be a string`
      );
    }
    return {
      recordType: recordType as LegalRecordType,
      recordId,
      classification: classification as string | undefined,
    };
  });
}

/**
 * Validate `legalRecordRefs` tham chiếu tới bản ghi legal THẬT qua Finance-
 * Legal read service — KHÔNG dùng SQL cross-schema access (task-1-brief:
 * "use existing Finance-Legal read service, not SQL cross-schema access").
 * `getObligationService` tự scope theo `ctx.workspaceId` — một `recordId`
 * không tồn tại HOẶC thuộc workspace khác đều throw `not_found` từ service
 * đó, ở đây convert thành `invalid_argument` (tham chiếu sai/không hợp lệ
 * trong chính input, không phải lỗi truy cập tài nguyên đang thao tác).
 */
async function assertLegalRecordRefsResolve(refs: LegalRecordRef[], ctx: TenantContext): Promise<void> {
  for (const ref of refs) {
    if (ref.recordType === "OBLIGATION") {
      try {
        await getObligationService(ref.recordId, ctx);
      } catch {
        throw APIError.invalidArgument(
          `LEGAL_DOSSIER_RECORD_REF_UNRESOLVED: legalRecordRefs entry recordId="${ref.recordId}" does not resolve to a real legal obligation in this workspace via the Finance-Legal service`
        );
      }
    }
  }
}

function validateCreateInput(input: unknown): CreateLegalIssueDossierInput {
  const obj = assertPlainObject(input, "input");
  deepAssertSafeShape(obj, "input");
  assertOnlyAllowedKeys(obj, ALLOWED_CREATE_KEYS, "input");
  if (typeof obj.projectId !== "string" || !obj.projectId.trim()) {
    throw APIError.invalidArgument("projectId is required");
  }
  return {
    projectId: obj.projectId,
    issueCategory: assertValidIssueCategory(obj.issueCategory, "issueCategory"),
    legalRecordRefs: normalizeLegalRecordRefs(obj.legalRecordRefs),
    applicabilityStatus: normalizeApplicabilityStatus(obj.applicabilityStatus, "applicabilityStatus"),
    jurisdiction: normalizeJurisdiction(obj.jurisdiction, "jurisdiction"),
    redactedQuestion: assertValidRedactedQuestion(obj.redactedQuestion, "redactedQuestion"),
    reasonCode: assertValidReasonCode(obj.reasonCode, "reasonCode"),
  };
}

function validateAppendInput(input: unknown): AppendLegalIssueRevisionInput {
  const obj = assertPlainObject(input, "input");
  deepAssertSafeShape(obj, "input");
  assertOnlyAllowedKeys(obj, ALLOWED_APPEND_KEYS, "input");
  if (obj.status !== undefined && obj.status !== "DRAFT" && obj.status !== "CONFIRMED") {
    throw APIError.invalidArgument("LEGAL_DOSSIER_SHAPE_INVALID: status must be DRAFT or CONFIRMED");
  }
  return {
    issueCategory: assertValidIssueCategory(obj.issueCategory, "issueCategory"),
    legalRecordRefs: normalizeLegalRecordRefs(obj.legalRecordRefs),
    applicabilityStatus: normalizeApplicabilityStatus(obj.applicabilityStatus, "applicabilityStatus"),
    jurisdiction: normalizeJurisdiction(obj.jurisdiction, "jurisdiction"),
    redactedQuestion: assertValidRedactedQuestion(obj.redactedQuestion, "redactedQuestion"),
    status: obj.status as "DRAFT" | "CONFIRMED" | undefined,
    reasonCode: assertValidReasonCode(obj.reasonCode, "reasonCode"),
  };
}

/**
 * Guard bắt buộc: chỉ human context (không phải AI agent) mới được tạo/append
 * Legal Issue Dossier — GC advisory chỉ được đề xuất qua kênh riêng
 * (skillpack, không phải ghi trực tiếp), KHÔNG BAO GIỜ tự ghi bản ghi vấn đề
 * pháp lý chính thức, KHÔNG tự tạo/sửa legal entity, ký/duyệt hợp đồng, đặt
 * legal applicability, nộp hồ sơ/liên hệ regulator, hay thuê luật sư
 * (CLAUDE.md quy tắc 1, 5, 8; task-1-brief §Global Constraints). Project phải
 * thuộc đúng Workspace của ctx — chống truy cập chéo project/workspace.
 *
 * Ghi chú (mirror security-posture.service.ts): qua các endpoint public hiện
 * có, `ctx.isAiAgent` không bao giờ true trong thực tế — transport-level auth
 * (`requireWorkspaceAccess` → `resolveTenantContext`) đã tự reject bất kỳ
 * token nào ký bởi `COSA_COMPANY_DELEGATION_SECRET` bằng
 * `APIError.unauthenticated` TRƯỚC KHI tới được service function này — xem
 * test "rejects a COSA-delegation-signed token before any TenantContext is
 * built". Check `ctx.isAiAgent` dưới đây vẫn giữ làm defense-in-depth cho một
 * endpoint nội bộ tương lai có thể tái dùng service function này với
 * `TenantContext` dựng từ cosa-delegation.
 */
function requireHumanContext(ctx: TenantContext): void {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }
  if (ctx.isAiAgent) {
    throw APIError.permissionDenied(
      "LEGAL_DOSSIER_HUMAN_REQUIRED: Only a human Founder/member context can create or append a legal issue dossier"
    );
  }
}

async function requireHumanProjectContext(
  ctx: TenantContext,
  projectId: string
): Promise<{ id: bigint }> {
  requireHumanContext(ctx);

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);

  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!project) {
    throw APIError.permissionDenied(
      "PROJECT_ACCESS_DENIED: project does not belong to this workspace"
    );
  }

  return project;
}

function toSnapshot(dossierId: bigint, revisionRow: {
  version: number;
  status: string;
  issueCategory: string;
  legalRecordRefs: unknown;
  applicabilityStatus: string;
  jurisdiction: string | null;
  redactedQuestion: string;
}): LegalIssueSnapshot {
  return {
    dossierId: dossierId.toString(),
    revision: revisionRow.version,
    issueCategory: revisionRow.issueCategory as LegalIssueCategory,
    legalRecordRefs: (revisionRow.legalRecordRefs as LegalRecordRef[]) ?? [],
    applicabilityStatus: revisionRow.applicabilityStatus as LegalApplicabilityStatus,
    jurisdiction: revisionRow.jurisdiction ?? undefined,
    redactedQuestion: revisionRow.redactedQuestion,
    status: revisionRow.status as LegalIssueDossierStatus,
  };
}

/**
 * Founder/member tạo Legal Issue Dossier mới cho Project (revision 1, status
 * DRAFT). Model/agent context không bao giờ tới được nhánh này. Input được
 * validate qua allowlist nghiêm ngặt + deep scan contract-body/PII/privileged
 * — bất kỳ field lạ hay chuỗi trông giống các shape đó đều bị reject bằng
 * `invalid_argument`, không âm thầm loại bỏ. `legalRecordRefs` phải resolve
 * được qua Finance-Legal read service — KHÔNG BAO GIỜ query trực tiếp schema
 * `legal.*`.
 */
export async function createLegalIssueDossier(
  ctx: TenantContext,
  input: CreateLegalIssueDossierInput
): Promise<LegalIssueSnapshot> {
  const validated = validateCreateInput(input);

  await requireHumanProjectContext(ctx, validated.projectId);
  await assertLegalRecordRefsResolve(validated.legalRecordRefs ?? [], ctx);

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(validated.projectId);
  const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  try {
    return await db.transaction(async (tx) => {
      const dossierId = generateSnowflake();

      // `uix_legal_issue_dossiers_project` (migration 016) bắt buộc duy nhất
      // 1 dossier/project — race giữa 2 request tạo đồng thời cho cùng
      // project bị chặn ở tầng DB (catch bên dưới).
      await tx.insert(legalIssueDossiers).values({
        id: dossierId,
        workspaceId: wsId,
        projectId: projId,
        status: "DRAFT",
        currentVersion: 1,
        createdByMemberId: actorMemberId,
      });

      const [revision] = await tx
        .insert(legalIssueDossierRevisions)
        .values({
          id: generateSnowflake(),
          workspaceId: wsId,
          projectId: projId,
          dossierId,
          version: 1,
          status: "DRAFT",
          issueCategory: validated.issueCategory,
          legalRecordRefs: validated.legalRecordRefs,
          applicabilityStatus: validated.applicabilityStatus,
          jurisdiction: validated.jurisdiction ?? null,
          redactedQuestion: validated.redactedQuestion,
          reasonCode: validated.reasonCode,
          actorMemberId,
        })
        .returning();

      if (!revision) throw APIError.internal("failed to create legal issue dossier");

      return toSnapshot(dossierId, revision);
    });
  } catch (err: any) {
    if (err?.cause?.code === "23505" || err?.code === "23505") {
      throw APIError.alreadyExists("a legal issue dossier already exists for this project");
    }
    throw err;
  }
}

/**
 * Founder/member append một revision mới (CAS theo expectedVersion). Đặt
 * status "CONFIRMED" chỉ hợp lệ khi ctx là human founder/co-founder. Model/
 * agent context luôn bị chặn ở `requireHumanContext` trước khi chạm DB.
 */
export async function appendLegalIssueRevision(
  ctx: TenantContext,
  dossierId: string,
  expectedVersion: number,
  input: AppendLegalIssueRevisionInput
): Promise<LegalIssueSnapshot> {
  requireHumanContext(ctx);

  const validated = validateAppendInput(input);

  await assertLegalRecordRefsResolve(validated.legalRecordRefs ?? [], ctx);

  const wsId = BigInt(ctx.workspaceId);
  const dossierBigId = BigInt(dossierId);

  const [dossier] = await db
    .select()
    .from(legalIssueDossiers)
    .where(and(eq(legalIssueDossiers.id, dossierBigId), eq(legalIssueDossiers.workspaceId, wsId)))
    .limit(1);
  if (!dossier) throw APIError.notFound("legal issue dossier not found in workspace");

  if (dossier.currentVersion !== expectedVersion) {
    throw APIError.aborted(
      `CAS_CONFLICT: stale dossier version (expected ${expectedVersion}, got ${dossier.currentVersion})`
    );
  }

  const nextStatus = validated.status ?? (dossier.status as LegalIssueDossierStatus) ?? "DRAFT";
  if (nextStatus === "CONFIRMED") {
    const role = (ctx.membershipRole || "").toLowerCase();
    if (!["founder", "co-founder"].includes(role)) {
      throw APIError.permissionDenied(
        "FOUNDER_CONFIRMATION_REQUIRED: Only a human founder can confirm a legal issue dossier revision"
      );
    }
  }

  const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;
  const nextVersion = dossier.currentVersion + 1;

  return db.transaction(async (tx) => {
    const [prior] = await tx
      .select({ id: legalIssueDossierRevisions.id })
      .from(legalIssueDossierRevisions)
      .where(eq(legalIssueDossierRevisions.dossierId, dossierBigId))
      .orderBy(desc(legalIssueDossierRevisions.version))
      .limit(1);

    const [revision] = await tx
      .insert(legalIssueDossierRevisions)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: dossier.projectId,
        dossierId: dossierBigId,
        version: nextVersion,
        status: nextStatus,
        issueCategory: validated.issueCategory,
        legalRecordRefs: validated.legalRecordRefs,
        applicabilityStatus: validated.applicabilityStatus,
        jurisdiction: validated.jurisdiction ?? null,
        redactedQuestion: validated.redactedQuestion,
        reasonCode: validated.reasonCode,
        actorMemberId,
        confirmedByMemberId: nextStatus === "CONFIRMED" ? actorMemberId : null,
        confirmedAt: nextStatus === "CONFIRMED" ? new Date() : null,
        supersedesRevisionId: prior?.id ?? null,
      })
      .returning();
    if (!revision) throw APIError.internal("failed to append legal issue dossier revision");

    const [updatedDossier] = await tx
      .update(legalIssueDossiers)
      .set({
        currentVersion: nextVersion,
        status: nextStatus,
        updatedAt: new Date(),
      })
      .where(
        and(
          eq(legalIssueDossiers.id, dossierBigId),
          eq(legalIssueDossiers.currentVersion, expectedVersion)
        )
      )
      .returning();
    if (!updatedDossier) {
      throw APIError.aborted("CAS_CONFLICT: dossier changed concurrently");
    }

    return toSnapshot(dossierBigId, revision);
  });
}

/**
 * Đọc snapshot mới nhất (chỉ classified metadata — issueCategory,
 * legalRecordRefs, applicabilityStatus, jurisdiction, redactedQuestion —
 * KHÔNG BAO GIỜ toàn văn hợp đồng/PII/privileged advice) của Legal Issue
 * Dossier theo Project. Model/agent context ĐƯỢC PHÉP đọc (chỉ không được
 * ghi). Project ở workspace khác hoặc project khác trong CÙNG workspace đều
 * bị từ chối — không lộ thông tin tồn tại/không tồn tại của project chéo
 * tenant hay chéo project.
 */
export async function readLegalIssueSnapshot(
  ctx: TenantContext,
  projectId: string
): Promise<LegalIssueSnapshot> {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);

  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);
  if (!project) {
    throw APIError.permissionDenied(
      "PROJECT_ACCESS_DENIED: project does not belong to this workspace"
    );
  }

  const [dossier] = await db
    .select()
    .from(legalIssueDossiers)
    .where(and(eq(legalIssueDossiers.workspaceId, wsId), eq(legalIssueDossiers.projectId, projId)))
    .orderBy(desc(legalIssueDossiers.updatedAt))
    .limit(1);
  if (!dossier) {
    throw APIError.notFound("no legal issue dossier found for this project");
  }

  const [revision] = await db
    .select()
    .from(legalIssueDossierRevisions)
    .where(eq(legalIssueDossierRevisions.dossierId, dossier.id))
    .orderBy(desc(legalIssueDossierRevisions.version))
    .limit(1);
  if (!revision) {
    throw APIError.internal("legal issue dossier has no revisions");
  }

  return toSnapshot(dossier.id, revision);
}
