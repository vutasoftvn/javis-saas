import { APIError } from "encore.dev/api";
import { and, desc, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import { EvidenceRef } from "./product-decision-dossier.service";

const { projects, peopleRiskDossiers, peopleRiskDossierRevisions } = schema;

export type PeopleRiskDossierStatus = "DRAFT" | "CONFIRMED" | "SUPERSEDED";

export type RiskSeverity = "LOW" | "MEDIUM" | "HIGH";

/**
 * Allowlist cố định các category risk signal — không phải danh sách gợi ý,
 * mà là toàn bộ tập hợp giá trị hợp lệ. Không thêm category mới bằng cách
 * gõ chuỗi tự do ở call site (chống rò rỉ PII qua trường category tự do).
 */
export type RiskSignalCategory =
  | "single_point_of_failure"
  | "attrition_risk"
  | "hiring_gap"
  | "skill_gap"
  | "succession_risk"
  | "overload_risk";

const RISK_SIGNAL_CATEGORIES: ReadonlySet<string> = new Set<RiskSignalCategory>([
  "single_point_of_failure",
  "attrition_risk",
  "hiring_gap",
  "skill_gap",
  "succession_risk",
  "overload_risk",
]);

const RISK_SEVERITIES: ReadonlySet<string> = new Set<RiskSeverity>(["LOW", "MEDIUM", "HIGH"]);

/**
 * Allowlist cố định cho `reasonCode` — KHÔNG free text. Review Task 1 finding
 * Critical: một trường narrative/reasonCode tự do sẽ đánh bại chính headline
 * privacy property của dossier này, vì quét compensation/protected-
 * characteristic/performance-note/health-data bằng regex không đáng tin cậy
 * (khác với email/phone, các category này không có "shape" cố định để quét).
 * Mọi lý do ghi nhận phải rơi vào 1 trong các mã cố định dưới đây.
 */
export type PeopleRiskReasonCode =
  | "INITIAL_ASSESSMENT"
  | "NEW_CAPACITY_DATA"
  | "RISK_REASSESSMENT"
  | "SOURCE_UPDATED"
  | "FOUNDER_REVIEW";

const PEOPLE_RISK_REASON_CODES: ReadonlySet<string> = new Set<PeopleRiskReasonCode>([
  "INITIAL_ASSESSMENT",
  "NEW_CAPACITY_DATA",
  "RISK_REASSESSMENT",
  "SOURCE_UPDATED",
  "FOUNDER_REVIEW",
]);

/**
 * Capacity band: đếm headcount theo role-category, KHÔNG BAO GIỜ chứa tên
 * người hay bất kỳ định danh cá nhân nào — chỉ số liệu tổng hợp.
 */
export interface CapacityBand {
  roleCategory: string;
  headcount: number;
}

/**
 * Risk signal: nhãn đã phân loại (category cố định + severity) tham chiếu
 * tới nguồn qua `sourceRef`/`classification` — mirror pattern reference-only
 * của `EvidenceRef` (product-decision-dossier.service.ts). KHÔNG có trường
 * text tự do nào khác (không note, không performance review, không excerpt)
 * vì risk signal có nguy cơ PII cao hơn evidence sản phẩm.
 */
export interface RiskSignal {
  category: RiskSignalCategory;
  severity: RiskSeverity;
  sourceRef: string;
  classification?: string;
}

export interface PeopleRiskSnapshot {
  dossierId: string;
  revision: number;
  capacityBands: CapacityBand[];
  riskSignals: RiskSignal[];
  sourceRefs: EvidenceRef[];
  status: PeopleRiskDossierStatus;
}

export interface CreatePeopleRiskDossierInput {
  projectId: string;
  capacityBands?: CapacityBand[];
  riskSignals?: RiskSignal[];
  sourceRefs?: EvidenceRef[];
  reasonCode: PeopleRiskReasonCode;
}

export interface AppendPeopleRiskRevisionInput {
  capacityBands?: CapacityBand[];
  riskSignals?: RiskSignal[];
  sourceRefs?: EvidenceRef[];
  status?: "DRAFT" | "CONFIRMED";
  reasonCode: PeopleRiskReasonCode;
}

// ---------------------------------------------------------------------------
// Validation — allowlist nghiêm ngặt, KHÔNG denylist theo tên trường PII.
// Bất kỳ key nào ngoài allowlist, hoặc bất kỳ string nào "trông giống" email
// hay số điện thoại (ở BẤT KỲ vị trí nào trong input, kể cả field hợp lệ),
// đều bị reject bằng APIError.invalidArgument. Đây là headline privacy
// property của dossier này (xem task-1-brief §Global Constraints) — test
// riêng cho từng nhánh reject, không chỉ tin tưởng TypeScript type (không
// sống sót qua JSON.parse).
// ---------------------------------------------------------------------------

const ALLOWED_CREATE_KEYS = new Set([
  "projectId",
  "capacityBands",
  "riskSignals",
  "sourceRefs",
  "reasonCode",
]);

const ALLOWED_APPEND_KEYS = new Set([
  "capacityBands",
  "riskSignals",
  "sourceRefs",
  "status",
  "reasonCode",
]);

const ALLOWED_CAPACITY_BAND_KEYS = new Set(["roleCategory", "headcount"]);
const ALLOWED_RISK_SIGNAL_KEYS = new Set(["category", "severity", "sourceRef", "classification"]);
const ALLOWED_SOURCE_REF_KEYS = new Set(["sourceRef", "classification", "redactedExcerpt"]);

// eslint-disable-next-line no-useless-escape
const EMAIL_PATTERN = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i;
// Chỉ khớp chuỗi "trông giống" số điện thoại có định dạng phân tách (dấu +,
// dấu gạch ngang, chấm, khoảng trắng, ngoặc đơn) — KHÔNG khớp chuỗi số thuần
// dài (vd. Snowflake ID 18-19 chữ số của projectId/dossierId), tránh false
// positive trên chính các định danh nội bộ hợp lệ của hệ thống.
const PHONE_PATTERN = /(\+\d[\d\-.\s()]{6,14}\d)|(\(\d{3}\)[\s.-]?\d{3}[\s.-]\d{4})|(\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b)/;

function assertNoPiiLikeString(value: unknown, path: string): void {
  if (typeof value !== "string") return;
  if (EMAIL_PATTERN.test(value)) {
    throw APIError.invalidArgument(
      `PEOPLE_DOSSIER_PII_REJECTED: "${path}" looks like an email address — contact PII is never allowed in this dossier`
    );
  }
  if (PHONE_PATTERN.test(value)) {
    throw APIError.invalidArgument(
      `PEOPLE_DOSSIER_PII_REJECTED: "${path}" looks like a phone number — contact PII is never allowed in this dossier`
    );
  }
}

/**
 * Quét đệ quy TOÀN BỘ input tìm chuỗi giống email/phone — kể cả những field
 * đã nằm trong allowlist key. Đây là lớp phòng thủ độc lập với check
 * allowlist-key: một field hợp lệ như `narrative` hay `sourceRef` vẫn có thể
 * bị nhét PII dạng text, nên phải quét giá trị chứ không chỉ tên khoá.
 */
function deepAssertNoPii(value: unknown, path: string): void {
  if (typeof value === "string") {
    assertNoPiiLikeString(value, path);
  } else if (Array.isArray(value)) {
    value.forEach((v, i) => deepAssertNoPii(v, `${path}[${i}]`));
  } else if (value && typeof value === "object") {
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      deepAssertNoPii(v, `${path}.${k}`);
    }
  }
}

