import { APIError } from "encore.dev/api";
import { and, desc, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";

const { projects, dataGovernanceDossiers, dataGovernanceDossierRevisions } = schema;

export type DataGovernanceDossierStatus = "DRAFT" | "CONFIRMED" | "SUPERSEDED";

/**
 * Allowlist cố định phân loại data classification — bắt buộc bao gồm
 * `MISSING` (task-1-brief §Global Constraints: "Missing provenance/
 * classification must be returned as missing, not inferred by LLM") — KHÔNG
 * BAO GIỜ null/undefined khi chưa xác định được, dùng MISSING thay vì suy
 * diễn.
 */
export type DataClassification = "PUBLIC" | "INTERNAL" | "CONFIDENTIAL" | "RESTRICTED" | "MISSING";

const DATA_CLASSIFICATIONS: ReadonlySet<string> = new Set<DataClassification>([
  "PUBLIC",
  "INTERNAL",
  "CONFIDENTIAL",
  "RESTRICTED",
  "MISSING",
]);

/**
 * Allowlist cố định trạng thái chất lượng dữ liệu — bắt buộc bao gồm
 * `UNKNOWN` cho cùng lý do trên (missing quality status là một unknown tường
 * minh, không phải suy diễn ngầm).
 */
export type DataQualityStatus = "VALIDATED" | "FLAGGED" | "UNKNOWN";

const DATA_QUALITY_STATUSES: ReadonlySet<string> = new Set<DataQualityStatus>([
  "VALIDATED",
  "FLAGGED",
  "UNKNOWN",
]);

export type DataGovernanceReasonCode =
  | "ASSET_CATALOGED"
  | "CLASSIFICATION_UPDATED"
  | "QUALITY_UPDATED"
  | "SOURCE_REF_UPDATED"
  | "FOUNDER_REVIEW";

const DATA_GOVERNANCE_REASON_CODES: ReadonlySet<string> = new Set<DataGovernanceReasonCode>([
  "ASSET_CATALOGED",
  "CLASSIFICATION_UPDATED",
  "QUALITY_UPDATED",
  "SOURCE_REF_UPDATED",
  "FOUNDER_REVIEW",
]);

/**
 * Một entry catalog của data asset — CHỈ metadata VỀ dữ liệu (opaque
 * reference + nhãn phân loại), KHÔNG BAO GIỜ chứa giá trị/field sample thật,
 * embedding vector, raw file URI hay API credential (task-1-brief §Global
 * Constraints: "Metadata is not a backdoor to data"). Deep-scan ở
 * `deepAssertSafeShape` chặn các shape đó ở BẤT KỲ field nào, kể cả field đã
 * nằm trong allowlist key.
 */
export interface DataAsset {
  assetId: string;
  classification: DataClassification;
  qualityStatus: DataQualityStatus;
}

/**
 * Tham chiếu nguồn đã redact — reference-only shape, mirror `EvidenceRef`
 * dùng chung bởi các dossier khác (product-decision/security-posture/
 * legal-issue). KHÔNG BAO GIỜ raw file URI/path hay credential — deep-scan
 * chặn ở value level bên dưới.
 */
export interface DataSourceRef {
  sourceRef: string;
  classification?: string;
  redactedExcerpt?: string;
}

export interface DataGovernanceSnapshot {
  dossierId: string;
  revision: number;
  assets: DataAsset[];
  sourceRefs: DataSourceRef[];
  status: DataGovernanceDossierStatus;
}

export interface CreateDataGovernanceDossierInput {
  projectId: string;
  assets?: DataAsset[];
  sourceRefs?: DataSourceRef[];
  reasonCode: DataGovernanceReasonCode;
}

/**
 * Append LUÔN yêu cầu lại toàn bộ `assets`/`sourceRefs` (không ngầm giữ
 * nguyên giá trị revision trước) — mirror full-replace semantics đã thiết
 * lập ở các dossier khác (Security Posture/People Risk/Legal Issue Dossier):
 * mỗi revision là một bản ghi TƯỜNG MINH, tự chứa toàn bộ nội dung tại thời
 * điểm đó — không có state ẩn nào carry-over từ revision cũ.
 */
export interface AppendDataGovernanceRevisionInput {
  assets?: DataAsset[];
  sourceRefs?: DataSourceRef[];
  status?: "DRAFT" | "CONFIRMED";
  reasonCode: DataGovernanceReasonCode;
}

// ---------------------------------------------------------------------------
// Validation — allowlist nghiêm ngặt + deep-scan chặn field-sample/raw-value,
// embedding-vector-shaped array, raw file URI, và credential-shaped string ở
// BẤT KỲ field nào (kể cả field đã nằm trong allowlist key). Đây là headline
// "metadata is not a backdoor to data" property của dossier này (task-1-brief
// §Global Constraints) — reject chủ động bằng `invalid_argument`, không chỉ
// "không có chỗ để lưu".
// ---------------------------------------------------------------------------

const ALLOWED_CREATE_KEYS = new Set(["projectId", "assets", "sourceRefs", "reasonCode"]);
const ALLOWED_APPEND_KEYS = new Set(["assets", "sourceRefs", "status", "reasonCode"]);
const ALLOWED_ASSET_KEYS = new Set(["assetId", "classification", "qualityStatus"]);
const ALLOWED_SOURCE_REF_KEYS = new Set(["sourceRef", "classification", "redactedExcerpt"]);

// Credential-shaped patterns — reuse cùng regex set với
// security-posture.service.ts's SECRET_PATTERNS để nhất quán trên toàn bộ
// portfolio dossier (progress.md lesson #9).
const CREDENTIAL_PATTERNS: ReadonlyArray<{ name: string; re: RegExp }> = [
  { name: "api_key_or_token", re: /\b(sk-[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{12,})\b/ },
  { name: "jwt_like_token", re: /\bey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/ },
  { name: "bearer_token", re: /\bBearer\s+[A-Za-z0-9\-_.]{20,}/i },
  { name: "pem_private_key", re: /-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----/ },
];

// Raw file URI/path patterns — "a raw file URI is exactly what must never
// appear" (task-1-brief). Bao gồm cả URL pattern chung vì đây cũng là một
// dạng "raw location reference" thay vì opaque metadata.
const RAW_FILE_URI_PATTERNS: ReadonlyArray<{ name: string; re: RegExp }> = [
  { name: "file_uri", re: /\bfile:\/\//i },
  { name: "s3_uri", re: /\bs3:\/\//i },
  { name: "gcs_uri", re: /\bgs:\/\//i },
  { name: "unix_absolute_path", re: /(^|\s)\/(Users|home)\//i },
  { name: "windows_absolute_path", re: /\b[A-Za-z]:\\/ },
  { name: "generic_url", re: /\bhttps?:\/\/\S+/i },
];

// "Trông giống một hàng dữ liệu" (data row/field sample) chứ không phải nhãn
// phân loại — heuristic thực dụng: >=3 field phân tách bằng dấu phẩy, hoặc
// tab-separated. Không cố phát hiện MỌI field sample, chỉ marker phổ biến,
// có thể test (task-1-brief: "at minimum enforce a length cap ... and reject
// anything that looks like a delimited data row").
const DELIMITED_ROW_PATTERN = /([^,\n]+,){2,}[^,\n]+/;
const TAB_DELIMITED_PATTERN = /\S+\t+\S+/;

// Một nhãn/tham chiếu metadata không có lý do gì cần dài hơn ngưỡng này — một
// chuỗi dài hơn được coi là "trông giống" một field sample/tài liệu dán nhầm
// vào, kể cả khi không khớp marker cụ thể nào.
const MAX_FREE_TEXT_LENGTH = 300;

function assertNoDataValueShape(value: string, path: string): void {
  for (const { name, re } of RAW_FILE_URI_PATTERNS) {
    if (re.test(value)) {
      throw APIError.invalidArgument(
        `DATA_DOSSIER_RAW_URI_REJECTED: "${path}" looks like a ${name} — raw file URIs/paths are never allowed in this dossier, only opaque asset references`
      );
    }
  }
  for (const { name, re } of CREDENTIAL_PATTERNS) {
    if (re.test(value)) {
      throw APIError.invalidArgument(
        `DATA_DOSSIER_CREDENTIAL_REJECTED: "${path}" looks like a ${name} — API credentials are never allowed in this dossier`
      );
    }
  }
  if (DELIMITED_ROW_PATTERN.test(value) || TAB_DELIMITED_PATTERN.test(value)) {
    throw APIError.invalidArgument(
      `DATA_DOSSIER_FIELD_SAMPLE_REJECTED: "${path}" looks like a delimited data row/field sample rather than a classification label — actual data values are never allowed in this dossier`
    );
  }
  if (value.length > MAX_FREE_TEXT_LENGTH) {
    throw APIError.invalidArgument(
      `DATA_DOSSIER_FIELD_SAMPLE_REJECTED: "${path}" exceeds ${MAX_FREE_TEXT_LENGTH} characters — a metadata label/reference should never be this long, this looks like pasted data`
    );
  }
}

/**
 * Một array mà TẤT CẢ phần tử là number bị coi là embedding-vector-shaped —
 * dossier này không có khái niệm "danh sách số" hợp lệ nào khác, nên chặn
 * chủ động thay vì cố phân biệt "vector thật" với "mảng số vô hại"
 * (task-1-brief: "reject any JSON array where all elements are numbers").
 */
function isEmbeddingVectorShaped(arr: unknown[]): boolean {
  return arr.length > 0 && arr.every((v) => typeof v === "number");
}

/**
 * Quét đệ quy TOÀN BỘ input tìm field-sample/raw-value/embedding-vector/raw-
 * file-URI/credential-shaped data — kể cả field đã nằm trong allowlist key
 * (mirror `deepAssertNoSecret`/`deepAssertSafeShape` của Security Posture/
 * Legal Issue Dossier).
 */
function deepAssertSafeShape(value: unknown, path: string): void {
  if (typeof value === "string") {
    assertNoDataValueShape(value, path);
  } else if (Array.isArray(value)) {
    if (isEmbeddingVectorShaped(value)) {
      throw APIError.invalidArgument(
        `DATA_DOSSIER_EMBEDDING_REJECTED: "${path}" looks like an embedding vector (an array of numbers) — embeddings are never allowed in this dossier`
      );
    }
    value.forEach((v, i) => deepAssertSafeShape(v, `${path}[${i}]`));
  } else if (value && typeof value === "object") {
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      deepAssertSafeShape(v, `${path}.${k}`);
    }
  }
}

function assertPlainObject(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw APIError.invalidArgument(`DATA_DOSSIER_SHAPE_INVALID: "${path}" must be an object`);
  }
  return value as Record<string, unknown>;
}

function assertOnlyAllowedKeys(obj: Record<string, unknown>, allowed: ReadonlySet<string>, path: string): void {
  for (const key of Object.keys(obj)) {
    if (!allowed.has(key)) {
      throw APIError.invalidArgument(
        `DATA_DOSSIER_FIELD_REJECTED: "${key}" is not an allowed field on ${path} — this dossier only accepts classified asset catalog metadata and source references`
      );
    }
  }
}

function assertValidReasonCode(value: unknown, path: string): DataGovernanceReasonCode {
  if (typeof value !== "string" || !DATA_GOVERNANCE_REASON_CODES.has(value)) {
    throw APIError.invalidArgument(
      `DATA_DOSSIER_SHAPE_INVALID: "${path}" must be one of the fixed allowed reason codes — free text is not accepted`
    );
  }
  return value as DataGovernanceReasonCode;
}

/**
 * Trả về MISSING theo mặc định — không bao giờ null/undefined (task-1-brief
 * §Global Constraints: "Missing provenance/classification must be returned
 * as missing, not inferred by LLM").
 */
function normalizeClassification(raw: unknown, path: string): DataClassification {
  if (raw === undefined) return "MISSING";
  if (typeof raw !== "string" || !DATA_CLASSIFICATIONS.has(raw)) {
    throw APIError.invalidArgument(
      `DATA_DOSSIER_SHAPE_INVALID: "${path}" must be one of PUBLIC|INTERNAL|CONFIDENTIAL|RESTRICTED|MISSING`
    );
  }
  return raw as DataClassification;
}

/**
 * Trả về UNKNOWN theo mặc định — cùng lý do trên, áp dụng cho quality status.
 */
function normalizeQualityStatus(raw: unknown, path: string): DataQualityStatus {
  if (raw === undefined) return "UNKNOWN";
  if (typeof raw !== "string" || !DATA_QUALITY_STATUSES.has(raw)) {
    throw APIError.invalidArgument(
      `DATA_DOSSIER_SHAPE_INVALID: "${path}" must be one of VALIDATED|FLAGGED|UNKNOWN`
    );
  }
  return raw as DataQualityStatus;
}

function normalizeAssets(raw: unknown): DataAsset[] {
  if (raw === undefined) return [];
  if (!Array.isArray(raw)) {
    throw APIError.invalidArgument("DATA_DOSSIER_SHAPE_INVALID: assets must be an array");
  }
  return raw.map((item, i) => {
    const obj = assertPlainObject(item, `assets[${i}]`);
    assertOnlyAllowedKeys(obj, ALLOWED_ASSET_KEYS, `assets[${i}]`);
    if (typeof obj.assetId !== "string" || !obj.assetId.trim()) {
      throw APIError.invalidArgument(`DATA_DOSSIER_SHAPE_INVALID: assets[${i}].assetId is required`);
    }
    return {
      assetId: obj.assetId,
      classification: normalizeClassification(obj.classification, `assets[${i}].classification`),
      qualityStatus: normalizeQualityStatus(obj.qualityStatus, `assets[${i}].qualityStatus`),
    };
  });
}

function normalizeSourceRefs(raw: unknown): DataSourceRef[] {
  if (raw === undefined) return [];
  if (!Array.isArray(raw)) {
    throw APIError.invalidArgument("DATA_DOSSIER_SHAPE_INVALID: sourceRefs must be an array");
  }
  return raw.map((item, i) => {
    const obj = assertPlainObject(item, `sourceRefs[${i}]`);
    assertOnlyAllowedKeys(obj, ALLOWED_SOURCE_REF_KEYS, `sourceRefs[${i}]`);
    if (typeof obj.sourceRef !== "string" || !obj.sourceRef.trim()) {
      throw APIError.invalidArgument(`DATA_DOSSIER_SHAPE_INVALID: sourceRefs[${i}].sourceRef is required`);
    }
    if (obj.classification !== undefined && typeof obj.classification !== "string") {
      throw APIError.invalidArgument(
        `DATA_DOSSIER_SHAPE_INVALID: sourceRefs[${i}].classification must be a string`
      );
    }
    if (obj.redactedExcerpt !== undefined && typeof obj.redactedExcerpt !== "string") {
      throw APIError.invalidArgument(
        `DATA_DOSSIER_SHAPE_INVALID: sourceRefs[${i}].redactedExcerpt must be a string`
      );
    }
    return {
      sourceRef: obj.sourceRef,
      classification: obj.classification as string | undefined,
      redactedExcerpt: obj.redactedExcerpt as string | undefined,
    };
  });
}

function validateCreateInput(input: unknown): CreateDataGovernanceDossierInput {
  const obj = assertPlainObject(input, "input");
  deepAssertSafeShape(obj, "input");
  assertOnlyAllowedKeys(obj, ALLOWED_CREATE_KEYS, "input");
  if (typeof obj.projectId !== "string" || !obj.projectId.trim()) {
    throw APIError.invalidArgument("projectId is required");
  }
  return {
    projectId: obj.projectId,
    assets: normalizeAssets(obj.assets),
    sourceRefs: normalizeSourceRefs(obj.sourceRefs),
    reasonCode: assertValidReasonCode(obj.reasonCode, "reasonCode"),
  };
}

function validateAppendInput(input: unknown): AppendDataGovernanceRevisionInput {
  const obj = assertPlainObject(input, "input");
  deepAssertSafeShape(obj, "input");
  assertOnlyAllowedKeys(obj, ALLOWED_APPEND_KEYS, "input");
  if (obj.status !== undefined && obj.status !== "DRAFT" && obj.status !== "CONFIRMED") {
    throw APIError.invalidArgument("DATA_DOSSIER_SHAPE_INVALID: status must be DRAFT or CONFIRMED");
  }
  return {
    assets: normalizeAssets(obj.assets),
    sourceRefs: normalizeSourceRefs(obj.sourceRefs),
    status: obj.status as "DRAFT" | "CONFIRMED" | undefined,
    reasonCode: assertValidReasonCode(obj.reasonCode, "reasonCode"),
  };
}

/**
 * Guard bắt buộc: chỉ human context (không phải AI agent) mới được tạo/append
 * Data Governance Dossier — CDO chỉ được đề xuất gap/remediation draft qua
 * kênh riêng (skillpack, không phải ghi trực tiếp), KHÔNG BAO GIỜ tự mutate
 * ACL hay xoá bản ghi (CLAUDE.md quy tắc 1, 5, 8; task-1-brief §Global
 * Constraints: "CDO proposes a gap/remediation draft, never mutates ACL or
 * deletes records"). Project phải thuộc đúng Workspace của ctx — chống truy
 * cập chéo project/workspace.
 *
 * Ghi chú (mirror legal-issue-dossier.service.ts): qua các endpoint public
 * hiện có, `ctx.isAiAgent` không bao giờ true trong thực tế — transport-level
 * auth (`requireWorkspaceAccess` → `resolveTenantContext`) đã tự reject bất
 * kỳ token nào ký bởi `COSA_COMPANY_DELEGATION_SECRET` bằng
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
      "DATA_DOSSIER_HUMAN_REQUIRED: Only a human Founder/member context can create or append a data governance dossier"
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
  assets: unknown;
  sourceRefs: unknown;
}): DataGovernanceSnapshot {
  return {
    dossierId: dossierId.toString(),
    revision: revisionRow.version,
    assets: (revisionRow.assets as DataAsset[]) ?? [],
    sourceRefs: (revisionRow.sourceRefs as DataSourceRef[]) ?? [],
    status: revisionRow.status as DataGovernanceDossierStatus,
  };
}

/**
 * Founder/member tạo Data Governance Dossier mới cho Project (revision 1,
 * status DRAFT). Model/agent context không bao giờ tới được nhánh này. Input
 * được validate qua allowlist nghiêm ngặt + deep scan field-sample/embedding/
 * raw-file-URI/credential — bất kỳ field lạ hay chuỗi trông giống các shape
 * đó đều bị reject bằng `invalid_argument`, không âm thầm loại bỏ.
 */
export async function createDataGovernanceDossier(
  ctx: TenantContext,
  input: CreateDataGovernanceDossierInput
): Promise<DataGovernanceSnapshot> {
  const validated = validateCreateInput(input);

  await requireHumanProjectContext(ctx, validated.projectId);

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(validated.projectId);
  const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  try {
    return await db.transaction(async (tx) => {
      const dossierId = generateSnowflake();

      // `uix_data_governance_dossiers_project` (migration 019) bắt buộc duy
      // nhất 1 dossier/project — race giữa 2 request tạo đồng thời cho cùng
      // project bị chặn ở tầng DB (catch bên dưới).
      await tx.insert(dataGovernanceDossiers).values({
        id: dossierId,
        workspaceId: wsId,
        projectId: projId,
        status: "DRAFT",
        currentVersion: 1,
        createdByMemberId: actorMemberId,
      });

      const [revision] = await tx
        .insert(dataGovernanceDossierRevisions)
        .values({
          id: generateSnowflake(),
          workspaceId: wsId,
          projectId: projId,
          dossierId,
          version: 1,
          status: "DRAFT",
          assets: validated.assets,
          sourceRefs: validated.sourceRefs,
          reasonCode: validated.reasonCode,
          actorMemberId,
        })
        .returning();

      if (!revision) throw APIError.internal("failed to create data governance dossier");

      return toSnapshot(dossierId, revision);
    });
  } catch (err: any) {
    if (err?.cause?.code === "23505" || err?.code === "23505") {
      throw APIError.alreadyExists("a data governance dossier already exists for this project");
    }
    throw err;
  }
}

/**
 * Founder/member append một revision mới (CAS theo expectedVersion). Đặt
 * status "CONFIRMED" chỉ hợp lệ khi ctx là human founder/co-founder. Model/
 * agent context luôn bị chặn ở `requireHumanContext` trước khi chạm DB.
 */
export async function appendDataGovernanceRevision(
  ctx: TenantContext,
  dossierId: string,
  expectedVersion: number,
  input: AppendDataGovernanceRevisionInput
): Promise<DataGovernanceSnapshot> {
  requireHumanContext(ctx);

  const validated = validateAppendInput(input);

  const wsId = BigInt(ctx.workspaceId);
  const dossierBigId = BigInt(dossierId);

  const [dossier] = await db
    .select()
    .from(dataGovernanceDossiers)
    .where(and(eq(dataGovernanceDossiers.id, dossierBigId), eq(dataGovernanceDossiers.workspaceId, wsId)))
    .limit(1);
  if (!dossier) throw APIError.notFound("data governance dossier not found in workspace");

  if (dossier.currentVersion !== expectedVersion) {
    throw APIError.aborted(
      `CAS_CONFLICT: stale dossier version (expected ${expectedVersion}, got ${dossier.currentVersion})`
    );
  }

  const nextStatus = validated.status ?? (dossier.status as DataGovernanceDossierStatus) ?? "DRAFT";
  if (nextStatus === "CONFIRMED") {
    const role = (ctx.membershipRole || "").toLowerCase();
    if (!["founder", "co-founder"].includes(role)) {
      throw APIError.permissionDenied(
        "FOUNDER_CONFIRMATION_REQUIRED: Only a human founder can confirm a data governance dossier revision"
      );
    }
  }

  const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;
  const nextVersion = dossier.currentVersion + 1;

  return db.transaction(async (tx) => {
    const [prior] = await tx
      .select({ id: dataGovernanceDossierRevisions.id })
      .from(dataGovernanceDossierRevisions)
      .where(eq(dataGovernanceDossierRevisions.dossierId, dossierBigId))
      .orderBy(desc(dataGovernanceDossierRevisions.version))
      .limit(1);

    const [revision] = await tx
      .insert(dataGovernanceDossierRevisions)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: dossier.projectId,
        dossierId: dossierBigId,
        version: nextVersion,
        status: nextStatus,
        assets: validated.assets,
        sourceRefs: validated.sourceRefs,
        reasonCode: validated.reasonCode,
        actorMemberId,
        confirmedByMemberId: nextStatus === "CONFIRMED" ? actorMemberId : null,
        confirmedAt: nextStatus === "CONFIRMED" ? new Date() : null,
        supersedesRevisionId: prior?.id ?? null,
      })
      .returning();
    if (!revision) throw APIError.internal("failed to append data governance dossier revision");

    const [updatedDossier] = await tx
      .update(dataGovernanceDossiers)
      .set({
        currentVersion: nextVersion,
        status: nextStatus,
        updatedAt: new Date(),
      })
      .where(
        and(
          eq(dataGovernanceDossiers.id, dossierBigId),
          eq(dataGovernanceDossiers.currentVersion, expectedVersion)
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
 * Đọc snapshot mới nhất (chỉ classified metadata — assets, sourceRefs — KHÔNG
 * BAO GIỜ giá trị/field sample thật, embedding, raw file URI hay credential)
 * của Data Governance Dossier theo Project. Model/agent context ĐƯỢC PHÉP đọc
 * (chỉ không được ghi). Project ở workspace khác hoặc project khác trong
 * CÙNG workspace đều bị từ chối — không lộ thông tin tồn tại/không tồn tại
 * của project chéo tenant hay chéo project (task-1-brief: "deny ... cross-
 * Project lineage").
 */
export async function readDataGovernanceSnapshot(
  ctx: TenantContext,
  projectId: string
): Promise<DataGovernanceSnapshot> {
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
    .from(dataGovernanceDossiers)
    .where(and(eq(dataGovernanceDossiers.workspaceId, wsId), eq(dataGovernanceDossiers.projectId, projId)))
    .orderBy(desc(dataGovernanceDossiers.updatedAt))
    .limit(1);
  if (!dossier) {
    throw APIError.notFound("no data governance dossier found for this project");
  }

  const [revision] = await db
    .select()
    .from(dataGovernanceDossierRevisions)
    .where(eq(dataGovernanceDossierRevisions.dossierId, dossier.id))
    .orderBy(desc(dataGovernanceDossierRevisions.version))
    .limit(1);
  if (!revision) {
    throw APIError.internal("data governance dossier has no revisions");
  }

  return toSnapshot(dossier.id, revision);
}