function assertPlainObject(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw APIError.invalidArgument(`PEOPLE_DOSSIER_SHAPE_INVALID: "${path}" must be an object`);
  }
  return value as Record<string, unknown>;
}

/**
 * Allowlist thuần tuý theo tên field — bất kỳ key nào không có trong
 * `allowed` bị reject NGAY LẬP TỨC, kể cả khi giá trị của nó không giống PII
 * (ví dụ `candidateName: "abc"`). An toàn hơn denylist theo tên field PII đã
 * biết vì không cần đoán trước hết mọi biến thể tên field.
 */
function assertOnlyAllowedKeys(obj: Record<string, unknown>, allowed: ReadonlySet<string>, path: string): void {
  for (const key of Object.keys(obj)) {
    if (!allowed.has(key)) {
      throw APIError.invalidArgument(
        `PEOPLE_DOSSIER_FIELD_REJECTED: "${key}" is not an allowed field on ${path} — this dossier only accepts classified aggregate data`
      );
    }
  }
}

function normalizeCapacityBands(raw: unknown): CapacityBand[] {
  if (raw === undefined) return [];
  if (!Array.isArray(raw)) {
    throw APIError.invalidArgument("PEOPLE_DOSSIER_SHAPE_INVALID: capacityBands must be an array");
  }
  return raw.map((item, i) => {
    const obj = assertPlainObject(item, `capacityBands[${i}]`);
    assertOnlyAllowedKeys(obj, ALLOWED_CAPACITY_BAND_KEYS, `capacityBands[${i}]`);
    const { roleCategory, headcount } = obj;
    if (typeof roleCategory !== "string" || !roleCategory.trim()) {
      throw APIError.invalidArgument(
        `PEOPLE_DOSSIER_SHAPE_INVALID: capacityBands[${i}].roleCategory must be a non-empty string`
      );
    }
    if (!/^[a-zA-Z0-9 _-]{1,64}$/.test(roleCategory)) {
      throw APIError.invalidArgument(
        `PEOPLE_DOSSIER_SHAPE_INVALID: capacityBands[${i}].roleCategory has an invalid shape`
      );
    }
    if (typeof headcount !== "number" || !Number.isInteger(headcount) || headcount < 0) {
      throw APIError.invalidArgument(
        `PEOPLE_DOSSIER_SHAPE_INVALID: capacityBands[${i}].headcount must be a non-negative integer`
      );
    }
    return { roleCategory, headcount };
  });
}

function normalizeRiskSignals(raw: unknown): RiskSignal[] {
  if (raw === undefined) return [];
  if (!Array.isArray(raw)) {
    throw APIError.invalidArgument("PEOPLE_DOSSIER_SHAPE_INVALID: riskSignals must be an array");
  }
  return raw.map((item, i) => {
    const obj = assertPlainObject(item, `riskSignals[${i}]`);
    assertOnlyAllowedKeys(obj, ALLOWED_RISK_SIGNAL_KEYS, `riskSignals[${i}]`);
    const { category, severity, sourceRef, classification } = obj;
    if (typeof category !== "string" || !RISK_SIGNAL_CATEGORIES.has(category)) {
      throw APIError.invalidArgument(
        `PEOPLE_DOSSIER_SHAPE_INVALID: riskSignals[${i}].category must be one of the fixed allowed risk categories`
      );
    }
    if (typeof severity !== "string" || !RISK_SEVERITIES.has(severity)) {
      throw APIError.invalidArgument(
        `PEOPLE_DOSSIER_SHAPE_INVALID: riskSignals[${i}].severity must be LOW|MEDIUM|HIGH`
      );
    }
    if (typeof sourceRef !== "string" || !sourceRef.trim()) {
      throw APIError.invalidArgument(`PEOPLE_DOSSIER_SHAPE_INVALID: riskSignals[${i}].sourceRef is required`);
    }
    if (classification !== undefined && typeof classification !== "string") {
      throw APIError.invalidArgument(
        `PEOPLE_DOSSIER_SHAPE_INVALID: riskSignals[${i}].classification must be a string`
      );
    }
    return {
      category: category as RiskSignalCategory,
      severity: severity as RiskSeverity,
      sourceRef,
      classification: classification as string | undefined,
    };
  });
}

function normalizeSourceRefs(raw: unknown): EvidenceRef[] {
  if (raw === undefined) return [];
  if (!Array.isArray(raw)) {
    throw APIError.invalidArgument("PEOPLE_DOSSIER_SHAPE_INVALID: sourceRefs must be an array");
  }
  return raw.map((item, i) => {
    const obj = assertPlainObject(item, `sourceRefs[${i}]`);
    assertOnlyAllowedKeys(obj, ALLOWED_SOURCE_REF_KEYS, `sourceRefs[${i}]`);
    if (typeof obj.sourceRef !== "string" || !obj.sourceRef.trim()) {
      throw APIError.invalidArgument(`PEOPLE_DOSSIER_SHAPE_INVALID: sourceRefs[${i}].sourceRef is required`);
    }
    if (typeof obj.classification !== "string" || !obj.classification.trim()) {
      throw APIError.invalidArgument(`PEOPLE_DOSSIER_SHAPE_INVALID: sourceRefs[${i}].classification is required`);
    }
    if (obj.redactedExcerpt !== undefined && typeof obj.redactedExcerpt !== "string") {
      throw APIError.invalidArgument(
        `PEOPLE_DOSSIER_SHAPE_INVALID: sourceRefs[${i}].redactedExcerpt must be a string`
      );
    }
    return {
      sourceRef: obj.sourceRef,
      classification: obj.classification,
      redactedExcerpt: obj.redactedExcerpt as string | undefined,
    };
  });
}

/**
 * Validate + normalize input tạo dossier. Nhận `unknown` (không tin type
 * TypeScript của caller — type không sống sót qua JSON body của HTTP
 * request) và trả về input đã "picked" chỉ những field allowlist, loại bỏ
 * hoàn toàn field lạ (vd. `candidateEmail`) dù giá trị của nó có giống PII
 * hay không.
 */
function assertValidReasonCode(value: unknown, path: string): PeopleRiskReasonCode {
  if (typeof value !== "string" || !PEOPLE_RISK_REASON_CODES.has(value)) {
    throw APIError.invalidArgument(
      `PEOPLE_DOSSIER_SHAPE_INVALID: "${path}" must be one of the fixed allowed reason codes — free text is not accepted`
    );
  }
  return value as PeopleRiskReasonCode;
}

function validateCreateInput(input: unknown): CreatePeopleRiskDossierInput {
  const obj = assertPlainObject(input, "input");
  deepAssertNoPii(obj, "input");
  assertOnlyAllowedKeys(obj, ALLOWED_CREATE_KEYS, "input");
  if (typeof obj.projectId !== "string" || !obj.projectId.trim()) {
    throw APIError.invalidArgument("projectId is required");
  }
  return {
    projectId: obj.projectId,
    capacityBands: normalizeCapacityBands(obj.capacityBands),
    riskSignals: normalizeRiskSignals(obj.riskSignals),
    sourceRefs: normalizeSourceRefs(obj.sourceRefs),
    reasonCode: assertValidReasonCode(obj.reasonCode, "reasonCode"),
  };
}

function validateAppendInput(input: unknown): AppendPeopleRiskRevisionInput {
  const obj = assertPlainObject(input, "input");
  deepAssertNoPii(obj, "input");
  assertOnlyAllowedKeys(obj, ALLOWED_APPEND_KEYS, "input");
  if (obj.status !== undefined && obj.status !== "DRAFT" && obj.status !== "CONFIRMED") {
    throw APIError.invalidArgument("PEOPLE_DOSSIER_SHAPE_INVALID: status must be DRAFT or CONFIRMED");
  }
  return {
    capacityBands: normalizeCapacityBands(obj.capacityBands),
    riskSignals: normalizeRiskSignals(obj.riskSignals),
    sourceRefs: normalizeSourceRefs(obj.sourceRefs),
    status: obj.status as "DRAFT" | "CONFIRMED" | undefined,
    reasonCode: assertValidReasonCode(obj.reasonCode, "reasonCode"),
  };
}

/**
 * Guard bắt buộc: chỉ human context (không phải AI agent) mới được tạo/append
 * People Risk Dossier — model/CHRO advisory có thể "draft" gợi ý nhưng KHÔNG
 * BAO GIỜ tự ghi bản ghi people risk chính thức (CLAUDE.md quy tắc 1 & 5,
 * task-1-brief: "A founder alone confirms a people policy/decision"). Project
 * phải thuộc đúng Workspace của ctx — chống truy cập chéo project/workspace.
 *
 * Ghi chú (mirror product-decision-dossier.service.ts): qua 3 endpoint public
 * hiện có, `ctx.isAiAgent` không bao giờ true trong thực tế — transport-level
 * auth (`requireWorkspaceAccess` → `resolveTenantContext`) đã tự reject bất
 * kỳ token nào ký bởi `COSA_COMPANY_DELEGATION_SECRET` (cách duy nhất
 * `apps/cosa` có thể tự xác thực sang service này) bằng
 * `APIError.unauthenticated` TRƯỚC KHI tới được service function này — xem
 * test "rejects a COSA-delegation-signed token before any TenantContext is
 * built". Check `ctx.isAiAgent` dưới đây vẫn giữ làm defense-in-depth cho một
 * endpoint nội bộ tương lai có thể tái dùng service function này với
 * `TenantContext` dựng từ cosa-delegation.
 *
 * Tách riêng phần check ctx/isAiAgent thành `requireHumanContext` để
 * `appendPeopleRiskRevision` (không cần lookup project) và
 * `requireHumanProjectContext` (cần cả lookup project) dùng chung, tránh 2
 * bản check lệch nhau theo thời gian (review Task 1 finding Important).
 */
function requireHumanContext(ctx: TenantContext): void {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }
  if (ctx.isAiAgent) {
    throw APIError.permissionDenied(
      "PEOPLE_DOSSIER_HUMAN_REQUIRED: Only a human Founder/member context can create or append a people risk dossier"
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
  capacityBands: unknown;
  riskSignals: unknown;
  sourceRefs: unknown;
}): PeopleRiskSnapshot {
  return {
    dossierId: dossierId.toString(),
    revision: revisionRow.version,
    capacityBands: (revisionRow.capacityBands as CapacityBand[]) ?? [],
    riskSignals: (revisionRow.riskSignals as RiskSignal[]) ?? [],
    sourceRefs: (revisionRow.sourceRefs as EvidenceRef[]) ?? [],
    status: revisionRow.status as PeopleRiskDossierStatus,
  };
}

/**
 * Founder/member tạo People Risk Dossier mới cho Project (revision 1, status
 * DRAFT). Model/agent context không bao giờ tới được nhánh này. Input được
 * validate qua allowlist nghiêm ngặt — bất kỳ field lạ (CV, compensation,
 * protected characteristic, performance note, health data, contact PII) đều
 * bị reject bằng `invalid_argument`, không âm thầm loại bỏ.
 */
export async function createPeopleRiskDossier(
  ctx: TenantContext,
  input: CreatePeopleRiskDossierInput
): Promise<PeopleRiskSnapshot> {
  const validated = validateCreateInput(input);

  await requireHumanProjectContext(ctx, validated.projectId);

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(validated.projectId);
  const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  try {
    return await db.transaction(async (tx) => {
      const dossierId = generateSnowflake();

      // `uix_people_risk_dossiers_project` (migration 012) bắt buộc duy nhất
      // 1 dossier/project — race giữa 2 request tạo đồng thời cho cùng
      // project bị chặn ở tầng DB (catch bên dưới).
      await tx.insert(peopleRiskDossiers).values({
        id: dossierId,
        workspaceId: wsId,
        projectId: projId,
        status: "DRAFT",
        currentVersion: 1,
        createdByMemberId: actorMemberId,
      });

      const [revision] = await tx
        .insert(peopleRiskDossierRevisions)
        .values({
          id: generateSnowflake(),
          workspaceId: wsId,
          projectId: projId,
          dossierId,
          version: 1,
          status: "DRAFT",
          capacityBands: validated.capacityBands,
          riskSignals: validated.riskSignals,
          sourceRefs: validated.sourceRefs,
          reasonCode: validated.reasonCode,
          actorMemberId,
        })
        .returning();

      if (!revision) throw APIError.internal("failed to create people risk dossier");

      return toSnapshot(dossierId, revision);
    });
  } catch (err: any) {
    if (err?.cause?.code === "23505" || err?.code === "23505") {
      throw APIError.alreadyExists("a people risk dossier already exists for this project");
    }
    throw err;
  }
}

/**
 * Founder/member append một revision mới (CAS theo expectedVersion). Đặt
 * status "CONFIRMED" chỉ hợp lệ khi ctx là human founder/co-founder — đúng
 * tinh thần "A founder alone confirms a people policy/decision" của
 * task-1-brief. Model/agent context luôn bị chặn ở
 * `requireHumanProjectContext` trước khi chạm DB.
 */
export async function appendPeopleRiskRevision(
  ctx: TenantContext,
  dossierId: string,
  expectedVersion: number,
  input: AppendPeopleRiskRevisionInput
): Promise<PeopleRiskSnapshot> {
  // Xem ghi chú đầy đủ ở `requireHumanContext` phía trên.
  requireHumanContext(ctx);

  const validated = validateAppendInput(input);

  const wsId = BigInt(ctx.workspaceId);
  const dossierBigId = BigInt(dossierId);

  const [dossier] = await db
    .select()
    .from(peopleRiskDossiers)
    .where(and(eq(peopleRiskDossiers.id, dossierBigId), eq(peopleRiskDossiers.workspaceId, wsId)))
    .limit(1);
  if (!dossier) throw APIError.notFound("people risk dossier not found in workspace");

  if (dossier.currentVersion !== expectedVersion) {
    throw APIError.aborted(
      `CAS_CONFLICT: stale dossier version (expected ${expectedVersion}, got ${dossier.currentVersion})`
    );
  }

  const nextStatus = validated.status ?? (dossier.status as PeopleRiskDossierStatus) ?? "DRAFT";
  if (nextStatus === "CONFIRMED") {
    const role = (ctx.membershipRole || "").toLowerCase();
    if (!["founder", "co-founder"].includes(role)) {
      throw APIError.permissionDenied(
        "FOUNDER_CONFIRMATION_REQUIRED: Only a human founder can confirm a people risk decision"
      );
    }
  }

  const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;
  const nextVersion = dossier.currentVersion + 1;

  return db.transaction(async (tx) => {
    const [prior] = await tx
      .select({ id: peopleRiskDossierRevisions.id })
      .from(peopleRiskDossierRevisions)
      .where(eq(peopleRiskDossierRevisions.dossierId, dossierBigId))
      .orderBy(desc(peopleRiskDossierRevisions.version))
      .limit(1);

    const [revision] = await tx
      .insert(peopleRiskDossierRevisions)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: dossier.projectId,
        dossierId: dossierBigId,
        version: nextVersion,
        status: nextStatus,
        capacityBands: validated.capacityBands,
        riskSignals: validated.riskSignals,
        sourceRefs: validated.sourceRefs,
        reasonCode: validated.reasonCode,
        actorMemberId,
        confirmedByMemberId: nextStatus === "CONFIRMED" ? actorMemberId : null,
        confirmedAt: nextStatus === "CONFIRMED" ? new Date() : null,
        supersedesRevisionId: prior?.id ?? null,
      })
      .returning();
    if (!revision) throw APIError.internal("failed to append people risk dossier revision");

    const [updatedDossier] = await tx
      .update(peopleRiskDossiers)
      .set({
        currentVersion: nextVersion,
        status: nextStatus,
        updatedAt: new Date(),
      })
      .where(
        and(
          eq(peopleRiskDossiers.id, dossierBigId),
          eq(peopleRiskDossiers.currentVersion, expectedVersion)
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
 * Đọc snapshot mới nhất (chỉ classified aggregate data — capacity_bands,
 * risk_signals, source_refs — KHÔNG BAO GIỜ raw attachment) của People Risk
 * Dossier theo Project. Model/agent context ĐƯỢC PHÉP đọc (chỉ không được
 * ghi). Project ở workspace khác hoặc project khác trong CÙNG workspace đều
 * bị từ chối bằng permission_denied — không lộ thông tin tồn tại/không tồn
 * tại của project chéo tenant hay chéo project.
 */
export async function readPeopleRiskSnapshot(
  ctx: TenantContext,
  projectId: string
): Promise<PeopleRiskSnapshot> {
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
    .from(peopleRiskDossiers)
    .where(and(eq(peopleRiskDossiers.workspaceId, wsId), eq(peopleRiskDossiers.projectId, projId)))
    .orderBy(desc(peopleRiskDossiers.updatedAt))
    .limit(1);
  if (!dossier) {
    throw APIError.notFound("no people risk dossier found for this project");
  }

  const [revision] = await db
    .select()
    .from(peopleRiskDossierRevisions)
    .where(eq(peopleRiskDossierRevisions.dossierId, dossier.id))
    .orderBy(desc(peopleRiskDossierRevisions.version))
    .limit(1);
  if (!revision) {
    throw APIError.internal("people risk dossier has no revisions");
  }

  return toSnapshot(dossier.id, revision);
}
